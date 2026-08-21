---
name: backlog-orchestrator
description: Autonomously executes a bounded dependency-linked implementation tranche from GitHub Issues, Linear, or another supported tracker. Prefers a parent/epic/build-order issue as the execution manifest, validates the DAG before dispatch, resumes safely after interruption, delegates one issue per Sonnet implementation worker using isolated worktrees and durable remote checkpoints, centrally supervises all PR CI/review activity, dispatches bounded repair workers, coordinates stacked PR ancestry, and enforces explicit usage/repair budgets.
---

# Backlog Orchestrator

Execute a prepared implementation tranche autonomously using a supervised worker pool.

The orchestrator owns **scope, DAG reasoning, scheduling, worker-pool lifetime, PR event supervision, repair budgets, recovery, and escalation**. It does not implement application code itself.

Implementation and repair logic lives in reusable worker skills:

- `validate-backlog` — mandatory shallow DAG preflight; optional deep validation;
- `implement-issue-core` — one issue → code → checks → durable remote checkpoints → PR;
- `repair-pr` — one bounded CI or review repair pass;
- `create-pr` — tracker linkage, stack metadata, PR creation/review trigger;
- `resolve-pr-comment` — thread-level review repair primitive used by `repair-pr`;
- `merge-stack` — separately authorized merge/restack workflow.

`implement-issue` remains a standalone one-ticket orchestrator and is **not** the normal worker primitive for this backlog orchestrator. Using `implement-issue-core` directly prevents implementation workers from sitting idle while waiting for CI/reviews and keeps lifecycle ownership centralized in the parent.

# Core invariants

1. **Tracker + GitHub remote state are durable truth.** Never depend only on parent/subagent conversation state or local worktrees.
2. **Canonical issue identity is the full issue URL.** Short keys/numbers are display helpers only.
3. **A run is bounded.** Never turn one build-order ticket into an open-ended project crawl.
4. **One implementation worker = one issue = one isolated checkout.** Concurrent workers never share mutable Git state.
5. **In-flight implementation is remotely checkpointed.** Meaningful completed work must not live only inside an ephemeral cloud worktree.
6. **Sonnet is the default implementation and repair model.** The orchestrator may use the strongest available reasoning model.
7. **Only validated READY work is dispatched.**
8. **Execution dependency is not automatically Git ancestry.** Stack only where code ancestry requires it.
9. **The parent owns all long-lived PR supervision.** Implementation/repair workers perform bounded work and return; they do not wait indefinitely for GitHub events.
10. **Retries and repair are bounded.** Failure eventually becomes `NEEDS_USER`.
11. **Recovery is idempotent.** Never duplicate implementations, branches, PRs, or repairs after restart.
12. **No automatic merges.** Merge authority is separate and explicit.

# Tracker abstraction

Determine tracker from each canonical issue URL.

Primary supported trackers:

- GitHub Issues: `https://github.com/.../issues/...`
- Linear: `https://linear.app/.../issue/...`

Other trackers may be used only when reliable read/status/dependency support and PR-linking semantics exist.

Prefer tracker-native structured metadata where available:

- parent/sub-issue hierarchy;
- `blocked by` / `blocking` relationships;
- status/state;
- project/priority/build-order fields.

Also inspect descriptions/comments for explicit dependency language because textual dependencies may not yet have been normalized.

## Completion semantics

### GitHub

A correctly linked implementation PR uses a full-URL GitHub closing relationship. Treat issue closed + implementation PR merged as canonical `DONE`. If a correctly linked merged PR failed to auto-close due to unusual stack/base behavior, explicitly close only after verifying that exact PR implemented the issue.

### Linear

A PR must retain the full Linear issue URL and repository/workspace linking convention. Treat configured terminal Linear status + linked merged implementation PR as canonical `DONE`. Do not manually complete Linear issues unless workspace policy explicitly requires that fallback.

# Environment capabilities

This skill must work in Claude Desktop cloud containers, local Claude Code folders/worktrees, Remote Control sessions, and equivalent environments.

Prefer safely available capabilities:

1. local `git` for branch/worktree/history operations;
2. authenticated local `gh` for GitHub operations;
3. GitHub MCP when `gh` is unavailable;
4. tracker-specific tools/MCP (for example Linear) for issue reads/writes;
5. native Claude task/subagent APIs for model choice, isolated worktrees, completion notifications, and waits;
6. installed skills from the active Claude configuration.

Missing optional capabilities degrade safely:

- no `gh` → GitHub MCP;
- no native Stack feature → ordinary PR base/head relationships;
- no tracker dependency fields → structured metadata available + text scan + warning;
- no worktree isolation → serialize that repository;
- no event subscription → bounded meaningful polling from the parent.

