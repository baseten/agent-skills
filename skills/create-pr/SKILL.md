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

Read `CLAUDE.md`/`AGENTS.md` for branch conventions, PR templates, draft/full rules, tracker linkage, and review-trigger conventions.

**That read does not supply the gate.** Where the caller supplied the check set and its outcomes, use them and do not re-derive. Where no caller did — a direct invocation — derive the set here, before running anything and before drafting the body, the way `implement-issue-core`, *Final local verification* does: the base branch's required status checks, falling back to the workflow's check steps and marking the set unproven, mapping each required context to the local command that produces it, and carrying a context with no local equivalent as `not locally runnable`. **Never from the `CLAUDE.md`/`AGENTS.md` list read above** — that list describes the gate and drifts from it, so a run built on it is complete against the wrong thing and the body's table then reports that completeness as compliance. Run the locally runnable part before opening the PR unless the caller explicitly documents that final verification was already completed by `implement-issue-core`, and hold the set and its outcomes for the body's gate table below.

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

**Anything the title or the body claims about existing code needs a read behind it before the PR is created** (`references/establish-do-not-assume.md`, *You are about to assert it*) — both are read by every reviewer and by the owner, and a remembered blast radius renders identically to a checked one. **The title is included deliberately**: it is composed in the same step and shown for the same confirmation, and a claim moved from the body into the title would otherwise escape the check by getting shorter.

**The body is short and states intent rather than content** — the authored-write-form rule stated once in `references/authored-write-form.md`, including its 300-word budget and what the body must not contain. Apply it from there rather than restating it. **Whether the body carries the attribution footer is decided by that section's approval test, and this skill is where the test actually splits**: a body opened by a dispatched worker carries it, and a body this skill showed to the user under *Creating and verifying the PR* below and created after their confirmation or edit does not — that confirmation is approval of this exact text, which is the whole condition. Where the run cannot say the user read the body, the footer goes on. Its consequences at this decision point: the linkage lines, the `Depends on:` line where there is one, and — **on a PR opened for an issue — a one-line `Chartered scope:` taken from that issue** are **required contents** and survive the budget, as are the `Part of:`/`Blocked by:` pair and its unmet-criteria section under a coverage finding, and a repository template's headings. **The `CLAUDE.md`/`AGENTS.md` read above is where a repository's or user's own PR-description style guide is found** — read it before drafting the body, not after, and where one exists it governs the body's shape and its budget wins over the floor. Run its edit pass if it has one. The footer applies either way.

# Creating and verifying the PR

- Draft/full behavior follows repo docs; otherwise work repos default to draft and personal repos to full. Explicit caller/user preference wins.
- **The `Chartered scope:` line is what makes a later ratchet check possible, and it is only truthful now.** One or two sentences from the issue, written at creation while the scope is still uncontested. A supervising run compares each repair push against it (`backlog-orchestrator`, *PR promotion and central supervision*); recorded later it would be written from the diff and could only agree with it, and the body is where it survives a session boundary that a run's own state does not.
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

- **Where the repository documents a documentation-review convention and this PR's diff qualifies, that convention is the trigger** — that convention is the `review-docs` skill, **invoked on the PR rather than posted as a comment**, so confirmation that the trigger took effect is its completed pass and the review comment it posts, not a reviewer arriving. On a **documentation-only** diff it runs *instead of* the ordinary review trigger; on a **mixed** diff, only where the repository documented the mixed case as well, and then *in addition to* the ordinary trigger, which is still issued in full. `review-docs` owns the documentation test, its rounds, and what it reports — do not restate them here. Cannot tell whether a path is documentation → it is not, and the ordinary trigger stands alone.
  - **This governs re-triggers as much as the first trigger**, and every caller that re-triggers "where repo convention requires it" inherits it: a routed convention is **re-invoked, not re-posted**, so there is no trigger comment and **no trigger author to select from the posting-identity map** — the selection step those callers perform has nothing to select and is not skipped by oversight. `review-docs` bounds its own rounds and declines past them; **a decline is that convention's completed answer to a re-trigger**, not a trigger that failed.
  - **Skill unavailable → the ordinary trigger stands alone, and report that it did.** Same fail-safe direction as the cannot-tell rule above: a PR reviewed by the wrong instrument costs a reading, a PR reviewed by nothing costs the review.
- **The trigger comment must come from the invoking user's own account, or the convention does not fire** — the one post exempted from the posting-identity rule (`references/posting-identity.md`, *The review trigger*, states the rule once; do not restate it). It carries no attribution footer either, and **the reason to state is the functional one** (`references/authored-write-form.md`): the comment must read exactly as the convention expects, so it carries the trigger text and nothing else. The trigger is also unattended, so the approval test on its own would ask for a footer — this exemption is what overrides it, and it does so on both counts for the same cause. Every other authored write this skill makes — the PR itself, its body, any other comment — follows both rules and the identity rule's availability test.
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
- **the gate table**: one row per check, with its outcome, from the set held since *Before creating the PR* — the caller's, or the one derived there. It is built from that set and from nothing else; a table assembled at this point from whatever is to hand is the failure the derivation exists to prevent, arriving one step later. This is a **required content** of the body under the write-form rule, so brevity governs how each row is written and never whether it is written. A body with a check missing from the table is an incomplete report, not a short one — and a caller that accepts it has moved the discovery of a skipped step from itself to CI;
- **for each claim about existing code carried in the title or body, the artifact read to settle it** — or that it was posted marked unverified, with what would settle it. The body carries the claim and never the audit trail (the write-form rule), so without this the read leaves no durable record and the caller either repeats it or trusts it;
- draft state as created (draft/ready) and what decided it (repo docs, caller preference, default);
- review triggered/deferred and how — and **where the convention was a skill invocation rather than a comment, that skill's returned result in full**: the round it ran, its findings by class with the actionable count, its declined/completed status, and the posting-identity observations it returned. Forward them; do not summarize them away. On a documentation-only routed PR this skill posts **no** trigger comment, so the routed skill's entry is the run's only comment-kind evidence and the bullet below has none of its own to report;
- **the posting identities observed, one entry per `(transport, credential)` pair written through, carrying both halves of its key plus the write kind observed** — the PR's creation and the trigger comment reported **separately**, even where they share a pair: a platform can author the two kinds differently, and a merged answer overwrites one observation with the other (NOTES). Report invoking-user entries too, and `unestablished` where a write was not read back — the trigger comment's entry is the only comment-kind evidence the caller's next trigger selection can use.
