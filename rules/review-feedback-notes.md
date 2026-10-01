# Notes — review-feedback

Reasoning for `rules/review-feedback.md`. Deliberately *not* bundled into
each skill: a copy of this per consumer would be design history with no reader,
and the audience for it is a person editing the rule, who has this checkout.

Moved here with the rule itself, from `backlog-orchestrator/NOTES.md`, where it
was reasoning about a section that no longer lives there.

**Why the kind test stays author-blind, including for the escalation (confirmed by the owner, Sept 2026):** the rule reads the same for a bot's question as for a human's — a thread needing intent, design, rationale or a decision is `NEEDS_USER`, reserved, and answered by nobody but the owner. This is worth writing down because it looks like an oversight and invites a "fix" back to an author-keyed rule, and that fix has already been made and reverted once here. Three reasons it is deliberate:

- **The two directions of error are symmetric and both were observed.** Automated reviewers raise architecture questions no run should answer; human reviewers file one-line nits any run can fix. An author key errs on both at once, which is why `auto-fix-reviewers` was deleted rather than re-defaulted (`rules/agent-policy-notes.md`, on why there is no reviewer-identity option).
- **Whose voice the reply would be in does not depend on who asked.** The escalation exists because an answer composed by a pass arrives as the owner's position (`resolve-pr-comment`, *Handling queries*). That is true in a bot's thread as much as a person's: the bot's thread is read by the humans reviewing the PR, and a confident wrong answer to a review bot is a confident wrong answer on the record.
- **Author is not reliably knowable anyway.** A bot posting through an integration, a human using a bot account, an account that changes hands — the test would key on the least stable field available, and `rules/posting-identity.md` already documents that authorship reads differently per transport.

The owner asked for the rule scoped to human comments and, when the asymmetry was put to them, confirmed author-blind. Do not narrow it without a new ruling.

