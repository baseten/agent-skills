# Review feedback

This is the rule other skills mean when they cite *review feedback*: what a run may auto-fix, what counts as feedback at all, which threads are reserved for the owner, and which a supervising run still has to dispatch. It is a shared rule, not a skill: held once at `rules/review-feedback.md` and copied into each applying skill's `references/review-feedback.md` by `scripts/refresh_shared_rules.sh`. Edit the source, never a copy; check_shared_rules.py fails if a generated copy diverges.

## What may be auto-fixed

**Decided by what the comment asks for, never by who wrote it.** No bot test and no reviewer allowlist enters it: a human reviewer's typo fix is repaired, an automated reviewer's architecture question is escalated.

| the thread asks for | kind | the run |
|---|---|---|
| a code change this pass can make and verify — a rename, a missing guard, an off-by-one, a test, a lint fix, a bounded refactor the comment itself specifies | **repairable** | fixes it |
| anything answering it requires other than a code change, whose correct response is prose rather than a diff — a question about intent, a design or product judgment, a request for rationale, an objection needing a decision | **`NEEDS_USER`** | escalates it (*Reserved for the owner*) |

**Authorship decides one later thing, and never this one**: whether the reply to a repaired thread, and its resolution, wait for the owner's approval (`resolve-pr-comment`, *Replies held for approval*). That is not the removed `auto-fix-reviewers` gate — what is fixed stays this test's alone.

## The thread-root test

**A review thread's root comment is feedback; a timeline comment is conversation.** A thread whose root someone wrote is feedback on the diff, classified by the kind test above; a comment on the PR's conversation timeline (a GitHub issue comment) is not feedback to act on. The test is **thread-rootness**, not "is it a review comment": a reply inside a thread is also a review comment, and the run posts replies constantly, so the weaker test would qualify its own replies. The invoking user's own rooted thread is feedback like any other, classified by the same kind test — their instruction directs the run, and a question they root is still a question, answered by them rather than guessed at. **This test is not part of the removed reviewer policy** (the deleted `auto-fix-reviewers` key, which gated auto-fixing on the author) and must not be removed with it.

**The run never opens a review thread on a PR it is driving.** It posts timeline comments and replies into existing threads; it never roots one. Wherever no distinct posting identity is available the run posts as the invoking user's own account (the *posting identity* shared rule — that degraded path is the common case), so a run-authored root would be indistinguishable from an instruction and the test above would silently break. The prohibition keeps the discriminator true by construction.

**That comments this run authored are never reviewer feedback follows from those two rules; it is not a mechanism of its own.** Every review comment the run posts is a reply, which roots nothing, and every timeline comment it posts — worker reports, repair replies, trigger comments — is conversation by kind. No author test could provide this: on the degraded path the run's comments carry the invoking user's login and `author_association: OWNER`. **Nor may the attribution footer be tested for** (`references/authored-write-form.md`): it goes only on writes nobody read, so every attended write legitimately carries none. **Do not restate the carve-out as a parallel rule anywhere** — it holds exactly as long as the root test and the no-new-threads rule hold. It also survives a restart, since thread structure and comment kind are durable forge state.

## Reserved for the owner

**A `NEEDS_USER` thread is reserved for the owner**: never resolved and never answered on the run's own authority, and never auto-fixed **for the part that wants an answer**. A comment asking for a diff *and* prose is repaired and still reserved — its fix pushed, its thread left open (`resolve-pr-comment`, *A comment can want both*): what is reserved is the question, and a pushed fix never stands in for one. The question is put to the owner rather than guessed at.

The reservation binds every skill that classifies, repairs or answers a thread. **The classification is made where the thread body is read** — `resolve-pr-comment` owns it, `repair-pr` propagates the items, and the supervising run (`supervise-prs`, and the orchestrator that runs it) reports and gates on them. What this section says about the checkpoint output, settle, invariant 12's clean-review condition and invariant 1 is that supervising run's obligation; a skill it invokes (`resolve-pr-comment`, `repair-pr`, `review-docs`) returns the items and leaves the reporting and the gate to it.

**A reserved thread is reported in the checkpoint output** with the thread's URL, its root author, what it asks, and what its item kind carries:

| item | carries | at settle |
|---|---|---|
| **question** | **everything `resolve-pr-comment`, *What a question item must contain*, requires** — that section owns the list — carried through verbatim, the `html_url` forwarded as a string and never rebuilt. **Recording all but one of them is recording none**: the missing one is the one the owner goes hunting for | `settle-outstanding-decisions` puts it to the owner as an intent question, answerable in one question because of the draft |
| **deferred repair** | the change it asks for, and **no draft** (`repair-pr`): a thread wanting a diff has nothing to answer, and a draft demanded of it could only be invented | **not** consumed by the walkthrough, whose bar takes choices rather than work (`settle-outstanding-decisions`, *What qualifies as an outstanding decision*); reported for the owner to apply themselves or to lift the budget on, never as something the walkthrough will clear |

