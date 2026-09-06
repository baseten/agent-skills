---
name: upgrade-major-dependency
description: Upgrade one dependency, or one coupled group of them, across a version whose breaking-change risk has not been ruled out — establish viability, research real breaking changes against the published package, audit usage, pin current behaviour with characterization tests written and proven green before the upgrade, migrate, then classify every behavioural difference. Use for any semver-major bump, and for any minor or patch bump not already cleared of breaking changes by an audit; a small version number is not evidence of a small change.
---

# Upgrade a Major Dependency

## Task

Upgrade: $ARGUMENTS

This file is the contract; the reasoning behind its rules lives in `NOTES.md` beside it, keyed by section. NOTES explains; it never overrides.

`$ARGUMENTS` is one package, or one **coupled group** whose members cannot move independently — a framework with its official companions, a plugin family sharing a version line. A group is one task, one branch and one PR throughout, and every rule below reads over all of its packages.

The version distance does not decide whether this skill applies; **unruled-out risk of a breaking change does**. A major always qualifies. So does any minor or patch a triage has not cleared — the phase order below is what clears it, and a bump nobody has audited is exactly the case where the number is the least informative thing about it. A lesser bump already cleared by a caller's research and usage audit is a routine bump and does not need this skill at all.

Work in a dedicated worktree, never the main checkout. Two cases, and they differ in exactly one way that matters later:

- **An adopted bump PR** — its head is the upgrade branch. **Read that PR before branching from it** (see Task). Its head already carries the bump, so it is never the baseline; take that from the PR's merge base (see Characterization tests).
- **No adopted PR** — branch from the latest `origin/<default>` unless a base is supplied. That branch still carries the *current* version, so it is the baseline, and stays one until the bump is applied to it. Do not cut a second worktree for it.

**A moved target ends this task; it does not reshape it.** Reuse is worth having: a caller that triaged the whole set knows things this task's scope cannot see, and re-deriving from inside one task is how a cleared candidate stops on its own siblings. But a bounded-concurrency dispatch can start a worker hours after triage, and everything triage concluded about a package it concluded about **one release**. **Compare each package's current target against the one triage measured for it before reusing any of it** — a bot updating its own PR to a newer release is the ordinary way all of it goes stale at once. **What moves a target is the adopted PR's head**, so that comparison is answered by reading that PR (below) and cannot precede it. Where there is no adopted PR nothing moves a target: it is the one the caller named, and a newer release appearing upstream mid-task is not a moved target — reading it as one stops every task the moment its registry publishes anything.

Where a target moved, **what survives is identity only**: the package names, and an adopted PR's URL. Everything else is void — that package's licence, install cooldown, breaking-change research and usage audit, and two conclusions that reach across the whole task, because both are relations over the targets rather than properties of one member:

- the **peer resolution**, since each release carries its own peer range: a companion at v3 demanding framework@3 breaks a framework@2 clearance whose own target never moved;
- the **coupled set itself**, since which packages must move together is *derived* from those peer requirements — A@3 may require a compatible B@3 where A@2 accepted the installed B.

**Two of the decisions built on that triage are the caller's, not this task's, which is why the answer is to stop rather than to re-derive and continue:**

- **membership** — absorbing a new member upgrades a package nobody triaged; dropping one splits a coupled group, the failure the grouping exists to prevent;
- **the model this task is running under** — selection keys on a failure mode derived from the research, and an agent cannot revise its own assignment. A release that advanced from a mechanical rename into a silent-failure domain needs a different model, and a worker that re-reads the range, sees exactly that, and proceeds anyway has produced the one migration the selection rule exists to prevent.

So re-read enough to make the report useful — **a package → current target mapping covering every package that moved**, what the range up to each new target says about failure mode, the recomputed set, and, where a peer range is what moved, **the incompatible tuple** that voids the clearance — and then **report and stop**. The re-reading serves the report, not the continuation. This costs a dispatch round trip in the common case where a bot advanced a patch and nothing material changed; that is the correct trade, because the failure it prevents is silent and this stop is not.

**Two things are never taken from a verdict at all**, whether or not a target moved:

