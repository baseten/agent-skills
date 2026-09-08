---
name: fix-review-round
description: >-
  Entry point for resolving a review round on this repository. Use when acting
  on Codex or human review comments on a PR against baseten/agent-skills,
  before editing any SKILL.md, NOTES.md or scripts/. It points at the two files
  that hold the procedure; it deliberately does not restate them.
---

# Fix a Review Round Here

Read these two, in this order, before editing anything:

1. **`CLAUDE.md`** — the rules. The completion criterion, the classification,
   the consequence sweep, what a guard owes, where the reasoning goes.
2. **`docs/review-fix-workflow.md`** — why those rules take the shape they do,
   the axis walk for a shape finding, and what automating a round here costs.

This file is a pointer and not a copy, for the reason `AGENTS.md` gives for
being one: a second statement of that procedure would be a summary maintained
apart from the rules it summarises, which is the failure mode `CLAUDE.md` is
largely about, and the reasoning applies here whether or not a check enforces
it — the one that did was removed for catching only verbatim copies.

## The one thing neither of those can tell you

**If you are working on a checkout of this repository from a session rooted
somewhere else** — a clone in a scratchpad, a worktree, another repository's
session driving this one over Bash — **then nothing here has been loaded for
you**, including `CLAUDE.md`, `AGENTS.md`, and this file. Whatever you know
about this repository came from a handoff or a review comment, as context
rather than as an instruction you are held to.

Read `CLAUDE.md` explicitly. A review comment citing `AGENTS.md:L3-L4` **is
that instruction arriving**; follow the link rather than reading past it. A
review series on this repository produced seventeen findings against a fixer
who had been handed that citation three times and never opened it.

## While you are in a round

- **Do not add a check that greps the contract's prose**, and do not restore one
  that was removed. Four such checks were deleted after each was tested and
  found to verify less than its name: assertions pinning a sentence, a
  duplicate-rule check that passed on a paraphrase, a cross-reference checker
  that confirmed a heading existed while its rule had been gutted from under it
  (`README.md`, *Checks*). What earns CI here reads a token, not prose.
- **Where a change should not alter meaning, compare two readings of it** rather
  than looking for a check that will confirm it — `CLAUDE.md` states the
  procedure, and with the prose checks gone it is the only signal there is.
- Where a finding is about behaviour — a shell invocation, a tool's flag, what
  a command leaves behind — **run it**. Reasoning about mechanics is how such a
  defect gets in, and one recipe here took three rounds because each corrected
  version was reasoned about rather than executed.
- Check merged-ness by PR state, not by ancestry. This repository squash-merges,
  and `git merge-base --is-ancestor` called 41 branches live when 6 were.
