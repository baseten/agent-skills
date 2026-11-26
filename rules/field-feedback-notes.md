# Field feedback — notes

Reasoning for `rules/field-feedback.md`, keyed by its sections. It explains; it
never overrides.

## When

**Why this rule exists (owner's request, 2026-11-26):** a cloud conductor on
2026-11-25 skipped a sweep, hand-patched its work queue and built a REST route
the contract never described. All of it was known to the run, and none of it
reached the contract until the owner asked for a write-up (agent-skills#240 fixed
it). The run is the only witness to where its contract failed; without a rule,
that evidence dies with the session.

**Why at wrap-up, never continuously:** feedback written mid-run spends tokens on
the contract instead of the work, and pulls the run toward commentary. A run
keeps one-line notes as it goes and drafts once, when the evidence is complete.
A run inside another's passes notes up, so one run yields one draft.

## What counts

**Why every finding names a turn:** it is the bar that separates evidence from
opinion. *Not findings* copies `review-docs`'s exclusion for the same reason:
prose invites endless rephrasing, and a report full of it gets switched off.

**Why a native replacement must be a tool the session holds:** a model's picture
of what a platform shipped is out of date or invented as often as not. A tool in
the session's own list is observed; anything else is an assumption.

## The draft

**Why the run never files it:** filing in the skills' repository is a write
outside the run's scope, under the owner's account, about the run's own
instructions. The owner reads the draft and decides; the form (the one the
2026-11-25 report used) makes it ready to file or to hand to a fixing session.

**Why at most one:** several drafts per run become noise across a fleet of runs;
one draft with several findings stays readable, and the open-issue search keeps
repeats from piling up.
