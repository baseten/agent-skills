# Notes — ci-attribution

Reasoning for `rules/ci-attribution.md`. Deliberately *not* bundled into
each skill: a copy of this per consumer would be design history with no reader,
and the audience for it is a person editing the rule, who has this checkout.

Moved here with the rule itself when it was split out (#144): the environment hypothesis from `repair-pr`, *CI repair*, step 2; the unconfirmed-dispatch rule and the producer-merge classification from `backlog-orchestrator`, *CI/review repair*; the infrastructure discriminator and the narrowing signature from `npm-dependency-upgrade-orchestrator`, *Supervise*. Their notes came with them. "The run" and "this pass" in the moved entries are those skills', as they stood when the entry was written.

**Why this is a shared rule (#144):** attribution is one test applied at two layers — the supervising run deciding whether to dispatch, and the repair pass deciding whether to change code — and three supervising skills held three versions of it. `backlog-orchestrator` and `implement-issue` pointed down into `repair-pr` for the environment test; the npm orchestrator had its own discriminator, the default branch failing the same job, which the other two never stated; and only `backlog-orchestrator` knew a producer merge's red was not the consumer PR's. A fix made to one reached neither of the others.

**Why the producer-merge remedy did not move with its classification.** Watching the refresh PR, reading its removals and restacking onto it are acts a run can take only where it may push to the PR's base — `backlog-orchestrator`'s stack authority. The classification is the part every supervising run needs, because without it the red reads as the PR's own and gets a repair pass against code nothing is wrong with.

## The environment hypothesis

**Why the infrastructure tell raises the hypothesis rather than settling it (round 1, Sept 2026):** the error signature — refused connection, missing socket, absent container — is produced identically by a dead service and by this PR changing connection configuration, and at the same breadth, since both hit every test that needs a connection. Routing on the signature alone gives the second case a `NO_CODE_CHANGE` and leaves the defect on the branch. What discriminates is something outside this branch: the service's own health, or whether unrelated branches and the default branch fail the same job, which `npm-dependency-upgrade-orchestrator` already required for its own case and this one was contradicting.

Two-thirds of the failures in one batch were a degraded build service failing repository-wide, including on the default branch. Treating them as defects in the changes under test produced repeated futile re-runs and, worse, a period of misattributing a shared outage to the run's own actions.

The discriminator is cheap and decisive: check whether unrelated branches fail the same job. Where they do, the useful action is escalation to whoever owns the service, not iteration.

## A producer merge

**Why a producer merge's red is expected-red (Sept 2026):** a merge on the producer side changed a generated API schema, and every open PR in the consuming repository failed a check none of their diffs touched — three times, once per producer merge. The repository's tooling opened a refresh PR within ninety seconds each time; the gap was that the refresh belonged to no tranche and no supervision loop, so every consumer PR stayed red while it sat, and the red was indistinguishable from a real failure at the moment it appeared. Watching the refresh and merging base before re-reading CI is cheaper than diagnosing one PR at a time — per check, because a consumer PR can be red for the producer's reason and its own at once. The removed-lines check is there because one refresh appeared to drop four fields from an endpoint its producer claimed not to touch; it was a reordering, and it could as easily not have been.

## A narrowing signature

A fix that reduces a failure rather than eliminating it is easily misread as a fix that did not work, and the natural response — revert or retry — discards information.

On that run, a defect blanking every data-driven view reduced, after a fix, to a subset of shards failing a specific element lookup. That narrowing was the evidence that the defect had two sites and one had been corrected. Reading the new signature located the second site; retrying would not have.
