# Field feedback

This is the rule other skills mean when they cite *field feedback*: how a
long-running run reports what in its own contract did not work, so the next
version can fix it.

**It is not a skill and nobody invokes it.** It is a shared rule, held once at
`rules/field-feedback.md` and copied into each skill that applies it by
`scripts/refresh_shared_rules.sh`. A skill reads its own
`references/field-feedback.md`. Edit the source, never a copy.

## When

**Once, at the run's wrap-up**, at the point its skill names: a settled run's
return, a final report, a conductor's context clear. **Never mid-run**: noticing
is the run's, reporting waits until the work is done, so feedback never competes
with it. The run keeps a one-line note of each candidate as it meets it, in the
record it already keeps (its state block, ledger or report notes); wrap-up turns
the notes into the draft, or into nothing. **A run inside another's** — a
`swarm` or `supervise-prs` a run invoked — drafts nothing: it passes its notes to
its caller, whose one draft carries them.

## What counts

**A finding is something that happened in this run, at a turn the draft can
name.** One of four kinds:

- **Did not work**: the run followed the contract and the outcome was wrong, or
  a step did not fit the environment it ran in (a route that does not exist
  there, a tool that failed, a read the environment forbids).
- **Workaround**: the run did something the contract does not describe, to finish.
- **Contradiction**: two rules disagreed at one decision, or the run had to guess
  which applied.
- **Native replacement**: a tool this session holds, named by its exact name,
  that does what the contract does by hand or with a script. Only a tool the
  session holds counts: a model's sense of what a platform added is not evidence
  (`references/establish-do-not-assume.md`).

**Not findings, at any count**: phrasing, length, ordering, terminology, and
anything of the shape *"this could be written differently"*. These are unbounded,
and admitting them is how a report stops being read.

## The draft

**At most one per run, and none where nothing qualifies** — say "No field
feedback" in the report. It is an issue draft for the repository the skill comes
from, in this form:

```text
Title: <skill>: <what to change, as an outcome>

## Summary
<the run, the skill's version where the run's report carries one, and what
went wrong, in two or three sentences>

## What happened, and why
<each finding: its kind, the turn or step where it happened, and the cause as far
as the run can tell — where the rule sits, what it costs, or what the environment
lacked>

## Proposed changes
<per finding, the smallest change that would have prevented it>

## Acceptance
<per finding, what a run reading the changed contract does differently>
```

**Search that repository's open issues first**; where one covers a finding, the
draft adds to it, by link, instead of repeating it.

**The run never files it.** The draft goes into the run's report, in full — on a
ledger that holds drafts, in the ledger too — and the owner files it or not. Filing
an issue in another repository is the owner's write, and no run's authority
reaches it. The report lists it once, at low urgency, never as a decision.
