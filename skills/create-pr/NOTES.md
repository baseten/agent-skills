# create-pr — design notes

Companion to `SKILL.md`. That file is the contract; this one holds the reasoning behind its rules, keyed by section. Read a section's note before changing its rules or when applying them to a case the contract doesn't obviously cover. Nothing here overrides the contract.

## Coverage findings and linkage form

A closing keyword is a **claim** that merging this PR completes the issue, and GitHub acts on that claim whether or not it is true. A PR shipping against a coverage finding — a declared dependency satisfied on paper (closed, merged, correctly linked) whose capability turned out absent, leaving acceptance criteria stubbed, disabled, or omitted — would, under a closing keyword, auto-close an issue nobody finished. The tracker then reads complete over work that was never done, and the gap survives only in a PR body nobody re-reads. Half-finished work must not reach a terminal state by default.

The non-closing form is the *same test* as the general linkage rule, read the other way: "`Part of:` alone is insufficient when the implementation issue should auto-close on merge" — and a coverage-finding PR's issue **should not** auto-close, because it is not finished. Reporting which form was emitted matters because the caller reconciles completion against it rather than assuming a close.

Scope this narrowly: it applies to a **recorded** coverage finding, never to a PR whose author merely feels uncertain — otherwise every hesitant worker degrades its linkage and nothing auto-closes anymore.

On Linear and other trackers, the same rule holds through a different mechanism (do not apply the workspace's completion automation), and where you cannot tell whether the integration transitions the issue on merge, saying so beats assuming it will not.

## Automated review trigger

The rule and its reasoning — the convention, documentation-review routing, the trigger comment's account and footer, and when review is triggered again — moved to `rules/review-trigger.md` and `rules/review-trigger-notes.md` (#142), because `backlog-orchestrator`, `implement-issue` and `npm-dependency-upgrade-orchestrator` issue triggers under it too, and the last of them on PRs that never pass through this skill. What stays here is what only this skill does: the first trigger after creation, and the deferred trigger a caller can request.

**Why the Output forwards the routed skill's result whole.** On a documentation-only routed PR no trigger comment is posted, so the comment-kind identity evidence this skill's Output otherwise supplies has no source — and the routed skill posts the comment that would have supplied it. Summarizing its result away also breaks the producer→recorder chain into `summarize-wave`, which is where its findings become action points and reach the merge gate at all.

## The PR body's brevity

The brevity rule lives in `references/authored-write-form.md`; what is local here is which of this skill's elements survive it. All of them do — the linkage line, `Depends on:`, and the `Part of:`/`Blocked by:` pair with its unmet-criteria section — and they have to be named rather than left to inference, because each exists to prevent a specific failure a shorter body would reintroduce: an orphan PR, a lost stack edge, an issue auto-closed over work nobody finished. The elements that brevity is actually aimed at are the ones nothing requires: the implementation narrative, the restated issue, the log of what was tried.

## Why the body's footer is mode-dependent, and why this skill is where it splits

Every other deferral site makes writes of one kind: a repair pass's replies are never read before posting, a walkthrough's rulings always are. This skill is the only one that authors the same artifact both ways — a PR body opened by a dispatched worker, which nobody has read, and a PR body this skill showed to the user and created after their confirmation or edit, which its author owns. So the approval test is not a formality to forward here; it is a real branch, and the confirmation step under *Creating and verifying the PR* is exactly the evidence that decides it. Where the run cannot say the user read the body, the answer is No.

## Why the output reports identities per write kind, even under one (transport, credential) pair

The PR's creation and the trigger comment are distinct write kinds a platform may author differently under the same pair — an app-scoped token attributes most endpoints to the user and some to the app. A merged single answer would overwrite one observation with the other, and the trigger comment's entry is the only comment-kind evidence the caller's next trigger selection can use. Filed under a composite key but reporting only the transport, an entry cannot be merged into the caller's map at all. The invoking-user entries are reported too because they are exactly what trigger selection needs — a single-valued output would force the caller to lose either the distinct path for later writes or the invoking-user path for later triggers.

## Why the as-created draft state is reported

No supervising workflow promotes a draft on its own judgement (`rules/draft-state.md` owns that rule, including where a repository's own convention instructs promotion), but each tracks as-created beside current state, and the held-draft and publish-as-step-of-merging rules need the distinction this field carries: a workflow cannot tell a PR this run drafted from one a human drafted unless this skill says so. This skill itself ends at creation and never changes draft state.

## Substantive vs mechanical pushes

The test and its reasoning moved to `rules/mechanical-pushes.md` and `rules/mechanical-pushes-notes.md` (#140), because `review-docs` applies it too and pointed up into this skill for it. The re-trigger rule that applied it here moved to `rules/review-trigger.md` (#142), which cites the test; this skill now carries it only through that rule.

## Why an unlinkable PR stops rather than ships

An implementation PR that cannot be linked to an exact issue would be an orphan the recovery and completion machinery cannot see — restart logic, completion semantics, and coverage reconciliation all key on the linkage. The ad-hoc exception exists only for directly-invoked PRs after the user confirms there is no issue.

## Before creating the PR

**Why the claim check is applied here and not left to the bundled reference (round 12, Sept 2026):** a reference sitting in a skill directory and cited nowhere near the write is a reference nobody reads. This skill composes the two artifacts every reviewer and the owner read first, in one step, under one confirmation — so the check is stated at that step. The **title** is included on purpose: it is composed in the same breath as the body and shown for the same confirmation, and a claim moved into it would otherwise escape by getting shorter.

**Why the verification goes in the output rather than in the body:** the write-form rule keeps the audit trail out of the body, correctly, which means a read performed here leaves no trace anywhere unless the output carries it. Without that field the caller either repeats the read or trusts the claim, and the rule's own requirement — say so where you verified what you could have assumed — has nowhere to land.

**Why this skill derives the gate the same way rather than reading the
documentation list (round 1, Sept 2026):** a directly-invoked `create-pr`, or one
whose caller omitted the gate, would otherwise build a gate report from
`CLAUDE.md`/`AGENTS.md` — complete against a list that describes the gate and
drifts from it. A report complete against the wrong source is worse than none:
it reads as evidence that the gate ran. (That report was a body table until
issue #158 moved it to the output: `rules/authored-write-form-notes.md`.)

**Why the derivation sits before the body and not in `# Output` (round 2):** it
was first written where the gate report is described, which is after the checks have
run, the body has been drafted and the PR has been created. A direct invocation
therefore ran the documentation list, created the PR, and only then met the rule
saying not to — so the rule was unreachable by the path it existed for. A
derivation that decides what to run belongs where running is decided.
