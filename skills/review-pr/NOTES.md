# NOTES — review-pr

Reasoning for `SKILL.md`, keyed by its section names. Explains; never overrides.

## Review a PR

**Where this came from (owner's ruling, 2026-11-06).** The owner kept a private
review skill that drafted reviews of colleagues' PRs for them to submit. Its
process was generic and its surfaces were not: it drafted some PRs in a tracker
that mirrors them for review, and named the owner's workplace throughout. The
owner split it. The generic process lives here, and the workplace wrapper keeps
only its facts and its tracker surface, declaring `metadata: extends: review-pr`
so a hand-off can substitute it where this skill is named. The owner wrote the
original, so its approach is reused where it is generic.

**Why drafts only, and why the owner submits.** A review is the owner's word
to a colleague, under their name. A draft costs the owner one read; a published
review that says the wrong thing costs a correction in front of the author. So
the skill never chooses the event either: approve, comment or request changes
is a judgement about a person's work, and it is the owner's.

## Never

**Why the review bot is never triggered and no reviewer is ever requested.** A
trigger comment is a live write on someone else's PR, and requesting a reviewer
changes who the author is waiting on; both are visible to the author, and
neither is drafting. Requesting or removing a human reviewer is protected
rule 4 everywhere; this skill adds the bot trigger because nothing here owns
the PR's review routing.

## 1. Read before drafting

**Why an existing pending review stops the run.** GitHub keeps one pending
review per user per PR, so the owner's in-progress review and this skill's draft
would be the same object. The original skill added to it; that is right when
the owner asks for it in the session, and wrong when a session nobody watches
does it, because it mixes the owner's half-written comments with a run's. So an
unattended run writes nothing and says why.

**Why a re-review covers only what changed (owner's ruling, 2026-11-06).** A
re-requested review after new commits is a question about those commits. The
last review's commit is the natural base; a force push can remove it from the
head's history, and then the whole diff is the only honest base.

## 2. Draft

**Why no replies into existing threads.** A reply in a pending review publishes
into a conversation when the owner submits, and a question someone asked there
is a decision the owner makes in their own words — the same reason a run never
answers a person's question (protected rule 1). Naming the thread in the summary
leaves the owner both the information and the choice.

**Why the pending review carries no footer.** The footer marks a write nobody
approved. A pending review is visible to no one but its author until they
submit it, and submitting is their approval of what it says, so it is recorded
in `rules/authored-write-form.md`'s table beside the `NEEDS_USER` draft reply:
material for a person, who authors it when they post it.

## 3. Write the pending review

**Why the owner's account, and why the read-back decides it.** A pending review
belongs to the account that created it, and only that account sees or submits
it. A transport that posts as a distinct agent identity would leave a draft the
owner can never find. Identity is established only by observing a write's
author (`rules/posting-identity.md`), so the review is read back and its author
checked; a wrong author is deleted by the id the write returned — the one case
where this run removes a whole review, since it is entirely its own.

**Why a published review is reported, never hidden.** A review whose event was
set by mistake is live, and GitHub's API deletes only a pending review whole
(its *Delete a pending review* endpoint); a quiet retry would leave the owner unaware of what their colleague
saw. The report says what is live so the owner can follow it up.

## Destructive operations

Carried over from the original skill, which learnt it the hard way: the owner
splits comments into pending reviews by hand, and a deleted draft cannot be
recovered. So deletion is by this run's own ids, one at a time, after the
replacement exists.

## Report

**Why this form.** A `conductor` reads many reviewers at once and puts each in
front of the owner as one line: where the drafts are, what to decide, and how
much is blocking. The form gives it exactly that and nothing else, and its
states are only `drafted` and `failed` because a reviewer has no PR of its own
to wait on. The draft text stays on the surface it was written to; the owner
reads it there.

**Why `drafted` waits on the read-back.** The conductor verifies the draft
again before telling the owner (`conductor`, *Reviewers*), but a reviewer that
reports a draft it never saw is the claim that check exists to catch, so the
report is not made until the review was read back.

## Decision scenarios

Pinned in `evals/evals.json`, single-arm on introduction (a baseline for the
next round, since there is no old arm to disagree with):

- the review is written pending, with no event, and the report says `drafted`
  (`a-review-is-left-pending-and-reported`);
- the owner already has a pending review, unattended → nothing written
  (`an-existing-pending-review-stops-an-unattended-run`);
- a re-request after new commits → review since the last review's commit
  (`a-re-request-reviews-only-what-changed`);
- the read-back shows another author → delete by id, `failed`
  (`a-wrong-author-read-back-is-deleted-and-fails`);
- asked to approve if it looks fine → still pending, the recommendation in the
  report (`asked-to-approve-it-still-only-drafts`);
- a question in an existing thread → named in the summary, never answered
  (`a-question-in-a-thread-is-left-to-the-owner`);
- the PR shows no review yet and a bot convention → no trigger, no reviewer
  request (`no-trigger-and-no-reviewer-request`).
