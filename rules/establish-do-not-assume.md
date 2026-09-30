# Establish it, do not assume it

**Nothing is established until something observed establishes it.** A claim is not evidence. An assumption is not evidence. A default is not evidence. Each arrives as a sentence that reads exactly like a finding, and the remedy is always the same shape: name the artifact that would settle it, and look at that.

Three kinds, and runs get caught by all of them — two where a claim arrives, one where the run makes it. What was established stays established only as of when it was read (*Every read is a snapshot*). **Where the run verified something it could have assumed, say so in the returned output, naming the artifact read** — the body or reply carries the claim, not the audit trail (the write-form rule), so without an output field the read leaves no record and the next session either repeats it or trusts it.

## Someone asserted it

A report is a claim about a world the reporter may not be able to see, whoever wrote it and however sincerely. That is not a reason to distrust the author; it is a reason to name what would settle it. **Settling a claim means checking the state it asserts, not that some object exists** — existence is the cheap half and the one that reads as done.

| the claim | what settles it |
|---|---|
| a worker: *all gates passed* | CI on the pushed head |
| a worker: *pushed* | the remote branch's head being the commit the worker claims — a branch that exists may carry an earlier push |
| a reviewer: *fixed in `<sha>`* | the ref resolving **and** its diff containing the fix — a commit that exists is not a commit that did the thing |
| a prior session's carried note | the thing it describes, re-read now |
| a tracker convention block: *Ready to build: yes* | the code against the ticket |
| a cross-repo `file:line` citation | that repository's current default branch |
| the run's own *next step* | whether the call was made |

**Never report a next step in a form readable as done**: perform it first, or mark it outstanding with the reason. Where something is blocked on an action this run owns, that action's observable status is part of the state — *not triggered*, *triggered at `<ts>`*, *awaiting*, *findings*, *clean on `<sha>`* — never a prose sentence about what is needed.

## Nobody asserted it — the run assumed it

No sentence to disbelieve: the run reasons from what a tool or provider *probably* does.

| the assumption | what to do instead |
|---|---|
| a provider's name says what triggers its automated review | that is a property of the repository's configuration, not of the name: **assume nothing does**. Trigger explicitly and verify per PR that the trigger took effect. Where an event was observed producing a review in a repository, record it; where no event-driven review exists, skip the machinery that waits for one rather than timing out against it |
| an enabled automation performed its action | query the artifact |
| a capability that is reachable is permitted, or one that is unreachable is absent | *cannot reach it*, *must not write it* and *it is not there* are three states; record which, since a report naming only the first leaves the others to be inferred |
| a repository documents it — its provider re-reviews on publish, a field is authoritative | **a documented claim is still a claim**: check once and record, never skip checking |

## You are about to assert it

**Any claim this run makes about existing code, or about current state, needs a read behind it before it is posted** — in a review reply, a PR body, a `DECISION` item, an issue, a commit message, a status summary. Not a recollection of the codebase, and not an inference from the part of it currently in view. Nothing about a remembered sentence marks it as remembered; a motivating example recalled rather than re-read is the same claim.

**Claims about state need the same, a status summary most of all**: what a PR, an issue, a branch or a session *is right now* changes underneath the run between turns. **The tell is a sentence about current state with no read behind it.** Either read it, or say when it was last read — state carried from an earlier read and reported with that time is honest and the normal form for a cached record, so this is not a demand to re-read everything before every report. What fails is the present tense with no read at all.

**Wire the check at the point the artifact is composed**, not at the skill that happens to carry this file: the reply *and* the escalation draft, the PR body *and* its title, the `DECISION` item, the issue body a rewrite produces, the ruling comment, the commit message, the status summary and checkpoint report — and into the dispatch prompt of any worker that will author one on the run's behalf, since a prompt that omits a requirement gets a worker that skips it.

**A claim that cannot be settled before posting is posted marked unverified, with what would settle it** — never posted plainly, never dropped. A `DECISION` item is the expensive case: the owner rules from the claim, with less of the codebase in front of them than the run has.

## Establishing it by trying it costs what the attempt costs

Some things have no artifact to read and can only be established by attempting them: whether a credential can write, whether a provider will answer, whether a channel delivers. **There the probe is the action, with the action's cost, side effects and budget.** Attempt it once, record what came back, and act on the record. **Never put such an attempt on a schedule** to find out when it starts working: every firing is another performance of the action (notes: twelve review rounds on a PR capped at two).

**What separates a probe from the action is consequences, not intent** — everything the attempt *causes*, not what remains afterwards:

| the attempt | what it is |
|---|---|
| reading to find out whether a read works | a probe: it changes nothing, and a decision may rest on it |
| writing to find out whether a write works | the write |
| triggering a review to find out whether the reviewer is answering | a review request |
| a write then undone — a comment posted and deleted | still a write: it queued the reviewer, mailed the subscribers and kept the audit entry |

A probe leaves no durable artifact and no side effect anyone else observes. It may still cost a metered read, so it stays inside the consuming skill's read budget, and a probe against a refused allowance is deferred like any other read, never retried.

**A refusal is an answer and is recorded as one.** *Refused, with a reason* is a third state beside *succeeded* and *no response*: the capability exists and is currently unavailable. Where the refusal names a condition that will lift — a quota, a window, a reset — the record carries it, and the run waits for the condition rather than re-attempting to discover it.

## Every read is a snapshot

**A multi-item read produces a composite of instants, not a state.** Several sessions routinely act on one remote at once; a PR read as open can merge before the next read in the same conversation. So:

- **Where a decision spans several reads — a merge gate, a ranking, a settle — re-read the deciding facts immediately before acting on them.** Not the whole world: the specific facts the decision turns on, at the moment it is made. A merge gate's freshness check is one instance.
- **Timestamp every state report.** "Zero open PRs" is only ever true as of a time. A checkpoint, a handover and a progress line each carry the instant they describe, so a reader can tell a current answer from a correct one that has aged.
- **A disagreement between a checkout and an API response is settled by a third read, not by precedence.** Both are observations with an age — a checkout as old as its last fetch, a response as old as when it was issued — and either can be the stale one. Where they disagree about a fact the next act turns on, **re-read the forge now**, then refresh the checkout to match, so the next comparison is not against a value already known to be wrong.
