---
name: backlog-orchestrator
description: Autonomously executes a bounded dependency-linked GitHub issue tranche across one or more repositories and GitHub Projects. Prefer a parent/epic/build-order issue as the execution manifest. Builds and reconciles the DAG, delegates one issue per Sonnet worker using isolated worktrees and installed skills, coordinates stacked PR ancestry, supervises workers end-to-end, and stops on explicit scope/repair budgets instead of consuming unbounded usage.
---

# Backlog Orchestrator

Execute a prepared GitHub backlog tranche autonomously using parallel implementation workers.

The orchestrator owns scope, dependency reasoning, scheduling, worker-pool lifetime, recovery, and escalation. It does **not** implement tickets itself. Each implementation ticket is delegated to one worker which must invoke `implement-issue`.

## Core invariants

1. **GitHub is durable state.** Reconstruct from issues, dependencies, branches, PRs, and CI after interruption.
2. **A run is bounded.** Never turn one build-order ticket into an open-ended project crawl.
3. **One worker = one issue = one isolated checkout.** Concurrent workers never share a working tree/index.
4. **Sonnet is the default worker model.** The orchestrator may use the strongest available reasoning model.
5. **Only READY work is dispatched.** Hard dependencies must be available on the calculated base.
6. **Execution dependency is not automatically Git ancestry.** Stack only when code ancestry requires it.
7. **Workers implement; the orchestrator coordinates.** Reuse installed skills (`implement-issue`, `create-pr`, `resolve-pr-comment`, `merge-stack`) rather than reproducing them.
8. **The parent owns worker lifetime.** It remains in a supervision/heartbeat loop while workers are active.
9. **Retries and repair cycles are bounded.** Failure eventually becomes `NEEDS_USER`, not another autonomous attempt.
10. **Recovery is idempotent.** Never duplicate branches, PRs, or implementations after a restart.

# Environment capabilities

This skill must work in Claude Desktop cloud containers, Claude Code from a local folder/worktree, Remote Control, and similar Claude Code environments.

Detect capabilities at runtime. Prefer, where appropriate:

1. local `git` for branch/worktree/history operations when a checkout exists;
2. authenticated local `gh` for GitHub operations when available;
3. GitHub MCP for equivalent GitHub operations when `gh` is unavailable;
4. native Claude Code subagent/task APIs for model selection, worker dispatch, worktree isolation, completion messages, and waiting;
5. installed user/project skills from the active Claude configuration.

Do not hardcode `~/.claude/skills` as the only skill path. Workers must inherit or receive the same required installed skills as the orchestrator. If skills can be preloaded declaratively, preload them; otherwise instruct workers to invoke them by name and verify availability.

Missing optional tooling must degrade safely:

- no `gh` -> use GitHub MCP;
- no native Stack support -> use ordinary PR base/head relationships;
- no native worker wait -> perform bounded meaningful task/GitHub reconciliation;
- no safe worktree isolation -> serialize that repository rather than sharing a checkout.

# Invocation and scope

Support these entry modes, in preference order.

## 1. Build-order / parent / epic issue — preferred

Treat the supplied root issue as an **execution manifest**.

### Strict manifest boundary

By default, the runnable set is:

- the manifest's direct sub-issues;
- their recursive sub-issues/descendants;
- issues explicitly named in the manifest body/comments as implementation items.

Do **not** automatically add arbitrary neighboring issues merely because they:

- share a GitHub Project;
- share a label/milestone;
- block or are blocked by a manifest child;
- are linked from a child for background/context;
- are in the same repository.

An issue outside the manifest descendant set may be read as an **external prerequisite** when necessary to understand readiness, but it is not authorized for implementation unless the root manifest explicitly includes it or the user supplied it as part of the run.

If a child requires an external unfinished prerequisite, mark that child `BLOCKED_EXTERNAL` and continue unrelated in-scope work. Do not silently enlarge the run.

The root manifest itself is coordination metadata and is not assigned to a worker unless it contains independent implementation acceptance criteria.

