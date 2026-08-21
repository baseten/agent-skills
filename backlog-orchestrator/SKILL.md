---
name: backlog-orchestrator
description: Autonomously executes a bounded dependency-linked implementation tranche from GitHub Issues, Linear, or another supported tracker. Prefers a parent/epic/build-order issue as the execution manifest, validates the DAG before dispatch, resumes safely after interruption, delegates one issue per Sonnet worker using isolated worktrees and installed skills, coordinates stacked PR ancestry, supervises workers end-to-end, and enforces explicit usage/repair budgets.
---

# Backlog Orchestrator

Execute a prepared implementation tranche autonomously using parallel workers.

The orchestrator owns scope, DAG reasoning, scheduling, worker-pool lifetime, recovery, and escalation. It does **not** implement tickets itself. Each implementation issue is delegated to one worker using `implement-issue`.

## Core invariants

1. **The issue tracker + GitHub PR state are durable state.** Reconstruct after interruption; never depend only on conversation/task state.
2. **Canonical issue identity is always the full issue URL.** Short keys/numbers are display helpers only.
3. **A run is bounded.** Never turn one build-order ticket into an open-ended project crawl.
4. **One worker = one issue = one isolated checkout.** Concurrent workers never share a mutable worktree/index.
5. **Sonnet is the default implementation model.** The orchestrator may use the strongest available reasoning model.
6. **Only validated READY work is dispatched.**
7. **Execution dependency is not automatically Git ancestry.** Stack only when code ancestry requires it.
8. **Workers implement; the orchestrator coordinates.** Reuse `validate-backlog`, `implement-issue`, `create-pr`, `resolve-pr-comment`, and `merge-stack`.
9. **The parent owns worker lifetime.** Stay in the supervision/heartbeat loop while workers are active.
10. **Retries/repair are bounded.** Failure eventually becomes `NEEDS_USER`.
11. **Recovery is idempotent.** Never duplicate branches, PRs, or implementations after restart.

# Tracker abstraction

Determine tracker from each canonical issue URL.

Supported primary trackers:

- GitHub Issues: `https://github.com/.../issues/...`
- Linear: `https://linear.app/.../issue/...`

Other trackers may be used only when the environment has reliable read/status/dependency support and the repository documents PR-linking semantics.

For every tracker prefer native structured metadata where available:

- parent/sub-issue hierarchy;
- `blocked by` / `blocking` relationships;
- state/status;
- project/priority/build-order fields.

Always also inspect issue description/comments for explicit dependency language because textual blockers may not yet have been normalized into native relationships.

## Completion semantics

Completion is tracker-specific:

### GitHub issue

A correctly linked implementation PR should contain a GitHub closing relationship using the full issue URL. On merge to the appropriate closing branch, the issue should close automatically. Treat issue closed + implementation PR merged as canonical `DONE` evidence.

### Linear issue

A PR must contain the full Linear issue URL plus the Linear issue identifier/linking convention required by the repository's Linear↔GitHub integration. Linear status automation may move the issue to Done/Completed on merge. Treat the configured terminal Linear status + linked implementation PR merged as canonical `DONE` evidence.

Do not manually close/complete a Linear issue merely because a PR merged unless repository/workspace policy explicitly requires that fallback.

# Environment capabilities

Work in Claude Desktop cloud, local Claude Code folders/worktrees, Remote Control, or equivalent environments.

Prefer available capabilities safely:

1. local `git` for worktrees/history;
2. authenticated `gh` for GitHub operations;
3. GitHub MCP when `gh` is unavailable;
4. tracker-specific tools/MCP for issue reads/writes (e.g. Linear);
5. native Claude subagent/task APIs for worker dispatch, Sonnet selection, worktree isolation, status, and waiting;
6. installed skills from the active Claude configuration.

Missing optional tooling must degrade safely. No worktree isolation => serialize that repo. No tracker dependency fields exposed => use available structured metadata + text and report limitations. No `gh` => GitHub MCP. No native Stack support => ordinary PR base/head relationships.

# Invocation and bounded scope

Support these modes, in preference order.

## 1. Parent / epic / build-order issue — preferred

Treat the supplied root issue as an execution manifest.

Default authorized implementation set:

- direct sub-issues;
- recursive sub-issues/descendants;
- issues explicitly named by the manifest as implementation items.

External dependency issues may be inspected for readiness but are **not** authorized for implementation unless the root explicitly includes them or the user supplies them.

Do not absorb unrelated work merely because it shares a project, repo, label, milestone, or appears in a child's contextual links.

The root issue itself is coordination metadata unless it has independent implementation acceptance criteria.

