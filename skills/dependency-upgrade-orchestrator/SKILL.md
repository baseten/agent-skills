---
name: dependency-upgrade-orchestrator
description: Take a set of dependency upgrades, triage each against its changelog and the codebase's usage, establish coupling and viability, select a model per upgrade by failure mode, then dispatch isolated subagents — one per upgrade or coupled group running `upgrade-major-dependency`, plus one batched task for the routine bumps triage cleared, which need no migration workflow. Supervises CI and separates infrastructure failure from real failure. Use for a batch; use `upgrade-major-dependency` directly for one.
---

# Dependency Upgrade Orchestrator

## Task

Upgrade this set: $ARGUMENTS

This file is the contract; the reasoning behind its rules lives in `NOTES.md` beside it, keyed by section. NOTES explains; it never overrides.

Derive the set where none is supplied — the package manager's outdated report, a scheduled dependency report, or the open automated-bump queue.

**An automated bump PR for a candidate is never work already in flight — it is the work.** Mark it **adopted** and carry it by URL through triage into dispatch: the upgrade continues on it — branch from its head, or supersede it and close it with a reference — and its diff is an input rather than a competing attempt. **Where the candidate came from does not enter into this.** Deriving the set from the open bump queue makes the point unmissable, since there every candidate arrives already open as a PR and the viability item would empty the batch it just produced — but a candidate derived from the outdated report whose triage then finds a bot PR is the same case, and dropping that one is the same defect committed quietly. What removes a candidate is somebody else's attempt at the same upgrade — a colleague's branch, another run's PR — which is a duplicate (see Triage each candidate).

**Triage is yours; implementation is delegated.** The research pass determines model selection, batching and viability, so it cannot be performed by the agents whose scope it defines.

## Enumerate

Bucket by distance behind: two or more majors (usually its own project, not a batch item), one major (the body of the work), minor and patch (cheap, but not assumed safe — a minor is a common source of breaking changes).

That last bucket is not assumed safe and is not assumed unsafe either; **triage decides which, and the answer decides how the candidate is dispatched** (see Dispatch). A minor or patch its research and usage audit clear — no breaking change in any version in the range, no affected call site — is a routine bump. One triage did not clear is a breaking change wearing a small version number, and is dispatched exactly like a major.

Order production dependencies before development ones.

## Triage each candidate

**Viability** — each independently removes a candidate: licence change against the repository's accepted set; publication inside an enforced minimum release age; a peer declaring a cap with no compatible release anywhere — **resolved against the candidate's coupled group, which is therefore established before this item is answered**, since a peer moving inside the group lifts its own cap and a candidate rejected on one is rejected by its own siblings; work already open on a branch or PR **other than an automated bump PR for this candidate** — a colleague's branch or another run's attempt is a duplicate and removes the candidate, while any bot bump PR for the package is the work itself, whatever discovery source produced the candidate, and is adopted or repaired rather than filtered out (see Task). `upgrade-major-dependency`, *Viability gate*, draws the same line at the agent's own gate, and the two must not disagree about it.

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

One subagent per upgrade or coupled group, each in **its own worktree**, each invoking `upgrade-major-dependency` — which covers a major, and any lesser bump whose triage did **not** clear it of breaking changes. Send everything in that scope through it, whatever the version number says.

**Routine bumps do not each get one.** A minor or patch triage cleared (see Enumerate) has nothing for the phase order to do: there is no migration to research and no behaviour to characterize, and dispatching one agent apiece spends a worktree and a test suite per candidate to prove that. Group them into a single task with one PR, and say in the report which candidates were cleared and on what evidence — a cleared candidate is a triage conclusion like any other, and the next run reads it as one.

**A routine clearance is about one release, so re-check every batched candidate's target immediately before that task lands.** This is the sharpest edge of the target rule and it cuts differently from the others: the clearance is not only a finding, it is a **routing decision**, and the route it chose has no viability gate in it. A candidate cleared as a routine patch whose adopted PR then advances to a release carrying a breaking change rides the batch straight past `upgrade-major-dependency` — no research, no usage audit, no characterization tests — and every check it does encounter passes. Where a batched candidate's target moved, its clearance is void: pull it out, re-triage against the new target, and dispatch it like any uncleared bump. The same move also invalidates the model selection that clearance implied, since that keys on a failure mode derived from the old release's research.

Supply each agent with the completed triage — **the viability verdict, the exact target version it measured for every package in the task, and the coupled set**, breaking changes, usage surface — rather than having it re-derive them. Supply its worktree path, its exact base branch, and any adopted bump PR by URL.

**The first two are supplied because the agent's own gate reaches a different answer without them, not to save it work.** `upgrade-major-dependency` re-runs its viability gate over what its own scope can see, and the coupled set is what it cannot: a peer cap that another member of the same group lifts reads there as a hard blocker, stopping an agent on a candidate this triage already cleared. Breaking changes and usage surface are safe for an agent to re-derive and are supplied only to save the duplicated work. (The adopted PR was once on this list too — re-derivation used to read it as work already in flight — but the gate now distinguishes an automated bump from somebody else's attempt, so it is supplied as identity rather than to prevent a wrong stop.)

**The verdict does not cover what can change in the dispatch gap, and must not be presented as though it does.** Two things expire, because bounded concurrency can start an agent hours after triage cleared it: work already in flight — a colleague's branch pushed in between is exactly what that item exists to catch — and **the adopted PR's own state**, which can merge, close or advance in the same window. The agent refreshes both itself (`upgrade-major-dependency`, *Task*); supply the adopted PR **by URL, as identity rather than as a state** — the refreshed search recognises it rather than stopping on it, and the agent reads its current state before branching.

