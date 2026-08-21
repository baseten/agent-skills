# Agent Skills

Reusable Claude Code skills for issue implementation, PR workflows, backlog validation/orchestration, and stacked PR management.

## Core workflow skills

- `implement-issue-core` — implements exactly one tracked issue to a durable remote PR state, including remote branch/checkpoint pushes for restart recovery. It does not own long-lived CI/review monitoring.
- `repair-pr` — performs one bounded CI or review repair pass on an existing PR and pushes the repair.
- `implement-issue` — convenient standalone single-issue orchestrator. It composes `implement-issue-core`, supervises that one PR's CI/review lifecycle, and invokes `repair-pr` for bounded fixes.
- `create-pr` — creates correctly linked PRs, preserves explicit stack bases, adds `Depends on:` for direct stack parents, verifies tracker linkage, and triggers repository review automation unless explicitly deferred.
- `resolve-pr-comment` — addresses one PR review thread using the repository's review workflow.

## Backlog / orchestration skills

- `validate-backlog` — validates a bounded issue DAG. Shallow mode checks tracker hierarchy/structured dependencies/text consistency; deep mode inspects implementation/spec reality for missing or incorrect dependencies.
- `normalize-github-dependencies` — converts high-confidence description-based GitHub dependencies into native blocked-by/blocking relationships where GitHub write capabilities are available.
- `backlog-orchestrator` — policy layer for a bounded build-order/parent issue or issue set. It validates the DAG, prefers Claude Code **Dynamic Workflows** as the execution runtime when available, fans out isolated Sonnet workers via `implement-issue-core`, consumes first-class/promoted PR events, dispatches bounded `repair-pr` workers, enforces stack/budget/recovery rules, and falls back to native/background sessions or ordinary supervised subagents when Dynamic Workflows are unavailable.
- `merge-stack` — safely merges one PR, part of a stack, or an explicitly authorized whole stack while rebasing/restacking descendants.

## Runtime model

`backlog-orchestrator` separates **policy** from **execution runtime**.

Preferred runtime order:

1. Claude Code Dynamic Workflows;
2. native/background Claude sessions or agent/task primitives;
3. ordinary isolated subagents with an explicit parent supervision loop;
4. serialized execution when safe parallel isolation is unavailable.

Dynamic Workflows may provide persistent multi-agent scheduling, worker lifecycle, first-class PR promotion, and native CI/review event surfacing. They do not replace the orchestrator's validated issue DAG, scope boundary, model policy, worktree isolation, repair budgets, stack topology, or tracker/GitHub recovery semantics.

## Recovery model

Local/cloud worktrees are isolation, not durable storage. `implement-issue-core` pushes the issue branch early and pushes coherent implementation checkpoints. If a cloud container or workflow disappears, backlog orchestration resumes from tracker + remote branch/PR state rather than relying on the lost worktree or runtime state.

A Dynamic Workflow's own persistence is useful but is not required for correctness.

## PR supervision

Implementation workers return after durable PR creation. When Claude Desktop/Dynamic Workflows promote worker-created PRs to the parent session, the orchestrator consumes that first-class PR/CI/review state directly. The **platform may observe the event; the orchestrator remains the policy owner** deciding whether repair budgets allow another Sonnet `repair-pr` worker.

When first-class PR events are unavailable, the parent falls back to other subscriptions or bounded polling. It does not keep one idle Sonnet agent alive per PR.

`implement-issue` keeps the same behavior on a single ticket: it remains a useful one-issue orchestrator that composes the same primitives and supervises just that PR.

## Cloud bootstrap

Run `bootstrap.sh` from a checkout of this repository to install all skills into the standard Claude configuration for a cloud/container session. The orchestration skills remain environment-agnostic and can also be used from local Claude Code setups.
