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
- `summarize-tranche` — writes a short plain-language summary of what a settled tranche actually did, plus the action points a human still has to manage: follow-up issues to open, verified bugs left unfixed, decisions waiting, scope deliberately cut. Read-only by default; it proposes issues rather than opening them. `backlog-orchestrator` invokes it per settled tranche, before ranking.
- `plan-merge-order` — ranks a settled tranche's open PRs by how much downstream work each unblocks, and emits a review order, a merge batching plan, and the hard sequencing constraints as a table. Read-only; it never merges. `backlog-orchestrator` invokes it when a run settles.
- `settle-outstanding-decisions` — walks the owner through the human-only decisions a settled run left outstanding, one at a time via `AskUserQuestion` with enough context to answer on the spot, and records each ruling durably where the decision lives. **You run this yourself after a tranche; nothing invokes it automatically**, and it refuses to prompt where nobody is present. Collect-and-record only; acting on the rulings stays with their owners.
- `merge-stack` — safely merges one PR, part of a stack, or an explicitly authorized whole stack while rebasing/restacking descendants.

## Writing skills

These read files from a personal machine (`~/Documents/version-control/ai-alex/...`) at load time, so their content is empty in a cloud container where those paths do not exist. They install everywhere regardless; use them from a local setup.

- `draft-blog-post` — draft a technical blog post using Alex's writing style and blog template from `ai-alex`.
- `draft-slack-message` — draft a Slack message using Alex's Slack examples and writing style from `ai-alex`.

## Repository layout

```
skills/           every directory with a SKILL.md ships
permissions.json
bootstrap.sh
```

Adding a skill requires no change to `bootstrap.sh` — create a directory under
`skills/` with a `SKILL.md` in it and the next bootstrap run installs it.

## Permissions

`permissions.json` is merged into `~/.claude/settings.json` by `bootstrap.sh`, so
a skill run does not stop on a prompt for a call the skill is expected to make.

### What this allowlist is, and is not

**It is a convenience layer. It is not a security boundary, and it cannot be made
into one.** Do not reason about it as though a hostile or prompt-injected agent
is contained by it — it isn't, by construction rather than by oversight.

Permission rules are **prefix matches**, so any rule ending in `*` admits
arbitrary trailing arguments. `git` and `gh` are both full of flags that name a
command to run or a file to read, and those flags simply ride along after
whatever prefix is granted. Five rounds of automated review found:

| rule | vector |
|---|---|
| `Bash(gh *)` | shell, via `gh alias set --shell` |
| `Bash(git rebase*)` | shell, via `-x` |
| `Bash(gh auth status*)` | prints the credential, via `--show-token` |
| `Bash(git fetch*)` / `Bash(git push*)` | local shell, via `--upload-pack=` / `--receive-pack=` against a `.` remote |
| `Bash(gh api*)` | reads a local file and publishes it, via `-F key=@<path>` |

Each was removed or replaced with a wildcard-free form. Those were cheap fixes
for capabilities nothing needed, and they should stay.

The fifth round is the one that settles the question. `Bash(git commit*)` and
`Bash(git push)` are each safe in isolation — the second takes no arguments at
all — yet compose into `git commit -F <secret>` followed by a push, which writes
an arbitrary local file into remote history. **No single rule is wrong there.**
Closing it means gating every commit or every push, and in an unattended fan-out
a worker stopped on a permission prompt is a deadlock, not a delay.

So: any rule set broad enough to let an agent commit and push unattended is
broad enough to exfiltrate a file. Narrowing relocates the hole; it does not
remove it. The controls that actually hold are elsewhere — container isolation,
credential scoping, egress policy, and what the token can reach.

Judge additions to this file by "does a skill need this to run without
prompting", not by "is this safe to grant an adversary".

### Two things that are easy to get wrong

- **The Claude Code Remote MCP server is registered under two different names
  depending on the surface.** A cloud/web session exposes its tools as
  `mcp__Claude_Code_Remote__<tool>`; the CLI registers the same server as
  `claude-code-remote`. Rule matching is on the literal tool name, so an entry
  under one spelling does not cover the other. Every Claude Code Remote tool is
  therefore listed under both.

  A wildcard cannot collapse them: an allow rule permits a glob only in the
  **tool** position, after a literal `mcp__<server>__` prefix, so
  `mcp__<server>__*` is valid and `mcp__*__delete_trigger` is not. The
  enumeration is the only option, and it is fragile by construction — a fourth
  registration would go unnoticed the same way the UUID one did. A prompt for a
  tool that looks allowlisted is the symptom; check the literal server segment
  in the pending tool name before assuming the entry is wrong.
- **Scheduled wakes have two implementations.** `backlog-orchestrator` arms a
  check-in when a run settles and disarms it once every PR is merged or closed
  (see Arming the wait when nothing is in flight). Depending on the session that
  is either the Claude Code Remote trigger tools (`create_trigger`,
  `list_triggers`, `delete_trigger`, `send_later`) or the built-in Routines tools
  (`CronCreate`, `CronList`, `CronDelete`), which are plain tool names with no
  `mcp__` prefix. Both sets are allowed.