- **Work already in flight**, because a colleague can push a branch in the gap. Re-run that search immediately before writing anything. The reason it was ever read from the verdict has since gone: the gate now distinguishes an automated bump from somebody else's attempt, so re-running it cannot reject the adopted PR the verdict named.
- **An adopted PR's state and head.** Its **URL is identity and does not change; nothing else about it is given.** In the same gap it can be merged, closed, superseded, or advanced — and the in-flight search will not surface a merged or closed one, because it searches open work. So read the PR itself before branching from it. Merged or closed: the upgrade may already be done or already declined, so verify against the installed version and report rather than branch and duplicate it. Advanced: check whether any package's target moved with it — if so, that ends the task (above) — and otherwise branch from its current head. Superseded: adopt the successor on the same terms.

Re-derive anything the verdict does not cover, and report a disagreement rather than silently taking either answer.

The phase order is load-bearing. Research precedes audit, audit precedes tests, tests precede the bump. Bumping first and reasoning backwards is how a silent behaviour change ships.

## Viability gate

Run before any other work; each item independently ends the task. A supplied verdict stands in for the licence and cooldown items **only while that package's target is the one it measured for it**, and for the peer item **only while no member's target has moved at all**. A moved target ends the task the way any gate item does — it puts membership and model selection back in the caller's hands (see Task). The fourth item is re-run always.

- **Licence.** Compare the new version's licence against the repository's accepted set. A permissive-to-copyleft change is an ownership decision, not an engineering one.
- **Install cooldown.** Where the package manager enforces a minimum release age, a version published inside that window is uninstallable. Never add a per-package exclusion to defeat a supply-chain control for a routine bump.
- **Peer caps.** Enumerate every package declaring one of this task's packages as a peer and confirm each has a release accepting the target major, resolving every cap against the group's **target** versions and not their installed ones — a companion moving in this same task lifts its own cap, and reading it as installed blocks the group on itself. A cap held outside the group with no compatible release anywhere is a hard blocker and reshapes the task. Because this resolves over the whole tuple rather than one package, a supplied clearance for it dies as soon as **any** member's target moves — not only the one whose cap you are reading (see Task).
- **Work already in flight.** Search open PRs and branches for every one of this task's package names immediately before writing anything — **this item is re-run even when a caller supplied a viability verdict clearing it**, because its answer expires between triage and implementation (see Task, which also covers the adopted PR's own state — this search sees only open work, so it cannot tell you that the adopted PR merged). Duplicating someone else's open work — a colleague's branch, another agent's attempt — ends the task. **An automated bump PR for these same packages is not that**: it is a machine's opening move on the work this task was sent to do, so adopt it — branch from its head, or supersede it and close it with a reference — and treat its diff as an input. Where a caller supplied one as adopted, its **identity** is settled and its state is not (see Task); where the search found it, say so in the report.

A blocked upgrade is reported, not worked around. A documented dead end is a result.

## Research

Read the changelog **and** the upgrade guide, and read **every version in the range**, not only the major. Minors ship breaking changes; assume they do.

Supplied research is reusable on the same condition as the gate's findings and no other: it described one target, so if that package's target moved it describes a release you are not installing (see Task). **That case does not resume here.** A moved target ended the task at the gate, and the only reading still owed is the one the report needs: the range up to the new target, read for what it says about failure mode and **reported rather than acted on**. Extending the old notes to cover the new range is the continuation the stop exists to prevent — and it arrives looking like diligence.

Verify against the **published artifact** rather than a rendered docs page where the two could diverge — changelog pages have been observed conflating an unrelated major's notes with the current one. For any load-bearing question ("is our patch still required?", "did this matcher's semantics move?"), read the installed source or diff two published versions directly. Diffing sources answers behavioural questions that prose about them cannot.

Record what applies, and separately **what was checked and cleared**. A reviewer cannot distinguish a thorough audit from an absent one without the second list.

## Usage audit

Establish which modules import the package and which APIs are actually called.

Two systematic blind spots:

- **Shape-based breaking changes evade line-oriented search.** Where a constraint concerns destructuring or object shape rather than an identifier, a grep under-reports it, and a second grep written from the same mental model under-reports it identically. Encode a mechanical constraint as a test that scans the tree, not as a search you repeat.
- **A package may be declared in more than one manifest.** In a workspace, confirm **every** manifest declaring it; a declaration left behind is the defect this looks for, and the upgrade's own summary will claim to have covered the module it strands.
  Confirm that afterwards by resolving the audited declarations and their consumers to the target version — **not by counting copies in the tree**. A second copy is a correct resolution wherever an unrelated transitive dependency still requires the old major, and reading it as a failed upgrade drives the two repairs that are genuinely unsafe: an override forcing a version its dependent never accepted, or an unrelated package dragged forward to collapse the duplicate. Require one resolved copy only where the package must be a singleton — one registry, one context, one instance of shared state — and where it must, say which of those it is, because there a duplicate is a real defect that no declaration-level check finds.

Also establish: version-pinned patches against this package (they will fail to apply), and whether it reaches the shipped bundle at all.

## Characterization tests

Write tests against the **current** version, prove them green there, commit them alone, then apply that commit **unmodified** to the upgrade branch and run it.

```
adopted PR        baseline = that PR's merge base, in its own worktree
                  write tests → prove green → commit (tests only)
                  cherry-pick that commit onto the PR's head → run untouched

no adopted PR     the upgrade branch is already the baseline — one worktree
                  write tests → prove green → commit (tests only)
                  apply the bump on top → run that same commit untouched
```

**What is invariant is the ordering, not the mechanism.** The tests are proven green on a tree that does not carry the bump and then run unmodified on one that does; whether that takes a cherry-pick depends only on how many branches are involved. With no adopted PR there is one branch, the test commit is already its ancestor, and cherry-picking it is at best a no-op — so the bump goes on top instead, and no second worktree is cut.

Where the adopted case leaves a choice, reset the baseline worktree to the exact parent of the upgrade commit so the sole variable between runs is the upgrade.

**An adopted bump PR's head is never the baseline.** It already carries the bump, so tests written and proven green there are post-migration tests wearing this phase's name — the precise inversion the phase order exists to prevent, and it arrives looking like ordinary compliance. Take the baseline from that PR's merge base and cherry-pick forward onto its head.

Rules:

- **Exercise the real integration, not a mock.** A hand-built stub satisfies the old and new shape simultaneously, so it cannot detect a shape change. Drive the real component, provider, or form.
- **Assert both directions** — a case that must be rejected and one that must be accepted. Happy-path-only assertions prove nothing about a constraint loosening.
- **Assert exact output.** Equality on the serialized value, not containment.
- **Where the behaviour is not a constraint over an input, both rules above have no referent — and the substitute is mandatory, not an exemption.** Layout, source-map alignment, bundle size and the rest of the Silent failure modes table's non-validation rows have no case to reject and often no serialized value, so a worker applying the two rules literally either invents an irrelevant assertion or quietly skips the phase. Instead, capture that domain's own measurement on the current version and compare it after: a visual-regression baseline, a lookup of a known source position through the map, a byte count. Fix any tolerance **before** the run — a threshold widened to accommodate what the run produced is the edited-test rule broken by another name — and name the measurement in the report, because it is the evidence the passing build is not.
- **Never edit a test to make it pass.** Each difference is a regression — report prominently, it is the highest-value output of the phase — or an intended change, updated with a comment recording why. Classify honestly; never relabel a regression as intended.

A characterization failure after the upgrade is the mechanism working. It converts a silent change into a reviewable decision.

## Migration and verification

Apply the bump and the call-site changes the research identified. Run the repository's documented checks in its documented order.

Run **scoped** tests locally. Where a suite is sharded across CI runners it does not fit on one machine; scoped runs plus CI is the correct division, and CI is the authority.

**Verify with the gate itself, never a proxy.** Where the gate is a command available locally, run that command. Approximating a lockfile check by searching the lockfile for a version string returns false passes. The real check is usually cheaper than the CI round trip it replaces.

