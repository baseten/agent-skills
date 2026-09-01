# Agent Skills

Reusable Claude Code skills for issue implementation, PR workflows, backlog validation/orchestration, and stacked PR management.

## A note on how the skills read

The `SKILL.md` files are dense and not easily human readable. That is deliberate, and it was tested rather than assumed: [issue #51](https://github.com/baseten/agent-skills/issues/51) benchmarked a plain-English rewrite of the densest section against the current text — all 21 eval scenarios, on Sonnet and on Haiku — and the plain version made the models no better (identical on Sonnet, worse-to-indistinguishable on Haiku). The density costs the models nothing; they interpret this register at least as well as plain prose, so the skills are written for their actual reader. Humans get their own entry points instead: each skill's `NOTES.md` explains the reasoning behind its rules, and `backlog-orchestrator/README.md` gives a plain-language overview and a glossary of the coined terms.

## Core workflow skills

- `implement-issue-core` — implements exactly one tracked issue to a durable remote PR state, including remote branch/checkpoint pushes for restart recovery. It does not own long-lived CI/review monitoring.
- `repair-pr` — performs one bounded repair pass on an existing PR — a CI failure, a review round, or a settle-time finding (an `IN_FLIGHT_FIX` action point or a code-changing walkthrough ruling) — and pushes the repair.
- `implement-issue` — convenient standalone single-issue orchestrator. It composes `implement-issue-core`, supervises that one PR's CI/review lifecycle, and invokes `repair-pr` for bounded fixes.
- `create-pr` — creates correctly linked PRs, preserves explicit stack bases, adds `Depends on:` for direct stack parents, verifies tracker linkage, and triggers repository review automation unless explicitly deferred.
- `resolve-pr-comment` — addresses one PR review thread using the repository's review workflow.

## Backlog / orchestration skills

- `validate-backlog` — validates a bounded issue DAG. Shallow mode checks tracker hierarchy/structured dependencies/text consistency; deep mode inspects implementation/spec reality for missing or incorrect dependencies.
- `normalize-github-dependencies` — converts high-confidence description-based GitHub dependencies into native blocked-by/blocking relationships where GitHub write capabilities are available.
- `backlog-orchestrator` — policy layer for a bounded build-order/parent issue or issue set. It validates the DAG, fans out isolated Sonnet workers via `implement-issue-core` (onto a Claude Code **Dynamic Workflow** when the user explicitly opts into one for this invocation, otherwise onto native/background sessions or ordinary supervised subagents), consumes platform-surfaced PR events on its own parent-level supervision loop, dispatches bounded `repair-pr` workers, and enforces stack/budget/recovery rules.
- `summarize-tranche` — writes a short plain-language summary of what a settled tranche actually did, plus the action points a human still has to manage: follow-up issues to open, verified bugs left unfixed, decisions waiting, scope deliberately cut. Read-only by default; it proposes issues rather than opening them. `backlog-orchestrator` invokes it per settled tranche, before ranking; `implement-issue` invokes it when its one issue reaches a terminal state, a tranche of one.
- `plan-merge-order` — ranks a settled tranche's open PRs by how much downstream work each unblocks, and emits a review order, a merge batching plan, and the hard sequencing constraints as a table. Read-only; it never merges. `backlog-orchestrator` invokes it when a run settles.
- `settle-outstanding-decisions` — walks the owner through the human-only decisions a settled run left outstanding, one at a time via `AskUserQuestion` with enough context to answer on the spot, and records each ruling durably where the decision lives. Run it yourself after a tranche, or let a settled step request it — `backlog-orchestrator` between summary and ranking, `implement-issue` between summary and merge gate — on by default, gated by `auto-request-settle`. Either way it refuses to prompt where nobody is present: a run settling on a scheduled wake gets a one-line decline, and the decisions stay in the summary's action points. Collect-and-record only; acting on the rulings stays with their owners.
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
scripts/          repo-level checks (run in CI, runnable locally)
.github/workflows/
```

Adding a skill requires no change to `bootstrap.sh` — create a directory under
`skills/` with a `SKILL.md` in it and the next bootstrap run installs it.

## Checks

`.github/workflows/checks.yml` runs on every pull request. Everything in it is
deterministic — no model calls, no API key, no cost — and every check is
runnable locally:

```bash
python3 scripts/check_skills.py                       # structure, schema, cross-references
bash skills/backlog-orchestrator/scripts/test-checkpoint-capture.sh
shellcheck --severity=warning bootstrap.sh skills/*/scripts/*.sh
bash scripts/eval_reminder.sh origin/main             # advisory, never fails
```

`check_skills.py` catches what is decidable from the text: frontmatter that
disagrees with its directory, an `evals.json` that no longer parses or has
duplicate ids, and — the one worth having in a document this cross-referenced —
a `(see Some Section)` or `` `other-skill`, *Some Section* `` pointer that
resolves to no heading. A section can be cited by the first clause of a longer
heading; anything else is an error, including a cross-reference naming a skill
that does not exist.

Contract and NOTES heading sets are kept separate, which matters more than it
sounds: `NOTES.md` is keyed by the section names of `SKILL.md` by design —
`backlog-orchestrator` shares 20 of its 21 — so a merged set would give almost
every contract section a shadow heading, and renaming one in `SKILL.md` alone
would leave its references resolving happily against `NOTES.md`. References
inside `NOTES.md` resolve against both, since a note legitimately cites a
contract section or one of its own.

`eval_reminder.sh` names a skill whose `SKILL.md`/`NOTES.md` changed while its
`evals/evals.json` did not. It is a warning and never a failure: it cannot know
whether a change needs a scenario, only that nobody added one.

**The eval scenarios themselves are deliberately not in CI.** They are
model-graded, cost money per run, and are non-deterministic, so a required
check built on them goes red on sampling noise and teaches everyone to override
it. Run them on demand instead, per `skill-creator`, comparing against the
previous text rather than against a fixed threshold.

## Permissions

`permissions.json` is merged into `~/.claude/settings.json` by `bootstrap.sh`, so
a skill run does not stop on a prompt for a call the skill is expected to make.

**The file holds tool-name rules only — no `Bash(...)` entries.** That is the
whole design now, and it follows from how auto mode treats each kind of rule.

### Why the tool-name entries are load-bearing under auto mode

Cloud containers and most Pro/Max/Team sessions start in **auto mode**, where a
classifier reviews actions instead of the user. Auto mode already permits the
ordinary work these skills do — local file operations, dependency installs,
`git` and `gh` against the session's own repository, pushing to any branch of it,
opening a PR that matches the request — so shell allow rules for that work buy
nothing but a saved classifier round-trip.

The tool-name entries are different, because several tools **decline to approve
themselves in auto mode**. Their own permission hook returns `passthrough` with
a message such as *"Scheduling a cron prompt requires classifier review"*, and
the permission pipeline converts an unresolved `passthrough` into **`ask`**. In
an unattended fan-out an `ask` is a deadlock, not a delay.

A matched whole-tool allow rule is evaluated **before** that conversion, so the
rule is what keeps the tool from asking. The only tools that ignore a whole-tool
allow rule declare `ignoresWholeToolAllowRule`, and none of the tools listed here
do. So every entry in this file is doing real work, and removing one reintroduces
a stop.

Two entries were removed for the opposite reason — auto mode drops them, so they
never did anything there:

| Removed | Why |
| --- | --- |
| `Agent` | Auto mode drops `Agent` allow rules on entry |
| All `Bash(...)` entries | Wildcarded interpreters and package-manager run commands are dropped; the rest duplicate what auto mode already allows |

Dropping the shell rules also retires the injection surface documented below:
a tool-name rule admits no trailing arguments, so there is nothing for a flag to
ride in on.

### Where to install it

1. **Per container — the working default.** `bootstrap.sh` writes
   `~/.claude/settings.json`. Claude Code watches its settings files and reloads
   `permissions` edits into a running session, so a bootstrap that finishes after
   the session starts still applies. `~/.claude` is per-container and disappears
   with it.
2. **Org-wide — the durable option.** An Owner or Primary Owner can paste the
   same `permissions.allow` into **Managed settings** at
   [claude.ai/admin-settings/claude-code](https://claude.ai/admin-settings/claude-code).
   Server-managed settings are the *only* managed channel that reaches cloud
   sessions — an MDM profile or a device `managed-settings.json` does not — and
   they sit at the highest precedence tier. This needs no per-repo file and no
   bootstrap write.
3. **Per repository — usually unnecessary.** Committing these entries to a
   repo's `.claude/settings.json` works, but it puts agent configuration in a
   shared repo for no gain over (1) or (2). Permission allow/deny lists **merge**
   across every scope rather than overriding, so a repo copy adds nothing that
   the union does not already contain.

### Verifying the rules are live in a container

`/permissions` does not exist in a cloud session, which is the one place this
question matters. Use a behavioural probe instead: call **`CronCreate`** with a
harmless one-shot job, then `CronDelete` it.

```
CronCreate  cron: "43 3 24 12 *"  prompt: "probe"  recurring: false
CronDelete  id: <returned id>
```

`CronCreate` is the right probe because it refuses to approve itself under auto
mode — its own hook returns `passthrough`, which the pipeline converts to `ask`.
So if the job is scheduled with no prompt, a whole-tool allow rule matched, and
the only file in a bootstrapped container that supplies one is
`~/.claude/settings.json`. If instead a permission prompt appears, the rules are
not reaching the session.

Confirmed working this way on Claude Code v2.1.252 in a cloud container: the
session's diagnostics log (`$CLAUDE_CODE_DIAGNOSTICS_FILE`) reports
`settings_load_completed` with `source_count: 4, error_count: 0`, and the probe
schedules without prompting.

**The documentation is easy to misread here.** *Settings in cloud sessions* lists
user settings (`~/.claude/settings.json`) as "not read". That is about *your
machine's* copy not being uploaded — the same table says the same of
`~/.claude/skills/`, which bootstrap populates and which demonstrably loads. A
file written inside the container is a live scope.

### Do we still need the deny list?

Yes, and it is the one part of this file not to cut. Auto mode's classifier
already blocks most of what it names — force push, `git reset --hard`,
`git clean -fd`, amending a pushed commit — but it blocks them *in auto mode*.
A `deny` rule binds in **every** mode, which is what makes it worth keeping for
local runs in Manual or `acceptEdits`, where no classifier reviews anything.

The entries also cover force bundled into a short-option group — `git push -uf`,
`-uqf`, `-nf` — which the whitespace-delimited `-f` forms miss entirely. They are
anchored so they cannot swallow `--force-with-lease`, an ordinary `-u` push, or a
branch name containing `f`, all verified against `fnmatch` before shipping.
**One residual is known and left uncovered on purpose:** options written *after*
the refspec (`git push origin -uf`) are not matched, because the pattern that
would catch them also denies a legitimate push to a branch ending in `-f`. That
is the prefix-match arms race this section is about; auto mode's classifier is
the control that actually covers it.

The entries are also anchored as substrings rather than prefixes, which closes
gaps a prefix-anchored form leaves open — `git push origin master --force`,
`git push origin master -f` and `git push origin +HEAD:master` all evade a rule
anchored at `git push --force`. Each is spaced so it cannot swallow
`--force-with-lease`, which the stacked-PR restack needs.

Two things deliberately **not** denied:

| Not denied | Why |
| --- | --- |
| `git push --delete` / `git push origin :branch` | Branch deletion is something these skills legitimately do; it was an `allow` entry here before. It now reaches the classifier, which is the right treatment |
| `git commit --amend` | Auto mode's handling is more precise than a blanket deny: it permits a message-only reword of a commit created in this session and blocks amending anything pushed |

One admin key to know about: `allowManagedPermissionRulesOnly: true` makes
Claude Code ignore every non-managed permission rule, including everything
`bootstrap.sh` installs. If an organization sets it, route (2) is the only one
that works, and route (1) fails silently.

### `permissions.json` is a managed set

`bootstrap.sh` records what it installed in `~/.claude/.agent-skills-permissions.json`
and subtracts that record on the next run before adding the current file. So:

| Entry | On the next bootstrap |
| --- | --- |
| Still shipped here | kept |
| **Retired from here** | **removed** |
| You added it to `settings.json` by hand | kept |

This matters because the merge used to be a plain `(existing + new | unique)`
union, which can only ever grow. A container that had once installed a wrong
entry kept it forever, and re-running bootstrap could not correct it — a wrong
entry is invisible, since a rule that matches nothing looks exactly like one
that works until an agent stops on it. Two such entries shipped from here for
months: `Bash(git push)` as an exact match, which covers neither
`git push -u origin <branch>` nor `git push --force-with-lease origin <branch>`,
and the Linear names `create_comment` / `update_issue`, which do not exist —
the real ones are `save_comment` / `save_issue`.

**Containers bootstrapped before the sidecar existed cannot be corrected in
place.** With no install record, every entry already in `settings.json` is
indistinguishable from a deliberate hand edit, so bootstrap keeps all of them
and prints a note saying so. To get a clean copy:

```bash
rm ~/.claude/settings.json && bash bootstrap.sh
```

Anything you had added by hand goes with it, so check the file first if that
matters.

### What this allowlist is, and is not

**It is a convenience layer. It is not a security boundary, and it cannot be made
into one.** Do not reason about it as though a hostile or prompt-injected agent
is contained by it — it isn't, by construction rather than by oversight.

This file no longer carries `Bash(...)` rules, which removes the sharpest edge
of that statement — the history below is kept because it is the reason the rules
went, and because anyone tempted to add one back needs it.

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

Each was removed or replaced with a wildcard-free form, and the whole class is
now gone from this file.

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

Auto mode is now the layer doing that work for shell commands, which is why the
`Bash(...)` rules could go rather than be narrowed a sixth time. It is not a
boundary either, but it is a reviewer, and a reviewer beats a prefix match.

Judge additions to this file by "does a skill need this to run without
prompting, and does auto mode not already allow it", not by "is this safe to
grant an adversary". A `Bash(...)` entry should now be an argued exception with a
named tool that stopped, not a default.

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
`merge-stack` is an explicitly invoked skill, and `backlog-orchestrator` and
`implement-issue` merge only through the invariant 12 gate — off by default,
opt-in per repository via `.claude/backlog-orchestrator.json` — which is a skill
rule, not a permission boundary.

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

## Per-repository policy

A repository can tune `backlog-orchestrator` for its own PRs with `.claude/backlog-orchestrator.json` — the same defaults the skill documents (concurrency, budgets, repair cycles, `auto-request-settle`) plus one permission: `auto-merge`, whether the invariant 12 merge gate may open at all (a gate-authorized merge publishes a still-draft PR as a step of merging it — a merge never happens on a draft — and never touches an explicitly held draft). The file is entirely optional and absence is the common case.

**There is no reviewer-identity option, and a repository needs no file to get safe review behaviour.** What the run may auto-fix is decided by the comment, not its author: a thread asking for a code change the pass can make and verify is repaired, whoever rooted it; a thread needing intent, design, rationale or a decision is `NEEDS_USER` — reserved for the owner, never answered on the run's own authority, and holding the merge gate shut. **An escalated thread comes back with a draft reply**, because the pass that read the thread and the surrounding code should not hand the owner a blank page: a question answerable from the work gets the answer and its evidence, a question only the owner can decide gets the options and their costs and deliberately no pick, and assumptions are marked inline. The draft is material for a person and is never posted on any path; `settle-outstanding-decisions` carries it into the walkthrough so an intent question can be answered on the spot. An `auto-fix-reviewers` key used to gate this on the author, tested against a vetted bot allowlist. It was removed rather than re-defaulted, because author identity is a poor proxy for the only thing that matters: automated reviewers raise design questions no run should answer, and human reviewers file one-line nits any run can fix, so the key erred in both directions at once. The kind test the repair path already applied was doing the real work.

Policy resolves **per PR, from the repository that PR lives in**, so a run spanning a personal and a work repository applies each repo's own rules within the same tranche. The file is owner-authored configuration: it is read at preflight from the repository state the run started from, never from anything a worker wrote mid-run, and a malformed file fails closed, reported rather than guessed at. An invocation argument overrides any key except `auto-merge`, which it can switch off but never on — the repository's opt-in is the only route to a merge. That one grant covers every consumer of the key, `implement-issue` included, so a file committed before a consumer could merge authorizes it once the skills are reinstalled: the permission is scoped to the invariant 12 gate rather than to the skill evaluating it, every consumer defers to that gate for all of its conditions, and splitting the key per consumer would gate which skill opened the PR rather than any difference in risk. `auto-merge: false` is how an owner declines autonomous merging outright. The resolved policy is reported per PR in the checkpoint output.

`implement-issue` runs the same settle sequence over its single PR — summary, then the decision walkthrough while `auto-request-settle` is on, then the merge gate, with `plan-merge-order` deliberately skipped because one PR has no ordering to rank — and reads the same file for the one PR it supervises — the budgets and `auto-merge`, on the semantics `backlog-orchestrator` defines and does not duplicate — so a repository's policy governs a single-issue run as much as a tranche. Its run-level keys have no single-issue meaning and are ignored. A caller that already resolved policy passes it down and suppresses the child's own read, so the parent's preflight read stays the run's policy rather than being re-derived later against a file that may have moved. The file keeps its `backlog-orchestrator` name now that two skills read it.

## Recovery model

Local/cloud worktrees are isolation, not durable storage. `implement-issue-core` pushes the issue branch early and pushes coherent implementation checkpoints — but the orchestrator treats that as best-effort rather than done. Workers reliably hold completed work uncommitted even when told not to, so the parent inspects every in-flight worktree each supervision cycle and, where a nudge has already failed, commits the work itself. Enforcement lives in the loop, not in the dispatch prompt. If a cloud container or a Dynamic Workflow's session disappears, backlog orchestration resumes from tracker + remote branch/PR state rather than relying on the lost worktree or runtime state — a Dynamic Workflow does not persist across a session exit, so this recovery path is required, not just a fallback.

## PR supervision

Implementation workers return after durable PR creation. When Claude Code's own background PR watch/notification behavior (a session-level feature, separate from Dynamic Workflows) surfaces worker-created PRs to the parent session, the orchestrator consumes that PR/CI/review state directly. The **platform may observe the event; the orchestrator remains the policy owner** deciding whether repair budgets allow another `repair-pr` worker, and on which model. If that background behavior has auto-merge enabled, disable it or treat any resulting merge as outside the orchestrator's control — it merges outside the invariant 12 gate.

When first-class PR events are unavailable, the parent falls back to other subscriptions or bounded polling. It does not keep one idle Sonnet agent alive per PR.

`implement-issue` keeps the same behavior on a single ticket: it remains a useful one-issue orchestrator that composes the same primitives and supervises just that PR, under the same per-repository policy.

A **mechanical** push — a restack, or a renumber/regeneration of a claimed artifact such as a migration number or a lockfile — moves identity or ordering rather than behavior. It consumes no review cycle, re-triggers no review, and does not reset a PR's reviewed state; the repository's deterministic checks validate it instead. This matters right after a sibling merges, when descendants restack for reasons unrelated to their own diffs. Where no such check exists, the push is substantive like any other.

The orchestrator does not promote drafts: marking a PR ready is how you ask a person to review — a social act, never an autonomous decision. A draft is published in exactly two ways: the owner does it themselves, or the invariant 12 merge path publishes it as a step of merging it. A draft held by an explicit instruction, a repository convention, or a caller's draft preference is excluded from the gate entirely — neither published nor merged, reported as held. `repair-pr` reports how many actionable threads remain but never changes draft state, and `implement-issue` applies the same contract to the one PR it supervises: it never promotes, so its PR stays a draft until the owner publishes it or the gate merges it.

## Settled tranches

A run is **settled** when no further implementation can start — every unstarted issue is blocked by implemented-but-unmerged work — and every open PR has had a completed automated review with all findings resolved. The run has produced everything it can; the next move belongs to whoever holds merge authority.

At that point `backlog-orchestrator` invokes `summarize-tranche` — a short account of what the tranche did plus the action points needing a human, run per tranche because its findings come from run context the next session will not have, and because a follow-up discovered mid-run needs to exist while later tranches can still pick it up.

Between the summary and the ranking — when `auto-request-settle` is on, the default — it requests `settle-outstanding-decisions` over the summary's decision items, seeded from the summary so the two skills cannot disagree about what is outstanding. The walkthrough asks only where someone is present; unattended it declines in one line and the decisions stay in the summary's action points. It runs before the ranking because a ruling can change what should merge.

Then it invokes `plan-merge-order`, which ranks the open PRs by downstream leverage and returns the review order, merge batches, and forced orderings. Stack ancestry is one input to that ranking, not the whole of it: the highest-leverage PR is often not a stack base, and a PR can unblock nothing on its own while still gating a large subtree behind it.

Where a repository opted into auto-merge, the invariant 12 gate is evaluated only after the summary, walkthrough, and ranking — its decision/merge-risk inputs do not exist earlier — and any merge it performs is reported with the gate evidence. A summary `IN_FLIGHT_FIX`, or a walkthrough ruling that requires code to change, un-settles the run instead: it dispatches one `repair-pr` pass with `repair type = finding`, bounded by its own `finding-repair-cycles` budget, then settles again from a fresh summary. And a PR whose dependency view was never proven complete — a run whose transport cannot read the dependency graph, accepted for dispatch — holds the gate for that PR: proceedable is not mergeable, and its merge stays the owner's.

## Cloud bootstrap

Run `bootstrap.sh` from a checkout of this repository to install the skills into the standard Claude configuration for a cloud/container session. It discovers every directory under `skills/` that contains a `SKILL.md`, so the install list never drifts from the repository. The orchestration skills remain environment-agnostic and can also be used from local Claude Code setups.
