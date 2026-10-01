---
name: backlog-orchestrator
description: Autonomously executes a bounded dependency-linked implementation wave from GitHub Issues, Linear, or another supported tracker. Can fan the implementation phase out onto a Claude Code Dynamic Workflow when the user opts into one, while preserving a validated issue DAG, per-issue model selection, isolated worktrees, durable remote checkpoints, stacked PR topology, centralized PR supervision, bounded repairs, and restart-safe tracker/GitHub state.
---

# Backlog Orchestrator

Execute a prepared implementation wave autonomously.

This file is the contract; the reasoning and incident history behind its rules live in `NOTES.md` beside it, keyed by section. NOTES explains; it never overrides. Four files beside it are part of the contract on their situation, each read only when it arises, and the pointer at each decision point says when: `deep-validation.md` (an escalation trigger fired), `restart-resume.md` (resuming an earlier run of this orchestration), `artifact-collisions.md` (a cross-branch collision, found or expected at dispatch) and `dynamic-workflow.md` (a Dynamic Workflow fan-out). The fields of the state block and the closing report are in `schemas/checkpoint-output.md` beside this file, and bind as this file does. The checkpoint-capture sequence lives in `swarm`, as a tested implementation in that skill's `scripts/checkpoint-capture.sh` with its test suite beside it.

This skill is the **policy and backlog layer**. Claude's runtime may provide the worker scheduling/persistence layer for the bounded implementation fan-out.

## Invocation

Dynamic Workflows can only start from the invoking user's own prompt (containing `ultracode`/"use a workflow" wording, or the session already running with `/effort ultracode`) — this skill cannot switch one on by itself mid-run. To get Dynamic Workflow execution for the implementation fan-out, the user must ask for it explicitly, for example:

```text
use a workflow to run backlog-orchestrator on <root/manifest URL>
```

Without that wording (or `ultracode` effort already active), treat Dynamic Workflows as unavailable for this invocation and use the fallback runtime chain below. Never "detect" or silently opt into a workflow — it is invocation-gated by the platform, not by this skill.

Even with that opt-in, the platform shows its own workflow-launch approval prompt before the run starts. That prompt is a one-time interactive checkpoint at fan-out start, not a break in autonomy — everything from validation through PR creation, supervision and repair proceeds unattended once it is cleared.

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
- `summarize-wave` — read-only short summary and action points for a settled wave;
- `settle-outstanding-decisions` — attended walkthrough of a settled wave's human-only decisions, requested between summary and ranking when `auto-request-settle` is on;
- `plan-merge-order` — read-only review/merge-order ranking for a settled wave;
- `merge-stack` — separately authorized stack merge/restack workflow.

`implement-issue` remains the convenient standalone **single-issue orchestrator**. Do not replace it with this skill for normal one-ticket work.

# Core invariants

1. **Tracker + GitHub remote state are durable truth, and truth moves while you read it.** Conversation state, workflow state and cloud worktrees are caches, not the only source of truth. Other sessions, other tracks and the owner write to the same remote, so anything computed from several reads is a composite of moments that never coexisted — see *Every read is a snapshot*.
2. **Canonical issue identity is the full issue URL.** Short keys/numbers are display helpers only.
3. **A run is bounded.** Never turn one build-order ticket into an open-ended project crawl.
4. **One implementation worker = one issue = one isolated checkout/worktree.**
5. **In-flight implementation is remotely checkpointed.** Significant completed work must not exist only in an ephemeral container. What enforces this differs by runtime: where the parent can reach a worker's checkout it verifies and captures (`swarm`, *Checkpoint compliance*; how a recovery ref ends here is *Checkpoint compliance*, here); where it cannot — normally the remote-session tier — the invariant rests on the worker's own pushes, with the dispatch prompt and the observable remote head as the only levers. Say which of those a run relies on rather than reporting the invariant as satisfied by machinery that was never available.
6. **The model is selected per issue, and Sonnet is the default where the selection does not say otherwise** (see Model and skill policy, which owns the assignment and the escalation ladder). Use the strongest available reasoning model for orchestration when appropriate.
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
- a `NEEDS_USER` **outcome** on a node after the budget governing its failure is exhausted — a CI or finding repair out of cycles, an implementation out of attempts — or one that leaves no dispatchable work at all, the same shape as the `FAIL` case below. **A `NEEDS_USER` item on a review thread is never an interruption**: a question, or a repair deferred because `review-repair-cycles` is spent, is reported in the checkpoint output, holds that PR's merge, and reaches the owner at settle (see `references/review-feedback.md`, *Reserved for the owner*) — the run still has work to do meanwhile. Every other `NEEDS_USER` — a dependency measure the run cannot observe included — is surfaced in the closing output instead of asked mid-run. The decision-shaped items get one sanctioned exception, where the run has nothing left to do meanwhile: the settled step requests `settle-outstanding-decisions` over them when `auto-request-settle` is on (see `settle-and-merge`, *The settle sequence*, step 4), and that skill's own attendance precondition, not this list, decides whether anything is actually asked;
- a `FAIL` validation result leaving no safe independent path;
- a genuine conflict with no documented default, where every available option loses work that cannot be recreated.

Everything else belongs in the checkpoint output.

## Worker dispatch authority

A session may carry standing guidance not to use subagents or the Agent tool unless the user asked for them. Invoking this skill satisfies that guidance: fanning a validated issue set out to isolated one-issue workers is this skill's documented mechanism, so the invocation is the request. Dispatch subagent workers, create worktrees, and start worker sessions without a separate confirmation.

That authority covers worker dispatch only. It is not permission to merge, to widen scope beyond the bounded set, or to work around a platform-owned permission prompt.

# Execution runtime

**`swarm` owns the generic statement of what this section, *Implementation worker contract* and *Parent supervision loop* describe** — runtime detection and the degrade chain, one worker per task in its own worktree off a stated base, model selection by failure visibility, the supervision rules including the no-change preflight, and the worker mechanics: remote session arguments, bounded probing, the countermand, how a report reaches the parent, the releasable test, checkpoint compliance, blocked workers and capacity. These sections hold the PR- and DAG-specific form: stacked branch topology, per-PR repair budgets, draft state, and a frontier that advances off merges. Read the general rule there; where the two appear to disagree, the general rule is the one that was written to be reused.

The orchestration policy must be independent of the mechanism used to run workers.

## Preferred runtime: Claude Code Dynamic Workflows

A Dynamic Workflow is a JavaScript orchestration script that fans plain subagents out (up to 16 concurrent, capped at 1000 total) in the background and returns only their final results to the caller — the shape of the **bounded implementation fan-out** this skill dispatches.

When the user has opted into a workflow for this invocation (see Invocation), use it **only for the implementation fan-out**. **Before writing the workflow script, read `dynamic-workflow.md` (beside this file)**: it holds what each worker's prompt must encode, where the checkpoint push goes, and what the workflow may not do to the backlog or to state. **Size the fan-out to the `concurrent-open-prs` headroom at launch, never to the whole authorized set**: a running workflow cannot be reached or paused once the cap fills, so the cap bounds nothing that runs inside it.

A Dynamic Workflow does **not** persist across a Claude Code session exiting (an interrupted one restarts fresh next session), accepts no external input mid-run, and cannot be woken later by a CI/webhook event. So never use a Dynamic Workflow for **long-lived PR/CI/review supervision**: it always stays with this skill's parent-level supervision loop (PR promotion and central supervision), whether or not the implementation fan-out ran inside a workflow.

## Fallback runtimes

When a Dynamic Workflow was not requested for this invocation, or cannot honor the required DAG/worker constraints, degrade through the remaining tiers of Runtime selection below: remote worker sessions, then ordinary isolated subagents with the parent supervision loop defined here, then serialized execution when safe isolation cannot be provided. Agent-team primitives may substitute for tier 2 where that experimental feature is confirmed enabled.

Degrade silently and get on with the run. Not requesting a Dynamic Workflow is neither a reason to abandon the orchestration nor a reason to ask the user which tier to use.

## Runtime selection

Choose the runtime yourself at startup, from what is actually callable in this session. Never present a runtime menu, and never offer a runtime whose tools are absent here.

Determine availability in preference order:

1. **Dynamic Workflow** — only if this invocation opted in (see Invocation). Not autodetectable; without the opt-in wording or `ultracode` effort it is unavailable, and that is not a question for the user.
2. **Remote worker sessions** — available when the session exposes a Claude Code Remote `create_session` tool. A cloud session exposes it whichever surface launched it: `origin` records the launch surface (`desktop_app`, web, mobile), `environment_kind` records where the session actually runs, and neither gates worker creation. Confirm with one cheap read (`list_environments` or `get_session`) rather than a speculative create.
3. **Subagents** — available when the session exposes the Agent tool. The normal runtime for a local session, and the normal fallback everywhere else.
4. **Serialized execution in this session** — always available; correct when safe isolation cannot be provided.

**That order trades invariant 5's enforcement for capacity and resilience.** Tier 2 buys a container per worker (see `swarm`, *Concurrency*), a worker that outlives this session's compaction, and per-container tool isolation; but the parent cannot reach a tier-2 worker's checkout, so the parent-side verification `swarm`, *Checkpoint compliance*, relies on is unavailable there, while on tier 3 it works. Report which tier was selected and, on tier 2, that invariant 5 rests on the worker's own pushes. Where an owner would rather have the guarantee than the capacity, tier 3 is the correct selection, and nothing here forbids it.

**This run's session-name prefix is `bo`** — `bo/<run-id>: <issue>`, for example
`bo/a41f: api#348`. The convention and the reason the name is never what a sweep
matches on are `swarm`, *Runtime: take what is there, and say which*.

`swarm`, *Remote worker session arguments*, owns the rest of what a worker session is created with and checked against — the explicit source, the checkout verification, ending a failed start, and the two capabilities, checkout reachability and the message channel, that the rest of this document divides on. Apply it from there.

### Review and repair sessions

