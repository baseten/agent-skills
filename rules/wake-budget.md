# Wake budget

This is the rule other skills mean when they cite *wake budget*: what a supervising run arms when it has nothing in flight to wake it, how often a scheduled check-in may fire, what counts as a productive wake, and when the watch stops.

**It is not a skill and nobody invokes it.** It is a shared rule, held once at
`rules/wake-budget.md` and copied into each skill that applies it by
`scripts/refresh_shared_rules.sh`. A skill reads its own
`references/wake-budget.md`, which works after `bootstrap.sh` has
installed only that skill's directory, and travels with the skill if it is
moved into a plugin. Edit the source, never a copy; check_shared_rules.py fails if a generated copy diverges.

It binds the supervising skill that applies it, wherever that skill's run arms a wake — one per run, whatever that wake watches. That party names the durable state its wake compares, and what it does on a wake that found something; this rule says how often it may wake and when it must stop.

## A subscription and a check-in, both

While workers are running, their completions are the events. A run with none in flight has no event source of its own, and the thing it waits on — a merge, a review, an owner's reply — may be a day away. So before it stops doing work it arms **both**:

1. **a subscription over what it tracks** — for PRs, the platform-native watch or an explicit PR-activity subscription. Normally these are already armed, because each item is armed as it enters the tracked set (the *watch and read* shared rule); this step confirms the set is complete rather than establishing it, and arms anything missing;
2. **a scheduled self check-in, as the backstop**, because that subscription does not cover everything. For PRs, CI success, new pushes and merge-conflict transitions are the known-unreliable deliveries, and a merge whose event never arrives is a merge the run never acts on. The check-in re-reads durable state and acts on what it finds, instead of treating silence as evidence that nothing happened.

Both, not either. The subscription is the fast path; the check-in is what makes the slow path terminate — and the check-in is itself bounded, because "re-arm forever until the merge comes" is the unbounded loop no worker may run either, written from the parent's side.

## The budget and the backoff

**Every recurring check-in that skill's runs arm — parent-side or worker-side — carries one unproductive-wake budget and a backoff**, these unless *A watch kept past a settled result* sets its own:

- **budget: 8 consecutive unproductive wakes**, then stop re-arming. **A wake is unproductive whether it read and found nothing or could not read at all** — one counter over both, because both spend money to learn nothing and a watch that alternates between them is as pointless as one that does either;
- **backoff: start at 20 minutes, double on each unproductive wake, cap at 4 hours.** Eight at that shape (20m, 40m, 80m, 160m, then 4h × 4) spans roughly 21 hours — long enough to wait out a night and a working day for a human reviewer, short enough that a forgotten watch dies in single-digit dollars. **Where the wake was deferred on a refused or exhausted allowance, it goes at whichever is later: the backoff's next step, or the reset/`Retry-After` floor, where the deferral has one** (the *watch and read* shared rule also defines when it has none) — waking before the reset is refused again, and waking before the backoff would have is the frequency the backoff exists to cut. The budget is one; the schedule is still per cause. A wake that defers draws on this same budget and carries none of its own; on exhausting it that way, stop re-arming and report the watch as blocked on the allowance, naming the contention — never as settled or quiet;
- **only an observed delta clears the count, and "nothing changed" means durable state only** — for a PR: its head, CI conclusions, the review-thread set and each thread's resolved state, mergeability, and tracker status — plus whatever further durable sources the arming party names for its wake. Any delta resets the count to zero, including a delta the run has no budget left to act on: a red CI it cannot fix is a change observed, never a no-op. **The test is what the wake observed, not how it ended** — a wake that saw a delta on one PR and was then refused reading another has observed a delta and clears the count, while a wake that observed none counts against the budget whether it read and found nothing or could not read at all;
- **write the count into the wake's own prompt.** The session's context does not survive between firings, and a compaction can drop it mid-run; a counter kept in memory resets silently and the budget never binds. Each re-armed prompt carries the consecutive-unproductive count and the durable state the next firing compares against;
- **stopping is reported, never silent**: which watch stopped, on which items, after how many unproductive wakes, **which kind they were**, and what would restart it — a fresh invocation, or the owner acting. A watch that expired against a contended allowance and one that expired on a quiet PR call for different remedies, so the report must not collapse them;
- **this is a cost guard, not a verdict.** An expired watch says nothing about the work: the item it watched is still open in the closing report, and its expiry must never be read as settled, merged, or finished.

## A watch kept past a settled result

**A run that has settled and reported its result, and keeps its PR watched for late human review** (`implement-issue`, *Completion*), waits on a person rather than a pipeline, so its check-in takes this schedule in place of the budget and backoff above: **the first check-in about 50 minutes after the last observed delta, then about every 4 hours, stopping after 3 consecutive unproductive wakes**. A delta restarts the schedule at its first step. Everything else in this rule holds unchanged: what counts as unproductive and as a delta, the count in the prompt, the reported stop, and its reading as a cost guard rather than a verdict.

## Not a licence to keep a loop warm

A subscription and a scheduled wake do not require the run to keep asking, which is what separates them from spinning, touching files, or committing to look busy. **Do not assume a subscription is free.** Absent documentation saying it is webhook-backed, treat its cost as unknown rather than zero — and do not hedge it with polling of the run's own invention. **The bounded scheduled check-in is not such a hedge and is not optional**: it is the backstop the first section requires alongside every subscription. What is banned is inventing a second, unbounded watch on top of both. Fake activity is what a run resorts to when it has no real wake mechanism, so arming one is the fix rather than the exception.

**When neither can be armed** — no subscription available, no scheduler — do not hold the session open reporting supervision that is not happening; the run would sleep through the event while the user believed it was watching. Reconcile durable state and return a restartable checkpoint naming what is still open and what would move it. What is lost is the automation, not the work.
