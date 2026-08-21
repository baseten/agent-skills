---
name: backlog-orchestrator
description: Autonomously executes a dependency-linked GitHub issue backlog across one or more repositories and GitHub Projects. Prefer a parent/epic/build-order issue as a bounded execution manifest, but also supports explicit issue sets or one/more project boards. Builds and reconciles the issue DAG, identifies ready work, delegates one issue per Sonnet implementation agent via installed skills and isolated worktrees, coordinates stacked PR ancestry for same-repo code dependencies, and keeps the parent thread actively supervising workers until the run reaches a real stop condition.
---

# Backlog Orchestrator

Execute a prepared GitHub backlog autonomously using parallel implementation agents.

The orchestrator owns coordination, dependency reasoning, dispatch, recovery, progress, and worker-pool lifetime. It does not implement tickets itself. Each implementation ticket is delegated to a dedicated worker which must use the installed implementation skills.

## Core rules

1. **GitHub is durable state.** Reconstruct state from issues, dependency links, branches, PRs, projects, and CI on startup and after interruption. Never rely solely on conversation/task state.
2. **Prefer a bounded manifest.** When given a parent/epic/build-order issue, treat it as the execution boundary and derive the runnable graph from it rather than sweeping an entire project board.
3. **One worker, one issue, one isolated checkout.** Concurrent implementation workers must never share a working tree, index, or mutable checkout.
4. **Dispatch only ready work.** Every hard implementation dependency must be available on the branch the worker will use.
5. **Parallelize independent work aggressively, not blindly.**
6. **Execution dependency is not automatically PR ancestry.** Stack only when downstream code genuinely needs an unmerged upstream branch.
7. **Workers implement; the orchestrator coordinates.** Reuse `implement-issue`, `create-pr`, `resolve-pr-comment`, `merge-stack`, and other installed skills rather than duplicating them.
8. **The parent thread owns worker lifetime.** While any worker is active, the parent must remain in an explicit supervision/heartbeat loop and must not return a final response.
9. **Recovery is idempotent.** Never duplicate a branch, PR, or implementation because orchestration state was lost.

## Environment capabilities

This skill must work from Claude Desktop cloud containers, Claude Code in a local folder, local worktrees, Remote Control sessions, and other Claude Code environments. Detect capabilities at runtime rather than assuming one execution environment.

Prefer available capabilities in this order where appropriate:

1. local `git` for branch/worktree/history operations when a repository checkout is available;
2. local `gh` for GitHub reads/writes when authenticated and available;
3. GitHub MCP for equivalent GitHub reads/writes when `gh` is unavailable or the environment is remote/cloud;
4. native Claude Code subagent/task APIs for worker dispatch, model selection, worktree isolation, completion messages, and waiting;
5. installed user/project skills from the active Claude configuration directory.

Do not require `gh` merely because it exists in local examples, and do not require GitHub MCP when authenticated local tooling provides the same operation safely. Ordinary Git branch ancestry and explicit PR base/head relationships remain authoritative regardless of which GitHub interface is used.

### Skill location

Do not hardcode `~/.claude/skills` as the only valid skill location. Use the active Claude configuration/environment. In standard cloud containers this is commonly `~/.claude/skills`; local users may use a different `CLAUDE_CONFIG_DIR` or project-level skills.

Workers must receive or inherit the same required installed skills available to the orchestrator. If the subagent API supports preloading skills, preload them; otherwise instruct the worker to invoke the installed skill by name and verify availability before implementation.

### Capability degradation

Missing optional tooling should degrade cleanly:

- no `gh` -> use GitHub MCP if available;
- no native GitHub Stack support -> use ordinary PR bases;
- no native worker wait primitive -> perform bounded meaningful reconciliation cycles;
- no worktree-capable worker isolation -> do **not** run concurrent workers against one mutable checkout.

If the environment cannot provide an isolated checkout for a worker, serialize that repository's implementation work or return `BLOCKED` for concurrency rather than allowing workers to share a working tree.

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