## 2. Explicit issue set

The supplied canonical issue URLs are the implementation boundary. Read external dependencies for readiness only.

## 3. One or more project boards/projects

A project is a discovery surface, not the execution graph. Combine supplied boards/projects across FE/BE repos into one candidate DAG. Prefer an identifiable build-order/root issue as the bounded manifest before dispatch.

# Mandatory preflight validation

**Before dispatching any new implementation worker, invoke `validate-backlog` in `shallow` mode on the complete bounded scope.**

Do not hand-roll this check inside the orchestrator.

Pass the root manifest / explicit issue set and tracker context to `validate-backlog`.

The preflight must:

- read native parent/sub-issue relationships;
- read native `blocked by` / `blocking` relationships when available;
- scan descriptions/comments for dependency language;
- compare text dependencies with native metadata;
- detect cycles, missing targets, contradictory edges, duplicates, and scope leaks;
- return a normalized DAG using canonical full issue URLs.

Behavior by result:

- `PASS` => use the returned normalized DAG and continue.
- `PASS_WITH_WARNINGS` => continue only when warnings do not make ordering unsafe; surface material warnings.
- `FAIL` => do not dispatch affected work. Surface the validation errors and continue only independent safe branches if the validator explicitly identifies them.

The orchestrator does **not** automatically mutate dependency metadata. If the user wants GitHub description-based relationships converted into native links, use `normalize-github-dependencies` separately.

A user may explicitly request `validate-backlog deep` before orchestration. Deep validation is optional and is **not** the default preflight because it can consume substantial tokens/code-reading time.

# Default usage safeguards

Unless user overrides:

- maximum concurrent implementation workers: **4**;
- maximum newly started issues per orchestrator invocation: **12**;
- maximum implementation attempts per issue: **2 total**;
- maximum strongest-model escalation per issue: **1**;
- maximum CI repair cycles per PR: **2**;
- maximum review-fix cycles per PR: **2**;
- maximum lost-worker redispatches per issue: **1**;
- automatic merges: **disabled**.

When the 12-new-issue run budget is reached, allow active workers to reach durable state, stop starting more issues, reconcile, and return a checkpoint. A restarted session does not count already-started/adopted work as newly started again.

Budget exhaustion on a node => `NEEDS_USER`, not another speculative retry. Continue independent branches where safe.

# Models and worker skills

Use strongest available reasoning model for orchestration.

Normal implementation workers must explicitly use **Sonnet** when the worker API supports model selection. Do not accidentally inherit Opus from the parent.

Escalate one issue to strongest model only for reasoning-heavy repeated failure or clearly exceptional ambiguity.

Workers must inherit/preload installed skills, especially `implement-issue`, `create-pr`, and `resolve-pr-comment`. If a required skill is unavailable, return `BLOCKED` rather than improvising.

# Reconcile durable state and restart

After preflight and before dispatch, classify every in-scope issue from tracker + GitHub evidence:

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

Never create a duplicate PR for an issue that already has a valid active implementation PR.

## Restart / resume rule

On orchestration restart:

1. re-expand the exact same bounded scope;
2. rerun shallow `validate-backlog` to account for tracker changes since the previous session;
3. order issues according to validated DAG + explicit manifest build order;
4. query current tracker status and GitHub PR/branch state;
5. skip every proven `DONE` issue;
6. adopt existing open PRs/branches as durable active work;
7. identify the **earliest still-unfinished executable frontier** in build order;
8. resume new dispatch there.

"Latest unclosed ticket" means the first remaining unfinished point in the established sequence, not the numerically newest issue. Parallel/fanout groups can have multiple resume-frontier nodes.

# DAG / PR topology

Use validator output plus implementation reality to classify dependencies:

- **hard same-repo code dependency**: downstream needs unmerged upstream code;
- **execution dependency only**: order matters but code ancestry does not;
- **fanout**: multiple children depend on one parent but not each other;
- **cross-repo dependency**: scheduler/readiness edge only;
- **external prerequisite**: out of authorized scope, inspect only.

PR base relationships are authoritative for stacks:

```text
main -> A -> B -> C
```

means B's PR targets A's branch, C targets B's branch.

Fanout:

```text
main -> A
        ├-> B
        └-> C
```

B and C both target A; never linearize them merely due to completion order.

Multiple unmerged sibling dependencies with no valid common base => block rather than invent an integration merge.

Cross-repo dependencies never become Git stack ancestry.

# Worker dispatch and mandatory isolation

Every implementation worker owns one isolated checkout for the lifetime of its issue.

