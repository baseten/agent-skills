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

"Work already in flight" is included because it nearly produced a duplicate of a colleague's five-week-old branch covering the same 69 files. Nothing in the dependency's own metadata reveals this; only searching the repository's open work does.

That item was written from that case and phrased for it — *any* open PR naming the package. The review round on [PR #72](https://github.com/baseten/agent-skills/pull/72) found the case it therefore swallows: an automated bump PR for the same package is not a duplicate of the work, it *is* the work, and under a caller whose whole candidate set was derived from the bump queue the item removes every candidate it was handed. The distinction the item now draws is between work this task was sent to do and work someone else already started, which is what the colleague's-branch case was about all along.

A later round drew the line the first version of that rule missed. A supplied verdict is a **snapshot**, and most of what it contains cannot go stale — a licence, a publication date, a peer's published ranges, the coupled set. Work already in flight can, and bounded concurrency is precisely what opens the gap: an agent can start hours after its verdict was written, which is long enough for a colleague to push a branch. So that one item is re-run and the rest are not.

The principle underneath took three rounds to state, and only the third version is safe. First: reuse the verdict. Then: reuse it except for what expires. Now: **reuse a finding only while the thing it measured has not moved** — which subsumes both earlier versions and closes a hole neither saw.

The hole is that a licence, a cooldown window and a peer cap are findings *about a target version*, and an adopted PR that advanced may have moved the target. A bot bumping its own PR to a newer release is the ordinary way a licence change, a release published inside the cooldown window, or a fresh peer cap appears after triage cleared all three — and the previous version of the rule, which asked only whether a fact *can change over time*, answered "no, a licence does not change" and branched from the new head. The question was the wrong one: the licence had not changed, the package had.

The round after stating it found the previous version still standing immediately above the new one, as a bold summary sentence saying those findings "cannot have changed" — contradicting the rule two lines below it, inside one section. It was not reconciled, it was **deleted**: a summary of a rule sitting beside that rule serves no decision point of its own, and this one drifted from its source within a single round, which is the shortest drift interval on this PR by a wide margin. The unique content it carried (why reuse is worth having at all, and to report a disagreement rather than resolve it silently) moved into the rule. There is now one statement, and an assertion that there is exactly one.

One further correction: a target-version finding is about **one package** at one version, and this skill's unit of work is a coupled group. Members can sit on different version lines, and the peer gate resolves caps against the group's targets rather than a single one — so "the triaged target" was the wrong shape as well as the wrong question, and a companion's clearance would have stayed attached to an older target while the group read as checked. Reuse is per package, and the comparison runs for every member.

So the sort is by what each finding is about. Target-version findings are conditional on the target; the coupled set is about which packages move together and survives a target change; work in flight and the adopted PR's state expire regardless. Comparing the current target against the triaged one is now the first thing the adopted-PR path does.

The split was drawn at the wrong granularity first, and the next round found it: it separated *items* of the verdict when what varies is *facts*. An adopted PR is one item, but its URL and its state are two facts with opposite lifetimes — the URL is identity and never changes, while in the same dispatch gap the PR can merge, close, be superseded, or advance past the head the verdict named. The dangerous case is the merged one, because the refreshed in-flight search cannot see it: that search looks at open work, so a worker would branch from a stale head and redo an upgrade that already landed. So the PR is read before it is branched from, and the contract says *URL is identity, nothing else about it is given* rather than naming the item.

The round after that found the fact-level split stated below a sentence that still granted reuse per *item* — "the gate reads a viability verdict, the coupled set, an adopted PR instead of re-deriving that item" — so the section contradicted itself, and the gate item below still called a supplied adoption "settled". Worse, the item-level phrasing was **mechanically required by an assertion**, which is how it survived a round: the guard was holding the contradiction in place. Reuse is now scoped to the facts that cannot have changed, and the assertion keys on that scoping rather than on the sentence around it.

The general form is worth keeping: **a guard keyed on wording rather than on what a rule turns on does not merely fail to catch drift, it can require it.** That is the sharper version of the lesson two rounds earlier about assertions going stale — a stale assertion that fails is cheap, one that passes costs a round, and one that *pins the wrong text* costs a round and resists the fix.

Worth noting why the original reason for reading it from the verdict is gone rather than overridden. It was read from the verdict because re-deriving it made the agent stop on the adopted bump PR — but the gate now distinguishes an automated bump from somebody else's attempt, so a refreshed search recognises that PR instead of rejecting it. The constraint that justified the shortcut was removed two rounds earlier and the shortcut outlived it, which is its own small lesson: when a rule is relaxed, the workarounds built on the old version are the next thing to sweep.

The same round is why the gate reads a supplied verdict where one exists. A caller that triaged the whole set — `dependency-upgrade-orchestrator`, *Dispatch* — resolved peer caps against the coupled group's target versions and cleared any adopted PR. Re-deriving those inside one task's scope reaches a different answer, and the answer it reaches is a stop: a companion moving in the same task still declares its cap at the installed major. Re-derivation is kept for everything the verdict does not cover, and a disagreement is reported rather than resolved silently, because the gate is still the last thing standing between a stale triage and a migration nobody may ship.

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