Treat the supplied issues as the initial bounded set. Follow explicit dependency edges needed to make their DAG complete, but do not expand into unrelated neighboring backlog work.

### 3. One or more GitHub Projects

A project board is a discovery surface, **not** the execution graph. A shared FE/BE project and separate FE/BE projects are both valid. Collect eligible issues from every supplied project, then build one dependency DAG across them regardless of repository/project membership.

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

## Models and worker skills

Use the strongest available reasoning model for the orchestrator itself.

Implementation workers must use **Sonnet by default**. Do not inherit the orchestrator's model accidentally. When the subagent/task API supports an explicit model parameter, set it to Sonnet for every normal implementation worker.

Escalate an individual worker to the strongest available model only when:

- the user explicitly requests it;
- Sonnet has already failed on that issue;
- the issue requires unusually ambiguous cross-system architecture/reasoning; or
- a retry is specifically being performed as a reasoning escalation.

### Installed skills are part of the worker contract

Workers must have access to the same active user-level/project-level installed skill set, especially:

- `implement-issue`
- `create-pr`
- `resolve-pr-comment`
- `merge-stack` when relevant
- repository/project-specific skills required by the issue

Treat installed skills as shared environment capability rather than copying skill text into every worker prompt.

When the subagent API supports declaring/preloading skills, explicitly include the skills required for that worker. When it does not, instruct the worker to invoke the named installed skills and verify they are available before beginning implementation.

If a required skill is unavailable inside the worker context, return `BLOCKED` to the orchestrator rather than silently hand-rolling a substitute workflow.

Do not use the orchestrator context to implement code that can be delegated.

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

For every included issue capture repository, issue URL, title/body, relevant comments, state/labels, parent/sub-issue relationships, blocked-by/blocking relationships, linked PRs, referenced dependencies, project metadata, explicit build order, and source manifest.

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

Prioritize explicit manifest/build order first, then explicit project priority, work unlocking the largest downstream subtree, shared/backend contracts before consumers, then stable issue order.

Do not override explicit build order without a concrete dependency/safety reason.

## 5. Calculate branch/stack topology

For every issue determine its exact required base before dispatch.

- Independent issue: repository default/integration branch.
- Same-repo hard dependency B on unmerged A: B branches from A and B's PR targets A's branch.
- Fanout B/C on A: both target A independently; neither targets the other.
- Multiple unmerged sibling dependencies with no single branch containing all required code: do not invent a linear stack or merge siblings. Wait for upstream merges, use an explicitly documented integration workflow, or block that issue and report the topology conflict.
- Cross-repo dependency: never model it as Git branch ancestry. It remains a scheduler edge between separately based PRs.

The DAG determines stack topology, not worker completion order and not project-board layout.

## 6. Dispatch workers with mandatory checkout isolation

Dispatch up to the concurrency limit, but **every implementation worker must own an isolated checkout** for the lifetime of its issue.

### Worktree invariant

For a local Git repository, create or allocate a dedicated Git worktree per worker/issue. The worktree's branch must be created from the exact calculated base for that issue.

Conceptually:

```text
repo/
  main checkout
worktrees/
  ISSUE-101/   -> branch issue-101
  ISSUE-102/   -> branch issue-102
  ISSUE-103/   -> branch issue-103
```

For stacked work, create the child worker's branch/worktree from the calculated parent branch rather than the repository default branch.

When the Claude subagent API supports native `isolation: worktree` or equivalent, use it. When it does not, create/manage a Git worktree explicitly before handing the path to the worker.

An environment-provided isolated repository clone/check-out may satisfy this invariant if it is exclusively owned by that worker and cannot share mutable Git/index/worktree state with another concurrent worker.

### Never share a working tree

Concurrent workers must never:

- edit the same checkout;
- share one Git index;
- switch branches underneath one another;
- reuse one worktree concurrently even when touching different files;
- run implementation in the parent orchestrator's checkout while another worker can mutate it.

