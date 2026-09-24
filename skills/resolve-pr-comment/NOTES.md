# NOTES — resolve-pr-comment

Reasoning for `SKILL.md`, keyed by its section names. This file explains; it
never overrides.

## Handling queries

**Why the check covers the escalation draft and the commit message, not just the reply (round 12, Sept 2026):** the one-line work-done reply rarely has room for a claim about the codebase, so a rule aimed only at it would almost never fire. The drafts this skill composes are where claims actually live, and they are read by the owner as the basis for a decision. The commit message is the other one: the most durable thing written here and the one nobody re-reads, so a wrong account of why a change is safe outlives every thread on the PR.

**Why the verification is returned:** the reply carries the claim and never the audit trail, so the output is the only durable record that a read happened. Without it a supervising or later session cannot tell the observation from the recollection.

These four notes moved here from `rules/authored-write-form-notes.md` when the
write-form rule was extracted. They explain the question item, whose contract
lives in this skill — *What a question item must contain* — and not the shared
write-form rule, which never mentions it. A note beside the wrong contract is
one the next editor of that contract will not find.

**Why a decision-only draft is not paste-ready, and why saying so took a whole column (Codex round, Sept 2026):** the item's third field said *"the recommended reply, paste-ready"*, and the attended path said the person may send it. Both are true of an answerable-from-work draft and false of a decision-only one, which deliberately lists options and costs and **makes no pick** — `settle-outstanding-decisions` already stated that *"approve the draft" would record a ruling that chose nothing*. So the branch told a person they could post a non-answer into a review thread, and the thread would then read as handled with the question still undecided, bypassing the one flow built to settle it. The two draft kinds had been split with care where the draft is *produced* and then silently collapsed everywhere the draft is *used* — six sites, which is why this was walked as an axis rather than patched at the line Codex flagged.

**Why two guards on that column were still green over it (same round):** both matched whole-file, and both phrases appear twice — once at the decision point and once in a downstream summary. Mutating the decision point left the summary, and the assertion passed. Scoping them with `clause()` and `near()` is the fix, and it is the same lesson the guard battery's own docstring records from rounds 29-33: presence in a file is not presence where the rule is read.

**Why the item's field list lives in one place (round two, Sept 2026):** the first version of the ruling stated the five fields at the emitting site and then enumerated them again at four consumers. Within one review round three of those copies had dropped a field and a fourth had dropped two — the walkthrough lost *why it was not posted*, which is the field its own next sentence branches on. That is the summary case `CLAUDE.md` says to collapse rather than reconcile, and it is worth naming here because the enumerations all looked like helpful precision. They are now pointers; the list has one home. The evals drifted the same way from the same cause, which is the tell that it was the shape and not four separate slips.

**Why a question item has required contents (Sept 2026):** the reason the answer is not posted is so that a person can post it. An item that makes them hunt defeats the rule it implements — they open the PR, find the thread, re-read the ask, reconstruct what the pass already knew, and the cost of escalating exceeds the cost of a wrong autonomous answer, which is how a rule like this gets quietly abandoned. Hence five fields and no partial credit: four of five is not four-fifths useful, because the missing one is the one they go looking for.

## Apply the fix(es)

**Why the other readers of a value count as mentioned:** "minimal change, nothing not mentioned" is right for a comment about one surface and wrong for a comment about what a value means, where fixing the named reader alone turns readers that were wrong together into readers that disagree — one PR took five rounds that way, and the fourth round's defect, an expired alert that could still be submitted, was caused by the first round's fix. The scope is bounded to readers the fix changes, so it does not turn a one-line repair into an audit. The full incident is in `repair-pr`'s NOTES, *Hard constraints*, which also says why every repair type takes this rule.

**Why the reply may carry the method:** the one-line reply otherwise states a result — *fixed* — that invites agreement. Naming how the readers were found gives the reviewer something to attack, and the reader missed in that incident was reached through a derived prop the grep did not name.
