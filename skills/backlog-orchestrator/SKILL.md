---
name: backlog-orchestrator
description: Autonomously executes a bounded dependency-linked implementation tranche from GitHub Issues, Linear, or another supported tracker. Can fan the implementation phase out onto a Claude Code Dynamic Workflow when the user opts into one, while preserving a validated issue DAG, Sonnet workers, isolated worktrees, durable remote checkpoints, stacked PR topology, centralized PR supervision, bounded repairs, and restart-safe tracker/GitHub state.
---

# Backlog Orchestrator

Execute a prepared implementation tranche autonomously.

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
- long-lived PR/CI/review supervision;
- repair dispatch;
- recovery and escalation.

It does **not** implement application code itself.

Reusable worker skills:

- `validate-backlog` — shallow/deep DAG validation;
- `implement-issue-core` — one issue -> code -> local checks -> remote checkpoints -> PR;
- `repair-pr` — one bounded CI or review repair pass;
- `create-pr` — issue linkage, stack metadata, PR creation, review trigger;
- `resolve-pr-comment` — thread-level review fix primitive;
- `summarize-tranche` — read-only short summary and action points for a settled tranche;
- `plan-merge-order` — read-only review/merge-order ranking for a settled tranche;
- `merge-stack` — separately authorized stack merge/restack workflow.

`implement-issue` remains the convenient standalone **single-issue orchestrator**. Do not replace it with this skill for normal one-ticket work.

# Core invariants

1. **Tracker + GitHub remote state are durable truth.** Conversation state, workflow state, and cloud worktrees are caches/conveniences, not the only source of truth.
2. **Canonical issue identity is the full issue URL.** Short keys/numbers are display helpers only.
3. **A run is bounded.** Never turn one build-order ticket into an open-ended project crawl.
4. **One implementation worker = one issue = one isolated checkout/worktree.**
5. **In-flight implementation is remotely checkpointed.** Significant completed work must not exist only in an ephemeral container.
6. **Sonnet is the default implementation/repair model.** Use the strongest available reasoning model for orchestration when appropriate.
7. **Only validated READY work is dispatched.**
8. **Execution dependency is not automatically Git ancestry.** Stack only where code ancestry requires it.
9. **The parent/orchestration layer owns long-lived PR state.** Implementation and repair workers are bounded and short-lived.
10. **Retries and repairs are bounded.** Persistent failure becomes `NEEDS_USER`.
11. **Recovery is idempotent.** Never duplicate work, branches, PRs, or repairs after restart.
12. **No automatic merges.** Merge authority is explicit and separate.

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
- `NEEDS_USER` after budgets are exhausted;
- a `FAIL` validation result leaving no safe independent path;
- a genuine conflict with no documented default, where every available option loses work that cannot be recreated.

Everything else belongs in the checkpoint output. A run that asks three questions before dispatching a single worker has already failed its main promise.

## Worker dispatch authority

A session may carry standing guidance not to use subagents or the Agent tool unless the user asked for them. Invoking this skill satisfies that guidance: fanning a validated issue set out to isolated one-issue workers is this skill's documented mechanism, so the invocation is the request. Dispatch subagent workers, create worktrees, and start worker sessions without a separate confirmation.

That authority covers worker dispatch only. It is not permission to merge, to widen scope beyond the bounded set, or to work around a platform-owned permission prompt.

# Execution runtime

The orchestration policy must be independent of the mechanism used to run workers.

## Preferred runtime: Claude Code Dynamic Workflows

A Dynamic Workflow is a JavaScript orchestration script that fans plain subagents out, runs them (up to 16 concurrent, capped at 1000 total) in the background, and returns only final agent results to the caller. It is well suited to the **bounded implementation fan-out** this skill dispatches — many independent, isolated one-issue-per-worker tasks — because that is exactly the "many small independent transformations" shape workflows are documented for.

When the user has opted into a workflow for this invocation (see Invocation above), use it **only for the implementation fan-out**:

- write the workflow script yourself so each `agent()` call's prompt/model explicitly encodes: exact authorized issue set and normalized dependency DAG (as separate fan-out stages honoring the DAG's ordering), Sonnet worker model, one issue per worker, isolated checkout/worktree per worker, exact calculated branch/base, remote checkpoint rules, retry budget;
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

Remote-session details worth not rediscovering each run: omit `environment_id` and the worker inherits this session's environment; `outcome_branch` is rejected unless `source_url` accompanies it; passing neither is valid, and the worker's prompt then pins the branch.

### Bounded runtime probing

