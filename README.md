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
- `backlog-orchestrator` — policy layer for a bounded build-order/parent issue or issue set. It validates the DAG, fans out isolated Sonnet workers via `implement-issue-core` (onto a Claude Code **Dynamic Workflow** when the user explicitly opts into one for this invocation, otherwise onto native/background sessions or ordinary supervised subagents), consumes platform-surfaced PR events on its own parent-level supervision loop, dispatches bounded `repair-pr` workers, and enforces stack/budget/recovery rules.
- `plan-merge-order` — ranks a settled tranche's open PRs by how much downstream work each unblocks, and emits a review order, a merge batching plan, and the hard sequencing constraints as a table. Read-only; it never merges. `backlog-orchestrator` invokes it when a run settles.
- `merge-stack` — safely merges one PR, part of a stack, or an explicitly authorized whole stack while rebasing/restacking descendants.

## Writing skills (`skills-local/`)

These read files from a personal machine (`~/Documents/version-control/ai-alex/...`) at load time, so they cannot work in a cloud container. They live under `skills-local/` and `bootstrap.sh` skips them unless `--include-local` is passed.

- `draft-blog-post` — draft a technical blog post using Alex's writing style and blog template from `ai-alex`.
- `draft-slack-message` — draft a Slack message using Alex's Slack examples and writing style from `ai-alex`.

## Repository layout

```
skills/         installed everywhere; every directory with a SKILL.md ships
skills-local/   needs a personal machine; installed only with --include-local
permissions.json
bootstrap.sh
```

Adding a skill requires no change to `bootstrap.sh` — create a directory under
`skills/` with a `SKILL.md` in it and the next bootstrap run installs it.

## Local Codex usage

Codex reads a subset of the skills via symlinks in `~/.codex/skills/`:

```bash
for s in create-pr resolve-pr-comment implement-issue draft-blog-post draft-slack-message; do
  ln -sfn "$HOME/.claude-personal/skills/$s" "$HOME/.codex/skills/$s"
done
```

## Runtime model

`backlog-orchestrator` separates **policy** from **execution runtime**.

A Claude Code Dynamic Workflow is only used for the bounded implementation fan-out, and only when the invoking user's own prompt opts into one (e.g. "use a workflow to run backlog-orchestrator on ...") or the session already has `/effort ultracode` on — the skill has no way to switch one on itself. When used, the workflow gives the fan-out persistent multi-agent scheduling and worker lifecycle up front, but it does not persist across a session exit and cannot receive events mid-run, so it is never used for PR supervision (see below).

Preferred runtime order for the implementation fan-out:

1. Claude Code Dynamic Workflows, when the user opted in for this invocation;
2. native/background Claude sessions or agent-team primitives (agent teams are experimental/opt-in);
3. ordinary isolated subagents with an explicit parent supervision loop;
4. serialized execution when safe parallel isolation is unavailable.

None of these replace the orchestrator's validated issue DAG, scope boundary, model policy, worktree isolation, repair budgets, stack topology, or tracker/GitHub recovery semantics.

## Recovery model

Local/cloud worktrees are isolation, not durable storage. `implement-issue-core` pushes the issue branch early and pushes coherent implementation checkpoints. If a cloud container or a Dynamic Workflow's session disappears, backlog orchestration resumes from tracker + remote branch/PR state rather than relying on the lost worktree or runtime state — a Dynamic Workflow does not persist across a session exit, so this recovery path is required, not just a fallback.

## PR supervision

Implementation workers return after durable PR creation. When Claude Code's own background PR watch/notification behavior (a session-level feature, separate from Dynamic Workflows) surfaces worker-created PRs to the parent session, the orchestrator consumes that PR/CI/review state directly. The **platform may observe the event; the orchestrator remains the policy owner** deciding whether repair budgets allow another Sonnet `repair-pr` worker. If that background behavior has auto-merge enabled, disable it or treat any resulting merge as outside the orchestrator's control — it conflicts with the no-automatic-merge invariant.

When first-class PR events are unavailable, the parent falls back to other subscriptions or bounded polling. It does not keep one idle Sonnet agent alive per PR.

`implement-issue` keeps the same behavior on a single ticket: it remains a useful one-issue orchestrator that composes the same primitives and supervises just that PR.

A **mechanical** push — a restack, or a renumber/regeneration of a claimed artifact such as a migration number or a lockfile — moves identity or ordering rather than behavior. It consumes no review cycle, re-triggers no review, and does not reset a PR's reviewed state; the repository's deterministic checks validate it instead. This matters right after a sibling merges, when descendants restack for reasons unrelated to their own diffs. Where no such check exists, the push is substantive like any other.

A PR opened as a draft is promoted to ready for review once its first automated review round has completed and every finding from it is resolved, CI is green, and nothing is waiting on the user. The supervisor owns that decision — `repair-pr` reports how many actionable threads remain but never changes draft state itself. Promotion is a review-readiness signal only; it never implies merge authority.

## Settled tranches

A run is **settled** when no further implementation can start — every unstarted issue is blocked by implemented-but-unmerged work — and every open PR has had a completed automated review with all findings resolved. The run has produced everything it can; the next move belongs to whoever holds merge authority.

At that point `backlog-orchestrator` invokes `plan-merge-order`, which ranks the open PRs by downstream leverage and returns the review order, merge batches, and forced orderings. Stack ancestry is one input to that ranking, not the whole of it: the highest-leverage PR is often not a stack base, and a PR can unblock nothing on its own while still gating a large subtree behind it.

## Cloud bootstrap

Run `bootstrap.sh` from a checkout of this repository to install the skills into the standard Claude configuration for a cloud/container session. It discovers every directory under `skills/` that contains a `SKILL.md`, so the install list never drifts from the repository. Pass `--include-local` to add `skills-local/` as well, on a machine where those skills' source files exist. The orchestration skills remain environment-agnostic and can also be used from local Claude Code setups.