Where a repository's review or repair is performed by dispatched sessions rather than by a trigger comment, those sessions are workers like any other: they carry the countermand (`swarm`, *Countermanding the worker's ambient supervision posture*), they are released by the releasable test (`swarm`, *Releasing a worker*) and reconciled by step 11, and they carry the report requirement (`swarm`, *How a worker's report actually reaches you*). Two shapes, and the difference between them is what the release test reads:

- **a review session** is dispatched per PR head with `source_revision` set to the PR branch and **no `outcome_branch`**: it reads, posts one PR review — a body carrying the attribution, plus inline comments each rooting a thread — or one ranked comment, per the repository's convention, and pushes nothing. That review is the one carve-out from the run never rooting a thread (`references/review-feedback.md`, *The thread-root test*): record the ids of the review and its comments from the session's report. **This run dispatches it**: the convention is passed to `supervise-prs` as performed by the `caller`, and each round that skill reports owed, with its head, is a review session this run dispatches;
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

The detection above establishes what exists; this establishes which one to use. For every tracker/forge read and write, in order:

1. a first-class MCP tool for that operation, where one exists;
2. an authenticated CLI (`gh`, `linear`, equivalent) when running locally under the user's own credential;
3. raw HTTP against the API, only where neither of the above exposes the operation at all.

Raw HTTP is a last resort, not a default. Reaching for it is a decision you record — which operation, and why no higher tier exposes it — never a habit.

**A higher tier that cannot ask incrementally where a lower one can** — no `since` bound and no conditional request, where a lower tier offers one (`references/watch-and-read.md`, *Allowances belong to the credential*) — also counts as "no higher tier exposes it". Record that descent like any other.

One operation is carved out of tier 3 entirely: a GitHub dependency-edge read over raw HTTP returns same-repository edges only, dropping cross-repository ones with no error, so where the scope spans repositories it is not the fallback for a missing higher tier — the result is the validator's `dependency transport unavailable` classification, with prose as the only source (see `validate-backlog`, *GitHub dependency reads depend on where you are running*). Falling back anyway turns that proceedable warning into an unproven boundary no proof can clear.

Precedence lowers the odds of a partial view; it does not remove the need to check for one. A first-class tool or a CLI can run on a directly scoped credential and under-report as quietly as a relayed one — the hazard is the **scope of the credential**, not the shape of the transport. So treat every relationship read as **provisional until validated below, whichever tier produced it**, and spend the extra scepticism on raw HTTP rather than reserving it for raw HTTP.

## Proving a transport can see the graph

Before a run depends on **relationship data** — dependency edges, hierarchy, cross-repository links, anything a server can legitimately return in part — prove the chosen transport can see it. A relayed, proxied, scoped, or short-lived credential returns a truthful-looking partial result — 200, no error, fewer rows — and any transport can do it. The shared model is stated canonically in `validate-backlog` (*Transport visibility*), and this skill's runs meet it through that preflight; these are the rules the rest of this document depends on:

- **Proof is a known-true case** — an edge this run just wrote, or one the user confirmed: its answer does not depend on any transport being trustworthy.
- **A second read corroborates at best, never proves.** Independence is a property of the credential, not the transport — `gh` and raw HTTP both reading `GITHUB_TOKEN` are one observation — and even two credentials can share insufficient scopes, a repository boundary, or a relationship transport. Where no known-true case is available, **that is the finding**: report the boundary as unproven rather than promoting agreement into a proof.
- **Enumerating the bounded scope is itself one of these reads.** A scope obtained from a possibly-partial read cannot bound its own validation. Draw the boundary list from something independent of the enumeration: the issue set the user supplied, the manifest's own prose listing of its children, or a second enumeration — where **a differing count is the finding, and a matching count proves nothing** unless one of the enumerations had proven visibility.
- **The control must match the shape of what the run consumes.** Cover each scope boundary the graph actually crosses, and where the graph spans repositories, at least one control must itself be a cross-repository edge.
- **Record validation per credential, transport and boundary**, never per transport alone ("MCP works" is not a finding; "MCP, as this account, resolves edges from A into B" is), with a non-secret identity of the credential beside the proof (the authenticated account and its scopes, an expiry, a fingerprint — never the credential itself).
- **Revalidate whenever that identity changes, whenever a transport reauthenticates, and always after a restart. An authorization error invalidates every proof bound to that credential, across every transport that uses it** — grants narrow server-side, so a `gh` 403 says nothing about `gh` and everything about the token.
- **Absence observed through an unvalidated transport is not evidence of absence** (`references/absence-is-not-a-verdict.md`, of which this is the transport case). Report it as "not visible via `<transport>`", never as "does not exist".

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
— that path, not the repository's `rules/` source, which does not exist on an
installed run. It covers length, what a body is for, what must never be in it,
the attribution footer and its approval test, the precedence of required
contents over brevity, and when a PR body may be edited after creation — this
run edits none itself; `settle-and-merge` and `merge-stack` apply it.

`references/posting-identity.md` decides which **author** a write carries; that
rule decides **what the write looks like** once it is authored; and
`references/establish-do-not-assume.md`, *You are about to assert it*, decides
what may be **claimed** in one — about existing code and about current state,
this run's own state block and checkpoint included. Every skill that applies it
carries a generated copy at that path; do not restate part of it here.

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

Also inspect descriptions/comments for explicit dependency language, because textual dependencies may not yet have been normalized.

## Completion semantics

### GitHub

A correctly linked implementation PR uses a full-URL GitHub closing relationship. Treat issue closed + implementation PR merged as canonical `DONE` — **provided that PR implemented the whole issue.** A PR carrying a coverage finding is linked with `Part of:` rather than a closing keyword precisely so this test cannot be satisfied by it (see `create-pr`), and an issue whose only merged implementation shipped acceptance criteria stubbed, disabled or omitted is not `DONE` however its tracker reads. If a correctly linked merged PR failed to auto-close due to unusual stack/base behavior, explicitly close only after verifying that exact PR implemented the issue — the same verification, which fails for a partial implementation for the same reason.

Closing state is evidence of completion, not a definition of it. Where the two disagree — an issue closed by a merge that did not finish it — the work decides, and the checkpoint reports the discrepancy rather than adopting the tracker's answer.

### Linear

A PR must retain the full Linear issue URL and repository/workspace linking convention. Treat configured terminal Linear status + linked merged implementation PR as canonical `DONE`, subject to the same completeness proviso: a coverage finding means the issue is not done, whatever status the workspace automation moved it to. Do not manually complete Linear issues unless workspace policy explicitly requires that fallback.

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

Projects are discovery surfaces, not execution graphs. Combine FE/BE/shared projects into one candidate DAG. Prefer an identifiable selected build-order/root issue before dispatching broad project work.

# Mandatory validation preflight

Before dispatching any **new** implementation worker, invoke `validate-backlog` on the entire bounded scope — `shallow` by default, deeper over the nodes the escalation rules below reach.

**The run's first preflight** is also where per-repository policy is read — each in-scope repository's `.claude/agent-policy.json`, per `references/agent-policy.md`, which owns the schema, resolution, and failure rules. **Later preflights do not re-read it, and reuse that snapshot.** A re-run after a frontier advance revalidates the *graph*, which the merge changed; policy is owner-authored configuration that can authorize merges, and re-reading it there would let a mid-run merge adopt a config the run's own workers wrote — which `references/agent-policy.md`, *Resolution*, forbids by fixing the read to the repository state the run started from. A restart is a new run and takes a fresh snapshot. **When this invocation resumes an earlier run of this orchestration — the same manifest re-invoked after an interruption or session exit, or a checkpoint a previous run returned — read `restart-resume.md` (beside this file) before the preflight, and follow its steps in order.** Its step 2 is this preflight.

Use the validator's normalized DAG as the scheduling graph. Do not let the execution runtime independently invent a competing decomposition. That prohibition is about re-planning, not evidence: a worker reporting a blocker it verified against its own issue is correcting the graph from a position the validator did not have (see Outcomes). Accept an edge a worker verified; reject a runtime's attempt to reorder or re-scope the backlog.

**One validator warning is expected rather than exceptional, and must not be treated as a stop.** `dependency transport unavailable` says the probe found no dependency read on this run's transport — GitHub in a container without an authenticated `gh`, today; the same tracker elsewhere may not be in this class at all. It is not a boundary you can prove later, so holding paths for it would halt every GitHub backlog permanently. Dispatch may proceed, on three conditions: record it on the run's state; carry it into **every** dispatch prompt, so no worker reports a false visibility disagreement or waits for a proof that cannot exist; and state it wherever this run reports readiness, since a READY computed from prose alone is a narrower claim than one computed from a corroborated graph.

Results:

- `PASS` -> proceed;
- a node carrying `PREMISE_LIKELY_RESOLVED` -> **never dispatch it**, whatever the result value alongside it: its cited defect is absent on another repository's current default branch with the replacement positively present. It is **not** `DONE` — that needs completion evidence this pass does not have — so classify it `NEEDS_USER`, surfaced to the owner with the evidence and the revision it was read at, and it keeps its edges. `CITATION_UNVERIFIED` is a warning and changes nothing about dispatch;
- `PASS_WITH_WARNINGS` -> proceed only where warnings do not make ordering unsafe;
- `FAIL` -> stop affected paths; continue only validator-confirmed independent safe branches.

One warning is never proceedable at any level: **unproven relationship visibility over dispatchable scope.** A current validator returns it as `FAIL`; treat it as blocking wherever it arrives, including from an older validator or another tool. Every other warning can be weighed because you can see what it is about; this one asks you to weigh what you cannot see, so "it probably does not affect ordering" is not a judgement available to you.

**The one exception is `dependency transport unavailable`, above** — where no transport in this environment exposes a dependency read, you know exactly what you cannot see, uniformly, for every issue, so it is not the invisible-weight case. Do not let the general rule swallow it.

Verify empirically any baseline a ticket tells workers to diff against — "~40 pre-existing type errors", "these tests already fail" — before it goes into a dispatch prompt; a wrong baseline hides genuinely new failures. Measure it at the parent level, keyed by **repository, base revision, and check**, never one number broadcast across the run: workers on stacked bases or in different repos do not share a baseline. Measure once per distinct base, pass each worker only its own, and correct the ticket's claim in the checkpoint output.

Run repo-relative checks from the repo root; a `cd` partway through a validation sweep silently invalidates ticket paths.

Do not automatically mutate dependency metadata. GitHub normalization is handled separately by `normalize-github-dependencies` when requested.

`validate-backlog deep` is not run by default, because it can consume materially more model/code-reading budget. It remains available on request — and it is entered **automatically**, without asking, under the triggers below.

## Escalating to deep validation

Shallow mode reads declared dependency metadata and issue text. It reads code in exactly one place — an issue's citations into *another* repository (`validate-backlog` owns that carve-out) — so it can establish that an edge is *satisfied* and nothing about whether the deliverable behind it covers what the consumer needs. Escalate from shallow to deep **automatically** — a documented default applied and reported, not a question for the user — when the bounded scope shows any of:

- **a cross-repository consumer edge** — an in-scope issue in one repository depends on an issue in another. This is the primary trigger; a frontend consuming a backend built in an earlier wave is the canonical case, and that wave having merged is what makes shallow mode confident and wrong;
- **an issue whose text hedges about its inputs** — "may require", "additional providers may be needed", "assuming X exists" — or an acceptance criterion naming a capability no in-scope issue delivers;
- **a dependency satisfied by an issue that closed in an earlier wave**, where nothing in this run verified what that issue actually exposes.

**A single-repository wave with no hedged inputs does not escalate.** Escalation answers a trigger and does not become the new baseline.

**When any trigger fires, read `deep-validation.md` (beside this file) before running the escalated preflight** — the first preflight, a restart's and a frontier advance's alike. It holds how the escalation is scoped, how its results are handled at either mode, what happens when deep mode is unavailable, why a coverage gap is not a visibility failure, and what the checkpoint reports.

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

These are the built-in defaults. An invocation argument and the repository's policy file override them by the precedence `references/agent-policy.md`, *Precedence*, states — including the keys it lists that an invocation can switch off but never on.

Dynamic Workflows do not override these limits.

**The two budgets bound different things and both apply.** `concurrent-open-prs` is **flow control**: how many of this run's PRs are open at one time — reviewer load, merge-order complexity, conflict surface. `new-issue-budget` is the **spend ceiling**: how much work one invocation is authorized to pay for. Never use cumulative starts as a proxy for how many PRs are open.

**`concurrent-open-prs` is a count of what is open, not a ledger of what was spent:**

- **this run's PRs are every PR this run tracks, created or adopted** — a restart that adopts twelve open PRs holds twelve slots;
- **an implementation worker in flight holds a slot too, from dispatch until its PR exists, it returns without one, or lost-worker recovery declares it lost.** Repair workers hold none; they open nothing;
- a slot is held while a PR of this run's is open and released the moment it is not — **merged, or closed unmerged; the reason is irrelevant to flow control**. Any pass, a restarted one included, recomputes it by counting this run's open PRs, so nothing about it can be lost to a checkpoint or laundered by a restart, and nothing is deferred to settle;
- at restart both halves are re-derived from durable truth, never from run state — adopted PRs at step 6, and in flight only what this parent dispatches. An adopted branch holds a slot only once a worker resumes it, and **resuming an adopted branch is a dispatch like any other** (`restart-resume.md`, step 9, where it is decided);
- **what a restart cannot see is a worker a previous parent left running**: recovery reads no runtime state, and that worker is another parent's by provenance (the supervision loop's step 11), so a restart can open up to `concurrent-workers` over the cap until those workers' PRs appear, and may resume an adopted branch with no PR beside a worker still on it. Report the restart as possibly over the cap by that bound;
- **what stops a run dispatching forever is `new-issue-budget`**, which no merge and no close ever restores, so flow control needs no second mechanism to terminate.

When the bounded scope exceeds `new-issue-budget`, do not ask which issues to drop. Start the first `new-issue-budget` issues in scheduling order — DAG readiness first, then how much downstream work each unblocks — and defer the rest, naming the deferred issues in the checkpoint output so the next invocation adopts them. A user who wants a different cap says so in the invocation; a `0` there is treated as the config rule treats one (`references/agent-policy.md`, *Fail-closed handling*).

