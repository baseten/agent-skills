# dependency-upgrade-orchestrator — design notes

Companion to `SKILL.md`. That file is the contract; this one holds the reasoning behind its rules, keyed by section. Read a section's note before changing its rules or when applying them to a case the contract doesn't obviously cover. Nothing here overrides the contract.

Derived from orchestrating thirteen major-version upgrades in a single repository. The rules below encode what that run got wrong as much as what it got right.

## Why triage cannot be delegated

Triage produces three outputs the dispatch depends on: which candidates are viable, which are coupled, and which model each warrants. An agent cannot determine its own model assignment, and coupling is a property of the *set* rather than of any member — an agent scoped to one package cannot see that another must move with it.

The failure this prevents is concrete. Naive per-package automation produces exactly the broken artifact the contract describes: one package advanced, its siblings stale, installation failing against a version-pinned patch. That is not a bug in the automation; it is the consequence of having no layer that reasons about the set.

## Why file count is explicitly demoted

Surface area is the intuitive proxy for effort and it is wrong in both directions, which is worse than being wrong in one.

A framework upgrade importing into 432 modules resolved to a three-line configuration change, because the migration's staged flags had already been enabled — the imports were unchanged API. A package with four direct imports required a new mandatory provider component, a changed session lifecycle, and a test double rebuilt from scratch, because the count measured direct imports and missed the provider layer wrapping them.

The estimate is therefore an opening position to be revised by reading what the APIs actually do, not an input to be trusted. The contract keeps it because it is cheap and better than nothing, and marks it as requiring critical reading because trusting it produced both errors above.

## Why model selection keys on failure mode

The question that predicts required capability is not "how much code" but "if this is wrong, how does it announce itself".

A mechanical rename across many files fails loudly — the build breaks, and a mid-tier model iterating against a compiler converges. A validation rule that loosens produces a passing build, a green suite, and an application that accepts input it should reject. No amount of iteration finds that, because nothing is failing; it requires reasoning about semantics that were never written down.

Hence the split. It also explains the asymmetry rule: over-assignment spends budget, under-assignment ships a defect that the run's own verification declares absent.

## Why escalation to the highest tier is authorized rather than assumed

Across a batch of thirteen it was necessary zero times, and the tier's cost is not proportionate to its marginal benefit on migrations of this shape. Requiring authorization makes the default correct while leaving the escalation available where a case genuinely warrants it.

## Why concurrency is bounded

The naive dispatch is full width, and it is wrong for a reason that is invisible until it happens: agents performing an upgrade each run a test suite, and test suites are the most resource-hungry thing in a repository.

Dispatched at full width, a thirteen-agent batch drove one machine to a load average of 288 with under 200 MB of memory free, and killed a quarter of the run through watchdog timeouts and starvation. The agents were not at fault and their work was not recoverable from the failure.

The same reasoning extends to shared infrastructure: simultaneous container-image builds triggered by a batch of pushes exhausted a build service used by the whole repository, degrading unrelated engineers' work. Staggering costs wall-clock time that is cheaper than the failure.

## Why "green" gates on the required check specifically

A check rollup is populated asynchronously. Immediately after a push — particularly one that cancels an in-flight run — it is briefly empty, and an empty rollup satisfies any predicate of the form "no failures and nothing pending".

That predicate reported a false green on the single most consequential result of the run, on the one PR whose outstanding question was whether its end-to-end suite passed. Gating on the repository's required check having *concluded successfully* is immune, because a check that has not registered has not concluded.

## Why supervisors emit only state changes, and only actionable ones

A supervisor that re-emits unchanged state trains its reader to ignore it, which defeats the purpose at exactly the moment something real occurs.

The subtle form of this bug: including a varying value in the compared representation. A check *count* increments as a run progresses, so a PR whose state is unchanged re-reports on every tick. The compared value must contain only what constitutes state.

## Why infrastructure is separated explicitly

Two-thirds of the failures in one batch were a degraded build service failing repository-wide, including on the default branch. Treating them as defects in the changes under test produced repeated futile re-runs and, worse, a period of misattributing a shared outage to the run's own actions.

The discriminator is cheap and decisive: check whether unrelated branches fail the same job. Where they do, the useful action is escalation to whoever owns the service, not iteration.

## Why a changed failure signature is read rather than retried

A fix that reduces a failure rather than eliminating it is easily misread as a fix that did not work, and the natural response — revert or retry — discards information.

On that run, a defect blanking every data-driven view reduced, after a fix, to a subset of shards failing a specific element lookup. That narrowing was the evidence that the defect had two sites and one had been corrected. Reading the new signature located the second site; retrying would not have.

## Why declined upgrades are recorded where decisions live

A closed PR's comment thread is not a durable record; the next attempt begins from the same outdated dependency list with no knowledge of why the previous attempt stopped. Where an upgrade is blocked on a licence change, an unresolvable peer, or a scheduling decision, that reasoning belongs in the issue tracker, and the record is more valuable than the PR that produced it.
