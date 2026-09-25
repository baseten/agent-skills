# settle-and-merge — design notes

Companion to `SKILL.md`. That file is the contract; this one holds the reasoning and the incident history behind its rules, keyed by section. Read a section's note before changing its rules or when applying them to a case the contract doesn't obviously cover. Nothing here overrides the contract.

**Most of these entries were written while their sections lived in `backlog-orchestrator`**, or in `implement-issue`'s *Merge*, and moved with them when the settle sequence and the merge gate were split into this skill (#132). Read "this skill", "here" and "the run" in them as the calling skill and its run as they stood when the entry was written; the incidents are the same incidents.

## Callers and inputs

**Why this is its own skill (#132, the second cut of #78):** `backlog-orchestrator` and `implement-issue` both end a run with the same sequence — summary, walkthrough, ranking where there is one, the gate, the merge — and `backlog-orchestrator` defined all of it while `implement-issue` evaluated invariant 12's gate "exactly as backlog-orchestrator defines it" and restated parts of the merge mechanics in its own *Merge*. One sequence with two readers is the shape #78 says to split on. What stays with each caller is what differs between them: when to settle, how an un-settle is handled, which supplier answers the gate's dependency-view condition, and the tranche-only inputs to the ranking. The move was meant to change no behaviour, and eval round 3 is the check.

## The settle sequence

**The removed decision docket (why the unattended decline's aggregation loss is accepted):** a second durable record written to close that gap is the decision docket this skill already carried and removed — it needed an in-place rewrite `permissions.json` cannot perform and stopped an unattended session on the prompt `backlog-orchestrator`'s step 8 forbids. Re-deriving a lost aggregate costs one summary; the record that would have prevented it cost four review findings and could not run.

**Why a code-changing ruling must not become a ranking constraint (the step-3 defect one step later):** choosing the other side of a decision a worker already implemented creates actionable work *after* step 3 processed the action points. Translating it into a ranking constraint would leave an orchestrator-owned fix undispatched and rank a PR that is not finished — the exact defect the `IN_FLIGHT_FIX` row guards against, arriving one step later.

## Merge behavior

**Why no waiver mechanism was built (Sept 2026):** a proposal asked for waived gate conditions recorded in the policy config with a machine-checkable removal trigger. The trigger requirement is right — a removal condition a preflight cannot execute is a promise nobody keeps, and both observed attempts failed it, one by living in a PR body no preflight reads and one by being circular, needing the very capability whose absence justified the lift. What the proposal did not carry is everything around it: which conditions may be waived at all, who may author the entry when the run is forbidden from honouring a config its own workers wrote, what a rejected trigger does, and what a consumer with no preflight does with an entry it cannot probe. Built as asked it is a second site that can subtract from invariant 12, controlled by whoever writes that site. The gate already has a discharge for an owner who wants a condition answered — a ruling, per tranche — and the honest answer to a standing lift is that this skill does not have one. The trigger constraint is recorded where it would apply if one is ever built.

**Why a waiver's removal trigger has to be a probe (Sept 2026):** a waiver is a promise to re-examine something, and the promise is only worth what the thing that would act on it can observe. Two attempts failed in the same way at different depths. The first recorded a bare boolean with the justification and the removal condition in the PR body — and a preflight reads the config, never a pull request, so the workaround would have outlived the tooling gap silently. The second attached a condition that read as checkable and was circular: *migrate the prose dependencies to native ones* cannot be confirmed complete without the native read the waiver exists because the run lacks. That one is worse than the boolean, because it looks like it has been handled.

**Why the stale-green rule is not the rejected up-to-date requirement:** requiring every branch be current before merging prevents this and serialises every merge behind every other, which a handover rejected and rightly. What landed is narrower in three ways: it is paid at the gate rather than continuously, only on the PRs about to merge, and only where the base has actually moved. The formatter case is carved out because there the diff's size argues in the wrong direction — a one-line tool bump conflicting with nothing is exactly the PR whose green is most likely to describe a tree without the code the tool will process.

**Why the integration result carries head SHAs (round 1):** the first version recorded which branches were integrated, which is enough to see a partial set and not enough to see a moved one. Another session opening or force-pushing a PR leaves the set of names unchanged while the trees change under it, so a cached clean result would let the gate merge a combination nobody ran — the check's own output becoming the thing that hides what the check exists to find.

**Why what discharges a stale green is established rather than stated:** whether a repository's checks run against the branch or against the branch merged with its base decides whether a re-run means anything, and it differs by configuration. Asserting either would make the rule confidently wrong in half the repositories it runs in — a re-run that proves nothing, or a branch update nobody needed.

**Why the merge goes through `merge-stack` and passes the map:** the stack rules require that skill for any merge or restack, and a raw forge call is exactly what the required-skills rule exists to prevent. Its merges, retargetings, and body edits are authored writes — easy to miss because it is invoked as an operation on the graph rather than as a worker that reports — and its identity observations are the last ones the structured result's map can carry.

**Why publishing has three states rather than two (round 1, Sept 2026):** the
first version of this said observed-to-trigger or not, and a review round pointed
out that a first run and every restart begin in neither. Not having observed a
trigger is not evidence that publishing is inert — which is this document's own
rule about absence, arriving inside the fix for its sibling rule about
assumption. Merging straight through on pre-publish evidence would land the PR
before a run that publishing started could report, so unknown means establish
rather than merge.

**Why establishing it takes a pass rather than a read (round 2):** the first fix
said publish, look once, record — and round 2 pointed out that the look lands
before a queued run or review has to exist, so it distinguishes *nothing was
triggered* from *nothing has appeared yet* only by luck. That is the same absence
rule again, one layer further in: a read with no lower bound on when the artifact
could appear is not a read of the artifact. Worse than getting it wrong once, the
answer is recorded and every later publish in the repository is decided by it. So
unknown takes the un-settle branch and classifies on the next delivered pass,
which is what `implement-issue` already requires of the draft→ready transition
under *Evidence freshness* — the read is taken no earlier than the next check-in.
The cost is one supervision cycle, once per repository, against a wrong answer
that would persist.

**Why the observation is recorded rather than re-derived:** it sits beside the
transport-visibility and posting-identity maps for the same reason those exist —
a fact about a repository that every later decision reads, established once by
observation rather than assumed from a provider's name.