Do not hardcode one skills directory. Workers must inherit/preload required installed skills.

# Invocation and bounded scope

Support these entry modes, in preference order.

## 1. Parent / epic / build-order issue — preferred

Treat the supplied root as an execution manifest.

Default authorized implementation set:

- direct sub-issues;
- recursive sub-issues/descendants;
- issues explicitly named by the manifest as implementation items.

External dependencies may be inspected for readiness but are not authorized for implementation unless explicitly included by the root/user.

Do not absorb work merely because it shares a project, repo, label, milestone, or contextual link.

The root itself is coordination metadata unless it contains independent implementation acceptance criteria.

## 2. Explicit issue set

The supplied full issue URLs form the implementation boundary. Read external dependencies for readiness only.

## 3. One or more project boards/projects

Projects are discovery surfaces, not execution graphs. Combine FE/BE/shared projects into one candidate DAG. Prefer an identifiable selected build-order/root issue before dispatching broad project work.

# Mandatory validation preflight

Before dispatching any **new** implementation worker, invoke `validate-backlog shallow` on the entire bounded scope.

Use the validator's normalized DAG rather than rebuilding a separate competing graph.

The validator must inspect native hierarchy/dependencies plus text dependency statements and detect cycles, missing targets, contradictions, duplicates, and scope leaks.

Results:

- `PASS` → proceed;
- `PASS_WITH_WARNINGS` → proceed only where warnings do not make ordering unsafe;
- `FAIL` → stop affected paths, continuing only validator-confirmed safe independent branches.

Do not automatically mutate dependency metadata. GitHub normalization is handled separately by `normalize-github-dependencies` when requested.

`validate-backlog deep` is optional and user-invoked because it can consume materially more model/code-reading budget.

# Default usage safeguards

Unless explicitly overridden:

- max concurrent implementation workers: **4**;
- max newly started issues per invocation: **12**;
- max implementation attempts per issue: **2 total**;
- max strongest-model escalation per issue: **1**;
- max CI repair cycles per PR: **2**;
- max review-fix cycles per PR: **2**;
- max lost-worker redispatches per issue: **1**;
- automatic merges: **disabled**.

A repair cycle may handle one coherent group of related failures/comments. Never create infinite fix/review loops.

When the 12-new-issue limit is reached, allow active workers/repairs to reach durable state, stop starting new issues, reconcile, and return a checkpoint. Restarting does not count already-adopted work as newly started.

Budget exhaustion on a node → `NEEDS_USER`, not another speculative attempt. Continue unrelated DAG branches safely.

# Model and skill policy

The orchestrator uses the strongest available reasoning model where available.

Normal implementation and repair workers use **Sonnet explicitly** when the subagent API supports model selection. Do not accidentally inherit the parent's stronger model.

At most one strongest-model implementation escalation is allowed for a reasoning-heavy repeated failure.

Implementation workers must have `implement-issue-core` and `create-pr`. Repair workers must have `repair-pr` and, for review fixes, `resolve-pr-comment`.

If a required skill is unavailable in a worker, return `BLOCKED` rather than improvising a substitute workflow.

# Durable state and restart

After validation and before dispatch, reconcile every in-scope issue from tracker + GitHub remote evidence:

- `DONE`
- `PR_OPEN`
- `CI_RUNNING`
- `CI_FAILED`
- `IN_REVIEW`
- `IMPLEMENTING_REMOTE`
- `READY`
- `BLOCKED`
- `BLOCKED_EXTERNAL`
- `NEEDS_USER`
- `NOT_READY`

## Durable implementation evidence

Prefer evidence in this order:

1. merged linked implementation PR + tracker terminal state;
2. open linked implementation PR;
3. remote issue branch with pushed commits/checkpoints;
4. local worktree only (least durable; never sufficient across container restart).

A cloud worktree is ephemeral. **Do not claim restart safety for unpushed local changes.**

## Restart / resume

On restart:

1. re-expand exactly the same bounded scope;
2. rerun shallow validation;
3. order by normalized DAG + explicit build order;
4. fetch current tracker status, PRs, and remote branches;
5. skip every proven `DONE` issue;
6. adopt existing PRs;
7. adopt matching remote issue branches with checkpoints even when no PR exists yet;
8. identify the earliest still-unfinished executable frontier;
9. resume there.

"Latest unclosed ticket" means the earliest remaining unfinished point in the established build sequence, not the numerically newest issue. Parallel groups can have multiple resume-frontier nodes.

Never restart from the beginning merely because the parent session died.

## Branch discoverability