For local repos, create a dedicated Git worktree from the exact calculated base. If the Claude worker API supports native worktree isolation, use it. An environment-provided isolated clone is acceptable if exclusively owned by the worker.

Concurrent workers must never share a working tree/index or switch branches underneath one another. If isolation is unavailable, reduce that repository to one active worker.

Before dispatch:

1. calculate/fetch exact required base;
2. allocate issue branch + isolated worktree;
3. record canonical issue URL -> tracker -> repo -> worktree -> branch -> base -> worker;
4. increment newly-started count only for genuinely new work in this invocation;
5. dispatch Sonnet worker.

Worker prompt must include:

```text
Canonical issue URL: <FULL URL>
Tracker: <github|linear|...>
Repository: <OWNER/REPO>
Working directory: <DEDICATED WORKTREE>
Branch: <ISSUE BRANCH>
Required base: <BASE BRANCH>
Execution manifest: <ROOT FULL URL OR NONE>
Required skill: implement-issue
Budgets: implementation <N>, CI <N>, review <N>, escalation <N>
```

Worker must use `implement-issue` end-to-end and return canonical issue URL, tracker, PR URL, branch/base, linkage verification, checks, CI/review state, attempts consumed, and blocker/`NEEDS_USER` details.

# End-to-end worker lifecycle

`implement-issue` owns:

1. issue/comments/spec reading;
2. dependency/scope validation;
3. implementation;
4. local checks;
5. `create-pr` with full canonical issue URL and exact base;
6. tracker-specific PR linkage verification;
7. automated review trigger;
8. bounded CI repair;
9. bounded review-comment resolution;
10. durable result.

The orchestrator does not duplicate worker fixes. It tracks high-level state and budgets.

# Parent supervision / heartbeat

The main thread remains active while any worker is running or completion may unlock more work.

Each cycle:

1. consume worker status/completion messages;
2. classify running/complete/blocked/failed/lost;
3. reconcile tracker + GitHub branch/PR state;
4. verify canonical issue linkage on newly opened PRs;
5. inspect relevant CI/review summaries;
6. update budgets;
7. recompute READY frontier from validated DAG;
8. fill free slots while run budget permits;
9. surface new `NEEDS_USER` items promptly;
10. wait using native task/agent waiting when available, then repeat.

Do not use fake CPU/file-touch loops merely as keepalive. If no native wait exists, use bounded meaningful task/GitHub/tracker reconciliation.

The parent must not return final while workers remain active unless the task runtime itself has failed and safe continuation is impossible.

## Lost worker handling

Inspect worktree + GitHub first. Adopt durable branch/PR state if present. Preserve recoverable unpushed work if possible. Redispatch at most once. After that mark `NEEDS_USER`/infrastructure failure and continue independent paths.

# Outcome handling

## PR_OPEN

Verify PR exists, correct head/base, full canonical issue URL + tracker linking semantics, and expected commits.

## BLOCKED / BLOCKED_EXTERNAL

Stop that path. Never silently add an external prerequisite to implementation scope.

## FAILED

Retry only within budget. At most one reasoning escalation. Then `NEEDS_USER`.

## NEEDS_USER

Surface canonical issue URL, PR URL if any, failure, attempts, latest relevant error/review request, and recommended next action. Stop spending tokens on that node.

# Stack behavior

`create-pr` writes `Depends on: <full parent PR URL>` for direct stacked parents. The orchestrator may construct stacks/fanout but does not merge automatically. `merge-stack` owns authorized merge/restack operations.

After merge, reconcile tracker-specific completion:

- GitHub: verify implementation issue closed; if closing relationship was correct but unusual stack/base behavior prevented auto-close, explicitly close only after confirming the implementation PR merged.
- Linear: verify configured Linear workflow automation moved the issue to its expected terminal status; report mismatch rather than guessing workspace policy.

# Stop conditions

Stop starting new work when:

- all in-scope issues reached requested durable state;
- 12-new-issue run budget is reached;
- all remaining paths are blocked/`NEEDS_USER`;
- user asks to stop;
- safety approval is needed;
- infrastructure repeatedly fails.

# Progress and completion

Report canonical URLs for issues/PRs when ambiguity matters. A compact status may show short keys additionally.

Before returning, reconcile tracker + GitHub and report:

- manifest/scope;
- validation result/warnings;
- resume frontier;
- issues started vs run budget;
- PRs by repository/stack;
- issue-linkage or tracker-status inconsistencies;
- remaining CI/review work;
- `NEEDS_USER` items;
- external blockers;
- unstarted work and why;
- whether the same manifest can safely resume later.
