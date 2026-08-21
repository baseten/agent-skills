---
name: backlog-orchestrator
description: Autonomously executes a dependency-linked GitHub issue backlog across one or more repositories. Builds and reconciles the issue DAG, identifies ready work, delegates one issue per implementation agent via implement-issue, coordinates stacked PR ancestry for same-repo code dependencies, and continuously dispatches newly unblocked work. Use when asked to execute, fan out, or work through a prepared GitHub backlog/project rather than a single issue.
---

# Backlog Orchestrator

Execute a prepared GitHub backlog autonomously using parallel implementation agents.

The orchestrator owns coordination, dependency reasoning, dispatch, recovery, and progress. It does not implement tickets itself. Each ticket is delegated to a dedicated worker which must invoke `implement-issue`.

## Core rules

1. **GitHub is durable state.** Reconstruct state from issues, dependency links, branches, PRs, and CI on startup and after interruption. Never rely solely on conversation/task state.
2. **One worker, one issue.** Workers never choose their next ticket.
3. **Dispatch only ready work.** Every hard implementation dependency must be available on the branch the worker will use.
4. **Parallelize independent work aggressively, not blindly.**
5. **Execution dependency is not automatically PR ancestry.** Stack only when downstream code genuinely needs an unmerged upstream branch.
6. **Workers implement; the orchestrator coordinates.** Reuse `implement-issue`, `create-pr`, `resolve-pr-comment`, and other installed skills rather than duplicating them.
7. **Remain active while workers run.** Continue reconciling worker/GitHub/CI state and dispatching newly ready work. Do not spawn workers and then end the main task while they remain active.
8. **Recovery is idempotent.** Never duplicate a branch, PR, or implementation because orchestration state was lost.

## Inputs

Accept the GitHub project/backlog/issue set, participating repositories, concurrency, root branches, stack preference, priority/build order, and optional stopping point when supplied. Discover anything that GitHub or repository metadata can answer instead of asking the user.

Default maximum implementation workers: **4**.

## Models

Use the strongest available reasoning model for orchestration. Use **Sonnet** for implementation workers by default. Escalate an individual worker when the user requests it, Sonnet has already failed, or the issue requires unusually ambiguous cross-system reasoning. Do not use the orchestrator context to implement code that can be delegated.

## 1. Discover backlog and repositories

Fetch the complete selected issue set. For each issue capture repository, number/URL, title/body, relevant comments, state, labels, parent/sub-issue and blocked-by relationships, linked PRs, referenced dependencies, and explicit priority/build-order metadata.

Include every participating repository, including frontend and backend repositories. Read each repo's `CLAUDE.md`/`AGENTS.md` and relevant docs. Do not assume repositories share the same default branch or workflow.

## 2. Build and validate the DAG

Construct a DAG where `A -> B` means B cannot safely be implemented until A reaches the state B requires.

Classify each dependency:

- **Hard code dependency:** B requires code/contracts/types/schema/API/components introduced by A. B must contain A's code or wait for A to merge.
- **Execution dependency only:** sequencing matters but B does not need A's branch contents. Do not create artificial PR ancestry.
- **Shared-parent fanout:** if B and C both require A but not each other, both branch from A. Never linearize this as A -> B -> C.
- **Cross-repository dependency:** stacks cannot span repositories. A consumer in another repo waits for the required integration surface unless that repo already has a stable contract allowing independent implementation. Never invent cross-repo contracts to increase parallelism.

Validate cycles, missing targets, cancelled/closed inconsistencies, duplicate tickets, contradictory edges, and ownership mismatches. Pause only affected paths when possible; unrelated DAG branches should continue.

## 3. Reconcile durable state

Before dispatch, classify issues using GitHub evidence: `DONE`, `PR_OPEN`, `CI_RUNNING`, `CI_FAILED`, `IN_REVIEW`, `IMPLEMENTING`, `READY`, `BLOCKED`, or `NOT_READY`.

