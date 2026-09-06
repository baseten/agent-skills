# upgrade-major-dependency — design notes

Companion to `SKILL.md`. That file is the contract; this one holds the reasoning behind its rules, keyed by section. Read a section's note before changing its rules or when applying them to a case the contract doesn't obviously cover. Nothing here overrides the contract.

These rules were derived from upgrading thirteen packages across major versions in one repository. Every rule below exists because its absence cost something on that run.

## Why the phase order is load-bearing

The contract fixes research → audit → tests → bump, and the fixed point is that **tests precede the bump**. This is not stylistic sequencing.

A test written after a migration encodes the behaviour the migration produced. If the migration introduced a defect, the test passes and enshrines it. A test written against the prior version, proven green there, then executed unchanged, tests a different proposition: not "the new code does what this test says" but "the new code does what the old code did". Only the second proposition is what an upgrade is claiming.

The empirical case: four packages on that run already carried post-migration tests, all green. Written the other way round, the same four surfaced a customer-facing regression that had passed every existing suite, and a false causal claim in a PR description that no reviewer could have checked. The difference was ordering alone.

One correction to how that ordering was written down, from the same round. Rewriting the worktree paragraph for the adopted-PR case produced "either way that head already carries the bump, so it is never the baseline" — true of an adopted PR's head and false of an ordinary branch cut from the default, which still carries the *current* version and is therefore the baseline until the bump is applied to it. Stated unconditionally it would push a worker into applying the bump before writing the tests, or into cutting a needless second worktree: the phase order broken by a sentence written to protect it. The two cases are now separate bullets, differing in exactly the one way that matters here.

This also explains why the contract forbids editing a failing characterization test. The failure is the signal the phase exists to produce; suppressing it returns the exercise to the post-hoc case it was designed to escape.