**When `new-issue-budget` is reached**, stop starting new issues and keep supervising through to settle — the PRs already open still need their reviews, ranking and gated merges — and return a checkpoint only where *Stop conditions* says the runtime cannot stay active. **When `concurrent-open-prs` is reached, do not return** unless *Stop conditions* says the runtime cannot stay active: pause dispatch, keep supervising, and resume on the next release (see *Frontier advance on merge*, step 5); it clears within the invocation as PRs close or merge. Say which of the two is holding in the checkpoint. Restarting does not count already-adopted work as newly started.

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
  "auto-resolve-comments": false,
  "auto-merge": false
}
```

The values shown are the built-in defaults. If an option of this skill's is configurable at all, it is configurable in that file.

Keys scope to different objects, and each resolves from the repository that owns its object (`references/agent-policy.md`, *Resolution*). This skill's keys:

| keys | scope | resolved from |
| --- | --- | --- |
| `ci-repair-cycles`, `review-repair-cycles`, `finding-repair-cycles`, `repair-model-escalations`, `auto-resolve-comments`, `auto-merge` | per PR | the PR's repository |
| `implementation-attempts`, `model-escalations`, `lost-worker-redispatches` | per issue | the issue's repository |
| `concurrent-workers`, `concurrent-open-prs`, `new-issue-budget`, `auto-request-settle` | per run | the manifest's repository; an explicit issue set contained in one repository uses that repository; a multi-repo set with no manifest uses the built-ins |

### Review feedback

**Stated in full in `references/review-feedback.md`.** What the run may auto-fix (the kind test), the thread-root test, the rule that the run never roots a review thread and its dispatched-review-session carve-out, the reservation of a `NEEDS_USER` thread for the owner, and which threads are unhandled all live there; `supervise-prs` applies them to this run's PRs, and this skill reports and gates on the reserved threads it returns.

# Model and skill policy

The orchestration/lead context may use the strongest available reasoning model.

**Select a model per issue, and select it before dispatch.** `swarm`, *Model: the caller chooses, by how failure shows*, owns the tier, chosen on failure visibility rather than task size. Apply it from there; do not restate it here. Never accidentally inherit the lead's model, and where a runtime has no per-worker model selection, every worker runs whatever it gives.

**Sonnet is this skill's default**, and it is where that skill's mid tier lands for implementation and repair work.

Deciding in advance covers the **confidently wrong** worker — a green PR that fixes the one site its ticket named where the defect was restated at three, or a worker doing exactly what a ticket got wrong — which the ladder below cannot catch, because no escalation rule that keys on failure ever sees one.

An implementation retry escalates by `swarm`, *Model*'s evidence rule, never on exhaustion, at most `model-escalations` times per issue. **The ladder is a floor under the selection above, not the primary mechanism.**

**A repair round's model is `supervise-prs`'s to choose** (*Repair dispatch*): it escalates on evidence, not on exhaustion, and an escalated round still consumes its cycle.

Implementation workers require `implement-issue-core` and `create-pr` — and `review-docs` wherever a target repository documents the documentation-review routing, since `create-pr` invokes it there and a worker without it would silently fall back to the ordinary trigger. `supervise-prs` invokes it on a re-trigger or an adoption trigger under that routing, so the requirement holds for the run as well as the worker.
PR supervision requires `supervise-prs`, and the `repair-pr` and `resolve-pr-comment` it composes.
The parent layer requires `swarm` for dispatch, release, capture and blocked or lost workers — without it nothing is dispatched — `validate-backlog` at preflight, and `settle-and-merge` when the run settles, with the skills it composes — `summarize-wave`, `settle-outstanding-decisions` and `plan-merge-order`, in that order, the middle one only while `auto-request-settle` is on (`settle-and-merge`, *Composed skills*). It also requires `merge-stack` wherever any repository's resolved `auto-merge` leaves invariant 12's gate reachable — checked at the run's first preflight, where policy is read, rather than discovered at the gate, exactly as `implement-issue` checks it for its one PR: the stack rules require that skill for any merge or restack.

Where `merge-stack` is unavailable with the gate reachable, the parent does not stop the wave the way a one-issue run returns `BLOCKED`, and does not improvise a raw merge either. Apply the documented default: the gate is unreachable for this run — the narrowing direction an invocation is always permitted — reported at the preflight and again wherever the gate would have been evaluated, with a closing `NEEDS_USER` naming the missing skill so the owner can install it or keep merging themselves. A parent-required settle skill that is unavailable degrades the same way, never by improvisation: that step's outputs are absent and reported, and a gate whose summary inputs never existed stays shut (see `settle-and-merge`, *Merge behavior*).

Workers must inherit/preload the active installed skills. A **worker** whose required skill is unavailable returns `BLOCKED` rather than improvising a replacement workflow. That rule is the worker's alone: the parent's required skills are the explicit exception, and degrade as the paragraph above has it — the step's outputs absent and reported, the gate unreachable where `merge-stack` is the one missing — never by stopping the wave and never by improvisation.

# Durable remote state and restart

**When this invocation resumes an earlier run of this orchestration — the same manifest re-invoked after an interruption or session exit, or a checkpoint a previous run returned — read `restart-resume.md` (beside this file) before the preflight, and follow its steps in order.**

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

**An outstanding recovery ref overrides all of it, completion evidence included.** Enumerate the recovery refs matching an issue's branch (named under `swarm`, *Checkpoint compliance*; ended under Checkpoint compliance, here) **before** classifying it: an issue with a ref outstanding against it is never `DONE`, whatever items 1–5 say. This is the durable half of that rule — the `NEEDS_USER` a run raises for it lives in run state, a cache by invariant 1, so without this check a restart re-derives `DONE` from the merge and drops the only copy of that work.

## Restart / resume

**When this invocation resumes an earlier run of this orchestration — the same manifest re-invoked after an interruption or session exit, or a checkpoint a previous run returned — read `restart-resume.md` (beside this file) before the preflight, and follow its steps in order.**

A fresh orchestration session must be able to recover from tracker + GitHub remote state alone.

"Latest unclosed ticket" means the earliest remaining unfinished point in established build order, not the numerically newest issue. Parallel groups may have multiple resume-frontier nodes.

## Branch discoverability

Follow repository branch conventions. Where permitted, include the issue key/number (`123-...`, `FEP-195-...`) to improve recovery. Never violate documented naming rules solely for this.

If an orphan remote branch cannot be safely mapped to an issue, inspect commit/diff/tracker development metadata. If still ambiguous -> `NEEDS_USER`.

## Session branch mandates

A cloud/remote session is usually created with one mandated outcome branch (`claude/<slug>-<suffix>`), injected as session-level instructions to land all work there and push nowhere else. It is chosen by the surface that created the session, applies per session rather than per repo, and cannot be removed from inside the session. Read its current value from the session context (`outcomes[].git_repository.git_info.branches`) rather than inferring it.

It is incompatible with the per-issue stacked topology below. Resolve that by default, without asking:

- **remote worker sessions** — give each worker session its own `outcome_branch`, set to that issue's calculated branch, so each worker's own session authorizes exactly the branch it needs and the parent, which dispatches rather than pushing implementation code, keeps its own. Prefer this whenever the runtime supports it;
- **shared-session workers (subagents, serialized)** — per-issue branches, overriding the mandate on the invocation's own authority (an n-issue wave is a request for n branches): name every branch used in the checkpoint output, and stop if the user says the mandate is externally imposed.

Ask only where the default would lose work: the mandated branch already carries unmerged commits, or an open PR overlapping this scope. A mandated branch holding no commits of its own is not a conflict.

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
6. compose the dispatch prompt so it carries every default the worker skills already own. **A design ruling this run writes into it states the ruling and links the record of it, and names the chosen shape's failure paths** — what persists if a later step fails, what a retry does — because the worker implements a ruling without re-deriving it, so nobody else is positioned to check them; the worker records it on the PR with the rest of its choices (step 8);
7. state branch protection explicitly: the worker pushes **only** to its assigned branch, never to the repository's default branch or to any branch it was not assigned — including to fix or revert something it just broke. A worker convinced a change must land on the default branch directly stops and reports instead of pushing it. The branch assignment does not imply any of this;
8. countermand interactive questions explicitly, and state the substitute. The worker never calls `AskUserQuestion` or otherwise stops to put a question to a human, and never waits for a reply or a confirmation either. Nobody is there to answer an unattended worker's prompts — the parent can surface one (`swarm`, *Blocked workers*) but never answer it — so the call stops the worker until a human happens to look. Where a worker holding a genuine open question puts it depends on whether its own skill already owns that stop:
   - `implement-issue-core` returns `BLOCKED`/`BLOCKED_EXTERNAL`/`NEEDS_USER` rather than guessing when scope is materially underspecified, a supplied base is invalid, a prerequisite cannot be observed, or a product decision needs approval; there the worker returns and documents that outcome. **The substitute never licenses implementing past a stop a worker skill prescribes** — a guess there produces a PR built against a missing dependency or invented product intent;
   - for every other open question — the ordinary judgement calls a task leaves open — it picks the most defensible option, implements that, and records the question, the choice, and the reasoning on the PR, where a human can overturn the call in review. **Where the choice is of a multi-step shape, it records its failure paths with it**: what persists if a later step fails, what a retry does, and whether the property that won the choice survives both.

   The prohibition on asking is absolute in both cases; what differs is whether the worker proceeds or returns. Where this countermand goes is decided with the others (see `swarm`, *Countermanding the worker's ambient supervision posture*);
9. include **the dependency context used to judge this issue READY** — the blockers considered, how each was resolved, which transport and credential produced that view, and **the provenance of each edge**: your own native read, or a blocker you established from a previous worker's evidence and recorded outside native metadata. The worker compares its native read against yours, and an edge you deliberately kept out of native metadata is one its native read is supposed to lack; unmarked, it comes back as a visibility disagreement against your own corrections. **Mark the context as your complete READY dependency set**, because it is: unmarked context is treated as a targeted answer whose omissions mean nothing, so an edge you never saw would come back unreported. State too whether the read behind it had **proven visibility** for the boundaries this issue's blockers could cross; marked complete, that is what makes the worker's own silent read meaningful rather than three sources collapsing to one unproven native read. You will normally have the proof, since an unproven dispatchable boundary is a preflight `FAIL`; where you are dispatching without it, say so, so the worker can stop instead of building against it;
10. include **authorization membership**: the bounded authorized set, or a per-blocker flag for whether each is inside it. Only you know this, and the worker's block outcome turns on it — without it, an external-looking prerequisite you did authorize comes back as an out-of-scope wait and you skip the frontier re-derivation it needed. A worker given nothing defaults to the stronger outcome. And where a sibling branch may claim the same migration number, that its number is provisional — **read `artifact-collisions.md` before this dispatch wherever more than one open branch targeting the base may generate a migration** (*Cross-branch artifact collisions*);
11. include, on any runtime where a worker's return value does not reach this run, the requirement that it **record the judgment part of its result on its PR before returning** — not on the issue, and not the run state, which the session record and the branch already carry; see `swarm`, *How a worker's report actually reaches you*. **Never enumerate what the report contains; state it as a subtraction.** The report is `implement-issue-core`'s entire Output contract *minus* what this run can already read for itself — the branch, the PR, and the session record's `status_bucket`, `pending_action`, `task_summary` and `post_turn_summary` — and minus the gate report, which is never posted (`references/authored-write-form.md`). Everything else in that contract is judgment, which has no other carrier. **The one fact it adds back is the head commit the worker pushed** — or that it pushed nothing, and the head it found (`swarm`, *How a worker's report actually reaches you*, says why).

    Any terminal outcome reached before a PR exists writes nothing and simply returns — investigating it, and recording anything that comes of it, is this run's job, not the worker's;
12. dispatch the worker with `implement-issue-core`, on the model selected for this issue (see Model and skill policy). **Where the fan-out runs as a Dynamic Workflow, read `dynamic-workflow.md` before writing its script**, and size it to the `concurrent-open-prs` headroom at launch (*Preferred runtime: Claude Code Dynamic Workflows*).

**A dispatch prompt that enumerates a required process is followed literally**: a default left out of it is a default skipped, and the worker will accurately report that the task never asked for it. The same literalism decides what the worker does with instructions this run did not write (see `swarm`, *Countermanding the worker's ambient supervision posture*). So every dispatched prompt must carry each of the following.

- **The automated review trigger instruction** — the worker's `create-pr` issues it under `references/review-trigger.md`, so do not restate the rule here — unless this run explicitly defers review. Deferral is a conscious choice recorded in run state, naming what review is owed and on which PRs; never an omission. **Record it as the per-PR `review trigger` value `deferred`** — that field is what `supervise-prs`, *Adopt*, reads, and a deferral left at `pending` is issued there as an unfinished trigger.
- **The pre-PR gate, derived once per repository and written out in full.** The parent derives it at preflight as `implement-issue-core`, *Final local verification* defines — the base branch's required status checks, mapped to the commands that produce them, with its fallback and its `not locally runnable` outcome; that skill owns the derivation — and puts the resulting set in the prompt, with each entry's outcome vocabulary and where the set came from. Not a path to it, and not a pointer to `AGENTS.md`, which describes the gate and drifts from it (`swarm`, *Isolation*, on why a path is worse than useless here). Deriving it once also stops two workers disagreeing about what the gate is.
- **How a worker settles a checkout against an API response.** Both are observations with an age — `origin/main` is as old as its last fetch, which on a container tier can be when the container was built, and a held response is as old as when it was issued. Where the two disagree about something the worker is about to act on, it re-reads the forge at that moment and refreshes the checkout to match (see *Every read is a snapshot*).
- **The outbound claim check, alongside the write-form rule** (`references/establish-do-not-assume.md`, *You are about to assert it*). A worker authors the writes this run is most likely to be judged by — its PR body, its report comment, its commit messages — and constraining only this orchestrator's own writes leaves every remembered claim a worker states about the codebase, or about the state of what it touched (*pushed* and *resolved* above all), unchecked.
- **The run's whole posting-identity map** — every (transport, credential) entry, not one selected pair — plus the instruction to read the worker's own first authored write back and report what it observed (see `references/posting-identity.md`). The worker's `create-pr` may need an agent-authored entry to create the PR and an invoking-user entry for the author-sensitive review trigger, so selecting one either gives the PR the wrong author or leaves a valid trigger path unavailable, and the worker cannot recover what it was not sent. The worker's report is itself an authored write, normally a PR comment: a prompt requiring the report while omitting the identity to report under gets it posted as the invoking user. A distinct identity observed at `create-pr` does not reach that write on its own.
- **The authored-write-form rule** (see Authored write form) — the rule, not a paraphrase of it: brevity, no list of checks in a body or comment, bare commit SHAs, the no-wrap constraint on forge fields, the footer **with its approval test**, the required-contents precedence, and the trigger comment's exemption. A worker carrying "sign every write" instead of the test will footer a body a person edited; one carrying only "sign unattended writes" will decide for itself what counts as attended. A dispatched worker's own writes answer No to the test — nobody reads them — so in practice its report and its PR body are footered, and the test is still what it carries, because the worker is what discovers whether anyone approved a given text. **Carry with it that the report's contents are required in full** — the judgment step 11's subtraction defines — so brevity governs how the worker writes each item and never whether it writes one. The footer goes at the end.

**A returned PR whose gate report is missing a derived check is rejected, not accepted and watched.** The gate report, in the worker's returned result (`implement-issue-core`, *Output*), is its report that it ran what it was given, and an incomplete one is the cheapest moment to catch a skipped step. A worker's claim that the gates passed is separate and is not evidence: the report says which ran, CI on the pushed head says whether they passed. Where the worker's return does not reach this run (step 11), there is no gate report to read, and CI on the pushed head is the whole record.

Issuing the review trigger is not the end of it: confirming it took effect, at adoption and after every re-trigger, and reading every PR's CI and review verdicts from then on, are `supervise-prs`'s (*Adopt*, *Review trigger*).

This generalizes past review triggers. When the platform offers several ways to perform the same write, prefer its first-class integration tooling over raw transport: attribution, permissions, and downstream automation can all differ between them, invisibly until a write is made and read back. Where identity matters to a workflow, verify it by inspecting an object the run actually created and reading its author — never by asking the credential who it is, which can answer differently from what its writes carry.

Under Dynamic Workflows, provide these constraints to every workflow worker explicitly. Do not let a worker select another backlog ticket when it finishes.

## Shared environment

Filesystem isolation is necessary but not sufficient. Workers with private checkouts still contend over shared mutable resources — a shared backing service instance, a fixed port, a shared cache or state directory, one set of credentials, a single external sandbox account.

At startup, enumerate the shared mutable resources workers in this run will contend for. That inventory is repository- and environment-specific: take it from repository configuration (`CLAUDE.md`/`AGENTS.md`, the session startup hook, the environment manifest), never from assumption. If a rule cannot be expressed without naming a concrete technology, it belongs in that configuration, not here.

For each enumerated resource, either give every worker its own namespace/instance, or serialize access to it. If neither is possible, serialize the affected workers.

Pass the resolved access details explicitly in each dispatch prompt so no worker has to guess them. A worker that guesses wrong reports failures that are not real.

**Carry the environment-hypothesis rule in every dispatch prompt** — `implement-issue-core`, *Final local verification*, states it and this run does not restate it. A worker inherits none of the repository's own context about a service that dies mid-session.

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
           and repair only through a `repair-pr` pass `supervise-prs` dispatches
```

