---
name: create-pr
description: Create a GitHub pull request following repo conventions and any explicit base branch supplied by an orchestrator. Ensures tracker-specific implementation linkage, records direct stacked parent PRs with `Depends on:`, verifies the created PR, and triggers the repository's automated review convention when requested by the calling workflow.
---

# Create a GitHub Pull Request

## Task

Create a pull request: $ARGUMENTS

This file is the contract; the reasoning behind its rules lives in `NOTES.md` beside it, keyed by section. NOTES explains; it never overrides.

Determine `owner/repo` from the current git remote. Determine the default branch from the repository — never hardcode `main`.

## PR base branch

- A user/caller-supplied required base **takes precedence over the repository default branch**. Validate it exists in the same repository; if it does not, **stop** — never fall back.
- No explicit base → the repository default branch. Call the result `<pr-base>`.

## Detect a stacked-PR parent

A non-default base is not automatically a stack parent (long-lived integration branches exist). Precedence:

1. caller supplied a parent PR URL → fetch it and verify its head branch is exactly `<pr-base>`;
2. otherwise search open PRs in this repository for one whose head branch is exactly `<pr-base>`;
3. exactly one → it is `<parent-pr>`;
4. none → `<pr-base>` is an ordinary integration base; add no stack metadata;
5. ambiguous → **stop** rather than writing incorrect metadata.

A parent PR must be in the same repository — cross-repository dependencies are scheduler/tracker relationships, never Git stack parents.

## Before creating the PR

Read `CLAUDE.md`/`AGENTS.md` for pre-PR checks, branch conventions, PR templates, draft/full rules, tracker linkage, and review-trigger conventions. Run required checks before opening the PR unless the caller explicitly documents that final verification was already completed by `implement-issue-core`.

**Branch naming**: follow documented repo convention; otherwise preserve the current branch — never invent a convention.

# Tracker-specific issue linkage

Every implementation PR is unambiguously linked to the exact canonical issue URL it implements. Determine the tracker from that full URL.

| tracker | linkage |
|---|---|
| GitHub Issues | a GitHub-recognized closing keyword with the **full canonical issue URL** (`Closes: https://github.com/acme/repo/issues/123`; `Fixes:`/`Resolves:` where repo convention requires). `Part of:` alone is insufficient when the issue should auto-close on merge — and is exactly what you emit when it should not (coverage finding, below) |
| Linear | preserve the **full Linear issue URL** near the top of the body and follow the workspace's documented linking convention, preserving any recognized identifier in title/body. Never invent GitHub `Closes:` semantics for a Linear issue — completion automation is workspace-specific |
| other | follow documented integration semantics; with no reliable convention, retain the full canonical URL and report that automatic status transition cannot be guaranteed |

If an implementation PR cannot be linked to an exact issue, **stop** rather than creating an orphan (NOTES). Directly-invoked ad-hoc PRs with no tracked issue are the exception only after the user confirms there is no issue.

## A PR shipping against a coverage finding links but does not close

When the caller reports a **coverage finding** — a declared dependency satisfied on paper whose capability is absent, leaving acceptance criteria stubbed, disabled, or omitted — a closing keyword would auto-close an issue nobody finished (NOTES). For that PR:

```text
Part of: https://github.com/acme/repo/issues/123
Blocked by: https://github.com/acme/repo/issues/131
```

- `Part of:` instead of any closing keyword; `Blocked by:` naming the prerequisite issue the finding produced; a body section stating which acceptance criteria are unmet and why.
- The issue stays **open**; closing it is a human decision once the gap is filled, never a side effect of this merge.
- On Linear and other trackers: keep the canonical URL and do not apply the workspace's completion automation; where you cannot tell whether the integration will transition the issue on merge, say so rather than assuming it will not.
- **Report which form you emitted**, so the caller reconciles completion against it rather than assuming a close.
- Scope narrowly: a **recorded** coverage finding only — never a PR whose author merely feels uncertain (NOTES).

# PR description template

Tracker relationship line(s) first. Immediately after them, if `<parent-pr>` exists, exactly one:

```text
Depends on: <full parent PR URL>
```