A runtime that fails to start a worker gets **at most 2 attempts**, with a backoff measured in seconds, and is then unavailable — move down the chain. Varying arguments between attempts does not extend that budget: a service-side error (`temporarily unavailable`, 5xx) is not an argument problem, and a validation error names its own fix in one retry.

Do not spend an orchestration run diagnosing a runtime. Degrading to subagents and reporting the outage in the checkpoint output always beats a ten-minute retry loop before any work has started.

Also detect:

- native worktree isolation;
- whether Claude Code's own background PR watch/notification behavior is active for this session (see PR promotion and central supervision, below) — and, if so, whether its auto-merge behavior is enabled, since that would conflict with this skill's no-automatic-merge invariant and should be disabled or reported before autonomous work proceeds;
- local `git`;
- authenticated `gh`;
- GitHub MCP;
- tracker-specific tooling (for example Linear);
- installed required skills.

Prefer native/runtime capabilities when they implement the required behavior safely, but retain tracker + GitHub remote state as recovery truth.

# Tracker abstraction

Determine tracker from each canonical issue URL.

Primary supported trackers:

- GitHub Issues: `https://github.com/.../issues/...`
- Linear: `https://linear.app/.../issue/...`

Other trackers may be used only when reliable read/status/dependency support and PR-linking semantics exist.

Prefer tracker-native structured metadata where available:

- parent/sub-issue hierarchy;
- `blocked by` / `blocking` relationships;
- status/state;
- project/priority/build-order fields.

Also inspect descriptions/comments for explicit dependency language because textual dependencies may not yet have been normalized.

## Completion semantics

### GitHub

A correctly linked implementation PR uses a full-URL GitHub closing relationship. Treat issue closed + implementation PR merged as canonical `DONE`. If a correctly linked merged PR failed to auto-close due to unusual stack/base behavior, explicitly close only after verifying that exact PR implemented the issue.

### Linear

A PR must retain the full Linear issue URL and repository/workspace linking convention. Treat configured terminal Linear status + linked merged implementation PR as canonical `DONE`. Do not manually complete Linear issues unless workspace policy explicitly requires that fallback.

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

Before dispatching any **new** implementation worker, invoke `validate-backlog shallow` on the entire bounded scope.

Use the validator's normalized DAG as the scheduling graph. Do not let the execution runtime independently invent a competing decomposition.

Results:

- `PASS` -> proceed;
- `PASS_WITH_WARNINGS` -> proceed only where warnings do not make ordering unsafe;
- `FAIL` -> stop affected paths; continue only validator-confirmed independent safe branches.

Verify empirically any baseline a ticket tells workers to diff against — "~40 pre-existing type errors", "these tests already fail" — before it goes into a dispatch prompt. Tickets go stale, and a wrong baseline is worse than none: genuinely new failures hide inside an imaginary one.

Measure it at the parent level, but key it by **repository, base revision, and check** rather than broadcasting one number across the run. Workers in a fanout off a single base share a baseline; workers on stacked bases or in different repos do not, and handing them a number measured somewhere else reintroduces the same defect from the other direction — a real regression hidden inside a borrowed baseline, or a pre-existing failure reported as new. Measure once per distinct base, pass each worker only its own, and correct the ticket's claim in the checkpoint output.

Run repo-relative checks from the repo root. Ticket paths are repo-relative, so a `cd` partway through a validation sweep silently invalidates them.

Do not automatically mutate dependency metadata. GitHub normalization is handled separately by `normalize-github-dependencies` when requested.

`validate-backlog deep` is optional/user-invoked because it can consume materially more model/code-reading budget.

# Default usage safeguards

Unless explicitly overridden:

- maximum concurrent implementation workers: **4**;
- maximum newly started issues per invocation: **12**;
- maximum implementation attempts per issue: **2 total**;
- maximum strongest-model escalation per issue: **1**;
- maximum CI repair cycles per PR: **2**;
- maximum review-fix cycles per PR: **2**;
- maximum lost-worker redispatches per issue: **1**;
- automatic merges: **disabled**.

Dynamic Workflows do not override these limits. Do not increase concurrency merely because the runtime can fan out more agents.

The concurrency number is a ceiling, not a target. Derive the level you actually run from machine capacity at startup — available CPUs, free disk against the container's fixed allowance, and whether each worker needs its own dependency install or test toolchain — and take the lower of the two. Decide that yourself and report it; do not ask.

When the bounded scope exceeds the 12-new-issue limit, do not ask which issues to drop. Start the first 12 in scheduling order — DAG readiness first, then how much downstream work each unblocks — and defer the rest, naming the deferred issues in the checkpoint output so the next invocation adopts them. A user who wants a different cap says so in the invocation.

