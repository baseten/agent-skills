---
name: backlog-orchestrator
description: Autonomously executes a dependency-linked GitHub issue backlog across one or more repositories and GitHub Projects. Prefer a parent/epic/build-order issue as a bounded execution manifest, but also supports explicit issue sets or one/more project boards. Builds and reconciles the issue DAG, identifies ready work, delegates one issue per implementation agent via implement-issue, coordinates stacked PR ancestry for same-repo code dependencies, and continuously dispatches newly unblocked work. Use when asked to execute, fan out, or work through a prepared GitHub backlog/project rather than a single issue.
---

# Backlog Orchestrator

Execute a prepared GitHub backlog autonomously using parallel implementation agents.

The orchestrator owns coordination, dependency reasoning, dispatch, recovery, and progress. It does not implement tickets itself. Each ticket is delegated to a dedicated worker which must invoke `implement-issue`.

## Core rules

1. **GitHub is durable state.** Reconstruct state from issues, dependency links, branches, PRs, projects, and CI on startup and after interruption. Never rely solely on conversation/task state.
2. **Prefer a bounded manifest.** When given a parent/epic/build-order issue, treat it as the execution boundary and derive the runnable graph from it rather than sweeping an entire project board.
3. **One worker, one issue.** Workers never choose their next ticket.
4. **Dispatch only ready work.** Every hard implementation dependency must be available on the branch the worker will use.
5. **Parallelize independent work aggressively, not blindly.**
6. **Execution dependency is not automatically PR ancestry.** Stack only when downstream code genuinely needs an unmerged upstream branch.
7. **Workers implement; the orchestrator coordinates.** Reuse `implement-issue`, `create-pr`, `resolve-pr-comment`, and other installed skills rather than duplicating them.
8. **Remain active while workers run.** Continue reconciling worker/GitHub/CI state and dispatching newly ready work. Do not spawn workers and then end the main task while they remain active.
9. **Recovery is idempotent.** Never duplicate a branch, PR, or implementation because orchestration state was lost.

## Supported invocation modes

Support these entry points, in preference order:

### 1. Parent / epic / build-order issue — preferred

Example:

```text
/backlog-orchestrator https://github.com/acme/backend/issues/500
```

Treat the supplied issue as an **execution manifest** when it is clearly a parent, epic, build-order, rollout, or implementation-plan ticket.

Recursively discover the bounded body of work from:

- GitHub sub-issues / parent-child relationships;
- explicit issue links in the manifest body/comments;
- blocked-by / blocking relationships among those issues;
- explicitly referenced cross-repository dependency issues;
- ordered build-plan sections in the manifest when they name concrete issues.

The manifest itself is normally coordination metadata, not implementation work. Do **not** assign it to a worker unless it contains its own independent implementation acceptance criteria.

Execution scope is the graph reachable from the manifest through the relationships above. Do not include unrelated issues merely because they appear on the same GitHub Project, milestone, label, or repository.

### 2. Explicit issue set

Example:

```text
/backlog-orchestrator <issue-1> <issue-2> <issue-3>
```

Treat the supplied issues as the initial bounded set. Follow explicit dependency edges needed to make their DAG complete, but do not expand into unrelated neighboring backlog work.

### 3. One or more GitHub Projects

Example shapes include:

```text
Shared Project
├── FE repo
└── BE repo
```

and:

```text
FE Project ── FE repo
BE Project ── BE repo
```

A project board is a discovery surface, **not** the execution graph. Collect eligible issues from every supplied project, then build one dependency DAG across them regardless of repository/project membership.

When project-based discovery is used, infer intended scope from explicit status/priority/build-order fields and dependency links. If a build-order/root issue exists within the supplied project(s), prefer it as the execution manifest for that tranche rather than autonomously absorbing unrelated work.

## Inputs

Accept any of:

- parent/epic/build-order issue URL;
- explicit issue URLs;
- one or more GitHub Projects;
- participating repositories;
- concurrency;
- root/default branches;
- stack preference;
- priority/build order;
- optional stopping point.

Discover anything GitHub or repository metadata can answer instead of asking the user.

Default maximum implementation workers: **4**.

## Models

Use the strongest available reasoning model for orchestration. Use **Sonnet** for implementation workers by default. Escalate an individual worker when the user requests it, Sonnet has already failed, or the issue requires unusually ambiguous cross-system reasoning. Do not use the orchestrator context to implement code that can be delegated.

## 1. Discover execution scope, backlog, and repositories

First determine the invocation mode and execution boundary.

### Manifest-driven discovery

When given a build-order/root issue:

1. fetch the manifest body and all comments;
2. enumerate direct sub-issues and explicitly named implementation issues;
3. recursively follow child relationships;
4. include dependency issues necessary to make those child paths executable;
5. record explicit ordering and parallelism guidance from the manifest;
6. identify every participating repository and project represented by the resulting graph;
7. stop expansion at the manifest boundary rather than traversing into unrelated project work.

A build-order ticket may reference issues in multiple repositories and on multiple GitHub Projects. That is valid and does not change its role as the single execution boundary.

### Explicit-issue discovery

For each supplied issue, include its explicit hard dependencies and descendants required to understand ordering, while preserving the supplied set as the scope boundary.

### Project-driven discovery

For each supplied GitHub Project, fetch candidate issues and relevant project fields. Projects may overlap and may contain issues from multiple repositories. Deduplicate by canonical issue URL.

If separate FE and BE project boards are supplied, combine their issues into a single DAG. Cross-repository issue dependencies provide the coordination edges; project-board membership does not need to match those edges.

For every included issue capture:

- repository;
- issue number and URL;
- title/body;
- relevant comments;
- state and labels;
- parent/sub-issue relationships;
- blocked-by / blocking relationships;
- linked PRs;
- referenced dependency issues;
- project membership and relevant project fields;
- explicit priority/build-order metadata;
- source manifest, if any.

Read each participating repo's `CLAUDE.md`/`AGENTS.md` and relevant docs. Do not assume repositories share the same default branch or workflow.

## 2. Build and validate the DAG

Construct one DAG across all included repositories/projects where `A -> B` means B cannot safely be implemented until A reaches the state B requires.

The GitHub Project layout is not the DAG. A shared project, separate FE/BE projects, or no project at all are all valid as long as issue relationships define the execution graph.

Classify each dependency:

- **Hard code dependency:** B requires code/contracts/types/schema/API/components introduced by A. B must contain A's code or wait for A to merge.
- **Execution dependency only:** sequencing matters but B does not need A's branch contents. Do not create artificial PR ancestry.
- **Shared-parent fanout:** if B and C both require A but not each other, both branch from A. Never linearize this as A -> B -> C.
- **Cross-repository dependency:** stacks cannot span repositories. A consumer in another repo waits for the required integration surface unless that repo already has a stable contract allowing independent implementation. Never invent cross-repo contracts to increase parallelism.

When a manifest includes an explicit build order, use it as authoritative scheduling guidance unless it conflicts with concrete dependency reality. Preserve intentional parallel groups where the manifest indicates them.

Validate cycles, missing targets, cancelled/closed inconsistencies, duplicate tickets, contradictory edges, ownership mismatches, and manifest references to missing issues. Pause only affected paths when possible; unrelated DAG branches should continue.

## 3. Reconcile durable state

Before dispatch, classify issues using GitHub evidence: `DONE`, `PR_OPEN`, `CI_RUNNING`, `CI_FAILED`, `IN_REVIEW`, `IMPLEMENTING`, `READY`, `BLOCKED`, or `NOT_READY`.

Use merged/open PRs, branches, PR base/head relationships, CI, issue state, and dependency state. Never create a second matching PR. If a branch exists without a PR, determine whether it is active/abandoned before assigning another worker.

On restart, rediscover scope from the same manifest/issue set/project inputs where available, then reconcile against GitHub. The user should not need to reconstruct which workers previously existed.

## 4. Compute the ready frontier

An issue is READY only when it is not complete/active, hard dependencies are sufficiently satisfied, its required base exists, no unresolved upstream blocker prevents it, and a worker slot is available.

Prioritize:

1. explicit manifest/build-order sequence and parallel groups;
2. explicit project priority within that allowed order;
3. work that unlocks the largest downstream subtree;
4. shared/backend contracts before consumers;
5. stable issue order.

Do not override explicit build order without a concrete dependency/safety reason.

## 5. Calculate branch/stack topology

For every issue determine its exact required base before dispatch.

- Independent issue: repository default/integration branch.
- Same-repo hard dependency B on unmerged A: B branches from A and B's PR targets A's branch.
- Fanout B/C on A: both target A independently; neither targets the other.
- Multiple unmerged sibling dependencies with no single branch containing all required code: do not invent a linear stack or merge siblings. Wait for upstream merges, use an explicitly documented integration workflow, or block that issue and report the topology conflict.
- Cross-repo dependency: never model it as Git branch ancestry. It remains a scheduler edge between separately based PRs.

The DAG determines stack topology, not worker completion order and not project-board layout.

## 6. Dispatch workers

Dispatch up to the concurrency limit using isolated worktrees/sessions where supported. Every worker receives exactly one issue, repository, required base, and relevant upstream context and uses Sonnet by default.

Worker instruction template:

