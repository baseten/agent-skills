# Establish it, do not assume it

**Nothing is established until something observed establishes it.** A claim is
not evidence. An assumption is not evidence. A default is not evidence. Each
arrives as a sentence that reads exactly like a finding, and the remedy is always
the same shape: name the artifact that would settle it, and look at that.

Two kinds, and runs get caught by both.

## Someone asserted it

A report is a claim about a world the reporter may not be able to see, and it is
a claim whoever wrote it believed. That is not a reason to distrust the author;
it is a reason to name what would settle it.

*Settling a claim means checking the state it asserts, not that some object
exists.* Existence is the cheap half and the one that reads as done.

| the claim | what settles it |
|---|---|
| a worker: *all gates passed* | CI on the pushed head — observed on a PR already red on `format:check` |
| a worker: *pushed* | the remote branch's head being the commit the worker claims — a branch that exists may carry an earlier push |
| a reviewer: *fixed in `<sha>`* | the ref resolving **and** its diff containing the fix — observed three times naming commits that did not exist, and a commit that exists is not a commit that did the thing |
| a prior session's carried note | the thing it describes, re-read now |
| a tracker convention block: *Ready to build: yes* | the code against the ticket — an audit found eight call sites where the issue named six, and three of those named a different function |
| a cross-repo `file:line` citation | that repository's current default branch |
| the run's own *next step* | whether the call was made — observed twice in one run, both caught by the owner asking |

That last row is the one that hides. In a report where every other line is
evidence, a sentence about what happens next renders identically to one about
what happened, and it is written at the moment of summarising rather than acting.
**Never report a next step in a form readable as done**: perform it first, or
mark it outstanding with the reason. Where something is blocked on an action this
run owns, that action's observable status is part of the state — *not triggered*,
*triggered at `<ts>`*, *awaiting*, *findings*, *clean on `<sha>`* — never a prose
sentence about what is needed.

## Nobody asserted it — the run assumed it

Harder to notice, because there is no sentence to disbelieve. The run reasons
from what a tool or a provider *probably* does, and the assumption is invisible
until it is wrong.

- **What triggers an automated review is a property of a repository's
  configuration, not of the provider's name.** Assume nothing does. Trigger
  explicitly and verify per PR that the trigger took effect. Where a run has
  observed an event producing a review in a given repository, record that
  observation — and where no event-driven review exists, skip the machinery that
  waits for one rather than timing out against it.
- **An enabled automation is not a performed action.** Query the artifact.
- **A capability being reachable is not a capability being permitted**, and
  neither is the same as its absence. *Cannot reach it*, *must not write it* and
  *it is not there* are three states; a report recording only the first leaves
  the others to be inferred.

**A documented claim is still a claim.** A repository may state its provider
re-reviews on publish, or that a field is authoritative. That is a reason to
check once and record, not a reason to skip checking — it was written by someone,
at a time, about a configuration that can change.

## Why this is worth a rule rather than diligence

The asymmetry is what makes it pay. Establishing something costs one call.
Assuming it costs a wasted pass, a timeout against an event that will never
arrive, or a merge on evidence nobody invalidated — and it fails silently, because
an assumption that holds and an assumption nobody tested produce the same output
until the day they do not.

Where a run has verified something it could have assumed, **say so in the
output**. The next session reads that as an observation rather than repeating the
assumption, which is the only way the record compounds.