When the 12-new-issue limit is reached, allow active workers/repairs to reach durable state, stop starting new issues, reconcile, and return a checkpoint. Restarting does not count already-adopted work as newly started.

Budget exhaustion on a node -> `NEEDS_USER`, not another speculative attempt. Continue unrelated DAG branches safely.

# Model and skill policy

The orchestration/lead context may use the strongest available reasoning model.

Normal implementation and repair workers must use **Sonnet explicitly** when the runtime supports per-worker model selection. Do not accidentally inherit the lead's stronger model.

At most one strongest-model implementation escalation is allowed for a reasoning-heavy repeated failure.

Implementation workers require `implement-issue-core` and `create-pr`.
Repair workers require `repair-pr` and, for review fixes, `resolve-pr-comment`.
The parent layer requires `validate-backlog` at preflight, and `summarize-tranche` followed by `plan-merge-order` when the run settles.

Workers must inherit/preload the active installed skills. If a required skill is unavailable, return `BLOCKED` rather than improvising a replacement workflow.

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
- `NEEDS_USER`
- `NOT_READY`

Prefer durable evidence in this order:

1. merged linked implementation PR + tracker terminal state;
2. open linked implementation PR;
3. remote issue branch with pushed checkpoints;
4. runtime/workflow-local state;
5. local worktree only.

A cloud worktree is ephemeral. Never claim restart safety for unpushed local changes.

## Restart / resume

A Dynamic Workflow interrupted by session exit restarts fresh next session rather than resuming — it has no cross-session persistence of its own. Restart recovery therefore always comes from tracker + GitHub remote state, never from workflow-runtime state:

1. re-expand the exact same bounded manifest/scope;
2. rerun `validate-backlog shallow`;
3. order by normalized DAG + explicit build order;
4. fetch current tracker statuses, PRs, and remote branches;
5. skip every proven `DONE` issue;
6. adopt existing open PRs;
7. adopt matching remote issue branches/checkpoints even when no PR exists yet;
8. identify the earliest still-unfinished executable frontier;
9. resume there, dispatching fresh workers (in a new Dynamic Workflow fan-out if the user re-opts in, or via the fallback runtime chain) for whatever is not yet durable.

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
6. compose the dispatch prompt so it carries every default the worker skills already own;
7. dispatch Sonnet worker with `implement-issue-core`.

A dispatch prompt that enumerates a required process is followed literally: a default left out of that enumeration is a default skipped, and the worker will accurately report that the task never asked for it. Every dispatched prompt must therefore carry the automated review trigger instruction — `create-pr` owns the trigger rules, do not restate them here — unless this run explicitly defers review. Deferral is a conscious choice recorded in run state, naming what review is owed and on which PRs; it is never an omission.

Issuing the trigger is not the end of that step. Confirm it took effect: a review from the repository's automated reviewer materializes within a bounded window, and the reviewer does not instead answer indicating it is not configured or not authorized. Verify per attempt, on every PR — one review arriving elsewhere in the run is not evidence the trigger works. A trigger that silently no-ops is worse than one that fails loudly, because the run then reports PRs as reviewed and clean when nothing reviewed them.

An elapsed window is not a refusal. A reviewer that is merely queued or slow leaves the PR unreviewed-pending, reconciled through ordinary event supervision and visible as such in checkpoint output; only an explicit not-configured/not-authorized response marks the trigger unavailable.

A refusal is first evidence of the wrong write path, not of insufficient authority. Where the platform offers more than one way to perform the write, reissue the trigger once through a different available mechanism before drawing any conclusion. Where the platform exposes only one write mechanism, the available paths are already exhausted. Do not otherwise repeat the same write path: it will not start working on the next PR, and each failed attempt leaves trigger and refusal comments behind on the PR.

Only once every available path has failed, record it as `NEEDS_USER`: surface once, with the affected PRs, that review could not be triggered, and stop issuing the trigger for the remainder of the run in that repository. One escalation per affected repository, not one per PR; suppression is scoped to the repository that refused, because review configuration is repository-specific. Never conclude from a refusal alone that review cannot be triggered from this run at all — that conclusion is cheap to draw, hard to disprove afterwards, and costs precisely the reviews it skips.

This generalizes past review triggers. When the platform offers several ways to perform the same write, prefer its first-class integration tooling over raw transport: attribution, permissions, and downstream automation can all differ between them, and the difference is invisible until a write is made and read back. Where identity matters to a workflow, verify it by inspecting an object the run actually created and reading its author — never by asking the credential who it is, which can answer differently from what its writes carry.