- **Workers inherit this allowlist** wherever a dispatched session runs
  `bootstrap.sh`, which merges the same file into that session's settings. So
  granting the trigger tools fixes the deadlock — a worker that arms a wake can
  now disarm it — without touching the reason it armed one. The duplicate
  watcher remains, defended only by the dispatch-time countermand.

  That is the right trade, since a worker deadlocked mid-run is worse than a
  redundant watcher. But it changes what the evidence afterwards can prove: a
  clean session list is equally consistent with the countermand working and with
  workers arming wakes exactly as before and tidying up after themselves. Only
  the checkpoint output's `Worker sessions:` line and its blocked-worker
  reporting separate those two, so read them rather than the session list.

Nothing here grants merge authority: `merge_pull_request` is allowed because
`merge-stack` is an explicitly invoked skill, and `backlog-orchestrator`'s
no-automatic-merge invariant is a skill rule, not a permission boundary.

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
2. remote Claude Code worker sessions, when the session exposes `create_session` (agent-team primitives may substitute here where that experimental feature is enabled);
3. ordinary isolated subagents with an explicit parent supervision loop;
4. serialized execution when safe parallel isolation is unavailable.

The orchestrator picks a tier itself from the tools actually callable in the session, probes a failing tier at most twice before degrading, and never asks the user to choose one. None of these replace the orchestrator's validated issue DAG, scope boundary, model policy, worktree isolation, repair budgets, stack topology, or tracker/GitHub recovery semantics.

## Autonomy after dispatch

`backlog-orchestrator` is meant to run unattended once the validation preflight clears. Anything it has a documented default for — runtime tier, concurrency, the budget cap when scope exceeds it, and a session branch mandate that conflicts with per-issue branches — is resolved by applying the default and reporting it in the checkpoint output. Only a platform-owned approval prompt, `NEEDS_USER` after exhausted budgets, a `FAIL` validation with no safe path, or an undocumented conflict that would lose unrecoverable work may interrupt the run.

Invoking the skill is itself the authorization to dispatch workers, so a session whose standing guidance is "no subagents unless asked" needs no extra confirmation for the fan-out.

## Recovery model

Local/cloud worktrees are isolation, not durable storage. `implement-issue-core` pushes the issue branch early and pushes coherent implementation checkpoints — but the orchestrator treats that as best-effort rather than done. Workers reliably hold completed work uncommitted even when told not to, so the parent inspects every in-flight worktree each supervision cycle and, where a nudge has already failed, commits the work itself. Enforcement lives in the loop, not in the dispatch prompt. If a cloud container or a Dynamic Workflow's session disappears, backlog orchestration resumes from tracker + remote branch/PR state rather than relying on the lost worktree or runtime state — a Dynamic Workflow does not persist across a session exit, so this recovery path is required, not just a fallback.

## PR supervision

Implementation workers return after durable PR creation. When Claude Code's own background PR watch/notification behavior (a session-level feature, separate from Dynamic Workflows) surfaces worker-created PRs to the parent session, the orchestrator consumes that PR/CI/review state directly. The **platform may observe the event; the orchestrator remains the policy owner** deciding whether repair budgets allow another Sonnet `repair-pr` worker. If that background behavior has auto-merge enabled, disable it or treat any resulting merge as outside the orchestrator's control — it conflicts with the no-automatic-merge invariant.

When first-class PR events are unavailable, the parent falls back to other subscriptions or bounded polling. It does not keep one idle Sonnet agent alive per PR.

`implement-issue` keeps the same behavior on a single ticket: it remains a useful one-issue orchestrator that composes the same primitives and supervises just that PR.

A **mechanical** push — a restack, or a renumber/regeneration of a claimed artifact such as a migration number or a lockfile — moves identity or ordering rather than behavior. It consumes no review cycle, re-triggers no review, and does not reset a PR's reviewed state; the repository's deterministic checks validate it instead. This matters right after a sibling merges, when descendants restack for reasons unrelated to their own diffs. Where no such check exists, the push is substantive like any other.

A PR opened as a draft is promoted to ready for review once its first automated review round has completed and every finding from it is resolved, CI is green, and nothing is waiting on the user. The supervisor owns that decision — `repair-pr` reports how many actionable threads remain but never changes draft state itself. Promotion is a review-readiness signal only; it never implies merge authority.

## Settled tranches

A run is **settled** when no further implementation can start — every unstarted issue is blocked by implemented-but-unmerged work — and every open PR has had a completed automated review with all findings resolved. The run has produced everything it can; the next move belongs to whoever holds merge authority.

At that point `backlog-orchestrator` invokes `summarize-tranche` — a short account of what the tranche did plus the action points needing a human, run per tranche because its findings come from run context the next session will not have, and because a follow-up discovered mid-run needs to exist while later tranches can still pick it up.

Then it invokes `plan-merge-order`, which ranks the open PRs by downstream leverage and returns the review order, merge batches, and forced orderings. Stack ancestry is one input to that ranking, not the whole of it: the highest-leverage PR is often not a stack base, and a PR can unblock nothing on its own while still gating a large subtree behind it.

## Cloud bootstrap

Run `bootstrap.sh` from a checkout of this repository to install the skills into the standard Claude configuration for a cloud/container session. It discovers every directory under `skills/` that contains a `SKILL.md`, so the install list never drifts from the repository. The orchestration skills remain environment-agnostic and can also be used from local Claude Code setups.