**A reserved thread does not block settlement** — the run cannot be required to resolve what only a person can answer — **but it is an unresolved actionable finding everywhere else**: it fails invariant 12's clean-review condition, so the gate does not open over it, and it is a `NEEDS_USER` item outstanding, which that gate independently refuses. Both conditions name the same threads.

**A reservation is run state: it does not survive the run.** The supervising run's record is a cache; a later invocation holds no reservation, re-classifies the thread from the forge, and repairs it where it now has budget — which is what makes *lift the budget* actionable. **Within a run it ends in one of two ways, read from the forge when the gate is evaluated:**

| ends it | how |
|---|---|
| the thread is **resolved** | by the owner, or by the review workflow where a reviewer's follow-up superseded the question and the re-classified thread wanted only a diff |
| an **answer is recorded** on it, **and** any code change it implies has been pushed by the `finding` repair its row routes to | a walkthrough ruling (`settle-outstanding-decisions`, *Recording the ruling*) or **the owner's own reply in the thread — the already-ruled test treats them alike** (*What qualifies as an outstanding decision*); counting only the ruling would hold the gate over an owner who simply answered the reviewer |

**A rejected-draft record ends nothing.** Ending a reservation does not make the thread unhandled — a settlement record is not new content — so nothing re-dispatches it.

## Approval-pending replies

**A repaired thread whose reply is held for approval** (`resolve-pr-comment`, *Replies held for approval*) has its fix pushed and its reply unposted. It is reported in the checkpoint output with what its item carries, and:

- **it is handled** (*Unhandled feedback*), so it is not re-dispatched while it waits;
- **it is not clean**: open, it fails invariant 12's clean-review condition, as any unresolved actionable thread does;
- **it does not block settlement**, exactly as a reserved thread does not: `settle-outstanding-decisions` is where it is put to the owner.

**It ends** when the run posts the owner's approved reply — the thread then resolved at once; in a thread with a reserved question that waits until the reservation has ended (`resolve-pr-comment`, *A comment can want both*) — or when the thread is resolved, or when **the owner replies in the thread themselves after the fix**, which ends it with nothing posted and nothing resolved, and is reported. That reply is ordinary new content (*Unhandled feedback*): the thread is re-admitted and re-classified, so a "thanks" is no-action and a change request is repaired. **Every post of an approved held reply re-reads the thread first** and posts nothing where a comment newer than the fix exists that this workflow did not write (`resolve-pr-comment`, *Replies held for approval*). **A rejection ends nothing, and is remembered for the run**: recorded in run state, it is not asked again in the same run unless new content has arrived on the thread since; it still holds the gate and is still listed at the end. **A thread whose requested change is already on the head is never fixed again**, in any mode and whatever the budget: it is held again — unless the owner has replied since that change, which ended the hold — never a deferred repair or a budget `NEEDS_USER` item (`resolve-pr-comment`, *Replies held for approval*).

**A held reply does not outlive the run.** It is run state: when the run ends, an unposted held reply's text is dropped, and the thread stays open with its fix pushed. No later invocation recovers that text. A later invocation that re-dispatches the open thread finds the change already on the head and composes a fresh held reply, as above. So the run's final report and checkpoint output list every held reply not yet posted — the thread URL, the fix SHA and the one-line text — and the owner can post it themselves.

Nothing here replaces the repository's review *trigger* convention, which the *review trigger* shared rule owns: triggering a reviewer and acting on its findings are separate concerns.

## Unhandled feedback

**Review feedback is unhandled when all of these hold:**

- the thread roots on the diff;
- the supervising run did not author it (a consequence of the thread-root test);
- **it is still unresolved** — a thread the run repaired and resolved is handled by being resolved;
- it is not already recorded as **handled — reserved, no-action or approval-pending — unless new content has arrived on it since**.

**Each of these marks a thread handled**: a reserved one awaits the owner, a no-action one wants nothing from anybody, an approval-pending one awaits the owner's approval of a reply. A predicate recording only reserved threads re-dispatches every acknowledgement on every cycle without bound, since a classify-only pass consumes no cycle; one omitting resolution re-groups every thread the run just fixed.

**New content means a write this workflow did not author.** A reviewer's follow-up re-opens the thread; a settlement record does not — an approved answer, a recorded choice, a rejected-draft record or an approved held reply posted by `settle-outstanding-decisions` is this workflow answering it. Treating one as new content would re-admit the thread, re-classify the answered question and re-offer the rejected draft, all while holding the merge gate. It is the thread-root test's carve-out applied to re-admission. **The exception belongs in this predicate, not only in the step that records a pass's returned threads**: a reviewer following up inside a reserved thread with a concrete change request has made it unhandled again, and a predicate that excludes the thread on its root's old classification never reaches the step that would re-admit it. Author identity decides nothing (*What may be auto-fixed*).

**The supervising run dispatches on any such round, including one where nothing looks repairable from the outside.** A reserved thread is never dispatched *for repair* — but reserving is a conclusion, not a precondition: classification and the draft reply need the thread body and the code around it, which is the dispatched pass's context. A run that triaged a round as question-only and skipped dispatch would reserve it with no draft.
