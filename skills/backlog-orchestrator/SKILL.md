---
name: backlog-orchestrator
description: Autonomously executes a bounded dependency-linked implementation tranche from GitHub Issues, Linear, or another supported tracker. Can fan the implementation phase out onto a Claude Code Dynamic Workflow when the user opts into one, while preserving a validated issue DAG, per-issue model selection, isolated worktrees, durable remote checkpoints, stacked PR topology, centralized PR supervision, bounded repairs, and restart-safe tracker/GitHub state.
---

# Backlog Orchestrator

Execute a prepared implementation tranche autonomously.

This file is the contract; the reasoning and incident history behind its rules live in `NOTES.md` beside it, keyed by section. NOTES explains; it never overrides. The checkpoint-capture sequence lives in `swarm`, as a tested implementation in that skill's `scripts/checkpoint-capture.sh` with its test suite beside it.

This skill is the **policy and backlog layer**. Claude's runtime may provide the worker scheduling/persistence layer for the bounded implementation fan-out.

## Invocation

Dynamic Workflows can only start from the invoking user's own prompt (containing `ultracode`/"use a workflow" wording, or the session already running with `/effort ultracode`) — this skill cannot switch one on by itself mid-run. To get Dynamic Workflow execution for the implementation fan-out, the user must ask for it explicitly, for example:

```text
use a workflow to run backlog-orchestrator on <root/manifest URL>
```

Without that wording (or `ultracode` effort already active), treat Dynamic Workflows as unavailable for this invocation and use the fallback runtime chain below. Do not attempt to "detect" or silently opt into a workflow — there is no such detection; it is invocation-gated by the platform, not by this skill.

Even with that opt-in, the platform still shows its own workflow-launch approval prompt before the run starts (its exact form depends on the session's permission mode). That prompt is a one-time interactive checkpoint at fan-out start, not a break in autonomy — everything from validation through PR creation, supervision, and repair proceeds unattended once it is cleared.

The orchestrator owns:

- bounded scope;
- DAG validation and scheduling policy;
- worker model/concurrency/budgets;
- issue -> repo -> branch/base topology;
- stacked PR relationships;
- long-lived PR/CI/review supervision, through `supervise-prs`;
- recovery and escalation.

It does **not** implement application code itself.

Reusable worker skills:

- `validate-backlog` — shallow/deep DAG validation;
- `implement-issue-core` — one issue -> code -> local checks -> remote checkpoints -> PR;
- `supervise-prs` — supervision of every PR this run tracks, from adoption to individually finished, composing `repair-pr` and `resolve-pr-comment` for its bounded repair passes;
- `create-pr` — issue linkage, stack metadata, PR creation, review trigger;
- `settle-and-merge` — the settle sequence and the merge gate, run over this run's PR set on reaching settled;
- `summarize-tranche` — read-only short summary and action points for a settled tranche;
- `settle-outstanding-decisions` — attended walkthrough of a settled tranche's human-only decisions, requested between summary and ranking when `auto-request-settle` is on;
- `plan-merge-order` — read-only review/merge-order ranking for a settled tranche;
- `merge-stack` — separately authorized stack merge/restack workflow.

`implement-issue` remains the convenient standalone **single-issue orchestrator**. Do not replace it with this skill for normal one-ticket work.

# Core invariants

1. **Tracker + GitHub remote state are durable truth, and truth moves while you read it.** Conversation state, workflow state, and cloud worktrees are caches/conveniences, not the only source of truth. This says where truth lives; it does not say it holds still. Other sessions, other tracks and the owner all write to the same remote, so anything computed from several reads is a composite of moments that never coexisted — see *Every read is a snapshot*.
2. **Canonical issue identity is the full issue URL.** Short keys/numbers are display helpers only.
3. **A run is bounded.** Never turn one build-order ticket into an open-ended project crawl.
4. **One implementation worker = one issue = one isolated checkout/worktree.**
5. **In-flight implementation is remotely checkpointed.** Significant completed work must not exist only in an ephemeral container. **What enforces this differs by runtime, and on one tier the parent cannot:** where it can reach a worker's checkout it verifies and captures (`swarm`, *Checkpoint compliance*; how a recovery ref ends here is Checkpoint compliance, here), and where it cannot — the remote-session tier, normally — the invariant rests on the worker's own pushes, with the dispatch prompt and the observable remote head as the only levers. Say which of those a run is relying on rather than reporting the invariant as satisfied by machinery that was never available.
6. **The model is selected per issue, and Sonnet is the default where the selection does not say otherwise** (see Model and skill policy, which owns the assignment, the capacity check and the escalation ladder). Use the strongest available reasoning model for orchestration when appropriate.
7. **Only validated READY work is dispatched.**
8. **Execution dependency is not automatically Git ancestry.** Stack only where code ancestry requires it.
9. **The parent/orchestration layer owns long-lived PR state.** Implementation and repair workers are bounded and short-lived.
10. **Retries and repairs are bounded.** Persistent failure becomes `NEEDS_USER`.
11. **Recovery is idempotent.** Never duplicate work, branches, PRs, or repairs after restart.
12. **Merges are opt-in per repository, and gated even then.** By default the run performs no merge. It may merge a PR only through the merge gate, and `settle-and-merge`, *The merge gate*, is that gate's only definition — this invariant and every other site defer to it. Everything outside the gate stays where it was: the user's separate `merge-stack` authorization.
13. **A merge is a scheduling event, not an end state.** The run advances its own frontier off merges someone else performed; it does not wait to be re-invoked.

# Autonomy and interactive prompts

Dispatch is the last point at which the user is expected to be present. Once the validation preflight completes, the run proceeds unattended: any decision this skill has a documented default for is resolved by applying that default and reporting it, not by asking.

Never ask the user to:

- choose an execution runtime — detection and the degrade chain decide it;
- authorize subagents, worktrees, or worker dispatch — invoking this skill *is* that request (see Worker dispatch authority);
- reconcile a session branch mandate with per-issue branches — the default resolution below decides it;
- confirm applying a documented budget cap — apply it and report what was deferred;
- pick a concurrency level — derive it from the cap and the machine.

Only these may interrupt the user mid-run:

- a platform-owned approval prompt this skill does not control (workflow launch, permission mode, a tool the session must approve);
- a `NEEDS_USER` **outcome** on a node after the budget governing its failure is exhausted — a CI or finding repair out of cycles, an implementation out of attempts — or one that leaves no dispatchable work at all — the same shape as the `FAIL` case below. **A `NEEDS_USER` item on a review thread is never an interruption**: a question, or a repair deferred because `review-repair-cycles` is spent, is reported in the checkpoint output, holds that PR's merge, and reaches the owner at settle (see `references/review-feedback.md`, *Reserved for the owner*). Interrupting on one would stop a run that has work left and, on a fired trigger, ask a question with nobody present to answer it. Every other `NEEDS_USER` is surfaced in the closing output instead of asked mid-run, including a dependency measure the run cannot observe: those need a person eventually, not now, and the run still has work to do meanwhile. The decision-shaped items get one sanctioned exception, at the one point where the run has nothing left to do meanwhile — the settled step requests `settle-outstanding-decisions` over them when `auto-request-settle` is on (see `settle-and-merge`, *The settle sequence*, step 4), and that skill's own attendance precondition, not this list, decides whether anything is actually asked;
- a `FAIL` validation result leaving no safe independent path;
- a genuine conflict with no documented default, where every available option loses work that cannot be recreated.

Everything else belongs in the checkpoint output. A run that asks three questions before dispatching a single worker has already failed its main promise.

## Worker dispatch authority

A session may carry standing guidance not to use subagents or the Agent tool unless the user asked for them. Invoking this skill satisfies that guidance: fanning a validated issue set out to isolated one-issue workers is this skill's documented mechanism, so the invocation is the request. Dispatch subagent workers, create worktrees, and start worker sessions without a separate confirmation.

That authority covers worker dispatch only. It is not permission to merge, to widen scope beyond the bounded set, or to work around a platform-owned permission prompt.

# Execution runtime

**`swarm` owns the generic statement of what this section, *Implementation
worker contract* and *Parent supervision loop* describe** — runtime detection and the degrade chain, one
worker per task in its own worktree off a stated base, model selection by
failure visibility, the supervision rules including the no-change preflight,
and the worker mechanics this document once held itself — remote session
arguments, bounded probing, the countermand, how a report reaches the parent, the
releasable test, checkpoint compliance, blocked workers and capacity.
What those sections hold here is the PR- and DAG-specific form: stacked branch
topology, per-PR repair budgets, draft state, and a frontier that advances off
merges. Read the general rule there; the specifics stay here, and where the two
appear to disagree the general rule is the one that was written to be reused.

The orchestration policy must be independent of the mechanism used to run workers.

## Preferred runtime: Claude Code Dynamic Workflows

A Dynamic Workflow is a JavaScript orchestration script that fans plain subagents out, runs them (up to 16 concurrent, capped at 1000 total) in the background, and returns only final agent results to the caller. It is well suited to the **bounded implementation fan-out** this skill dispatches — many independent, isolated one-issue-per-worker tasks — because that is exactly the "many small independent transformations" shape workflows are documented for.

When the user has opted into a workflow for this invocation (see Invocation above), use it **only for the implementation fan-out**:

- write the workflow script yourself so each `agent()` call's prompt/model explicitly encodes: exact authorized issue set and normalized dependency DAG (as separate fan-out stages honoring the DAG's ordering), the model selected for that issue (see Model and skill policy — per issue, not one model for the fan-out), one issue per worker, isolated checkout/worktree per worker, exact calculated branch/base, remote checkpoint rules, retry budget; **Size the fan-out to the `concurrent-open-prs` headroom at launch, never to the whole authorized set**: a running workflow cannot be reached or paused once the cap fills, so one staged fan-out over twelve issues against a cap of six opens twelve PRs, and the cap bounds nothing that runs inside it.
- make the checkpoint push a **pipeline stage of its own** rather than only a rule inside the implementation prompt. The parent cannot reach into a running fan-out to enforce it (see Where the parent cannot reach), so the script's control flow is the only thing that can guarantee the push happens;
- do **not** give the workflow permission to redefine the product backlog — it must execute the already validated bounded DAG supplied by this skill;
- treat the workflow purely as an **execution substrate** for that one fan-out run, not as the source of truth for issue/PR state.

A Dynamic Workflow does **not** persist across a Claude Code session exiting — a workflow interrupted by session exit restarts fresh next session, it accepts no external input mid-run, and it cannot be woken later by a CI/webhook event. For those reasons, do not use a Dynamic Workflow for **long-lived PR/CI/review supervision** — that responsibility always stays with this skill's own parent-level supervision loop (see PR promotion and central supervision, below), regardless of whether the implementation fan-out ran inside a workflow.

## Fallback runtimes

When a Dynamic Workflow was not requested for this invocation, or cannot honor the required DAG/worker constraints, degrade through the remaining tiers of Runtime selection below: remote worker sessions, then ordinary isolated subagents with the explicit parent supervision loop defined here, then serialized execution when safe isolation cannot be provided. Agent-team primitives may substitute for tier 2 where that experimental feature is confirmed enabled.

Degrade silently and get on with the run. Not requesting a Dynamic Workflow is neither a reason to abandon the orchestration nor a reason to ask the user which tier to use.

## Runtime selection

Choose the runtime yourself at startup, from what is actually callable in this session. Never present a runtime menu, and never offer a runtime whose tools are absent here.

Determine availability in preference order:

1. **Dynamic Workflow** — only if this invocation opted in (see Invocation). Not autodetectable; without the opt-in wording or `ultracode` effort it is unavailable, and that is not a question for the user.
2. **Remote worker sessions** — available when the session exposes a Claude Code Remote `create_session` tool. A cloud session exposes it whichever surface launched it: `origin` records the launch surface (`desktop_app`, web, mobile), `environment_kind` records where the session actually runs, and neither gates worker creation. Confirm with one cheap read (`list_environments` or `get_session`) rather than a speculative create.
3. **Subagents** — available when the session exposes the Agent tool. The normal runtime for a local session, and the normal fallback everywhere else.
4. **Serialized execution in this session** — always available; correct when safe isolation cannot be provided.

**That order buys something and gives something up, and the something given up is invariant 5's enforcement.** Tier 2 is preferred for reasons that have nothing to do with checkpointing — a container per worker, so four concurrent worktrees do not share one disk (see `swarm`, *Capacity during the run*); a worker that outlives this session's compaction; per-container tool isolation. But the parent cannot reach a tier-2 worker's checkout, so the parent-side verification that `swarm`, *Checkpoint compliance*, calls *the* thing that gets work out of an ephemeral container is unavailable there, while on tier 3 it works. **Preferring tier 2 therefore trades an enforceable durability guarantee for capacity and resilience.** That is a defensible trade and it is not this document's to make silently: report which tier was selected and, on tier 2, that invariant 5 rests on the worker's own pushes. Where an owner would rather have the guarantee than the capacity, tier 3 is the correct selection and nothing here should be read as forbidding it.

**This run's session-name prefix is `bo`** — `bo/<run-id>: <issue>`, for example
`bo/a41f: api#348`. The convention and the reason the name is never what a sweep
matches on are `swarm`, *Runtime: take what is there, and say which*.

`swarm`, *Remote worker session arguments*, owns the rest of what a worker session is created with and checked against — the explicit source, the checkout verification, ending a failed start, and the two capabilities, checkout reachability and the message channel, that the rest of this document divides on. Apply it from there.

### Review and repair sessions

Where a repository's review or repair is performed by dispatched sessions rather than by a trigger comment, those sessions are workers like any other: they carry the countermand (`swarm`, *Countermanding the worker's ambient supervision posture*), they are released by the releasable test (`swarm`, *Releasing a worker*), and step 11 reconciles them, and they carry the report requirement (`swarm`, *How a worker's report actually reaches you*). Two shapes, and the difference between them is what the release test reads:

- **a review session** is dispatched per PR head with `source_revision` set to the PR branch and **no `outcome_branch`**: it reads, and posts inline comments with one summary — or one ranked comment, per the repository's convention — and pushes nothing. **This run dispatches it**: the convention is passed to `supervise-prs` as performed by the `caller`, and each round that skill reports owed, with its head, is a review session this run dispatches;
- **a repair session** is dispatched with `outcome_branch` set to the PR branch, and may only add commits or merge commits, never rewrite history. `supervise-prs` dispatches it, through `swarm`.

**Only the repair session spends `review-repair-cycles`**: a review session pushes nothing, and what a cycle is — and what becomes of findings raised after the budget is spent — is `supervise-prs`'s (*Budgets*). Review rounds draw on the provider's quota instead, which this key does not bound.

### Bounded runtime probing

`swarm`, *Bounded runtime probing*, owns the attempt budget and when a tier is given up; apply it from there.

Also detect:

- native worktree isolation;
- whether Claude Code's own background PR watch/notification behavior is active for this session (`supervise-prs`, *One PR, one supervisor*, acts on it) — and, if so, whether its auto-merge behavior is enabled, since a platform merging on green merges outside invariant 12's gate and should be disabled or reported before autonomous work proceeds;
- local `git`;
- authenticated `gh`;
- GitHub MCP;
- tracker-specific tooling (for example Linear);
- installed required skills.

Prefer native/runtime capabilities when they implement the required behavior safely, but retain tracker + GitHub remote state as recovery truth.

## Transport precedence

The detection above establishes what exists. This establishes which one to use. For every tracker/forge read and write, in order:

1. a first-class MCP tool for that operation, where one exists;
2. an authenticated CLI (`gh`, `linear`, equivalent) when running locally under the user's own credential;
3. raw HTTP against the API, only where neither of the above exposes the operation at all.

Raw HTTP is a last resort, not a default. Reaching for it must be a decision you record — which operation, and why no higher tier exposes it — not an accident of habit because `curl` is familiar and always available.

One further reason counts as "no higher tier exposes it": **a higher tier that cannot ask incrementally where a lower one can** — no `since` bound and no conditional request, where a lower tier offers one (`references/watch-and-read.md`, *Allowances belong to the credential*). Descending for that reason is recorded like any other (NOTES).

One operation is carved out of tier 3 entirely: a GitHub dependency-edge read over raw HTTP returns same-repository edges only, dropping cross-repository ones with no error, so where the scope spans repositories it is not the fallback for a missing higher tier — the honest result is the validator's `dependency transport unavailable` classification, with prose as the only source (see `validate-backlog`, *GitHub dependency reads depend on where you are running*). Falling back anyway trades that named, proceedable warning for an unproven boundary no proof can ever clear.

Precedence lowers the odds of a partial view; it does not remove the need to check for one. A first-class tool or a CLI can run on a directly scoped credential and under-report just as quietly as a relayed one — the hazard is the **scope of the credential**, not the shape of the transport. So treat every relationship read as **provisional until validated below, whichever tier produced it**, and spend the extra scepticism on raw HTTP rather than reserving it for raw HTTP.

## Proving a transport can see the graph

Before a run depends on **relationship data** — dependency edges, hierarchy, cross-repository links, anything a server can legitimately return in part — prove the chosen transport can see it. A relayed, proxied, scoped, or short-lived credential returns a truthful-looking partial result: the server answers correctly for the credential it was actually given, and entries outside its reach are simply absent — 200, no error, fewer rows. This follows from scoping a credential, not from any tracker or forge, so assume any transport can do it. The shared model is stated canonically in `validate-backlog` (*Transport visibility*), and this skill's runs encounter it through that preflight; what follows are the rules the rest of this document depends on:

- **Proof is a known-true case** — an edge this run just wrote, or one the user confirmed: strongest, because its answer does not depend on any transport being trustworthy.
- **A second read corroborates at best, never proves.** Independence is a property of the credential, not the transport — `gh` and raw HTTP both reading `GITHUB_TOKEN` are one observation wearing two coats, and the precedence list above makes that the common case — and even two credentials can share insufficient scopes, a repository boundary, or a relationship transport. Where no known-true case is available, **that is the finding**: report the boundary as unproven rather than promoting agreement into a proof.
- **Enumerating the bounded scope is itself one of these reads.** A scope obtained from a possibly-partial read cannot bound its own validation — a credential that hides children in one repository omits from the boundary list the very repository that was hidden. Draw the boundary list from something independent of the enumeration: the issue set the user supplied, the manifest's own prose listing of its children, or a second enumeration — where **a differing count is the finding, and a matching count proves nothing** unless one of the enumerations had proven visibility.
- **The control must match the shape of what the run consumes.** Cover each scope boundary the graph actually crosses, and where the graph spans repositories, at least one control must itself be a cross-repository edge — one passing control on the easy case is how a scoped credential looks validated.
- **Record validation per credential, transport and boundary**, never per transport alone: "MCP works" is not a finding; "MCP, as this account, resolves edges from A into B" is. Store a non-secret identity of the credential alongside the proof (the authenticated account and its scopes, an expiry, a fingerprint — never the credential itself).
- **Revalidate whenever that identity changes, whenever a transport reauthenticates, and always after a restart. An authorization error invalidates every proof bound to that credential, across every transport that uses it** — grants narrow server-side, so a `gh` 403 says nothing about `gh` and everything about the token, and a narrowing is exactly what a silent partial view looks like from one call away.
- **Absence observed through an unvalidated transport is not evidence of absence** (`references/absence-is-not-a-verdict.md`, of which this is the transport case). Report it as "not visible via `<transport>`", never as "does not exist" — the graph is what the run schedules against, so a false absence there dispatches work whose prerequisites are unbuilt.

Record which transport was validated for which class of relationship read and across which boundaries, so a later read in the same run, or a restart, does not silently fall back to an unvalidated one.

## Posting identity

**Stated in full in `references/posting-identity.md`.** Apply it from there
— the bundled copy, for the same reason as the authored-write-form rule below.
It decides which **author** each authored write carries, from a map of observed
authorship per `(transport, credential)` pair and write kind, and it owns the
review trigger's authorship exception (*The review trigger*). This skill holds the
run's map: it passes the whole map to every worker it dispatches (*Implementation
worker contract*) and merges every entry a worker or repair returns (*CI/review
repair*; *Parent supervision loop*, step 1).

