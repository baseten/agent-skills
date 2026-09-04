---
name: dependency-upgrade-orchestrator
description: Take a set of dependency upgrades, triage each against its changelog and the codebase's usage, establish coupling and viability, select a model per upgrade by failure mode, then dispatch isolated subagents that each run `upgrade-major-dependency`. Supervises CI and separates infrastructure failure from real failure. Use for a batch; use `upgrade-major-dependency` directly for one.
---

# Dependency Upgrade Orchestrator

## Task

Upgrade this set: $ARGUMENTS

This file is the contract; the reasoning behind its rules lives in `NOTES.md` beside it, keyed by section. NOTES explains; it never overrides.

Derive the set where none is supplied — the package manager's outdated report, a scheduled dependency report, or the open automated-bump queue.

**Triage is yours; implementation is delegated.** The research pass determines model selection, batching and viability, so it cannot be performed by the agents whose scope it defines.

## Enumerate

Bucket by distance behind: two or more majors (usually its own project, not a batch item), one major (the body of the work), minor and patch (cheap, but not assumed safe — a minor is a common source of breaking changes).

Order production dependencies before development ones.

## Triage each candidate

**Viability** — each independently removes a candidate: licence change against the repository's accepted set; publication inside an enforced minimum release age; a peer declaring a cap with no compatible release anywhere; work already open on a branch or PR.

**Breaking changes** — changelog and upgrade guide, every version in the range rather than only the major, verified against the published artifact where a rendered page could diverge from it.

**Usage surface** — modules importing it, APIs actually called, whether it reaches the shipped bundle. Treat the file count as an opening estimate that must be read critically: a framework bump importing into hundreds of modules reduced to a three-line configuration change because its migration flags were already enabled, while a package with a handful of direct imports required a new required provider, a changed session API and a rebuilt test double. Surface area predicts effort poorly in both directions.

**Coupling** — packages that cannot move independently form one task with one PR: a framework and its official companion packages; a plugin family with its shared peers; packages sharing a peer whose major is changing. Splitting a coupled group reproduces the failure mode of naive automated bumps — one package advanced, its siblings stale, installation failing against a version-pinned patch.

## Model selection

Select by **failure mode**, not by file count.

Assign the strongest available model where a wrong answer is **silent**: validation, authorization or monetary logic, where a constraint can loosen without erroring; framework or build configuration, where breakage is environmental rather than local; API rewrites requiring judgement about intent rather than mechanical rename; and any case where a regression's appearance cannot be described in advance.

Assign a mid-tier model where the surface is bounded and the failure mode is legible: a documented rename across known call sites; configuration-only bumps gated by a passing hook or job; migrations whose guide is accurate and whose diff is mechanical.

Where an escalation tier requires authorization, request it rather than assuming; across a thirteen-package batch it was needed zero times.

Where the estimate is uncertain, over-assign. Over-assignment costs budget; under-assignment costs a silently incorrect migration.

## Dispatch

One subagent per upgrade or coupled group, each in **its own worktree**, each invoking `upgrade-major-dependency`.

Supply each agent with the completed triage — breaking changes, usage surface, coupling — rather than having it re-derive them. Supply its worktree path and exact base branch.

Constrain each agent explicitly:

- **Foreground execution only.** No backgrounded long-running commands, no monitors. An agent that backgrounds a command and ends its turn waits on a wake-up that does not arrive.
- **No full-suite runs** where the suite is sharded across CI runners. Scoped runs plus CI.
- **Stopping and reporting outranks producing a PR.** State that a documented dead end is an acceptable and valuable outcome.

**Bound concurrency.** Agents each running a test suite are not free; a batch dispatched at full width exhausted one machine's memory and killed a quarter of the run. Begin narrow and widen as agents complete. Where CI builds container images, stagger pushes — simultaneous multi-architecture builds exhaust shared infrastructure the run does not own.

## Supervise

Gate "green" on the repository's actual required check concluding successfully. A rollup that is empty or barely populated means checks have not registered; reporting it as green is a false pass.

Emit only state **changes**, and only actionable ones. A value that varies for reasons unrelated to state — a count, a timestamp — re-emits every unchanged entry on every tick.

**Separate infrastructure from code.** Builder timeouts, image-build transport errors and browser-harness teardown messages are not the change under test. Confirm by checking whether unrelated branches, and the default branch, fail the same job; where the failure is repository-wide, re-running is futile and escalation is the useful action.

Read a **changed** failure signature carefully. A signature that narrows after a fix indicates one defect with multiple sites, not a failed fix.

## Close out

Per upgrade, a PR following the repository's conventions. Across the batch, report what landed, what was declined and why, and what remains blocked on a decision only a human can make.

Record declined upgrades where decisions are tracked rather than in a closed PR, since the next attempt begins from the same outdated list.

Report infrastructure findings the batch surfaced. A run of this shape reliably exposes gaps nobody was searching for; passing them on is more valuable than routing around them.