**Re-resolve the lockfile against the base before pushing, and record which base.** A branch cut before a lockfile change landed on the base — another upgrade's merge, a dedupe, a version unified across the tree — resolves the entries *it* adds against the tree as it was, and can pin a transitive to a version the base no longer carries. Every signal stays green: the branch installs, the characterization tests pass, CI is clean and the merge has no conflict, and the merged lockfile carries a resolution the base had removed. So bring the base in and re-resolve with the package manager — never by hand, and never by settling a lockfile conflict textually — then diff the lockfile against the base and account for **every** entry the branch introduces at a version the base does not carry. An adopted bump PR is stale by construction: it was cut whenever the queue proposed it.

**That result expires, and this task ends at handoff.** This skill produces a PR and merges nothing, so it cannot hold the check at the moment that decides the outcome; a rule telling it to act "immediately before merging" names an actor this contract does not have. What it can do is make later staleness visible instead of leaving it to be remembered: **state in the PR body the base commit the lockfile was resolved against**, and that the re-resolution must be repeated if the base has moved since. Report it as a handoff result and never as a merge-time one — the same false pass this rule exists to prevent, wearing the rule's own name.

**Absence of output is not success.** A filter matching only the success signal is silent through a crash. An empty or barely-populated check rollup means checks have not registered, not that they passed — and one required check concluding successfully while another is pending or failing is the same false pass reached from the other side. Green is **every** check the repository requires having concluded successfully on the current head.

## Silent failure modes

Type checks and unit tests do not detect these. For any that apply, state in the report what the real evidence is and that the passing build is not it.

| Domain | Silent change |
|---|---|
| Validation | Constraints loosen; invalid input begins passing. Also which rule reports, deciding the message a user reads |
| Test matchers | A matcher loosens, converting an assertion into a no-op no suite can flag |
| Serialization | Output shifts by characters; the difference persists to storage, not to a test |
| Source maps | Still emitted, now misaligned. Visible only when debugging production |
| Build transforms | Output subtly wrong, exit code zero |
| Animation / layout | Visual regression tooling only |
| Hook and glob configs | Config stops matching; the hook passes by running nothing |
| Bundle size | A compatibility layer or new transitive dependency adds weight nobody measures |

## Report

State what changed, what was audited and cleared, every behavioural difference and its classification, the base commit the lockfile was resolved against (see Migration and verification — it is what makes later staleness detectable, and it is the one item here a reader acts on rather than reads), and what a human must still verify manually. Three further items are required by the phases that produce them, and are listed again here because **this is the section an agent writes the report from**, so an obligation stated only where it arises is the one that goes missing: the measurement standing in for a rejected/accepted pair where the behaviour is not a constraint over an input (see Characterization tests); for every applicable row of the silent-failure table, what the real evidence is and that the passing build is not it (see Silent failure modes); and, where the in-flight search rather than the caller found the adopted bump PR, that it did (see Viability gate). Follow the repository's PR conventions for the description; do not enumerate changed files or narrate the investigation.

A task ended by a moved target reports a **package → current target mapping for every package that moved**, the refreshed failure-mode reading per moved package, the recomputed coupled set, and — where a peer range is what moved — **the incompatible tuple**, naming which package at which version demands what of which other, so the caller can re-triage and re-dispatch without repeating the reading (see Task). The tuple is the evidence for the group-wide void, and without it the caller re-resolves peers this task has already resolved. The mapping is symmetric with the one dispatch supplies and for the same reason: a single figure cannot say which new version belongs to which package, so a caller re-triaging from it attaches a refreshed finding to one member while keeping a stale target for another — the failure that made the forward direction a mapping, recreated on the way back.

**A task ended by a moved target leaves an adopted PR open**, and the rule below is not about it: the upgrade was not judged unsafe, the caller re-dispatches, and that PR's URL is the one thing the move leaves standing (see Task). Closing it hands the re-dispatch a dead identity and re-proposes the bump from scratch.

If the upgrade proved unsafe, open nothing and report why. Where a bump PR was adopted a PR already exists, so instead close it carrying the reason, and record the decision where the repository tracks them — a closed PR's thread is not where the next attempt will look, and the queue re-proposes the same bump until something durable says why not.