A worker never supervises its own PR and is never resumed to repair it — only a dispatched `repair-pr` pass repairs (`references/platform-pr-posture.md`, *The override*) — and a Dynamic Workflow never supervises anything: it returns its fan-out results and supervision is the parent's from that moment (see Parent supervision loop).

**What this run passes `supervise-prs`:**

- **PR set**: every PR this run tracks, with its canonical issue URL;
- **budgets**: `ci-repair-cycles`, `review-repair-cycles`, `finding-repair-cycles` and `repair-model-escalations` per PR, as this run's preflight resolved them (*Policy keys and defaults*), with their source — and `auto-resolve-comments` per PR, the same way;
- **counters**: 0 for a PR this run created; otherwise the counters in `supervise-prs`'s last returned record for that PR, which the state block carries every cycle;
- **posting-identity map**: the run's whole map — and this run takes back the map it returns and merges it, as it does a worker's (`references/posting-identity.md`);
- **review routing and trigger state**: as each worker's `create-pr` left it, and `deferred` where this run deferred review (*Implementation worker contract*); a convention performed by dispatched review sessions is passed as performed by the `caller`, with the review and comment ids recorded there (*Review and repair sessions*);
- **repair dispatch**: `swarm`, with whether a worker's return value reaches this run on the selected tier;
- **head checks**: the chartered-scope check below;
- **caller pushes**: every restack (*Stack mutation while PRs are open*) and renumber (`artifact-collisions.md`, *Performing the renumber*) this run pushed since the last pass, and every restack `merge-stack` performed with a gate-authorized merge, tagged by `references/mechanical-pushes.md`, with each branch this run is about to mutate held locked;
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

**Invariant 3, the frontier rule and dispatch authority do not bound one PR's diff through its review rounds; the chartered scope does**: each round's fix can be right for its finding and still enlarge what the reviewer is shown next. So the charter is written down at creation, from the issue, while it is still uncontested — never after the fact, from the diff.

**It is written where a restart can find it**, which the per-PR block, a cache by invariant 1, is not: `create-pr` writes it into the PR body at creation as a **`Chartered scope:` line** — a required content under the write-form rule, one or two sentences, surviving the budget as the linkage lines do — and adoption recovers it from there, never rebuilding one from the issue as it now stands.

**Where no charter line is recoverable, say so and do not invent one.** A PR this run did not create, or one whose body was rewritten without it, has no charter, and the chartered-scope comparison is **unavailable** for that PR rather than performed against a guess. Record it as unavailable in the block and report it that way.

**A worker that sees the seam first reports it rather than crossing the charter** (`implement-issue-core`, *Implement with remote checkpoints*), and it arrives as a **design finding on that worker's return**. Record it as a `DECISION` item — split or absorb — which is the disposition this gate would reach anyway, and hold the path it bears on.

**The chartered-scope head check, passed to `supervise-prs` stated in full** — `on-repair-head`:

> Compare the repair pass's pushed diff against the PR's `Chartered scope:` line. A fix that introduces a **new module**, a **new build or CI step**, or a **new cross-cutting invariant** is `hold` — a `DECISION`, split or absorb — and not an adoption. Everything else is `adopt`: the test is the kind of thing added, not its size. Where the PR carries no charter line, the check is unavailable for that PR: `adopt`, and report the check as unavailable — never perform it against a reconstructed charter.

A PR `supervise-prs` returns `held: check` by this check is recorded here as a `DECISION` item, and holds the path it bears on. It stays held — no dispatch and no adoption on that branch — until this run passes a release, which it does once the `DECISION` is ruled, with the ruling.

The worker-session line makes the loop's release reconciliation a lookup rather than fuzzy-matching session titles.

# CI/review repair

`supervise-prs` — *CI failure*, *Review feedback*, *Finding repairs* — owns every repair of this run's PRs, dispatched through `swarm` on the model it chooses. What stays here:

**A producer merge can turn this run's open PRs in another repository red.** `references/ci-attribution.md`, *A producer merge*, classifies that red as expected-red, and `supervise-prs` reports it and counts it as surfaced. **The remedy is this run's**, because it needs authority over the PRs' bases:

1. a confirmed check is expected-red pending the refresh PR the repository's tooling opens. Watch that PR — it belongs to no wave and is outside `supervise-prs`'s PR set, so this run reads it itself, under `references/watch-and-read.md`;
2. read its removed lines before trusting it: generated is not additive, and an apparent removal may be a reordering or a producer silently dropping what it claimed not to touch. A real removal is `NEEDS_USER` naming the field;
3. once it merges, restack each consumer PR onto the refreshed default branch as *Stack mutation* does — a stacked PR's base is its parent, not the default branch — passing each push to `supervise-prs` as a caller push, and read CI again; the rule says when the check then belongs to the PR.

A confirmed expected-red check **counts as surfaced rather than outstanding** (*Settled wave* states the set): it holds that PR's merge under invariant 12 and never blocks settlement, because nothing in this run can merge the refresh. The settled report names the refresh PR as the owner's merge to make, with any removal item attached.

## A settle finding is the third repair shape

**A thread reserved for the owner is not a source of an `IN_FLIGHT_FIX` where nothing can dispatch it:** a deferred repair is review-shaped work the review budget already refused, so it is reported and holds the gate rather than being re-dispatched under the finding budget (`summarize-wave`, *Action points*). **A thread carrying a recorded code-changing ruling is the exception and does belong here** — the finding path is its dispatch, and after a restart it is the only one left.

`summarize-wave` can derive an `IN_FLIGHT_FIX` action point solely from durable evidence that is neither CI- nor review-shaped — a worker's documented caveat, the diff itself, a coverage finding — and a walkthrough ruling that requires code to change arrives the same way, routed through the `IN_FLIGHT_FIX` row (see Settled wave). Neither has a failing check or a reviewer's thread behind it, so neither CI nor review repair has a compliant invocation for them, and `repair-pr` is required, so improvising something else is not an answer. `repair-pr`'s `finding` repair type is for exactly this: it takes the action point or recorded ruling verbatim as its evidence, the way `ci` takes logs and `review` takes threads, under the same bounded one-pass contract.

On an `IN_FLIGHT_FIX` action point, or a code-changing ruling its row routes here, **hand it to `supervise-prs` as a finding to repair**, verbatim, with the run's map; take back its outcome and the map it returns, merged; then re-test the settled conditions before ranking anything (see The summary can un-settle the run):

- a pushed repair un-settles the run as any change does; `NO_CODE_CHANGE` changes nothing;
- `needs-user` is surfaced like any other — and **that finding is never handed back again on a later settle**: its `NEEDS_USER` item now carries it, as a `DECISION` for the owner, so a failed repair, which consumes no cycle when it pushed nothing, cannot loop through the summary and back;
- **an owner's ruling to try again is new evidence, not the same finding**: a ruling to lift the budget or try again on a `needs-user` PR — CI-, review- or finding-shaped — is a code-changing ruling, and takes this path within `finding-repair-cycles`. Where that budget is itself spent, the ruling cannot move the PR on this run's authority: the settled report says so, and names the re-invocation that would — this manifest with `finding-repair-cycles` raised for that PR, the policy being read once at preflight.

## Mechanical pushes do not consume review

This run tags each restack and renumber it pushes by `references/mechanical-pushes.md`'s test, conditions included, and passes it to `supervise-prs` as a caller push; what a mechanical push means for the PR's record is that skill's (*Pushes this skill did not make*).

## Draft state

`supervise-prs`, *Draft state*, applies `references/draft-state.md` to this run's PRs. An **explicitly held draft** is reported in the checkpoint output as held, awaiting the owner.

# Parent supervision loop

Long-lived PR/CI/review supervision always runs in this parent loop, never inside a Dynamic Workflow — a workflow run accepts no external input once started and does not persist past the current session. This holds even for a run whose implementation fan-out did execute inside a Dynamic Workflow: once it returns its worker results (PR URLs, branches, heads), supervision reverts to this loop.

The main parent thread must remain active while mutating workers run or active PR events can lead to more in-scope work.

Each cycle performs real work:

1. consume worker completions (including a Dynamic Workflow's returned fan-out results, if one was used), extracting each one's dependency evidence — unmet blockers, source disagreements, **and the resolutions that confirmed your view** — and **merging every posting-identity entry it returned into the run's transport-and-credential-keyed map** (see `references/posting-identity.md`), regardless of its outcome. Do this before releasing the worker: the worker's transports are not this run's, so its observations are the only evidence the run will ever have about them, and a released worker cannot be asked again;
2. **run `supervise-prs`, *Pass*, over this run's PR set** — the delivered PR events, the repair completions step 1 consumed, this cycle's caller pushes and any findings to repair — with the inputs *PR promotion and central supervision* lists. It reads what is due, dispatches repairs through `swarm`, adopts heads after the chartered-scope check, re-triggers and promotes, and returns an outcome per PR with the map it updated. This run makes no supervision read of its own beside it. Its own reads — the tracker reconciliation, the refresh PR, and the reads `validate-backlog` and the settle skills make — follow `references/watch-and-read.md` too: only where this cycle has a reason to, in one consolidated pass, a deliberate descent to a lower transport tier recorded as *Transport precedence* requires. Its dispatch-as-reading carve-out reaches those required skills, which are mandatory where they are mandated, budget or no;
3. fold the outcomes into the per-PR blocks and act on them: `merged` or `closed` is a frontier event (Frontier advance on merge); `finished` feeds the settled predicate; `held: check` by the chartered-scope check is a `DECISION` item; `needs-user` goes to step 15, whose item is what makes it surfaced (*Settled wave*);
4. merge the map `supervise-prs` returned into the run's map, and update this run's budgets;
5. repair workers are this run's workers under `swarm` like any other — their completions arrive at step 1 and are forwarded to the next *Pass*;
6. recompute READY frontier;
7. fill available worker slots, up to the `concurrent-open-prs` headroom (optionally via a fresh Dynamic Workflow fan-out if the user re-opts in for the next batch — read `dynamic-workflow.md` before writing it);
8. inspect stack ancestry changes;
9. inspect every in-flight worktree for uncommitted work and enforce checkpoints (see `swarm`, *Checkpoint compliance* — a mandatory step; the parent captures on the worker's behalf as `swarm`, *Enforce, do not re-ask*, decides for the recorded capabilities — on first observation where no channel reaches the worker — by the capture that section defines, its ref then ended under Checkpoint compliance here) — **mandatory wherever worktrees are reachable, and inapplicable where the run established they are not**, in which case this step is the remote-head reading and the report saying so, never a skipped step recorded as a passed one;
10. read every worker's runtime state, not only its work state — release the finished (see `swarm`, *Releasing a worker*) and act on the blocked (see `swarm`, *Blocked workers*);
11. **reconcile released-vs-alive against the runtime, never against the run's memory** (`swarm`, *Runtime: take what is there, and say which*, states the three sources and which is authoritative) — the run's own record of releasing is not evidence, and reporting an action is not performing it. On a runtime with a session list, list the sessions whose provenance marks them as created by this run (`parent_session_id` on Claude Code Remote — never "sessions that look like workers"), and compare against the per-PR records. Three outcomes:

    | session | action |
    |---|---|
    | **mine and archived** | done |
    | **mine and still alive** | apply the releasable test and **archive every session that passes**, this cycle. On the remote-session tier the worktree is never inspectable and the test reads the remote state in its place (`swarm`, *Releasing a worker*, condition 2), so an uninspectable worktree is no reason to keep a finished session. What fails the test takes the state `swarm`, *Releasing a worker*, gives it: **still working is left and re-checked next cycle**, a stopped one goes to *Blocked workers*, a lost one to *Lost workers*, and a mismatch is `NEEDS_USER` only after the commit-and-push lever, where a channel exists, fails to close it; a live session this run created stays this run's cost and this run's problem |
    | **not mine** — provenance proves it another run's or the user's | report it and never reclaim it, whether or not its worktree is inspectable |

    **For every session this step leaves alive, the report is diagnostic rather than a count.** Name, per session: the issue it was chartered for; **its reachability** — whether its head commit is reachable on the remote, and where it is not, how far the remote head has got; and whether it carries staged or uncommitted files. **Branch existence is not progress** — the `clean | local ahead` case (`swarm`, *Checkpoint compliance*) reads as healthy under a branch-exists field. Where the worktree is reachable, compare its local head against the remote's; where it is not, record the remote head and **how long since it last advanced** — a head unmoved for days against a live session is the same signal from outside. Where a field cannot be read from here, say which one and that it is unread; an unread field is not a clean one.

    **The test is whether the work is reachable on the remote, never whether a branch of that name exists.** Reachable is defined once, on the worker's head commit, under `swarm`, *Releasing a worker*. Where the tracked remote branch is absent, check whether its PR merged before reading anything as stranded: a merged PR's branch is routinely deleted by the forge. The remote-branch reading is also what the capture lever under `swarm`, *Releasing a worker*, turns on, so it is needed in this pass regardless.

    **Report every session this step archived** in the state block, by id and charter. **And list this run's triggers**: a trigger bound to one of this run's worker sessions means the countermand did not hold, and the remedy is to archive that session where the releasable test passes — not to delete the trigger, which a live session re-arms (see `swarm`, *Releasing a worker*). A worker that is still working and has armed one is a finding about the dispatch prompt, reported as such;
12. **emit the state block** (fields: `schemas/checkpoint-output.md`; rules: Progress / checkpoint output) — every cycle, including the long one-PR supervision tail, not only in closing output;
13. report slot capacity (`swarm`, *Capacity during the run*);
14. check sibling branches for colliding added or modified claimed artifacts (Cross-branch artifact collisions) — on finding one, read `artifact-collisions.md` before acting on it;
15. surface `NEEDS_USER`;
16. wait using native task/event wait, then repeat. **One loop and one wait per session, and both are this run's**: `supervise-prs` runs inside this loop with `wait owner = caller`, arms no check-in of its own, and its PRs' changes are deltas on this run's one wake (Arming the wait when nothing is in flight). **The PR subscriptions `supervise-prs` armed wake this session, and this invocation overrides the platform's PR posture they carry** (`references/platform-pr-posture.md`): every wake — `subscription.created`, a CI failure, a comment, the check-in — is answered by this loop's next cycle, never by the posture's own loop, and a spent budget ends in `supervise-prs`'s outcome for that PR, never in another repair push.

Do not use CPU loops, file-touch loops, detached sleeps, meaningless commits, or other fake activity solely to prevent idling.

Remote Git checkpoints remain mandatory regardless of runtime, because no platform/runtime persistence substitutes for durable source control.

## Every read is a snapshot

`references/establish-do-not-assume.md`, *Every read is a snapshot*, states it: a multi-item read is a composite of instants, so re-read the deciding facts immediately before acting on them, timestamp every state report, and settle a checkout-versus-API disagreement by a third read. Apply it from there. Here it reaches the merge gate's freshness check (`settle-and-merge`, *Merge behavior*, is one instance), the ranking, every checkpoint and handover, and every dispatch prompt, which carries the checkout-versus-API half because a worker inherits the same habit and has less to check it against (*Implementation worker contract*).

## Arming the wait when nothing is in flight

Step 16's native task/event wait is sufficient while workers are running: their completions are the events. A **settled** run has none — no worker will finish, no CI will fire, and the merge it is waiting on may be a day away.

**Before a settled-and-undispatchable run stops doing work, it arms the wake `references/wake-budget.md` requires** — a PR-activity subscription over this run's own PR set, which `supervise-prs` armed per PR at adoption, so this step confirms the set is complete and arms anything missing, and a bounded scheduled check-in as the backstop — under that rule's budget and backoff, which bind **every recurring check-in this skill's runs arm, parent-side or worker-side**. What this run adds:

- **the check-in runs `supervise-prs`, *Pass*, and re-reads the frontier**, and acts on what it finds. Its prompt carries what that skill's comparison needs — the PR set and each PR's durable state (`supervise-prs`, *Wait*) — and the inputs this run passes it, as the last state block recorded them: budgets, counters, trigger states, the chartered-scope check's text, and the run's own write ids the reply watch filters, hold retirement records included;
- **it also re-reads each held worker session** (`swarm`, *Blocked workers*) — one observed to have resumed, been released or been redispatched retires its item on that section's closing rule, and un-settles the run;
- **the reply watch: it also re-reads where every open `NEEDS_USER` and `DECISION` item this run raised lives** — the item's own issue or thread, a short list bounded by the items themselves — for a reply newer than the item, since no subscription delivers an owner answering on an issue. **A reply releases the hold only when it is the owner's and it answers the item**: authored by the owner — not a bot, and not one of this run's own writes (the write ids its posting-identity map records, hold retirement records included, since the run commonly posts as the owner's own account) — and choosing one of the options the item put. Then release what the item held, re-test dispatch (*When the advance waits for a human*), and report the release with the reply's URL. It is an observed answer, not a ruling, so write nothing claiming one — an interactive ruling is `settle-outstanding-decisions`' to record, and this wake is unattended. A reply that is ambiguous, answers something else, or comes from anyone other than the owner is reported and the hold stays. **Releasing the hold releases dispatch only**: the item stays outstanding for invariant 12 until the settled step's walkthrough retires it, since the owner's reply is a record it can retire it from without asking again (`settle-outstanding-decisions`, *What qualifies as an outstanding decision*). **A held worker's item is the exception**: only its hold's observed ending retires it, never a reply or a ruling (`swarm`, *Blocked workers*, its last rule). An item that rule restated to its work unit after an archive is no longer a held worker's item, and takes this bullet's ordinary path;
- **deltas**: a held worker session resuming, and a new reply at the site of an open item this run raised, are deltas under the budget's clearing rule; a wake that finds a new reply at an open item's site is productive, whichever way it goes;
- **stop once every PR in the set is merged or closed and no item this run raised is still open**; until then the watch runs within the budget, which the open items do not extend. **Where an item this run raised is still open when the budget runs out, the stop report names each one and says that a reply to it will not be noticed until the run is invoked again — and lists from `supervise-prs`'s record every held reply not yet posted, with its text, every rejected one and every mixed-thread fix left for the owner, since all are dropped with the run** (`references/review-feedback.md`, *Approval-pending replies*). **A stop on the budget ends the subscriptions with the check-in** — every PR still open is unsubscribed and named with its toggle line (`references/platform-pr-posture.md`, *The watch ends with the run, not after it*). A held worker session is returned as `swarm`, *Blocked workers*, requires when its watch is spent;
- **a quiet wake is silent about state and never silent about what is waiting on the owner.** An outstanding `DECISION` or `NEEDS_USER` item is not durable state, so the unproductive-wake test cannot see it: every wake reports (in the state block) the outstanding `DECISION` and `NEEDS_USER` counts and the approval-pending reply count, on the same lengthening cadence as the wake itself, even when it reports nothing else. **Quiescence with open decisions or approval-pending replies is a settle trigger on an attended turn or a real state change, never on a quiet unattended wake**: a run whose only remaining movement depends on an answer nobody has been asked for settles and routes the items through the settled step — but on a scheduled wake `settle-outstanding-decisions` declines for want of anybody to ask, and step 8 forbids re-deriving settled state that has not changed. The counts are reported on every wake; the sequence re-runs only where someone is there or something actually moved;
- **write the release step into the wake's own prompt, as well as the count** — the prompt a run writes for its own check-in is what survives compaction, and the run's memory of what supervision involves does not. Each re-armed prompt names step 11 — read the session list by provenance, apply the releasable test, archive what passes, report what was archived — and the settled step sweeps once more before returning;
- **the wake's prompt carries the posture line** (`references/platform-pr-posture.md`, *Saying so*), naming this skill — the check-in is the one wake whose text this run writes;
- **the wake's prompt carries, beside the count and the comparands the budget rule requires, each open item's site, the newest reply already seen there, and the ids of this run's own writes**, since the posting-identity map that tells an owner's reply from the run's own post lives in session memory, and a firing without it reads the run's own review trigger as the owner's answer.

**When neither can be armed**, reconcile durable state and return the restartable checkpoint the budget rule requires, naming the resume frontier and the PRs whose merges would advance it, exactly as Stop conditions already requires when the runtime cannot safely stay active. Restart / resume (`restart-resume.md`) adopts that and re-derives readiness from durable truth, so what is lost is the automation, not the work.

## Frontier advance on merge

A merge someone else performed is a **frontier-advancing event**, not a terminal one: it is the thing that turns in-scope `BLOCKED` issues into READY work. Steps 6 and 7 of the loop above are how the run consumes it, and they stay reachable after the wave settles. On every merge/close event:

1. reconcile tracker + GitHub remote state, so readiness is recomputed from durable truth rather than cached run state — **once over every merge/close event already delivered**;
2. restack affected descendants (see Stack mutation while PRs are open), **and renumber the next independent colliding migration** where the merge was one of them (read `artifact-collisions.md`, *Performing the renumber*, before performing it);
3. recompute the READY frontier over the **same bounded manifest**, crediting merges only (below). A merge never widens scope: an issue the invocation did not adopt does not become in-scope because something it depends on merged;
4. if new nodes became READY, re-run the preflight over the bounded scope before dispatching — **at the mode the escalation rules select**, not shallow by default (see Escalating to deep validation; where a trigger fires, read `deep-validation.md` before this preflight) — then fill free worker slots in scheduling order, **up to the `concurrent-open-prs` headroom**; free worker slots are not free PR slots. The preflight is mandatory before **any** new implementation worker, and the merge changed the graph the previous run validated. **What is optional is rebuilding what you already hold**: hand the validator the prior validated graph and the change, so it verifies the delta rather than re-enumerating hierarchy, project structure and every dependency edge. Where the validator cannot accept prior state, the full re-derivation stands; the cost is a tooling limitation to report, not a reason to skip it;
5. **whether or not anything became READY, a merge or close of one of this run's PRs released a `concurrent-open-prs` slot — if the cap was holding READY work, fill the freed capacity**, within `new-issue-budget` and running the preflight over the nodes it starts (where a trigger fires, read `deep-validation.md` before it; step 4's waiver covers the *advance*, never a dispatch: invariant 7 dispatches only validated READY work). Otherwise stay settled and keep supervising.

This requires no new user prompt. While `new-issue-budget` has headroom and in-scope work remains, a merge or close resumes dispatch inside the same invocation.

**Only a merge advances the frontier; step 3 credits merges alone.** A close is worth reconciling but is never an advance: completion is a closed issue **plus a merged** implementation PR (see Completion semantics), so crediting a close dispatches a fresh worker to recreate the PR a human just declined, and an unmerged close unblocks nothing downstream. On an unmerged close, reconcile and stop there: hold that issue and everything downstream, surface it as `NEEDS_USER` naming the closed PR — abandonment, a rejected approach, and work superseded elsewhere are indistinguishable from the event and call for opposite next moves — and redispatch that path only on an answer, never on the close itself. **That prohibition is about the closed PR's own path and nothing else: the close still released a `concurrent-open-prs` slot, and step 5 fills it from the READY set the cap was holding.**

### When the advance waits for a human

Continuing is the default, and the advance never manufactures a question the skill has a documented default for (see Autonomy and interactive prompts). What it must not do is dispatch *through* an ask the previous wave already left outstanding — starting the work is one way of answering it. Hold a path where an outstanding item bears on the work about to start:

- a `DECISION` action point, or a `MERGE_RISK` raised as `NEEDS_USER`, **whose answer would change what or how the newly-READY node gets built**;
- an unverifiable-prerequisite `NEEDS_USER` the merge did not satisfy — a merge retires only the blockers it actually satisfied;
- an **unproven dependency view** `NEEDS_USER`, which holds the whole advance rather than one path: step 3 recomputes readiness through the same transport whose reach is in doubt. **A worker cannot raise this against a boundary you classified `dependency transport unavailable`, and if one does, read it as a report rather than a hold** — there is no proof to re-establish. Where a dependency transport does exist, re-establish the visibility proof before dispatching anything, exactly as at the preflight.

Everything else continues. A `NEW_ISSUE` follow-up, a question about how the merged PRs themselves are handled, or a `NEEDS_USER` on an unrelated branch does not hold a node it has no bearing on — and holding one path never holds the others: dispatch the unaffected newly-READY nodes in the same pass.

Read the merge itself as evidence. A user asked to choose between two approaches who then merged one has answered; do not hold work on a question their merge settled. What survives is the ask the merge left genuinely open.

Holding is not idling. Name the outstanding item, the node it holds, and what answer releases it — in the checkpoint output and as a live `NEEDS_USER` — and treat the answer as its own resume signal: the held node dispatches on a reply that passes the check-in's test (see Arming the wait when nothing is in flight), in the same run, with no re-invocation.

Nothing about the advance relaxes the safeguards it dispatches under:

- **invariant 12 still holds.** Auto-advance is triggered by observing a merge — whoever performed it, a merge invariant 12's gate authorized included — never by deciding one should happen. The advance itself merges nothing.
- **both budgets are consumed like any other dispatch.** If `new-issue-budget` is exhausted, do not dispatch: report the newly-READY frontier in the checkpoint output as the resume frontier, so a resumed invocation adopts it instead of rediscovering it. If `concurrent-open-prs` is the one exhausted, the frontier is reachable within this invocation without settling anything: dispatch into whatever headroom there is, which a merge of one of this run's PRs has just freed and a merge elsewhere has not — then wait for the next release (step 5). Never silently drop newly-unblocked work.
- `concurrent-workers`, attempt/repair caps, per-issue model selection, one issue per worker, and isolated checkouts apply to resumed dispatch unchanged.

Edge cases:

- **A merge that unblocks nothing in scope** advances nothing: no advance and no preflight *for the advance* — reconcile and restack, then go on to step 5, which still applies. **It still released a `concurrent-open-prs` slot**, so where the cap was holding READY work, fill the freed capacity — the release is a dispatch trigger in its own right, and a close of one of this run's PRs is too, though a close advances no frontier.
- **A merge landing while workers are still in flight** advances the frontier without disturbing them. Recompute readiness and dispatch only into free slots; in-flight workers are never cancelled, restarted, or re-scoped because their frontier moved.
- **A newly-READY node that re-blocks on validation** (the preflight returns `FAIL` on its path, or a warning that makes its ordering unsafe) is not dispatched. Record it and continue with the validator-confirmed safe branches, exactly as at the initial preflight.
- **A wave that settled with a `DECISION` outstanding** advances every path the decision does not bear on, and holds only the ones it does. A pending question is a reason to hold a node, never a reason to stop the run.
- **A close event mixed into a batch of merges** — a stack where seven PRs merged and one was closed unmerged — advances on the seven and holds the eighth's issue and its descendants. Do not let the merges in the batch launder the close.

## How a worker's report actually reaches you

`swarm`, *How a worker's report actually reaches you*, owns the carrier — which runtime delivers a worker's report at all, what the session record carries without anyone writing it, and routing the report by whether a PR exists. This is the dependency-specific half: what this run does with a worker that stopped on a dependency before any PR existed, and why a report never becomes a blocker record.

On the no-PR path, first separate the dependency-shaped outcomes from the rest. A `FAILED` from an implementation or tooling fault carries no blocker URL, no resolution and no dependency credential — legitimately, and not the "unanswerable" of step 1 below — and feeding it into the decision below would send a compile error down the unproven-boundary path and hold every sibling. Route those by their own outcome: `FAILED` follows the retry policy, a product-decision `NEEDS_USER` its own handling. What follows applies where the worker stopped **on a dependency**:

- **`needs_action` carries the same duty on every dependency-shaped outcome, not only `NEEDS_USER`:** the blocker's canonical URL, how it resolved, and the worker's transport tier and non-secret credential identity. Without the identity a `BLOCKED` is uninterpretable: step 2's reconcile-and-stop is available only where both sides read the same transport.
- **One line cannot carry several blockers, so never read it as a complete set.** The summary is a **pointer**; its silence about further blockers is not evidence there are none. And where it names **any** blocker the worker could see and you could not, the finding is that **your view of that boundary is short**, whether or not the named edge was already in your set.
- The parent cannot close that hole by looking harder: repeating the dependency read under its own credential reproduces the blind spot exactly and returns looking like confirmation.

The response is an ordered decision, and **every step resolves to the last branch when its input is missing** — absent is never treated as matching, as empty, or as agreeing:

1. **Can the blocking edge be identified at all?** A dropped URL has no PR and no readable transcript to recover it from, and the dependency set that would answer the next question is the very set suspected of omitting it. Unanswerable — go to 4.
2. **Did both sides read the same transport, and is that edge already in this run's dependency set?** Test the transport first: if the worker's credential reached edges yours cannot, **stop here and go to 4** whatever the membership answer is — a summary naming one blocker you already hold had room for one. Where both read the same transport and the edge is already in your set, only its *state* differs — an open PR not in the selected base, a prerequisite incomplete by its own measure, a `BLOCKED_EXTERNAL` that is a known wait rather than a graph error. That is an availability matter, as Outcomes separates availability from visibility: reconcile that edge's state and stop. **Do not invalidate visibility for it.**
3. **If the edge is absent from this run's set, rule out an intervening change before concluding anything about visibility**, per Outcomes. Re-read now: if the edge appears, it was added between this run's readiness computation and the worker's read — a race, reconciled as an ordinary new dependency. If it does not appear, it is either invisible to this run's credential or was removed after the worker saw it, and **only a demonstrable removal resolves that** — otherwise go to 4.
4. **The boundary is unproven.** Establish visibility against a known-true case, per Transport visibility; where none is available the issue is held as the *unproven dependency view* kind of `NEEDS_USER`, which holds every sibling dispatched through the same read. Treat the block as disproof of this run's own view rather than as a claim to re-check.

   **Unless the boundary is already classified `dependency transport unavailable`** — then no known-true case can exist by construction, and demanding one would hold every sibling indefinitely on a limitation accepted at preflight. The worker blocked on prose, the only source either of you has: reconcile the blocker from the issue's own text, and where that cannot identify it, escalate **this issue** as an unverifiable prerequisite — never the boundary.

**Where the worker's credential identity is unknown, treat it as differing** — the same rule as step 1, at the other input. `needs_action` is written by the runtime summarizing the worker's turn, not by the worker, and how reliably the summarizer preserves these facts is **untested**. The identity and the blocker URL sharpen this decision when they arrive; neither is a precondition for reaching step 4 without them.

**`NEEDS_USER` needs one thing more**, because its two kinds demand opposite handling — an unverifiable prerequisite is a question for a person; an unproven dependency view is transport evidence that invalidates a visibility proof and holds every sibling. Require the dispatch prompt to have the worker put **which kind, and the exact measure that was out of reach**, into `needs_action`. A parent left to infer the kind from an empty blocker list handles the expensive one as the cheap one.

Establishing a blocker is the parent's job, needing a visibility proof the worker does not hold, so on the no-PR path the parent writes the record, never the worker.

None of this is implementation-specific. A repair worker's return value is lost on the same tier in the same way; what its dispatch prompt carries for that is `supervise-prs`'s (*Repair dispatch*).

**A worker's report is evidence; a blocker record is a conclusion. Keeping them apart is what the routing (`swarm`, *How a worker's report actually reaches you*) is for.**

| | written by | says | restart treats it as |
|---|---|---|---|
| worker report | the worker, on its PR | what I observed | input awaiting classification — never a blocker |
| blocker record | the parent, after classifying | what was established, and how it was verified | an established blocker |

**Restart adopts blockers only from parent-written records**, per `restart-resume.md`, step 2. An unclassified edge does not become established by surviving a session boundary.

A report must never land in an issue comment: three skills read issue comments for dependency information, so a report there manufactures permanent blockers, automatically, on every run:

| reader | what it does with a comment-named edge | why it matters |
|---|---|---|
| `implement-issue-core` | unions it into the issue's blocker set | re-blocks the issue on every later dispatch |
| `validate-backlog` | scans comments in a **mandatory preflight** | reintroduces the edge on every validation |
| `normalize-github-dependencies` | **promotes it into native metadata** | worst case — native is authoritative and an empty `blocked_by` is indistinguishable from "no blockers", so nothing later re-examines it |

## Verifying worker reports

`swarm`, *Verifying what workers report*, states the rule; apply it from there. For a PR, the durable evidence is CI on the pushed head, and the rule reaches one decision that module does not have: never block a merge decision on a worker-reported failure unverified. The same status attaches to a reviewer's claim of a commit, a carried note from a previous run, and this run's own statement of what it is about to do (`references/establish-do-not-assume.md`).

## Checkpoint compliance

`swarm`, *Checkpoint compliance*, owns what the parent observes of every in-flight worker each cycle, the stalled-head escalation, and when it nudges and when it captures instead (its *Enforce, do not re-ask*). It also owns how the parent captures — the ref-neutral sequence that does not race a live worker, its verification (in the tested script), the recovery-ref naming, the wedged-worker path and the tested script beside that skill (its *Capturing without racing the worker*) — and the recovery ref's generic lifecycle (its *The recovery ref's lifecycle*). Apply them from there; here the worker's branch is its issue branch, and its task-owned paths are the issue-owned paths. This section is what becomes of a ref this run captured: an ender keyed on PR state, the issue's completeness and invariant 12, which replaces `swarm`'s generic reachability ender (the rest of that lifecycle — redundancy, release-time reconciliation — still applies).

**The principle is `swarm`'s — a recovery ref is dropped only once a durable carrier the run will actually read holds its contents.** The four PR states differ solely in whether such a carrier exists, and all four are enumerated deliberately: a missing case leaves a ref with no ender, which invariant 12 then converts into a PR that can never merge. Its consumers are the release-time reconciliation and the blocked-worker archive (`swarm`, *The recovery ref's lifecycle* and *Blocked workers*), and lost-worker recovery (Lost worker / workflow recovery):

| PR state | ender |
|---|---|
| **open** | Reconciling advances the branch, so the PR's CI and review evidence now describes a head that no longer exists: that PR re-enters ordinary supervision and is re-evaluated on a later pass. Until the reconciliation lands the PR carries an outstanding recovery ref, which the gate excludes. Once it is on the branch, **verify the capture's commit is an ancestor of the branch head, then delete the ref.** |
| **none yet** — a worker that returned `BLOCKED` or `FAILED` before creating one | PR state is irrelevant to release (`swarm`, *Releasing a worker*), so this worker is as released as any other. Reconcile as `swarm`'s release-time reconciliation says (*The recovery ref's lifecycle*); then verify and delete as above. The branch is a carrier the run reads — item 3 of the durable-evidence order — so a redispatch picks the work up, and nothing here looks like completion. |
| **closed without merging** | Same handling as no PR: the branch is still the carrier, nothing merged, the issue is not complete. Reconcile, verify, delete — and **report it**, because a closed PR usually means a person decided against that line of work. Do not treat the closure as authority to discard the capture; that decision is theirs and this path does not ask them for it. |
| **already merged** | **Branch reconciliation is not a fix and must not be performed as though it were**: the merge commit is already in the base, the branch of a merged PR is not read again, no CI or review runs on a merged PR, and the gate has nothing left to withhold. This is common — a wake armed at PR creation outlives the PR that armed it (`swarm`, *Releasing a worker*). So this case is `NEEDS_USER`, and **that issue is not complete**, whatever the merged PR implies, and must not be reconciled to complete while the ref is outstanding. Surface the issue, the merged PR, and the ref name. Do not open a follow-up PR automatically — the capture is a WIP snapshot of unknown completeness (`swarm`, *Capturing without racing the worker*), and landing it under the authority of a review that never saw it is worse than reporting it. **Delete nothing** until the owner decides; here the ref is the only copy. |

### Where the parent cannot reach

This contract assumes the parent can **see** a worker's checkout and **send it an instruction**, and the two come apart by tier. Both are established at startup rather than assumed (`swarm`, *Remote worker session arguments*):

| tier | see the checkout | send an instruction | what enforces invariant 5 |
|---|---|---|---|
| subagents in parent-created worktrees | yes | yes | the escalation (`swarm`, *Checkpoint compliance*), as written |
| remote worker sessions | normally no, and never assumed — the session record hands out a repository and no path, and the container is not shared | whichever the recorded capability says — absent for every worker session the observed runtime was asked about; never assumed | only the worker's own pushes, via its dispatch prompt, plus `NEEDS_USER` |
| Dynamic Workflow fan-out | no — its worktrees are not paths the parent was given | no — workflow agents accept no input mid-run | the script's structure (below) |

So the remote-session tier sits beside the workflow tier for this section's purposes, not beside subagents. A remote worker session cannot be made to checkpoint structurally — nothing in the parent's reach interposes on it — so the honest guarantee is weaker: state that in the checkpoint output rather than reporting invariant 5 as enforced.

Under a workflow, work is checkpointed only at stage boundaries; report invariant 5 as holding only there.

## Cross-branch artifact collisions

After each PR reaches durable state, compare it against **every open branch targeting the same base, not only this run's own members** — a track this run did not dispatch is not in its graph at all — and flag three kinds of collision:

1. files that two branches both **add** under the same name or sequence number;
2. incompatible edits two branches make to a shared claimed artifact — a generated manifest, lockfile, registry or index that branches amend rather than create, and which therefore collides with no added path in common. The general class of the first two is any artifact whose identity or ordering is claimed rather than derived;
3. **a collision with no textual overlap at all**, where one branch renames or redefines something another branch's new code depends on by name (one adds tests querying `Center`, another renames it `Centre`). It has no conflict signal of any sort, and each PR's CI is green against a base without the other: detect it by merging the branches into a scratch branch and running the suite whole, never by reading diffs.

Dependency edges and stack ancestry do not detect any of these — the branches are siblings, not ancestors. **State in the run's output which branches were integrated, each with the head SHA it was integrated at**, so a partial set is visible as partial rather than as a clean result, and so the gate can tell whether the tips have moved since (see `settle-and-merge`, *Merge behavior*).

**On finding a collision of any of the three kinds, read `artifact-collisions.md` (beside this file) before acting on it**: which kinds this skill resolves itself and which it surfaces to the owner, and how a renumber is performed. **Read it before dispatch as well, wherever more than one open branch targeting a base may generate a migration** — an issue this wave dispatches that names a table, column, index or migration, or another track's branch that already carries an added migration: such a collision is expected, and that file says what each worker is told and what is recorded.

# Lost worker / workflow recovery

`swarm`, *Lost workers*, owns the procedure — what to inspect in which order, adopting pushed checkpoints, the redispatch and the escalation on repeated loss — and applies here as written, with the issue as the task, `lost-worker-redispatches` as its budget, and tracker state among what a resume reads when the whole cloud container/workflow disappears.

