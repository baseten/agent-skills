# create-pr — design notes

Companion to `SKILL.md`. That file is the contract; this one holds the reasoning behind its rules, keyed by section. Read a section's note before changing its rules or when applying them to a case the contract doesn't obviously cover. Nothing here overrides the contract.

## Coverage findings and linkage form

A closing keyword is a **claim** that merging this PR completes the issue, and GitHub acts on that claim whether or not it is true. A PR shipping against a coverage finding — a declared dependency satisfied on paper (closed, merged, correctly linked) whose capability turned out absent, leaving acceptance criteria stubbed, disabled, or omitted — would, under a closing keyword, auto-close an issue nobody finished. The tracker then reads complete over work that was never done, and the gap survives only in a PR body nobody re-reads. Half-finished work must not reach a terminal state by default.

The non-closing form is the *same test* as the general linkage rule, read the other way: "`Part of:` alone is insufficient when the implementation issue should auto-close on merge" — and a coverage-finding PR's issue **should not** auto-close, because it is not finished. Reporting which form was emitted matters because the caller reconciles completion against it rather than assuming a close.

Scope this narrowly: it applies to a **recorded** coverage finding, never to a PR whose author merely feels uncertain — otherwise every hesitant worker degrades its linkage and nothing auto-closes anymore.

On Linear and other trackers, the same rule holds through a different mechanism (do not apply the workspace's completion automation), and where you cannot tell whether the integration transitions the issue on merge, saying so beats assuming it will not.

## The review trigger's authorship

The trigger comment is the one post exempted from the posting-identity rule because there its authorship is **functional, not cosmetic**: authored by anything but the invoking user, the repository's review convention silently does not fire — nothing refuses it, so the run waits out a review that was never going to arrive. `backlog-orchestrator`, *Posting identity*, states the rule once, including the bootstrap for a fresh run's first trigger; this skill carries only the exception, not a restatement.

## The PR body's brevity, and the trigger's second exemption

The brevity rule lives in `backlog-orchestrator`, *Authored write form*; what is local here is which of this skill's elements survive it. All of them do — the linkage line, `Depends on:`, and the `Part of:`/`Blocked by:` pair with its unmet-criteria section — and they have to be named rather than left to inference, because each exists to prevent a specific failure a shorter body would reintroduce: an orphan PR, a lost stack edge, an issue auto-closed over work nobody finished. The elements that brevity is actually aimed at are the ones nothing requires: the implementation narrative, the restated issue, the log of what was tried.

The trigger comment's exemption from the footer is the same argument as its exemption from the posting-identity rule, one section up: the comment must match what the convention matches on, and a convention that does not fire fails silently. Two exemptions, one cause — which is why the contract states them in one bullet rather than two.

Under the approval test that now governs the footer (`backlog-orchestrator`, *Authored write form*), the trigger has **two** independent reasons to carry none, and only one of them is worth stating. The functional one — it must read exactly as the convention expects — is the one that fails silently and the one a reader has to know. The approval test on its own would ask for a footer here, since nobody reads a trigger comment before it is posted; the exemption overrides it. Stating both would invite someone to satisfy the weaker reason and think the rule met.

## Why the body's footer is mode-dependent, and why this skill is where it splits

Every other deferral site makes writes of one kind: a repair pass's replies are never read before posting, a walkthrough's rulings always are. This skill is the only one that authors the same artifact both ways — a PR body opened by a dispatched worker, which nobody has read, and a PR body this skill showed to the user and created after their confirmation or edit, which its author owns. So the approval test is not a formality to forward here; it is a real branch, and the confirmation step under *Creating and verifying the PR* is exactly the evidence that decides it. Where the run cannot say the user read the body, the answer is No.

## Why the output reports identities per write kind, even under one (transport, credential) pair

The PR's creation and the trigger comment are distinct write kinds a platform may author differently under the same pair — an app-scoped token attributes most endpoints to the user and some to the app. A merged single answer would overwrite one observation with the other, and the trigger comment's entry is the only comment-kind evidence the caller's next trigger selection can use. Filed under a composite key but reporting only the transport, an entry cannot be merged into the caller's map at all. The invoking-user entries are reported too because they are exactly what trigger selection needs — a single-valued output would force the caller to lose either the distinct path for later writes or the invoking-user path for later triggers.

## Why the as-created draft state is reported

No supervising workflow promotes a draft (`backlog-orchestrator`, *Draft state*, owns that rule), but each tracks as-created beside current state, and the held-draft and publish-as-step-of-merging rules need the distinction this field carries: a workflow cannot tell a PR this run drafted from one a human drafted unless this skill says so. This skill itself ends at creation and never changes draft state.

## Substantive vs mechanical pushes

The re-trigger split exists because restacks and renumbers happen for reasons unrelated to a PR's own diff — most often right after a sibling merges — and re-reviewing every one spends review budget on code that did not change. The hazard is that a *botched* renumber is indistinguishable in the diff from a correct one while changing whether the artifact runs at all: a migration whose identity fields went stale in a hand-rename is **silently skipped** — it compiles, CI is green, and the schema change never happens. That is why "passes the checks" means **verified to apply** (regenerate through the repository's own generator, then exercise the artifact's apply path), why an unverified renumber is substantive, and why a repository with no deterministic check that would catch a bad renumber gets no mechanical exemption at all.

The split governs what the workflow itself triggers, not what the review provider does on its own events (e.g. re-reviewing when a draft is marked ready) — provider behavior is neither a reason to suppress a due trigger nor to issue one that is not due.

## Why an unlinkable PR stops rather than ships

An implementation PR that cannot be linked to an exact issue would be an orphan the recovery and completion machinery cannot see — restart logic, completion semantics, and coverage reconciliation all key on the linkage. The ad-hoc exception exists only for directly-invoked PRs after the user confirms there is no issue.