Then a blank line and the normal description/template. `Depends on:` always means the direct Git stack parent PR, never tracker issue dependencies.

# Creating and verifying the PR

- Draft/full behavior follows repo docs; otherwise work repos default to draft and personal repos to full. Explicit caller/user preference wins.
- **Report the as-created draft state** — supervising workflows need it to tell a run-drafted PR from a human-drafted one, and this skill never changes draft state after creation (NOTES).
- Use GitHub MCP in remote/web environments; `gh pr create --base <pr-base>` locally when available.
- Directly invoked by a user → show proposed title/body and confirm before creation. Chained from an authorized implementation workflow → no second confirmation.

After creation, fetch/read the PR and verify:

1. head/base are correct;
2. canonical tracker linkage is present exactly as intended, **in the intended form** — a closing keyword only where the issue is fully implemented, `Part of:` plus `Blocked by:` where a coverage finding was reported. A PR that links correctly but closes an issue it only partly implements passes a linkage check and still ends the issue's life;
3. `Depends on:` is correct when stacked and absent when not.

**Do not report success before verification.**

# Automated review trigger

By default, implementation workflows expect this skill to trigger the repository's documented automated review after the PR is created and final implementation state is pushed. Use the repo's documented trigger; with none, default to `@codex review` where that convention is supported.

- **The trigger comment must come from the invoking user's own account, or the convention does not fire** — the one post exempted from the posting-identity rule (`backlog-orchestrator`, *Posting identity*, states the rule once; do not restate it). Every other authored write this skill makes — the PR itself, its body, any other comment — follows that rule and its availability test.
- A caller may explicitly request a **deferred review trigger** (e.g. an intentionally early WIP draft): create/verify the PR but do not trigger until the caller later requests it.
- Do not re-trigger merely because subsequent CI checks run. Re-trigger after a substantive review-fix round only when repo convention requires it.

## Substantive vs mechanical pushes

Re-trigger review after a **substantive** push; never after a **mechanical** one. A push is mechanical when it changes identity, location, or formatting and nothing else:

- a restack/rebase onto a new base whose conflict resolutions reproduce both sides' original intent rather than picking between them;
- a renumber/regeneration of a claimed artifact (migration number + index entry, lockfile, generated manifest or client) where content is unchanged apart from the identity or ordering that had to move;
- formatter-only output.

Everything else is substantive — including a conflict resolution that chose between behaviors, and a regeneration whose output differs beyond identity/ordering. **Cannot tell → substantive.**

Qualifying as mechanical also requires the repository's deterministic checks to validate the push — those, not another review round, are what stand behind it:

- no check exists that would catch a bad renumber or dropped hunk → the push is **not mechanical**; it needs review;
- for a renumbered/regenerated artifact, "passes the checks" means **verified to apply** — regenerate through the repository's own generator (never hand-edit identity fields) and exercise the apply path (migrate a scratch database, install from the lockfile, regenerate-and-diff). Unverified → substantive (NOTES: the silently-skipped-migration failure).

This governs what the workflow triggers, not what the review provider does on its own events (e.g. re-reviewing a draft marked ready) — neither a reason to suppress a due trigger nor to issue one that is not due.

# Boundaries

This skill ends after PR creation, verification, and the review trigger. Later review fixes belong to `repair-pr`/`resolve-pr-comment`; long-lived event supervision belongs to the invoking orchestrator.

# Output

Return:

- PR URL; canonical issue URL + tracker; PR base branch; parent PR URL when stacked;
- issue linkage verified: yes/no, **and the form emitted** (closing keyword, or `Part of:`+`Blocked by:` for a coverage finding);
- draft state as created (draft/ready) and what decided it (repo docs, caller preference, default);
- review triggered/deferred and how;
- **the posting identities observed, one entry per `(transport, credential)` pair written through, carrying both halves of its key plus the write kind observed** — the PR's creation and the trigger comment reported **separately**, even where they share a pair: a platform can author the two kinds differently, and a merged answer overwrites one observation with the other (NOTES). Report invoking-user entries too, and `unestablished` where a write was not read back — the trigger comment's entry is the only comment-kind evidence the caller's next trigger selection can use.