Under Dynamic Workflows, provide these constraints to every workflow worker explicitly. Do not let a worker select another backlog ticket when it finishes.

## Shared environment

Filesystem isolation is necessary but not sufficient. Workers with private checkouts still contend over shared mutable resources — a shared backing service instance, a fixed port, a shared cache or state directory, one set of credentials, a single external sandbox account.

At startup, enumerate the shared mutable resources workers in this run will contend for. That inventory is repository- and environment-specific: take it from repository configuration (`CLAUDE.md`/`AGENTS.md`, the session startup hook, the environment manifest), never from assumption. If a rule cannot be expressed without naming a concrete technology, it belongs in that configuration, not here.

For each enumerated resource, either give every worker its own namespace/instance, or serialize access to it. If neither is possible, serialize the affected workers.

Pass the resolved access details explicitly in each dispatch prompt so no worker has to guess them. A worker that guesses wrong reports failures that are not real.

Standing rule in every dispatch prompt: never stop, reset, reconfigure, or clean up a concurrently shared resource — a sibling worker may be using it. A worker holding serialized exclusive access may perform the lifecycle operations the repository's own configuration sanctions, since nothing else holds the resource during its turn.

## Remote checkpoint requirement

`implement-issue-core` must:

1. push the issue branch early so it has remote identity;
2. commit/push meaningful coherent checkpoints during substantial implementation;
3. push final implementation state before returning;
4. create/verify the PR;
5. return remote branch/PR/head SHA.

Do not create meaningless checkpoint commits merely as heartbeat activity. Checkpoint after meaningful completed work so container loss discards only the most recent unfinished chunk.

Treat all five as best-effort on the worker's part. They belong in every dispatch prompt, but do not count them as satisfied because they were instructed — Checkpoint compliance below is what actually enforces them.

# PR promotion and central supervision

A PR opened by a worker may be surfaced back to the parent/top-level session by Claude Code's own background PR watch/notification behavior (a session-level feature, distinct from Dynamic Workflows — a Dynamic Workflow run does not itself persist or surface PR/CI/review events once it returns its fan-out results) or by an explicit event subscription such as `subscribe_pr_activity`. **Use that platform PR state when available.** Do not create a duplicate monitor merely because the PR originated in a child worker.

If Claude Code's background PR behavior has auto-merge enabled, it will merge PRs itself once checks pass — this conflicts directly with this skill's no-automatic-merge invariant. Confirm auto-merge is off (or explicitly authorized by the user for this run) before relying on that background behavior for CI/review surfacing.

Once an implementation worker reaches `PR_OPEN`, release that implementation worker. Long-lived PR supervision belongs to the parent/runtime orchestration layer.

For every active PR track:

```text
canonical issue URL
tracker
PR URL
branch/base
remote head SHA
CI state
review state
review trigger: issued/verified/pending/unavailable
first review round: pending/complete-with-findings/clean
draft state: as-created -> current
CI repair cycles used/remaining
review repair cycles used/remaining
stack parent/children
```

## Event handling