Follow repository branch conventions. Where conventions permit, branch names should include the issue key/number to improve recovery (`123-...`, `FEP-195-...`). Never violate repo naming rules just to enforce this.

If branch naming is not enough to identify an orphan remote branch safely, inspect commit messages/diffs/tracker development metadata. If still ambiguous, return `NEEDS_USER` rather than attaching the wrong branch to an issue.

# DAG and PR topology

Classify validated dependencies by implementation reality:

- hard same-repo code dependency;
- execution dependency only;
- shared-parent fanout;
- cross-repo scheduler dependency;
- external prerequisite.

PR base relationships are the durable stack representation.

Linear same-repo chain:

```text
main -> A -> B -> C
```

means B targets A's branch and C targets B's.

Fanout:

```text
main -> A
        ├-> B
        └-> C
```

B and C both target A and never each other merely due to timing.

Multiple unmerged siblings with no valid common base → block rather than invent an integration merge.

Cross-repo dependencies never become Git stack ancestry.

# Worker dispatch and mandatory isolation

Every implementation worker owns one isolated checkout for its issue.

For local repos, create a dedicated worktree from the exact calculated base. Use native worktree isolation where available. An exclusive environment clone also qualifies.

Concurrent workers must never share one working tree/index or switch branches under one another. If isolation cannot be created, reduce that repository's concurrency to one.

Before dispatch:

1. calculate/fetch exact required base;
2. create/identify issue branch;
3. allocate isolated worktree/check-out;
4. record canonical issue URL → tracker → repo → worktree → branch → base → worker;
5. dispatch Sonnet worker with `implement-issue-core`.

Worker prompt includes canonical issue URL, tracker, repo, worktree, branch, required base, manifest, dependency context, and implementation budget.

## Remote checkpoint requirement

`implement-issue-core` must:

1. push the issue branch early so it has remote identity;
2. commit/push meaningful coherent checkpoints during substantial implementation;
3. push final implementation state before returning;
4. create/verify the PR;
5. return remote branch/PR/head SHA.

Do not use commits as fake heartbeat activity. Checkpoint after meaningful completed work so container destruction loses only the most recent unfinished chunk.

# Central PR supervision — parent responsibility

Once an implementation worker returns `PR_OPEN`, **its worker slot is released**. The implementation worker does not remain alive waiting for CI/review.

The parent owns all long-lived PR state for every active PR.

For each PR maintain:

```text
canonical issue URL
tracker
PR URL
branch/base
remote head SHA
CI state
review state
CI repair cycles used/remaining
review repair cycles used/remaining
stack parent/children
```

## Event subscriptions

Prefer available event-driven mechanisms for:

- workflow/check completion/failure;
- PR review/comment activity;
- branch/head changes;
- merge/close events.

If event subscriptions are unavailable, the **parent** performs bounded polling at reasonable intervals. Avoid one child agent per PR sitting idle.

The parent heartbeat therefore has genuine work: consuming worker completions, consuming/reconciling PR events, updating state/budgets, dispatching repairs, and unlocking DAG nodes.

## CI failure handling

On relevant CI failure:

1. retrieve the smallest useful failure/log context;
2. determine whether failure belongs to the PR;
3. if code repair is justified and budget remains, allocate an isolated checkout/worktree for the PR branch and dispatch one Sonnet worker invoking `repair-pr` with `repair type = ci`;
4. adopt its pushed remote head and increment the repair cycle;
5. release the repair worker immediately;
6. parent resumes waiting for CI.

If failure is external/flaky and no code change is justified, do not consume a repair cycle.

After CI budget exhaustion → `NEEDS_USER`.

## Review handling

On actionable review feedback:

1. group the coherent current review round;
2. if review budget remains, allocate an isolated checkout of the PR branch and dispatch one Sonnet `repair-pr` worker with `repair type = review`;
3. the repair worker uses `resolve-pr-comment` where relevant, commits/pushes, and returns;
4. adopt new head and increment review cycle;
5. retrigger/request review if repo convention requires it;
6. parent resumes waiting.

Product/architecture judgment → `NEEDS_USER` without speculative repair.

## Repair-worker isolation

Never allow an implementation worker and repair worker to mutate the same branch simultaneously. A PR branch may have only one active mutating worker at a time.

Before repair, verify remote head has not moved unexpectedly. If it has, reconcile/recreate the repair checkout from the current remote head.

# Parent supervision / anti-idle loop

The main orchestrator thread must remain active while any of the following exists:

- implementation worker running;
- repair worker running;
- active PR waiting for CI/review and more in-scope work/repair may occur;
- a completion/event may unlock another READY issue;
- the run has not hit a stop condition.

