---
name: backlog-orchestrator
description: Autonomously executes a bounded dependency-linked implementation tranche from GitHub Issues, Linear, or another supported tracker. Prefers Claude Code Dynamic Workflows when available, while preserving a validated issue DAG, Sonnet workers, isolated worktrees, durable remote checkpoints, stacked PR topology, centralized PR supervision, bounded repairs, and restart-safe tracker/GitHub state.
---

# Backlog Orchestrator

Execute a prepared implementation tranche autonomously.

This skill is the **policy and backlog layer**. Claude's runtime may provide the worker scheduling/persistence layer.

The orchestrator owns:

- bounded scope;
- DAG validation and scheduling policy;
- worker model/concurrency/budgets;
- issue -> repo -> branch/base topology;
- stacked PR relationships;
- long-lived PR/CI/review supervision;
- repair dispatch;
- recovery and escalation.

It does **not** implement application code itself.

Reusable worker skills:

- `validate-backlog` — shallow/deep DAG validation;
- `implement-issue-core` — one issue -> code -> local checks -> remote checkpoints -> PR;
- `repair-pr` — one bounded CI or review repair pass;
- `create-pr` — issue linkage, stack metadata, PR creation, review trigger;
- `resolve-pr-comment` — thread-level review fix primitive;
- `merge-stack` — separately authorized stack merge/restack workflow.

`implement-issue` remains the convenient standalone **single-issue orchestrator**. Do not replace it with this skill for normal one-ticket work.

# Core invariants

1. **Tracker + GitHub remote state are durable truth.** Conversation state, workflow state, and cloud worktrees are caches/conveniences, not the only source of truth.
2. **Canonical issue identity is the full issue URL.** Short keys/numbers are display helpers only.
3. **A run is bounded.** Never turn one build-order ticket into an open-ended project crawl.
4. **One implementation worker = one issue = one isolated checkout/worktree.**
5. **In-flight implementation is remotely checkpointed.** Significant completed work must not exist only in an ephemeral container.
6. **Sonnet is the default implementation/repair model.** Use the strongest available reasoning model for orchestration when appropriate.
7. **Only validated READY work is dispatched.**
8. **Execution dependency is not automatically Git ancestry.** Stack only where code ancestry requires it.
9. **The parent/orchestration layer owns long-lived PR state.** Implementation and repair workers are bounded and short-lived.
10. **Retries and repairs are bounded.** Persistent failure becomes `NEEDS_USER`.
11. **Recovery is idempotent.** Never duplicate work, branches, PRs, or repairs after restart.
12. **No automatic merges.** Merge authority is explicit and separate.

# Execution runtime

The orchestration policy must be independent of the mechanism used to run workers.

## Preferred runtime: Claude Code Dynamic Workflows

When Dynamic Workflows are available in the current Claude Code/Desktop environment and can preserve the supplied execution contract, **prefer a Dynamic Workflow** as the runtime for the backlog run.

Use the Dynamic Workflow for:

- persistent multi-agent scheduling;
- fanout/concurrency;
- worker lifecycle and completion signaling;
- runtime-level progress persistence/resumption;
- first-class PR promotion/visibility when the platform provides it;
- platform-native CI/review/PR event surfacing where available.

Do **not** give the Dynamic Workflow permission to redefine the product backlog. It must execute the already validated bounded DAG supplied by this skill.

The workflow must preserve all of these policies:

- exact authorized issue set;
- normalized dependency DAG;
- maximum concurrency;
- Sonnet worker model by default;
- one issue per implementation worker;
- isolated checkout/worktree per mutating worker;
- exact calculated branch/base for each issue;
- remote checkpoint rules;
- retry/repair budgets;
- stack/fanout topology;
- tracker/PR completion semantics;
- no merge authority unless explicitly granted.

A Dynamic Workflow is the **execution substrate**, not the source of truth.

## Fallback runtimes

If Dynamic Workflows are unavailable or cannot honor the required DAG/worker constraints, degrade in this order where possible:

