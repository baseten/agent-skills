# CI and review verdicts

This is the rule other skills mean when they cite *CI and review verdicts*: what establishes that a PR's CI is green and that its review ran and came back clean, and on which commit either verdict holds.

**It is not a skill and nobody invokes it.** It is a shared rule, held once at
`rules/ci-and-review-verdicts.md` and copied into each skill that applies it by
`scripts/refresh_shared_rules.sh`. A skill reads its own
`references/ci-and-review-verdicts.md`, which works after `bootstrap.sh` has
installed only that skill's directory, and travels with the skill if it is
moved into a plugin. Edit the source, never a copy; check_shared_rules.py fails if a generated copy diverges.

It binds every skill that gates on either verdict or supervises a PR toward one. Which review conventions a PR's routing requires is the *review trigger* shared rule's; what happens when a round is refused, or a trigger never took effect, is that rule's too. This one says how to read the answer.

## A verdict attaches to a commit

**A verdict attaches to the commit it was computed on, not to the PR**, and the
head moves under it. Where a review names a commit other than the current head,
there is no review for the current head: that is `NOT REVIEWED`, not a stale
clean verdict. Findings routinely exist only after a repair push, so re-trigger
and wait rather than reading the earlier verdict forward. The same holds for CI:
an arriving check event is evidence about the SHA it names, and a name that is
not the head is no signal yet rather than a green.

**So filter an event against the head before anything is counted or posted.**
Compare the event's `head_sha` with the PR's current head — as read, not as
remembered — and do it before attribution, a budget or a comment sees the event:

- **an event naming another commit is not a signal about this PR**, red or
  green. It uses no repair cycle, dispatches nothing and gets no PR comment,
  whatever the wake's text asks;
- **a run cancelled because a newer run superseded it is not a failure**, and
  neither is an aggregate check whose only non-successful inputs were cancelled
  that way — a rollup job reporting `failure` over shards that report
  `cancelled`. Concurrency cancels superseded runs, so this is the ordinary
  shape of a push landing mid-run. It uses no cycle and gets no comment either;
  on the current head, the newer run is the one to read, and until it concludes
  the check is waiting, not green;
- **a cancel with no newer run on the head is not that case** — a job that
  exceeded its time limit, or a run cancelled by hand. It is a red check on the
  head like any other, and goes to attribution.

## CI is green

**Green means every check the repository actually requires has concluded successfully on the current head.** Enumerate what is required rather than gating on whichever check you happened to read. Two false passes share one root here, and closing only the second leaves the first:

- **an empty or barely populated rollup is not green.** A rollup is populated asynchronously and is briefly empty after a push — particularly one that cancels an in-flight run — and an empty rollup satisfies any predicate of the form "no failures and nothing pending" (`references/absence-is-not-a-verdict.md`). A check that has not registered has not concluded;
- **one required check concluding is not green** where several are required and another is still pending or failing.

Neither is a pass.

## A review is clean

**The two review sources are either/or, not summary-and-detail** — each is empty
exactly where the other carries the answer, which is why reading them in the
wrong order produces a confident wrong result. A clean review creates no review
object and no threads, so no endpoint can distinguish *clean* from *never ran*
without the second read.

1. **Existence is the summary comment, always.** Require a `Reviewed commit:`
   matching the current head. No match → `NOT REVIEWED`; request the round and
   never merge — **except a round recorded `refused`, which is not re-requested**
   (the *review trigger* shared rule, *A refused round*). This read is not
   skippable, because a thread does not say *which round produced it*: a
   resolved, non-outdated thread left by an earlier round or by a person
   satisfies any existence test built on threads, and a new trigger that
   silently no-ops then merges behind it.
2. **Severity is the threads, always.** Any unresolved thread means not clean,
   whatever the summary says, and an owner-reserved thread holds the gate
   regardless of the rest.
3. Both, or the PR does not merge. They are either/or as *sources* — each is
   empty exactly where the other carries the answer — and both as *conditions*.

**The summary comment is never evidence of severity.** A review that found things
may post a summary carrying no verdict, so its wording decides nothing — only the
thread list does. The prohibition is on that endpoint *for severity*, and it is
scoped deliberately: it is the wrong source for what a review found and the only
source for whether one happened, and a rule that forbade it outright misfired in
the opposite direction once already.

**Where the routed convention is a review skill invoked rather than a reviewer triggered** — `review-docs` is the case that exists — existence is that skill's completed pass and the review comment it posts, whose `Reviewed commit:` line is the one item 1 reads. What its decline means is the *review trigger* shared rule's (*Documentation-review routing*).
