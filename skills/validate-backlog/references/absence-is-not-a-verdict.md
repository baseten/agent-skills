# Absence is not a verdict

**A query that returned nothing is evidence about the query.** It is not evidence
about the world, and it is never evidence that the thing you were checking for is
fine. This rule exists because the failure is invisible from inside the run: an
empty read and a clean result are the same bytes, so the run reports success and
nothing contradicts it.

Observed, independently, in six places:

- a review endpoint returning no rows, read as a clean review — five findings
  including a P1 came within one step of merging unread;
- a second endpoint returning no rows, read as *the reviewer is down* — five days
  lost on an unactioned P1, while five sibling PRs were answered in the same minute;
- a supervision poll seeing no events, read as *nothing happened*, where the true
  state was *nothing was listening*;
- a scenario nothing graded, counted as a scenario that passed;
- three hundred probes that each failed to authenticate, scored as three hundred
  clean non-triggers, across five iterations that therefore scored identically;
- an issue absent from a project board, read as present because the board's
  auto-add automation was enabled.

## What to do instead

- **Name the lookup, not the world.** *"I did not find a review at
  `<endpoint>`"* is what you observed. *"No review ran"* is a claim about an
  external system, and a different statement. Report the first until you have
  checked everywhere the answer could be.
- **Before concluding a system is broken, rule out the local explanation.**
  Where sibling items processed normally in the same window, a reading error is
  the default hypothesis, not an outage. You almost certainly looked in one place.
- **Know which emptiness is meaningful.** Where two sources can answer, they are
  often **either/or rather than summary-and-detail** — each empty exactly where
  the other carries the answer. A rule that forbids a source must say *for what*:
  the wrong source for severity can be the only source for existence, and a
  prohibition without its reason becomes a superstition the next run inherits.
- **Distinguish configured from performed.** That an automation is enabled is a
  fact about configuration. That it ran and produced the item is a fact about the
  artifact. Query the artifact. An enabled automation has been observed to miss.
- **Distinguish unavailable from forbidden from absent.** *Cannot reach it*,
  *must not write it* and *it is not there* are three states, and a capability
  report that records only the first leaves the other two to be inferred from an
  empty result — which is this rule's failure by another route.
- **Never let an ungraded, unread or unreachable item count as a pass.** Mark it
  as what it is. A tally that folds *unknown* into *fine* is a tally that cannot
  go red.

## Where it bites hardest

A check whose own inputs have gone missing reports success, because absence is
what it reads as "nothing wrong". Any guard that walks a list, matches a pattern
or consumes a generated set must be able to say **"I could not see anything"**
distinctly from **"I saw everything and it was fine"** — and must fail on the
first. A guard that cannot tell those apart is worse than no guard, because it
is believed.