If safe isolation cannot be created, reduce concurrency for that repository to one. Do not silently fall back to multiple agents editing one checkout.

### Worktree lifecycle

Before dispatch:

1. calculate the required base;
2. fetch/verify that base;
3. create or allocate the issue branch and isolated worktree;
4. record issue -> repository -> worktree path -> branch -> base -> worker;
5. dispatch the worker into that worktree.

After the worker has produced durable branch/PR state and no follow-up worker requires that exact checkout, the worktree may be cleaned up. Never delete a worktree containing unpushed/uncommitted work. A restarted orchestrator must not depend on the old worktree existing; GitHub branch/PR state remains authoritative.

Every normal implementation worker must:

- use **Sonnet** explicitly where the API permits model selection;
- own exactly one issue;
- own exactly one isolated checkout/worktree;
- receive the exact repository and working directory;
- receive the exact required base branch;
- receive only the upstream dependency context it needs;
- have/inherit access to the installed skill set;
- invoke `implement-issue` rather than reproducing its workflow;
- avoid broadening scope;
- report a structured result to the orchestrator.

Worker instruction template:

```text
You are a Sonnet implementation worker. You own exactly one backlog issue:
<ISSUE URL>

Repository: <OWNER/REPO>
Working directory: <DEDICATED WORKTREE/CHECKOUT PATH>
Branch: <ISSUE BRANCH>
Required base: <BASE BRANCH>
Upstream dependency context: <DEPENDENCIES OR NONE>
Execution manifest: <ROOT ISSUE URL OR NONE>

Required installed skill: implement-issue
Other relevant installed skills are available from the active Claude skill environment.

This working directory is exclusively yours for this issue. Do not switch to another repository checkout or mutate another worker's worktree.

You MUST invoke the installed `implement-issue` skill rather than hand-rolling the workflow. Verify that required skills are available. If they are not, return BLOCKED rather than improvising a replacement workflow.

Respect the required base/stack ancestry above; do not replace it with the repository default branch. Work only on this issue. Do not choose another ticket when finished.

When complete report:
- issue
- repository
- working directory
- outcome: PR_OPEN | BLOCKED | FAILED
- branch
- base branch
- PR URL/number
- head commit SHA
- checks run
- CI/review state if known
- blocker details if blocked
```

## 7. Stacked PRs and PR bases

**PR base relationships are authoritative.** Do not require `gh stack`, native GitHub Stack metadata, or any other stack-specific tool in order to execute dependent work correctly.

For same-repository hard dependency chains, construct the stack with ordinary branches and explicit PR bases:

```text
main
  -> feature-a   (PR A base: main)
      -> feature-b   (PR B base: feature-a)
          -> feature-c   (PR C base: feature-b)
```

For fanout, preserve sibling ancestry rather than linearizing it:

```text
main
  -> feature-a
      -> feature-b   (PR B base: feature-a)
      -> feature-c   (PR C base: feature-a)
```

The ordinary GitHub PR base/head relationships are the durable representation the orchestrator must use for reconciliation and recovery. `create-pr` must receive the calculated explicit base and create the PR against that branch.

If native GitHub Stacked PR tooling or `gh stack` is available, it may be used optionally to add native stack metadata/UI or convenience operations, but absence of that tooling must never block orchestration. Do not make correctness depend on ephemeral local stack metadata such as `.git/gh-stack`.

If the available GitHub integration exposes only ordinary PR operations, use those operations directly. Creating a PR with `head: feature-b` and `base: feature-a` is sufficient to preserve the stack's Git ancestry and review diff even if GitHub does not expose that chain as a native Stack object.

If `create-pr` cannot target the required non-default base, stop that path and report the missing capability rather than silently targeting the repository default.

Never attempt to create one Git stack across multiple repositories. Cross-repo dependencies are coordinated by dispatch order/readiness and remain separately based PRs.

## 8. Parent supervision and heartbeat

