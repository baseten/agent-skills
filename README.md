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
- `backlog-orchestrator` — validates a bounded build-order/parent issue or issue set, fans out isolated Sonnet implementation workers via `implement-issue-core`, centrally owns all long-lived PR CI/review supervision, dispatches short-lived `repair-pr` workers, enforces budgets, and recovers from tracker + remote Git state.
- `merge-stack` — safely merges one PR, part of a stack, or an explicitly authorized whole stack while rebasing/restacking descendants.

## Recovery model

Local/cloud worktrees are isolation, not durable storage. `implement-issue-core` pushes the issue branch early and pushes coherent implementation checkpoints. If a cloud container disappears, backlog orchestration resumes from the latest remote branch/PR state rather than relying on the lost worktree.

## Cloud bootstrap

Run `bootstrap.sh` from a checkout of this repository to install all skills into the standard Claude configuration for a cloud/container session. The orchestration skills remain environment-agnostic and can also be used from local Claude Code setups.