1. native/background Claude sessions or agent-team/task primitives;
2. ordinary isolated subagents with the explicit parent supervision loop defined below;
3. serialized execution when safe isolation/concurrency cannot be provided.

Do not abandon the orchestration run merely because Dynamic Workflows are unavailable.

## Runtime detection

At startup determine whether the current environment provides:

- Dynamic Workflows;
- first-class/background agent sessions;
- native worktree isolation;
- PR promotion/event monitoring;
- local `git`;
- authenticated `gh`;
- GitHub MCP;
- tracker-specific tooling (for example Linear);
- installed required skills.

Prefer native/runtime capabilities when they implement the required behavior safely, but retain tracker + GitHub remote state as recovery truth.

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

# Invocation and bounded scope

Support these entry modes, in preference order.

## 1. Parent / epic / build-order issue — preferred

Treat the supplied root as the execution manifest.

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

Use the validator's normalized DAG as the scheduling graph. Do not let the execution runtime independently invent a competing decomposition.

Results:

- `PASS` -> proceed;
- `PASS_WITH_WARNINGS` -> proceed only where warnings do not make ordering unsafe;
- `FAIL` -> stop affected paths; continue only validator-confirmed independent safe branches.

Do not automatically mutate dependency metadata. GitHub normalization is handled separately by `normalize-github-dependencies` when requested.

`validate-backlog deep` is optional/user-invoked because it can consume materially more model/code-reading budget.

# Default usage safeguards

Unless explicitly overridden:

- maximum concurrent implementation workers: **4**;
- maximum newly started issues per invocation: **12**;
- maximum implementation attempts per issue: **2 total**;
- maximum strongest-model escalation per issue: **1**;
- maximum CI repair cycles per PR: **2**;
- maximum review-fix cycles per PR: **2**;
- maximum lost-worker redispatches per issue: **1**;
- automatic merges: **disabled**.

Dynamic Workflows do not override these limits. Do not increase concurrency merely because the runtime can fan out more agents.

When the 12-new-issue limit is reached, allow active workers/repairs to reach durable state, stop starting new issues, reconcile, and return a checkpoint. Restarting does not count already-adopted work as newly started.

Budget exhaustion on a node -> `NEEDS_USER`, not another speculative attempt. Continue unrelated DAG branches safely.

# Model and skill policy

The orchestration/lead context may use the strongest available reasoning model.

Normal implementation and repair workers must use **Sonnet explicitly** when the runtime supports per-worker model selection. Do not accidentally inherit the lead's stronger model.

At most one strongest-model implementation escalation is allowed for a reasoning-heavy repeated failure.

Implementation workers require `implement-issue-core` and `create-pr`.
Repair workers require `repair-pr` and, for review fixes, `resolve-pr-comment`.

Workers must inherit/preload the active installed skills. If a required skill is unavailable, return `BLOCKED` rather than improvising a replacement workflow.

# Durable remote state and restart

Classify in-scope issues from tracker + GitHub remote evidence:

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

Prefer durable evidence in this order:

1. merged linked implementation PR + tracker terminal state;
2. open linked implementation PR;
3. remote issue branch with pushed checkpoints;
4. runtime/workflow-local state;
5. local worktree only.

A cloud worktree is ephemeral. Never claim restart safety for unpushed local changes.

## Restart / resume

On restart, including after Dynamic Workflow interruption:

1. re-expand the exact same bounded manifest/scope;
2. rerun `validate-backlog shallow`;
3. order by normalized DAG + explicit build order;
4. fetch current tracker statuses, PRs, and remote branches;
5. skip every proven `DONE` issue;
6. adopt existing open PRs;
7. adopt matching remote issue branches/checkpoints even when no PR exists yet;
8. reconcile any runtime-level Dynamic Workflow resume state when available;
9. identify the earliest still-unfinished executable frontier;
10. resume there.

Runtime persistence is useful but **must not be required** for correctness. A fresh orchestration session must be able to recover from tracker + GitHub remote state alone.

"Latest unclosed ticket" means the earliest remaining unfinished point in established build order, not the numerically newest issue. Parallel groups may have multiple resume-frontier nodes.

