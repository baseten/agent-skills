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

**Why two guards on that column were still green over it (same round, historical):** both matched a phrase whole-file, and the phrase also appeared in a downstream summary, so mutating the decision point left them green. Those prose-grep guards have since been removed; see the repository README, *Checks*. The lesson that survives: presence in a file is not presence where the rule is read.

**Why the item's field list lives in one place (round two, Sept 2026):** the first version of the ruling stated the five fields at the emitting site and then enumerated them again at four consumers. Within one review round three of those copies had dropped a field and a fourth had dropped two — the walkthrough lost *why it was not posted*, which is the field its own next sentence branches on. That is the summary case `CLAUDE.md` says to collapse rather than reconcile, and it is worth naming here because the enumerations all looked like helpful precision. They are now pointers; the list has one home. The evals drifted the same way from the same cause, which is the tell that it was the shape and not four separate slips.

**Why a question item has required contents (Sept 2026):** the reason the answer is not posted is so that a person can post it. An item that makes them hunt defeats the rule it implements — they open the PR, find the thread, re-read the ask, reconstruct what the pass already knew, and the cost of escalating exceeds the cost of a wrong autonomous answer, which is how a rule like this gets quietly abandoned. Hence five fields and no partial credit: four of five is not four-fifths useful, because the missing one is the one they go looking for.

## Apply the fix(es)

**Why the other readers of a value count as mentioned:** "minimal change, nothing not mentioned" is right for a comment about one surface and wrong for a comment about what a value means, where fixing the named reader alone turns readers that were wrong together into readers that disagree — one PR took five rounds that way, and the fourth round's defect, an expired alert that could still be submitted, was caused by the first round's fix. The scope is bounded to readers the fix changes, so it does not turn a one-line repair into an audit. The full incident is in `repair-pr`'s NOTES, *Hard constraints*, which also says why every repair type takes this rule.

**Why the reply may carry the method:** the one-line reply otherwise states a result — *fixed* — that invites agreement. Naming how the readers were found gives the reviewer something to attack, and the reader missed in that incident was reached through a derived prop the grep did not name.

## 2. One commit per thread

**Why one commit per thread replaced rolling mechanical comments together (#174, owner's ruling 2026-10-01):** a held reply is approved against the commit it names. A shared commit would put several reviewers' changes behind one SHA and ask the owner to approve, for one person, a reply pointing at someone else's change too. A commit per thread costs a few more commits on the branch and makes every reply's SHA mean exactly that thread's fix. An explicit "one commit" from the user still wins: they have chosen the trade themselves.

## Replies held for approval

**Why the reply waits and the fix does not (#174, owner's ruling 2026-10-01):** the kind test is author-blind on purpose, and that is right for the fix. It was wrong for what follows it. The reply goes out under the owner's account to a person, and resolving the thread tells that person the owner considered their point and is done with it. Neither is the run's to say unread. A thread only bots are in has nobody waiting to be told, so it keeps today's path. `auto-resolve-comments: true` restores today's path for people too, for a repository whose owner wants it.

**Why this is not the removed `auto-fix-reviewers` gate:** that key decided what was *fixed* by who wrote the comment, and erred both ways. Here authorship decides nothing about the fix — a person's nit is still repaired and pushed in the same pass — only whether the reply and the resolution wait.

**Why `user.type == "Bot"` and not a login list:** it is a property the forge sets for GitHub Apps and bot accounts, so it needs no allowlist to drift. A machine user posting from an ordinary account reads as human, and that direction only holds a reply. Checked on 2026-10-01 against an automated reviewer's root comment on a public PR of this repository: the REST review comment returned `user.type: "Bot"` for the `[bot]` login, and the GraphQL `reviewThreads` query returned `author { __typename }` as `Bot` for the same comment, while the owner's replies returned `User`. Step 1's query selects `__typename` for that reason.

**Why any person in the thread, not the root author (blind audit of #175):** the root author is the wrong comment to test. A person following up inside a bot's thread is the one being answered, and a bot following up in a thread a person is in is still answering to them. Testing every comment is the simplest rule that gets both right, and it errs only towards holding.

**Why an already-fixed thread is held again, never reserved (blind audit of #175):** a restart loses the record of a held reply but not the pushed fix. Read with a spent budget, the thread would come back as a deferred repair — a `NEEDS_USER` item holding the whole wave over work that is done. Checking the head first turns it back into what it was: a reply waiting for approval.

**Why a held reply is not a `NEEDS_USER` item:** nothing is undecided — the fix is pushed and the text is one line. Made a `NEEDS_USER` item, it would hold every PR in a wave through the gate's wave-wide condition. As an open thread it holds only its own PR, through the clean-review condition.

**How it meets a mixed thread (owner's ruling, #174; ordering from the blind audit of #175):** the question stays reserved, the work-done reply is held like any other, and the thread is resolved only once both are settled. The held reply is never offered while the question is reserved, because a footerless approved reply in a reserved thread reads as the owner's answer to it. This skill returns before the reservation can end, so it offers nothing there.