## 2. Explicit issue set

The supplied issues are the implementation boundary. Read their dependencies for readiness, but do not implement dependency issues outside the supplied set unless explicitly authorized.

## 3. One or more GitHub Projects

Projects are discovery surfaces, not execution graphs. Combine supplied FE/BE/shared projects into one DAG, deduplicating canonical issue URLs.

If one or more build-order/root issues are identifiable, prefer the selected root as the execution manifest instead of sweeping the whole project. If project-driven scope remains broad/ambiguous, create a bounded candidate set before dispatch and apply the run budget below.

# Default usage safeguards

These defaults apply unless the user explicitly overrides them.

- **Maximum concurrent implementation workers:** 4.
- **Maximum newly started issues per orchestrator run:** 12.
- **Maximum autonomous implementation attempts per issue:** 2 total before escalation/stop.
- **Maximum model escalation per issue:** 1 escalation to the strongest available model.
- **Maximum CI repair cycles per PR:** 2.
- **Maximum review-fix cycles per PR:** 2.
- **Maximum lost-worker redispatches per issue:** 1.
- **No automatic PR merges.** Merging requires explicit merge authority / `merge-stack` invocation.

A "cycle" may resolve multiple closely related CI failures or review comments in one pass. Do not count every comment as a separate cycle when one coherent fix addresses them together.

## Run-budget behavior

Before dispatch, calculate the bounded issue set and report its size internally. If the scope exceeds the per-run issue-start budget, execute only the highest-priority READY portion up to the budget. When the run reaches the budget:

1. allow already-running workers to reach a durable result;
2. do not start additional issues;
3. reconcile GitHub state;
4. return a checkpoint showing completed/active/remaining work;
5. require a new invocation/explicit continuation for the next batch.

A restart caused by infrastructure failure does **not** reset the conceptual budget for issues already started in that tranche; reconstruct started work from GitHub before dispatching more.

## Repair-budget behavior

Workers and the orchestrator must track repair attempts. When a PR exhausts CI/review/implementation repair allowance, return `NEEDS_USER` with:

- issue + PR;
- what is failing;
- fixes already attempted;
- latest relevant error/review request;
- recommended next action.

Do not perform another speculative repair merely because capacity remains elsewhere.

`NEEDS_USER` blocks that node and its dependents but does not stop independent DAG branches.

# Models and skills

Use the strongest available reasoning model for orchestration.

Normal implementation workers must use **Sonnet** explicitly when the worker API permits model selection. Do not accidentally inherit the orchestrator's model.

Escalate one worker to the strongest available model only when:

- Sonnet has failed and the remaining problem is reasoning/architecture related;
- the user explicitly requests it; or
- the issue is clearly unusually ambiguous/cross-system before implementation begins.

Do not repeatedly alternate models.

Workers must have access to the active installed skill set, especially:

- `implement-issue`
- `create-pr`
- `resolve-pr-comment`
- repository/project-specific skills required by the issue

`merge-stack` is used only when merge authority has been explicitly granted; normal implementation workers do not merge their PRs.

If a required skill is unavailable in the worker context, return `BLOCKED` instead of hand-rolling a replacement workflow.

# 1. Discover and validate the bounded DAG

For every in-scope issue capture repository, issue URL, body/comments as needed, state, parent/sub-issue relationships, blocked-by/blocking relationships, linked PRs, explicit build order, and source manifest.

Read each participating repo's `CLAUDE.md`/`AGENTS.md` and relevant specs. Repositories may use different default branches/workflows.

Build one DAG across all participating repositories where `A -> B` means B cannot safely be implemented until A reaches the state B requires.

Classify dependencies:

- **Hard same-repo code dependency:** B needs unmerged code from A.
- **Execution dependency only:** ordering matters, but B does not need A's branch contents.
- **Shared-parent fanout:** B and C both require A but not each other.
- **Cross-repository dependency:** scheduler/readiness edge only; never Git ancestry.
- **External prerequisite:** dependency outside the authorized run boundary; inspect for readiness but never implement automatically.