Prefer platform-native/promoted PR events (Claude Code's background PR watch behavior, or an explicit subscription such as `subscribe_pr_activity`) for:

- CI/check completion/failure;
- review/comment activity;
- branch/head changes;
- merge/close events.

If those are unavailable, fall back to other event subscriptions, then bounded parent polling.

The parent remains the **policy owner** even when the platform performs the observation. The platform may surface that CI failed or review feedback arrived; this skill decides whether budgets allow repair and what worker to dispatch.

Do not keep one Sonnet worker alive per PR merely to wait.

# CI/review repair

On an actionable CI failure:

1. retrieve the smallest useful failure context;
2. decide whether it belongs to this PR;
3. if repair is justified and budget remains, allocate an isolated checkout of the current PR branch;
4. dispatch one Sonnet `repair-pr` worker with `repair type = ci`;
5. adopt its pushed remote head;
6. increment the CI repair cycle;
7. release the repair worker and resume event supervision.

External/flaky failure with no justified code change does not consume a repair cycle.

On actionable review feedback:

1. group the coherent current review round;
2. if budget remains, allocate an isolated checkout of the current PR branch;
3. dispatch one Sonnet `repair-pr` worker with `repair type = review`;
4. `repair-pr` uses `resolve-pr-comment` where relevant;
5. adopt the new remote head and increment review cycle;
6. retrigger/request review when repo convention requires it, unless review is still deferred for this PR or triggering was suppressed for this run;
7. release worker and resume event supervision.

Review feedback may reference a head already superseded by a rebase/restack. Locate each finding by content rather than line number, and confirm it still applies to the current head before repairing.

Product/architecture judgment -> `NEEDS_USER` rather than speculative repair.

A PR branch may have only **one active mutating worker** at a time. Before repair, verify the remote head has not moved unexpectedly.

## Mechanical pushes do not consume review

A restack, or a renumber/regeneration of a claimed artifact, moves identity or ordering rather than behavior. Such a push:

- does not consume a review repair cycle;
- does not re-trigger automated review;
- does not reset the PR's reviewed state or its eligibility for draft promotion.

The repository's deterministic checks are what validate it. Where the repository has no check that would catch a bad renumber, treat the push as substantive instead — `create-pr` carries the full test for which is which.

This matters most right after a sibling merges. Descendants restack and claimed artifacts renumber for reasons that have nothing to do with their own diffs, and re-reviewing every one of them spends the review budget on code that did not change.

## Draft promotion after a clean first review

A PR opened as a draft is signalling "not finished yet". Once its **first** automated review round has completed and every actionable finding from it is resolved, that signal is stale and the PR should be marked ready for review.

Promote when all of these hold:

- the PR was created as a draft by this run (`create-pr` reports its as-created draft state);
- the automated review trigger was issued and a review round actually came back — a review that was deferred, suppressed, or never fired is not a completed round;
- no actionable finding from that round is unresolved, whether it was fixed, or answered with a reply explaining why no change is warranted;
- CI is green on the current remote head;
- the PR is not `NEEDS_USER` and has no unanswered product/architecture question.

Then mark the PR ready for review once, and record the transition in the per-PR state.

Rules:

- Promote at most once per PR. Never flip a PR back to draft, and never re-promote one a human returned to draft.
- Never promote a PR this run did not open.
- Repository convention or an explicit user instruction to keep PRs in draft overrides this, as does a caller passing an explicit draft preference through `implement-issue-core`.
- Later review rounds do not re-trigger promotion; the PR is already ready.
- Promotion is not merge authorization and does not interact with invariant 12. It changes the PR's review-readiness signal and nothing else.

A repair worker never promotes. `repair-pr` reports how many actionable threads remain unresolved; this parent layer owns the decision.

# Parent supervision loop

Long-lived PR/CI/review supervision always runs in this parent loop, never inside a Dynamic Workflow: a workflow run accepts no external input once started and does not persist past the current Claude Code session, so it cannot sit and wait across hours/days for CI or review to come back. This holds even for a run whose implementation fan-out did execute inside a Dynamic Workflow — once that workflow returns its worker results (PR URLs, branches, heads), supervision reverts to this same parent loop.

The main parent thread must remain active while mutating workers run or active PR events can lead to more in-scope work.

Each cycle performs real work:

1. consume worker completions (including a Dynamic Workflow's returned fan-out results, if one was used);
2. reconcile tracker + remote branches/PRs;
3. consume/reconcile CI/review events;
4. update heads/budgets;
5. dispatch repairs;
6. recompute READY frontier;
7. fill available worker slots (optionally via a fresh Dynamic Workflow fan-out if the user re-opts in for the next batch);
8. inspect stack ancestry changes;
9. inspect every in-flight worktree for uncommitted work and enforce checkpoints (see Checkpoint compliance — this is a mandatory step, and the parent commits on the worker's behalf when a nudge has already failed);
10. re-check disk/slot capacity;
11. check sibling branches for colliding added or modified claimed artifacts;
12. surface `NEEDS_USER`;
13. wait using native task/event wait, then repeat.

Do not use CPU loops, file-touch loops, detached sleeps, meaningless commits, or other fake activity solely to prevent idling.

Remote Git checkpoints remain mandatory regardless of runtime, because no platform/runtime persistence substitutes for durable source control.

## Verifying worker reports

A worker's reported check results are a claim about its own environment, which may be misconfigured in ways the worker cannot see. Before relaying or acting on reported results, verify them against durable evidence: CI on the pushed head, or a re-run outside that worker's environment. Never escalate a worker-reported mass failure to the user, or block a merge decision on it, unverified.

## Checkpoint compliance

**Assume the checkpoint instruction will not land.** Across observed runs, workers hold completed work uncommitted at a high rate — including workers whose dispatch prompt explicitly told them to push before running checks. Sonnet workers treat committing as something that follows green checks rather than something that protects work in progress, and no amount of prompt emphasis has reliably changed that. Parent-side verification, not the worker's instructions, is what actually satisfies invariant 5.

So this is a step of every supervision cycle, not a periodic spot check, and it observes three things per in-flight worker — the worktree, the local branch, and the remote:

| worktree | local vs. tracked remote | state | action |
|---|---|---|---|
| dirty | — | completed edits exist only on disk | capture, below |
| clean | local ahead | committed, push failed or was deferred | push the stranded commits |
| clean | level | nothing saved yet | leave alone unless dispatch was long ago |

A remote head that has not advanced tells you nothing arrived; it cannot distinguish a worker still reading code from a worker sitting on eight finished files. Only the worktree separates those. And a clean worktree is not proof of durability on its own: a worker that committed but whose push failed leaves `git status` clean while the remote stays put, so the local/remote comparison is what catches that case. Pushing stranded commits is always safe against a live worker — it touches neither its index nor its working tree.

### Enforce, do not re-ask

On first observing uncommitted completed work, instruct that worker to commit and push immediately. If the next cycle still shows it uncommitted, the parent captures the work itself rather than nudging again: a second nudge is evidence the instruction is not landing, and the parent already holds worktree path, branch and base in the tracking record.

**Capture without racing the worker.** A live worker owns its index and `HEAD`, and the shared-resource rule above applies to its own checkout as much as to a service — two actors staging into one `.git/index` can capture a half-written tree, or make each other's commits fail. So never run `git add` in a live worker's index. Either:

- **live worker** — build the commit **ref-neutrally** and push it to a **recovery ref**, never to the issue branch:

  ```bash
  GIT_INDEX_FILE=<scratch> git -C <worktree> read-tree <worker-head-sha>   # seed first
  GIT_INDEX_FILE=<scratch> git -C <worktree> add -- <issue-owned paths>
  GIT_INDEX_FILE=<scratch> git -C <worktree> write-tree                    # -> <tree>
  git -C <worktree> commit-tree <tree> -p <worker-head-sha> \
      -m "wip: parent checkpoint capture"                                  # -> <commit>
  git -C <worktree> push origin <commit>:refs/checkpoints/<issue-branch>/<commit>
  ```

  Every line is load-bearing. `read-tree` **must** come first: a scratch index starts empty, so `add` on a path list would produce a tree containing only those paths, and a commit parented on the worker's head then records every other file in the repository as a deletion — recovery merging that checkpoint would delete most of the repo. Seed from the worker's head, then overlay the issue-owned paths. `GIT_INDEX_FILE` isolates the index and nothing else, so plain `git commit` would still advance whatever ref `HEAD` names — the worker's branch — reintroducing the race this avoids; `commit-tree` writes a commit attached to no ref, so nothing the worker holds moves.

  Verify a capture by diffing it **against its parent**, not by confirming the work is present: `git diff-tree -r --name-status <worker-head-sha> <commit>` must show only the paths you intended. Content being present says nothing about what else the tree dropped, and that is the failure mode this sequence had;
- **wedged worker** — stop it first, then commit normally onto the issue branch in the now-quiesced worktree. Stopping consumes that issue's lost-worker budget, so it needs the same evidence any redispatch does.

The issue branch has exactly one writer at a time, and while a worker lives that writer is the worker — locally as well as remotely. Advancing either end underneath it is not a neutral act even when its index and worktree are untouched: its next push becomes a non-fast-forward rejection, and a worker that reacts by force-pushing destroys the snapshot that was protecting it. A recovery ref buys durability without a second writer. Making the worker fetch and reconcile instead would put the fix back in the worker's hands — the same hands that did not commit when told to.

The general rule behind all three cases: **capture must not move any ref the worker holds.** Test a proposed capture against that before running it, because several plausible sequences violate it silently — the index, the branch, and `HEAD` each have to be checked separately.

Once the worker pushes its own commit covering that work, its recovery refs are redundant; drop them when the PR reaches durable state. Lost-worker recovery reads them.

A snapshot that caught a file mid-write is still worth having: it is a WIP checkpoint, never the PR's final state, and a partial save beats an empty branch. Prefer the worker doing its own commit precisely because it has no such hazard — parent capture is the fallback, not the mechanism.

Securing a worker's work never waits on that worker finishing. A worker mid-check with completed edits uncommitted is the highest-risk state in the run, because a long check is exactly when a container is most likely to disappear.

### Where the parent cannot reach

This contract assumes the parent can see a worker's checkout and send it an instruction. That holds for subagents in parent-created worktrees and for remote worker sessions, and **not** for a Dynamic Workflow fan-out: workflow agents accept no input mid-run, and the worktrees the runtime creates for them are not paths the parent was given. Neither half of the escalation above is available there.

So under a Dynamic Workflow, enforcement has to be structural — encoded in the script's control flow, which is deterministic, rather than in an agent prompt, which is the thing that does not land.

**Checkpoint granularity equals stage granularity.** A script can only interpose where it has a stage boundary, so a single checkpoint stage after implementation is not a checkpoint at all — it is the final push, which the worker was going to make anyway. If implementation hangs or the container dies inside that one long stage, the stage never returns and nothing was saved. Bounded loss requires implementation split into several bounded stages, each ending with a push: the number of boundaries is the granularity, and one boundary at the end is none.

That only works where the issue's work decomposes into units the script can name in advance — per-file tranches, per-module conversions, work already sliced by the ticket. Where it does not, the workflow runtime **cannot** satisfy invariant 5 for that issue, and no arrangement of stages changes that.

So the runtime preference is conditional, not absolute. A Dynamic Workflow suits the fan-out shape, but invariant 5 outranks that convenience: prefer a runtime whose workers the parent can reach whenever the implementation cannot be staged into script-visible units. Unreachable-mid-run is a real cost of the workflow runtime, the same one that already disqualifies it for PR supervision — this is the second thing it cannot do, not a footnote on the first.

## Capacity during the run

Re-check disk headroom and worker-slot capacity each cycle, not only at dispatch. Worktrees, dependency installs, and build caches accumulate as the run proceeds, so startup headroom does not predict headroom at the fifth concurrent worker. Report the current figure with the worker count in the checkpoint output, and stop filling slots before exhaustion rather than after a write fails.

## Cross-branch artifact collisions

After each PR reaches durable state, compare it against sibling branches in the same run and flag two things: files that two branches both **add** under the same name or sequence number, and incompatible edits two branches make to a shared claimed artifact — a generated manifest, lockfile, registry or index that branches amend rather than create, and which therefore collides with no added path in common. The general class is any artifact whose identity or ordering is claimed rather than derived.

Two chains cut from the same base can each be internally consistent and both pass CI while colliding, because neither can see the other; the conflict only materializes when the second one merges. Dependency edges and stack ancestry do not detect this — the branches are siblings, not ancestors.

Correct resolution depends on merge order, which this skill does not own. Surface the collision as `NEEDS_USER` with both PR URLs and the colliding paths. Never renumber or rewrite the artifact pre-emptively.

# Lost worker / workflow recovery

A worker whose remote branch never advanced is the expensive case; prefer catching it through the checkpoint-compliance check above, before it is lost.

If a worker disappears:

1. inspect remote branch/PR first;
2. inspect any recovery refs the parent pushed for that issue (see Checkpoint compliance) — work captured from a live worker lives there, not on the issue branch;
3. inspect local worktree only if the container still exists;
4. adopt pushed checkpoints/PR, merging a recovery ref into the issue branch where it holds work the branch does not;
5. redispatch at most once from latest durable remote checkpoint;
6. repeated loss -> `NEEDS_USER`/infrastructure failure.

If the whole cloud container/workflow disappears, assume local worktrees are lost. Resume from remote branches/PRs plus tracker state.

Never double-apply a repair already pushed by a worker whose runtime status was lost.

# Stack mutation while PRs are open

When an upstream stack branch changes, descendants may become `STACK_STALE`.

Do not blindly restack every descendant after every upstream push. Instead:

- record stale ancestry;
- restack before descendant diffs/CI/review become misleading;
- ensure ancestry is correct before merge-ready state;
- treat a restack-only push as mechanical (see above): no review re-trigger, no cycle consumed;
- use `merge-stack` for authorized merge/restack operations;
- reconcile new remote heads before dispatching further repairs.

# Outcomes

- `PR_OPEN` — implementation reached durable remote PR state; parent/runtime owns supervision.
- `BLOCKED` / `BLOCKED_EXTERNAL` — stop affected path; never silently enlarge scope.
- `FAILED` — retry only inside budgets; at most one reasoning escalation.
- `NEEDS_USER` — surface full issue/PR URLs, failure/review state, attempts consumed, and recommended action; stop spending tokens on that node while continuing safe independent branches.

# Merge behavior

Normal orchestration never merges automatically.

If the user separately authorizes `merge-stack`, that skill owns merge ordering and descendant rebasing/restacking. Reconcile tracker completion after every merge.

# Settled tranche

A run is **settled** when no further implementation can start and every open PR is individually finished:

- no in-scope issue is READY — each unstarted issue is blocked by work that is implemented but unmerged;
- no implementation or repair worker is in flight;
- every open PR from this run has had at least one **completed** automated review round, not merely a trigger issued;
- every actionable review finding on every open PR is resolved or answered;
- no open PR is `NEEDS_USER` or waiting on CI.

Settled is not the same as finished. The run has produced everything it can; the remaining move belongs to whoever holds merge authority.

On reaching settled:

1. reconcile tracker + remote state one final time, so both the summary and the ranking are computed from durable truth rather than cached run state;
2. invoke `summarize-tranche` with the manifest/scope, this run's PR set, and the worker/review findings it produced;
3. **act on its action points before ranking anything** (below);
4. invoke `plan-merge-order` with the manifest/scope, this run's PR set, and any `MERGE_RISK`/`DECISION` items the summary produced, so the ranking is computed against those constraints rather than around them;
5. surface the summary and action points first, then the ranking table, as the run's closing output;
6. stop dispatching work and stop spending tokens re-deriving the same state.

Summarize before ranking. An action point can change whether something should merge at all, and a ranking the user has already begun acting on is the wrong place to discover that. Run the summary once per settled tranche rather than saving one up for the end of a whole backlog: its findings come from run context that the next session will not have, and follow-ups need to exist while later tranches are still running, so they get picked up instead of rediscovered.

## The summary can un-settle the run

Settlement was computed before the summary existed, so the summary is capable of falsifying it. Branch on what it returns rather than proceeding to the ranking unconditionally:

| action point | effect |
|---|---|
| `IN_FLIGHT_FIX` | the tranche is **not settled** — that PR has actionable work outstanding. Return it to supervision, dispatch the repair within budget, and re-test the settled conditions before ranking |
| `MERGE_RISK` | still settled, but the ranking must carry it. Pass it to `plan-merge-order`, and raise it as `NEEDS_USER` where it blocks a merge decision outright |
| `DECISION` | pass to `plan-merge-order` and surface as `NEEDS_USER`; it gates a human, not the run |
| `NEW_ISSUE` | no effect on settlement or ordering — report it |

An `IN_FLIGHT_FIX` reaching the ranking is the same defect the settled conditions already guard against: a table that orders PRs which are not actually finished is a table the user cannot act on. Finding it one step later does not make it acceptable.

Do not merge, and do not treat the ranking as authorization to merge — invariant 12 still holds.

If a run reaches all other settled conditions but some PR still has an unresolved finding, an unfired review, or red CI, it is **not** settled. Finish that PR within budget, or surface it as `NEEDS_USER`, before ranking. Ranking PRs that are not actually finished produces a merge order the user cannot act on.

After the ranking is delivered, supervision continues only for merge/close events and for the restack work a merge triggers. Re-run `plan-merge-order` when merges change the graph enough that the previous ordering is stale.

# Stop conditions

Stop starting new implementation work when:

- all in-scope issues reached requested durable state;
- the run is settled (see above) and the merge-order ranking has been delivered;
- the 12-new-issue budget is reached;
- all remaining paths are blocked/`NEEDS_USER`;
- the user asks to stop;
- safety approval is required;
- infrastructure/runtime repeatedly fails.

If only external CI/review remains and the runtime cannot safely stay active, reconcile durable state and return a restartable checkpoint rather than pretending monitoring will continue.

# Progress / checkpoint output

Keep concise state, for example:

```text
Runtime: Dynamic Workflow
Manifest: <full URL>
Validation: PASS
Scope: 18 issues
Run budget: 9/12 newly started
Implementation workers: 3
Repair workers: 1
Active PRs: 7
Waiting CI/review: 4
Unreviewed (trigger pending/unavailable): 0
Unresolved review findings: 0
Drafts promoted to ready: 2
Ready: 3
Blocked: 2
Needs user: 1
Resume frontier: <full URL(s)>
```

Before returning, reconcile tracker + GitHub remote state and report:

- runtime used, plus any runtime probed and rejected, with the reason;
- documented defaults applied without asking — branch-mandate override, issues deferred at the budget cap, concurrency reduced for machine capacity, corrected ticket baselines;
- validation result/warnings;
- manifest/scope;
- resume frontier;
- PRs + stack topology;
- remote checkpoint branches without PRs;
- checkpoint enforcement: workers nudged, and workers whose work the parent committed itself;
- disk headroom against the concurrent worker count;
- CI/review states + repair budgets consumed;
- PRs left unreviewed, and whether the review trigger was deferred or unavailable;
- PRs promoted from draft to ready, and any left in draft with the reason;
- the `summarize-tranche` summary and action points, and the `plan-merge-order` table, when the run settled;
- issue-linkage/tracker-status inconsistencies;
- `NEEDS_USER` items;
- external blockers;
- unstarted work and why;
- whether invoking the same manifest can safely resume.