**Why this rule names the posting-identity rule path-neutrally (#168):** it names that rule to say why the no-new-threads prohibition is needed — the degraded path — not because a skill applying this rule must select an author to do so. Cited as a `references/` path, it was copied into every skill carrying this one. Every consumer of this rule that makes an authored write declares the posting-identity rule itself — `summarize-wave` included, since the owner's ruling on #168. The citation of the write-form rule stays a path: a skill acting on the thread-root carve-out reads there what the footer marks, which is why nothing may test for it.

## Unhandled feedback

**Why the unhandled-feedback predicate moved here (#140):** it was stated in full in `backlog-orchestrator`, *CI/review repair*, and `implement-issue` applied it too — restating the predicate in condensed form and pointing up into `backlog-orchestrator` for the rest ("states the rule"), an orchestrator it never runs under. Both supervising runs apply it on every supervision cycle, and it is the thread-root test's carve-out applied to re-admission, so it belongs beside that test. The text moved verbatim except for role nouns and self-citations: "this run" and "the parent" became "the supervising run", "step 5's mechanism sentence" became the step that records a pass's returned threads (each consumer numbers its steps differently), and citations of `references/review-feedback.md` became in-file section references.

## What may be auto-fixed

**Moved from the rule (#168):** author identity predicts the kind of comment only loosely — automated reviewers ask design questions and humans file one-line nits — so gating on it reserved work the run could safely do while admitting work it could not. The first entry in this file gives the owner's ruling.

## The thread-root test

**Moved from the rule (#168):** nothing today makes the run want to root a thread, which is exactly why the prohibition must be a stated rule rather than an observed habit. The restart property matters because an author-side carve-out would have to fall back to recognizing the run's own report and reply forms once the predecessor's record of its own writes is gone; thread structure and comment kind need no such record.

## Reserved for the owner

**Moved from the rule (#168):** both gate conditions — invariant 12's clean-review condition and the outstanding `NEEDS_USER` item — name the same threads, which is why removing the reviewer policy did not loosen the gate. The two ways a reservation ends exist because without them the gate reads a thread as reserved after the owner has answered it: the deadlock the carve-out exists to prevent, one step later. Counting the owner's own reply alongside a walkthrough ruling covers the commonest case, an owner who simply answers the reviewer, which leaves the walkthrough nothing to ask and nothing else to clear it.

**Also moved from the rule (#168):** the thread-root test survives independently of the kind test; the carve-out would drift the moment it were maintained separately; a question item carries every field so the owner posts the reply from the checkpoint without opening anything; and skipping dispatch on a question-only round reserves the thread with no draft, the one outcome the reservation exists to avoid.

## Approval-pending replies

**Why a held reply is handled but not clean (#174, owner's ruling 2026-10-01):** handled, because otherwise the supervisor would see an unresolved thread on every cycle and redispatch a fix that is already pushed. Not clean, because the reviewer has not been told, and the thread is still open; merging over it would merge past a person who has not seen their point answered. Like a reserved thread it does not block settlement: settlement is where it gets put to the owner.

**Why the approved reply is not new content:** the walkthrough posting it is this workflow's own write, exactly as a ruling is. Treating it as new content would re-admit the thread it has just finished.

**Why a held reply does not outlive the run (owner's ruling on the blind audit of #175):** making the hold durable would need a trailer on every fix commit and a forge-derived definition every consumer reads. The owner declined that: a dropped hold costs one unposted line, and the fix is already pushed. So the run lists every held reply it did not post, with its text, and the owner posts it if they want to. Nothing claims a later walkthrough can find it.

**Why `auto-resolve-comments` turns on only from the repository (blind audit of #175):** `true` posts under the owner's name in a thread a person is in with nobody having read the reply. That is the same kind of grant as a merge permission, so it takes the same exemption.

**Why the held-reply rules are this simple (owner's ruling after the third blind audit of #175):** three audit rounds each found a dead end in a special case: a rejection memory, a re-read that blocked an approved post, an owner-reply exemption, and an ordering for threads that also asked a question. Each fix added another case with its own edge. The owner chose a flow with none. A held reply is asked once, with the thread's newer comments shown. Approved, it posts; otherwise it is listed for the owner. Any new comment is ordinary new content. A thread that also asks a question never gets a held reply at all.

**Why a rejection is a handled kind keyed by fix SHA (fourth blind audit of #175):** passing a filtered set down to each consumer left every consumer to repeat the filter, and a settle that ran twice lost the rejection. Recorded once in the supervising run's record, it survives repeated settles and needs no memory anywhere else. Keying it by the fix SHA means a newer fix is plainly a new reply to ask.

**Why a comment landing between the ask and the approval is resolved over (fourth blind audit of #175):** the owner is shown the thread's newer comments when asked, not again after answering. One posted in the gap is not shown, and approval resolves the thread over it. That is accepted: blocking the post on it is the re-read the simpler design removed, and it left an approved reply nowhere to go.

**Why only held-reply records replace each other (fifth blind audit of #175):** a blanket "one record per thread" let a later "thanks" replace a reserved question, and it collided with threads that carry two items. Replacement is scoped to the held-reply records, and a reservation keeps its own endings.

**Why the run no longer resolves a reserved thread on a superseding follow-up (seventh blind audit of #175):** main let the review workflow resolve a reserved thread when it judged a reviewer's follow-up had superseded the question. That is the run reading a person's comment as an answer. With no run allowed to resolve a reserved thread, that ending was unreachable, and an author's withdrawal deadlocked. This narrows main deliberately, toward the owner: a follow-up is classified alongside the question, and the reservation ends when the owner records an answer, *withdrawn* included.

**Why an approved reply posts but does not resolve over a newer comment (seventh blind audit of #175):** the owner approves against the comments shown at ask time. A newer comment that nobody classified would be closed unread by the resolve. Posting keeps the approved text; leaving the thread open lets supervision classify the newcomer.
