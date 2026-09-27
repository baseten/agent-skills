# Repair rounds

This is the rule other skills mean when they cite *repair rounds*: which model a repair round is dispatched on, how an escalated round meets the repair-cycle caps, where the remaining budget is read from, and why the finding budget is a counter of its own.

**It is not a skill and nobody invokes it.** It is a shared rule, held once at
`rules/repair-rounds.md` and copied into each skill that applies it by
`scripts/refresh_shared_rules.sh`. A skill reads its own
`references/repair-rounds.md`, which works after `bootstrap.sh` has
installed only that skill's directory, and travels with the skill if it is
moved into a plugin. Edit the source, never a copy; check_shared_rules.py fails if a generated copy diverges.

It binds the layer that dispatches a `repair-pr` pass and counts its cycles. Which budget keys that layer reads, and their built-in defaults, each reading skill states itself.

## Escalation on evidence

**Repair escalates on evidence, not on exhaustion** (`repair-model-escalations`, per PR). Dispatch a repair round on the strongest available model when the round about to be dispatched carries a finding on a **locus an earlier repair on this PR already wrote** — a reshaped version of a finding an earlier round addressed, or a new finding in text an earlier repair authored. That is the signal that the previous repair was shallow and the root was never understood, and it is the one place in the repair path where model strength is the binding constraint. Everything else about the round is unchanged, and Sonnet remains the default for all the others.

The trigger is that evidence and nothing else, so it fires on the earliest round where the evidence can exist rather than after the cheaper rounds have been spent, and it never fires merely because the budget is nearly gone. Exhaustion and non-convergence are different failure modes wearing the same counter: a round that fixes real findings while genuinely new ones keep surfacing is breadth, and a stronger model buys nothing there; a round whose fix draws a reshaped finding back onto the same locus is a reasoning failure. A count-based ladder cannot tell them apart (`rules/repair-rounds-notes.md`: the observed spec-PR case).

## The cycle cap

**The cycle cap is a separate mechanism, and an escalated pass that pushes a repair still consumes its cycle.** `ci-repair-cycles`/`review-repair-cycles`/`finding-repair-cycles` bound unattended churn, which is model-independent; a round that skipped the counter because it escalated would make "escalate" a way to buy extra rounds. At the cycle cap the PR goes to the owner whatever model ran. `repair-model-escalations` bounds only how many of a PR's rounds may be escalated, so exhausting it does not end the repairs — it returns them to Sonnet.

## Who decides

**The dispatching layer owns the decision.** `repair-pr` never selects or escalates its own model, exactly as `implement-issue-core` returns a reasoning-heavy repeated failure instead of escalating one. The evidence is readable by the dispatching layer from durable state — the PR's own commit history against where each finding sits — so a restart evaluates the same trigger its predecessor would have; the repair worker reports what it saw as corroboration, not as the record.

## The remaining budget

**Read the remaining budget off the run's record of the PR — the resolved cap minus the cycles it records — and pass it; never dispatch on a recollection of it.** A repository instruction to keep repairing until review is clean does not raise it: that instruction is about how a finding is fixed, and a deferred-repair item keeps the finding in front of the owner rather than burying it (`rules/repair-rounds-notes.md`: why the budget is read at dispatch).

## The finding budget

**The budget for a `finding` repair is its own counter (`finding-repair-cycles`), not a draw on `review-repair-cycles`** — the two budgets bound different loops (reviewer convergence versus the settle-repair-resettle loop the supervising run drives itself), and one counter over both lets either loop starve the other (`rules/repair-rounds-notes.md`: the argued choice, including the case for sharing and why it loses). An escalated round still consumes its finding cycle, exactly as for the other two types (*The cycle cap*).