```text
You own exactly one backlog issue:
<ISSUE URL>

Repository: <OWNER/REPO>
Required base: <BASE BRANCH>
Upstream dependency context: <DEPENDENCIES OR NONE>
Execution manifest: <ROOT ISSUE URL OR NONE>

This issue is part of an orchestrated backlog.

You MUST invoke the installed `implement-issue` skill rather than hand-rolling the workflow. Respect the required base/stack ancestry above; do not replace it with the repository default branch. Work only on this issue.

When complete report:
- issue
- repository
- outcome: PR_OPEN | BLOCKED | FAILED
- branch
- base branch
- PR URL/number
- head commit SHA
- checks run
- CI/review state if known
- blocker details if blocked
```

## 7. Stacked PRs

Use the repository's supported GitHub stacked-PR tooling for same-repository hard dependency chains where available. The PR workflow must preserve the explicit base supplied by this orchestrator.

If `create-pr` cannot target the required non-default base, do not pretend the stack is correct: use supported stack tooling or report the missing capability.

Never attempt to create one Git stack across multiple repositories. Cross-repo dependencies are coordinated by dispatch order/readiness instead.

## 8. Active orchestration loop

After dispatching workers, keep the main orchestration task active. Repeatedly:

1. inspect worker/task status;
2. process completed reports;
3. reconcile corresponding GitHub branches/PRs;
4. inspect blockers and relevant CI/review state;
5. recompute the DAG frontier;
6. dispatch newly READY work into free slots;
7. preserve enough durable state that restart is safe;
8. continue until a stop condition is reached.

Do not manufacture meaningless busywork to prevent idleness. Poll/reconcile real task and GitHub state at reasonable intervals.

## 9. Handle worker outcomes

### PR_OPEN
Verify PR, head branch, calculated base, issue linkage, and expected commits. A same-repo stacked dependent may become READY once its upstream branch is safely available; it need not always wait for merge.

### BLOCKED
Determine whether another backlog ticket resolves the blocker, the DAG is missing an edge, the issue is genuinely ambiguous, or only this subtree is affected. If another backlog ticket resolves it, update scheduling and continue. Do not ask the user for information already present in the manifest, backlog, project fields, docs, or discussion.

### FAILED
Inspect the failure. Retry once with Sonnet for transient/operational failure. Escalate to a stronger model when failure is reasoning/architecture-related or repeated Sonnet attempts fail. Never loop indefinitely.

## 10. CI and review

`implement-issue` owns per-PR CI/review monitoring where supported. Track high-level PR health without duplicating comment-fix logic. Review fixes must use `resolve-pr-comment`. If an upstream stacked PR changes, coordinate required descendant rebase/restack before declaring descendants healthy.

## Restart and recovery

Assume the cloud container or parent session can disappear at any time. Every invocation begins by reconstructing current state from GitHub.

For manifest-driven runs, the root/build-order issue is the preferred durable resume key: re-expand its bounded graph, then reconcile each node against branches/PRs/CI.

For explicit issue sets or project-driven runs, re-use the supplied scope inputs and deduplicate against GitHub-visible state.

A local state file may cache information but must never be the only record of issue ownership, branch, PR, dependency completion, or implementation state. Do not assume a worker lost with a previous container still exists.

## Stop conditions

Continue until:

1. all selected issues in the bounded execution graph are complete or have reviewable PRs according to requested mode;
2. every remaining path genuinely requires user input;
3. the user asks to stop;
4. an unsafe/destructive operation requires explicit approval; or
5. repeated infrastructure/tool failure makes continued execution unreliable.

A blocker in one DAG branch does not stop independent work.

Do not expand the scope merely because the current manifest/tranche completes. A separate build-order/root ticket is a separate run unless the user explicitly requests broader execution.

## Safety boundaries

Pause the affected issue rather than guessing on destructive DB migrations, irreversible data operations, production deployment, secrets/credential changes, unclear public API/schema decisions affecting multiple services, dependency contradictions, or semantic merge conflicts.

Routine implementation, branch creation, pushing, PR creation, CI fixes, stack rebases already implied by the approved topology, and review fixes are part of this workflow. **Do not merge PRs unless explicitly authorized.**

## Progress reporting

Keep a concise running summary rather than narrating every tool call. Include the current manifest/scope when useful, for example:

```text
Manifest: backend#500 — Custom Fields build order
Backlog: 18 issues across 2 repos / 2 projects
Complete: 4
Active: 4
Ready: 3
Blocked: 1
Waiting: 6
```

Surface DAG problems, manifest inconsistencies, genuine product/spec blockers, persistent CI failures, and topology conflicts promptly.

## Completion

Before claiming completion, reconcile against GitHub. Report the manifest/scope executed, completed issues, PRs grouped by repository, stack relationships, remaining CI/review work, blockers, unstarted issues and why, and whether invoking this skill again with the same root can safely resume the tranche.
