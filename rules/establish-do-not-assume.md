# Establish it, do not assume it

**Nothing is established until something observed establishes it.** A claim is
not evidence. An assumption is not evidence. A default is not evidence. Each
arrives as a sentence that reads exactly like a finding, and the remedy is always
the same shape: name the artifact that would settle it, and look at that.

Three kinds, and runs get caught by all of them — two where a claim arrives, one where the run makes it. And what was established stays established only as of when it was read (*Every read is a snapshot*).

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

## You are about to assert it

The same rule pointed outward, and the one that is easiest to skip because
nothing about it looks like a lookup. **Any claim this run makes about existing
code, or about current state, needs a read behind it before it is posted** — in
a review reply, a PR body, a `DECISION` item, an issue, a commit message, a
status summary. Not a recollection of the codebase, and not an inference from
the part of it currently in view.

The failure looks like confidence. A reply asserted that adding a connection
parameter in one module would also affect migrations; migrations built their own
connection and it would not, which four greps settled in minutes. Nothing about
the sentence marked it as remembered rather than read.

**Claims about state need the same, and a status summary most of all.** What a
PR, an issue, a branch or a session *is right now* is as much a claim as what code
does, and it changes underneath the run between turns. **The tell is a sentence
about current state with no read behind it.** Either read it, or say when it was
last read: state carried from an earlier read and reported with that time is
honest and is the normal form for a cached record, so this is not a demand to
re-read everything before every report. What fails is the present tense with no
read at all.

Two such claims were caught by the owner in one day: a PR reported as having every
review thread resolved, with four still open — answered with fixes and never
marked resolved — and a wave's worker sessions reported as done and archived,
all four idle and holding containers, with the session list never read. A status
summary is where this concentrates, because it is written to be believed, in the
register of a report. A motivating example recalled rather than re-read is the
same claim with a longer life: one session was cited in several places as four
weeks of unpushed work, and its PR had merged the day it was created.

**The check belongs at the point the artifact is composed, not at the skill that happens to carry this file.** A reference present in a skill directory and cited nowhere near the write is a reference nobody reads: wire it at each site that authors one of these — the reply *and* the escalation draft, the PR body *and* its title, the `DECISION` item, the issue body a rewrite produces, the ruling comment, the commit message, the status summary and checkpoint report — and into the dispatch prompt of any worker that will author one on the run's behalf, since a prompt that omits a requirement gets a worker that skips it.

**Where the run did verify something it could have assumed, the verification belongs in the returned output**, naming the artifact read. The body or the reply carries the claim and not the audit trail — that is the write-form rule — so without an output field the read leaves no durable record and the next session either re-does it or trusts it.

**A wrong claim in a `DECISION` item is the expensive case**, because the owner
rules on it: the claim is the evidence they are ruling from, and they have less
of the codebase in front of them than the run does. Where a claim cannot be
settled before posting, post it marked as unverified with what would settle it,
rather than posting it plainly or dropping it.

## Establishing it by trying it costs what the attempt costs

Most of this rule is about reading an artifact, which is cheap. Some things have
no artifact to read and can only be established by attempting the thing: whether
a credential can write, whether a provider will answer, whether a channel
delivers. **There the probe is not a probe — it is the action, with the action's
cost, its side effects and its budget.** So: attempt it once, record what came
back, and act on the record. Never put such an attempt on a schedule to find out
when it starts working, because every firing is another performance of the
action.

**What separates a probe from the action is consequences, not intent.** Reading
to find out whether a read works costs a read and changes nothing, so it is a
probe and a fine thing to build a decision on. Writing to find out whether a
write works leaves the write behind. Triggering a review to find out whether the
reviewer is answering *is* a review request. Ask what the attempt leaves behind:
**a probe leaves no durable artifact and no side effect anyone else observes — and the test is over everything the attempt *causes*, not over what remains afterwards. A write undone is still a write**: posting a comment and deleting it queued the reviewer, mailed the subscribers and kept the audit entry. It
may still cost a metered read, so it stays inside whatever read budget the
consuming skill governs — cheap is not free, and a probe against a refused
allowance is deferred like any other read rather than retried.

Observed: a run out of review budget retried the trigger every ten minutes until the provider answered, and it answered all twelve queued requests at once — twelve rounds on a pull request capped at two (notes). The job was right to want to know and wrong about how to find out.

**A refusal is an answer and is recorded as one.** *Refused, with a reason* is a
third state beside *succeeded* and *no response*: it establishes the capability
exists and is currently unavailable, which is more than silence tells you and
different from failure. Where the refusal names a condition that will lift —
a quota, a window, a reset — the record carries it, and the run waits for the
condition rather than re-attempting to discover it.

## Every read is a snapshot

**A multi-item read produces a composite of instants, not a state.** Several sessions are routinely active on one remote at once, and one of them merging three PRs during another's run is ordinary rather than exceptional. Observed directly: a PR read as open, was reported as open in a handover, and had merged between two reads **in the same conversation**. Three separate audits of "where are we" over three days each produced a different answer and each was correct when it was taken.

Two rules follow, and they are cheap:

- **Where a decision spans several reads — a merge gate, a ranking, a settle — re-read the deciding facts immediately before acting on them.** Not the whole world: the specific facts the decision turns on, at the moment it is made. A merge gate's freshness check is one instance of this; the general rule is that a decision computed at 14:02 and executed at 14:31 was made about a repository that no longer exists.
- **Timestamp every state report.** "Zero open PRs" is only ever true as of a time, and in a repository with concurrent tracks that time expires in minutes. A checkpoint, a handover and a progress line each carry the instant they describe, so a reader can tell a current answer from a correct one that has aged.

**And a disagreement between a checkout and an API response is settled by a third read, not by precedence.** Both are observations with an age: a checkout is as old as its last fetch, a response as old as when it was issued, and either can be the stale one. A redundant PR was opened against a base that had already moved because a stale `origin/main` was believed over a response the run was already holding — but a response held for an hour while the checkout was fetched a minute ago fails the same way with the sides swapped. So where the two disagree about a fact the next act turns on, **re-read the forge now**: a read taken at the moment of deciding is newer than both, which is the same rule as re-reading the deciding facts above. Then refresh the checkout to match, so the next comparison is not against a value already known to be wrong.

## Why this is worth a rule rather than diligence

The asymmetry is what makes it pay. Establishing something costs one call.
Assuming it costs a wasted pass, a timeout against an event that will never
arrive, or a merge on evidence nobody invalidated — and it fails silently, because
an assumption that holds and an assumption nobody tested produce the same output
until the day they do not.

Where a run has verified something it could have assumed, **say so in the
output**. The next session reads that as an observation rather than repeating the
assumption, which is the only way the record compounds.