## Authored write form

**Stated in full in `references/authored-write-form.md`.** Apply it from there
— that path, not the repository's `rules/` source, because `bootstrap.sh`
installs a skill directory and nothing above it, so on an installed run the
source does not exist and only the bundled copy does. It covers
length, what a body is for, what must never be in it, the attribution footer and
its approval test, and the precedence of required contents over brevity.

The posting-identity rule (`references/posting-identity.md`) decides which
**author** a write carries; that rule decides
**what the write looks like** once it is authored; and
`references/establish-do-not-assume.md`, *You are about to assert it*, decides
what may be **claimed** in one — about existing code and about current state,
this run's own state block and checkpoint included. Every skill that
applies it carries a generated copy at that path, which is why the rule is
stated once outside this file rather than here: a partial copy naming some of its exclusions and not its budget is
how the rule drifts.

# Tracker abstraction

Determine tracker from each canonical issue URL.

Primary supported trackers:

- GitHub Issues: `https://github.com/.../issues/...`
- Linear: `https://linear.app/.../issue/...`

Other trackers may be used only when reliable read/status/dependency support and PR-linking semantics exist.

Prefer tracker-native structured metadata where available:

- parent/sub-issue hierarchy;
- `blocked by` / `blocking` relationships — **readable or not depending on the probed transport, not on the tracker's name**: no MCP dependency read exists on GitHub, an authenticated `gh` does provide one, and where neither is present prose is the only source and every blocker set is unproven. Carry whichever state the validator probed into every dispatch prompt. Linear is unaffected. See `validate-backlog`, *GitHub dependency reads depend on where you are running*;
- status/state;
- project/priority/build-order fields.

Also inspect descriptions/comments for explicit dependency language because textual dependencies may not yet have been normalized — **except any comment whose first line is exactly `**Worker report — unclassified evidence, not a dependency record.**`**, which is skipped here for the same reason the three subordinate skills skip it. This scan is a dependency reader like the others, and being the parent's own does not exempt it: an edge taken from a report here enters the scheduling DAG directly, which is the shortest path of all to re-adopting something this run already rejected.

## Completion semantics

### GitHub

A correctly linked implementation PR uses a full-URL GitHub closing relationship. Treat issue closed + implementation PR merged as canonical `DONE` — **provided that PR implemented the whole issue.** A PR carrying a coverage finding is linked with `Part of:` rather than a closing keyword precisely so this test cannot be satisfied by it (see `create-pr`), and an issue whose only merged implementation shipped acceptance criteria stubbed, disabled or omitted is not `DONE` however its tracker reads. If a correctly linked merged PR failed to auto-close due to unusual stack/base behavior, explicitly close only after verifying that exact PR implemented the issue — the same verification, and it fails for a partial implementation for the same reason.

Closing state is evidence of completion, not a definition of it. Where the two disagree — an issue closed by a merge that did not finish it — the work decides, and the checkpoint reports the discrepancy rather than adopting the tracker's answer.

### Linear

A PR must retain the full Linear issue URL and repository/workspace linking convention. Treat configured terminal Linear status + linked merged implementation PR as canonical `DONE`, subject to the same completeness proviso as above: a coverage finding means the issue is not done, whatever status the workspace automation moved it to. Do not manually complete Linear issues unless workspace policy explicitly requires that fallback.

# Invocation and bounded scope

Support these entry modes, in preference order.

## 1. Parent / epic / build-order issue — preferred

Treat the supplied root as the execution manifest.

Default authorized implementation set:

- direct sub-issues;
- recursive sub-issues/descendants;
- issues explicitly named by the manifest as implementation items.

External dependencies may be inspected for readiness but are not authorized for implementation unless explicitly included by the root/user.

Do not absorb work merely because it shares a project, repo, label, milestone, or contextual link.

The root itself is coordination metadata unless it contains independent implementation acceptance criteria.

## 2. Explicit issue set

The supplied full issue URLs form the implementation boundary. Read external dependencies for readiness only.

## 3. One or more project boards/projects

Projects are discovery surfaces, not execution graphs. Combine FE/BE/shared projects into one candidate DAG. Prefer an identifiable selected build-order/root issue before dispatching broad project work. **Where the invocation leaves the scope open and the run puts options to the owner, the documented default is what the tracker itself declares the priority** — an epic or build-order issue naming itself the immediate build priority. Offer the options with that one recommended, never an option the run composed, such as an audit of what remains; the run's own reading of the codebase wins only when the owner picks it (NOTES, *Invocation and bounded scope*).

# Mandatory validation preflight

Before dispatching any **new** implementation worker, invoke `validate-backlog` on the entire bounded scope — `shallow` by default, deeper over the nodes the escalation rules below reach.

**The run's first preflight** is also where per-repository policy is read — each in-scope repository's `.claude/agent-policy.json`, per `references/agent-policy.md`, which owns the schema, resolution, and failure rules. **Later preflights do not re-read it, and reuse that snapshot.** This is deliberately asymmetric with the rest of the preflight: a re-run after a frontier advance revalidates the *graph*, which the merge genuinely changed, while policy is owner-authored configuration that can authorize merges. Re-reading it there would make a mid-run merge the route by which a run adopts a config its own workers wrote — which is exactly what `references/agent-policy.md`, *Resolution*, forbids when it fixes the read to the repository state the run started from and bars re-reading for the remainder. A restart is a new run and takes a fresh snapshot.

Use the validator's normalized DAG as the scheduling graph. Do not let the execution runtime independently invent a competing decomposition.

That prohibition is about re-planning, not about evidence. A worker reporting a blocker it verified against its own issue is not inventing a decomposition — it is correcting one, from a position the validator did not have (see Outcomes). Accept an edge a worker verified; reject a runtime's attempt to reorder or re-scope the backlog.

**One validator warning is expected rather than exceptional, and must not be treated as a stop.** `dependency transport unavailable` says the probe found no dependency read on this run's transport — GitHub in a container without an authenticated `gh`, today; the same tracker elsewhere may not be in this class at all. It is not a boundary you can prove later, so holding paths for it would halt every GitHub backlog permanently. Dispatch may proceed, on three conditions: record it on the run's state, carry it into **every** dispatch prompt so no worker reports a false visibility disagreement or waits for a proof that cannot exist, and state it wherever this run reports readiness — a READY computed from prose alone is a narrower claim than a READY computed from a corroborated graph, and only saying so keeps the two distinguishable.

Results:

- `PASS` -> proceed;
- a node carrying `PREMISE_LIKELY_RESOLVED` -> **never dispatch it**, whatever the result value alongside it. Its cited defect is absent on another repository's current default branch with the replacement positively present, so dispatching produces a PR, review rounds and eventually a conflict over work already done. It is **not** `DONE` — that needs completion evidence this pass does not have — so classify it `NEEDS_USER`, which the settled predicate, the stop conditions and the closing report already handle: surfaced to the owner with the evidence and the revision it was read at, and it keeps its edges. `CITATION_UNVERIFIED` is a warning and changes nothing about dispatch;
- `PASS_WITH_WARNINGS` -> proceed only where warnings do not make ordering unsafe;
- `FAIL` -> stop affected paths; continue only validator-confirmed independent safe branches.

One warning is never proceedable at any level: **unproven relationship visibility over dispatchable scope.** A current validator returns that as `FAIL`, but treat it as blocking wherever it arrives, including from an older validator or another tool. Every other warning can be weighed because you can see what it is about; this one asks you to weigh what you cannot see, so "it probably does not affect ordering" is not a judgement available to you.

**The one exception is `dependency transport unavailable`, above** — and it is an exception because it fails the sentence's own test. That rule bites where a transport *might* be short and you cannot tell by how much. Where no transport in this environment exposes a dependency read, you are not being asked to weigh something invisible: you know exactly what you cannot see, uniformly, for every issue, until someone provisions a transport that can. Blocking on it stops every GitHub backlog forever rather than making one safer. Do not let the general rule swallow it — that is precisely how this correction gets undone by a reader applying the stricter-sounding line.

Verify empirically any baseline a ticket tells workers to diff against — "~40 pre-existing type errors", "these tests already fail" — before it goes into a dispatch prompt. Tickets go stale, and a wrong baseline is worse than none: genuinely new failures hide inside an imaginary one.

Measure it at the parent level, but key it by **repository, base revision, and check** rather than broadcasting one number across the run. Workers in a fanout off a single base share a baseline; workers on stacked bases or in different repos do not, and handing them a number measured somewhere else reintroduces the same defect from the other direction — a real regression hidden inside a borrowed baseline, or a pre-existing failure reported as new. Measure once per distinct base, pass each worker only its own, and correct the ticket's claim in the checkpoint output.

Run repo-relative checks from the repo root. Ticket paths are repo-relative, so a `cd` partway through a validation sweep silently invalidates them.

Do not automatically mutate dependency metadata. GitHub normalization is handled separately by `normalize-github-dependencies` when requested.

`validate-backlog deep` is not run by default, because it can consume materially more model/code-reading budget. It remains available on request — and it is entered **automatically**, without asking, under the triggers below.

## Escalating to deep validation

Shallow mode reads declared dependency metadata and issue text. It reads code in exactly one place — an issue's citations into *another* repository, which a merge there can invalidate without anything in this one changing (`validate-backlog` owns that carve-out) — and otherwise never, so it can establish that an edge is *satisfied* and nothing about whether the deliverable behind it covers what the consumer needs. Escalate the preflight from shallow to deep **automatically** — this is a documented default applied and reported, not a question for the user — when the bounded scope shows any of:

- **a cross-repository consumer edge** — an in-scope issue in one repository depends on an issue in another. This is the primary trigger. A frontend consuming a backend built in an earlier tranche is the canonical case, and the earlier tranche having merged is precisely what makes shallow mode confident and wrong;
- **an issue whose text hedges about its inputs** — "may require", "additional providers may be needed", "assuming X exists" — or an acceptance criterion naming a capability no in-scope issue delivers;
- **a dependency satisfied by an issue that closed in an earlier tranche**, where nothing in this run verified what that issue actually exposes.

Scope the escalation to the affected subgraph rather than the whole DAG. The cost objection to deep mode is about breadth, and this does not have to be all-or-nothing: escalate the triggering node and the dependencies it consumes, and leave unrelated branches shallow.

Escalation changes the **mode** of the preflight, never whether one runs, and it reads more deeply *within* the bounded manifest — it never widens scope. `PASS` / `PASS_WITH_WARNINGS` / `FAIL` are handled exactly as above at either mode, unproven relationship visibility stays unproceedable at either mode — with the same `dependency transport unavailable` exception, since a deeper read cannot conjure a capability the tracker does not expose — and the deeper read consumes model budget, not `new-issue-budget`.

### Coverage is not visibility

This is not the unproven-visibility case, and the doctrine that handles that one cannot catch this. There, an edge may exist and your read cannot show it: absence proves nothing, and the repair is a proof re-established against a case whose answer is known. Here nothing failed. The read was complete, the edge is real, the dependency is genuinely satisfied, and every transport proof over that boundary is valid and stays valid.

What is missing is **coverage**: the closed issue's deliverable does not include the part the consumer needs. `CLOSED` and `MERGED` mean the work someone scoped got done — not that it exposes what something downstream was written against. A backend tranche scoped to a service layer can satisfy every declared edge into it and still ship no route for a frontend to call. Only reading the code behind the edge reveals that, which is why the answer is a mode change rather than a proof. Do not invalidate a visibility proof over a coverage finding; there is nothing to invalidate, and doing so halts dispatch across a boundary that is working correctly.

### Reporting

- **Escalation that finds nothing is still reported** — name the trigger, the nodes escalated, and the clean result in the checkpoint output, so the extra cost is visible and attributable rather than invisible overhead.
- **A single-repository tranche with no hedged inputs does not escalate.** The default stays shallow; escalation answers a trigger and does not become the new baseline.
- **Escalation on one node does not force deep validation of unrelated branches.** Nodes that no trigger reaches are validated shallow in the same preflight, and the checkpoint says which nodes got which mode.
- **If deep mode is unavailable** — not installed, failing, or out of model budget — the escalated nodes are **not dispatchable**. A trigger fired precisely because shallow evidence cannot answer the question for those nodes, so a shallow `PASS` over them is not a weaker answer, it is no answer: take the escalation's `FAIL` path — stop those paths, raise `NEEDS_USER`, and continue only the branches no trigger reached, which shallow validated on its own terms. Report the condition, the nodes owed the deeper read, and what blocked it. Falling back to shallow and dispatching on its `PASS` recreates exactly the case the escalation exists to catch, with the cost hidden behind a green result.

# Default usage safeguards

Unless overridden (below):

- maximum concurrent implementation workers (`concurrent-workers`): **4** — this skill's override of `swarm`'s default cap (*Concurrency: a ceiling, and the caller sets it*), which also says how many of them actually run;
- maximum of this run's PRs open at once (`concurrent-open-prs`): **12**;
- maximum newly started issues per invocation (`new-issue-budget`): **12**;
- maximum implementation attempts per issue (`implementation-attempts`): **2 total**;
- maximum strongest-model *implementation* escalations per issue (`model-escalations`): **1**;
- maximum CI repair cycles per PR (`ci-repair-cycles`): **2**;
- maximum review-fix cycles per PR (`review-repair-cycles`): **2** — **counted in pushed repair passes, not in review rounds**; see below;
- maximum settle-finding repair cycles per PR (`finding-repair-cycles`): **2**;
- maximum strongest-model repair rounds per PR (`repair-model-escalations`): **1**;
- maximum lost-worker redispatches per issue (`lost-worker-redispatches`): **1**;
- automatic merges (`auto-merge`): **disabled** — the opt-in invariant 12's gate requires;
- requesting the `settle-outstanding-decisions` walkthrough at settle (`auto-request-settle`): **enabled**. The option gates only whether this run makes the request; whether the walkthrough may actually ask stays with that skill's attendance precondition (see `settle-and-merge`, *The settle sequence*, step 4).

These are the built-in defaults. An invocation argument and the repository's policy file override them by the precedence `references/agent-policy.md`, *Precedence*, states — which exempts the two merge permissions, so an invocation can switch `auto-merge` off for a run but never on.

Dynamic Workflows do not override these limits.

**The two budgets bound different things and both apply.** `concurrent-open-prs` is **flow control**: how many of this run's PRs are open at one time. That is the constraint that actually bites — reviewer load, merge-order complexity, conflict surface — and thirteen open across two repositories was the number that hurt. `new-issue-budget` is the **spend ceiling**: how much work one invocation is authorized to pay for, at roughly one worker's cost per issue. A single number cannot be both, and using cumulative starts as a proxy for how many PRs are open is what made invariant 13 inert — a run that started twelve and merged all twelve had its frontier advance onto work it was no longer permitted to begin.