## Branch discoverability

Follow repository branch conventions. Where permitted, include the issue key/number (`123-...`, `FEP-195-...`) to improve recovery. Never violate documented naming rules solely for this.

If an orphan remote branch cannot be safely mapped to an issue, inspect commit/diff/tracker development metadata. If still ambiguous -> `NEEDS_USER`.

# DAG and PR topology

Classify validated dependencies by implementation reality:

- hard same-repo code dependency;
- execution dependency only;
- shared-parent fanout;
- cross-repo scheduler dependency;
- external prerequisite.

Ordinary PR base/head relationships are the durable stack representation.

Same-repo chain:

```text
main -> A -> B -> C
```

B targets A's branch; C targets B's.

Fanout:

```text
main -> A
        |-> B
        `-> C
```

B and C both target A and never each other merely because of timing.

Multiple unmerged sibling dependencies with no valid common base -> block rather than invent an integration merge.

Cross-repo dependencies are scheduler edges only and never Git stack ancestry.

# Implementation worker contract

Each implementation worker owns one isolated checkout for one issue.

For local repos, create a dedicated worktree from the exact calculated base. Use runtime-native worktree isolation where available. An exclusive runtime clone also qualifies.

Concurrent workers must never share one mutable checkout/index. If isolation cannot be provided, serialize that repository.

Before dispatch:

1. calculate/fetch exact required base;
2. create/identify issue branch;
3. allocate isolated worktree/check-out;
4. record canonical issue URL -> tracker -> repo -> worktree -> branch -> base -> worker;
5. dispatch Sonnet worker with `implement-issue-core`.

Under Dynamic Workflows, provide these constraints to every workflow worker explicitly. Do not let a worker select another backlog ticket when it finishes.

## Remote checkpoint requirement

`implement-issue-core` must:

1. push the issue branch early so it has remote identity;
2. commit/push meaningful coherent checkpoints during substantial implementation;
3. push final implementation state before returning;
4. create/verify the PR;
5. return remote branch/PR/head SHA.

Do not create meaningless checkpoint commits merely as heartbeat activity. Checkpoint after meaningful completed work so container loss discards only the most recent unfinished chunk.

# PR promotion and central supervision

A PR opened by a worker may be promoted by Claude Desktop/Dynamic Workflows into the parent/top-level session. **Use that first-class platform PR state when available.** Do not create a duplicate monitor merely because the PR originated in a child worker.

Once an implementation worker reaches `PR_OPEN`, release that implementation worker. Long-lived PR supervision belongs to the parent/runtime orchestration layer.

For every active PR track:

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

## Event handling

Prefer platform-native/promoted PR events and Dynamic Workflow notifications for:

- CI/check completion/failure;
- review/comment activity;
- branch/head changes;
- merge/close events.

If those are unavailable, fall back to other event subscriptions, then bounded parent polling.

The parent remains the **policy owner** even when Claude Desktop performs the observation. The platform may surface that CI failed or review feedback arrived; this skill decides whether budgets allow repair and what worker to dispatch.

Do not keep one Sonnet worker alive per PR merely to wait.

# CI/review repair

On an actionable CI failure:

1. retrieve the smallest useful failure context;
2. decide whether it belongs to this PR;
3. if repair is justified and budget remains, allocate an isolated checkout of the current PR branch;
4. dispatch one Sonnet `repair-pr` worker with `repair type = ci`;
5. adopt its pushed remote head;
6. increment the CI repair cycle;
7. release the repair worker and resume event supervision.

External/flaky failure with no justified code change does not consume a repair cycle.

On actionable review feedback:

1. group the coherent current review round;
2. if budget remains, allocate an isolated checkout of the current PR branch;
3. dispatch one Sonnet `repair-pr` worker with `repair type = review`;
4. `repair-pr` uses `resolve-pr-comment` where relevant;
5. adopt the new remote head and increment review cycle;
6. retrigger/request review when repo convention requires it;
7. release worker and resume event supervision.

Product/architecture judgment -> `NEEDS_USER` rather than speculative repair.

A PR branch may have only **one active mutating worker** at a time. Before repair, verify the remote head has not moved unexpectedly.

# Parent / Dynamic Workflow supervision loop

## Dynamic Workflow path

When running as a Dynamic Workflow, keep the workflow/lead responsible for:

1. worker completion events;
2. promoted PR/CI/review events;
3. tracker + GitHub reconciliation;
4. repair budgets;
5. repair-worker dispatch;
6. READY-frontier recomputation;
7. new implementation-worker dispatch;
8. stack ancestry state;
9. `NEEDS_USER` surfacing;
10. stop/checkpoint decisions.

Use the workflow runtime's own persistence/waiting primitives instead of inventing artificial keepalive work.

## Fallback explicit parent loop

If Dynamic Workflows are unavailable, the main parent thread must remain active while mutating workers run or active PR events can lead to more in-scope work.

Each cycle performs real work:

1. consume worker completions;
2. reconcile tracker + remote branches/PRs;
3. consume/reconcile CI/review events;
4. update heads/budgets;
5. dispatch repairs;
6. recompute READY frontier;
7. fill available worker slots;
8. inspect stack ancestry changes;
9. surface `NEEDS_USER`;
10. wait using native task/event wait, then repeat.

Do not use CPU loops, file-touch loops, detached sleeps, meaningless commits, or other fake activity solely to prevent idling.

Dynamic Workflow persistence substantially reduces reliance on this fallback anti-idle behavior, but remote Git checkpoints remain mandatory because platform/runtime persistence is not the same as durable source control.

# Lost worker / workflow recovery

If a worker disappears:

1. inspect remote branch/PR first;
2. inspect local worktree only if the container still exists;
3. adopt pushed checkpoints/PR;
4. redispatch at most once from latest durable remote checkpoint;
5. repeated loss -> `NEEDS_USER`/infrastructure failure.

If the whole cloud container/workflow disappears, assume local worktrees are lost. Resume from remote branches/PRs plus tracker state.

Never double-apply a repair already pushed by a worker whose runtime status was lost.

# Stack mutation while PRs are open

When an upstream stack branch changes, descendants may become `STACK_STALE`.

Do not blindly restack every descendant after every upstream push. Instead:

- record stale ancestry;
- restack before descendant diffs/CI/review become misleading;
- ensure ancestry is correct before merge-ready state;
- use `merge-stack` for authorized merge/restack operations;
- reconcile new remote heads before dispatching further repairs.

# Outcomes

- `PR_OPEN` — implementation reached durable remote PR state; parent/runtime owns supervision.
- `BLOCKED` / `BLOCKED_EXTERNAL` — stop affected path; never silently enlarge scope.
- `FAILED` — retry only inside budgets; at most one reasoning escalation.
- `NEEDS_USER` — surface full issue/PR URLs, failure/review state, attempts consumed, and recommended action; stop spending tokens on that node while continuing safe independent branches.

# Merge behavior

Normal orchestration never merges automatically.

If the user separately authorizes `merge-stack`, that skill owns merge ordering and descendant rebasing/restacking. Reconcile tracker completion after every merge.

# Stop conditions

Stop starting new implementation work when:

- all in-scope issues reached requested durable state;
- the 12-new-issue budget is reached;
- all remaining paths are blocked/`NEEDS_USER`;
- the user asks to stop;
- safety approval is required;
- infrastructure/runtime repeatedly fails.

If only external CI/review remains and the runtime cannot safely stay active, reconcile durable state and return a restartable checkpoint rather than pretending monitoring will continue.

# Progress / checkpoint output

Keep concise state, for example:

```text
Runtime: Dynamic Workflow
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

- runtime used;
- validation result/warnings;
- manifest/scope;
- resume frontier;
- PRs + stack topology;
- remote checkpoint branches without PRs;
- CI/review states + repair budgets consumed;
- issue-linkage/tracker-status inconsistencies;
- `NEEDS_USER` items;
- external blockers;
- unstarted work and why;
- whether invoking the same manifest can safely resume.
