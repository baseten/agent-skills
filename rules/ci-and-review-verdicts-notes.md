# Notes — ci-and-review-verdicts

Reasoning for `rules/ci-and-review-verdicts.md`. Deliberately *not* bundled into
each skill: a copy of this per consumer would be design history with no reader,
and the audience for it is a person editing the rule, who has this checkout.

Moved here with the rule itself when it was split out (#144): *A verdict attaches to a commit* and *A review is clean* from the section of `backlog-orchestrator` that established a review was clean (under its *Implementation worker contract*), and *CI is green* from `npm-dependency-upgrade-orchestrator`, *Supervise*, with that skill's note on it. "The run" and "this layer" in the moved entries are those skills' runs, as they stood when the entry was written.

**Why this is a shared rule (#144):** five skills read one of the two verdicts. `backlog-orchestrator` and `implement-issue` supervise toward them, `settle-and-merge`'s gate requires both, `npm-dependency-upgrade-orchestrator`'s gate requires both for the PRs it merges, and `review-docs` writes the `Reviewed commit:` line the existence read matches. The review half lived in `backlog-orchestrator`, so `review-docs` and the gate pointed into an orchestrator neither runs under; the CI half lived only in the npm orchestrator, so the other gate read "green" with no definition behind it. They are one rule rather than two because every skill that reads one verdict reads the other.

**Why the refused exception is stated here and defined elsewhere.** Item 1 says to request the round when the summary names another commit, and a refused round is the one case where requesting it again is the scheduled retry the trigger rule forbids. The exception has to be visible at the point that would otherwise re-request, so it is named here; what a refusal is, and why it is never reissued, is the trigger rule's. The source text had this sentence spliced into the middle of item 1's own sentence, where it read as noise; it was separated when the rule moved.

## CI is green

A check rollup is populated asynchronously. Immediately after a push — particularly one that cancels an in-flight run — it is briefly empty, and an empty rollup satisfies any predicate of the form "no failures and nothing pending".

That predicate reported a false green on the single most consequential result of the run, on the one PR whose outstanding question was whether its end-to-end suite passed. Gating on the repository's required check having *concluded successfully* is immune, because a check that has not registered has not concluded.

Reviewed again on [PR #72](https://github.com/baseten/agent-skills/pull/72): "the required check", singular, closes that hole and leaves an adjacent one open. A repository requiring three checks satisfies a singular reading the moment any one of them concludes successfully, so a PR reports green with two required results still pending — the same false pass reached from the other side, and it does not even need a race to happen. The rule is therefore stated over *every* required check on the current head, with enumerating what the repository actually requires as part of it, because gating on whichever check the run happened to read is how the singular reading gets rebuilt by accident.