**The verdict's licence and cooldown findings — and the breaking-change research and usage audit — are each about one package at one version, so name the target per package.** An adopted PR that advanced may have moved a target, which invalidates all four for that package, and the agent is required to compare current against triaged before reusing them (`upgrade-major-dependency`, *Task*). **It cannot run that comparison against a version this dispatch never named** — a rule whose operand is not forwarded cannot fire, and the failure is silent, because reuse of a stale clearance looks like compliance.

**One target for the task is not enough, because a coupled task has several.** Its members can sit on different version lines, and the agent's peer gate resolves caps against the group's target versions rather than one of them, so a single figure cannot say which version each finding measured — and a companion's clearance stays attached to an older target while the check reads as done. Forward a **package → triaged target** mapping covering every member, and the agent compares each.

**The peer finding is the exception to per-package, and the mapping is what makes it checkable.** A peer range is a relation between packages, so any member advancing can void another member's clearance while that member's own target sits unchanged; the agent re-runs the peer check over the whole tuple whenever any target moved (`upgrade-major-dependency`, *Task*). A partial mapping is worse than none here: it lets every individual clearance read as valid while the combination goes unchecked.

**Coupling is target-derived too, so nothing in a verdict survives a moved target except identity.** Which packages must move together comes from peer requirements at the target versions — this section's own definition includes packages sharing a peer whose major is changing — so A advancing to a release requiring a compatible B@3 where A@2 accepted the installed B *adds B to the group*. The agent recomputes the set and, finding it different, **reports and stops rather than reshaping its own task**: membership is this layer's decision, and an agent that absorbs a new member has upgraded a package nobody triaged.

**Expect that stop on any moved target, not only a changed set, and treat it as the dispatch working rather than a worker failing.** The agent cannot revise its own model assignment, and selection keys on a failure mode derived from research the move invalidated — so a release that advanced from a mechanical rename into a silent-failure domain must come back here to be re-selected, or a mid-tier agent implements exactly the migration the selection rule exists to catch. The return carries the new target, the refreshed failure-mode reading and the recomputed set, so re-triage and re-dispatch cost a round trip and not the reading. That round trip is the price of the routine-bump re-check above being the *only* place a moved target was previously caught.

Constrain each agent explicitly:

- **Foreground execution only.** No backgrounded long-running commands, no monitors. An agent that backgrounds a command and ends its turn waits on a wake-up that does not arrive.
- **No full-suite runs** where the suite is sharded across CI runners. Scoped runs plus CI.
- **Stopping and reporting outranks producing a PR.** State that a documented dead end is an acceptable and valuable outcome.

**A batch shares one lockfile, and staleness compounds across it.** Every agent branches from the same base and resolves the lockfile against it independently, so each merge moves that base under every PR still open. Nothing announces the consequence: a branch cut before another's merge resolves its *new* entries against the tree as it was, and can pin a transitive to a version the base no longer carries.

**This run merges nothing, so it cannot hold that check at merge time — it carries the check there instead.** Require each agent to re-resolve before pushing and to record the base commit its lockfile was resolved against (`upgrade-major-dependency`, *Migration and verification*). Then compare that recorded base against the current base on every supervision pass and again at close-out, and **name every open PR whose lockfile has gone stale**. That comparison is this layer's actual job here, it costs one read per PR, and it is the only thing standing between a handoff-time result and a merge that trusts it hours later. A stale PR is redispatched for a re-resolution pass like any other repair — never merged on the strength of the handoff check, and never reported green on it. Where a merge does happen under a separate explicit authorization, the re-resolution belongs immediately before that merge, and merges are staggered for the same reason concurrency is bounded, so a re-resolving agent is not racing the next one.

**Bound concurrency.** Agents each running a test suite are not free; a batch dispatched at full width exhausted one machine's memory and killed a quarter of the run. Begin narrow and widen as agents complete. Where CI builds container images, stagger pushes — simultaneous multi-architecture builds exhaust shared infrastructure the run does not own.

## Supervise

Gate "green" on **every** check the repository actually requires having concluded successfully **on the current head** — enumerate what is required rather than gating on whichever check you happened to read. Two false passes share one root here, and closing only the second leaves the first: a rollup that is empty or barely populated means checks have not registered, and where several checks are required, one concluding successfully while another is still pending or failing satisfies any singular reading of this gate. Neither is a pass.

Emit only state **changes**, and only actionable ones. A value that varies for reasons unrelated to state — a count, a timestamp — re-emits every unchanged entry on every tick.

**Separate infrastructure from code.** Builder timeouts, image-build transport errors and browser-harness teardown messages are not the change under test. Confirm by checking whether unrelated branches, and the default branch, fail the same job; where the failure is repository-wide, re-running is futile and escalation is the useful action.

Read a **changed** failure signature carefully. A signature that narrows after a fix indicates one defect with multiple sites, not a failed fix.

## Close out

Per task, a PR following the repository's conventions — one per upgrade or coupled group, plus the one carrying the batched routine bumps (see Dispatch). Across the batch, report what landed, what was declined and why, what remains blocked on a decision only a human can make, and **per open PR, whether its lockfile is still resolved against the current base** — naming that check as the merger's to repeat, since this run merges nothing.

Record declined upgrades where decisions are tracked rather than in a closed PR, since the next attempt begins from the same outdated list.

Report infrastructure findings the batch surfaced. A run of this shape reliably exposes gaps nobody was searching for; passing them on is more valuable than routing around them.