The main orchestrator thread must stay alive for the entire worker wave. **Do not treat spawning workers as completion of the parent task.** This applies in cloud and local environments; in cloud it additionally reduces the risk of container/session idle termination.

Immediately after dispatching workers, enter a supervision loop and remain there while any worker is running, while a worker completion message is outstanding, or while completion may unlock more work.

### Heartbeat cycle

Each supervision cycle must perform real orchestration work:

1. inspect the native subagent/task list and consume any worker completion/status messages;
2. record each worker as running, complete, blocked, failed, or lost;
3. reconcile GitHub state for workers that may have pushed a branch or opened a PR;
4. inspect relevant CI/review state for newly created/changed PRs;
5. recompute the READY frontier;
6. immediately fill free worker slots from READY work, creating isolated worktrees first;
7. verify that currently running workers still exist before assuming they are active;
8. update the concise parent progress state;
9. wait using a native task/agent wait mechanism if one is available, then run the next cycle.

### Wait behavior

Prefer native Claude Code task/subagent waiting or completion notifications when available. A wait is part of the active orchestration task; after it returns, run another heartbeat cycle.

If there is no native wait primitive but workers are still active, perform bounded periodic checks of actual worker/task and GitHub state. Do **not** end the parent response merely because no worker completed during the last check.

Do not use an unbounded shell `sleep`, detached shell keepalive, CPU loop, file-touch loop, or other fake activity whose only purpose is keeping the environment alive. The heartbeat must always be attached to meaningful worker/GitHub reconciliation.

### Parent termination rule

The parent may return a final response only when:

- no worker is active and no READY work remains;
- every remaining path is genuinely blocked;
- the requested tranche has reached its requested completion state;
- the user asks to stop;
- a safety stop condition applies; or
- the worker/task runtime itself has failed and durable GitHub reconciliation confirms that continuing in the current session is not reliable.

If any worker is still active, **do not return a final answer**.

### Lost-worker handling

If a worker disappears or the task runtime reports it no longer exists:

1. inspect its worktree for uncommitted/unpushed changes if that worktree still exists;
2. inspect GitHub before retrying;
3. if the worker already produced a branch/PR, adopt that durable state rather than rerunning it;
4. if no durable result exists but recoverable work remains in the isolated worktree, preserve/recover it rather than overwriting it;
5. otherwise mark the worker lost and re-dispatch the issue once into a safe isolated checkout;
6. do not create duplicate PRs/branches;
7. if repeated worker loss occurs, stop that node and report infrastructure failure while continuing unrelated executable paths when safe.

This loop reduces the chance of Claude Desktop considering the parent finished while subagents are still working. It is not a guarantee against infrastructure/container termination; restart/recovery from GitHub remains mandatory.

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

Assume the cloud container, parent session, local process, or worker process can disappear at any time. Every invocation begins by reconstructing current state from GitHub.

For manifest-driven runs, the root/build-order issue is the preferred durable resume key: re-expand its bounded graph, then reconcile each node against branches/PRs/CI.

For explicit issue sets or project-driven runs, re-use the supplied scope inputs and deduplicate against GitHub-visible state.

A local state file may cache worker/worktree information but must never be the only record of issue ownership, branch, PR, dependency completion, or implementation state. Do not assume a worker or worktree from a previous environment still exists.

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

Routine implementation, isolated worktree creation, branch creation, pushing, PR creation, CI fixes, stack rebases already implied by the approved topology, and review fixes are part of this workflow. **Do not merge PRs unless explicitly authorized.**

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

Surface DAG problems, manifest inconsistencies, genuine product/spec blockers, persistent CI failures, topology conflicts, isolation failures, and repeated worker loss promptly.

## Completion

Before claiming completion, reconcile against GitHub. Report the manifest/scope executed, completed issues, PRs grouped by repository, stack relationships, remaining CI/review work, blockers, unstarted issues and why, and whether invoking this skill again with the same root can safely resume the tranche.