Validate cycles, missing targets, contradictory edges, cancelled/closed inconsistencies, and manifest references to missing issues. Pause affected paths only where possible.

# 2. Reconcile durable state

Before dispatch classify each in-scope issue using GitHub evidence:

- `DONE`
- `PR_OPEN`
- `CI_RUNNING`
- `CI_FAILED`
- `IN_REVIEW`
- `IMPLEMENTING`
- `READY`
- `BLOCKED`
- `BLOCKED_EXTERNAL`
- `NEEDS_USER`
- `NOT_READY`

Never create a second matching PR. If a branch exists without a PR, determine whether it contains recoverable work before assigning another worker.

On restart, re-expand the same manifest/scope and reconcile GitHub before dispatching anything.

# 3. Compute the READY frontier

An issue is READY only when:

1. it is authorized/in scope;
2. it is not already complete/active;
3. hard dependencies are sufficiently satisfied;
4. required base exists;
5. no unresolved blocker/`NEEDS_USER` ancestor prevents it;
6. both concurrency and run-start budgets allow dispatch.

Prioritize explicit manifest build order, then project priority, then work unlocking the largest downstream subtree, then stable issue order.

# 4. Calculate branch and PR topology

Determine the exact required base before dispatch.

- Independent issue -> repository default/integration branch.
- Same-repo hard dependency B on unmerged A -> B branches from A and B's PR targets A's branch.
- Fanout B/C on A -> both independently target A; do not linearize B -> C.
- Multiple unmerged sibling dependencies with no common valid base -> block rather than inventing a linear stack/merge.
- Cross-repo dependency -> scheduler edge only.

Ordinary GitHub PR base/head relationships are the durable stack representation. Native GitHub Stack/`gh stack` metadata is optional enrichment only.

# 5. Dispatch workers with mandatory isolation

Every implementation worker owns an isolated checkout for the lifetime of its issue.

For a local Git repo, allocate a dedicated worktree whose branch starts from the exact calculated base. If the Claude worker API supports native worktree isolation, use it. An environment-provided isolated clone also satisfies the invariant if exclusively owned by that worker.

Concurrent workers must never edit the same checkout, share an index, switch branches under one another, or reuse a worktree concurrently. If isolation is unavailable, reduce that repository's concurrency to one.

Before dispatch:

1. calculate/fetch required base;
2. create/allocate issue branch + isolated worktree;
3. record issue -> repo -> worktree -> branch -> base -> worker;
4. increment the run's newly-started-issue count only if this issue has not previously been started in the current tranche;
5. dispatch the worker as Sonnet by default.

Worker contract:

```text
You are a Sonnet implementation worker. You own exactly one backlog issue.

Issue: <ISSUE URL>
Repository: <OWNER/REPO>
Working directory: <DEDICATED WORKTREE/CHECKOUT>
Branch: <ISSUE BRANCH>
Required base: <BASE BRANCH>
Execution manifest: <ROOT ISSUE OR NONE>

Required installed skill: implement-issue

Use the installed implement-issue skill end-to-end. Do not hand-roll its workflow. Do not switch checkout, broaden scope, choose another ticket, or merge the PR.

Budgets for this issue:
- implementation attempts remaining: <N>
- CI repair cycles remaining: <N>
- review-fix cycles remaining: <N>
- model escalation remaining: <N>

If a budget is exhausted or a judgment call remains, return NEEDS_USER rather than trying again.

Return:
- issue
- repository
- working directory
- outcome: PR_OPEN | BLOCKED | NEEDS_USER | FAILED
- branch/base
- PR URL/number
- head SHA
- checks run
- CI/review state
- attempts/cycles consumed
- blocker/escalation details
```

After durable branch/PR state exists and no follow-up needs the exact checkout, a clean worktree may be removed. Never delete uncommitted/unpushed work.

# 6. End-to-end worker lifecycle

`implement-issue` owns the implementation lifecycle inside each worker:

1. read issue/comments/specs;
2. validate scope/dependencies;
3. implement in the assigned worktree;
4. run required local checks;
5. invoke `create-pr` with the calculated base;
6. trigger the repository's automated review via `create-pr`;
7. monitor CI/review where supported;
8. make bounded targeted CI fixes;
9. use `resolve-pr-comment` for bounded review fixes;
10. return durable PR state or `NEEDS_USER`/`BLOCKED`.

The orchestrator does not duplicate those fixes. It tracks the high-level state, budgets, and whether downstream work can be dispatched.

# 7. Parent supervision / heartbeat

After dispatching workers, the main orchestrator thread remains active while any worker is running or completion can unlock more work.

Each heartbeat cycle performs real work:

1. consume worker status/completion messages;
2. classify workers running/complete/blocked/failed/lost;
3. reconcile GitHub branches/PRs for changed workers;
4. inspect relevant CI/review summaries;
5. update per-issue attempt/repair budgets;
6. recompute READY frontier;
7. fill free slots only when the run-start budget allows;
8. surface any new `NEEDS_USER` item promptly while continuing independent work;
9. wait using a native task/agent wait mechanism when available, then repeat.

If no native wait exists, perform bounded periodic checks of actual worker/GitHub state. Do not use fake CPU/file-touch/unbounded shell activity as a keepalive.

The parent must not return a final response while workers remain active, except when the worker runtime itself has failed and GitHub reconciliation shows continuation is unsafe/unreliable.

## Lost worker handling

On worker disappearance:

1. inspect its isolated worktree for recoverable changes;
2. inspect GitHub for branch/PR state;
3. adopt durable work if present;
4. otherwise redispatch once into a safe isolated checkout;
5. after the redispatch budget is exhausted, mark `NEEDS_USER`/infrastructure failure and continue unrelated work.

# 8. Worker outcomes

## PR_OPEN

Verify PR exists, head/base topology is correct, issue is linked, and expected commits exist. Same-repo descendants may become READY once the upstream branch safely exists; they do not always need the parent PR merged.

## BLOCKED / BLOCKED_EXTERNAL

Record the blocker and stop that path. If the blocker is an unfinished out-of-scope prerequisite, do not add it to the run automatically.

## FAILED

Retry only within the issue's remaining implementation budget. A transient failure may receive one Sonnet retry. A reasoning-heavy repeated failure may receive at most one strongest-model escalation. After budget exhaustion -> `NEEDS_USER`.

## NEEDS_USER

Surface it to the user in the parent progress/output as soon as practical, including PR/issue, failure, attempts, and recommendation. Do not keep spending tokens on that node. Continue independent branches where safe.

# 9. Stack behavior

For dependent PRs, `create-pr` records `Depends on: <parent PR URL>` and uses the calculated base branch.

The orchestrator may create stacks/fanout while implementing, but **does not merge them automatically**. If the user later invokes/authorizes `merge-stack`, that skill owns merge ordering and descendant rebasing/restacking.

# Stop conditions

Stop dispatching new work when any of these occurs:

- all in-scope issues reached the requested durable state;
- the per-run newly-started-issue budget is reached;
- every remaining path is blocked/`NEEDS_USER`;
- user asks to stop;
- safety/destructive-operation approval is needed;
- infrastructure repeatedly fails.

A blocker on one DAG branch does not stop independent work.

# Progress reporting

Keep concise state such as:

```text
Manifest: backend#500 — Custom Fields build order
Scope: 18 authorized issues
Run budget: 9/12 issues started
Complete/PR open: 6
Active: 3
Ready: 4
Blocked: 3
Needs user: 2
```

For each `NEEDS_USER`, include the issue/PR and reason without burying it in general status.

# Completion / checkpoint

Before returning, reconcile GitHub. Report:

- manifest/scope executed;
- issues started vs run budget;
- PRs grouped by repository and stack relationship;
- remaining CI/review work;
- `NEEDS_USER` failures with attempted fixes;
- blocked external prerequisites;
- unstarted in-scope issues and why;
- whether invoking the same manifest again can safely continue the next batch.
