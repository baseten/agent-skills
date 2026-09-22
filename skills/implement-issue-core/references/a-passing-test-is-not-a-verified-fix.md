# A passing test is not a verified fix

**"Make the test fail first" is the conclusion, not the method.** It is correct
and it is not enough: where the fix and the test were written together, a broken
test fails before the fix and passes after it for reasons that have nothing to do
with the behaviour, and the check is satisfied trivially. Four distinct defeats
appeared in a single tranche, and each one is mechanical enough to check
directly.

Run this against every new or changed test, before the fix is accepted.

## The four defeats

**A sentinel that reads as a valid answer.** An ordering assertion used
`indexOf(a) < indexOf(b)`. With `a` absent, `indexOf` returns `-1`, which is less
than everything — so *never happened* and *happened first* are the same
assertion. *Assert presence before asserting order.* Any comparison against a
lookup that can return a not-found sentinel needs the presence assertion above
it.

**A sample size that cannot express the property.** A per-symbol ordering test
used one symbol, and one element is in order under every possible
implementation. *A test of an ordering, a grouping or a dedup needs enough
elements that a wrong implementation gives a different answer* — and, where the
failure is probabilistic, enough repetitions. That test only discriminated at 200.

**The assertion names the premise rather than the behaviour.** A "rejects a
poisoned batch" test constructed a poisoned batch and asserted the batch was
poisoned. It passed on every implementation, including no implementation at all.
*The assertion must name something the code under test decided.* **If it would
still hold with the module deleted, it is testing the fixture.**

**The fixture supplies the condition the test exists to detect.** A "late stream,
no workers" test pushed a fake worker into the registry, so the stream-only path —
the subject — was never reached. *State the negative in the fixture.* A test whose
name contains *no X* or *only Y* constructs that absence explicitly rather than
relying on the default fixture happening to lack it.

## Time is not an assertion target

**A test may assert that a bound fired** — the timeout result, the named pending
work. **It must not assert that elapsed wall-clock met or exceeded that bound**
without an explicit skew tolerance. Timers fire against a cached loop time that
can sit milliseconds behind a clock read, so the measured delta reads under its
own bound; the skew is in the timer, not in how the clock is read, and switching
to a monotonic clock does not remove it. One such assertion reproduced at 3 runs
in 400 on an idle machine and passed 10/10 locally — which is also why running
the unfixed code a few times does not discriminate here. Reproducing the
*mechanism*, at the iteration count the rate demands, does.
