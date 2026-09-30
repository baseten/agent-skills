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

**Why the rule is worth stating: the asymmetry.** A rule of this shape reads as
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

**Why an unverified claim is marked rather than dropped** (the rule states it for every outbound claim; the `DECISION` item is the expensive instance, and #168 separated the two sentences so the general reading, which the section's scope already gave, cannot be read as scoped to `DECISION` items). Dropping it loses
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

**Why the output instruction opens the rule (#168):** it used to close it, in a *Why this is worth a rule rather than diligence* section whose argument is the asymmetry entry above (*Why the rule is worth stating*) and whose one instruction — say in the output what was verified, naming the artifact — restated a line in the outbound section. It now sits once in the opening, where it governs every section rather than reading as a coda to one.

## Every read is a snapshot

Moved here from `backlog-orchestrator`, *Every read is a snapshot*, with its notes (#144). The rule is a claim about when an observation stops being evidence, which is this rule's subject; `settle-and-merge`'s freshness checks and the orchestrator's dispatch prompt each apply it.

**Why this is stated separately from invariant 1 (Sept 2026):** invariant 1 says where truth lives and was read as though that settled it. It does not say that truth moves while you read it, and with several sessions writing to the same remote it moves constantly — a PR read as open merged between two reads in one conversation. Everything downstream of a multi-item read is a composite of instants that never coexisted, which is a different failure from reading the wrong source and needs its own name.

**Why a disagreement is settled by a third read rather than by precedence (round 1):** the first version made the API response authoritative over the checkout, which is right about the observed failure and wrong as a rule — a response held for an hour loses to a checkout fetched a minute ago, and a permanent precedence sends the worker on with the stale one in exactly that case. Both are observations with an age. A read taken at the moment of deciding is newer than either, so the disagreement resolves into the rule one paragraph above rather than into a ranking.

**Why re-reading is scoped to the deciding facts:** re-reading everything before every action would cost more API budget than the read discipline allows, and the exposure is not uniform — a ranking computed from stale data is re-derivable, a merge performed on it is not. So the rule attaches to the acts that cannot be undone.

**The incidents behind the section (moved from the rule, #168):** a PR read as open was reported as open in a handover and had merged between two reads in the same conversation, and three audits of "where are we" over three days each gave a different answer, each correct when taken. A decision computed at 14:02 and executed at 14:31 was made about a repository that no longer exists. And the third-read rule's case: a redundant PR was opened against a base that had already moved because a stale `origin/main` was believed over a response the run already held.

## Someone asserted it

**The observations behind the table (moved from the rule, #168):** *all gates passed* was reported on a PR already red on `format:check`; *fixed in `<sha>`* named commits that did not exist, three times; a *Ready to build: yes* ticket named six call sites where an audit found eight, three of them naming a different function; and the run's own next step was reported as done twice in one run, both caught by the owner asking.

## You are about to assert it

**The incidents behind the section (moved from the rule, #168):** a reply asserted that adding a connection parameter in one module would also affect migrations; migrations built their own connection and it would not, which four greps settled in minutes. Two state claims were caught by the owner in one day — a PR reported as having every review thread resolved with four still open (answered with fixes, never marked resolved), and a wave's worker sessions reported done and archived, all four idle and holding containers, the session list never read. A recalled example: one session was cited in several places as four weeks of unpushed work, and its PR had merged the day it was created. The check is wired at each composing site because a reference present in a skill directory and cited nowhere near the write is a reference nobody reads.

## Establishing it by trying it costs what the attempt costs

**Moved from the rule (#168):** the retry-on-a-timer incident is the entry above; the job was right to want to know and wrong about how to find out.

**Also moved from the rule (#168):** a probe is cheap, but cheap is not free — which is why it stays inside the consuming skill's read budget; and a timestamp matters because, in a repository with concurrent tracks, the instant a state report describes expires in minutes.
