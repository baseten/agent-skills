# dependency-upgrade-orchestrator — design notes

Companion to `SKILL.md`. That file is the contract; this one holds the reasoning behind its rules, keyed by section. Read a section's note before changing its rules or when applying them to a case the contract doesn't obviously cover. Nothing here overrides the contract.

Derived from orchestrating thirteen major-version upgrades in a single repository. The rules below encode what that run got wrong as much as what it got right.

## Why triage cannot be delegated

Triage produces three outputs the dispatch depends on: which candidates are viable, which are coupled, and which model each warrants. An agent cannot determine its own model assignment, and coupling is a property of the *set* rather than of any member — an agent scoped to one package cannot see that another must move with it.

The failure this prevents is concrete. Naive per-package automation produces exactly the broken artifact the contract describes: one package advanced, its siblings stale, installation failing against a version-pinned patch. That is not a bug in the automation; it is the consequence of having no layer that reasons about the set.

## What dispatch forwards, and why the queue's own PRs are adopted

Added after the review round on [PR #72](https://github.com/baseten/agent-skills/pull/72), which reported one instance of this — deriving the set from the open bump queue produces a batch that the "work already open on a branch or PR" viability item then empties, because every candidate arrived as exactly such a PR.

That is one cell of a larger table, so the whole axis was walked rather than the instance patched. The axis is: **every conclusion triage reaches that `upgrade-npm-dependency` re-derives from its own narrower scope**, and the question per cell is *what supplies this there?*

| triage output | the agent's consuming phase | forwarded before? | survives a target move? | what re-derivation produced |
|---|---|---|---|---|
| Viability | *Viability gate* | **no** — the contract's supply list named the other three | licence and cooldown: no, per package. Peer caps: no, group-wide — any member moving voids it for all | the reported defect: an adopted bump PR reads as work already in flight, and the agent stops on the very PR that supplied its candidate |
| Coupling | *Viability gate*, peer caps | named, but the agent had no notion of a group | **no** — membership is *derived* from peer requirements at the targets, so a move can add or drop a member; the worker reports and stops rather than reshaping its own task, on the move itself and not on the set having come out different | a companion moving in the same task still declares its cap at the installed major, so the group blocks on its own member |
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

What this layer *can* do is the one thing neither the worker nor the merger is positioned to: it sees the whole batch, so it knows when a merge has moved the base under PRs that are still open. So the check is carried rather than held — each agent records the base its lockfile was resolved against, and this run compares that against the current base every supervision pass and at close-out, naming the PRs that have gone stale and redispatching them. The comparison costs one read per PR and it is the only thing between a handoff-time result and a merge that trusts it hours later. `upgrade-npm-dependency`, *Migration and verification*, states the per-agent half and its own expiry.

Staggering survives unchanged, for its original reason.

## Why "green" gates on the required check specifically

A check rollup is populated asynchronously. Immediately after a push — particularly one that cancels an in-flight run — it is briefly empty, and an empty rollup satisfies any predicate of the form "no failures and nothing pending".

That predicate reported a false green on the single most consequential result of the run, on the one PR whose outstanding question was whether its end-to-end suite passed. Gating on the repository's required check having *concluded successfully* is immune, because a check that has not registered has not concluded.

Reviewed again on [PR #72](https://github.com/baseten/agent-skills/pull/72): "the required check", singular, closes that hole and leaves an adjacent one open. A repository requiring three checks satisfies a singular reading the moment any one of them concludes successfully, so a PR reports green with two required results still pending — the same false pass reached from the other side, and it does not even need a race to happen. The rule is therefore stated over *every* required check on the current head, with enumerating what the repository actually requires as part of it, because gating on whichever check the run happened to read is how the singular reading gets rebuilt by accident.

## Why a cleared minor is dispatched differently from an uncleared one

From round two of the same PR, and worth recording as a hit for the escalation signal in `docs/review-fix-workflow.md`, *Model choice*: the finding landed on *Dispatch*, a locus round one had just rewritten. The round-one fix forwarded triage correctly and never asked the adjacent question — whether the agent it forwards to claims to cover what is being sent. Shallow at that locus, exactly as the signal predicts. *Enumerate* keeps minors and patches on the stated grounds that a minor is a common source of breaking changes, and *Dispatch* sent every surviving candidate through `upgrade-npm-dependency` — whose own scope is a major, or a minor that ships breaking changes. A routine patch therefore went through a workflow that did not claim to cover it, and the two documents disagreed about what the worker was for.

Filtering minors out of the batch would have thrown away the reason they are in it. Broadening the worker to every bump would have sent audited-clean patches through a viability gate, a research pass and a characterization phase that have nothing to act on. The resolution is that neither the version distance nor the bucket decides: **unruled-out risk does**, and triage is what rules it out. A cleared candidate has already had the phases performed on it, at the batch level, by the layer that can see the whole set; an uncleared one has not, whatever its version number says. So the cleared ones batch into one routine-bump task and the rest dispatch like majors — and the clearance is reported with its evidence, because it is a triage conclusion and the next run reads it as one.

Round twenty-nine, from a repository-scoped pass rather than a diff review, found the batching decision carries a second consequence nobody had walked: **the routine batch is the one task in the run that executes no named contract.** Everything this section delegates by pointing at `upgrade-npm-dependency` — re-running the in-flight search, reading an adopted PR's current state, re-resolving the lockfile and recording the base, re-checking each candidate's target — reaches that task through nothing. (Four, and the count is not the point: the list below it grew twice, which is the lesson at the end of this section.) The exclusion itself is right; there is no migration to research. But it was written as though the only thing being excluded were the phase order, when what actually rode on those cross-references was a set of rules about the **dispatch gap**, which apply to a routine bump exactly as they apply to a major.

The sharpest cell is the lockfile. The routine batch is the most exposed task in the run — many candidates, one file, one PR — and it was the only one whose producer contract was inherited rather than stated. So the obligations are now written out to that agent directly. **A cross-reference is a supply mechanism, and it supplies nothing to a task that never invokes the target.** That is the same defect class as the missing operand recorded above, one level up: there the caller failed to send a value the rule reads, here the caller pointed at a document the reader never opens.

The routine target re-check had a second defect of its own, and it is the more transferable one. It was written as "re-check every batched candidate's target immediately before that task lands" — **a moment no layer here occupies**, since this run merges nothing. That is precisely the defect rounds three to five removed from the lockfile rule two sections down, which was rewritten to *carry* its check to actors that exist rather than hold it. The fix was never swept onto this rule, and the guard left behind at round three could not see it: that guard was scoped to the worker's eval answers and spelled to the phrasing of the instance that produced it, so the same defect wearing a different verb in the other file passed it untouched. **A guard spelled to the instance that found it inherits the rule's failure mode** — this is the third time that has happened on this PR, and the guard now asserts the carried structure at both of its sites and names the constructions that have actually occurred.

Round thirty, verifying that fix rather than trusting it, found it three-quarters done — and the incomplete quarter **pinned in place by the fix itself**. The commit named four obligations and the directive list carried three; the new assertion hardcoded the same three, and the new eval graded "all three obligations". So the missing one was locked out at two tiers by the work that was supposed to add it, and every later round would have read a green check and a passing scenario as evidence it was complete.

That is the sharpest form of a habit this file already records twice. A guard written from the instances a round happened to find is a **fixture**, and a fixture cannot tell you the list is short. The three rescued consequences say what it cost: the batch agent was told to re-check targets with no definition of what moves one (so it checks the registry and stops the batch on any upstream release), no disposition for a positive result (so it re-triages work that is not its to re-route), and no exception for bot bump PRs on the one route where nearly every candidate has one (so the in-flight search empties the batch it was given — the defect round one opened with, rediscovered on a route nobody had walked).

The general rule, which is what to carry away: **where a fix enumerates, the guard must assert the property that generates the list, not the list.** Where only the list is available — and here it was — the honest move is to say so in the comment and expect the next round to extend it, rather than to let the enumeration read as a closed set. Both new assertions now name the property first and hold the fixture second.

The other half of round thirty is the same shape one level down. Five of the seven assertions written the round before checked `flat(du)` or `flat(ud)` — whole file — for rules whose entire content is *where* they are stated. The worst of them was green over the defect it was written for: the carried-check guard passed while *Supervise* mentioned neither carried check, because the sentence satisfying it sat in *Dispatch* describing what *Supervise* would do. **A guard for a placement rule has to check placement**, and this file's own central claim is that a rule present but misplaced reads correct to a grep and is inert to a reader.

Round thirty-two found the sixth instance of that class four lines above the block round thirty-one had just edited — a check named *"close-out reports per-PR lockfile staleness to the merger"* that tested for none of "lockfile", "base" or "PR", and passed on a sentence in *Dispatch* describing what *Close out* would do. It also found round thirty-one's "property" clause was a longer list of literals with the word *property* in the comment above it, which a fifth obligation with no disposition passed straight through.

**Four consecutive rounds ended with a guard green over its own subject, and each round fixed the instance it was shown.** That is the finding, and it is not about any of the individual guards. Every one of them was found in seconds by breaking the rule and re-running the check — which this repository had recommended since round twelve, *as a paragraph*, in a file whose own tier list says prose reaches an agent only when something makes it read it. `scripts/test_contract_guards.py` is that paragraph as a script, and it caught a live instance on its first run.

The routine-batch guard is now structural rather than a longer list: it extracts the bullets from the contract and asserts **one disposition entry per bullet**. Arity is the property that generates the list, so adding an obligation without saying what the agent does about it goes red. That is the difference between a property and a fixture, and the previous three attempts all failed it in the same direction — a list cannot tell you it is short, and calling it a property does not change that.

Round thirty-three applied that same test one level up, to the harness itself, and it failed identically: twenty-nine mutations over a hundred and forty-seven assertions, with no way to know which of the rest were load-bearing. Round thirty-two's own headline assertion was among the uncovered, and turned out to be four whole-file greps that a relocation walked straight through. So the harness now computes its own coverage — every assertion name in the checker, minus those with a mutation, minus a short list of stated exemptions — and prints the gap. **It reports rather than fails, on purpose**: a build that goes red on an uncovered assertion buys a mutation written to pass rather than one written to break the rule, which is how a battery becomes decoration.

Two smaller lessons from the same measurement, both about what a mutation actually tests. Reverting every `near()` in the checker to a whole-file grep left twenty-one of twenty-three mutations still red — so almost none of them exercised the scoping that three rounds of work had been about. A deletion tests that a rule is *present*; only a **relocation** tests that it is present where it is read, which is what most of these assertions are for. The harness grew a `MOVE_TO_END` mutation kind for that, and the first one written with it found the gap above. And the harness read only stdout, so a checker that *crashed* produced no failures, was counted as green over every defect, and printed a passing baseline first — the exit code is checked now.

And a coverage regression worth naming, because it hid inside a fix: replacing a twelve-literal fixture with one phrase per bullet dropped four protections, two of them consequences round thirty had paid a round to rescue. The structure was right and the contents were narrower than what they replaced, and nothing recorded the trade. A guard rewritten to be better shaped still owes an accounting of what it stopped checking.

Then the coverage number itself was wrong twice, in ways worth recording because both are the shape this whole exercise is about. It first counted by grepping `("...",` — which also matches the checker's own phrase fixtures, inflating the denominator into a number nobody could act on — and then, once parsed properly, printed *mutations plus uncovered assertions* as a total, adding two different units. **A reassuring number that does not mean what it says is the same defect as a guard that cannot fail**, one level further out, and it was committed inside the thing built to measure that defect.

Writing the first eighteen mutations for previously untested assertions immediately found two more guards green over their own subject: the one requiring the worker's stop to be reported checked a phrase that **survives inside the conditional wrapper round nineteen used**, so the old conditional could come back untouched; and the one holding the no-adopted-PR baseline checked the *Task* sentence while the phase that performs the ordering could lose its path entirely. Neither was reachable by reading. Both were the first thing their mutation found.

That is the argument for the coverage line existing at all. It does not fail the build, so it costs nothing; it just says how much of the checker has never been broken on purpose, and the first two batches of that debt each returned a real defect.

The final pre-merge pass found two more, and both are the same shape as everything above. **The superseding closure was deferred in the worker and not on the batch route** — the one route that inherits nothing by cross-reference, so the fix reached it through nothing, and its own bullet went on naming *Advanced* as a live outcome after ordering every bot PR closed. And **the coupled-siblings rule was fixed at four removal points and pinned to exactly those four anchors**, while the fifth — the earliest and most emphatic statement of it — sat *above* the scope paragraph, whose word "below" textually excluded it. A list of anchors cannot tell you a site is missing; the assertion now holds the scope sentence itself, which says "on this route" rather than "below".

The harness had the same defect in its own coverage number for the third time: it read `checks = [...]` and not `checks.append(...)`, so the one conditionally-built assertion was invisible and the denominator was short by one. Its docstring had said "appended" since the first version. That is now three counting errors inside the thing built to count honestly, which is the most durable lesson in this file: **a number that reads as reassurance gets less scrutiny than a rule does**, and the machinery that measures is not exempt from the failure it measures.

Paying down the rest of this PR's own subject returned one more, and it is the sharpest of the three. The guard requiring an oracle to make the moved-target stop unconditional read the scenario's **assertions** and not its **expected answer** — so the expected answer could teach *"the set is unchanged, so the task continues"* while the assertion beside it still graded the stop, and the check would pass over a scenario contradicting itself. That is worse than either field going stale alone: the corpus's own documentation calls the expected answer the only field that *prescribes*, so the field that teaches was free to disagree with the field that grades, and the guard watched the wrong one. It reads both now.

The third batch was otherwise clean — fourteen mutations, no defects — which is the first batch that has been. Every assertion protecting a rule this pull request introduces now has a mutation behind it; what remains uncovered belongs to the other skills' rules and predates this work.

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
