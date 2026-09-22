# Notes — prose review round budget

Reasoning for `rules/prose-review-round-budget.md`. Explains; never overrides.

**Why a ceiling and not a stopping condition.** Every other terminator in this
repository is a condition someone can evaluate — a check passes, a budget of
repair cycles is spent, a gate opens. Prose has no condition of that shape,
because the question a reviewer asks is *is there anything left to say* and the
honest answer is always yes. Nine rounds and 28 threads on one document is what
that looks like in practice, and the document was not materially better after
round four. So the terminator has to be a number fixed before the review starts,
which is the one thing a grinding reviewer cannot argue with.

**Why it is not a policy key.** Every other budget here is configurable, and this
one deliberately is not, for a reason that is about who would turn the dial: the
run that has spent nine rounds is exactly the run that concludes it needs a
tenth. A ceiling that the thing being ceilinged can raise is a suggestion.

**Why the count lives on the pull request.** A count in run state is laundered by
a restart, and restarts are ordinary — a container dies, a worker is redispatched,
a person picks the PR up by hand. Reading it off the reviewer's own comments makes
the count survive all three, and makes it auditable by anyone looking at the PR.

**Why round 2 may still raise two things.** Both are the same case: a repair that
produced the failure the reviewer exists for. A budget that forbade even this
would ship the defect it was built to catch, having spent a round confirming it
was introduced. The exception is narrow on purpose — reported inside the finding
whose fix created it, earning no extra round — because a reviewer that can open a
new topic in round 2 has a third round wearing a second round's name.

**Why the added-material clause is here rather than in a skill.** It arrived as
`review-docs`'s bug and generalises without residue: any prose reviewer whose
report certifies a revision marker can certify prose it never read, and the fix
is the same in every case — check the delta only, or decline to certify and leave
the consumer's gate shut. The specific marker differs per reviewer, which is why
the rule names the shape and each skill names its own line.

**Why phrasing is excluded explicitly.** It reads as obvious and was not:
a reviewer that reports wording has stopped distinguishing a defect from a
preference, and each such finding costs a round at the same price as a real one.
Naming it in the budget rather than in each skill's taxonomy puts it where the
cost is counted.

**Why one comment per round.** The thread count was the symptom that made an
unbounded review look like diligence — 28 threads reads as thoroughness and was
one reviewer with no stopping rule. It also makes the round countable, which the
budget depends on.
