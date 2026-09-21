# NOTES — review-skill

Reasoning for `SKILL.md`, keyed by its section names. Explains; never overrides.

## What this reviews, and what it replaces

**Why a third reviewer rather than widening `review-docs`.** They differ in the
oracle, and the oracle is the whole review. `review-docs` checks claims against a
codebase at `path:line`; a contract makes no claims about a codebase, it makes a
reader decide. Their finding taxonomies follow from that and share nothing:
`FALSE_PREMISE` has no analogue here, and `SHAPE` has none there. What they do
share is termination, which is why that left as a rule rather than either skill
absorbing the other.

Issue #93 proposed a thin orchestrator over review and repair primitives. This
skill is review only, deliberately. `repair-pr` already owns bounded repair and
already takes a finding set; a second repair primitive would restate its budgets
where they could drift.

## Establish what changed for a reader

**Why the arms come from git and never from a committed copy.** A baseline in the
tree is a second contract to maintain, and the one that goes stale is the one
nobody is reading. `CLAUDE.md` states this for the method generally; it is
repeated here only as an instruction to the script, which is where it is acted on.

## What is a finding

**Why `UNPINNED` is a finding at all**, given it names no defect in the change:
because the alternative is a reviewer arguing about behaviour with nothing to
settle it, which is the loop this repository has already paid for. Issue #93's
ordering is `bug → failing eval → repair → passing eval`, and a change whose
behaviour no scenario covers cannot enter that ordering at step one. Reporting
the missing scenario is cheaper than discovering its absence in round two.

**Why `SHAPE` is called out in the taxonomy rather than left to `CLAUDE.md`.**
The classification exists in `CLAUDE.md` and was still missed on a live change:
one assumption about where reasoning lives arrived as three separate findings
across three rounds, and each was patched where it landed. A reviewer that can
name the shape is the cheapest place to stop that, because it is the one holding
all the instances at once.

## The rounds

**Why this skill's report carries no revision marker**, where `review-docs`'s
does. A marker is a promise that the named commit was read, and the budget rule
governs certifying one. This review's consumer is a person deciding whether to
merge a contract change, not a gate reading a freshness line; adding a marker
would create an obligation with no reader and a way to be wrong with no benefit.

## When to reach for a real task run

**Why `skill-creator` is named here and not made a dependency.** It answers a
question the scenario corpus cannot — whether the model behaves better, judged
blind — and its baseline for an existing skill is explicitly the previous
version. But it needs test cases and a human in the loop, so making it mandatory
would price out the common case, which is a two-paragraph contract edit.

The capability-based wording is load-bearing rather than polite. An earlier
session concluded `skill-creator` was the wrong instrument here, having
generalised from its trigger evaluator — a separate subsystem that never reads
`evals.json`. A skill that silently skipped it would have made that mistake
permanent and invisible; one that reports what it could not run makes it a line
in a report someone can question.
