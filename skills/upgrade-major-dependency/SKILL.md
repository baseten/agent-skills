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

Work in a dedicated worktree, never the main checkout. The **upgrade branch** is an adopted bump PR's head where one is supplied — **read that PR before branching from it** (see Task) — otherwise a branch from the latest `origin/<default>` unless a base is supplied. Either way that head already carries the bump, so it is never the baseline (see Characterization tests).

**Where a caller supplied a triage — a viability verdict, the coupled set, an adopted PR — the gate below reads it instead of re-deriving that item.** A caller that triaged the whole set knows things this task's scope cannot see, and re-deriving from inside it is how a cleared candidate stops on its own siblings. Re-derive only what the verdict does not cover, and report a disagreement rather than silently taking either answer.

**Split the verdict by whether a fact can change, not by which item it belongs to.** A licence, a publication date, a peer's published ranges and the coupled set are as true when this task starts as when triage cleared them; take those as given. Two things are not, because a bounded-concurrency dispatch can start a worker hours after its verdict was written:

- **Work already in flight** — long enough for a colleague to push a branch. Re-run that search immediately before writing anything, whatever the verdict said. The reason it was ever read from the verdict has since gone: the gate now distinguishes an automated bump from somebody else's attempt, so re-running it cannot reject the adopted PR the verdict named.
- **An adopted PR's state and head.** Its **URL is identity and does not change; nothing else about it is given.** In the same gap it can be merged, closed, superseded, or advanced past the head the verdict named — and the in-flight search will not surface a merged or closed one, because it searches open work. So read the PR itself before branching from it. Merged or closed: the upgrade may already be done or already declined, so verify against the installed version and report rather than branch and duplicate it. Advanced: branch from its current head. Superseded: adopt the successor on the same terms.

The phase order is load-bearing. Research precedes audit, audit precedes tests, tests precede the bump. Bumping first and reasoning backwards is how a silent behaviour change ships.

## Viability gate

Run before any other work; each item independently ends the task.

- **Licence.** Compare the new version's licence against the repository's accepted set. A permissive-to-copyleft change is an ownership decision, not an engineering one.
- **Install cooldown.** Where the package manager enforces a minimum release age, a version published inside that window is uninstallable. Never add a per-package exclusion to defeat a supply-chain control for a routine bump.
- **Peer caps.** Enumerate every package declaring one of this task's packages as a peer and confirm each has a release accepting the target major, resolving every cap against the group's **target** versions and not their installed ones — a companion moving in this same task lifts its own cap, and reading it as installed blocks the group on itself. A cap held outside the group with no compatible release anywhere is a hard blocker and reshapes the task.
- **Work already in flight.** Search open PRs and branches for every one of this task's package names immediately before writing anything — **this item is re-run even when a caller supplied a viability verdict clearing it**, because its answer expires between triage and implementation (see Task, which also covers the adopted PR's own state — this search sees only open work, so it cannot tell you that the adopted PR merged). Duplicating someone else's open work — a colleague's branch, another agent's attempt — ends the task. **An automated bump PR for these same packages is not that**: it is a machine's opening move on the work this task was sent to do, so adopt it — branch from its head, or supersede it and close it with a reference — and treat its diff as an input. Where a caller supplied one as adopted, that is settled; where the search found it, say so in the report.

A blocked upgrade is reported, not worked around. A documented dead end is a result.

## Research

Read the changelog **and** the upgrade guide, and read **every version in the range**, not only the major. Minors ship breaking changes; assume they do.

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
baseline worktree at the pre-upgrade commit   # NOT an adopted bump PR's head
write tests → prove green → commit (tests only)
cherry-pick that commit onto the upgrade branch
run untouched
```

Where practical, reset the baseline worktree to the exact parent of the upgrade commit so the sole variable between runs is the upgrade.

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

State what changed, what was audited and cleared, every behavioural difference and its classification, the base commit the lockfile was resolved against (see Migration and verification — it is what makes later staleness detectable, and it is the one item here a reader acts on rather than reads), and what a human must still verify manually. Follow the repository's PR conventions for the description; do not enumerate changed files or narrate the investigation.

If the upgrade proved unsafe, open nothing and report why. Where a bump PR was adopted a PR already exists, so instead close it carrying the reason, and record the decision where the repository tracks them — a closed PR's thread is not where the next attempt will look, and the queue re-proposes the same bump until something durable says why not.