Use merged/open PRs, branches, PR base/head relationships, CI, issue state, and dependency state. Never create a second matching PR. If a branch exists without a PR, determine whether it is active/abandoned before assigning another worker.

## 4. Compute the ready frontier

An issue is READY only when it is not complete/active, hard dependencies are sufficiently satisfied, its required base exists, no unresolved upstream blocker prevents it, and a worker slot is available.

Prioritize explicit build order first, then work that unlocks the largest downstream subtree, then shared/backend contracts before consumers, then stable issue order. Do not override explicit build order without a concrete reason.

## 5. Calculate branch/stack topology

For every issue determine its exact required base before dispatch.

- Independent issue: repository default/integration branch.
- Same-repo hard dependency B on unmerged A: B branches from A and B's PR targets A's branch.
- Fanout B/C on A: both target A independently; neither targets the other.
- Multiple unmerged sibling dependencies with no single branch containing all required code: do not invent a linear stack or merge siblings. Wait for upstream merges, use an explicitly documented integration workflow, or block that issue and report the topology conflict.

The DAG determines stack topology, not worker completion order.

## 6. Dispatch workers

Dispatch up to the concurrency limit using isolated worktrees/sessions where supported. Every worker receives exactly one issue, repository, required base, and relevant upstream context and uses Sonnet by default.

Worker instruction template:

```
You own exactly one backlog issue:
<ISSUE URL>

Repository: <OWNER/REPO>
Required base: <BASE BRANCH>
Upstream dependency context: <DEPENDENCIES OR NONE>

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
Determine whether another backlog ticket resolves the blocker, the DAG is missing an edge, the issue is genuinely ambiguous, or only this subtree is affected. If another backlog ticket resolves it, update scheduling and continue. Do not ask the user for information already present in backlog/docs/discussion.

### FAILED
Inspect the failure. Retry once with Sonnet for transient/operational failure. Escalate to a stronger model when failure is reasoning/architecture-related or repeated Sonnet attempts fail. Never loop indefinitely.

## 10. CI and review

`implement-issue` owns per-PR CI/review monitoring where supported. Track high-level PR health without duplicating comment-fix logic. Review fixes must use `resolve-pr-comment`. If an upstream stacked PR changes, coordinate required descendant rebase/restack before declaring descendants healthy.

## Restart and recovery

Assume the cloud container or parent session can disappear at any time. Every invocation begins by reconstructing current state from GitHub. A restarted orchestrator should be able to see merged/open/failed/ready/blocked issues and continue without user reconstruction.

A local state file may cache information but must never be the only record of issue ownership, branch, PR, dependency completion, or implementation state. Do not assume a worker lost with a previous container still exists.

## Stop conditions

Continue until:

1. all selected issues are complete or have reviewable PRs according to requested mode;
2. every remaining path genuinely requires user input;
3. the user asks to stop;
4. an unsafe/destructive operation requires explicit approval; or
5. repeated infrastructure/tool failure makes continued execution unreliable.

A blocker in one DAG branch does not stop independent work.

## Safety boundaries

Pause the affected issue rather than guessing on destructive DB migrations, irreversible data operations, production deployment, secrets/credential changes, unclear public API/schema decisions affecting multiple services, dependency contradictions, or semantic merge conflicts.

Routine implementation, branch creation, pushing, PR creation, CI fixes, stack rebases already implied by the approved topology, and review fixes are part of this workflow. **Do not merge PRs unless explicitly authorized.**

## Progress reporting

Keep a concise running summary rather than narrating every tool call, for example:

```
Backlog: 18 issues
Complete: 4
Active: 4
Ready: 3
Blocked: 1
Waiting: 6
```

Surface DAG problems, genuine product/spec blockers, persistent CI failures, and topology conflicts promptly.

## Completion

Before claiming completion, reconcile against GitHub. Report completed issues, PRs grouped by repository, stack relationships, remaining CI/review work, blockers, unstarted issues and why, and whether invoking this skill again can safely resume the backlog.
