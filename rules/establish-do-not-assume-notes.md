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

**Why the outbound direction is a third section rather than a line in the first
(Sept 2026).** The remedy is identical — name what settles it and read that — but
the trigger is not, and the trigger is what a rule has to be reachable from. The
first two sections fire when something arrives or when a step is about to run;
this one fires at the moment of writing a sentence, which is exactly when nothing
feels like a lookup. Folded into *Someone asserted it* it would have been read as
being about other people's claims, which is how the docs-only version of this
check sat next to a review reply carrying a false premise and did not catch it.

**Why an unverified claim is marked rather than dropped.** Dropping it loses
information the owner may need and cannot recover; posting it plainly launders a
recollection into evidence. Marking it costs a clause and keeps the reader's
ability to weigh it — and where they do have the codebase in front of them, they
settle it in seconds.

**Why attempting-as-establishing gets its own section (Sept 2026).** The rest of
the rule assumes there is something to look at, and its whole economy — one call
against a wasted pass — depends on that. Where the only way to know is to do the
thing, the economy inverts: the attempt costs what the action costs and may
consume a budget the run is trying to protect. A rule that said only *establish
it* would keep being followed by re-attempting on a timer, which is how twelve
review rounds landed on a two-round PR. Naming the refusal as an answer is the
other half: without it, a refusal reads as a failed attempt and the natural
response to a failed attempt is another attempt.

**The incident the section is written from.** A run out of review budget armed a
job to retry the review trigger every ten minutes until the provider answered. It
answered all twelve queued triggers at once when the budget reset: twelve review
rounds on a pull request with a two-round cap, fourteen findings, and the budget
spent many times over before the first fix landed. Nothing about the job was
lazy — it wanted to know when the provider returned, which is the right question.
What it got wrong is that there was no way to ask that did not consume the thing
it was waiting for.

**Why claims about state were folded into the outbound section rather than given
their own (Sept 2026).** The remedy is identical — a read behind the sentence —
and so is the trigger: the moment of writing it. What differs is the object, and
a separate section would have implied a separate rule. The status summary is
named because it is where the failure concentrates: a report is written to be
believed, so a sentence recalled rather than read carries the full weight of an
observation. Both owner-caught instances were in summaries, and neither was
load-bearing at the moment it was written, which is exactly why neither was
checked. The recalled-example case is included because it is the same failure
with a longer half-life, and the example given is this repository's own.
