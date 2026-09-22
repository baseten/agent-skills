# Notes — establish it, do not assume it

Reasoning for `rules/establish-do-not-assume.md`. Explains; never overrides.

**Why assertion and assumption are one rule and not two.** They arrive
differently — one as a sentence someone wrote, one as a step nobody questioned —
but the remedy is identical: name the artifact that settles it and read that.
Splitting them would have produced two rules with the same body and a boundary
nobody could apply, because the interesting cases sit on it. *Ready to build:
yes* is a sentence a previous session wrote **and** a step this one did not
question.

**Why the run's own next step is in the table.** It is the one that hides, and it
was found twice in a single run, both times by the owner asking rather than by
any check. A supervision summary is built from observations — heads, CI, threads
— and the next step is appended as prose. Nothing joins that prose to a tool
call, so *I triggered the reviews* and *the reviews need triggering* render the
same in a table where every other row is evidence. The false one is the more
likely, because a next step is written while summarising rather than while acting.

**Why a documented claim is still a claim.** This is the clause most likely to be
read as paranoia. It is not about trusting the author: a repository's convention
block is correct on the day it is written, describes a configuration that can
change, and is the only part of the system nothing re-verifies. The cost of
checking once and recording is one call; the cost of inheriting a stale assertion
is a run that reasons confidently from it.

**Why the provider half was worth stating at all**, given the skill already
demands per-PR verification that a trigger took effect. Because it demanded that
and then assumed publishing re-triggers a review, which is the same question
answered two ways in one document. The general form is that this repository is
rigorous about what it cannot see — transport visibility, posting identity,
worker check results — and credulous about provider behaviour one call would
settle. That asymmetry is the finding; the instances are how it was noticed.

**Why the asymmetry argument closes the rule.** A rule of this shape reads as
counsel of perfection unless the cost is named. Establishing costs one call.
Assuming costs a wasted pass, a timeout against an event that will never arrive,
or a merge on evidence nobody invalidated — and it is silent, because an
assumption that holds and an assumption nobody tested look identical until the
day they diverge.

**Why the rule asks a run to report what it verified.** Otherwise the record does
not compound: the next session repeats the call, or worse, repeats the
assumption. A recorded observation is the only artifact that turns this from a
per-run discipline into a property of the repository.