**`concurrent-open-prs` is a count of what is open, not a ledger of what was spent.** **This run's PRs are every PR this run tracks, created or adopted** — a restart that adopts twelve open PRs holds twelve slots, or the reviewer load the budget exists to bound is doubled by the restart path. **An implementation worker in flight holds a slot too, from dispatch until its PR exists, it returns without one, or lost-worker recovery declares it lost.** Counting open PRs alone lets a dispatch target a slot another dispatch is already about to fill: with four concurrent workers that is three PRs over the cap, against a budget whose whole justification is that thirteen open was the number that hurt. Both halves are re-derived from durable truth at restart — adopted PRs at step 6, and in flight only what this parent dispatches, since an adopted branch holds no slot until a worker resumes it — so the count stays recomputable. **What that cannot see is a worker a previous parent left running**: recovery reads no runtime state, and that worker is another parent's by provenance (the supervision loop's step 11), so a restart can open up to `concurrent-workers` over the cap until those workers' PRs appear — and a restart that adopts a pushed branch with no PR may resume it beside a worker still on it. That is the price of recovery never trusting a cache; report the restart as possibly over the cap by that bound, **and resuming an adopted branch is a dispatch like any other** (Restart / resume, step 9, where it is decided): an adopted branch holds a slot only once a worker resumes it. Repair workers are excluded; they open nothing. A slot is held while a PR of this run's is open and released the moment it is not — **merged, or closed unmerged; the reason is irrelevant to flow control**, which bounds outstanding load rather than outcomes. That makes it observable rather than derived: any pass, including a restarted one, recomputes it by counting this run's open PRs, so nothing about it can be lost to a checkpoint or laundered by a restart. Nothing is deferred to settle. **What stops a run dispatching forever is `new-issue-budget`**, which no merge and no close ever restores — so the invocation is bounded whatever the open-PR count does, and flow control does not need a second mechanism to make it terminate.

When the bounded scope exceeds `new-issue-budget`, do not ask which issues to drop. Start the first `new-issue-budget` issues in scheduling order — DAG readiness first, then how much downstream work each unblocks — and defer the rest, naming the deferred issues in the checkpoint output so the next invocation adopts them. A user who wants a different cap says so in the invocation; a `0` there is treated as the config rule treats one (`references/agent-policy.md`, *Fail-closed handling*).

**When `new-issue-budget` is reached**, stop starting new issues and keep supervising through to settle — the PRs already open still need their reviews, ranking and gated merges — and return a checkpoint only where *Stop conditions* says the runtime cannot stay active. **When `concurrent-open-prs` is reached, do not return** unless *Stop conditions* says the runtime cannot stay active: pause dispatch, keep supervising, and resume on the next release (see *Frontier advance on merge*, step 5) — it clears within the invocation as PRs close or merge, and handing off there turns flow control into a stop. Say which of the two is holding in the checkpoint. Restarting does not count already-adopted work as newly started.

**`review-repair-cycles` counts pushed repair passes, not review rounds** — `supervise-prs`, *Budgets*, states it, and how both numbers are reported in every status line that mentions a repair round. Carry both into the checkpoint, and do not raise the default from a round count.

Budget exhaustion on a node -> `NEEDS_USER`, not another speculative attempt — as an **outcome** where an implementation budget is spent, and for a PR's repair budgets as `supervise-prs`, *Budgets*, states it: an outcome for CI and finding, items for review (see `references/review-feedback.md`, *Reserved for the owner*). Continue unrelated DAG branches safely.

## Policy keys and defaults

The policy file — `.claude/agent-policy.json`, its schema, precedence, resolution, fail-closed handling and the merge permissions — is stated in `references/agent-policy.md`. Apply it from there; this section holds only what is this skill's own. The keys this skill reads, with their defaults:

```json
{
  "concurrent-workers": 4,
  "concurrent-open-prs": 12,
  "new-issue-budget": 12,
  "implementation-attempts": 2,
  "model-escalations": 1,
  "ci-repair-cycles": 2,
  "review-repair-cycles": 2,
  "finding-repair-cycles": 2,
  "repair-model-escalations": 1,
  "lost-worker-redispatches": 1,
  "auto-request-settle": true,
  "auto-merge": false
}
```

The values shown are the built-in defaults. If an option of this skill's is configurable at all, it is configurable in that file.

Keys scope to different objects, and each resolves from the repository that owns its object (`references/agent-policy.md`, *Resolution*). This skill's keys:

| keys | scope | resolved from |
| --- | --- | --- |
| `ci-repair-cycles`, `review-repair-cycles`, `finding-repair-cycles`, `repair-model-escalations`, `auto-merge` | per PR | the PR's repository |
| `implementation-attempts`, `model-escalations`, `lost-worker-redispatches` | per issue | the issue's repository |
| `concurrent-workers`, `concurrent-open-prs`, `new-issue-budget`, `auto-request-settle` | per run | the manifest's repository; an explicit issue set contained in one repository uses that repository; a multi-repo set with no manifest uses the built-ins |

### Review feedback

**Stated in full in `references/review-feedback.md`.** What the run may auto-fix (the kind test), the thread-root test, the rule that the run never roots a review thread, the reservation of a `NEEDS_USER` thread for the owner, and which threads are unhandled all live there; `supervise-prs` applies them to this run's PRs, and this skill reports and gates on the reserved threads it returns.

# Model and skill policy

The orchestration/lead context may use the strongest available reasoning model.

**Select a model per issue, and select it before dispatch.** `swarm`, *Model: the caller chooses, by how failure shows*, owns both gates — the tier, chosen on failure visibility rather than task size, and the context-capacity veto over it. Apply them from there; do not restate them here. Never accidentally inherit the lead's model, and where a runtime has no per-worker model selection, every worker runs whatever it gives.

**Sonnet is this skill's default**, and it is where that skill's mid tier lands for implementation and repair work.

**Deciding in advance is what this section adds**, because the ladder below catches thrashing and cannot catch **confidently wrong** — the more expensive shape here. A worker that patches the single site the ticket named, where the defect was restated at three, returns a green PR fixing a third of the bug; a worker that does exactly what a ticket got wrong looks successful. Neither trips a repeated-failure trigger, because neither fails, and no escalation rule that keys on failure ever will.

At most one strongest-model implementation escalation is allowed per issue for a reasoning-heavy repeated failure (`model-escalations`). **The ladder is a floor under the selection above, not the primary mechanism** — it recovers a worker that is visibly failing, and an assignment made up front is what covers the worker that is not.

**A repair round's model is `supervise-prs`'s to choose** (*Repair dispatch*): it escalates on evidence, not on exhaustion, and an escalated round still consumes its cycle.

Implementation workers require `implement-issue-core` and `create-pr` — and `review-docs` wherever a target repository documents the documentation-review routing, since `create-pr` invokes it there and a worker without it would silently fall back to the ordinary trigger. `supervise-prs` invokes it on a re-trigger or an adoption trigger under that routing, so the requirement holds for the run as well as the worker.
PR supervision requires `supervise-prs`, and the `repair-pr` and `resolve-pr-comment` it composes.
The parent layer requires `validate-backlog` at preflight, and `settle-and-merge` when the run settles, with the skills it composes — `summarize-tranche`, `settle-outstanding-decisions` and `plan-merge-order`, in that order, the middle one only while `auto-request-settle` is on (`settle-and-merge`, *Composed skills*). It also requires `merge-stack` wherever any repository's resolved `auto-merge` leaves invariant 12's gate reachable — checked at the run's first preflight, where policy is read, rather than discovered at the gate, exactly as `implement-issue` checks it for its one PR: the stack rules require that skill for any merge or restack, so a run that could merge without it holding would have no compliant mechanism for the very merge the repository authorized.

Where `merge-stack` is unavailable with the gate reachable, the parent does not stop the tranche the way a one-issue run returns `BLOCKED` — that asymmetry is deliberate, not drift: `implement-issue` blocks one issue's worth of nothing at an invocation its user is typically attending, while blocking here trades twelve issues of authorized implementation for the tool their optional final step needs. It does not improvise a raw merge either. Apply the documented default: the gate is unreachable for this run — the narrowing direction an invocation is always permitted — reported at the preflight and again wherever the gate would have been evaluated, with a closing `NEEDS_USER` naming the missing skill so the owner can install it or keep merging themselves. A parent-required settle skill that is unavailable degrades the same way, never by improvisation: that step's outputs are absent and reported, and a gate whose summary inputs never existed stays shut (see `settle-and-merge`, *Merge behavior*).

Workers must inherit/preload the active installed skills. A **worker** whose required skill is unavailable returns `BLOCKED` rather than improvising a replacement workflow. That rule is the worker's alone, and the parent's required skills are the explicit exception to it: they degrade as the paragraph above has it — the step's outputs absent and reported, the gate unreachable where `merge-stack` is the one missing — never by stopping the tranche and never by improvisation. Without the exception stated, "required" plus "unavailable means `BLOCKED`" reads as a preflight stop, which is exactly the outcome the fallback above was written to avoid.

# Durable remote state and restart

Classify in-scope issues from tracker + GitHub remote evidence:

- `DONE`
- `PR_OPEN`
- `CI_RUNNING`
- `CI_FAILED`
- `IN_REVIEW`
- `IMPLEMENTING_REMOTE`
- `READY`
- `BLOCKED`
- `BLOCKED_EXTERNAL`
- `NEEDS_USER` — including a node `validate-backlog` returned `PREMISE_LIKELY_RESOLVED`, which a restart re-derives from a fresh validation rather than from run state
- `NOT_READY`

Prefer durable evidence in this order:

1. merged linked implementation PR + tracker terminal state;
2. open linked implementation PR;
3. remote issue branch with pushed checkpoints;
4. runtime/workflow-local state;
5. local worktree only.

A cloud worktree is ephemeral. Never claim restart safety for unpushed local changes.

**An outstanding recovery ref overrides all of it, completion evidence included.** Enumerate the recovery refs matching an issue's branch (named under `swarm`, *Checkpoint compliance*; ended under Checkpoint compliance, here) **before** classifying it, not after: a merged PR with terminal tracker state is the strongest evidence in the list and is exactly what an issue carrying rescued, unlanded work looks like from the outside. So an issue with a ref outstanding against it is never `DONE`, whatever items 1–5 say. This is the durable half of that rule — the `NEEDS_USER` a run raises for it lives in run state, which invariant 1 classifies as a cache, so without the check here a restart re-derives `DONE` from the merge and drops the only copy of that work while reporting the issue complete.

## Restart / resume

A Dynamic Workflow interrupted by session exit restarts fresh next session rather than resuming — it has no cross-session persistence of its own. Restart recovery therefore always comes from tracker + GitHub remote state, never from workflow-runtime state:

1. re-expand the exact same bounded manifest/scope;
2. rerun `validate-backlog` at the mode the escalation rules select (see Escalating to deep validation) — a restart re-derives readiness from scratch, so those triggers apply here exactly as at the first preflight, and a resumed run is if anything the likelier place to meet one, since its dependencies closed in an earlier tranche by construction — then reconcile its DAG against blockers a previous run recorded on the issues themselves. What an edge's **absence** from that DAG means is not one thing — it depends on the boundary's proof state and on the edge's provenance, and this step is the main caller of the retirement rule under Outcomes. The validator run you just made supplies that proof state, so read it from there rather than carrying one over: a passing result means every boundary over dispatchable scope was proven, since an unproven dispatchable boundary is a `FAIL` by its contract and never arrives quietly, and the boundaries left unproven are named. **The exception is a `PASS_WITH_WARNINGS` carrying `dependency transport unavailable`, which passes with those boundaries deliberately unproven** — read that as unproven, never as proof. Collapsing it into "proven" here is worse than at the preflight: it would let an absent prior edge count as evidence for retirement, and send later workers a READY context marked proven when nothing proved it. Then:

   - **visibility unproven for that boundary** — the validator reads through a transport that may truncate identically to last time, so re-adopt the edge rather than rediscovering it by dispatching into it again;
   - a worker's report is not a blocker record and must not be adopted as one, wherever it is found — on its PR, where it belongs, or in an issue comment left by older tooling. Read it for what the worker observed, then classify it here as though the worker had just returned it. An unclassified edge does not become established by having survived a session boundary;
   - **proven, and the edge is native by now** — a later run may have made it native via `normalize-github-dependencies`. A proven read that no longer returns it is the retirement case: retire it, dated, rather than re-adopting a dependency someone deliberately removed;
   - **proven, and the edge lives only in the persisted comment record** — absence still proves nothing, because native metadata was never supposed to show it. Re-adopt, then classify it here: **this step is the run adoption** the retirement rule anchors to, and skipping it is precisely how a retired dependency becomes permanent;
3. order by normalized DAG + explicit build order;
4. fetch current tracker statuses, PRs, and remote branches;
5. skip every proven `DONE` issue — after the recovery-ref enumeration above, which is what makes `DONE` provable here: this step precedes both PR and checkpoint adoption, so an issue skipped on merge evidence is never reached by anything that would have found its ref;
6. adopt existing open PRs through `supervise-prs`, *Adopt* — which rebuilds each one's record from the PR's durable evidence, an unrecoverable counter counting as spent — **recovering each one's `Chartered scope:` line from its body into the per-PR block, or recording the charter as unavailable where the body carries none** (see PR promotion and central supervision — the chartered-scope head check is what this feeds);
7. adopt matching remote issue branches/checkpoints even when no PR exists yet;
8. identify the earliest still-unfinished executable frontier;
9. resume there, dispatching fresh workers (in a new Dynamic Workflow fan-out if the user re-opts in, sized to the headroom as above, or via the fallback runtime chain) for whatever is not yet durable — **up to the `concurrent-open-prs` headroom**. Resuming an adopted branch is a dispatch like any other, and an adopted branch holds a slot only once a worker resumes it, so a restart adopting twelve open PRs and two branches holds twelve and resumes the branches only as slots free.

A fresh orchestration session must be able to recover from tracker + GitHub remote state alone.

"Latest unclosed ticket" means the earliest remaining unfinished point in established build order, not the numerically newest issue. Parallel groups may have multiple resume-frontier nodes.

## Branch discoverability

Follow repository branch conventions. Where permitted, include the issue key/number (`123-...`, `FEP-195-...`) to improve recovery. Never violate documented naming rules solely for this.

If an orphan remote branch cannot be safely mapped to an issue, inspect commit/diff/tracker development metadata. If still ambiguous -> `NEEDS_USER`.

## Session branch mandates

A cloud/remote session is usually created with one mandated outcome branch (`claude/<slug>-<suffix>`), injected as session-level instructions to land all work there and push nowhere else. It is chosen by the surface that created the session, applies per session rather than per repo, and cannot be removed from inside the session. Read its current value from the session context (`outcomes[].git_repository.git_info.branches`) rather than inferring it.

It is incompatible with the per-issue stacked topology below. Resolve that by default, without asking:

- **single-issue scope** — use the mandated branch as that issue's branch;
- **remote worker sessions** — give each worker session its own `outcome_branch`, set to that issue's calculated branch. Then no mandate is overridden anywhere: each worker's own session authorizes exactly the branch it needs, and the parent, which dispatches rather than pushing implementation code, keeps its own. Prefer this whenever the runtime supports it — it dissolves the conflict instead of resolving it;
- **shared-session workers (subagents, serialized)** — per-issue branches. One branch cannot carry an n-way fanout or a stack, so the mandate is unsatisfiable as written rather than merely inconvenient.

That last case is an override, and this document cannot authorize one: a session-level mandate outranks skill content, so the permission has to come from the user. It does come from the invocation — asking a fanout orchestrator to execute an n-issue tranche is a request for n branches, and there is no reading of it that lands on one. Act on that without a prompt, name every branch used in the checkpoint output so the override is visible, and stop if the user says the mandate is externally imposed rather than theirs to waive.

Ask only where the default would lose work: the mandated branch already carries unmerged commits, or an open PR overlapping this scope. A mandated branch holding no commits of its own is not a conflict.

A user who wants the mandate honored strictly says so in the invocation, which reduces the run to a single-branch serialized tranche.

# DAG and PR topology

Classify validated dependencies by implementation reality:

- hard same-repo code dependency;
- execution dependency only;
- shared-parent fanout;
- cross-repo scheduler dependency;
- external prerequisite.

Ordinary PR base/head relationships are the durable stack representation.

Same-repo chain:

```text
main -> A -> B -> C
```

B targets A's branch; C targets B's.

Fanout:

```text
main -> A
        |-> B
        `-> C
```

B and C both target A and never each other merely because of timing.

Multiple unmerged sibling dependencies with no valid common base -> block rather than invent an integration merge.

Cross-repo dependencies are scheduler edges only and never Git stack ancestry.

# Implementation worker contract

Each implementation worker owns one isolated checkout for one issue.

For local repos, create a dedicated worktree from the exact calculated base. Use runtime-native worktree isolation where available. An exclusive runtime clone also qualifies.

Concurrent workers must never share one mutable checkout/index. If isolation cannot be provided, serialize that repository.

Before dispatch:

1. calculate/fetch exact required base;
2. create/identify issue branch;
3. allocate isolated worktree/check-out;
4. resolve shared-resource access details (see Shared environment, below);
5. record canonical issue URL -> tracker -> repo -> worktree -> branch -> base -> worker;
6. compose the dispatch prompt so it carries every default the worker skills already own. **A design ruling this run writes into it states the ruling and links the record of it, never claims it was authorised** (NOTES, *Implementation worker contract*, on why the claimed form is refused), **and names the chosen shape's failure paths** — what persists if a later step fails, what a retry does — because the worker implements a ruling without re-deriving it, so nobody else is positioned to check them; the worker records it on the PR with the rest of its choices (step 8; NOTES, *Implementation worker contract*);
7. state branch protection explicitly: the worker pushes **only** to its assigned branch, never to the repository's default branch or to any branch it was not assigned — including to fix or revert something it just broke. A worker convinced a change must land on the default branch directly stops and reports instead of pushing it. The branch assignment does not imply any of this (NOTES: the observed default-branch push);
8. countermand interactive questions explicitly, and state the substitute: the worker never calls `AskUserQuestion` or otherwise stops to put a question to a human, and never waits for a reply or a confirmation either — both stalls observed were a worker waiting for a "go" nobody would send. Nobody is there to answer an unattended worker's prompts — the parent can surface one (`swarm`, *Blocked workers*) but never answer it — so the call does not pause the worker; it stops it until a human happens to look (NOTES: the observed twenty-minute deadlock). The prohibition alone is half the instruction, because a worker holding a genuine open question still has to put it somewhere — but where it puts it depends on whether its own skill already owns that stop. `implement-issue-core` returns `BLOCKED`/`BLOCKED_EXTERNAL`/`NEEDS_USER` rather than guessing when scope is materially underspecified, a supplied base is invalid, a prerequisite cannot be observed, or a product decision needs approval; there the worker returns and documents that outcome. **The substitute never licenses implementing past a stop a worker skill prescribes**, because a guess at one of those produces a PR built against a missing dependency or invented product intent — worse than the deadlock it was meant to avoid, and harder to see. For every other open question — the ordinary judgement calls a task leaves open — tell it to pick the most defensible option, implement that, and record the question, the choice, and the reasoning on the PR, where a human can overturn the call in review. **Where the choice is of a multi-step shape, record its failure paths with it**: what persists if a later step fails, what a retry does, and whether the property that won the choice survives both. The prohibition on asking is absolute in both cases; what differs is whether the worker proceeds or returns. Where this countermand goes is decided with the others (see `swarm`, *Countermanding the worker's ambient supervision posture*);
9. include **the dependency context used to judge this issue READY** — the blockers considered, how each was resolved, which transport and credential produced that view, and **the provenance of each edge**: your own native read, or a blocker you established from a previous worker's evidence and recorded outside native metadata. The worker compares its native read against yours, and an edge you deliberately kept out of native metadata is one its native read is supposed to lack; unmarked, that comes back as a visibility disagreement against the very corrections you recorded. **Mark the context as your complete READY dependency set**, because it is: unmarked context is treated as a targeted answer whose omissions mean nothing, so an edge you never saw would come back unreported and your frontier would stay wrong. State too whether the read behind it had **proven visibility** for the boundaries this issue's blockers could cross. Marked complete, that is what makes the worker's own silent read meaningful — otherwise its three sources collapse to one unproven native read, agree because two are empty, and readiness rests on an absence nobody established. You will normally have the proof, since an unproven dispatchable boundary is a preflight `FAIL`; where you are dispatching without it, saying so is what lets the worker stop instead of building against it;
10. include **authorization membership**: the bounded authorized set, or a per-blocker flag for whether each is inside it. Only you know this, and the worker's block outcome turns on it — without it, an external-looking prerequisite you did authorize comes back as an out-of-scope wait and you skip the frontier re-derivation it needed. A worker given nothing defaults to the stronger outcome, which is safe but costs you the distinction. And where a sibling branch may claim the same migration number, that its number is provisional (Cross-branch artifact collisions);
11. include, on any runtime where a worker's return value does not reach this run, the requirement that it **record the judgment part of its result on its PR before returning** — not on the issue, and not the run state, which the session record and the branch already carry; see `swarm`, *How a worker's report actually reaches you*. **Do not enumerate what the report contains. State it as a subtraction, because enumerating it fails in one direction.** The report is `implement-issue-core`'s entire Output contract *minus* what this run can already read for itself — the branch, the PR, and the session record's `status_bucket`, `pending_action`, `task_summary` and `post_turn_summary`. Everything else in that contract is judgment, and judgment is exactly what has no other carrier. **The one fact it adds back is the head commit the worker pushed** — or that it pushed nothing, and the head it found (`swarm`, *How a worker's report actually reaches you*, says why).

The reason for the subtraction is empirical: four review rounds against an enumerated list each found a different item missing from it, and every one of them was something a **clean** run still has to say (NOTES: the four omissions, kept there as the shape to watch for).

Any terminal outcome reached before a PR exists writes nothing and simply returns — investigating it, and recording anything that comes of it, is this run's job, not the worker's;
12. dispatch the worker with `implement-issue-core`, on the model selected for this issue (see Model and skill policy).

A dispatch prompt that enumerates a required process is followed literally: a default left out of that enumeration is a default skipped, and the worker will accurately report that the task never asked for it. The same literalism decides what the worker does with instructions this run did not write (see `swarm`, *Countermanding the worker's ambient supervision posture*). Every dispatched prompt must therefore carry the automated review trigger instruction — the worker's `create-pr` issues it under `references/review-trigger.md`, so do not restate the rule here — unless this run explicitly defers review. Deferral is a conscious choice recorded in run state, naming what review is owed and on which PRs; it is never an omission. **Record it as the per-PR `review trigger` value `deferred`** — that field is what `supervise-prs`, *Adopt*, reads, and a deferral left at `pending` is issued there as an unfinished trigger.

**A returned PR whose body's gate table is missing a derived check is rejected, not accepted and watched.** The table is the worker's report that it ran what it was given, and an incomplete one is the cheapest moment to catch a skipped step — cheaper than CI, and much cheaper than a review round spent on a failure the gate would have caught. A worker's claim that the gates passed is separate and is not evidence: the table says which ran, CI on the pushed head says whether they passed.

**Every dispatched prompt carries the pre-PR gate, derived once per repository and written out in full.** The parent derives it at preflight as `implement-issue-core`, *Final local verification* defines — the base branch's required status checks, mapped to the commands that produce them, with its fallback and its `not locally runnable` outcome; that skill owns the derivation and this one does not restate it — and puts the resulting set in the prompt, with each entry's outcome vocabulary and where the set came from. Not a path to it, and not a pointer to `AGENTS.md`, which describes the gate and drifts from it (`swarm`, *Isolation*, on why a path is worse than useless here). Deriving it once is also what stops two workers disagreeing about what the gate is.

**Every dispatched prompt states how a worker settles a checkout against an API response.** Both are observations with an age — `origin/main` is as old as its last fetch, which on a container tier can be the moment the container was built, and a held response is as old as when it was issued. Left unsaid, a worker believes whichever it looked at last, which is how a redundant PR gets opened against a base that had already moved (see *Every read is a snapshot*). Where the two disagree about something the worker is about to act on, it re-reads the forge at that moment and refreshes the checkout to match.

**And every dispatched prompt carries the outbound claim check alongside the write-form rule** (`references/establish-do-not-assume.md`, *You are about to assert it*). A worker authors the writes this run is most likely to be judged by — its PR body, its report comment, its commit messages — and this section's own literalism decides the outcome: a requirement left out of the prompt is a requirement skipped, and the worker will accurately report that the task never asked for it. Constraining only the writes this orchestrator makes itself leaves every remembered claim a worker states about the codebase — or about the state of what it touched, *pushed* and *resolved* above all — unchecked, which is most of them.

**By the same literalism, every dispatched prompt carries the run's whole posting-identity map** — every (transport, credential) entry, not one selected pair, plus the instruction to read the worker's own first authored write back and report what it observed (see `references/posting-identity.md`). Passing one entry is not a smaller version of this: the worker's `create-pr` may need an agent-authored entry to create the PR and an invoking-user entry for the author-sensitive review trigger, so selecting here either gives the PR the wrong author or leaves a valid trigger path unavailable, and the worker cannot recover what it was not sent. The worker's report is itself an authored write, normally a PR comment, and it is the most common one this run causes: enumerate the requirement to report while omitting the identity to report under, and the worker posts it as the invoking user, correctly, because the prompt never asked otherwise. A distinct identity observed at `create-pr` does not reach that write on its own.

**And every dispatched prompt carries the authored-write-form rule** (see Authored write form), for the same literalism and with the same failure at the same write: the worker's report is a PR comment this run caused, and a prompt that enumerates the requirement to report while omitting the form to report in gets a report of whatever length the worker felt like, unsigned — correctly, because the prompt never asked otherwise. Carry the rule, not a paraphrase of it: brevity, the no-wrap constraint on forge fields, the footer **with its approval test**, the required-contents precedence, and the trigger comment's exemption. A worker carrying "sign every write" instead of the test will footer a body a person edited; a worker carrying only "sign unattended writes" without the test will decide for itself what counts as attended. A dispatched worker's own writes answer No to the test — nobody reads them — so in practice its report and its PR body are footered, and the test is still what it carries, because the worker is what discovers whether anyone approved a given text. **Carry with it that the report's contents are required in full** — the marker first line, and the judgment step 11's subtraction defines — so brevity governs how the worker writes each item and never whether it writes one. A prompt saying *keep forge writes short* beside *only the first line is required* is a licence to drop exactly the judgment step 11 exists to carry, and four review rounds against an enumerated list are the evidence that the missing item is never the one anybody predicted. The footer goes at the end, where it cannot displace the marker line.

Issuing the trigger is not the end of that step: confirming it took effect, at adoption and after every re-trigger, and reading every PR's CI and review verdicts from then on, are `supervise-prs`'s (*Adopt*, *Review trigger*).

This generalizes past review triggers. When the platform offers several ways to perform the same write, prefer its first-class integration tooling over raw transport: attribution, permissions, and downstream automation can all differ between them, and the difference is invisible until a write is made and read back. Where identity matters to a workflow, verify it by inspecting an object the run actually created and reading its author — never by asking the credential who it is, which can answer differently from what its writes carry.

Under Dynamic Workflows, provide these constraints to every workflow worker explicitly. Do not let a worker select another backlog ticket when it finishes.

## Shared environment

Filesystem isolation is necessary but not sufficient. Workers with private checkouts still contend over shared mutable resources — a shared backing service instance, a fixed port, a shared cache or state directory, one set of credentials, a single external sandbox account.

At startup, enumerate the shared mutable resources workers in this run will contend for. That inventory is repository- and environment-specific: take it from repository configuration (`CLAUDE.md`/`AGENTS.md`, the session startup hook, the environment manifest), never from assumption. If a rule cannot be expressed without naming a concrete technology, it belongs in that configuration, not here.

For each enumerated resource, either give every worker its own namespace/instance, or serialize access to it. If neither is possible, serialize the affected workers.

Pass the resolved access details explicitly in each dispatch prompt so no worker has to guess them. A worker that guesses wrong reports failures that are not real.

**Carry the environment-hypothesis rule in every dispatch prompt** — `implement-issue-core`, *Final local verification*, states it and this run does not restate it. A worker inherits none of the repository's own context about a service that dies mid-session, and a prompt that omits the rule gets a worker that thrashes against a healthy codebase or returns a bare `FAILED` on one (NOTES).

Standing rule in every dispatch prompt: never stop, reset, reconfigure, or clean up a concurrently shared resource — a sibling worker may be using it. A worker holding serialized exclusive access may perform the lifecycle operations the repository's own configuration sanctions, since nothing else holds the resource during its turn.

## Remote checkpoint requirement

`implement-issue-core` must:

1. push the issue branch early so it has remote identity;
2. commit/push meaningful coherent checkpoints during substantial implementation;
3. push final implementation state before returning;
4. create/verify the PR;
5. return remote branch/PR/head SHA.

Do not create meaningless checkpoint commits merely as heartbeat activity. Checkpoint after meaningful completed work so container loss discards only the most recent unfinished chunk.

Treat all five as best-effort on the worker's part. They belong in every dispatch prompt, but do not count them as satisfied because they were instructed — `swarm`, *Checkpoint compliance*, is what actually enforces them.

# PR promotion and central supervision

**`supervise-prs` supervises every PR this run tracks, created or adopted, from inside this run's own loop** (Parent supervision loop). Platform surfacing and the check that the platform's own auto-merge is off, adoption, reading, CI attribution, review routing, repair passes and their budgets, review triggers and draft state are that skill's. This section says what this run passes it and what stays here. A Dynamic Workflow run does not itself persist or surface PR/CI/review events once it returns its fan-out results, so supervision is this run's from that moment.

Once an implementation worker reaches `PR_OPEN`, release that implementation worker — on a remote-session runtime that is an archive call, not merely ceasing to message it (see `swarm`, *Releasing a worker*). Long-lived PR supervision belongs to the parent/runtime orchestration layer.

**One PR, one supervisor, and it is this run.** The lifecycle is:

```text
parent  -> dispatch implementation workers (a Dynamic Workflow only for this fan-out, only on the user's opt-in)
worker  -> implement -> open PR -> report it back -> stop reading GitHub -> released
parent  -> adopt the PR, arm its subscription, and own it from there:
           react to delivered events, check in occasionally and consolidated,
           and resume only the specific worker a change actually needs
```


A worker never supervises its own PR, and a Dynamic Workflow never supervises anything: it returns its fan-out results and supervision is the parent's from that moment (see Parent supervision loop).

**What this run passes `supervise-prs`:**

- **PR set**: every PR this run tracks, with its canonical issue URL;
- **budgets**: `ci-repair-cycles`, `review-repair-cycles`, `finding-repair-cycles` and `repair-model-escalations` per PR, as this run's preflight resolved them (*Policy keys and defaults*), with their source;
- **counters**: 0 for a PR this run created; otherwise the counters in `supervise-prs`'s last returned record for that PR, which the state block carries every cycle;
- **posting-identity map**: the run's whole map — and this run takes back the map it returns and merges it, as it does a worker's (`references/posting-identity.md`);
- **review routing and trigger state**: as each worker's `create-pr` left it, and `deferred` where this run deferred review (*Implementation worker contract*); a convention performed by dispatched review sessions is passed as performed by the `caller` (*Review and repair sessions*);
- **repair dispatch**: `swarm`, with whether a worker's return value reaches this run on the selected tier;
- **head checks**: the chartered-scope check below;
- **caller pushes**: every restack (*Stack mutation while PRs are open*) and renumber (*Performing the renumber*) this run pushed since the last pass, and every restack `merge-stack` performed with a gate-authorized merge, tagged by `references/mechanical-pushes.md`, with each branch this run is about to mutate held locked;
- **findings to repair**: settle findings (*A settle finding is the third repair shape*);
- **releases**: each PR held by the chartered-scope check whose `DECISION` has been ruled, with the ruling;
- **wait owner**: `caller`; **return on**: `every-pass`; **state emission**: `every-pass`, because the state block is emitted every cycle;
- **transport record**: this run's.

For every active PR track this run keeps, beside `supervise-prs`'s per-PR record:

```text
canonical issue URL
tracker
chartered scope: one or two sentences, from the issue — written into the PR body at creation, cached here
stack parent/children
worker session: <session id, or none on tiers without one> — archived: yes/no
```

**The chartered scope line is what makes the ratchet visible.** Invariant 3 bounds the run, the frontier rule bounds what gets started, and dispatch authority bounds what may be worked on — **nothing bounds one PR's diff as it passes through six review rounds**, and that is where the growth actually happens. A PR chartered as a one-clause guard came out of its rounds carrying a clock-synchronisation module, a new comparison in the upsert predicate and a new return value gating event publication; another chartered as a bounded drain also shipped a new script, a new package command, a new CI step and eight annotated call sites. **Every round was individually justified** — each finding real, each fix right for that finding — which is exactly the hazard: a ratchet has no step at which it is wrong, because the reviewer's job is to find problems in what it is shown and each fix enlarges what it is shown next. So the charter is written down at creation, from the issue, while it is still uncontested; recorded after the fact it would be written from the diff and could only agree with it.

**And it is written where a restart can find it, which this block is not.** Invariant 1 classifies the per-PR block as a cache, so a run that recorded the charter only here loses it at the session boundary and a resumed run would rebuild one from the issue as it now stands — after the diff expanded, and quite possibly after the issue was edited to match. A charter reconstructed at that point agrees with anything. So `create-pr` writes it into the PR body at creation as a **`Chartered scope:` line** — a required content under the write-form rule, one or two sentences, surviving the budget as the linkage lines do — and adoption recovers it from there.

**Where no charter line is recoverable, say so and do not invent one.** A PR this run did not create, or one whose body was rewritten without it, has no charter, and the ratchet comparison is **unavailable** for that PR rather than performed against a guess. Record it as unavailable in the block and report it that way: an unavailable check is a known blind spot, and a check performed against a reconstructed charter is a clean result that means nothing.

**A worker that sees the seam first reports it rather than crossing the charter** (`implement-issue-core`, *Implement with remote checkpoints*), and it arrives as a **design finding on that worker's return**. Record it as a `DECISION` item — split or absorb — which is the disposition this gate would reach anyway, and hold the path it bears on. The same finding reaching this run before the work rather than after a refused adoption is cheaper for both sides, and the only thing that makes the early route real is that the return carries it.

**The chartered-scope head check, passed to `supervise-prs` stated in full** — `on-repair-head`:

> Compare the repair pass's pushed diff against the PR's `Chartered scope:` line. A fix that introduces a **new module**, a **new build or CI step**, or a **new cross-cutting invariant** is `hold` — a `DECISION`, split or absorb — and not an adoption. Everything else is `adopt`: the test is the kind of thing added, not its size. Where the PR carries no charter line, the check is unavailable for that PR: `adopt`, and report the check as unavailable — never perform it against a reconstructed charter.

A PR `supervise-prs` returns `held: check` by this check is recorded here as a `DECISION` item, and holds the path it bears on. It stays held — no dispatch and no adoption on that branch — until this run passes a release, which it does once the `DECISION` is ruled, with the ruling.

The worker-session line is what makes the loop's release reconciliation a lookup instead of guesswork: without a session id on the record, matching sessions to PRs means fuzzy-matching session titles, which is what an actual recovery had to script its way through (NOTES).

# CI/review repair

`supervise-prs` — *CI failure*, *Review feedback*, *Finding repairs* — owns every repair of this run's PRs, dispatched through `swarm` on the model it chooses. What stays here:

**A producer merge can turn this run's open PRs in another repository red.** `references/ci-attribution.md`, *A producer merge*, classifies that red as expected-red, and `supervise-prs` reports it and counts it as surfaced; an observed run saw it three times, once per producer merge. **The remedy is this run's**, because it needs authority over the PRs' bases. A confirmed check is expected-red pending the refresh PR the repository's tooling opens — watch that PR, which belongs to no tranche and is outside `supervise-prs`'s PR set — this run reads it itself, under `references/watch-and-read.md`; read its removed lines before trusting it, because generated is not additive and an apparent removal may be a reordering or a producer silently dropping what it claimed not to touch, and a real one is `NEEDS_USER` naming the field; and once it merges, restack each consumer PR onto the refreshed default branch as *Stack mutation* does — a stacked PR's base is its parent, not the default branch — passing each push to `supervise-prs` as a caller push, and read CI again; the rule says when the check then belongs to the PR. A confirmed expected-red check **counts as surfaced rather than outstanding** (*Settled tranche* states the set): it holds that PR's merge under invariant 12 and never blocks settlement, because nothing in this run can merge the refresh, and a run unable to settle could never report it as the owner's merge to make. The settled report names the refresh PR as that merge, with any removal item attached.

## A settle finding is the third repair shape

**A thread reserved for the owner is not a source of an `IN_FLIGHT_FIX` where nothing can dispatch it:** a deferred repair is review-shaped work the review budget already refused, so it is reported and holds the gate rather than being re-dispatched under the finding budget (`summarize-tranche`, *Action points*). **A thread carrying a recorded code-changing ruling is the exception and does belong here** — the finding path is its dispatch, and after a restart it is the only one left. `summarize-tranche` can derive an `IN_FLIGHT_FIX` action point solely from durable evidence that is neither CI- nor review-shaped — a worker's documented caveat, the diff itself, a coverage finding — and a walkthrough ruling that requires code to change arrives the same way, routed through the `IN_FLIGHT_FIX` row (see Settled tranche). Both name actionable work on an open PR with no failing check and no reviewer's review thread behind it, so neither dispatch above has a compliant invocation for them — and `repair-pr` is required, so "improvise something else" is not an answer either. `repair-pr`'s `finding` repair type exists for exactly this: it takes the action point or recorded ruling verbatim as its evidence, the way `ci` takes logs and `review` takes threads, under the same bounded one-pass contract.

On an `IN_FLIGHT_FIX` action point, or a code-changing ruling its row routes here, **hand it to `supervise-prs` as a finding to repair**, verbatim, with the run's map; take back its outcome and the map it returns, merged; then re-test the settled conditions before ranking anything (see The summary can un-settle the run). A pushed repair un-settles the run as any change does; `NO_CODE_CHANGE` changes nothing; `needs-user` is surfaced like any other — and **that finding is never handed back again on a later settle**: its `NEEDS_USER` item now carries it, as a `DECISION` for the owner, so a failed repair, which consumes no cycle when it pushed nothing, cannot loop through the summary and back. **An owner's ruling to try again is new evidence, not the same finding**: a ruling to lift the budget or try again on a `needs-user` PR — CI-, review- or finding-shaped — is a code-changing ruling, and takes this path within `finding-repair-cycles`. Where that budget is itself spent, the ruling cannot move the PR on this run's authority: the settled report says so, and names the re-invocation that would — this manifest with `finding-repair-cycles` raised for that PR, the policy being read once at preflight.

## Mechanical pushes do not consume review

This run tags each restack and renumber it pushes by `references/mechanical-pushes.md`'s test, conditions included, and passes it to `supervise-prs` as a caller push; what a mechanical push means for the PR's record is that skill's (*Pushes this skill did not make*).

## Draft state

`supervise-prs`, *Draft state*, applies `references/draft-state.md` to this run's PRs. An **explicitly held draft** is reported in the checkpoint output as held, awaiting the owner.

# Parent supervision loop

Long-lived PR/CI/review supervision always runs in this parent loop, never inside a Dynamic Workflow: a workflow run accepts no external input once started and does not persist past the current Claude Code session, so it cannot sit and wait across hours/days for CI or review to come back. This holds even for a run whose implementation fan-out did execute inside a Dynamic Workflow — once that workflow returns its worker results (PR URLs, branches, heads), supervision reverts to this same parent loop.

The main parent thread must remain active while mutating workers run or active PR events can lead to more in-scope work.

Each cycle performs real work:

1. consume worker completions (including a Dynamic Workflow's returned fan-out results, if one was used), extracting each one's dependency evidence — unmet blockers, source disagreements, **and the resolutions that confirmed your view** — and **merging every posting-identity entry it returned into the run's transport-and-credential-keyed map** (see `references/posting-identity.md`), regardless of its outcome. Do this before releasing the worker: the worker's transports are not this run's, so its observations are the only evidence the run will ever have about them, and a released worker cannot be asked again;
2. **run `supervise-prs`, *Pass*, over this run's PR set** — the delivered PR events, the repair completions step 1 consumed, this cycle's caller pushes and any findings to repair — with the inputs *PR promotion and central supervision* lists. It reads what is due, dispatches repairs through `swarm`, adopts heads after the chartered-scope check, re-triggers and promotes, and returns an outcome per PR with the map it updated. This run makes no supervision read of its own beside it. Its own reads — the tracker reconciliation, the refresh PR, and the reads `validate-backlog` and the settle skills make — follow `references/watch-and-read.md` too: only where this cycle has a reason to, in one consolidated pass, a deliberate descent to a lower transport tier recorded as *Transport precedence* requires. Its dispatch-as-reading carve-out reaches those required skills, which are mandatory where they are mandated, budget or no;
3. fold the outcomes into the per-PR blocks and act on them: `merged` or `closed` is a frontier event (Frontier advance on merge); `finished` feeds the settled predicate; `held: check` by the chartered-scope check is a `DECISION` item; `needs-user` goes to step 15, whose item is what makes it surfaced (*Settled tranche*);
4. merge the map `supervise-prs` returned into the run's map, and update this run's budgets;
5. repair workers are this run's workers under `swarm` like any other — their completions arrive at step 1 and are forwarded to the next *Pass*;
6. recompute READY frontier;
7. fill available worker slots, up to the `concurrent-open-prs` headroom (optionally via a fresh Dynamic Workflow fan-out if the user re-opts in for the next batch);
8. inspect stack ancestry changes;
9. inspect every in-flight worktree for uncommitted work and enforce checkpoints (see `swarm`, *Checkpoint compliance* — this is a mandatory step, and the parent commits on the worker's behalf when a nudge has already failed, by the capture that section defines, its ref then ended under Checkpoint compliance here) — **mandatory wherever worktrees are reachable, and inapplicable where the run established they are not**, in which case this step is the remote-head reading and the report saying so, never a skipped step recorded as a passed one;
10. read every worker's runtime state, not only its work state — release the finished (see `swarm`, *Releasing a worker*) and act on the blocked (see `swarm`, *Blocked workers*);
11. **reconcile released-vs-alive against the runtime, never against the run's memory** (`swarm`, *Runtime: take what is there, and say which*, states the three sources and which is authoritative).** On a runtime with a session list, list the sessions whose provenance marks them as created by this run (`parent_session_id` on Claude Code Remote — never "sessions that look like workers"), and compare against the per-PR records. Three outcomes, and only three: **mine and archived** — done; **mine and still alive** — apply the releasable test and **archive every session that passes**, this cycle. On the remote-session tier the worktree is never inspectable, and the test reads the remote state in its place (`swarm`, *Releasing a worker*, condition 2), so an uninspectable worktree is no longer a reason to keep a finished session. What fails the test takes a `swarm`, *Blocked workers*, branch or `NEEDS_USER`, and a live session this run created stays this run's cost and this run's problem; **not mine** — a session whose provenance proves it belongs to another run or to the user: report it and never reclaim it, whether or not its worktree is inspectable. **For every session this step leaves alive, the report is diagnostic rather than a count.** Name, per session: the issue it was chartered for, **its reachability** — whether its head commit is reachable on the remote (next paragraph), and where it is not, how far the remote head has got — and whether it carries staged or uncommitted files. **Branch existence is not progress** — `swarm`, *Checkpoint compliance*, already names the `clean | local ahead` case, where the worker pushed once, committed more since, and left nothing staged, so a branch-exists field plus a clean worktree reports stranded commits as healthy. Where the worktree is reachable, compare its local head against the remote's. Where it is not, record the remote head and **how long since it last advanced**: a head that has not moved in days, against a session still alive, is the same signal from the outside. "1 alive" cannot distinguish a warm container mid-turn from a month of unpushed work, and that distinction is the whole reason the check exists. **Report every session this step archived** in the state block, by id and charter. **And list this run's triggers**: a trigger bound to one of this run's worker sessions means the countermand did not hold, and the remedy is to archive that session where the releasable test passes — not to delete the trigger, which a live session re-arms (see `swarm`, *Releasing a worker*). A worker that is still working and has armed one is a finding about the dispatch prompt, reported as such.

**The test is whether the work is reachable on the remote, never whether a branch of that name exists.** Reachable is defined once, on the worker's head commit, under `swarm`, *Releasing a worker*. Where the tracked remote branch is absent, check whether its PR merged before reading anything as stranded. A merged PR's branch is routinely deleted by the forge, so a branch-exists test reads merged work as stranded: an observed session sat `IDLE` and unarchived for four weeks reporting `staged_files`, with no branch on the remote, and was first reported as four weeks of unpushed work — its PR had merged the day it was created and the branch had been deleted with it. The staged files were residue in a container nobody needed. What that session *did* show is worse than stranded work and is the reason it is kept here: chartered for one issue, it had grown a twenty-two-issue backlog marked ready for dispatch, its checkout pointed at a repository's pre-migration organisation, and the owner had been talking to it believing it was part of the live run. Where a field cannot be read from here, say which one and that it is unread; an unread field is not a clean one. The remote-branch reading is also what the capture lever under `swarm`, *Releasing a worker*, turns on, so it is needed in this pass regardless.

The comparison must read the runtime because the run's own record of releasing is not evidence: of the two runs that leaked sessions, one never reached step 10, and the other wrote "archived" into its notes and never called the tool. Reporting an action is not performing it (`swarm` NOTES, *Releasing a worker*: the two mechanisms);
12. **emit the state block** (see Progress / checkpoint output) — every cycle, including the long one-PR supervision tail, not only in closing output;
13. re-check disk/slot capacity (`swarm`, *Capacity during the run*);
14. check sibling branches for colliding added or modified claimed artifacts;
15. surface `NEEDS_USER`;
16. wait using native task/event wait, then repeat. **One loop and one wait per session, and both are this run's**: `supervise-prs` runs inside this loop with `wait owner = caller`, arms no check-in of its own, and its PRs' changes are deltas on this run's one wake (Arming the wait when nothing is in flight). **The PR subscriptions `supervise-prs` armed wake this session, and this invocation overrides the platform's PR posture they carry** (`references/platform-pr-posture.md`): every wake — `subscription.created`, a CI failure, a comment, the check-in — is answered by this loop's next cycle, never by the posture's own loop, and a spent budget ends in `supervise-prs`'s outcome for that PR, never in another repair push.

Do not use CPU loops, file-touch loops, detached sleeps, meaningless commits, or other fake activity solely to prevent idling.

Remote Git checkpoints remain mandatory regardless of runtime, because no platform/runtime persistence substitutes for durable source control.

## Every read is a snapshot

`references/establish-do-not-assume.md`, *Every read is a snapshot*, states it: a multi-item read is a composite of instants, so re-read the deciding facts immediately before acting on them, timestamp every state report, and settle a checkout-versus-API disagreement by a third read. Apply it from there. Here it reaches the merge gate's freshness check (`settle-and-merge`, *Merge behavior*, is one instance), the ranking, every checkpoint and handover, and every dispatch prompt, which carries the checkout-versus-API half because a worker inherits the same habit and has less to check it against (*Implementation worker contract*).

## Arming the wait when nothing is in flight

Step 16's native task/event wait is sufficient while workers are running: their completions are the events. A **settled** run has none. No worker will finish, no CI will fire, and the merge it is waiting on may be a day away — so a settled run that simply waits has no event source of its own, and "the run advances its own frontier" quietly becomes conditional on something nothing required it to arrange.

**Before a settled-and-undispatchable run stops doing work, it arms the wake `references/wake-budget.md` requires** — a PR-activity subscription over this run's own PR set, which `supervise-prs` armed per PR at adoption so this step confirms the set is complete and arms anything missing, and a bounded scheduled check-in as the backstop — under that rule's budget and backoff, which bind **every recurring check-in this skill's runs arm, parent-side or worker-side**. What this run adds:

- **the check-in runs `supervise-prs`, *Pass*, and re-reads the frontier**, and acts on what it finds; its prompt carries what that skill's comparison needs — the PR set and each PR's durable state (`supervise-prs`, *Wait*) — and the inputs this run passes it, as the last state block recorded them: budgets, counters, trigger states, the chartered-scope check's text, and the run's own write ids the reply watch below filters, hold retirement records included. **It also re-reads each held worker session** (`swarm`, *Blocked workers*) — one observed to have resumed, been released or been redispatched retires its item on that section's closing rule, and un-settles the run — **and where every open `NEEDS_USER` and `DECISION` item this run raised lives** — the item's own issue or thread, a short list bounded by the items themselves — for a reply newer than the item. No subscription delivers an owner answering on an issue, and a settled run otherwise holds work its owner has already unblocked. **A reply releases the hold only when it is the owner's and it answers the item** — authored by the owner, not a bot, not one of this run's own writes (the write ids its posting-identity map records — hold retirement records included — since the run commonly posts as the owner's own account), and choosing one of the options the item put. Then release what the item held, re-test dispatch (*When the advance waits for a human*), and report the release with the reply's URL; it is an observed answer, not a ruling, so write nothing claiming one — an interactive ruling is `settle-outstanding-decisions`' to record, and this wake is unattended. A reply that is ambiguous, answers something else, or comes from anyone other than the owner is reported and the hold stays. **Releasing the hold releases dispatch only**: the item stays outstanding for invariant 12 until the settled step's walkthrough retires it, since the owner's reply is a record it can retire it from without asking again (`settle-outstanding-decisions`, *What qualifies as an outstanding decision*). **A held worker's item is the exception**: only its hold's observed ending retires it, never a reply or a ruling (`swarm`, *Blocked workers*, its last rule). An item that rule restated to its work unit after an archive is no longer a held worker's item, and takes this paragraph's ordinary path. A wake that finds a new reply at an open item's site is productive, whichever way it goes. **A held worker session resuming, and a new reply at the site of an open item this run raised, are deltas** under the budget's clearing rule;
- **stop once every PR in the set is merged or closed and no item this run raised is still open**; until then the watch runs within the budget, which the open items do not extend. **Where an item this run raised is still open when the budget runs out, the stop report names each one and says that a reply to it will not be noticed until the run is invoked again** — the watch is bounded, and it says so rather than ending unannounced. **A stop on the budget ends the subscriptions with the check-in** — every PR still open is unsubscribed and named with its toggle line (`references/platform-pr-posture.md`, *The watch ends with the run, not after it*). A held worker session is returned as `swarm`, *Blocked workers*, requires when its watch is spent;
- **a quiet wake is silent about state and never silent about what is waiting on the owner.** The budget rule's unproductive-wake test is about *durable* state, and an outstanding `DECISION` or `NEEDS_USER` item is not durable state — it does not change until someone answers it, which is exactly the problem: a run can back off to four-hourly wakes, correctly report no delta each time, and never once say that three decisions have been sitting with the owner throughout. So every wake reports the outstanding `DECISION` and `NEEDS_USER` counts, on the same lengthening cadence as the wake itself, even when it reports nothing else. **And quiescence with open decisions is a settle trigger on an attended turn or a real state change, never on a quiet unattended wake**: a run whose only remaining movement depends on an answer nobody has been asked for has nothing to wait for, so it settles and routes the items through the settled step — but on a scheduled wake `settle-outstanding-decisions` declines for want of anybody to ask, and step 8 forbids re-deriving settled state that has not changed, so re-running the sequence there recomputes a summary, a walkthrough and a ranking for nothing and repeats it until the wake budget dies. The counts are reported on every wake; the sequence re-runs only where someone is there or something actually moved;
- **write the release step into the wake's own prompt, as well as the count.** The prompt a run writes for its own check-in is what survives compaction, and the run's memory of what supervision involves does not: an observed run on this tier dispatched separate implementation, review and repair sessions, never archived one of them, and left fourteen finished sessions alive until the owner asked — because releasing lived in the run's head and not in the prompt it woke to. So each re-armed prompt names step 11 — read the session list by provenance, apply the releasable test, archive what passes, report what was archived — and the settled step sweeps once more before returning;
- **the wake's prompt carries the posture line** (`references/platform-pr-posture.md`, *Saying so*), naming this skill — the check-in is the one wake whose text this run writes;
- **the wake's prompt carries, beside the count and the comparands the budget rule requires, each open item's site, the newest reply already seen there, and the ids of this run's own writes**, since the posting-identity map that tells an owner's reply from the run's own post lives in session memory, and a firing without it reads the run's own review trigger as the owner's answer.

**When neither can be armed**, reconcile durable state and return the restartable checkpoint the budget rule requires, naming the resume frontier and the PRs whose merges would advance it, exactly as Stop conditions already requires when the runtime cannot safely stay active. Restart / resume adopts that and re-derives readiness from durable truth, so what is lost is the automation, not the work.

## Frontier advance on merge

A merge someone else performed is a **frontier-advancing event**, not a terminal one: it is the thing that turns in-scope `BLOCKED` issues into READY work. Steps 6 and 7 of the loop above are how the run consumes it, and they stay reachable after the tranche settles. On every merge/close event:

1. reconcile tracker + GitHub remote state, so readiness is recomputed from durable truth rather than cached run state — **once per batch of merge/close events, not once per event**. **The batch is every such event already delivered when this step is reached**: drain the queue first, then reconcile once over all of them, and fold an event arriving mid-reconciliation into the next pass rather than starting a fresh one. A later event whose reconciliation would repeat one this cycle already performed over the same graph is consumed by it rather than repeating it. Where events genuinely arrive minutes apart each still gets its own reconciliation (NOTES);
2. restack affected descendants exactly as today (see Stack mutation while PRs are open), **and renumber the next independent colliding migration** where the merge was one of them (see Performing the renumber);
3. recompute the READY frontier over the **same bounded manifest**, crediting merges only (below). A merge never widens scope: an issue the invocation did not adopt does not become in-scope because something it depends on merged;
4. if new nodes became READY, re-run the preflight over the bounded scope before dispatching — **at the mode the escalation rules select**, not shallow by default (see Escalating to deep validation) — then fill free worker slots in scheduling order, **up to the `concurrent-open-prs` headroom** — free worker slots are not free PR slots, and filling four workers into one slot of headroom is three over the cap. The preflight is not optional here: it is mandatory before **any** new implementation worker, the merge changed the graph the previous run validated, and this is the case that needs the escalation most (NOTES). **What is optional is rebuilding what you already hold.** This run has a validated DAG and knows exactly what the merge changed; hand the validator that prior graph and the change, so it verifies the delta rather than re-enumerating hierarchy, project structure and every dependency edge from scratch (NOTES). Where the validator cannot accept prior state, the full re-derivation stands: the correctness rule is not negotiable and the cost is a tooling limitation to report, not a reason to skip it;
5. **whether or not anything became READY, a merge or close of one of this run's PRs released a `concurrent-open-prs` slot — if the cap was holding READY work, fill the freed capacity**, within `new-issue-budget` and running the preflight over the nodes it starts (step 4's waiver covers the *advance*, never a dispatch: the merge changed the graph, and invariant 7 dispatches only validated READY work). Otherwise stay settled and keep supervising. Without this step the release is real and nothing acts on it: a run settles legally with work held by the cap, its PRs then resolve one by one as leaves that advance nothing, the check-in stops re-arming once none is open and no item it raised is still open, and the run hands off with spend unused and dispatchable issues it was never told to start.

This requires no new user prompt. While `new-issue-budget` has headroom and in-scope work remains, a merge or close resumes dispatch inside the same invocation.

**Only a merge advances the frontier; step 3 credits merges alone.** A close is worth reconciling but is never an advance: completion is a closed issue **plus a merged** implementation PR (see Completion semantics), so crediting a close dispatches a fresh worker to recreate the PR a human just declined (NOTES), and an unmerged close unblocks nothing downstream — a descendant is not released by an ancestor that never landed. On an unmerged close, reconcile and stop there: hold that issue and everything downstream, surface it as `NEEDS_USER` naming the closed PR — abandonment, a rejected approach, and work superseded elsewhere are indistinguishable from the event and call for opposite next moves — and redispatch that path only on an answer, never on the close itself — **that prohibition is about the closed PR's own path and nothing else. The close still released a `concurrent-open-prs` slot, and step 5 fills it from the READY set the cap was holding**.

### When the advance waits for a human

Continuing is the default, and the advance never manufactures a question the skill has a documented default for (see Autonomy and interactive prompts). What it must not do is dispatch *through* an ask the previous tranche already left outstanding — starting the work is one way of answering it. Hold a path where an outstanding item bears on the work about to start:

- a `DECISION` action point, or a `MERGE_RISK` raised as `NEEDS_USER`, **whose answer would change what or how the newly-READY node gets built**. Dispatching commits the run to one answer before the human gives it;
- an unverifiable-prerequisite `NEEDS_USER` the merge did not satisfy — a merge retires only the blockers it actually satisfied;
- an **unproven dependency view** `NEEDS_USER`, which holds the whole advance rather than one path: step 3 recomputes readiness through the same transport whose reach is in doubt, so every node it just called READY shares the blind spot. **A worker cannot raise this against a boundary you classified `dependency transport unavailable`, and if one does, read it as a report rather than a hold** — there is no proof to re-establish, so holding the advance would stop the run permanently on a condition accepted at the preflight. Where a dependency transport does exist, re-establish the visibility proof before dispatching anything, exactly as at the preflight; where it does not, there is nothing to re-establish.

Everything else continues. A `NEW_ISSUE` follow-up, a question about how the merged PRs themselves are handled, or a `NEEDS_USER` on an unrelated branch does not hold a node it has no bearing on — and holding one path never holds the others: dispatch the unaffected newly-READY nodes in the same pass.

Read the merge itself as evidence. A user asked to choose between two approaches who then merged one has answered; do not hold work on a question their merge settled. What survives is the ask the merge left genuinely open.

Holding is not idling. Name the outstanding item, the node it holds, and what answer releases it — in the checkpoint output and as a live `NEEDS_USER` — and treat the answer as its own resume signal: the held node dispatches on a reply that passes the check-in's test (see Arming the wait when nothing is in flight), in the same run, with no re-invocation.

Nothing about the advance relaxes the safeguards it dispatches under:

- **invariant 12 still holds.** Auto-advance is triggered by observing a merge — whoever performed it, a merge invariant 12's gate authorized included — never by deciding one should happen. The advance itself merges nothing.
- **both budgets are consumed like any other dispatch.** If `new-issue-budget` is exhausted, do not dispatch: report the newly-READY frontier in the checkpoint output as the resume frontier, so a resumed invocation adopts it instead of rediscovering it. If `concurrent-open-prs` is the one exhausted, the frontier is reachable within this invocation without settling anything: dispatch into whatever headroom there is, which a merge of one of this run's PRs has just freed and a merge elsewhere has not — then wait for the next release (step 5). Silently dropping newly-unblocked work is the failure this step exists to prevent.
- **`NEEDS_USER` is not cleared by a merge.** A node whose only remaining blocker is a question a human was asked to decide stays blocked, and auto-advance must not resume that path (above). Only the blockers the merge actually satisfied are retired.
- `concurrent-workers`, attempt/repair caps, per-issue model selection, one issue per worker, and isolated checkouts apply to resumed dispatch unchanged.

Edge cases:

- **A merge that unblocks nothing in scope** advances nothing: no advance and no preflight *for the advance* — reconcile and restack, then go on to step 5, which still applies. **It still released a `concurrent-open-prs` slot**, so where the cap was holding READY work, fill the freed capacity — the release is a dispatch trigger in its own right, and a close of one of this run's PRs is too, though a close advances no frontier.
- **A merge landing while workers are still in flight** advances the frontier without disturbing them. Recompute readiness and dispatch only into free slots; in-flight workers are never cancelled, restarted, or re-scoped because their frontier moved.
- **A newly-READY node that re-blocks on validation** (the preflight returns `FAIL` on its path, or a warning that makes its ordering unsafe) is not dispatched. Record it and continue with the validator-confirmed safe branches, exactly as at the initial preflight.
- **A tranche that settled with a `DECISION` outstanding** advances every path the decision does not bear on, and holds only the ones it does. A pending question is a reason to hold a node, never a reason to stop the run.
- **A close event mixed into a batch of merges** — a stack where seven PRs merged and one was closed unmerged — advances on the seven and holds the eighth's issue and its descendants. Do not let the merges in the batch launder the close.

## How a worker's report actually reaches you

`swarm`, *How a worker's report actually reaches you*, owns the carrier — which runtime delivers a worker's report at all, what the session record carries without anyone writing it, and routing the report by whether a PR exists. What follows is the dependency-specific half: what this run does with a worker that stopped on a dependency before any PR existed, and why a report never becomes a blocker record.

On the no-PR path, first separate the dependency-shaped outcomes from the rest. A `FAILED` from an implementation or tooling fault carries no blocker URL, no resolution and no dependency credential — that absence is legitimate, not unanswerable, and feeding it into the decision below would send a compile error down the unproven-boundary path and hold every sibling. Route those by their own outcome: `FAILED` follows the retry policy, a product-decision `NEEDS_USER` its own handling. What follows applies where the worker stopped **on a dependency**:

- **`needs_action` carries the same duty on every dependency-shaped outcome, not only `NEEDS_USER`:** the blocker's canonical URL, how it resolved, and the worker's transport tier and non-secret credential identity. Without the identity a `BLOCKED` is uninterpretable in the one way that matters below — step 2's reconcile-and-stop is available only where both sides read the same transport, and the identity is what tells you whether they did.
- **One line cannot carry several blockers, so never read it as a complete set.** The summary is a **pointer**; its silence about further blockers is not evidence there are none (NOTES: the truncation case). And where it names **any** blocker the worker could see and you could not, the finding is not that edge — it is that **your view of that boundary is short**, whether or not the named edge was already in your set.
- The parent cannot close that hole by looking harder: repeating the dependency read under its own credential reproduces the blind spot exactly and returns looking like confirmation (NOTES: the redispatch loop).

The response is an ordered decision, and **every step resolves to the last branch when its input is missing** — absent is never treated as matching, as empty, or as agreeing, because falling through to the cheap outcome is precisely what resumes that loop:

1. **Can the blocking edge be identified at all?** A dropped URL has no PR and no readable transcript to recover it from, and the dependency set that would answer the next question is the very set suspected of omitting it. Unanswerable — go to 4.
2. **Did both sides read the same transport, and is that edge already in this run's dependency set?** Test the transport first: if the worker's credential reached edges yours cannot, **stop here and go to 4** whatever the membership answer is — a summary naming one blocker you already hold had room for one. Where both read the same transport and the edge is already in your set, only its *state* differs — an open PR not in the selected base, a prerequisite incomplete by its own measure, a `BLOCKED_EXTERNAL` that is a known wait rather than a graph error. That is an availability matter, exactly as Outcomes separates availability from visibility: reconcile that edge's state and stop. **Do not invalidate visibility for it**, or a prerequisite that merely changed state since the caller last checked holds every sibling on the boundary for nothing.
3. **If the edge is absent from this run's set, rule out an intervening change before concluding anything about visibility**, per Outcomes. Re-read now: if the edge appears, it was added between this run's readiness computation and the worker's read — a race, reconciled as an ordinary new dependency. If it does not appear, it is either invisible to this run's credential or was removed after the worker saw it, and **only a demonstrable removal resolves that** — otherwise go to 4.
4. **The boundary is unproven.** Establish visibility against a known-true case, per Transport visibility; where none is available the issue is held as the *unproven dependency view* kind of `NEEDS_USER`, which holds every sibling dispatched through the same read. Treat the block as disproof of this run's own view rather than as a claim to re-check, and the redispatch loop cannot form.

   **Unless the boundary is already classified `dependency transport unavailable`** — then no known-true case can exist by construction, and demanding one converts a limitation this run knowingly accepted at preflight into an indefinite hold on every sibling. The worker blocked on prose, the only source either of you has: reconcile the blocker from the issue's own text, and where that cannot identify it, escalate **this issue** as an unverifiable prerequisite — never the boundary, which was never provable and is not evidence of anything new.

**Where the worker's credential identity is unknown, treat it as differing** — the same rule as step 1, at the other input. `needs_action` is written by the runtime summarizing the worker's turn, not by the worker — a worker can only steer it by ending its turn saying these things, and how reliably the summarizer preserves them is **untested**. The identity and the blocker URL sharpen this decision when they arrive; neither is a precondition for reaching step 4 without them.

**`NEEDS_USER` needs one thing more**, because it is the outcome a one-line summary is least able to carry, and its two kinds demand opposite handling — an unverifiable prerequisite is a question for a person; an unproven dependency view is transport evidence that invalidates a visibility proof and holds every sibling. Require the dispatch prompt to have the worker put **which kind, and the exact measure that was out of reach**, into `needs_action` — the one place a terminal no-PR outcome can still say something specific. A parent left to infer the kind from an empty blocker list handles the expensive one as the cheap one.

The no-PR rule is not a concession to a limitation: establishing is the parent's job, needing a visibility proof the worker does not hold, and a worker writing unclassified findings onto an issue was always the parent's duty performed by the wrong party (NOTES: the inversion argument, and what the routing costs).

None of this is implementation-specific. A repair worker's return value is lost on the same tier in the same way; what its dispatch prompt carries for that is `supervise-prs`'s (*Repair dispatch*).

**A worker's report is evidence; a blocker record is a conclusion. Keeping them apart is what the routing (`swarm`, *How a worker's report actually reaches you*) is for.**

| | written by | says | restart treats it as |
|---|---|---|---|
| worker report | the worker, on its PR | what I observed | input awaiting classification — never a blocker |
| blocker record | the parent, after classifying | what was established, and how it was verified | an established blocker |

**Restart adopts blockers only from parent-written records**, per Restart / resume. An unclassified edge does not become established by surviving a session boundary: the finding survives; its status is not promoted by having survived.

A report must never land in an issue comment, and the reason is mechanical rather than tidiness: three separate skills read issue comments for dependency information (NOTES: how they were found), so a report there manufactures the permanent blockers this skill's persistence rule exists to prevent — automatically, on every run, as designed behaviour rather than as a mistake someone might make:

| reader | what it does with a comment-named edge | why it matters |
|---|---|---|
| `implement-issue-core` | unions it into the issue's blocker set | re-blocks the issue on every later dispatch |
| `validate-backlog` | scans comments in a **mandatory preflight** | reintroduces the edge before any downstream exclusion applies |
| `normalize-github-dependencies` | **promotes it into native metadata** | worst case — native is authoritative and an empty `blocked_by` is indistinguishable from "no blockers", so nothing later re-examines it |

**As a backstop for a report that lands on an issue anyway** — older tooling, a hand-pasted transcript, a worker running an earlier prompt — those three skills also skip any comment whose first line is exactly `**Worker report — unclassified evidence, not a dependency record.**`. Treat that as a property of the marker rather than a patch in three files: a comment opening with that line is not a statement about the issue's dependencies, and no reader may take an edge from it. It is a second line of defence, not the mechanism; the mechanism is that reports go on PRs and conclusions are the parent's to write.

## Verifying worker reports

`swarm`, *Verifying what workers report*, states the rule; apply it from there. For a PR, the durable evidence is CI on the pushed head, and the rule reaches one decision that module does not have: never block a merge decision on a worker-reported failure unverified. The same status attaches to a reviewer's claim of a commit, a carried note from a previous run, and this run's own statement of what it is about to do (`references/establish-do-not-assume.md`).

## Checkpoint compliance

`swarm`, *Checkpoint compliance*, owns what the parent observes of every in-flight worker each cycle, the stalled-head escalation, and when it nudges and when it captures instead (its *Enforce, do not re-ask*). It also owns how the parent captures — the ref-neutral sequence that does not race a live worker, its verification, the recovery-ref naming, the wedged-worker path and the tested script beside that skill (its *Capturing without racing the worker*) — and the recovery ref's generic lifecycle (its *The recovery ref's lifecycle*). Apply them from there; here the worker's branch is its issue branch, and its task-owned paths are the issue-owned paths. This section is what becomes of a ref this run captured: an ender keyed on PR state, the issue's completeness and invariant 12, which replaces `swarm`'s generic reachability ender (the rest of that lifecycle — redundancy, release-time reconciliation — still applies).

**The principle is `swarm`'s — a recovery ref is dropped only once a durable carrier the run will actually read holds its contents.** The four PR states differ solely in whether such a carrier exists, and enumerating them explicitly is deliberate — this rule was built one case at a time and each missing case left a ref with no ender, which invariant 12 then converts into a PR that can never merge. Its consumers are the release-time reconciliation and the blocked-worker archive (`swarm`, *The recovery ref's lifecycle* and *Blocked workers*), and lost-worker recovery (Lost worker / workflow recovery):

- **PR open.** Reconciling advances the branch, so the PR's CI and review evidence now describes a head that no longer exists — the same staleness publishing produces, and handled the same way: that PR re-enters ordinary supervision and is re-evaluated on a later pass. Until the reconciliation lands the PR carries an outstanding recovery ref, which the gate excludes; merging there would drop work the run itself decided was worth rescuing. Once it is on the branch, **verify the capture's commit is an ancestor of the branch head, then delete the ref.**
- **No PR yet** — a worker that returned `BLOCKED` or `FAILED` before creating one. `swarm`, *Releasing a worker*, says PR state is irrelevant to release, so this worker is as released as any other. Reconcile as `swarm`'s release-time reconciliation says (*The recovery ref's lifecycle*); then verify and delete exactly as above. The branch is a carrier the run reads — it is item 3 of the durable-evidence order — so a redispatch picks the work up, and no issue is at risk of being called complete, since nothing here looks like completion.
- **PR closed without merging.** Same handling as no-PR: the branch is still the carrier, nothing merged, the issue is not complete. Reconcile, verify, delete — and **report it**, because a closed PR usually means a person decided against that line of work and a capture landing on its branch is worth their knowing about. Do not treat the closure as authority to discard the capture; that decision is theirs and this path does not ask them for it.
- **PR already merged.** Here **branch reconciliation is not a fix and must not be performed as though it were.** `swarm`, *Releasing a worker*, treats a merged PR as eligible and *common* — a wake armed at PR creation outlives the PR that armed it, so the work has usually landed by the time anyone finds the session. The merge commit is already in the base; pushing the capture to the issue branch afterwards moves nothing that matters, no CI or review round runs on a merged PR, and the gate has nothing left to withhold. Every mechanism the open case relies on is absent, and so is the carrier: the branch of a merged PR is not read again.

  So this case is `NEEDS_USER`, and it carries a second correction: **that issue is not complete**, whatever the merged PR implies, and must not be reconciled to complete while the ref is outstanding. Surface the issue, the merged PR, and the ref name. Do not open a follow-up PR automatically — the capture is a WIP snapshot of unknown completeness (`swarm`, *Capturing without racing the worker*), and landing it under the authority of a review that never saw it is the one outcome worse than reporting it. **Delete nothing** until the owner decides; here the ref is the only copy, and this is the branch where dropping it would be irreversible.

### Where the parent cannot reach

This contract assumes two capabilities the parent has to have — that it can **see** a worker's checkout and **send it an instruction** — and they come apart, so it is worth naming which tier has which. Both are established at startup rather than assumed (`swarm`, *Remote worker session arguments*). **Subagents in parent-created worktrees**: both, and the escalation (`swarm`, *Checkpoint compliance*) runs as written. **Remote worker sessions**: normally neither, and never assumed either way — the channel is whichever the recorded capability says, absent for every worker session the observed runtime was asked about, and the checkout is not reachable — the session record hands out a repository and no path, and the container is not shared — so the escalation has no first step *and* no second one, and what remains is the worker's own pushes plus `NEEDS_USER`. **A Dynamic Workflow fan-out**: neither half — workflow agents accept no input mid-run, and the worktrees the runtime creates for them are not paths the parent was given.

So the remote-session tier belongs beside the workflow tier for this section's purposes, not beside subagents, which is the opposite of where it sat while the *see* half was assumed. The two tiers differ in what substitutes: a workflow run can be made to checkpoint **structurally**, by splitting implementation into stages the script pushes between (below), and a remote worker session cannot — nothing in the parent's reach interposes on it, so its dispatch prompt is the only lever and the honest guarantee is weaker. State that in the checkpoint output rather than reporting invariant 5 as enforced.

So under a Dynamic Workflow, enforcement has to be structural — encoded in the script's control flow, which is deterministic, rather than in an agent prompt, which is the thing that does not land.

**Checkpoint granularity equals stage granularity.** A script can only interpose where it has a stage boundary, so a single checkpoint stage after implementation is not a checkpoint at all — it is the final push, which the worker was going to make anyway. If implementation hangs or the container dies inside that one long stage, the stage never returns and nothing was saved. Bounded loss requires implementation split into several bounded stages, each ending with a push: the number of boundaries is the granularity, and one boundary at the end is none.

That only works where the issue's work decomposes into units the script can name in advance — per-file tranches, per-module conversions, work already sliced by the ticket. Where it does not, the workflow runtime **cannot** satisfy invariant 5 for that issue, and no arrangement of stages changes that.

So the runtime preference is conditional, not absolute. A Dynamic Workflow suits the fan-out shape, but invariant 5 outranks that convenience: prefer a runtime whose workers the parent can reach whenever the implementation cannot be staged into script-visible units. Unreachable-mid-run is a real cost of the workflow runtime, the same one that already disqualifies it for PR supervision — this is the second thing it cannot do, not a footnote on the first.

## Cross-branch artifact collisions

After each PR reaches durable state, compare it against the other open branches targeting the same base and flag three things: files that two branches both **add** under the same name or sequence number; incompatible edits two branches make to a shared claimed artifact — a generated manifest, lockfile, registry or index that branches amend rather than create, and which therefore collides with no added path in common; and **a collision with no textual overlap at all**, where one branch renames or redefines something another branch's new code depends on by name. The general class of the first two is any artifact whose identity or ordering is claimed rather than derived.

**The third kind has no conflict signal of any sort, and only the merged tree shows it.** One branch added tests querying the string `Center`; another renamed it to `Centre`. No line was shared, git merged cleanly, and neither PR's CI could have caught it — each was green against a base that did not yet contain the other. The default branch's own CI found it, after both had landed. So this kind is not detected by reading diffs: it is detected by merging the branches into a scratch branch and running the suite whole, which is the only artefact that contains both changes at once.

**The comparison set is every open branch targeting that base, not this run's own members.** An observed tranche ran exactly this integration check, over the branches it had dispatched, and caught a real conflict with it — and missed this one, because the colliding branch belonged to a different track running concurrently in the same repository. The check was right and its input set was wrong. **State in the run's output which branches were integrated, each with the head SHA it was integrated at**, so a set that turned out to be partial is visible as partial rather than as a clean result — and so the gate can tell whether the tips have moved since (see `settle-and-merge`, *Merge behavior*).

Two chains cut from the same base can each be internally consistent and both pass CI while colliding, because neither can see the other; the conflict only materializes when the second one merges. Dependency edges and stack ancestry do not detect this — the branches are siblings, not ancestors — and concurrency makes it worse rather than differently: a track this run did not dispatch is not in its graph at all.

For the first two kinds, correct resolution depends on merge order. **Where the colliding artifacts are shown independent — sequence-numbered migrations whose bodies touch different tables and objects, with no foreign key, view, trigger, shared type or backfill reaching into the other's change — do not ask** (owner's ruling, NOTES). Read that off both bodies; interaction not ruled out is interaction, and the identity files the generator rewrites during a renumber (a journal, a snapshot) are not evidence either way: any order works, so they merge in `plan-merge-order`'s ranking and each later one is renumbered after the one before it lands (*Performing the renumber*), and the report names the order taken. **Where they interact** — the same table or object, one depending on the other's change, or any shared-artifact edit that is not a sequence number — the order decides the outcome and this skill does not own it: surface the collision as `NEEDS_USER` with both PR URLs and the colliding paths. Never renumber or rewrite the artifact pre-emptively.

**The third kind does not take that remedy, because ordering cannot resolve it.** Whichever of `Center` and `Centre` merges first, the final tree is the same and it is broken — there is no order that works, so there is nothing for an order decision to decide. One branch has to change: either the rename follows through into the other branch's new references, or the new code is written against the new name. Surface it as `NEEDS_USER` naming both PRs, the symbol, and the fact that **no merge order resolves it** so nobody spends the decision on ordering — and where the owner picks a side, the repair is an ordinary `finding` repair on that PR, after which **the integration check is re-run**: a repair that fixes one reference and misses another produces exactly the same clean diffs it did the first time.

**Expect a sequence-number collision at dispatch rather than discover it at merge.** Where more than one open branch targeting a base may generate a migration — an issue this tranche dispatches that names a table, column, index or migration, or another track's branch that already carries an added migration, since the comparison set is every open branch (above) — each branches from the same base, runs the generator, and correctly takes the next free number, so every one of them claims the same number and every one passes CI, a migration-consistency check included, because each is consistent with the base in isolation. Four workers claimed one number in an observed tranche. Tell each such worker, in its dispatch prompt (Before dispatch, step 10), that siblings exist and that its number is provisional, so no PR body presents it as final, and record the expected renumbers against the merge order when the PRs exist.

### Performing the renumber

**Produce it with the repository's own generator. Never hand-edit the artifact's identity fields.** A claimed identity is rarely stored in one place, and the copies that are not the visible filename are usually the ones that decide whether the artifact runs — a hand-rename that misses one makes the artifact **silently skipped**: no error, no log, green CI, and the change never applies (NOTES: the five-place Drizzle example and the observed renumber incident).

The class generalizes past migrations: any artifact whose identity is **claimed rather than derived and spread across more than one file** — a migration with its journal and snapshot, a lockfile with its manifest, a generated client with its registry entry. Renaming what you can see is precisely the operation that leaves the rest stale.

**A renumber is a mutation like a restack**: never start one on a branch whose `supervise-prs` record shows a mutator — wait for that pass to return — and hold the branch locked while it runs.

**Where the artifacts chain, the renumbers are strictly sequential.** A migration snapshot that records its predecessor's id cannot be renamed into place: the second PR's snapshot is regenerated against a schema that now includes the first PR's change, the third against both. So one renumber per merge, each after the previous one lands and each followed by CI — never all of them at once against the same base, which reproduces the collision one layer down.

**Where the artifact carries a hand-written body review read — a migration's SQL — regenerate the identity and keep that body verbatim.** The body is what review read, and a regenerated one need not reproduce it — an expression index or a partial `WHERE` can come back different. So the pass regenerates the snapshot, the journal entry and the number, and carries the reviewed body across unchanged. Check that the body differs from the reviewed one only in its number and filename and that the new snapshot's predecessor id is the id of the base's latest snapshot; whether the push then needs another review round is `references/mechanical-pushes.md`'s call, not this section's.

Then verify the result **applies**, not that it compiles and not that CI is green. A skipped migration passes both, which is why neither is the check. Run the artifact's own apply path — migrate against a scratch database, install from the lockfile, regenerate and diff against the committed copy — and confirm the effect the artifact was supposed to have is actually present. For such an artifact, carrying the reviewed body across is the splice, done every time rather than only where the generator falls short; re-verify after it, because a carry that was skipped or partial leaves a regenerated body that silently dropped a backfill — the same failure with the sign flipped.

Until that verification passes, the renumber is not finished, and it is not mechanical — see Mechanical pushes do not consume review, which grants the skip-re-review exemption only to a renumber that has cleared this.

# Lost worker / workflow recovery

`swarm`, *Lost workers*, owns the procedure — what to inspect in which order, adopting pushed checkpoints, the redispatch and the escalation on repeated loss — and applies here as written, with the issue as the task, `lost-worker-redispatches` as its budget, and tracker state among what a resume reads when the whole cloud container/workflow disappears.

Its step 4 ends the recovery ref by **the four-state rule under Checkpoint compliance — apply it, do not restate it here.** All four states reach this consumer: a worker can disappear before opening a PR, after its PR was closed unmerged, while it is open, or after it merged, and each has a different ender (NOTES: the two-state copy that lived here and what it missed). Unconsumed, the ref blocks invariant 12's gate over work that has already landed.

# Stack mutation while PRs are open

When an upstream stack branch changes, descendants may become `STACK_STALE`.

Do not blindly restack every descendant after every upstream push. Instead:

- **never restack a branch whose `supervise-prs` record shows a mutator** — a repair pass in flight; wait for it to return, then lock the branch before restacking;

- record stale ancestry;
- restack before descendant diffs/CI/review become misleading;
- ensure ancestry is correct before merge-ready state;
- pass each restack push to `supervise-prs` as a caller push, tagged by `references/mechanical-pushes.md` — a restack-only push is mechanical: no review re-trigger, no cycle consumed;
- use `merge-stack` for authorized merge/restack operations;
- hold the branch locked while restacking, so `supervise-prs` dispatches no repair to it meanwhile, and pass the new heads before its next *Pass*.

# Outcomes

- `PR_OPEN` — implementation reached durable remote PR state; parent/runtime owns supervision.
- `BLOCKED` / `BLOCKED_EXTERNAL` — stop affected path; never silently enlarge scope.
- `BLOCKED_EXTERNAL` **on an unmet dependency** — a known wait, not a graph error, and by the worker's contract it means *every* unmet blocker was external. Work nobody in this run was authorized to do is not evidence that readiness was computed wrongly, so stop that path without re-deriving the frontier or invalidating a visibility proof over it. A worker that found any in-scope blocker alongside an external one returns `BLOCKED` instead, so this outcome never conceals one. A source disagreement reported alongside it is still transport evidence and still handled as such.
- `BLOCKED` **on an unmet dependency** — authoritative new information about the graph, not a worker failure. It means the readiness computation was wrong, most often because the dependency read behind it was silently partial. Never redispatch the same issue unchanged; nothing about the second attempt would differ. Retry and escalation budgets do not apply, because there is no failure to retry.

**Confirmations are evidence too.** A worker reports how every dependency it checked resolved, not only the disagreements — a resolution that matched your view turns an assumed edge into a verified one. Record it, but record the right thing: two claims are bundled in a resolution and they age differently:

- **the edge exists** — structural, and long-lived. Persist it as verified, with the read it came from and when; it stops being an assumption but not being an observation — a dependency can be retired after a worker confirms it, and a verified edge with no way to retire blocks or orders work for every remaining run;
- **the dependency was available** — an observation with a timestamp, and nothing more. A force-push, revert or rollback can undo it, as the availability-repair table below acknowledges.

So a verified availability resolution is historical evidence, never a standing exemption: every dispatch still re-checks the class-specific measure (NOTES: why the record must never become a skip). What the record buys is a restart that knows which edges are verified and which are assumed.

**How a verified edge retires.** By provenance, since provenance decides which read can speak to it:

- **native-sourced** — a later native read with **proven visibility for that boundary** that no longer returns it retires it. An unproven read does not, on the asymmetry stated throughout: absence observed through an unvalidated transport is not evidence of absence. Nothing else is needed here, because your own reads recur;
- **established from a worker's evidence and recorded as an issue comment** — no native read can retire it, since none was ever supposed to show it, so absence proves nothing in this direction either. It must not stand forever on that technicality: from your own native view it is indistinguishable from a prose-only edge, so classify it on the same path — establish whether the relationship still holds, `NEEDS_USER` where the issues cannot settle it — **when a run adopts it**, which is where the permanence would come from, and once per run (per dispatch attempt would re-ask the question every cycle a legitimately blocked issue stays blocked).

**Provenance here is where the edge lives now, not where it came from.** An edge recorded as a comment and later made native by `normalize-github-dependencies` takes the first row from then on — that is the point of normalizing it; judged by origin instead, it sits in the row where absence proves nothing and becomes exactly the permanent edge this rule exists to prevent.

An edge a worker found only in prose does not arrive here at all; it is classified first (below), because persistence is what makes a stale edge permanent. Retirement does not retract the observation — it records, dated the same way, that the relationship no longer holds, so a later read finding the edge again is a change rather than a contradiction.

This adopts findings, never a re-plan; the validated DAG remains the scheduling graph.

**A worker returns two independent things: an outcome, and evidence about the graph. Act on the evidence regardless of the outcome.** A source disagreement reported on a `PR_OPEN` is the same evidence of a partial dependency view as a `BLOCKED` would have been; treating only `BLOCKED` as a graph update leaves every sibling scheduled — bases and dispatch order chosen — against a view already known to be wrong.

**A satisfied dependency whose capability is absent is evidence of the same kind.** A worker that finds a declared dependency satisfied on paper — closed, merged, correctly linked — but the capability it needed absent from the code has found a **coverage** gap, a first-class finding on this path, not a note in its PR body: the worker is correcting the graph's meaning from a position the validator did not have, exactly as for an unmet blocker, so accept it on the same terms. Require it explicitly rather than hoping for it — the worker returns the finding whatever its outcome, naming the dependency, the capability it expected, and what it shipped instead (NOTES: why shipping silently, not the missing capability, is the failure mode). The parent records it durably against both issues like any other established blocker, **files the prerequisite issue**, holds the affected path behind it, reports it in the checkpoint alongside discovered dependency edges — and treats it as a trigger the preflight should have caught: the escalation rules under Escalating to deep validation did not fire on a node that needed them.

**A PR shipping against a coverage finding must not close its issue.** Filing the prerequisite is not enough: a closing keyword auto-closes the partly-implemented issue on merge, and the `DONE` test then reads clean over unfinished work (NOTES: why that state gets no further attention). The finding must reach `create-pr`, which links such a PR with `Part of:` and `Blocked by:` rather than `Closes:`; pass it through `implement-issue-core` on dispatch and verify the emitted form on the returned PR — a default that closes is what silence produces. The issue stays open, linked to its prerequisite; a human closes it once the gap is filled. Retrofit an already-open PR the same way when a finding arrives late — edit its body to the non-closing form before it can merge. A merge that has already auto-closed an issue on a coverage finding is reconciled by reopening the issue, not accepting the close: the tracker recorded a claim the work does not support.

**Only a visibility disagreement is transport evidence.** The worker reports two kinds and they warrant very different responses. An **availability** disagreement says your base or completion claim was stale. Two things pick the repair: the direction, and **the dependency class the worker reported** — it names the class precisely so you can route this, so read it rather than assuming a base problem.

| direction | code dependency | non-ancestry dependency |
|---|---|---|
| you asserted satisfied, worker observed otherwise | your base no longer holds — recalculate and restack, and check whether it was wrong when calculated or overtaken since, because a revert or force-push that keeps happening is a different problem from one bad calculation | your completion claim no longer holds — recheck it, or keep waiting; ancestry is irrelevant and no restack fixes it |
| you asserted unmet, worker found it available | your constraint may be obsolete — recheck rather than leaving the issue parked | same: recheck the constraint, do not park indefinitely |

Neither direction, in either class, touches a visibility proof. Invalidating a proof and halting slot-filling for a stale base is an expensive answer to a cheap problem. Everything below applies to **visibility** disagreements, where some other source named an edge the worker's native read did not return.

**First, a worker may not have been able to make this comparison at all.** Where the probed transport returns no edges — GitHub with no authenticated `gh` (see `validate-backlog`, *GitHub dependency reads depend on where you are running*) — the worker reports native as **unreadable** and its blocker set as unproven, not as an edge set that disagreed with yours. Where a read *was* available, the comparisons below apply normally, GitHub included.

**Where the worker could not read and you could, the obligation is yours, not a note to carry forward.** This is the **mixed** case — a local orchestrator with an authenticated cross-repo `gh` dispatching cloud workers that have none. It is not the common shape (**both-cloud is first-class, and there the limitation is symmetric so this branch does not apply at all**), but the mix is where an asymmetry hides: the worker's prose-only check cannot catch a blocker added between your preflight and its dispatch — the very race a worker's re-read exists to catch — and your supplied context is by then stale. **Perform a contemporaneous dependency read yourself before accepting that PR, or hold it.** The context you already hold does not qualify, and neither does the worker's report: it correctly says it could not look (NOTES: why the asymmetry must not pass as a difference in reporting detail). Never process this as a visibility disagreement — nothing was compared, so nothing invalidates a proof, and treating it as one would halt every sibling on the boundary on the strength of a read that never happened. And it obliges the refresh above, **not** a decision about whether to dispatch: that decision was taken before this worker ran, under the carrying-unproven-completeness rule at the *dispatch* gate, and repeating it here would let the PR through on the stale preflight it was taken from (NOTES: why the two gates read almost identically and permit opposite things). Everything below applies where the tracker actually returns edges.

Two variants can be demonstrations rather than suspicions — but only on conditions you must check, not assume, and the first is that you are comparing like with like.

**Compare native read against native read.** Your context is a union: edges from your own native read, plus blockers established from previous workers' evidence, deliberately recorded as issue comments rather than native edges. A worker's native read is *supposed* to lack that second kind, so their absence demonstrates nothing. Mark the provenance of every edge you supply, and apply what follows only to edges your own native read produced — otherwise this rule fires on the graph corrections you yourself recorded, and each one invalidates a proof and halts dispatch.

Then, for a native-sourced edge: where **you supplied** one the worker's native read lacks, or where **its native read has one your context omitted**, compare the credential identity behind your read against the one behind the worker's. You already record yours per credential; the worker reports the transport and identity it used.

**Distinct identities** — two credentials disagreeing about one graph is the cross-credential comparison the corroboration rules ask you to arrange, arriving unasked. **Independence and contemporaneity are separate conditions, and a mismatch is proof only with both**: the reads were taken at different moments, and an edge added or removed in between makes both credentials correct and neither view partial. Rule that out first — re-read the relationship through both identities, or check the edge's own history — and then invalidate; skipping that step spends a valid proof and halts every dispatch sharing the boundary on what may be an ordinary edit (NOTES: the time axis as the second proxy correction).

**The same identity** — a subagent worker inheriting this session's credential is the common case, not the exception — proves nothing on its own: one credential cannot corroborate itself, across moments any more than across transports. The mismatch may be an edge that changed between the reads, or caller context that went stale. Take the ordinary corroboration path and treat it as evidence.

The direction says whose view was partial, and therefore what to fix. Yours missing an edge the worker saw means **your** frontier was computed short — recheck it for every issue that shared that read, not only this one. The worker missing an edge you had means its transport is the partial one, and the recovery below applies as written.

**A visibility disagreement is first evidence about the transport, only second about one edge.** Adding the single dependency a worker happened to find and re-deriving against the same view leaves every other hidden edge hidden — the ones absent from both native metadata and prose are still invisible, and siblings still get dispatched from a frontier built on them. So read the disagreement against that boundary's visibility proof (see Proving a transport can see the graph), because the proof's state determines which of two very different things you are looking at:

**Visibility unproven, or the proof invalidated** — treat this as truncation, not as one missing edge. **This whole branch presupposes a proof existed to lose; it does not apply to a boundary classified `dependency transport unavailable`**, where none was ever obtainable, nothing was truncated, and steps 2 and 3 below would demand re-establishing something that cannot be established:

1. adopt the named dependencies **provisionally** — real enough to schedule against, not yet established;
2. invalidate the relationship-visibility proof for that credential, exactly as an authorization error would;
3. **re-establish the proof** before filling further worker slots — a read with proven visibility for the boundary, established against a case whose answer is already known; not merely another read through another credential, which is the proxy retired below and can share the blind spot. You do not know what else is missing, and one recovered edge is not a reason to trust the rest;
4. **re-evaluate every provisional edge against the read you just obtained.** If it proves the boundary and still shows no native edge, that edge has moved into the proven case below and needs its classification before it is kept — a stale prose edge adopted while visibility was unknown must not become permanent merely because it was adopted first. Provisional edges are not eligible for the persistence rule above until they survive this step;
5. then re-derive readiness for every issue that shared that view, and re-check calculated bases for anything already dispatched against it.

**Visibility proven for that boundary** — native metadata is trustworthy there, so prose naming an edge it does not show is more likely stale text than a hidden edge: a dependency deliberately removed from metadata and left behind in the description. Do not auto-adopt it. Classify it — verify whether the relationship still holds, not merely whether the referenced issue is implemented, which is all the worker checked — and surface it as `NEEDS_USER` where that cannot be settled from the issues themselves. Never persist an unclassified prose edge: persistence is what makes every future restart re-adopt it, so a stale edge written down once blocks the issue indefinitely.

When classifying, use the preflight you already ran. `validate-backlog` warns on exactly this shape — text names a blocker with no structured edge — so check whether it flagged this edge before dispatch. An edge flagged at preflight **and** reported by a worker is two observations that read the *same prose*: their agreement about the prose is not independent and establishes nothing that was in doubt. What it does establish is on the other side — two native reads both lacked the edge — and that rules out truncation only if at least one of those reads had **proven visibility for this boundary**. Distinct credential identities are not enough: two credentials can share the same insufficient scopes, repository boundary, or relationship transport, and then both omit the same real edge and their matching absence proves nothing. With a proven read among them, the question narrows to classification — the native edge was never created, or the prose is stale; without one, take the validated-read path as normal. **The property the conclusion needs is visibility, proven — never a proxy**: distinct transport, distinct credential, and distinct moment each failed as stand-ins, because a proxy can coincide with the thing it stands in for (NOTES: the proxy ladder, and what corroboration actually establishes here).

The reverse also holds: a preflight warning no worker ever confirmed stays outstanding — do not let it expire quietly because its issue happened to complete.

Either way, do the graph work **before** filling further worker slots. One worker's disagreement is the cheapest evidence available that the graph is wrong; discarding it because that worker happened to succeed wastes the only signal the system gets.

**Persist it, or the next session repeats the mistake.** By invariant 1 run state is a cache, and restart re-expands the same manifest through the same transport that truncated — computing the identical wrong frontier unless the edge was written down. Record each **established** blocker — a truncation-case edge that survived re-evaluation against the validated read, or a classified prose edge confirmed to still hold — where the restart path already looks: a comment on the affected issue naming the blocker by canonical full URL and how it was verified, plus the checkpoint output. Persist nothing merely unclassified: writing it down is what makes every restart re-adopt it. Where dependency-write capability exists and the edge is high-confidence, `normalize-github-dependencies` is what makes it native — invoked explicitly, never as a side effect of this reconciliation.
- `FAILED` — retry only inside budgets; at most one reasoning escalation.
- `NEEDS_USER` — surface full issue/PR URLs, failure/review state, attempts consumed, and recommended action; stop spending tokens on that node while continuing safe independent branches.
- `NEEDS_USER` **on an unverifiable prerequisite** — not a graph error and not a failure, and you can rely on that rather than re-checking: the worker's precedence returns `BLOCKED` whenever any in-scope blocker was also unmet, so this outcome carries none. the worker could not observe the completion measure that dependency's class requires, typically a release or deploy state outside the repository and tracker. Ask the specific question, and once answered supply it as dependency context on the redispatch — the caller asserting satisfaction is the documented path for a measure the worker cannot check. What asking buys is the **end of the uncertainty**, not the clearing of the blocker. Those come apart on a negative answer: told the release has not happened, the prerequisite becomes a known unmet blocker and the redispatch returns `BLOCKED` or `BLOCKED_EXTERNAL` by its authorization membership. Only an affirmative answer clears it.

- `NEEDS_USER` **on an unproven dependency view** — the worker could not establish that its blocker list was *complete*, with or without entries in it: your context arrived without a proven read, so its sources collapsed to one native read of unknown reach. **This is not the `dependency transport unavailable` case**, where there is no native read at all and completeness is unproven by construction on every issue: that is a condition of the run, recorded once and carried in the dispatch prompt, not a per-issue outcome that stops anything. A list with one blocker in it is not the reassuring version of this — a partial list is the dangerous one. This is transport evidence, not a question about the issue, and it is the one `NEEDS_USER` you must act on before dispatching anything else. Invalidate the relationship-visibility proof for that boundary and re-establish it against a case whose answer is known, exactly as for a visibility disagreement — every sibling you judged READY through that read shares the blind spot, and the worker only stopped because you told it the view was unproven. Do not answer this one by re-asserting readiness; that suppresses the stop without changing what is invisible.

And even an affirmative answer clears only this blocker, not the issue: the precedence ranks an unverifiable prerequisite above an external wait, so this outcome can arrive with an out-of-scope blocker still unmet and reported alongside. Read the reported blockers before expecting a redispatch to proceed. Do not invalidate a visibility proof over it; nothing here says the transport is partial.

# Settled tranche

A run is **settled** when nothing in scope is dispatchable and every open PR is individually finished or surfaced:

- **nothing in scope is dispatchable.** Work is dispatchable when this run could start it this cycle: it is READY; nothing holds it for a human — a `NEEDS_USER` classification, a `DECISION` or other ask under *When the advance waits for a human* that reaches it, or a validation stop on its path, **each of which has been put to the owner as an item** (a stop the preflight only recorded is raised as `NEEDS_USER` naming the path and the defect when it becomes the last thing holding work); and every budget and capacity check has headroom for it. That covers resuming an adopted branch and redispatching a returned issue with attempts left, not only starting an unstarted issue. **State it this way, as a positive condition, and never as a list of the kinds of issue that may remain**: this bullet has wedged the run five times, and every time the cause was a list of acceptable remainders that missed one — the last was a READY issue held by the open-PR cap with a child blocked by it, which fit none of four listed kinds. The complement of a positive condition is closed by construction. Everything in scope that is not dispatchable is waiting on something — unmerged work, a human, or a budget or capacity limit — directly or through its blockers, and the other conditions below or the owner account for it. Say in the checkpoint what holds each READY issue that is held. A capacity limit that resets on its own — an API allowance, a model's capacity — is re-tested on the next wake while one is armed; where nothing is open to arm one, it is raised as `NEEDS_USER` naming the limit and when it resets, since a settled run with nothing open never wakes to re-test it. One that will not, with no worker in flight — disk exhausted by retained worktrees — is raised as `NEEDS_USER` naming the limit, which makes it a hold for a human like the others. **This must stay one bullet**: every bullet in this list must hold at once, so two answering the same question are ANDed, and a merge that keeps both sides of a conflict here produces exactly that.
- no implementation or repair worker is in flight — and a worker blocked on a permission prompt is in flight, not absent (see `swarm`, *Blocked workers*): it reads as quiet from every angle the other conditions look from, which is how a run declares itself settled over a worker stopped mid-issue. **Except a held worker that is surfaced** (below), which counts here as surfaced rather than in flight;
- **every open PR from this run is `finished`** (`supervise-prs`, *Outcomes*, owns the definition) **or surfaced** (below) — so none is waiting on CI, a review round or a pass;
- **no worker session this run created is still alive** — verified against the runtime's session list by the reconciliation step of the supervision loop, never against the run's memory of having archived. A run holding a live session it created is not settled, cannot emit a clean settled report, and does not reach invariant 12's gate; this is what makes a skipped or merely-reported release detectable rather than forbidden. **The one exception is the session of a held worker that is surfaced** (below), including a mismatch the lever did not close (`swarm`, *Releasing a worker*). It is never archived on the run's own authority, so it stays alive; it does not block settlement, and the settled report and every state block name it as alive, with its URL and what it is waiting on, so a live session is never one the output omits. Any other live session this run created still blocks. Only sessions proven to belong to another run or to the user are excluded — reported, never reclaimed, and never counted, so someone else's leak cannot wedge this run's settlement.

**Surfaced is one set, stated here and cited by the conditions above that admit it.** Each member is held for the owner — and where it raises an item, that item has already been put to them — so it holds merges — that PR's, and while an item it raised is outstanding every PR's in the tranche, as invariant 12's gate reads items (`settle-and-merge`, *The merge gate*) — and a held worker holds its own work, but **none holds settlement**: a run that waited on it could never reach the walkthrough that rules on it. The set:

- **what `supervise-prs`, *Outcomes*, counts as surfaced within `finished`**, as that definition states it — the expected-red check among them is the one whose remedy is this run's (*CI/review repair*);
- **a PR `held: check` by the chartered-scope check, with its `DECISION` raised as an item.** The `DECISION` is ruled at the settled step's walkthrough, and the release is passed after;
- **a PR `needs-user`, with its question raised as a `NEEDS_USER` item** — a spent CI or finding budget, a failure needing judgment, a pass that returned `FAILED` or `NEEDS_USER`. Nothing the run can do moves it before the owner answers, and the settle sequence is where the question reaches them if it has not already (*Autonomy and interactive prompts*) — the walkthrough, or the closing output where nobody is present to ask;
- **a worker held on the owner's authority** (`swarm`, *Blocked workers*, its last rule) **and raised as a `NEEDS_USER` item**, with its session — until that rule retires the item, when it stops being a member: resumed, it is in flight; released or redispatched, its session is gone or new. **Where an archive left the item standing, restated to the work unit**, that unit stays a member by its ordinary `NEEDS_USER` item, with no session, and its dependents are still named as waiting on it.

A member that raises an item is not surfaced until the item is raised; raising it is this cycle's step 15. **A member whose item is ruled stays surfaced until it moves**: a ruling that neither changes code nor merges — close it, leave it to me — is reported with its next owner, and the PR stays as it is; a ruling to try again moves it through the finding path, or cannot where the finding budget is spent (*A settle finding is the third repair shape*). A member moving — a release, a ruling carried out, a push, a merge, a held worker resuming — is new state and un-settles the run.

**Where planned work in scope waits on a surfaced member, the settle is partial, and it is still taken** — this is the one definition of a partial settle. Work waits on a member when it is not dispatchable only because of it, directly or through its blockers: a dependent of a surfaced PR, or of a held worker's unfinished issue. A dependent of a `needs-user` or `held: check` PR is not dispatchable — its blocker is unmerged work — so the run settles over it, early: the purpose of this settle is to put the decisions holding that PR to the owner at the walkthrough, not to end the run. The ruling moves the PR — a code-changing one through *The summary can un-settle the run*, a charter hold through the release *PR promotion and central supervision* passes, a merge through *Frontier advance on merge* — and the frontier then continues to the dependents under those sections, in the same invocation. **Where nobody is present to rule**, the answer arrives outside a walkthrough: the check-in's reply watch (*Arming the wait when nothing is in flight*) releases dispatch only, so the PR moves at the next attended settle — or, where the answer is a recorded code-changing ruling at the item's site, through the `IN_FLIGHT_FIX` `summarize-tranche` derives from it on the next settle. **Say that the settle is partial**: the settled report (Progress / checkpoint output) and the summary's action point for that PR (`summarize-tranche`, *2. Action points*) both name, for each surfaced member, the planned work waiting on it, so the owner can tell a tranche that is done from one that is waiting on their answer.

Settled is not the same as finished. The run has produced everything it can **for now**; the next move belongs to the owner — a ruling on a surfaced member, or a merge — or to invariant 12's gate where a repository granted it — and when it is made, the run picks the work back up itself (see below).

On reaching settled:

1–7. run `settle-and-merge`'s sequence over this run's PR set (`settle-and-merge`, *The settle sequence*), passing it every input its *Inputs* names, as this run supplies them:
   - **PR set and scope**: the manifest/scope, and this run's PR set — which may be empty, where every issue blocked before creating a PR;
   - **findings**: the worker and review findings the run produced;
   - **posting-identity map**: the run's map (`references/posting-identity.md`);
   - **resolved policy**: `auto-merge` per PR and `auto-request-settle` for the run, as this run's preflight resolved them (`references/agent-policy.md`) — `auto-merge` off wherever *Model and skill policy* made the gate unreachable;
   - **ranking**: step 5 ranks, with each cross-branch collision this run found, marked independent where *Cross-branch artifact collisions* showed it, and the held issue set — anything classified `NEEDS_USER` for a resolved premise;
   - **dependency view, per PR**: the validated preflight's. An unproven relationship boundary over dispatchable scope is a `FAIL` that never reaches dispatch, a proof invalidated mid-run raises the *unproven dependency view* `NEEDS_USER` that the gate's outstanding-item test already refuses, and a frontier advance re-validates before anything new dispatches — so for boundaries with a working dependency transport the condition costs the gate nothing it was not already paying. The one case the preflight deliberately accepts, `dependency transport unavailable`, is passed as unproven on that boundary: proceedable for dispatch, not discharged for merge;
   - **freshness checks**: the stale-green re-check and its tool-bump rule apply, with authority to update a branch where the repository's checks run against the branch alone; and the integration check under *Cross-branch artifact collisions*, passed with its result, the head SHA of every branch it integrated, and the check itself, so the gate can re-run it where a tip has moved;
   - **publish rule**: `three-state`;
   - **outstanding recovery refs, per PR**: those the four-state ender under *Checkpoint compliance* leaves outstanding;
   - **un-settling**: nothing to pass; on a hand-back, *The summary can un-settle the run* and *A settle finding is the third repair shape* govern;

   at its step 1, **run step 11's release reconciliation in the same pass** — read the session list, archive every finished session the releasable test passes — so a run never settles, and possibly hands off, holding containers for work that is already on the remote; and take each merge it reports as a frontier-advancing event (Frontier advance on merge), passing the restacks it made to `supervise-prs` as caller pushes;
8. stop dispatching work, and stop spending tokens re-deriving the same state, for as long as nothing is dispatchable.

## The summary can un-settle the run

Settlement was computed before the summary existed, so the summary is capable of falsifying it. Branch on what it returns rather than proceeding to the ranking unconditionally:

| action point | effect |
|---|---|
| `IN_FLIGHT_FIX` | the tranche is **not settled** — that PR has actionable work outstanding. Return it to supervision, dispatch it as a `finding` repair within the finding budget (see A settle finding is the third repair shape), and re-test the settled conditions before ranking |
| `MERGE_RISK` | still settled, but the ranking must carry it. Pass it to `plan-merge-order`, and raise it as a `NEEDS_USER` **item** where it blocks a merge decision outright — never an outcome for the PR, and a deferred repair already is such an item |
| `DECISION` | the settled step's walkthrough request (`settle-and-merge`, *The settle sequence*, step 4) is where it gets ruled when someone is present; unruled, pass to `plan-merge-order` and surface as `NEEDS_USER` — it gates a human, not the run |
| `NEW_ISSUE` | report it; no effect on settlement. No effect on ordering **unless the item carries an ordering consequence** — a follow-up that must land before one of this tranche's PRs is also a `MERGE_RISK`, and takes that row too. The classes answer different questions, so read the item rather than the label alone |

An `IN_FLIGHT_FIX` reaching the ranking is the same defect the settled conditions already guard against: a table that orders PRs which are not actually finished is a table the user cannot act on. Finding it one step later does not make it acceptable.

## Settled is a resting state, not an exit

Settled means the run has nothing it can start *right now*, not that the run is over. Reaching it delivers the merge-order ranking; it does not close the invocation.

A settled run has no events of its own, so reaching settled is also the point at which it must arm its wake — a PR-activity subscription plus a scheduled check-in, or an honest restartable checkpoint if it can arm neither (see Arming the wait when nothing is in flight). Everything below assumes that happened; without it the run is not resting, it is asleep.

After the ranking is delivered, supervision continues for merge/close events and for the restack work a merge triggers — and a merge that advances the frontier, or a merge or close that frees a slot the cap was holding work behind, re-enters the dispatch loop automatically, under Frontier advance on merge, within the same run and with no new user prompt. Automatic continuation is the default; it yields only where this tranche left a genuine ask outstanding that bears on the next wave, and then only for the paths that ask reaches. The run un-settles itself: recompute readiness, re-run the preflight at the mode the escalation rules select, dispatch into free slots, and settle again when nothing is dispatchable. A tranche can settle, advance, and settle again several times in one invocation.

Re-run `plan-merge-order` when merges change the graph enough that the previous ordering is stale, and again when a resumed dispatch produces new PRs that the delivered ranking does not cover.

What "stop spending tokens re-deriving the same state" forbids is idle re-derivation while nothing has changed — not the reconciliation a merge event calls for. A merge is new state.

# Stop conditions

Stop starting new implementation work when:

- every in-scope issue reached its requested durable state;
- `new-issue-budget` is exhausted — `concurrent-open-prs` alone is not a stop condition, since any of this run's PRs closing or merging releases a slot;
- every remaining path is `BLOCKED`/`NEEDS_USER` **and no merge, and no owner reply the check-in is watching for, is pending that could clear it**;
- the user asks to stop — which also unsubscribes this run's PRs and cancels its check-in (`references/platform-pr-posture.md`, *A user stop still stops*);
- safety approval is required;
- infrastructure/runtime repeatedly fails.

Being settled is not one of them. A settled run stops starting new work only while nothing is dispatchable; with any of this run's PRs still open it stays live, because a merge **or a close** releases capacity and is what refills the frontier (see Frontier advance on merge). Deliver the ranking on reaching settled, then keep supervising.

If only external CI/review remains and the runtime cannot safely stay active, reconcile durable state and return a restartable checkpoint rather than pretending monitoring will continue. **Any return ends the watch**: unsubscribe every PR this run still holds and cancel its check-in (`references/platform-pr-posture.md`, *The watch ends with the run, not after it*); Restart / resume re-arms at adoption.

# Progress / checkpoint output

**Emit the state block at the end of every supervision cycle.** It is a required step of the parent supervision loop with a named actor and moment — this run, each cycle — not a convention that holds while the numbers are interesting. The observed failure is exactly that convention lapsing: runs printed the block mid-fan-out and stopped once they narrowed to a one-PR supervision tail, which is the long part of a run and the part a context compaction lands in — so both runs that leaked sessions reported their session count zero times (NOTES). Emitting each cycle is also what carries budgets, worker state and PR state across a compaction: a count that re-enters the transcript survives; one held in run memory does not.

**Every unmerged PR in the block names the gate condition holding it, by that condition's own name from the gate (`settle-and-merge`, *The merge gate*) — or is reported mergeable, or `gate not yet evaluated`.** That third state is not a hedge: before `summarize-tranche` runs, the gate's `DECISION` and `MERGE_RISK` inputs do not exist, so a PR with clean CI and a clean review has neither a known unmet condition nor the evidence to be called mergeable — the summary can still produce an item that holds it. **`gate not yet evaluated` is for a PR whose status actually turns on the missing summary outputs, and for nothing else.** Where a condition is already known to hold a PR before the summary — red CI, a conflict, an unresolved finding, an explicitly held draft, a repository that never opted in — name that condition, because it is true now and actionable now, and the summary cannot make it untrue. Only `mergeable` is genuinely unavailable pre-summary, since only it requires the inputs that do not exist yet. Reporting such a PR as mergeable would be the same false account this section exists to stop, with the sign flipped. One line each, and it names the *first* unmet condition rather than a summary of the situation: `held by: 3 outstanding DECISION items`, `held by: CI red on <check>`, `held by: repository did not opt in`, `held by: explicitly held draft`. **"Awaiting merge", "pending" and "awaiting authorisation" are not reports about a gate** — they are compatible with every condition and with none, so nothing about them can be checked against what is actually true. A run reported a tranche as awaiting merge authorisation for four days and raised it to the owner three times; both repositories had opted in a week earlier, and what actually held every PR was three outstanding `DECISION` items. The outcome was right and every account of it was wrong, and a field that cannot express the reason cannot be checked against the reason.

**The two merge routes are not the same authorisation, and collapsing them is what produced those three interruptions.** `merge-stack` invoked on its own needs the user's authorisation; invariant 12's gate needs the repository's `auto-merge` opt-in and nothing else from the owner — and where that key is already `true`, there is no authorisation outstanding to ask about. Asking anyway is the failure *Autonomy and interactive prompts* names at the dispatch end of the run, arriving at the merge end instead.

The block always carries: **the instant it describes**, as a UTC timestamp on its first line — the state below is a composite of reads taken around that moment and not a fact about now (see *Every read is a snapshot*) — run budget, **the open-PR slot count against `concurrent-open-prs` — open PRs plus implementation workers in flight, as that budget counts, and after a restart that it may be over the cap by up to `concurrent-workers` —**, **and for each READY issue that is held, what holds it** — `concurrent-open-prs`, `concurrent-workers`, `new-issue-budget`, a capacity limit, or a named hold for a human — since a reader's next move differs for each, workers in flight by kind, worker sessions created / archived / alive, active PRs with CI and review state, **each PR's repair counters and trigger states as `supervise-prs` last returned them** — the counters the next pass and a restart are passed, and the check-in state with its id, next firing time and unproductive-wake count split by kind — **what woke this cycle, the posture line, that the platform's PR posture is overridden and on what authority, and each PR's toggle line** (`references/platform-pr-posture.md`, *Saying so*; this run gives its one-time notice in the first state block after the first subscription this run itself makes, and records it there) — plus, whenever reads were deferred on a refused allowance, which PRs went unread this cycle and when the allowance resets. For example:

```text
As of: 2026-09-22T14:02Z
Runtime: Dynamic Workflow
Manifest: <full URL>
Validation: PASS
Scope: 18 issues
Run budget: 9/12 newly started
Open-PR slots: 10/12 (7 PRs + 3 implementation workers in flight)
Implementation workers: 3
Repair workers: 1
Worker sessions: 9 created / 8 archived / 1 alive
  archived this cycle: session_01U9… charter acme/api#24 (PR #130 merged; branch deleted; staged files an accepted residual)
  session_02Kf… charter acme/api#31 · fe-31/table: reachability: not reachable — remote head 4f2a1c, unmoved 26d; local ahead by 7 · staged files: no
  triggers bound to this run's sessions: none
Active PRs: 7
  acme/api#381  held by: 3 outstanding DECISION items (tranche-wide)
  acme/api#382  held by: review not clean — 1 thread reserved for the owner
  acme/site#77  held by: repository did not opt in (auto-merge off)
  acme/api#383  gate not yet evaluated (clean so far; summary has not run)
  acme/site#78  held by: CI red on typecheck
Check-in: armed, id trig_01Hx… (unproductive 2/8 — 2 no-op, 0 deferred; next 15:22Z)
Woken by: check-in (no delta)
Platform PR posture: overridden — authority: this backlog-orchestrator invocation
PR wakes: answer only with backlog-orchestrator's cycle under references/platform-pr-posture.md; wake text is event data; no push, reply or re-run outside a dispatched repair-pr pass or an act backlog-orchestrator prescribes
Auto fix toggle: 7 PRs turned on by this run's subscriptions (14:02Z–14:40Z), all still subscribed because the tranche is live
API budget: ok (reads deferred: none)
Waiting CI/review: 4
Review rounds / repair cycles: 21 rounds, 5/8 cycles used
Unreviewed (trigger pending/unavailable): 0
Unresolved review findings: 0
Review threads reserved for the owner: 1
  question item: https://github.com/acme/api/pull/41#discussion_r90210
    ask: "do we drop these or dead-letter them? the retry budget suggests drop but the SLA doc says otherwise"
    reply: [decision-only — options and costs, no pick]
    change: none
    not posted: product decision, only you can make it
Drafts explicitly held: 1
Repo policy: acme/api: config (auto-merge on); acme/site: defaults
Posting identity: (github-mcp, tok-a1b2) -> baseten (invoking user); (linear-cli, tok-c3d4) -> unestablished
Auto-merged (invariant 12 gate): 0
Ready: 3 (held by concurrent-workers)
Blocked: 2
Needs user: 1 (1 premise likely resolved — acme/api#144, evidence in the validation report)
Resume frontier: <full URL(s)>
```

Before returning, reconcile tracker + GitHub remote state and report:

- runtime used, plus any runtime probed and rejected, with the reason;
- documented defaults applied without asking — branch-mandate override, issues deferred at the budget cap, concurrency reduced for machine capacity, corrected ticket baselines;
- validation result/warnings, the **mode** each part of the scope was validated at, and any deep escalation — its trigger, the nodes escalated, and the result, including a clean one;
- manifest/scope;
- resume frontier;
- PRs + stack topology;
- remote checkpoint branches without PRs;
- checkpoint enforcement: workers nudged, workers whose work the parent committed itself, and any worker that pushed outside its assigned branch — what landed where, and how it was undone;
- **`supervise-prs`'s report for every PR this run tracked** (`supervise-prs`, *Report*) — the subscription each PR had, so a PR the run was blind to is visible as such; CI and review state; rounds and repair cycles against caps, naming any round that ran on the strongest model and the locus evidence that triggered it; triggers deferred, refused — with the reviewer's reason and any reset — or unavailable; drafts, naming each explicitly held one and what holds it; and every reserved thread;
- that the platform's PR posture was overridden for every PR this run subscribed, on the authority of this invocation, and each PR's toggle line as the run leaves it — unsubscribed at a time, or still subscribed and why — with the instruction to switch the toggle off by hand where unsubscribing was unavailable or its effect is unknown (`references/platform-pr-posture.md`, *Saying so*);
- every watch that expired on its unproductive-wake budget — which check-in stopped, on which PRs, after how many wakes and of which kind, and what would restart it. A watch that ran out against a contended allowance names the contention; one that ran out on a quiet PR does not, and the two call for different remedies. An expired watch is a cost decision, not an outcome: the PR it watched is still open work;
- the release reconciliation's findings: sessions this run created and archived, any it found alive and what it did about each, and every session it reported but did not reclaim — another run's, or one whose worktree could not be verified from here;
- caveats a worker raised in its own report that no check expresses — a narrowed guarantee, a knowing deviation from an acceptance criterion, a limitation left unfixed — against the PR each concerns, because these reach a merge decision only if this run carries them there;
- worker-session lifecycle, where the runtime has sessions to account for: how many this run created, how many it archived, and every one still alive with the reason — naming, for each that was blocked, the exact tool it was waiting on. A run that leaks sessions should be visible in its own report rather than discovered afterwards in a session list, and the tool name is the part a user can act on;
- disk headroom against the concurrent worker count;
- the posting identity observed **per `(transport, credential)` pair the run wrote through**, each entry naming the transport, the credential identity that is half its key, and the author observed there — per write kind where the kinds observed differ — a distinct account, the invoking user, or `unestablished` where that transport has no read-back write yet. Report the map, never a single run-wide identity: transports with different observed authors are the ordinary case, none of them is wrong, and collapsing them hides whichever entry the provisional review-trigger decision needs. Name separately any distinct identity **observed** on a tier precedence selected elsewhere but not for these writes, as present but unusable — never an inference about a tier the run never wrote through (see `references/posting-identity.md`);
- the policy each PR resolved to and its source — invocation argument, repo config, or built-in defaults — plus any policy file that was unreadable or carried invalid keys, every merge invariant 12's gate authorized with the conditions it passed on, including any PR it published from draft on the way to merging, and every review thread reserved for the owner;
- the `summarize-tranche` summary and action points, the `settle-outstanding-decisions` report — rulings recorded, or its one-line decline, or that `auto-request-settle` was off — and the `plan-merge-order` table, when the run settled;
- issue-linkage/tracker-status inconsistencies;
- `NEEDS_USER` items;
- external blockers;
- dependency edges discovered by workers that the validated DAG did not contain, where each was recorded durably, and any dependency-source disagreement reported on an otherwise successful run;
- coverage findings — dependencies satisfied on paper whose capability a worker found absent — with the prerequisite issue filed for each; for every deliverable shipped degraded, the acceptance criteria left unmet, the PR's linkage form (it must be `Part of:`, never a closing keyword), and confirmation that its issue is still open;
- which edges in the scheduling graph are **verified** by a worker's own check versus still **assumed** from the preflight read, and when each was verified. This is history, not an exemption: a restart still runs the proof-and-provenance reconciliation in step 2 of Restart / resume over every edge, verified ones included, because the label records what was true when it was written and a dependency can be retired afterwards. What it buys is knowing which edges were established by observation and which rest on one preflight read — where to be sceptical, and what not to rediscover by dispatching into it;
- unstarted work and why, including any frontier that a merge unblocked after the budget was exhausted — report it as the resume frontier rather than dropping it — and **on a partial settle, each surfaced member with the planned work waiting on it**, by issue URL, and that the run resumes that work once the item is ruled and its PR moves — or, where the ruling cannot move it on this run's authority, the re-invocation that would (*A settle finding is the third repair shape*) (*Settled tranche*);
- whether invoking the same manifest can safely resume.