Each heartbeat cycle performs real orchestration work:

1. consume implementation/repair worker completion messages;
2. verify all active workers still exist;
3. reconcile tracker status + GitHub remote branches/PRs;
4. consume/reconcile CI/review/PR events;
5. update remote-head and repair-budget state;
6. dispatch required bounded repair workers;
7. recompute READY frontier;
8. fill available implementation slots while run budget permits;
9. inspect stack ancestry changes that affect descendants;
10. surface new `NEEDS_USER` states promptly;
11. wait using native task/event wait where available, then repeat.

Do not use detached sleeps, CPU loops, file-touch loops, or meaningless commits solely to keep the container alive.

### Why parent-owned PR supervision matters

This event loop is deliberately parent-owned because it:

- gives the Desktop cloud parent continuing legitimate work while children are short-lived;
- avoids Sonnet agents consuming context/slots while idle;
- centralizes repair budgets and DAG unlocking;
- makes restart reconstruction possible entirely from remote state.

This reduces but **does not guarantee elimination** of cloud container idle/session termination. Remote checkpoints remain mandatory recovery protection.

## Parent termination

Do not return final while a mutating worker is active.

For PRs merely waiting on external CI/review, continue event supervision while the environment supports it and the run remains active. If the runtime cannot remain alive reliably while only external events are pending, reconcile all remote durable state and return a restartable checkpoint rather than pretending monitoring will continue.

# Lost worker handling

If an implementation worker disappears:

1. inspect GitHub remote branch/PR first;
2. inspect local worktree if container still exists;
3. adopt pushed checkpoints/PR when present;
4. if only local unpushed work survives, preserve it and push before redispatch if safe;
5. redispatch at most once from latest durable remote checkpoint;
6. after repeated loss → `NEEDS_USER`/infrastructure failure.

If the entire cloud container disappears, local worktrees are assumed lost. Resume from the most recent remote branch checkpoint/PR only.

A lost repair worker follows the same rule: inspect remote head before retrying and never double-apply a repair that was already pushed.

# Stack mutation while PRs are open

When an upstream stack branch receives a new implementation/review/CI commit, descendants may temporarily be based on its older history.

Do not blindly restack every descendant after every parent push; this creates unnecessary churn. Instead:

- record that descendants may be `STACK_STALE`;
- before treating a descendant as final review-ready/merge-ready, reconcile its ancestry;
- before/after parent merge, use `merge-stack`/restack logic as required;
- if stale ancestry makes CI/review diffs misleading, restack earlier before continuing that descendant.

Any rebase/restack that changes a descendant remote branch must be reflected in parent PR state before more repairs are dispatched to that branch.

# Outcomes

## PR_OPEN

Implementation reached durable remote PR state. Parent assumes supervision.

## BLOCKED / BLOCKED_EXTERNAL

Stop affected path; never silently enlarge scope.

## FAILED

Retry only inside implementation/lost-worker budgets. At most one strongest-model escalation when reasoning-heavy. Then `NEEDS_USER`.

## NEEDS_USER

Surface canonical issue URL + PR URL, failure/review state, attempts already consumed, and recommended action. Stop spending tokens on the node but continue safe independent branches.

# Merge behavior

Normal orchestration never merges automatically.

If user separately authorizes `merge-stack`, that skill owns merge ordering and descendant rebasing/restacking. After merge, parent/restart reconciliation verifies tracker completion semantics.

# Stop conditions

Stop starting new implementation work when:

- all in-scope issues reached requested durable state;
- 12-new-issue budget reached;
- every remaining path is blocked/`NEEDS_USER`;
- user asks to stop;
- safety approval is needed;
- infrastructure repeatedly fails.

If only external CI/review is pending and the environment cannot safely stay active, return a durable checkpoint explicitly stating what needs reconciliation on restart.

# Progress and checkpoint output

Keep concise parent state such as:

```text
Manifest: <full URL>
Validation: PASS
Scope: 18 issues
Run budget: 9/12 newly started
Implementation workers: 3
Repair workers: 1
Active PRs: 7
Waiting CI/review: 4
Ready: 3
Blocked: 2
Needs user: 1
Resume frontier: <full URL(s)>
```

Before returning, reconcile tracker + GitHub remote state and report:

- validation result/warnings;
- manifest/scope;
- resume frontier;
- implementation/repair workers still active (normally none before final);
- PRs and stack topology;
- remote checkpoint branches without PRs;
- CI/review states and repair budgets consumed;
- issue-linkage/tracker-status inconsistencies;
- `NEEDS_USER` items;
- external blockers;
- unstarted work and why;
- whether invoking the same manifest can safely resume.
