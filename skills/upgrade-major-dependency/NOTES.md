# upgrade-major-dependency — design notes

Companion to `SKILL.md`. That file is the contract; this one holds the reasoning behind its rules, keyed by section. Read a section's note before changing its rules or when applying them to a case the contract doesn't obviously cover. Nothing here overrides the contract.

These rules were derived from upgrading thirteen packages across major versions in one repository. Every rule below exists because its absence cost something on that run.

## Why the phase order is load-bearing

The contract fixes research → audit → tests → bump, and the fixed point is that **tests precede the bump**. This is not stylistic sequencing.

A test written after a migration encodes the behaviour the migration produced. If the migration introduced a defect, the test passes and enshrines it. A test written against the prior version, proven green there, then executed unchanged, tests a different proposition: not "the new code does what this test says" but "the new code does what the old code did". Only the second proposition is what an upgrade is claiming.

The empirical case: four packages on that run already carried post-migration tests, all green. Written the other way round, the same four surfaced a customer-facing regression that had passed every existing suite, and a false causal claim in a PR description that no reviewer could have checked. The difference was ordering alone.

This also explains why the contract forbids editing a failing characterization test. The failure is the signal the phase exists to produce; suppressing it returns the exercise to the post-hoc case it was designed to escape.

## Why viability is gated before research

Each gate item ended a real upgrade before any code was written, and each is minutes of work against hours.

The licence gate is the sharpest: a package that relicensed from permissive to copyleft failed the repository's licence check outright. That is not a migration problem with a technical solution — it is an ownership decision about whether the organisation may ship the code at all, and an agent that migrates first and discovers it second has spent the entire budget on an artifact that cannot merge.

"Work already in flight" is included because it nearly produced a duplicate of a colleague's five-week-old branch covering the same 69 files. Nothing in the dependency's own metadata reveals this; only searching the repository's open work does.

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

## Why mocks are excluded from characterization tests

A hand-built stub is constructed to satisfy the consumer, so it satisfies the pre- and post-upgrade contract simultaneously. It is therefore structurally incapable of detecting a shape change — the exact failure class characterization testing is for.

This is not hypothetical: a defect that blanked every data-driven view in one application survived a full suite of stub-based unit tests and was caught, immediately and on first run, by a test that rendered through the real provider. When the two disagree, the stub is measuring itself.

## Why "assert both directions" is a rule and not advice

An upgrade that tightens a constraint fails loudly. An upgrade that loosens one produces a suite that stays green while the guarantee evaporates. Only the rejection case detects loosening, and it is the case a test author writing from the happy path will not think to add.

## Why proxies for gates are forbidden

Substituting a cheap approximation for an available gate produced two false passes on a run where the real command was a single invocation away. The approximation — searching a lockfile for a version string — matched an unrelated occurrence in a file of tens of thousands of lines and reported both branches correct. CI then failed on the real check twice.

The generalisation is that a proxy's failure mode is a *false pass*, which is the most expensive kind, and its saving is usually smaller than one CI round trip.

## Why absence of output is called out explicitly

Two distinct false positives on one run shared this root: a filter matching only success signals stayed silent through a crash, and an empty check rollup — checks not yet registered — was read as everything passing. In both, nothing was wrong with the observation; the error was treating "no evidence of failure" as "evidence of no failure".

For any watcher, the test is: *if this failed right now, would my filter emit anything?* If not, widen it.

## Why the silent-failure table is enumerated rather than generalised

Each row is a domain where the ordinary evidence of correctness — a green build — is uninformative, and where an agent will otherwise report success in good faith. The rows are not exhaustive, but naming them converts a general caution nobody acts on into a checklist that produces a specific sentence in the report: which check is the real evidence, and that the passing build is not it.