Its step 4 ends the recovery ref by **the four-state rule under Checkpoint compliance — apply it, do not restate it here.** All four states reach this consumer: a worker can disappear before opening a PR, after its PR was closed unmerged, while it is open, or after it merged. Unconsumed, the ref blocks invariant 12's gate over work that has already landed.

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
- `BLOCKED_EXTERNAL` **on an unmet dependency** — a known wait, not a graph error: by the worker's contract *every* unmet blocker was external, and a worker that found any in-scope blocker alongside an external one returns `BLOCKED` instead, so this outcome never conceals one. Stop that path without re-deriving the frontier or invalidating a visibility proof over it. A source disagreement reported alongside it is still transport evidence and still handled as such.
- `BLOCKED` **on an unmet dependency** — authoritative new information about the graph, not a worker failure: the readiness computation was wrong, most often because the dependency read behind it was silently partial. Never redispatch the same issue unchanged. Retry and escalation budgets do not apply, because there is no failure to retry.
- `FAILED` — retry only inside budgets, escalated only on evidence (*Model and skill policy*).
- `NEEDS_USER` — surface full issue/PR URLs, failure/review state, attempts consumed, and recommended action; stop spending tokens on that node while continuing safe independent branches.
- `NEEDS_USER` **on an unverifiable prerequisite** — not a graph error and not a failure, and you can rely on that rather than re-checking: the worker's precedence returns `BLOCKED` whenever any in-scope blocker was also unmet, so this outcome carries none. The worker could not observe the completion measure that dependency's class requires, typically a release or deploy state outside the repository and tracker. Ask the specific question, and once answered supply it as dependency context on the redispatch — the caller asserting satisfaction is the documented path for a measure the worker cannot check. Asking buys the **end of the uncertainty**, not the clearing of the blocker: told the release has not happened, the prerequisite becomes a known unmet blocker and the redispatch returns `BLOCKED` or `BLOCKED_EXTERNAL` by its authorization membership; only an affirmative answer clears it. And even an affirmative answer clears only this blocker, not the issue: the precedence ranks an unverifiable prerequisite above an external wait, so this outcome can arrive with an out-of-scope blocker still unmet and reported alongside — read the reported blockers before expecting a redispatch to proceed. Do not invalidate a visibility proof over it; nothing here says the transport is partial.
- `NEEDS_USER` **on an unproven dependency view** — the worker could not establish that its blocker list was *complete*, with or without entries in it: your context arrived without a proven read, so its sources collapsed to one native read of unknown reach. A list with one blocker in it is not the reassuring version — a partial list is the dangerous one. **This is not the `dependency transport unavailable` case**, where there is no native read at all and completeness is unproven by construction on every issue: that is a condition of the run, recorded once and carried in the dispatch prompt, not a per-issue outcome that stops anything. This is transport evidence, and the one `NEEDS_USER` you must act on before dispatching anything else: invalidate the relationship-visibility proof for that boundary and re-establish it against a case whose answer is known, exactly as for a visibility disagreement — every sibling you judged READY through that read shares the blind spot. Do not answer it by re-asserting readiness; that suppresses the stop without changing what is invisible.

**A worker returns two independent things: an outcome, and evidence about the graph. Act on the evidence regardless of the outcome.** A source disagreement reported on a `PR_OPEN` is the same evidence of a partial dependency view as a `BLOCKED` would have been; treating only `BLOCKED` as a graph update leaves every sibling scheduled — bases and dispatch order chosen — against a view already known to be wrong. This adopts findings, never a re-plan; the validated DAG remains the scheduling graph.

**Confirmations are evidence too.** A worker reports how every dependency it checked resolved, not only the disagreements — a resolution that matched your view turns an assumed edge into a verified one. Record the right thing: two claims are bundled in a resolution and they age differently:

- **the edge exists** — structural, and long-lived. Persist it as verified, with the read it came from and when; it stops being an assumption but not being an observation, and it can still be retired (below);
- **the dependency was available** — an observation with a timestamp, and nothing more. A force-push, revert or rollback can undo it, as the availability-repair table below acknowledges.

So a verified availability resolution is historical evidence, never a standing exemption: every dispatch still re-checks the class-specific measure. What the record buys is a restart that knows which edges are verified and which are assumed.

**How a verified edge retires** — by provenance, since provenance decides which read can speak to it. **Provenance is where the edge lives now, not where it came from**: an edge recorded as a comment and later made native by `normalize-github-dependencies` takes the first row from then on.

| provenance | what retires it |
|---|---|
| **native-sourced** | a later native read with **proven visibility for that boundary** that no longer returns it. An unproven read does not: absence observed through an unvalidated transport is not evidence of absence. Nothing else is needed, because your own reads recur |
| **established from a worker's evidence and recorded as an issue comment** | no native read, since none was ever supposed to show it. From your own native view it is indistinguishable from a prose-only edge, so classify it on the same path — establish whether the relationship still holds, `NEEDS_USER` where the issues cannot settle it — **when a run adopts it**, which is where permanence would come from, and once per run (per dispatch attempt would re-ask every cycle a legitimately blocked issue stays blocked) |

An edge a worker found only in prose does not arrive here at all; it is classified first (below), because persistence is what makes a stale edge permanent. Retirement does not retract the observation — it records, dated the same way, that the relationship no longer holds, so a later read finding the edge again is a change rather than a contradiction.

**A satisfied dependency whose capability is absent is evidence of the same kind.** A worker that finds a declared dependency satisfied on paper — closed, merged, correctly linked — but the capability it needed absent from the code has found a **coverage** gap, a first-class finding on this path, not a note in its PR body; accept it on the same terms as an unmet blocker. Require it explicitly: the worker returns the finding whatever its outcome, naming the dependency, the capability it expected, and what it shipped instead. The parent records it durably against both issues like any other established blocker, **files the prerequisite issue**, holds the affected path behind it, reports it in the checkpoint alongside discovered dependency edges — and treats it as a trigger the preflight should have caught: the escalation rules under Escalating to deep validation did not fire on a node that needed them. **Before acting on a coverage finding, read `deep-validation.md`, *Coverage is not visibility***, for what such a finding does and does not invalidate.

**A PR shipping against a coverage finding must not close its issue.** Filing the prerequisite is not enough: a closing keyword auto-closes the partly-implemented issue on merge, and the `DONE` test then reads clean over unfinished work. The finding must reach `create-pr`, which links such a PR with `Part of:` and `Blocked by:` rather than `Closes:`; pass it through `implement-issue-core` on dispatch and verify the emitted form on the returned PR — a default that closes is what silence produces. The issue stays open, linked to its prerequisite; a human closes it once the gap is filled. Retrofit an already-open PR the same way when a finding arrives late, by `references/authored-write-form.md`, *Editing a PR body after it is created*: the non-closing form is edited in only where that rule allows, and otherwise the drift is reported with the non-closing replacement body. A merge that has already auto-closed an issue on a coverage finding is reconciled by reopening the issue, not accepting the close.

**Only a visibility disagreement is transport evidence.** The worker reports two kinds, and they warrant very different responses. An **availability** disagreement says your base or completion claim was stale. Two things pick the repair: the direction, and **the dependency class the worker reported** — read it rather than assuming a base problem.

| direction | code dependency | non-ancestry dependency |
|---|---|---|
| you asserted satisfied, worker observed otherwise | your base no longer holds — recalculate and restack, and check whether it was wrong when calculated or overtaken since, because a revert or force-push that keeps happening is a different problem from one bad calculation | your completion claim no longer holds — recheck it, or keep waiting; ancestry is irrelevant and no restack fixes it |
| you asserted unmet, worker found it available | your constraint may be obsolete — recheck rather than leaving the issue parked | same: recheck the constraint, do not park indefinitely |

Neither direction, in either class, touches a visibility proof. Everything below applies to **visibility** disagreements, where some other source named an edge the worker's native read did not return.

**First, a worker may not have been able to make this comparison at all.** Where the probed transport returns no edges — GitHub with no authenticated `gh` (see `validate-backlog`, *GitHub dependency reads depend on where you are running*) — the worker reports native as **unreadable** and its blocker set as unproven, not as an edge set that disagreed with yours. Where a read *was* available, the comparisons below apply normally, GitHub included.

**Where the worker could not read and you could, the obligation is yours, not a note to carry forward.** This is the **mixed** case — a local orchestrator with an authenticated cross-repo `gh` dispatching cloud workers that have none. (**Both-cloud is first-class, and there the limitation is symmetric, so this branch does not apply at all.**) The worker's prose-only check cannot catch a blocker added between your preflight and its dispatch, and your supplied context is by then stale. **Perform a contemporaneous dependency read yourself before accepting that PR, or hold it.** The context you already hold does not qualify, and neither does the worker's report: it correctly says it could not look. Never process this as a visibility disagreement — nothing was compared, so nothing invalidates a proof. And it obliges the refresh, **not** a decision about whether to dispatch: that decision was taken before this worker ran, under the carrying-unproven-completeness rule at the *dispatch* gate, and repeating it here would let the PR through on the stale preflight it was taken from. Everything below applies where the tracker actually returns edges.

Two variants can be demonstrations rather than suspicions — but only on conditions you must check, not assume, and the first is that you are comparing like with like.

**Compare native read against native read.** Your context is a union: edges from your own native read, plus blockers established from previous workers' evidence, deliberately recorded as issue comments rather than native edges. A worker's native read is *supposed* to lack that second kind, so their absence demonstrates nothing. Mark the provenance of every edge you supply (Before dispatch, step 9), and apply what follows only to edges your own native read produced — otherwise it fires on the graph corrections you yourself recorded, and each one invalidates a proof and halts dispatch.

Then, for a native-sourced edge — where **you supplied** one the worker's native read lacks, or where **its native read has one your context omitted** — compare the credential identity behind your read against the one behind the worker's. You already record yours per credential; the worker reports the transport and identity it used.

- **Distinct identities** — the cross-credential comparison the corroboration rules ask you to arrange, arriving unasked. **Independence and contemporaneity are separate conditions, and a mismatch is proof only with both**: the reads were taken at different moments, and an edge added or removed in between makes both credentials correct and neither view partial. Rule that out first — re-read the relationship through both identities, or check the edge's own history — and then invalidate; skipping that step spends a valid proof and halts every dispatch sharing the boundary on what may be an ordinary edit.
- **The same identity** — a subagent worker inheriting this session's credential is the common case, not the exception — proves nothing on its own: one credential cannot corroborate itself, across moments any more than across transports. The mismatch may be an edge that changed between the reads, or caller context that went stale. Take the ordinary corroboration path and treat it as evidence.

The direction says whose view was partial, and therefore what to fix. Yours missing an edge the worker saw means **your** frontier was computed short — recheck it for every issue that shared that read, not only this one. The worker missing an edge you had means its transport is the partial one, and the recovery below applies as written.

**A visibility disagreement is first evidence about the transport, only second about one edge.** Adding the single dependency a worker happened to find and re-deriving against the same view leaves every other hidden edge hidden. So read the disagreement against that boundary's visibility proof (see Proving a transport can see the graph), whose state determines which of two things you are looking at:

**Visibility unproven, or the proof invalidated** — treat this as truncation, not as one missing edge. **This whole branch presupposes a proof existed to lose; it does not apply to a boundary classified `dependency transport unavailable`**, where none was ever obtainable and steps 2 and 3 would demand re-establishing something that cannot be established:

1. adopt the named dependencies **provisionally** — real enough to schedule against, not yet established;
2. invalidate the relationship-visibility proof for that credential, exactly as an authorization error would;
3. **re-establish the proof** before filling further worker slots — a read with proven visibility for the boundary, established against a case whose answer is already known; not merely another read through another credential, which can share the blind spot. You do not know what else is missing;
4. **re-evaluate every provisional edge against the read you just obtained.** If it proves the boundary and still shows no native edge, that edge has moved into the proven case below and needs its classification before it is kept — a stale prose edge adopted while visibility was unknown must not become permanent merely because it was adopted first. Provisional edges are not eligible for the persistence rule below until they survive this step;
5. then re-derive readiness for every issue that shared that view, and re-check calculated bases for anything already dispatched against it.

**Visibility proven for that boundary** — native metadata is trustworthy there, so prose naming an edge it does not show is more likely stale text than a hidden edge: a dependency deliberately removed from metadata and left behind in the description. Do not auto-adopt it. Classify it — verify whether the relationship still holds, not merely whether the referenced issue is implemented, which is all the worker checked — and surface it as `NEEDS_USER` where that cannot be settled from the issues themselves. Never persist an unclassified prose edge: persistence is what makes every future restart re-adopt it.

When classifying, use the preflight you already ran. `validate-backlog` warns on exactly this shape — text names a blocker with no structured edge — so check whether it flagged this edge before dispatch. An edge flagged at preflight **and** reported by a worker is two observations of the *same prose*: their agreement about the prose establishes nothing that was in doubt. What it does establish is that two native reads both lacked the edge — and that rules out truncation only if at least one of those reads had **proven visibility for this boundary**. Distinct credential identities are not enough: two credentials can share the same insufficient scopes, repository boundary, or relationship transport, and both omit the same real edge. With a proven read among them, the question narrows to classification — the native edge was never created, or the prose is stale; without one, take the validated-read path as normal. **The property the conclusion needs is visibility, proven — never a proxy**: distinct transport, distinct credential, and distinct moment each fail as stand-ins.

The reverse also holds: a preflight warning no worker ever confirmed stays outstanding — do not let it expire quietly because its issue happened to complete.

Either way, do the graph work **before** filling further worker slots. One worker's disagreement is the cheapest evidence available that the graph is wrong; do not discard it because that worker happened to succeed.

**Persist it, or the next session repeats the mistake.** Run state is a cache (invariant 1), and restart re-expands the same manifest through the same transport that truncated. Record each **established** blocker — a truncation-case edge that survived re-evaluation against the validated read, or a classified prose edge confirmed to still hold — where the restart path already looks: a comment on the affected issue naming the blocker by canonical full URL and how it was verified, plus the checkpoint output. Persist nothing merely unclassified. Where dependency-write capability exists and the edge is high-confidence, `normalize-github-dependencies` is what makes it native — invoked explicitly, never as a side effect of this reconciliation.

# Settled wave

A run is **settled** when nothing in scope is dispatchable and every open PR is individually finished or surfaced:

- **nothing in scope is dispatchable.** Work is dispatchable when this run could start it this cycle: it is READY; nothing holds it for a human — a `NEEDS_USER` classification, a `DECISION` or other ask under *When the advance waits for a human* that reaches it, or a validation stop on its path, **each of which has been put to the owner as an item** (a stop the preflight only recorded is raised as `NEEDS_USER` naming the path and the defect when it becomes the last thing holding work); and every budget and capacity check has headroom for it. That covers resuming an adopted branch and redispatching a returned issue with attempts left, not only starting an unstarted issue. **State it this way, as a positive condition, and never as a list of the kinds of issue that may remain** — the complement of a positive condition is closed by construction, and every list of acceptable remainders has missed one. Everything in scope that is not dispatchable is waiting on something — unmerged work, a human, or a budget or capacity limit — directly or through its blockers, and the other conditions below or the owner account for it. Say in the checkpoint what holds each READY issue that is held. A capacity limit that resets on its own — an API allowance, a model's capacity — is re-tested on the next wake while one is armed; where nothing is open to arm one, it is raised as `NEEDS_USER` naming the limit and when it resets, since a settled run with nothing open never wakes to re-test it. One that will not, with no worker in flight — disk exhausted by retained worktrees — is raised as `NEEDS_USER` naming the limit, which makes it a hold for a human like the others. **This must stay one bullet**: every bullet in this list must hold at once, so two answering the same question are ANDed, and a merge that keeps both sides of a conflict here produces exactly that.
- no implementation or repair worker is in flight — and a worker blocked on a permission prompt is in flight, not absent (see `swarm`, *Blocked workers*), though it reads as quiet from every angle the other conditions look from. **Except a held worker that is surfaced** (below), which counts here as surfaced rather than in flight;
- **every open PR from this run is `finished`** (`supervise-prs`, *Outcomes*, owns the definition) **or surfaced** (below) — so none is waiting on CI, a review round or a pass;
- **no worker session this run created is still alive** — verified against the runtime's session list by the reconciliation step of the supervision loop, never against the run's memory of having archived. A run holding a live session it created is not settled, cannot emit a clean settled report, and does not reach invariant 12's gate. **The one exception is the session of a held worker that is surfaced** (below), including a mismatch the lever did not close (`swarm`, *Releasing a worker*): it is never archived on the run's own authority, so it stays alive; it does not block settlement, and the settled report and every state block name it as alive, with its URL and what it is waiting on. Any other live session this run created still blocks. Only sessions proven to belong to another run or to the user are excluded — reported, never reclaimed, and never counted.

**Surfaced is one set, stated here and cited by the conditions above that admit it.** Each member is held for the owner — and where it raises an item, that item has already been put to them — so it holds merges — that PR's, and while an item it raised is outstanding every PR's in the wave, as invariant 12's gate reads items (`settle-and-merge`, *The merge gate*) — and a held worker holds its own work, but **none holds settlement**: a run that waited on it could never reach the walkthrough that rules on it. The set:

- **what `supervise-prs`, *Outcomes*, counts as surfaced within `finished`**, as that definition states it — the expected-red check among them is the one whose remedy is this run's (*CI/review repair*);
- **a PR `held: check` by the chartered-scope check, with its `DECISION` raised as an item.** The `DECISION` is ruled at the settled step's walkthrough, and the release is passed after;
- **a PR `needs-user`, with its question raised as a `NEEDS_USER` item** — a spent CI or finding budget, a failure needing judgment, a pass that returned `FAILED` or `NEEDS_USER`. Nothing the run can do moves it before the owner answers, and the settle sequence is where the question reaches them if it has not already (*Autonomy and interactive prompts*) — the walkthrough, or the closing output where nobody is present to ask;
- **a worker held on the owner's authority** (`swarm`, *Blocked workers*, its last rule) **and raised as a `NEEDS_USER` item**, with its session — until that rule retires the item, when it stops being a member: resumed, it is in flight; released or redispatched, its session is gone or new. **Where an archive left the item standing, restated to the work unit**, that unit stays a member by its ordinary `NEEDS_USER` item, with no session, and its dependents are still named as waiting on it.

A member that raises an item is not surfaced until the item is raised; raising it is this cycle's step 15. **A member whose item is ruled stays surfaced until it moves**: a ruling that neither changes code nor merges — close it, leave it to me — is reported with its next owner, and the PR stays as it is; a ruling to try again moves it through the finding path, or cannot where the finding budget is spent (*A settle finding is the third repair shape*). A member moving — a release, a ruling carried out, a push, a merge, a held worker resuming — is new state and un-settles the run.

**Where planned work in scope waits on a surfaced member, the settle is partial, and it is still taken** — this is the one definition of a partial settle. Work waits on a member when it is not dispatchable only because of it, directly or through its blockers: a dependent of a surfaced PR, or of a held worker's unfinished issue. A dependent of a `needs-user` or `held: check` PR is not dispatchable — its blocker is unmerged work — so the run settles over it, early: the purpose of this settle is to put the decisions holding that PR to the owner at the walkthrough, not to end the run. The ruling moves the PR — a code-changing one through *The summary can un-settle the run*, a charter hold through the release *PR promotion and central supervision* passes, a merge through *Frontier advance on merge* — and the frontier then continues to the dependents under those sections, in the same invocation. **Where nobody is present to rule**, the answer arrives outside a walkthrough: the check-in's reply watch (*Arming the wait when nothing is in flight*) releases dispatch only, so the PR moves at the next attended settle — or, where the answer is a recorded code-changing ruling at the item's site, through the `IN_FLIGHT_FIX` `summarize-wave` derives from it on the next settle. **Say that the settle is partial**: the settled report (Progress / checkpoint output) and the summary's action point for that PR (`summarize-wave`, *2. Action points*) both name, for each surfaced member, the planned work waiting on it.

Settled is not the same as finished. The run has produced everything it can **for now**; the next move belongs to the owner — a ruling on a surfaced member, or a merge — or to invariant 12's gate where a repository granted it — and when it is made, the run picks the work back up itself (see below).

On reaching settled:

1–7. run `settle-and-merge`'s sequence over this run's PR set (`settle-and-merge`, *The settle sequence*), passing it every input its *Inputs* names, as this run supplies them:
   - **PR set and scope**: the manifest/scope, and this run's PR set — which may be empty, where every issue blocked before creating a PR;
   - **findings**: the worker and review findings the run produced;
   - **held-reply records**: the approval-pending, rejected and mixed-thread records `supervise-prs`'s record holds; pass the held-reply outcomes `settle-and-merge` returns to `supervise-prs` as its *held-reply outcomes* input;
   - **posting-identity map**: the run's map (`references/posting-identity.md`);
   - **resolved policy**: `auto-merge` per PR and `auto-request-settle` for the run, as this run's preflight resolved them (`references/agent-policy.md`) — `auto-merge` off wherever *Model and skill policy* made the gate unreachable;
   - **ranking**: step 5 ranks, with each cross-branch collision this run found, marked independent where `artifact-collisions.md`, *Resolving a collision*, showed it, and the held issue set — anything classified `NEEDS_USER` for a resolved premise;
   - **dependency view, per PR**: the validated preflight's. For boundaries with a working dependency transport this costs the gate nothing new — an unproven boundary over dispatchable scope is a preflight `FAIL` that never reaches dispatch, and a proof invalidated mid-run raises the *unproven dependency view* `NEEDS_USER` the gate's outstanding-item test already refuses, and a frontier advance re-validates before anything new dispatches. `dependency transport unavailable` is passed as unproven on that boundary: proceedable for dispatch, not discharged for merge;
   - **freshness checks**: the stale-green re-check and its tool-bump rule apply, with authority to update a branch where the repository's checks run against the branch alone; and the integration check under *Cross-branch artifact collisions*, passed with its result, the head SHA of every branch it integrated, and the check itself, so the gate can re-run it where a tip has moved;
   - **publish rule**: `three-state`;
   - **outstanding recovery refs, per PR**: those the four-state ender under *Checkpoint compliance* leaves outstanding;
   - **un-settling**: nothing to pass; on a hand-back, *The summary can un-settle the run* and *A settle finding is the third repair shape* govern;

   at its step 1, **run step 11's release reconciliation in the same pass** — read the session list, archive every finished session the releasable test passes — so a run never settles, and possibly hands off, holding containers for work that is already on the remote; and take each merge it reports as a frontier-advancing event (Frontier advance on merge), passing the restacks it made to `supervise-prs` as caller pushes;
8. stop dispatching work, and stop spending tokens re-deriving the same state, for as long as nothing is dispatchable.

## The summary can un-settle the run

Settlement was computed before the summary existed, so the summary can falsify it. Branch on what it returns rather than proceeding to the ranking unconditionally:

| action point | effect |
|---|---|
| `IN_FLIGHT_FIX` | the wave is **not settled** — that PR has actionable work outstanding. Return it to supervision, dispatch it as a `finding` repair within the finding budget (see A settle finding is the third repair shape), and re-test the settled conditions before ranking |
| `MERGE_RISK` | still settled, but the ranking must carry it. Pass it to `plan-merge-order`, and raise it as a `NEEDS_USER` **item** where it blocks a merge decision outright — never an outcome for the PR, and a deferred repair already is such an item; a body drift never is one, since it holds only its own PR (`summarize-wave`, *2. Action points*) |
| `DECISION` | the settled step's walkthrough request (`settle-and-merge`, *The settle sequence*, step 4) is where it gets ruled when someone is present; unruled, pass to `plan-merge-order` and surface as `NEEDS_USER` — it gates a human, not the run |
| `NEW_ISSUE` | report it; no effect on settlement. No effect on ordering **unless the item carries an ordering consequence** — a follow-up that must land before one of this wave's PRs is also a `MERGE_RISK`, and takes that row too |

An `IN_FLIGHT_FIX` reaching the ranking is the same defect the settled conditions guard against: a table ordering PRs that are not finished is a table the user cannot act on.

## Settled is a resting state, not an exit

Settled means the run has nothing it can start *right now*, not that the run is over. Reaching it delivers the merge-order ranking; it does not close the invocation.

A settled run has no events of its own, so reaching settled is also the point at which it must arm its wake — a PR-activity subscription plus a scheduled check-in, or an honest restartable checkpoint if it can arm neither (see Arming the wait when nothing is in flight). Without it the run is not resting, it is asleep.

After the ranking is delivered, supervision continues for merge/close events and for the restack work a merge triggers — and a merge that advances the frontier, or a merge or close that frees a slot the cap was holding work behind, re-enters the dispatch loop automatically, under Frontier advance on merge, within the same run and with no new user prompt. Automatic continuation is the default; it yields only where this wave left a genuine ask outstanding that bears on the next wave, and then only for the paths that ask reaches. The run un-settles itself: recompute readiness, re-run the preflight at the mode the escalation rules select (where a trigger fires, after reading `deep-validation.md`), dispatch into free slots, and settle again when nothing is dispatchable. A wave can settle, advance, and settle again several times in one invocation.

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

If only external CI/review remains and the runtime cannot safely stay active, reconcile durable state and return a restartable checkpoint rather than pretending monitoring will continue. **Any return ends the watch**: unsubscribe every PR this run still holds and cancel its check-in (`references/platform-pr-posture.md`, *The watch ends with the run, not after it*); Restart / resume (`restart-resume.md`) re-arms at adoption.

# Progress / checkpoint output

**Emit the state block at the end of every supervision cycle** — a required step of the parent supervision loop (step 12), with a named actor and moment: this run, each cycle, including the one-PR supervision tail, which is the long part of a run and the part a compaction lands in. Emitting each cycle is what carries budgets, worker state and PR state across a compaction: a count that re-enters the transcript survives; one held in run memory does not. **Its fields, and those of the closing report, are `schemas/checkpoint-output.md`** — every block carries the check-in state with its id and next firing time, what woke this cycle, and the posture line with its override authority among them; read it before emitting the first one, and again whenever its fields are no longer in context. The rules for what they say are here.

**Every unmerged PR in the block names the gate condition holding it, by that condition's own name from the gate (`settle-and-merge`, *The merge gate*) — or is reported mergeable, or `gate not yet evaluated`.** Before `summarize-wave` runs, the gate's `DECISION` and `MERGE_RISK` inputs do not exist, so a PR with clean CI and a clean review has neither a known unmet condition nor the evidence to be called mergeable — the summary can still produce an item that holds it. **`gate not yet evaluated` is for a PR whose status actually turns on the missing summary outputs, and for nothing else.** Where a condition is already known to hold a PR before the summary — red CI, a conflict, an unresolved finding, an explicitly held draft, a repository that never opted in — name that condition, because it is true now and actionable now, and the summary cannot make it untrue. Only `mergeable` is genuinely unavailable pre-summary. One line each, naming the *first* unmet condition rather than a summary of the situation: `held by: 3 outstanding DECISION items`, `held by: CI red on <check>`, `held by: repository did not opt in`, `held by: explicitly held draft`. **"Awaiting merge", "pending" and "awaiting authorisation" are not reports about a gate** — they are compatible with every condition and with none, so nothing about them can be checked against what is actually true.

**The two merge routes are not the same authorisation.** `merge-stack` invoked on its own needs the user's authorisation; invariant 12's gate needs the repository's `auto-merge` opt-in and nothing else from the owner — and where that key is already `true`, there is no authorisation outstanding to ask about. Asking anyway is the failure *Autonomy and interactive prompts* names at the dispatch end of the run, arriving at the merge end instead.

Before returning, reconcile tracker + GitHub remote state and emit the closing report, per the same schema.
