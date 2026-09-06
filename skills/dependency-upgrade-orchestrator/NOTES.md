# dependency-upgrade-orchestrator — design notes

Companion to `SKILL.md`. That file is the contract; this one holds the reasoning behind its rules, keyed by section. Read a section's note before changing its rules or when applying them to a case the contract doesn't obviously cover. Nothing here overrides the contract.

Derived from orchestrating thirteen major-version upgrades in a single repository. The rules below encode what that run got wrong as much as what it got right.

## Why triage cannot be delegated

Triage produces three outputs the dispatch depends on: which candidates are viable, which are coupled, and which model each warrants. An agent cannot determine its own model assignment, and coupling is a property of the *set* rather than of any member — an agent scoped to one package cannot see that another must move with it.

The failure this prevents is concrete. Naive per-package automation produces exactly the broken artifact the contract describes: one package advanced, its siblings stale, installation failing against a version-pinned patch. That is not a bug in the automation; it is the consequence of having no layer that reasons about the set.

## What dispatch forwards, and why the queue's own PRs are adopted

Added after the review round on [PR #72](https://github.com/baseten/agent-skills/pull/72), which reported one instance of this — deriving the set from the open bump queue produces a batch that the "work already open on a branch or PR" viability item then empties, because every candidate arrived as exactly such a PR.

That is one cell of a larger table, so the whole axis was walked rather than the instance patched. The axis is: **every conclusion triage reaches that `upgrade-major-dependency` re-derives from its own narrower scope**, and the question per cell is *what supplies this there?*

| triage output | the agent's consuming phase | forwarded before? | survives a target move? | what re-derivation produced |
|---|---|---|---|---|
| Viability | *Viability gate* | **no** — the contract's supply list named the other three | licence and cooldown: no, per package. Peer caps: no, group-wide — any member moving voids it for all | the reported defect: an adopted bump PR reads as work already in flight, and the agent stops on the very PR that supplied its candidate |
| Coupling | *Viability gate*, peer caps | named, but the agent had no notion of a group | **no** — membership is *derived* from peer requirements at the targets, so a move can add or drop a member; the worker reports the difference and stops rather than reshaping its own task | a companion moving in the same task still declares its cap at the installed major, so the group blocks on its own member |
| Breaking changes | *Research* | yes | **no** — the research described one release | consistent; re-derivation is merely wasted work |
| Usage surface | *Usage audit* | yes | **no** — same | consistent; same |
| Routine-bump clearance | *Dispatch*'s batching, and the model selection it implies | not applicable — it routes rather than travels | **no**, and this is the sharp one: the route it picks has no viability gate in it, so a cleared patch whose PR advances to a breaking release bypasses the whole skill | added in the same round as the target rule, and exempted from it by oversight until the round after |
| Adopted bump PR | *Task*'s two worktree cases, and *Viability gate*'s in-flight item | yes, by URL | **identity only** — the URL survives any move; the PR's *state* was never the verdict's to give, since it can merge, close, advance or be superseded in the dispatch gap | before the gate distinguished a bot bump from a colleague's branch, re-derivation stopped the agent on the very PR that supplied its candidate; the row is here because forwarding a *state* would have looked identical and failed silently |
| Target version, per package | *Task*'s reuse rule, and *Viability gate*'s first three items | **no** — added as a triage output without a row, in the round that wrote this rule | n/a — it *is* the thing that moves | the worker is told to compare current target against triaged target and has no triaged target to compare with, so a stale licence, cooldown or peer clearance is reused and reads as compliance |

Two defects, one column fix: **at that round** dispatch began forwarding the viability verdict, the coupled set and any adopted PR, and the agent's gate began reading a supplied verdict instead of re-deriving that item. The payload is four items now — the per-package target was added a round later, for the reason the next paragraph gives — so read this sentence as the state it left, not as the current list, which the contract's *Dispatch* holds. The two safe cells stay forwarded for cost alone, and the contract now says which reason applies to which — an unlabelled list is what let the load-bearing entries drop out of it.

The target version was added to the payload a round after the worker was told to compare against it. That is the chain defect `scripts/check_contract_placement.py` exists for, committed by the person who had just written the rule: a consumer obligation whose operand the producer never sends. It is worth separating from the ordinary stale-restatement case, because it fails differently — a restatement contradicts and can be read as a contradiction, while a missing operand makes the rule silently unrunnable and the omission looks like nothing at all. Reusing a stale clearance reads as compliance.

The general form: **adding a rule that compares against something the caller knows is also a change to the caller's contract.** Ask what the new rule reads, and whether anything supplies it, in the same pass that writes the rule.

**A new triage output owes this table a row before it ships**, answering the same question — what supplies this at the agent's gate, and what does the agent conclude without it. That is what makes the table a guard rather than a record of one fix.

The routine-bump row is the one to read first, because it is the only cell whose failure is not a wrong answer but a **wrong route**. Every other target-dependent finding, if stale, gets a chance to be caught: the worker runs a gate, reads research, writes characterization tests. A stale routine clearance skips all of that by construction — batching is what "cleared" means — so a patch that advances into a breaking release ships with every check it meets passing, because the checks that would have failed are the ones the route removed. It was also exempted from the target rule by oversight for a round, which is the ordinary shape here and a worse cost than usual.

The target-version row is the proof that a written rule is not a guard. It was added a round late, by the person who wrote the sentence above it, in the round that introduced the output — the rule was two lines away and did not fire, because nothing made it fire. A table maintained by remembering to maintain it has the same failure mode as a sweep performed by remembering to sweep. The row is here now; what would actually enforce it is a check, and none of the mechanical checks can tell a triage output from a paragraph.

This file's own note on triage said all along that dispatch depends on *three* outputs including viability. The contract's supply list named breaking changes, usage surface and coupling. The disagreement sat in the repository for a full round; it is the ordinary way a rule and its restatement drift, and it is why the fix here is the table rather than the line.

Round seven found the exemption still half-scoped, and it is the same producer/consumer disagreement one clause deeper. The rule was written as *a derived set's own source* is not work in flight, because the bump queue is where the defect was reported — so a candidate derived from the outdated report, whose triage then turned up a bot PR, was still removed. The worker's gate had never been conditional that way, so the two contracts disagreed about the same PR depending on how its candidate had been found. What matters is what the open PR *is*, never which discovery path reached the candidate: a bot bump is the work, somebody else's attempt at the same upgrade is a duplicate. The discovery source is now explicitly stated as irrelevant, and both sides of the chain are asserted.

That is the third time on this PR that a rule was scoped to the circumstance it was first observed in rather than to the condition that actually governs it. Worth reading as a class, not three incidents.

And the round after fixing the contract found the scenario still teaching the old rule — the second time on this PR that a contract was swept and its evals were not, after the identical miss two rounds earlier. Twice is not an oversight, it is a habit: the sweep reads as finished when the prose agrees, because prose is what a reader checks. The eval corpus is now asserted against on both sides of this particular rule, but the general remedy is the ordering — sweep every restatement in one pass, never as a follow-up.

A fourth instance followed the round that introduced the *accommodations* rule — the sites still justifying the adopted PR's forwarding by "otherwise the agent reads it as work in flight", a reason removed three rounds earlier, survived in the contract's dispatch paragraph and in an eval, and the fix for them had been applied only where the finding pointed. Writing down a sweep rule and then not running it on the change that produced it is the same failure as the three before, and the honest reading is that the ordering rule needs to be executed as a step rather than remembered as a principle.

One thing did work: the guard for the previous round's rule failed on this round's rewrite, because its assertion quoted wording the fix replaced. A stale assertion that fails loudly is the cheap case — it is the stale assertion that keeps passing that costs a round, and that is the argument for keying assertions on the phrase a rule turns on rather than on its surrounding prose.

**Stated that way on the second instance, it was still too narrow, and the third instance proved it.** The remedy first read "sweep the scenarios in the same pass as the paragraphs", because scenarios were where the miss had been observed both times — and the next round found the stale rule sitting in the paragraph immediately below this one, in this file. That is the scoping class applied to the fix for the sweeping class: a remedy scoped to the material the habit was caught in rather than to the condition, which is *any* restatement in any material — contract prose, these notes, the scenarios, the README, the checks themselves.

The adoption rule itself is not merely an exemption. A bump PR is a machine's opening move on the work the run was sent to do, and it carries a lockfile resolution and a CI history worth having; superseding it silently also leaves the queue re-proposing the same bump forever. So the contract adopts or repairs it and says which, and reserves the duplicate finding for **somebody else's attempt at the same upgrade** — a colleague's branch, another run's PR — which is the case the item was written for. What the open work *is* decides that, never what supplied the candidate; see the round-seven note above, which this sentence outlived by two rounds.

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

Concurrency has a second cost that is not about resources at all, found later and from a merged defect rather than a failed run: a batch shares one lockfile. Each agent resolves it against the base as the agent found it, and each merge moves that base under every PR still open — so the first merge is safe and none of the ones after it are, without anything failing to say so. The branch installs, its tests pass, CI is green and the merge is conflict-free, because two upgrades editing different entries of the same lockfile do not conflict; what merges is a resolution the base had already removed.

The lever is partly the same one, which is why the rule sits beside it, and partly not — as round three of that PR established. This layer defines no merge gate and merges nothing (`README.md` limits autonomous merging to the explicitly gated skills), so "re-resolve immediately before merging" was an instruction with no owner: the worker ends at handoff, and nothing in either contract occupies the moment the rule names.

What this layer *can* do is the one thing neither the worker nor the merger is positioned to: it sees the whole batch, so it knows when a merge has moved the base under PRs that are still open. So the check is carried rather than held — each agent records the base its lockfile was resolved against, and this run compares that against the current base every supervision pass and at close-out, naming the PRs that have gone stale and redispatching them. The comparison costs one read per PR and it is the only thing between a handoff-time result and a merge that trusts it hours later. `upgrade-major-dependency`, *Migration and verification*, states the per-agent half and its own expiry.

Staggering survives unchanged, for its original reason.

## Why "green" gates on the required check specifically

A check rollup is populated asynchronously. Immediately after a push — particularly one that cancels an in-flight run — it is briefly empty, and an empty rollup satisfies any predicate of the form "no failures and nothing pending".

That predicate reported a false green on the single most consequential result of the run, on the one PR whose outstanding question was whether its end-to-end suite passed. Gating on the repository's required check having *concluded successfully* is immune, because a check that has not registered has not concluded.

Reviewed again on [PR #72](https://github.com/baseten/agent-skills/pull/72): "the required check", singular, closes that hole and leaves an adjacent one open. A repository requiring three checks satisfies a singular reading the moment any one of them concludes successfully, so a PR reports green with two required results still pending — the same false pass reached from the other side, and it does not even need a race to happen. The rule is therefore stated over *every* required check on the current head, with enumerating what the repository actually requires as part of it, because gating on whichever check the run happened to read is how the singular reading gets rebuilt by accident.

## Why a cleared minor is dispatched differently from an uncleared one

From round two of the same PR, and worth recording as a hit for the escalation signal in `docs/review-fix-workflow.md`, *Model choice*: the finding landed on *Dispatch*, a locus round one had just rewritten. The round-one fix forwarded triage correctly and never asked the adjacent question — whether the agent it forwards to claims to cover what is being sent. Shallow at that locus, exactly as the signal predicts. *Enumerate* keeps minors and patches on the stated grounds that a minor is a common source of breaking changes, and *Dispatch* sent every surviving candidate through `upgrade-major-dependency` — whose own scope is a major, or a minor that ships breaking changes. A routine patch therefore went through a workflow that did not claim to cover it, and the two documents disagreed about what the worker was for.

Filtering minors out of the batch would have thrown away the reason they are in it. Broadening the worker to every bump would have sent audited-clean patches through a viability gate, a research pass and a characterization phase that have nothing to act on. The resolution is that neither the version distance nor the bucket decides: **unruled-out risk does**, and triage is what rules it out. A cleared candidate has already had the phases performed on it, at the batch level, by the layer that can see the whole set; an uncleared one has not, whatever its version number says. So the cleared ones batch into one routine-bump task and the rest dispatch like majors — and the clearance is reported with its evidence, because it is a triage conclusion and the next run reads it as one.

Round twenty-nine, from a repository-scoped pass rather than a diff review, found the batching decision carries a second consequence nobody had walked: **the routine batch is the one task in the run that executes no named contract.** Everything this section delegates by pointing at `upgrade-major-dependency` — re-running the in-flight search, reading an adopted PR's current state, re-resolving the lockfile and recording the base — reaches that task through nothing. The exclusion itself is right; there is no migration to research. But it was written as though the only thing being excluded were the phase order, when what actually rode on those cross-references was a set of rules about the **dispatch gap**, which apply to a routine bump exactly as they apply to a major.

The sharpest cell is the lockfile. The routine batch is the most exposed task in the run — many candidates, one file, one PR — and it was the only one whose producer contract was inherited rather than stated. So the obligations are now written out to that agent directly. **A cross-reference is a supply mechanism, and it supplies nothing to a task that never invokes the target.** That is the same defect class as the missing operand recorded above, one level up: there the caller failed to send a value the rule reads, here the caller pointed at a document the reader never opens.

The routine target re-check had a second defect of its own, and it is the more transferable one. It was written as "re-check every batched candidate's target immediately before that task lands" — **a moment no layer here occupies**, since this run merges nothing. That is precisely the defect rounds three to five removed from the lockfile rule two sections down, which was rewritten to *carry* its check to actors that exist rather than hold it. The fix was never swept onto this rule, and the guard left behind at round three could not see it: that guard was scoped to the worker's eval answers and spelled to the phrasing of the instance that produced it, so the same defect wearing a different verb in the other file passed it untouched. **A guard spelled to the instance that found it inherits the rule's failure mode** — this is the third time that has happened on this PR, and the guard now asserts the carried structure at both of its sites and names the constructions that have actually occurred.

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