The adopted-bump-PR rule added in the [PR #72](https://github.com/baseten/agent-skills/pull/72) round is the same proposition reached from a new direction, and it is worth stating separately because it does not look like a violation. Adopting a bump PR makes its head the upgrade branch, and a worker that then writes its characterization tests in the obvious place — the branch it is working on — has written them against the new version. Every visible step of the phase is performed and the phase's whole claim is gone. So the baseline is named as the adopted PR's merge base at the phase itself, not only implied by "still the old version".

The cherry-pick beside it was written as though it were the rule, and a later round found the cost. It is the mechanism for moving a test commit between two branches — what the adopted-PR case needs and the ordinary case does not, since there the upgrade branch is already the baseline and the test commit is already its ancestor. Stated as an unconditional step it is a no-op that reads as work, which is enough to make a worker cut a second worktree to have something to cherry-pick *from* — the very thing the round before had just forbidden. Both paths are spelled out now, and the invariant is stated as the ordering: proven green on a tree without the bump, run unmodified on one with it.

## Why viability is gated before research

Each gate item ended a real upgrade before any code was written, and each is minutes of work against hours.

The licence gate is the sharpest: a package that relicensed from permissive to copyleft failed the repository's licence check outright. That is not a migration problem with a technical solution — it is an ownership decision about whether the organisation may ship the code at all, and an agent that migrates first and discovers it second has spent the entire budget on an artifact that cannot merge.

"Work already in flight" is included because it nearly produced a duplicate of a colleague's five-week-old branch covering the same 69 files. Nothing in the dependency's own metadata reveals this; only searching the repository's open work does. That item was written from that case and phrased for it — *any* open PR naming the package — and the review on [PR #72](https://github.com/baseten/agent-skills/pull/72) found the case it therefore swallows: an automated bump PR for the same package is not a duplicate of the work, it *is* the work. The distinction the item now draws is between work this task was sent to do and work someone else already started, which is what the colleague's-branch case was about all along.

## Why a moved target voids the whole triage

The contract's rule is one sentence — a moved target voids that package's triage, and only identity survives — and it reached that form by being wrong six times. The versions are worth recording as **superseded**, because each was defensible under the question it asked, and the questions are the transferable part:

| the question asked | its answer | why it was wrong |
|---|---|---|
| Can the caller's triage be reused at all? | yes, wholesale | ignores that a verdict is a snapshot |
| Can this *fact* change over time? | a licence cannot | the licence had not changed; the *package* had |
| Which *item* of the verdict did it arrive in? | reuse per item | an adopted PR is one item carrying two facts of opposite lifetime — URL and state |
| What is the finding *about*? | a package at a version | right for licence and cooldown, wrong for the two relations |
| What is its *arity*? | per package | peer resolution is a relation over the whole target tuple, not a property of one member |
| Does anything survive besides identity? | the coupled set does | membership is *derived* from peer requirements at the targets, so it moves too |

Only the last question has a stable answer, and it collapsed the taxonomy rather than extending it: **nothing survives but identity.** Five rounds of adding categories ended by deleting them, which is the thing to remember the next time one starts growing a fourth.

One of those rounds carried a lesson that outlives this rule. The reason the in-flight item was ever read from a verdict at all was a *workaround* for an older rule — re-deriving it used to make the agent stop on the adopted bump PR — and that constraint had been removed two rounds before the workaround was. **When a rule is relaxed, the accommodations built on the old version are the next thing to sweep**, and they are harder to spot than restatements, because an accommodation reads as a considered decision rather than as a contradiction.

Three consequences are worth stating on their own, because each is a silent failure rather than a wrong answer:

- **A stale peer clearance passes a check that never ran over the tuple.** Every individual clearance reads as valid while the combination goes unchecked — a companion at v3 demanding framework@3 breaks a framework@2 clearance whose own target never moved.
- **A stale routine-bump clearance picks a wrong route, not a wrong answer.** It is the only cell of the forwarding table with that shape: the route it selects has no viability gate in it, so a patch advancing into a breaking release ships past research, audit and characterization with every check it *does* meet passing.
- **A moved target is a stopping condition, not a repair.** Two decisions built on the old triage belong to the caller: **membership**, because absorbing a new member upgrades a package nobody triaged while proceeding without it splits a coupled group; and **the model**, because selection keys on a failure mode derived from the research, and an agent cannot revise its own assignment. A worker that re-reads the range, sees the release has advanced from a mechanical rename into a silent-failure domain, and proceeds anyway has produced the one migration the selection rule exists to prevent — correctly re-derived and dispatched at the wrong capability. So the re-reading serves the report and the task stops — **on the move itself, not on the set having changed**. Making the stop conditional on a changed membership was the first way it was written, and it leaves the model question unanswered in every case where the set happens to be stable, which is most of them. What the report hands back is a **package → current target mapping**, symmetric with the one dispatch supplies and for the same reason: a single figure cannot say which new version belongs to which package, so a caller re-triaging from it attaches a refreshed finding to one member while keeping a stale target for another. A note on the guard that watched for this grouping, because it is the second natural-language detector these checks have had and both ended the same way. It failed four times in four rounds: one spelling missed two others; a per-package vocabulary missed "for every package"; the group vocabulary that was supposed to be the *reliable* half missed "for the group as a whole" and so blocked a **correct** oracle; and accepting any group marker anywhere in the sentence let through a sentence where that marker scoped the coupled set while peer stayed per package. Binding the marker to the peer finding is syntactic attachment, which a word list cannot do.

So it is deleted, exactly as `prescribes()` was at round ten, and replaced with a property that needs no parsing: **an oracle states the two rules as two, and never names all three findings in one unit of text.** Licence and cooldown are per package; the peer finding is a relation over the tuple; a text listing them together is the shape every contradiction on this PR grew from. Round twenty-five made that unit a *sentence*, and the three rounds below are what it took to establish that a sentence cannot be decided — **the unit is a paragraph or list item, settled at round twenty-eight**, and the rest of this section is why.

The test of whether that is a real convention rather than a device to satisfy a checker is what conforming cost: one run-on sentence, split into the two rules it was conflating, and one assertion that graded two things at once, split into two. Both texts are better for it. The residual is stated in the code — an oracle spread across two sentences that still means per-package peer reuse passes — and it is smaller than a detector that blocks correct oracles.

Round twenty-six then found the replacement carrying the same defect as the thing it replaced, which is the part worth remembering. Its sentence split broke on `;` and `:` as well as on `.`, so *"Per package, reuse licence and cooldown; under that same rule, reuse peer too."* — the contradictory rule in one breath, the exact sentence the convention exists to reject — read as two compliant halves and the corpus guard stayed green over it. Clause punctuation is how a run-on smuggles a conflated rule past a sentence-scoped check, so the split was narrowed to `.`, `!` and `?` — **the round-twenty-six rule, superseded one round later**, and left standing here only because the two consequences below outlived it. Two consequences beyond the one-character fix. **The corpus had been made to conform under the loose split**, so tightening it re-flagged one oracle in eval 14 — a sixty-word sentence chaining both rules through a colon and a semicolon — which is the accommodation-sweep lesson above, arriving from the direction of the guard rather than the contract: a corpus shaped to a defective check inherits the defect. And **a heuristic belongs in the fixture tier whatever its author believes about it**: `scripts/test_contract_placement.py` now pins the constructions that must fire alongside the oracle prose that must keep passing, which is what `test_rule_locality.py` was built for after a detector shipped green over a live violation. Three natural-language guards on this contract have now had the same failure; the one that did not recur is the one with fixtures.

Round twenty-seven found the narrowed split escaped again, by an abbreviation: *"Reuse licence and cooldown for e.g. unchanged targets, and reuse peer under the same rule."* breaks at `g.`, so one sentence conflating the two rules read as two and the guard was green over it a second consecutive round. What matters is the shape of the fix rather than the fix. Adding `e.g.` and `i.e.` to an exception list would have been the third guess at an open-ended list, and it would have missed a version number — `v2.9.0` has the same property and is not an abbreviation. **The class is a terminator with nothing starting a sentence after it**, so the boundary was made to require a sentence start, which needs no vocabulary at all: `e.g. unchanged` continues, `v2.9.0. Peer` does not. **That is the round-twenty-seven rule, superseded by the round below**, and it is recorded because the reasoning under it — fix the class, never the instance — is what produced the fixture that then killed it.

That round argued the guard should survive where the two before it had not, because `prescribes()` and `groups_peer_per_package()` needed **vocabularies** — open-ended lists of English phrasings, where each round could only add the phrasing it happened to find — while a sentence boundary was one syntactic property with a residual that fits on a line. The argument was wrong, and one round later. It is left here because **the pre-commitment made alongside it is the thing that worked**: if a third construction escaped, the answer was not to be a third patch to the boundary but to stop parsing sentences and make the corpus carry the structure. Naming the escalation before needing it is what stopped rounds ten and twenty-five being patched a fourth time, and it is what let round twenty-eight be a decision rather than a re-derivation.

Round twenty-eight collected on it. *"Reuse licence and cooldown for e.g. **unchanged targets**, and reuse peer under the same rule."* splits at `g.` because `*` reads as a sentence start — and `*` **has** to read as a sentence start, since `**Peer** is a relation over the tuple.` is ordinary oracle prose that a fixture required passing. Markup must be able to start a sentence and must not be able to fake one. That is not another escape to patch; it is a proof that no character class satisfies the unit, so the unit is wrong.

So the unit is a **block** — a paragraph or a list item — decided by layout alone: no terminator, no capitalisation, no vocabulary, nothing an oracle's wording can spoof. Two things are worth carrying forward from how that landed.

**A convention's demand is not a heuristic's false positive, and the difference is whether the author can act on it.** The block rule is stricter than the sentence rule and rejects prose that reads perfectly well — *"Licence and cooldown are measured per package. Peer resolution is a relation over the tuple."* was compliant a round earlier and is a violation now. That would be fatal to a heuristic, because an author cannot see why it fired and eventually switches it off. It is survivable here because the remedy is mechanical and always available: put the second rule in its own bullet. What conforming cost was three oracles, each of which already carried the two rules under labels — "Per package:" and "Group-wide:" — and now carries them as two list items, which is how they should have been written in the first place.

**The escape fixtures are kept even though the block rule makes them uninteresting.** All three sentence-era constructions still sit in `BAD`, passing trivially. They are the evidence for the unit rather than tests of the regex, and an author tempted back to sentence parsing should have to delete them on purpose.

That is the forward-direction failure of round fifteen, recreated on the return path, and it is worth noting that an asymmetry between a call and its return is invisible from either end alone. The guard written to stop that pair drifting had the same defect one level down: the worker end was scoped to *Report*, the producer end to the whole file, so removing the requirement from the paragraph that carries it would still have passed. A presence check must name the clause that has to carry the requirement — the round-five lesson, violated inside the guard added to enforce symmetry. This is the only place in the contract where getting something right is still a stop, and it costs a dispatch round trip in the common case; that is the correct trade, because the failure it prevents is silent and the stop is not.

Two things are never taken from a verdict whatever the target does: work already in flight, and the adopted PR's own state. The second matters because the in-flight search cannot cover it — that search reads *open* work, so a merged adopted PR is invisible to it, and a worker would branch from a stale head and redo an upgrade that already landed.

## Why the published artifact outranks the docs page

A rendered changelog page for one package interleaved an unrelated major's notes with the current release, which would have propagated a false claim about what changed. The published tarball and the installed source cannot drift from the code they describe, because they *are* it.

The stronger form — diffing two published versions' sources — answers behavioural questions prose cannot. Asked whether a matcher library's semantics had moved, the diff showed every existing matcher implementation byte-identical, which settles the question in a way no changelog reading could. Asked whether a local patch was still required, the installed source showed the upstream behaviour unchanged, so the patch stayed.

## Why "checked and cleared" is reported separately

A reviewer reading an audit that lists only findings cannot distinguish a thorough audit that found two things from a cursory one that noticed two things. The cleared list is what makes the finding list trustworthy, and it is cheap to produce because the work was already done.

## Why shape-based changes get a scanning test rather than a search

An identifier rename is legible to a line-oriented search. A constraint about *shape* — here, that a runtime's methods stopped tolerating being destructured off their receiver — is not, because the offending code varies in layout while remaining semantically identical. A search written from one mental model of the pattern found five instances and missed five more nested one level deeper; a second search, written by the same reasoning, would have missed them again.

The remedy is not a better search. It is to encode the constraint mechanically — a test that walks the tree checking the property directly — so the check does not depend on having imagined every spelling. That the constraint then stays enforced afterwards is a second benefit, not the primary one.

## Why the audit checks multiple manifests

In a workspace, a package can be declared by more than one member. Upgrading the declaration that surfaced first left a second member on the prior major and the resolved tree carrying both, in a state where every check passed. The consuming code was split across the two, so a module the upgrade's own summary claimed to have audited was still running against the old version.

The rule this produced first said to confirm the resolved tree carries one copy afterwards, and that is the wrong reading of the incident. The signal was a *declaration* left behind; the duplicate copy was only how it showed. Reviewed on [PR #72](https://github.com/baseten/agent-skills/pull/72): in a workspace where every audited declaration has moved but an unrelated transitive dependency still requires the old major, the package manager retains both copies and is correct to. A rule demanding one copy calls that valid graph a failed upgrade, and an agent obeying it has exactly two moves — force an override the dependent never accepted, or drag an unrelated package forward — both of which ship more risk than the duplicate they remove.

So the check is on resolution of the audited declarations and their consumers, which is what the incident actually needed, and global deduplication is reserved for packages that must be singletons. That exception is not a hedge: for a registry, a context, or any package holding shared process state, a second copy is a real defect, it is invisible to a declaration-level check, and it is worth naming which kind applies rather than asserting the requirement in the abstract.

## Why mocks are excluded from characterization tests

A hand-built stub is constructed to satisfy the consumer, so it satisfies the pre- and post-upgrade contract simultaneously. It is therefore structurally incapable of detecting a shape change — the exact failure class characterization testing is for.

This is not hypothetical: a defect that blanked every data-driven view in one application survived a full suite of stub-based unit tests and was caught, immediately and on first run, by a test that rendered through the real provider. When the two disagree, the stub is measuring itself.

## Why "assert both directions" is a rule and not advice

An upgrade that tightens a constraint fails loudly. An upgrade that loosens one produces a suite that stays green while the guarantee evaporates. Only the rejection case detects loosening, and it is the case a test author writing from the happy path will not think to add.

Both assertion rules are written for a constraint over an input, and the [PR #72](https://github.com/baseten/agent-skills/pull/72) round found the domains where that has no referent — the non-validation rows of this contract's own *Silent failure modes* table. Layout, source-map alignment and bundle size have no case to reject and often nothing serialized to compare, so a worker applying the two rules literally either writes an assertion that measures nothing or decides the phase is inapplicable and falls back on the green build, which those rows exist to say is not the evidence.

The fix deliberately is not "apply these where they apply". An escape hatch phrased that way is taken by the same author who would have written happy-path-only assertions, and for the same reason. What replaces the rules is stated as an obligation of its own — capture the domain's measurement on the current version, compare it after — so the phase still produces a before/after comparison in every domain, and the only thing that varies is what is measured. The tolerance is fixed before the run for the same reason the contract forbids editing a failing test: a threshold widened to fit the result is that rule broken by another name.

## Why proxies for gates are forbidden

Substituting a cheap approximation for an available gate produced two false passes on a run where the real command was a single invocation away. The approximation — searching a lockfile for a version string — matched an unrelated occurrence in a file of tens of thousands of lines and reported both branches correct. CI then failed on the real check twice.

The generalisation is that a proxy's failure mode is a *false pass*, which is the most expensive kind, and its saving is usually smaller than one CI round trip.

## Why the lockfile is re-resolved against the base, not against the base as it was

A later incident, in a repository running several upgrades at once. One upgrade's branch was cut before a transitive package had been unified to a single version across the lockfile. The branch was not wrong about anything it changed; it simply resolved the *new* entries it introduced — a peer snapshot the upgrade added — against the tree as it stood when the branch was cut, pinning that transitive to the variant the base had since removed. It merged, and the stale resolution came back with it.

What makes this worth a rule rather than a caution is that every signal a worker is taught to trust stayed green. The install succeeded, the characterization tests passed, CI was clean, and the merge had no conflict — a conflict is what would have surfaced it, and there was none, because the two changes touched different entries of the same file. The evidence the rule asks for therefore has to be produced deliberately: re-resolve with the package manager against the base as it is at merge time, and diff for entries the branch introduces at versions the base does not carry.

It also compounds with two rules already here. "Branch from the latest `origin/<default>`" is a statement about the moment of cutting and says nothing about the hours after it, which is exactly the window this defect lives in. And an adopted bump PR is stale by construction — the queue proposed it at some earlier time — so adoption imports this failure mode rather than merely being exposed to it.

Hand-resolving is excluded for the same reason a grep on the lockfile is: it is a proxy for a resolution the package manager is the only authority on, and its failure mode is a false pass.

Round three of that PR then found the rule stated at a decision point this contract does not own. "Re-resolve immediately before merging" is correct about the moment and names an actor that does not exist here: this skill is dispatched to produce a PR and merges nothing, so the earliest it can act is handoff, and the base can go stale again in the hours before a human merges — reproducing the exact defect. That is mechanism 1 in `docs/review-fix-workflow.md`, and it is worth recording that the fix for the incident introduced it: a rule written where the failure was observed rather than where it can be executed reads as correct and is inert.

Round four then found the guard for that fix still carrying the instruction the fix had removed: the eval scenario written for the incident told the model to "re-resolve immediately before merging" and never mentioned the handoff record. That is worse than a stale paragraph. A stale sentence in a contract is a contradiction someone may notice; a stale eval **rewards** the rewrite that reintroduces the defect, and it does so at the one tier meant to catch a rewrite. The lesson is not specific to this rule: an eval is a restatement, so it belongs in the consequence sweep with every other restatement, and sweeping the prose while leaving the scenarios is how a guard comes to certify the thing it was built to stop. `scripts/check_contract_placement.py` now reads the eval corpus for exactly this.

Round five then found that guard green over a blank. It asserted the required phrase against the whole eval file, and a file is every field concatenated — so the check matched the text of an *assertion* while the expected answer it existed to pin had never contained the phrase at all. Dropping the requirement from the expected answer would have left it passing, which is the failure it was written to catch, one level up.

The rule that came out of it was half right, and round six supplied the other half. The first half stands: **a presence check must scope to the field that has to carry the requirement**, because a required phrase is required *somewhere specific* and a blob silently accepts it anywhere — including in the assertion that was supposed to be testing for it.

The second half was wrong as first stated. "A forbidden phrase is forbidden wherever it appears" conflates **use with mention**. A scenario whose prompt quotes the forbidden instruction so the model can reject it, or whose assertion requires that rejection, is the guard working — and a corpus-wide absence check blocks exactly that scenario, which is how a guard earns being deleted rather than fixed. So absence scopes to the expected answers, the only field that tells the model what to do, and skips occurrences negated within their own sentence.

Within that, one more correction, from writing the check rather than from review: negation was first looked for in a fixed window of preceding characters, and a negation belonging to the *neighbouring* sentence then marked a genuine prescription as a mention. "Do not claim it as a merge-time result. Re-resolve immediately before merging." passed. That is the exact regression the check exists to catch, and it passed the first negative test — so the window is a sentence, and the check is negative-tested in three directions rather than one: prescribed (fails), negated in its own sentence (passes), quoted in a prompt (passes).

Two more rounds settled it, and the settlement was to stop. A third supplied the opposite failure: the clause scope rejected `Do not merge or re-resolve immediately before merging.`, where one negation governs both coordinated verbs. So the function has now been wrong in both directions, and the two sentences that must be classified differently —

    Do not trust green CI and re-resolve immediately before merging.   (prescribes)
    Do not merge or re-resolve immediately before merging.             (mention)

— are identical in shape. The only surface signal separating them is the conjunction: under negation, disjunction distributes and conjunction does not, so `or` and `nor` carry the negator across while `and` opens a fresh imperative. That is a real asymmetry rather than an epicycle, but it is also the last one available, and the residual case (a comma-separated disjunction) is genuinely ambiguous in English too. A fourth round then found comma-separated imperatives — "Reject the stale handoff result, re-resolve immediately before merging." — where the negator carries across a bare comma. Fixing that requires treating a comma as a clause break, which immediately misreads "do not merge, or re-resolve …": the case documented one round earlier as ambiguous in English too. Tested rather than assumed, and it failed exactly there.

Four constructions, four rounds, each fix buying one and costing another: the surface signals are exhausted, and that is a property of the problem rather than of any particular regex. Deciding use from mention needs the semantics.

So the heuristic is deleted rather than extended, and what replaces it is decidable — **an expected answer states what it requires and never restates what it rejects.** That is an authoring convention rather than a device to satisfy a checker: the wrong instruction belongs in the prompt where a colleague suggests it, the assertions may name it freely, and only the expected answer is constrained, because that is the field that teaches. All eleven scenarios here already read that way, which is the evidence it is a real convention and not a rule invented to make a check pass. What it gives up is stated in the code: a paraphrase escapes it — as it escaped the heuristic too, which additionally carried an undecidable class.

This repository has now had four rounds in which a guard was green over a live violation of the thing it guarded. Every one was a scope error; none was a logic error. That is the thing to attack first when writing the next guard, and the way to attack it is to mutate the rule the guard protects and watch the guard fail — testing the direction you are already confident in proves nothing.

The resolution is not to weaken the moment but to stop pretending this skill occupies it. It re-resolves before pushing, records the base commit it resolved against in the PR body, and reports the result as a handoff result. That record is what converts "someone must remember to re-check" into a comparison anyone can make later, and it is why the contract forbids describing the handoff check as a merge-time one — a rule's own name attached to weaker evidence is the false pass in its purest form.

## Why absence of output is called out explicitly

Two distinct false positives on one run shared this root: a filter matching only success signals stayed silent through a crash, and an empty check rollup — checks not yet registered — was read as everything passing. In both, nothing was wrong with the observation; the error was treating "no evidence of failure" as "evidence of no failure".

For any watcher, the test is: *if this failed right now, would my filter emit anything?* If not, widen it.

## Why the silent-failure table is enumerated rather than generalised

Each row is a domain where the ordinary evidence of correctness — a green build — is uninformative, and where an agent will otherwise report success in good faith. The rows are not exhaustive, but naming them converts a general caution nobody acts on into a checklist that produces a specific sentence in the report: which check is the real evidence, and that the passing build is not it.
