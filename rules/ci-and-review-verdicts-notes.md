# Notes — ci-and-review-verdicts

Reasoning for `rules/ci-and-review-verdicts.md`. Deliberately *not* bundled into
each skill: a copy of this per consumer would be design history with no reader,
and the audience for it is a person editing the rule, who has this checkout.

Moved here with the rule itself when it was split out (#144): *A verdict attaches to a commit* and *A review is clean* from the section of `backlog-orchestrator` that established a review was clean (under its *Implementation worker contract*), and *CI is green* from `npm-dependency-upgrade-orchestrator`, *Supervise*, with that skill's note on it. "The run" and "this layer" in the moved entries are those skills' runs, as they stood when the entry was written.

**Why this is a shared rule (#144):** five skills read one of the two verdicts. `backlog-orchestrator` and `implement-issue` supervise toward them, `settle-and-merge`'s gate requires both, `npm-dependency-upgrade-orchestrator`'s gate requires both for the PRs it merges, and `review-docs` writes the `Reviewed commit:` line the existence read matches. The review half lived in `backlog-orchestrator`, so `review-docs` and the gate pointed into an orchestrator neither runs under; the CI half lived only in the npm orchestrator, so the other gate read "green" with no definition behind it. They are one rule rather than two because every skill that reads one verdict reads the other.

**Why the refused exception is stated here and defined elsewhere.** Item 1 says to request the round when the summary names another commit, and a refused round is the one case where requesting it again is the scheduled retry the trigger rule forbids. The exception has to be visible at the point that would otherwise re-request, so it is named here; what a refusal is, and why it is never reissued, is the trigger rule's. The source text had this sentence spliced into the middle of item 1's own sentence, where it read as noise; it was separated when the rule moved.

## A verdict attaches to a commit

**Why events are filtered against the head before anything counts them (#154):** in an observed run two CI-failure wakes arrived for a commit that had already been replaced. Its end-to-end step had failed on purpose — "shards result: cancelled" — because concurrency cancelled the superseded run and the rollup check then reported `failure`. The wakes' text asked for a fix. The rule already said a check event is evidence about the SHA it names; what it did not say was that the comparison comes *first*, before a supervising skill retrieves context, attributes, spends a cycle or posts, and each of those steps read the event as though it were about the PR. The cancelled case is stated beside it because it is the same event from the other side: a cancelled run on the head is a check that has not concluded, and a rollup failing over cancelled inputs is reporting the cancellation, not a defect. Neither is green, which is why it is reported as waiting and not dropped. **Only a cancel a newer run explains is exempt (#154 review):** a job that exceeds its time limit also concludes `cancelled`, and a hang the PR itself caused would otherwise never reach attribution — and, with re-runs overridden, a head cancelled with nothing superseding it would wait with no end.

## CI is green

A check rollup is populated asynchronously. Immediately after a push — particularly one that cancels an in-flight run — it is briefly empty, and an empty rollup satisfies any predicate of the form "no failures and nothing pending".

That predicate reported a false green on the single most consequential result of the run, on the one PR whose outstanding question was whether its end-to-end suite passed. Gating on the repository's required check having *concluded successfully* is immune, because a check that has not registered has not concluded.

Reviewed again on [PR #72](https://github.com/baseten/agent-skills/pull/72): "the required check", singular, closes that hole and leaves an adjacent one open. A repository requiring three checks satisfies a singular reading the moment any one of them concludes successfully, so a PR reports green with two required results still pending — the same false pass reached from the other side, and it does not even need a race to happen. The rule is therefore stated over *every* required check on the current head, with enumerating what the repository actually requires as part of it, because gating on whichever check the run happened to read is how the singular reading gets rebuilt by accident.

## Path filters

**Why the filters are read before "no run" means anything (#180):** once a workflow declares `paths`, a head can correctly have no run of it, and read off the rollup alone that absence is indistinguishable from a trigger that never fired. A supervisor that reads it as missing CI waits on a run that is never coming, or holds a PR that is fine. Comparing the changed files with each workflow's filters separates the two. The comparison fails closed in the direction rule 8 needs: a workflow with no filter, a filter that matches, or a filter nobody could read all mean the check should have run, so a missing run of it is still missing.

**Why a filtered required check is reported rather than satisfied:** on GitHub a check branch protection requires by name stays `Expected` for ever when its workflow is filtered off the head, and the merge is blocked. Treating it as satisfied would open the gate onto a merge the forge refuses; treating it as pending waits without end. Neither is right, so it is a held PR with a named cause, and the remedy (a filter, a protection rule, a skip job that reports the status) is a workflow change only the owner makes.

**Why `dirty` is stated beside them:** a conflicted pull request runs no `pull_request` workflow at all, so its empty rollup looks like the filtered case. The mergeable state settles it before the filters are read.
