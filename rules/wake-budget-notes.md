# Notes — wake-budget

Reasoning for `rules/wake-budget.md`. Deliberately *not* bundled into
each skill: a copy of this per consumer would be design history with no reader,
and the audience for it is a person editing the rule, who has this checkout.

Moved here with the rule itself, from `backlog-orchestrator`, *Arming the wait when nothing is in flight*, and the part of *API budget and read discipline* that bounded a deferring wake, with their notes (#144). "The run" in the moved entries is `backlog-orchestrator`'s, as it stood when the entry was written. The reply watch, the owner-queue report on a quiet wake and the attendance-gated settle trigger stayed in that skill: they are about its items and its settle sequence, not about how often a wake may fire.

**Why this is a shared rule (#144):** the wake is armed by whichever party owns supervision — `backlog-orchestrator` over a tranche, and a PR supervisor running its own loop over one PR — and the budget must bind both identically, or the unbounded watcher it exists to stop comes back through whichever copy is looser.

## A subscription and a check-in, both

**Why "costs nothing between firings" had to go:** the earlier text asserted that a durable subscription and a scheduled wake are free, and nothing available here documents that. What can be relied on is weaker and enough: whatever a subscription costs is paid at arming rather than per check, so it does not scale with how long the run waits. Treating it as zero is how a run justifies arming several, and hedging it with polling of the run's own invention spends exactly what the subscription was armed to avoid — while the bounded check-in, which looks like the same hedge, is the backstop the section requires and must not be cut with it.

## The budget and the backoff

**What two unbounded check-ins cost:** the previous rule — "re-arm each time it fires and finds nothing, stop when everything is merged or closed" — terminates only on an event that may never come. Two sessions running exactly that loop against already-merged PRs billed $33.45 and $59.60 doing nothing but waking hourly, reading no change, and re-arming. The budget-and-backoff shape (8 unproductive wakes — see the collapse note below for why unreadable wakes count too — 20 minutes doubling to a 4-hour cap, ~21 hours total) is sized so a watch survives a night and a working day waiting on a human reviewer but a forgotten one dies in single-digit dollars. (#50's own text estimated ~14 hours; the arithmetic was corrected in review — 20+40+80+160+240×4 = 1,260 minutes.)

**Why the counter lives in the wake's prompt:** the run that leaked one session was compacted twice mid-run. A counter held in session memory does not survive a compaction or the gap between firings, so it resets silently and the budget never binds. The re-armed prompt is the only storage that provably reaches the next firing.

**The four findings the seam produced, kept because they are the argument for collapsing it.** Clearing on *any* successful read failed when GraphQL was refused and REST healthy: every wake read REST, cleared the count, was refused on the GraphQL read it needed, and re-armed forever. Clearing on *the previously blocked resource* failed two further ways — where exhaustion alternates between buckets each wake reads the resource that blocked the last one, clears, and is refused by the other, so the count never passed 1 though every wake was throttled; and a secondary limit is tied to no resource at all, so a count it caused had nothing that could ever clear it and would have stopped a healthy watch. Then the trigger itself: the deferral rule fires on three conditions and each restatement of it recognized one, so a wake deferring preemptively on a low allowance — refused by nothing — incremented neither counter.

Every one of those is a clearing or trigger condition drifting from the rule it shadowed, which is the failure mode a second counter makes available and a single counter does not have. Under the collapsed design none of the four is expressible: there is one count, it rises on any unproductive wake, and only an observed delta clears it.

What deliberately does **not** collapse is the resource dimension: deferral stays per resource, because it decides which reads may be attempted, while the budget decides whether waking is worth doing at all. Those are different questions and conflating them produced the middle two defects above.

**Why this was two counters and is now one:** the split came from a true observation and the wrong conclusion. A throttled wake genuinely cannot claim "nothing changed" — it read nothing, so it does not know — so exempting it from the budget as it then was — no-ops only — was right. But the exemption removed the check-in's only termination guarantee, and rather than questioning the split, a second budget was bolted on beside the first.

That seam produced four review findings in a row, each a real unbounded-watcher path and each fixed narrowly enough to leave the next one open: clearing on any successful read, then on the previously blocked resource, then on a condition restated instead of referenced. The final design is sound but baroque, and every defect lived in the interaction between two counters rather than in either one.

The conflation underneath was between **how long to keep waking** and **when to wake next**. Only the second differs by cause. So the budget is now single — a wake is unproductive whether it read and found nothing or could not read at all, since both spend money to learn nothing — while the schedule stays per cause (the reset/`Retry-After` floor where the deferral supplied one, the doubling backoff otherwise — whichever is later; a deferral supplying neither bound sets no floor, per the entry above) and so does the report, because a watch that expired against a contended allowance and one that expired on a quiet PR call for different remedies.

One consequence is worth stating: a wake that could not read never clears the count, because clearing requires an observed delta and it observed nothing. That is what makes the single counter bind on a permanently contended credential, and it is the property the second counter was invented to supply.
