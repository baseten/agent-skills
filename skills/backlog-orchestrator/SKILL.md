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
- `NEEDS_USER` after budgets are exhausted, or one that leaves no dispatchable work at all — the same shape as the `FAIL` case below. Every other `NEEDS_USER` is surfaced in the closing output instead of asked mid-run, including a dependency measure the run cannot observe and the summary's `DECISION`/`MERGE_RISK` escalations: those need a person eventually, not now, and the run still has work to do meanwhile;
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

### Releasing a worker

"Release the worker" appears throughout this document — at `PR_OPEN`, after every repair — and it names a different act on every tier, so it is defined here beside the tiers rather than at each call site:

| runtime | what releasing is |
|---|---|
| Dynamic Workflow agent | nothing to do — the runtime reclaims the agent when the workflow returns |
| remote worker session | **archive the session.** A live one holds a container, a session-list entry, and whatever permission prompt it may be sitting on |
| in-process subagent | stop messaging it; there is no resource to reclaim |
| serialized execution | nothing to do — there was never a second actor |

The first and third rows are why the second needed writing down. On two of the four tiers release *is* the absence of an action, so a reader generalizing from those reads "release the worker" as a remark about attention rather than an instruction — and on the tier this run most often degrades to, the same words name a real resource that then leaks silently. Nine finished worker sessions still holding containers after a run, found by the user in a session list rather than by the run in its own report, is what that reads like from outside.

**The releasable test, stated once and referenced everywhere else that needs it.** Restating it in situ is how successive versions of it came to disagree about the same worker — every review round this section has had found one such disagreement, each introduced by the fix for the last. A second copy of this test appearing anywhere is the regression to look for.

A worker is releasable when both hold, and not before:

1. **it is done** — either of:
   - it **returned a terminal outcome**, any of them and not only the successful ones. `implement-issue-core` ends on `BLOCKED`, `BLOCKED_EXTERNAL`, `FAILED` and `NEEDS_USER` exactly as it ends on `PR_OPEN`; `repair-pr` ends on `NO_CODE_CHANGE`, `FAILED` and `NEEDS_USER` exactly as it ends on `REPAIRED`. A repair worker that correctly classified a CI failure as external returns `NO_CODE_CHANGE` with an unchanged head and nothing to push, and is as done as one that pushed a fix. Releasing only on the two successful outcomes leaks every session whose worker did its job and had nothing to show for it, which a run dispatching into a wrong graph produces in bulk;
   - or its **work reached durable remote state and it is now blocked on a prompt this run does not need answered**. No outcome arrives in this case because the prompt is what stops it arriving, and waiting for one strands the session forever.

     **That last qualifier is load-bearing, not throat-clearing.** A pushed branch, an existing PR and a clean worktree do not by themselves mean the worker is finished: `create-pr` verifies tracker linkage and issues the automated review trigger *after* creating the PR, so a worker blocked on either of those is stopped mid-deliverable rather than tidying up behind one. Archiving it there leaves a PR that is unlinked or never reviewed while the run records the issue as complete — the coverage failure this document spends a section on, arrived at through cleanup. Cleanup the run does not need — disarming a wake the worker should never have armed — releases it. Anything the deliverable still depends on takes the parent's-clear or `NEEDS_USER` branches under Blocked workers instead;
2. **nothing is stranded in its worktree** — which no outcome label can speak to, and which Checkpoint compliance is what establishes.

**Durable remote state** means the branch is pushed and a PR exists for it. **The PR's own state is irrelevant** — open, merged, or closed. Merged is the *common* case here rather than an edge one: a wake armed at PR creation outlives the PR that armed it, so by the time anyone notices the blocked session the work has usually landed. The session that prompted all of this had merged hours before it was found. Any test that requires the PR still be open excludes precisely the deadlock this section exists for.

A session merely reading `IDLE` asserts neither condition: idle is also what a worker looks like when it finished editing and never committed — the state Checkpoint compliance exists to catch, because workers reliably reach it.

And a worker that has not returned an outcome is not therefore lost. It is one of three things, and only the last is:

| state | who owns it |
|---|---|
| stopped on a prompt | Blocked workers — released by the test above, cleared, or raised as `NEEDS_USER` |
| still working | nobody yet — leave it and re-check next cycle |
| unreachable | Lost worker / workflow recovery |

The ordering between the two conditions is fixed rather than incidental: the checkpoint-compliance step of the supervision cycle runs first, and a session is archived only once the worktree it holds has no uncommitted work left in it. Archiving first destroys the container and the only copy of that work together, and the check that would have caught it no longer has anything to look at.

Two things are never archived. A **`RUNNING`** session — a worker that must be stopped is interrupted first, which consumes that issue's lost-worker budget and needs the same evidence any redispatch does (see Checkpoint compliance), and is archived only after its work is captured. And a session **this run did not create** — the user's own sessions from every other surface share that list, and none of them are this run's to reclaim.

## Transport precedence

The detection above establishes what exists. This establishes which one to use. For every tracker/forge read and write, in order:

1. a first-class MCP tool for that operation, where one exists;
2. an authenticated CLI (`gh`, `linear`, equivalent) when running locally under the user's own credential;
3. raw HTTP against the API, only where neither of the above exposes the operation at all.

Raw HTTP is a last resort, not a default. Reaching for it must be a decision you record — which operation, and why no higher tier exposes it — not an accident of habit because `curl` is familiar and always available.

Precedence lowers the odds of a partial view; it does not remove the need to check for one. A first-class tool or a CLI can run on a directly scoped credential and under-report just as quietly as a relayed one — the hazard is the **scope of the credential**, not the shape of the transport. So treat every relationship read as **provisional until validated below, whichever tier produced it**, and spend the extra scepticism on raw HTTP rather than reserving it for raw HTTP.

## Proving a transport can see the graph

Before a run depends on **relationship data** — dependency edges, hierarchy, cross-repository links, anything a server can legitimately return in part — prove the chosen transport can see it, using a case whose answer is already known: an edge this run just wrote, or one the user confirmed.

A relayed, proxied, scoped, or short-lived credential can return a truthful-looking partial result. The server answers correctly for the credential it was actually given, and entries outside that credential's reach are simply absent: 200, no error, no warning, fewer rows. A credential scoped per repository returns a single repository's worth of a graph that spans several, and nothing in the response says so. This is not specific to any tracker, forge, or hosting arrangement — it follows from scoping a credential, so assume any transport can do it.

**Independence is a property of the credential, not of the transport.** A second endpoint behind the same credential reproduces the same blind spot and reads as confirmation, which is worse than a single read because it manufactures confidence — and two *different* transports do this too whenever they authenticate the same way. `gh` and raw HTTP both reading `GITHUB_TOKEN` are one observation wearing two coats, and the precedence list above makes that the common case rather than the exotic one.

So corroborate in this order:

1. **a known-true case** — an edge this run just wrote, or one the user confirmed. Strongest, because its answer does not depend on any transport being trustworthy;
2. **a second read** — corroborating at best, never proving. A different identity or token source is worth having, but two credentials can share insufficient scopes, a repository boundary, or a relationship transport, and every distinguishing feature offered so far has turned out able to coincide with a shared blind spot. Agreement between two reads narrows nothing on its own;
3. **no known-true case available** — that is the finding. Report the boundary as unproven rather than promoting agreement into a proof.

**Enumerating the bounded scope is itself one of these reads.** A manifest or parent issue is expanded through native hierarchy, so a credential that hides children in one repository produces a truncated scope — and the boundary list derived from that scope omits the very repository that was hidden, so nothing ever tests it. A scope obtained from a possibly-partial read cannot bound its own validation. Draw the boundary list from something independent of the enumeration: the issue set the user supplied, the manifest's own prose listing of its children, or a second enumeration. Note the asymmetry, because it is what makes a second enumeration worth running at all: **a differing count is the finding, and a matching count proves nothing** unless one of the two enumerations had proven visibility. Two reads that share a blind spot agree precisely about what they cannot see.

**The control must match the shape of what the run consumes.** A credential scoped per repository reads a known edge inside one repository perfectly well while omitting every relationship that touches another — so a control drawn from a single repository proves visibility for that repository and nothing else. Cover each scope boundary the graph actually crosses, and where the graph spans repositories, at least one control must itself be a cross-repository edge. One passing control on the easy case is how a scoped credential looks validated.

Record validation per **credential, transport and boundary**, not per transport alone. "MCP works" is not a finding; "MCP, as this account, resolves edges from A into B" is. The credential is the part that decides what was visible, so it is the part a later read has to match.

**A cached proof is only as good as the credential it was made with.** Transport, class and boundary do not identify a credential, so the same tuple can later be backed by a narrower one — a short-lived token rotates, a transport reauthenticates mid-run, or a fresh session starts with different grants — and the stale proof reads as applicable. Store a non-secret identity of the credential alongside the proof (the authenticated account and its scopes, an expiry, a fingerprint — never the credential itself), and revalidate whenever that identity changes, whenever a transport reauthenticates, and always after a restart. Treat any authorization error mid-run as invalidating every proof bound to that **credential**, across every transport that uses it — not just the failed call, and not just the transport it arrived on. Grants narrow server-side, so a `gh` call returning 403 says nothing about `gh` and everything about the token; cached raw-HTTP proofs on the same token are equally stale even though nothing has failed there yet. A narrowing is exactly what a silent partial view looks like from one call away.

The conclusion rule: **absence observed through an unvalidated transport is not evidence of absence.** Report it as "not visible via `<transport>`", never as "does not exist". A dependency edge that is invisible rather than missing produces a wrong DAG, dispatches work whose prerequisites are unbuilt, and reads as a clean validation the whole way — the graph is the thing the run schedules against, so a false absence there is not a cosmetic error.

Record which transport was validated for which class of relationship read and across which boundaries, so a later read in the same run, or a restart, does not silently fall back to an unvalidated one.

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

Projects are discovery surfaces, not execution graphs. Combine FE/BE/shared projects into one candidate DAG. Prefer an identifiable selected build-order/root issue before dispatching broad project work.

# Mandatory validation preflight

Before dispatching any **new** implementation worker, invoke `validate-backlog` on the entire bounded scope — `shallow` by default, deeper over the nodes the escalation rules below reach.

Use the validator's normalized DAG as the scheduling graph. Do not let the execution runtime independently invent a competing decomposition.

That prohibition is about re-planning, not about evidence. A worker reporting a blocker it verified against its own issue is not inventing a decomposition — it is correcting one, from a position the validator did not have (see Outcomes). Accept an edge a worker verified; reject a runtime's attempt to reorder or re-scope the backlog.

Results:

- `PASS` -> proceed;
- `PASS_WITH_WARNINGS` -> proceed only where warnings do not make ordering unsafe;
- `FAIL` -> stop affected paths; continue only validator-confirmed independent safe branches.

One warning is never proceedable at any level: **unproven relationship visibility over dispatchable scope.** A current validator returns that as `FAIL`, but treat it as blocking wherever it arrives, including from an older validator or another tool. Every other warning can be weighed because you can see what it is about; this one asks you to weigh what you cannot see, so "it probably does not affect ordering" is not a judgement available to you.

Verify empirically any baseline a ticket tells workers to diff against — "~40 pre-existing type errors", "these tests already fail" — before it goes into a dispatch prompt. Tickets go stale, and a wrong baseline is worse than none: genuinely new failures hide inside an imaginary one.

Measure it at the parent level, but key it by **repository, base revision, and check** rather than broadcasting one number across the run. Workers in a fanout off a single base share a baseline; workers on stacked bases or in different repos do not, and handing them a number measured somewhere else reintroduces the same defect from the other direction — a real regression hidden inside a borrowed baseline, or a pre-existing failure reported as new. Measure once per distinct base, pass each worker only its own, and correct the ticket's claim in the checkpoint output.

Run repo-relative checks from the repo root. Ticket paths are repo-relative, so a `cd` partway through a validation sweep silently invalidates them.

Do not automatically mutate dependency metadata. GitHub normalization is handled separately by `normalize-github-dependencies` when requested.

`validate-backlog deep` is not run by default, because it can consume materially more model/code-reading budget. It remains available on request — and it is entered **automatically**, without asking, under the triggers below.

## Escalating to deep validation

Shallow mode reads declared dependency metadata and issue text. It never reads code, so it can establish that an edge is *satisfied* and nothing about whether the deliverable behind it covers what the consumer needs. Escalate the preflight from shallow to deep **automatically** — this is a documented default applied and reported, not a question for the user — when the bounded scope shows any of:

- **a cross-repository consumer edge** — an in-scope issue in one repository depends on an issue in another. This is the primary trigger. A frontend consuming a backend built in an earlier tranche is the canonical case, and the earlier tranche having merged is precisely what makes shallow mode confident and wrong;
- **an issue whose text hedges about its inputs** — "may require", "additional providers may be needed", "assuming X exists" — or an acceptance criterion naming a capability no in-scope issue delivers;
- **a dependency satisfied by an issue that closed in an earlier tranche**, where nothing in this run verified what that issue actually exposes.

Scope the escalation to the affected subgraph rather than the whole DAG. The cost objection to deep mode is about breadth, and this does not have to be all-or-nothing: escalate the triggering node and the dependencies it consumes, and leave unrelated branches shallow.

Escalation changes the **mode** of the preflight, never whether one runs, and it reads more deeply *within* the bounded manifest — it never widens scope. `PASS` / `PASS_WITH_WARNINGS` / `FAIL` are handled exactly as above at either mode, unproven relationship visibility stays unproceedable at either mode, and the deeper read consumes model budget, not the 12-new-issue budget.

### Coverage is not visibility

This is not the unproven-visibility case, and the doctrine that handles that one cannot catch this. There, an edge may exist and your read cannot show it: absence proves nothing, and the repair is a proof re-established against a case whose answer is known. Here nothing failed. The read was complete, the edge is real, the dependency is genuinely satisfied, and every transport proof over that boundary is valid and stays valid.

What is missing is **coverage**: the closed issue's deliverable does not include the part the consumer needs. `CLOSED` and `MERGED` mean the work someone scoped got done — not that it exposes what something downstream was written against. A backend tranche scoped to a service layer can satisfy every declared edge into it and still ship no route for a frontend to call. Only reading the code behind the edge reveals that, which is why the answer is a mode change rather than a proof. Do not invalidate a visibility proof over a coverage finding; there is nothing to invalidate, and doing so halts dispatch across a boundary that is working correctly.

### Reporting

- **Escalation that finds nothing is still reported** — name the trigger, the nodes escalated, and the clean result in the checkpoint output, so the extra cost is visible and attributable rather than invisible overhead.
- **A single-repository tranche with no hedged inputs does not escalate.** The default stays shallow; escalation answers a trigger and does not become the new baseline.
- **Escalation on one node does not force deep validation of unrelated branches.** Nodes that no trigger reaches are validated shallow in the same preflight, and the checkpoint says which nodes got which mode.
- **If deep mode is unavailable** — not installed, failing, or out of model budget — the escalated nodes are **not dispatchable**. A trigger fired precisely because shallow evidence cannot answer the question for those nodes, so a shallow `PASS` over them is not a weaker answer, it is no answer: take the escalation's `FAIL` path — stop those paths, raise `NEEDS_USER`, and continue only the branches no trigger reached, which shallow validated on its own terms. Report the condition, the nodes owed the deeper read, and what blocked it. Falling back to shallow and dispatching on its `PASS` recreates exactly the case the escalation exists to catch, with the cost hidden behind a green result.

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
2. rerun `validate-backlog` at the mode the escalation rules select (see Escalating to deep validation) — a restart re-derives readiness from scratch, so those triggers apply here exactly as at the first preflight, and a resumed run is if anything the likelier place to meet one, since its dependencies closed in an earlier tranche by construction — then reconcile its DAG against blockers a previous run's workers recorded on the issues themselves. What an edge's **absence** from that DAG means is not one thing — it depends on the boundary's proof state and on the edge's provenance, and this step is the main caller of the retirement rule under Outcomes. The validator run you just made supplies that proof state, so read it from there rather than carrying one over: either passing result means every boundary over dispatchable scope was proven, since an unproven dispatchable boundary is a `FAIL` by its contract and never arrives quietly, and the boundaries left unproven are named. Then:

   - **visibility unproven for that boundary** — the validator reads through a transport that may truncate identically to last time, so re-adopt the edge rather than rediscovering it by dispatching into it again;
   - a worker's report is not a blocker record and must not be adopted as one, wherever it is found — on its PR, where it belongs, or in an issue comment left by older tooling. Read it for what the worker observed, then classify it here as though the worker had just returned it. An unclassified edge does not become established by having survived a session boundary;
   - **proven, and the edge is native by now** — a later run may have made it native via `normalize-github-dependencies`. A proven read that no longer returns it is the retirement case: retire it, dated, rather than re-adopting a dependency someone deliberately removed;
   - **proven, and the edge lives only in the persisted comment record** — absence still proves nothing, because native metadata was never supposed to show it. Re-adopt, then classify it here: **this step is the run adoption** the retirement rule anchors to, and skipping it is precisely how a retired dependency becomes permanent;
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
7. include **the dependency context used to judge this issue READY** — the blockers considered, how each was resolved, which transport and credential produced that view, and **the provenance of each edge**: your own native read, or a blocker a previous worker established that you recorded outside native metadata. The worker compares its native read against yours, and an edge you deliberately kept out of native metadata is one its native read is supposed to lack; unmarked, that comes back as a visibility disagreement against the very corrections you recorded. **Mark the context as your complete READY dependency set**, because it is: unmarked context is treated as a targeted answer whose omissions mean nothing, so an edge you never saw would come back unreported and your frontier would stay wrong. State too whether the read behind it had **proven visibility** for the boundaries this issue's blockers could cross. Marked complete, that is what makes the worker's own silent read meaningful — otherwise its three sources collapse to one unproven native read, agree because two are empty, and readiness rests on an absence nobody established. You will normally have the proof, since an unproven dispatchable boundary is a preflight `FAIL`; where you are dispatching without it, saying so is what lets the worker stop instead of building against it;
8. include **authorization membership**: the bounded authorized set, or a per-blocker flag for whether each is inside it. Only you know this, and the worker's block outcome turns on it — without it, an external-looking prerequisite you did authorize comes back as an out-of-scope wait and you skip the frontier re-derivation it needed. A worker given nothing defaults to the stronger outcome, which is safe but costs you the distinction;
9. include, on any runtime where a worker's return value does not reach this run, the requirement that it **record the judgment part of its result on its PR before returning** — not on the issue, and not the run state, which the session record and the branch already carry; see How a worker's report actually reaches you. Judgment here means **every dependency it checked, with the class it judged each under and how each resolved — the ones that matched as much as the ones that did not** — plus the criteria it could not satisfy, the guarantees it narrowed, and the sources that disagreed. The confirmations are not filler: Outcomes requires this run to record verified edges, a clean run has nothing else to record them from, and a report phrased only as exceptions leaves a fully-satisfied dependency set indistinguishable from one nobody checked. Any terminal outcome reached before a PR exists writes nothing and simply returns — investigating it, and recording anything that comes of it, is this run's job, not the worker's;
10. dispatch Sonnet worker with `implement-issue-core`.

A dispatch prompt that enumerates a required process is followed literally: a default left out of that enumeration is a default skipped, and the worker will accurately report that the task never asked for it. The same literalism decides what the worker does with instructions this run did not write (see Countermanding the worker's ambient supervision posture, below). Every dispatched prompt must therefore carry the automated review trigger instruction — `create-pr` owns the trigger rules, do not restate them here — unless this run explicitly defers review. Deferral is a conscious choice recorded in run state, naming what review is owed and on which PRs; it is never an omission.

Issuing the trigger is not the end of that step. Confirm it took effect: a review from the repository's automated reviewer materializes within a bounded window, and the reviewer does not instead answer indicating it is not configured or not authorized. Verify per attempt, on every PR — one review arriving elsewhere in the run is not evidence the trigger works. A trigger that silently no-ops is worse than one that fails loudly, because the run then reports PRs as reviewed and clean when nothing reviewed them.

An elapsed window is not a refusal. A reviewer that is merely queued or slow leaves the PR unreviewed-pending, reconciled through ordinary event supervision and visible as such in checkpoint output; only an explicit not-configured/not-authorized response marks the trigger unavailable.

A refusal is first evidence of the wrong write path, not of insufficient authority. Where the platform offers more than one way to perform the write, reissue the trigger once through a different available mechanism before drawing any conclusion. Where the platform exposes only one write mechanism, the available paths are already exhausted. Do not otherwise repeat the same write path: it will not start working on the next PR, and each failed attempt leaves trigger and refusal comments behind on the PR.

Only once every available path has failed, record it as `NEEDS_USER`: surface once, with the affected PRs, that review could not be triggered, and stop issuing the trigger for the remainder of the run in that repository. One escalation per affected repository, not one per PR; suppression is scoped to the repository that refused, because review configuration is repository-specific. Never conclude from a refusal alone that review cannot be triggered from this run at all — that conclusion is cheap to draw, hard to disprove afterwards, and costs precisely the reviews it skips.

This generalizes past review triggers. When the platform offers several ways to perform the same write, prefer its first-class integration tooling over raw transport: attribution, permissions, and downstream automation can all differ between them, and the difference is invisible until a write is made and read back. Where identity matters to a workflow, verify it by inspecting an object the run actually created and reading its author — never by asking the credential who it is, which can answer differently from what its writes carry.

Under Dynamic Workflows, provide these constraints to every workflow worker explicitly. Do not let a worker select another backlog ticket when it finishes.

## Countermanding the worker's ambient supervision posture

Prompt literalism cuts both ways. A prompt that omits a required default gets a worker that skips it; a prompt that omits a required **contradiction** gets a worker that follows whatever its own session already told it to do. A Claude Code Remote worker session inherits a system prompt instructing every session to subscribe to PR activity and to schedule a self check-in roughly an hour out, re-arming it silently until the PR merges. That instruction arrives with the runtime rather than from any skill this run dispatches, and it is correct for the sessions it was written for.

So every dispatched prompt — implementation and repair alike — must state that this run owns PR supervision and the worker does not: do not subscribe to PR activity, do not schedule a check-in, trigger, routine or wake of any kind, and return after pushing and reporting, **even where the worker's own session instructions direct otherwise**. Name the override rather than merely stating the rule.

**But put it where it can actually outrank what it countermands.** A dispatch prompt is a task instruction, and a task instruction is the weaker side of an argument with a session's own system prompt — telling a worker in its task to disregard its session instructions does not, by itself, make it do so. So on a runtime where this run *builds* the worker's session, write the countermand into that session's system prompt: `create_session` takes an `append_system_prompt` for exactly this purpose, and it is the only lever here that sits at the same level as the instruction it is answering. The dispatch prompt then restates it rather than carrying it alone.

The tier decides which lever exists, and only one tier has the problem:

| runtime | where the countermand goes |
|---|---|
| remote worker session | `append_system_prompt` at creation, restated in the dispatch prompt |
| subagent, Dynamic Workflow agent, serialized | the dispatch prompt is the whole of it — none of these inherits a session posture to countermand |

Expect this to reduce the behavior, not to eliminate it. Appending does not delete the instruction already present, some environments ignore the parameter outright, and a worker resolving two same-level instructions may still arm a wake. That residue is why **Blocked workers** is a backstop rather than a redundancy: the run has to be able to notice a worker that armed one anyway and clear it, not merely to have forbidden it.

**And do not read a quiet session list as proof this worked.** Where workers inherit an allowlist that grants the trigger tools, a worker that arms a wake can also disarm it, so it leaves nothing blocked behind — which looks identical from outside to a worker that never armed one. Only the checkpoint output separates them. Report the wake a worker armed wherever you can observe one, and treat an absence of blocked sessions as the absence of a symptom rather than as evidence about the cause.

Do not leave this to the worker skills. `implement-issue-core` and `repair-pr` now forbid delegating a wait as well as performing one, but their earlier wording — bounding duration alone — is what a worker met and satisfied while still leaving a watcher armed, because arming a wake is not entering a loop. That reading is available again to any worker weighing a skill rule against a session instruction, and the skill rule is the weaker of the two on its own. The gap is **delegation, not duration**, and this prompt is the only place in the system that sees both instructions at once.

It is also the only place the problem is visible. The instruction being countermanded appears in none of the worker skills, so searching them for the behavior finds nothing that could be causing it.

The parent arming its own subscription and check-in when a run settles (see Arming the wait when nothing is in flight) is this same ownership stated from the other side, not an exception to it. One watcher, held by the layer that owns supervision.

Two costs, and the second is the one observed. A second watcher duplicates supervision the parent already owns and can act on a PR the parent is mid-repair on. And a worker that arms a wake it is not permitted to disarm — the trigger tools are routinely outside a worker session's allowlist — blocks on a permission prompt with nobody watching, holding a container for hours after its own work merged. The implementation succeeded; the deadlock was entirely in the cleanup.

Scope this to workers **this skill dispatches**. `implement-issue` invoked standalone owns supervision of its one PR by design, and the ambient posture is right there; this countermand does not travel to it.

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

Once an implementation worker reaches `PR_OPEN`, release that implementation worker — on a remote-session runtime that is an archive call, not merely ceasing to message it (see Releasing a worker). Long-lived PR supervision belongs to the parent/runtime orchestration layer.

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
event subscription: armed/unavailable
```

## Event handling

**Arm the subscription when the PR enters the tracked set, not when the run settles.** A PR becomes trackable the moment a worker reports it, and every rule below about consuming events assumes something is delivering them. Nothing is, until this run says so: `subscribe_pr_activity` is a call the parent makes per PR, and Claude Code's background PR watch covers only what it already surfaced. Arm it as part of adopting the PR, alongside recording its head and base, and record the result in the per-PR block above — a PR whose subscription is `unavailable` is one this run must poll deliberately rather than assume it will hear about.

Arming later is not equivalent. Between a PR's creation and its subscription the run is blind to exactly the events it most needs: a merge someone performs, a review that lands, a base that moves underneath it. A tranche whose first PRs were subscribed and whose later ones were not looks identical from the inside — events keep arriving, they are simply the wrong ones — and the run reads its own quiet as nothing having happened. The settled-state arming under Arming the wait when nothing is in flight is a backstop for the empty-frontier case, not the primary mechanism, and treating it as the moment subscriptions begin leaves every PR unwatched for the whole of its active life.

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
7. release the repair worker (see Releasing a worker) and resume event supervision.

External/flaky failure with no justified code change does not consume a repair cycle.

On actionable review feedback:

1. group the coherent current review round;
2. if budget remains, allocate an isolated checkout of the current PR branch;
3. dispatch one Sonnet `repair-pr` worker with `repair type = review`;
4. `repair-pr` uses `resolve-pr-comment` where relevant;
5. adopt the new remote head and increment review cycle;
6. retrigger/request review when repo convention requires it, unless review is still deferred for this PR or triggering was suppressed for this run;
7. release the worker (see Releasing a worker) and resume event supervision.

Review feedback may reference a head already superseded by a rebase/restack. Locate each finding by content rather than line number, and confirm it still applies to the current head before repairing.

Product/architecture judgment -> `NEEDS_USER` rather than speculative repair.

A PR branch may have only **one active mutating worker** at a time. Before repair, verify the remote head has not moved unexpectedly.

## Mechanical pushes do not consume review

A restack, or a renumber/regeneration of a claimed artifact, moves identity or ordering rather than behavior. Such a push:

- does not consume a review repair cycle;
- does not re-trigger automated review;
- does not reset the PR's reviewed state or its eligibility for draft promotion.

The repository's deterministic checks are what validate it. Where the repository has no check that would catch a bad renumber, treat the push as substantive instead — `create-pr` carries the full test for which is which.

A renumber earns the mechanical label only once its regeneration has been **verified to apply** (see Performing the renumber once a human decides). "Moves identity or ordering rather than behavior" describes what a *correct* renumber does; the hazard is that a botched one is indistinguishable from it in the diff while changing whether the artifact runs at all. So an unverified renumber is not a mechanical push, it is an unvalidated one, and skipping review over it is the shortcut that makes the failure invisible. Verify first, then claim the exemption.

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

1. consume worker completions (including a Dynamic Workflow's returned fan-out results, if one was used), extracting each one's dependency evidence — unmet blockers, source disagreements, **and the resolutions that confirmed your view** — regardless of its outcome;
2. reconcile tracker + remote branches/PRs;
3. consume/reconcile CI/review events;
4. update heads/budgets;
5. dispatch repairs;
6. recompute READY frontier;
7. fill available worker slots (optionally via a fresh Dynamic Workflow fan-out if the user re-opts in for the next batch);
8. inspect stack ancestry changes;
9. inspect every in-flight worktree for uncommitted work and enforce checkpoints (see Checkpoint compliance — this is a mandatory step, and the parent commits on the worker's behalf when a nudge has already failed);
10. read every worker's runtime state, not only its work state — release the finished (see Releasing a worker) and act on the blocked (see Blocked workers);
11. re-check disk/slot capacity;
12. check sibling branches for colliding added or modified claimed artifacts;
13. surface `NEEDS_USER`;
14. wait using native task/event wait, then repeat.

Do not use CPU loops, file-touch loops, detached sleeps, meaningless commits, or other fake activity solely to prevent idling.

Remote Git checkpoints remain mandatory regardless of runtime, because no platform/runtime persistence substitutes for durable source control.

## Arming the wait when nothing is in flight

Step 13's native task/event wait is sufficient while workers are running: their completions are the events. A **settled** run has none. No worker will finish, no CI will fire, and the merge it is waiting on may be a day away — so a settled run that simply waits has no event source of its own, and "the run advances its own frontier" quietly becomes conditional on something nothing required it to arrange.

Before a settled-and-empty run stops doing work, it arms both of:

1. **a PR-activity subscription over this run's own PR set** — the platform-native watch or an explicit `subscribe_pr_activity` (see Event handling). This is what delivers the merge that advances the frontier. Normally these are already armed, because Event handling arms each PR when it enters the tracked set; this step confirms the set is complete rather than establishing it, and arms anything missing;
2. **a scheduled self check-in, as the backstop**, because that subscription does not cover everything. CI success, new pushes and merge-conflict transitions are the known-unreliable deliveries, and a merge whose event never arrives is a merge the run never acts on. The check-in re-reads durable state — PR states, mergeability, the frontier — and acts on what it finds, instead of treating silence as evidence that nothing happened.

Both, not either. The subscription is the fast path; the check-in is what makes the slow path terminate. Re-arm the check-in each time it fires and finds nothing, and stop once every PR in the set is merged or closed.

This is not a licence to keep a loop warm, and the ban above is unchanged. A durable subscription and a scheduled wake cost nothing between firings, which is exactly what separates them from spinning, touching files, or committing to look busy. The two rules point the same way: fake activity is what a run resorts to when it has no real wake mechanism, so arming one is the fix rather than the exception.

**When neither can be armed** — no subscription available, no scheduler — do not hold the session open reporting supervision that is not happening; the run would sleep through the merge while the user believed it was watching. Reconcile durable state and return a restartable checkpoint naming the resume frontier and the PRs whose merges would advance it, exactly as Stop conditions already requires when the runtime cannot safely stay active. Restart / resume adopts that and re-derives readiness from durable truth, so what is lost is the automation, not the work.

## Frontier advance on merge

A merge someone else performed is a **frontier-advancing event**, not a terminal one: it is the thing that turns in-scope `BLOCKED` issues into READY work. Steps 6 and 7 of the loop above are how the run consumes it, and they stay reachable after the tranche settles. On every merge/close event:

1. reconcile tracker + GitHub remote state, so readiness is recomputed from durable truth rather than cached run state;
2. restack affected descendants exactly as today (see Stack mutation while PRs are open) — this step is unchanged;
3. recompute the READY frontier over the **same bounded manifest**, crediting merges only (below). A merge never widens scope: an issue the invocation did not adopt does not become in-scope because something it depends on merged;
4. if new nodes became READY, re-run the preflight over the bounded scope before dispatching — **at the mode the escalation rules select**, not shallow by default (see Escalating to deep validation) — then fill free worker slots in scheduling order. The preflight is not optional here: it is mandatory before **any** new implementation worker, and the merge changed the graph the previous run validated. This is the case that needs the escalation most: nobody is watching the resumed dispatch, and the merge that triggered it is itself the event that makes a stale cross-tranche dependency look satisfied;
5. if nothing became READY, stay settled and keep supervising.

This requires no new user prompt. While the run still holds budget and in-scope work remains, the merge resumes dispatch inside the same invocation.

**Only a merge advances the frontier.** A close is worth reconciling but is never an advance, and step 3 must credit merges alone. A PR closed without merging leaves its issue short of `DONE` — completion is a closed issue **plus a merged** implementation PR (see Completion semantics) — so a recompute that treats close like merge sees a dependency-free node and dispatches a fresh worker for the work a human just declined, recreating the PR they closed and spending budget to do it. Nor does an unmerged close unblock anything downstream: a descendant is not released by an ancestor that never landed.

So on an unmerged close, reconcile and stop there. Hold that issue and everything downstream of it, and surface it as `NEEDS_USER` naming the closed PR. Closing unmerged is a decision the run cannot read from the event — abandonment, a rejected approach, and work superseded by something that landed elsewhere are indistinguishable to it, and they call for opposite next moves. Redispatch that path only on an answer, never on the close itself.

### When the advance waits for a human

Continuing is the default, and the advance never manufactures a question the skill has a documented default for (see Autonomy and interactive prompts). What it must not do is dispatch *through* an ask the previous tranche already left outstanding — starting the work is one way of answering it. Hold a path where an outstanding item bears on the work about to start:

- a `DECISION` action point, or a `MERGE_RISK` raised as `NEEDS_USER`, **whose answer would change what or how the newly-READY node gets built**. Dispatching commits the run to one answer before the human gives it;
- an unverifiable-prerequisite `NEEDS_USER` the merge did not satisfy — a merge retires only the blockers it actually satisfied;
- an **unproven dependency view** `NEEDS_USER`, which holds the whole advance rather than one path: step 3 recomputes readiness through the same transport whose reach is in doubt, so every node it just called READY shares the blind spot. Re-establish the visibility proof before dispatching anything, exactly as at the preflight.

Everything else continues. A `NEW_ISSUE` follow-up, a question about how the merged PRs themselves are handled, or a `NEEDS_USER` on an unrelated branch does not hold a node it has no bearing on — and holding one path never holds the others: dispatch the unaffected newly-READY nodes in the same pass.

Read the merge itself as evidence. A user asked to choose between two approaches who then merged one has answered; do not hold work on a question their merge settled. What survives is the ask the merge left genuinely open.

Holding is not idling. Name the outstanding item, the node it holds, and what answer releases it — in the checkpoint output and as a live `NEEDS_USER` — and treat the answer as its own resume signal: the held node dispatches on the reply, in the same run, with no re-invocation.

Nothing about the advance relaxes the safeguards it dispatches under:

- **invariant 12 still holds.** The run reacts to merges; it never performs one. Auto-advance is triggered by observing a merge, never by deciding one should happen.
- **the 12-new-issue budget is consumed like any other dispatch.** If the budget is exhausted, do not dispatch: report the newly-READY frontier in the checkpoint output as the resume frontier, so a resumed invocation adopts it instead of rediscovering it. Silently dropping newly-unblocked work is the failure this step exists to prevent.
- **`NEEDS_USER` is not cleared by a merge.** A node whose only remaining blocker is a question a human was asked to decide stays blocked, and auto-advance must not resume that path (above). Only the blockers the merge actually satisfied are retired.
- 4 concurrent workers, attempt/repair caps, Sonnet workers, one issue per worker, and isolated checkouts apply to resumed dispatch unchanged.

Edge cases:

- **A merge that unblocks nothing in scope** ends at step 3. Reconcile and restack, then return to supervision — do not run a preflight or a dispatch pass for it.
- **A merge landing while workers are still in flight** advances the frontier without disturbing them. Recompute readiness and dispatch only into free slots; in-flight workers are never cancelled, restarted, or re-scoped because their frontier moved.
- **A newly-READY node that re-blocks on validation** (the preflight returns `FAIL` on its path, or a warning that makes its ordering unsafe) is not dispatched. Record it and continue with the validator-confirmed safe branches, exactly as at the initial preflight.
- **A tranche that settled with a `DECISION` outstanding** advances every path the decision does not bear on, and holds only the ones it does. A pending question is a reason to hold a node, never a reason to stop the run.
- **A close event mixed into a batch of merges** — a stack where seven PRs merged and one was closed unmerged — advances on the seven and holds the eighth's issue and its descendants. Do not let the merges in the batch launder the close.

## How a worker's report actually reaches you

Everything below about consuming a worker's outcome — its dependency evidence, its coverage findings, its disagreements — assumes the report arrives. Whether it does is a property of the runtime, and it is worth stating beside the tiers for the same reason releasing a worker was: the phrase names a real mechanism on some tiers and nothing at all on others.

| runtime | how the report reaches the parent |
|---|---|
| in-process subagent | the return value, delivered to the caller |
| Dynamic Workflow agent | the fan-out result the workflow returns |
| serialized execution | directly, in the same context |
| **remote worker session** | **it does not.** A remote session cannot message its parent. Its structured return lands in its own transcript, which the parent never reads |

On that last tier — the one the degrade chain most often lands on — a worker's report reaches this run only through what it wrote somewhere durable. All of that is **pulled**, never pushed. A dispatch prompt asking a remote worker to "report back" gets a report; it is simply addressed to nobody.

**So require the worker to write the report down, before relying on being able to read it.** Nothing in the worker contract does this today: `implement-issue-core` requires returning its structured state *to its caller* and never requires persisting it anywhere, and `create-pr` writes only the PR's own metadata. Pulling therefore recovers whatever happened to land in an artifact, which is not the same thing as the report and is sometimes none of it.

The gap is worst precisely where the report matters most. A `BLOCKED` or `FAILED` outcome usually happens **before any PR exists**, so there is no PR body to read, no review thread, no commit message — the dependency correction that stopped the worker exists only in a transcript nobody will open. A parent that pulls the usual sources finds nothing unusual and concludes the worker had nothing to say. Successful runs leak less but still leak: graph corrections and caveats that are not coverage findings have no place they are guaranteed to be written.

**Read the session record before requiring anyone to write anything.** A remote session's own record already carries most of the run state. It is written by the runtime rather than by the worker, costs no permission, needs no tracker write, and survives the session being archived:

| field | carries | limit |
|---|---|---|
| `status_bucket` | `WORKING` / `COMPLETED` / `BLOCKED` | disagrees with `session_status` — see Blocked workers |
| `pending_action.tool_name` | exactly what a blocked worker is waiting on | only while it is blocked |
| `task_summary` | what it is doing right now | ephemeral; says nothing about outcome |
| `post_turn_summary` | `status_category`, `status_detail`, `needs_action` | **one line of free text**, rewritten each turn |

Add the branch — commits, diff, messages — and the PR where one exists, and *did it finish*, *is it stuck*, *on what*, and *what landed* are all answerable without the worker writing a word to the tracker.

**What none of it carries is judgment.** An acceptance criterion the worker could not satisfy, a guarantee it narrowed, an endpoint it found missing, a dependency it read in prose that native metadata denies — those live in its reasoning, and `status_detail` has room for a sentence. That is the only thing a written report is needed for, and scoping it that tightly matters: a requirement phrased as "persist the run state" writes down a great deal that was already free, into a place that then has to be defended against every reader of it.

So route the report by whether a PR exists, and **never to the issue**:

- **`PR_OPEN` — a comment on the PR.** That is where a reviewer and a merge decision look, it exists exactly when there is a body of work to qualify, and it is inert to every dependency reader. This is the large majority of reports.
- **every other terminal outcome — `BLOCKED`, `BLOCKED_EXTERNAL`, `FAILED`, `NEEDS_USER` — the worker writes nothing.** All four normally occur before a PR exists, so all four take this path; naming only two would leave the other two with neither a sink nor a parent-side investigation. The worker returns; its one line of `status_detail` and `needs_action` tells this run there is something to look at. The parent then investigates — the branch, `pending_action`, the issue's own prose, the dependency read repeated under its own credential — and **writes the record itself, after classifying it.**

  `NEEDS_USER` needs one thing more, because it is the outcome a one-line summary is least able to carry. Its two kinds — an unverifiable prerequisite, and an unproven dependency view — demand opposite things: the first is a question to put to a person, the second is transport evidence that invalidates a visibility proof and holds up every sibling dispatched through the same read. Require the dispatch prompt to have the worker put **which kind, and the exact measure that was out of reach**, into `needs_action` — the field exists for precisely this and is the one place a terminal no-PR outcome can still say something specific. A parent left to infer the kind from an empty blocker list handles the expensive one as the cheap one.

The second rule is not a concession to a limitation. It restores a separation this skill already required: *record each **established** blocker, naming how it was verified* — and establishing is the parent's job, needing a visibility proof the worker does not hold. A worker writing unclassified findings onto an issue was always the parent's duty performed by the wrong party. Every failure that followed from it — the next dispatch re-adopting a rejected edge, validation's preflight reintroducing it, dependency normalization promoting it into native metadata where nothing later re-examines it — followed from that inversion, not from any detail of how the writing was labelled.

**What this costs, stated plainly:** on a `BLOCKED`/`FAILED` outcome the worker's verbatim reasoning compresses to a line, and the rest goes with its transcript. That is a real loss. It is the right trade because the parent cannot adopt that reasoning unclassified in any case — it has to re-establish the finding before recording it — and a line saying *where to look* is what it actually needs in order to start.

**Verify at dispatch time that the worker can write the sink it is being asked to use.** The requirement is not satisfiable by instruction, and an allowlist entry does not settle it either — the entry has to name an operation the connected server actually exposes. A worker told to write a sink it cannot reach either stops on a permission gap or returns with the result in its transcript, arriving here as silence. Where the sink is unreachable, the runtime choice is what gives: dispatch that issue on a tier whose return value reaches this run.

**A worker's report is evidence; a blocker record is a conclusion. Keeping them apart is what the routing above is for.**

| | written by | says | restart treats it as |
|---|---|---|---|
| worker report | the worker, on its PR | what I observed | input awaiting classification — never a blocker |
| blocker record | the parent, after classifying | what was established, and how it was verified | an established blocker |

**Restart adopts blockers only from parent-written records**, per Restart / resume. An unclassified edge does not become established by surviving a session boundary: that the parent had not got round to classifying one is exactly the case this preserves — the finding survives, its status is not promoted by having survived.

This is why a report must not land in an issue comment, and the reason is mechanical rather than tidiness. Three separate skills read issue comments for dependency information, and they were found one at a time, each after the previous fix looked complete:

| reader | what it does with a comment-named edge | why it matters |
|---|---|---|
| `implement-issue-core` | unions it into the issue's blocker set | re-blocks the issue on every later dispatch |
| `validate-backlog` | scans comments in a **mandatory preflight** | reintroduces the edge before any downstream exclusion applies |
| `normalize-github-dependencies` | **promotes it into native metadata** | worst case — native is authoritative and an empty `blocked_by` is indistinguishable from "no blockers", so nothing later re-examines it |

A report is a copy of a read, stated by a party not entitled to conclude anything from it. Put one where those three look and the run manufactures the permanent blockers this skill's persistence rule exists to prevent — automatically, on every run, as designed behaviour rather than as a mistake someone might make.

**As a backstop for a report that lands on an issue anyway** — older tooling, a hand-pasted transcript, a worker running an earlier prompt — those three skills also skip any comment whose first line is exactly `**Worker report — unclassified evidence, not a dependency record.**`. Treat that as a property of the marker rather than a patch in three files: a comment opening with that line is not a statement about the issue's dependencies, and no reader may take an edge from it. It is a second line of defence, not the mechanism; the mechanism is that reports go on PRs and conclusions are the parent's to write.

This is the same division of labour as the ambient-posture countermand: the worker skills are runtime-agnostic and cannot know whether their return value goes anywhere, so the obligation belongs in the dispatch prompt, which is written by the only layer that knows the runtime.

So on a remote-session runtime, treat the worker's own writing as a required read rather than a courtesy copy, and pull it deliberately: the PR body and thread replies for substance, the session's summary for whether it finished, was blocked, or stopped mid-issue. A run that waits for a report to arrive from a remote worker waits forever, and — worse — reads the silence as nothing having happened.

**This bites hardest on the things no check expresses.** CI reports whether the code passes; it says nothing about a caveat the worker deliberately raised. A worker that narrowed a guarantee, deviated knowingly from an acceptance criterion, or flagged a limitation it chose not to fix writes that in its PR comment and nowhere else. Read it before any merge-order ranking, before surfacing the PR as finished, and before relaying a PR as ready — not afterwards, when the decision it should have informed has already been made. A green PR whose worker flagged a scope caveat is not the same object as a green PR whose worker flagged nothing, and only the report distinguishes them.

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

## Blocked workers

A worker waiting on a permission prompt is neither running nor finished. Its session reports `REQUIRES_ACTION` — or whatever the runtime calls *stopped, awaiting a human* — and a supervision cycle that looks only for `RUNNING` and `IDLE` sorts it under quiet and moves on.

**Read the field that reflects the blocked state, not the one whose name suggests it.** A runtime may expose several, and they can disagree: an observed session reported a plain `IDLE` in its status field while a separate derived-state field read `BLOCKED`, with the pending tool named only in a third. Checking the obvious field and finding a familiar value is therefore not evidence the worker is fine — it is the reading this failure mode produces. Establish once, per runtime, which field actually changes when a worker stops for a human, and read that one every cycle; where a summary of what the worker was last asking for is exposed, read it too, because that is what turns "blocked" into something a user can act on. Quiet is the one thing it is not: nobody is watching that prompt, so nothing will ever answer it, and the worker holds its container indefinitely. A worker sat blocked for six hours on a prompt to delete a trigger, its PR long since merged, before a human found it in a session list.

Read the blocked state explicitly each cycle, and resolve it in this order:

1. **it passes the releasable test** in Releasing a worker — apply that test, do not restate it here. Every version of this rule that was written out a second time drifted from the first, including the one that required a PR still be open and so excluded the merged-PR case this section is written from. Release it and record what it was asking for;
2. **the block is the parent's to clear** — a resource detail the worker was dispatched without, an instruction it can be sent, a write the parent can perform itself. Clear it and let the worker continue;
3. **neither** — `NEEDS_USER`, naming the issue, the session, and **the exact tool being requested**. "A worker needs permission" is not actionable; the tool's name is what lets a user allow it once and unblock every run after this one. Report the literal string the runtime gave you, server segment included, and never a tidied version of it: an MCP server can be registered under a display name, a slug, or its bare UUID, the allowlist matches the literal name, and a tool already allowlisted under one of those spellings still prompts under another. Normalizing the name to the one you expected is how that reads as an entry that exists and does not work.

Never resolve it as "still waiting". A blocked worker holds a slot, so reading it as idle also stalls the frontier: the run keeps scheduling against capacity that is not in use. It must not be possible for a worker to sit blocked across an entire run without appearing anywhere in its output.

## Capacity during the run

Re-check disk headroom and worker-slot capacity each cycle, not only at dispatch. Worktrees, dependency installs, and build caches accumulate as the run proceeds, so startup headroom does not predict headroom at the fifth concurrent worker. Report the current figure with the worker count in the checkpoint output, and stop filling slots before exhaustion rather than after a write fails.

## Cross-branch artifact collisions

After each PR reaches durable state, compare it against sibling branches in the same run and flag two things: files that two branches both **add** under the same name or sequence number, and incompatible edits two branches make to a shared claimed artifact — a generated manifest, lockfile, registry or index that branches amend rather than create, and which therefore collides with no added path in common. The general class is any artifact whose identity or ordering is claimed rather than derived.

Two chains cut from the same base can each be internally consistent and both pass CI while colliding, because neither can see the other; the conflict only materializes when the second one merges. Dependency edges and stack ancestry do not detect this — the branches are siblings, not ancestors.

Correct resolution depends on merge order, which this skill does not own. Surface the collision as `NEEDS_USER` with both PR URLs and the colliding paths. Never renumber or rewrite the artifact pre-emptively.

### Performing the renumber once a human decides

**Produce it with the repository's own generator. Never hand-edit the artifact's identity fields.** A claimed identity is rarely stored in one place, and the copies that are not the visible filename are usually the ones that decide whether the artifact runs. A Drizzle migration's identity lives in five: the `.sql` filename, the journal's `idx`, `tag` and `when`, and the snapshot's `id`/`prevId` chain. A hand-rename that updates four of them and misses `when` makes the migration **silently skipped** — no error, no log, green CI, and the schema change never applies. Renumbering `0011` to `0014` in `crypto-scanner-api` was exactly this; the repair was regenerating through `pnpm db:generate` and splicing the hand-written backfill back in.

The class generalizes past migrations: any artifact whose identity is **claimed rather than derived and spread across more than one file** — a migration with its journal and snapshot, a lockfile with its manifest, a generated client with its registry entry. Renaming what you can see is precisely the operation that leaves the rest stale.

Then verify the result **applies**, not that it compiles and not that CI is green. A skipped migration passes both, which is why neither is the check. Run the artifact's own apply path — migrate against a scratch database, install from the lockfile, regenerate and diff against the committed copy — and confirm the effect the artifact was supposed to have is actually present. Where the generator cannot reproduce hand-written content the original carried, splice it back and re-verify; a regenerated artifact that silently dropped a backfill is the same failure with the sign flipped.

Until that verification passes, the renumber is not finished, and it is not mechanical — see Mechanical pushes do not consume review, which grants the skip-re-review exemption only to a renumber that has cleared this.

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
- `BLOCKED_EXTERNAL` **on an unmet dependency** — a known wait, not a graph error, and by the worker's contract it means *every* unmet blocker was external. Work nobody in this run was authorized to do is not evidence that readiness was computed wrongly, so stop that path without re-deriving the frontier or invalidating a visibility proof over it. A worker that found any in-scope blocker alongside an external one returns `BLOCKED` instead, so this outcome never conceals one. A source disagreement reported alongside it is still transport evidence and still handled as such.
- `BLOCKED` **on an unmet dependency** — authoritative new information about the graph, not a worker failure. It means the readiness computation was wrong, most often because the dependency read behind it was silently partial. Never redispatch the same issue unchanged; nothing about the second attempt would differ. Retry and escalation budgets do not apply, because there is no failure to retry.

**Confirmations are evidence too.** A worker reports how every dependency it checked resolved, not only the ones that disagreed with you — and a resolution that matched your view is a verified edge where you previously had an assumed one. Record those against your graph — but record the right thing, because two claims are bundled in a resolution and they age differently:

- **the edge exists** — structural, and long-lived. Persist it as verified, with the read it came from and when; it stops being an assumption. It does not stop being an observation: a dependency can be retired from the graph after a worker confirms it, and a verified edge with no way to retire blocks or orders work on it for every remaining run;
- **the dependency was available** — an observation with a timestamp, and nothing more. A force-push, revert or rollback can undo it, as the availability-repair table below already acknowledges.

So a verified availability resolution is historical evidence, never a standing exemption. Every dispatch re-checks the class-specific measure — the worker's dependency precondition runs regardless, and it would be a contradiction to build a record whose purpose was to let a caller skip it. What the record buys is a restart that knows which edges are verified and which are assumed, not a shortcut past the check.

**How a verified edge retires.** By provenance, since provenance decides which read can speak to it:

- **native-sourced** — a later native read with **proven visibility for that boundary** that no longer returns it retires it. An unproven read does not, on the asymmetry stated throughout: absence observed through an unvalidated transport is not evidence of absence. Nothing else is needed here, because your own reads recur;
- **established by a worker and recorded as an issue comment** — no native read can retire it, since none was ever supposed to show it. Absence therefore proves nothing in this direction either, and the edge cannot simply stand forever on that technicality: from your own native view it is indistinguishable from a prose-only edge, so classify it on the same path — establish whether the relationship still holds, `NEEDS_USER` where the issues cannot settle it. Do that **when a run adopts it**, which is where the permanence would come from: a restart re-reads the comment and inherits the edge. Once per run is enough, and the answer holds for that run; classifying per dispatch attempt would re-ask the same question every cycle an issue stays legitimately blocked.

**Provenance here is where the edge lives now, not where it came from.** An edge recorded as a comment and later made native by `normalize-github-dependencies` is native-sourced from then on, and takes the first row — which is the point of normalizing it, since a native edge is one your own reads can retire. Judging it by its origin instead leaves the edge in the row where absence proves nothing, and it becomes exactly the permanent edge this rule exists to prevent.

An edge a worker found only in prose does not arrive here at all; it is classified first (see below), because persistence is what makes a stale edge permanent. Retirement does not retract what the worker observed — the observation stood when it was made. It records that the relationship no longer holds, dated the same way, so a later read finding the edge again is a change rather than a contradiction.

This adopts findings, never a re-plan; the validated DAG remains the scheduling graph.

**A worker returns two independent things: an outcome, and evidence about the graph.** Act on the evidence regardless of the outcome. A worker that found the prose naming a dependency native metadata did not return, and then proceeded because the work was present in its base, reports that disagreement on a `PR_OPEN` — and that report is the same evidence of a partial dependency view as a `BLOCKED` would have been. Treating only `BLOCKED` as a graph update leaves every sibling scheduled against the view already known to be wrong, choosing bases and dispatch order from it.

**A satisfied dependency whose capability is absent is evidence of the same kind.** The evidence a worker returns is not only about which edges exist. A worker that finds a declared dependency satisfied on paper — closed, merged, correctly linked — but the capability it needed absent from the code has found a **coverage** gap, and it reaches this path as a first-class finding, not as a note in its PR body. Nothing here is a re-plan: the worker is correcting the graph's meaning from a position the validator did not have, exactly as it does for an unmet blocker, so accept it on the same terms.

Require it explicitly rather than hoping for it. A worker that meets this and ships anyway — disabled UI, a stubbed call, an acceptance criterion quietly dropped — has produced a permanently partial deliverable and left the prerequisite invisible, and that, not the missing capability, is the failure mode. So the worker returns the finding whatever its outcome, naming the dependency, the capability it expected, and what it shipped instead; the parent records it durably against both issues like any other established blocker, **files the prerequisite issue**, and holds the affected path behind it. Report it in the checkpoint alongside the dependency edges workers discovered — and treat it as a trigger the preflight should have caught: a coverage finding at worker time means the escalation rules under Escalating to deep validation did not fire on a node that needed them.

**A PR shipping against a coverage finding must not close its issue.** Filing the prerequisite is not enough on its own: the degraded PR still carries a closing keyword, so merging it auto-closes the issue it only partly implemented, and the `DONE` test above then reads clean over unfinished work — the prerequisite sits open beside an issue the tracker calls complete, which is exactly the state that gets no further attention. The finding must therefore reach `create-pr`, which links such a PR with `Part of:` and `Blocked by:` rather than `Closes:`; pass it through `implement-issue-core` on dispatch and verify the emitted form on the returned PR, because a default that closes is what silence produces. The issue stays open, linked to its prerequisite, and a human closes it once the gap is filled.

Retrofit an already-open PR the same way when a finding arrives late — edit its body to the non-closing form before it can merge. A merge that has already auto-closed an issue on a coverage finding is reconciled by reopening the issue, not by accepting the close: the tracker recorded a claim the work does not support.

**Only a visibility disagreement is transport evidence.** The worker reports two kinds and they warrant very different responses. An **availability** disagreement says your base or completion claim was stale. Two things pick the repair: the direction, and **the dependency class the worker reported** — it names the class precisely so you can route this, so read it rather than assuming a base problem.

| direction | code dependency | non-ancestry dependency |
|---|---|---|
| you asserted satisfied, worker observed otherwise | your base no longer holds — recalculate and restack, and check whether it was wrong when calculated or overtaken since, because a revert or force-push that keeps happening is a different problem from one bad calculation | your completion claim no longer holds — recheck it, or keep waiting; ancestry is irrelevant and no restack fixes it |
| you asserted unmet, worker found it available | your constraint may be obsolete — recheck rather than leaving the issue parked | same: recheck the constraint, do not park indefinitely |

Neither direction, in either class, touches a visibility proof. Invalidating a proof and halting slot-filling for a stale base is an expensive answer to a cheap problem. Everything below applies to **visibility** disagreements, where some other source named an edge the worker's native read did not return.

Two variants can be demonstrations rather than suspicions — but only on conditions you must check, not assume, and the first is that you are comparing like with like.

**Compare native read against native read.** Your context is a union: edges from your own native read, plus blockers a previous worker established that the persistence rule above deliberately records as issue comments rather than native edges. A worker's native read is *supposed* to lack that second kind — you created them outside native metadata on purpose — so their absence demonstrates nothing. Mark the provenance of every edge you supply, and apply what follows only to edges your own native read produced. Without that, this rule fires on the graph corrections you yourself recorded, and each one invalidates a proof and halts dispatch.

Then, for a native-sourced edge: where **you supplied** one the worker's native read lacks, or where **its native read has one your context omitted**, compare the credential identity behind your read against the one behind the worker's. You already record yours per credential; the worker reports the transport and identity it used.

**Distinct identities** — two credentials have disagreed about one graph, which is the cross-credential comparison the corroboration rules ask you to arrange, arriving unasked. It is proof only once you rule out the other explanation: the two reads were taken at different moments, so an edge added or removed in between makes both credentials correct and neither view partial. Rule that out first — re-read the relationship through both identities, or check the edge's own history — and then invalidate. Skipping that step spends a valid proof and halts every dispatch sharing the boundary on what may be an ordinary edit.

Independence and contemporaneity are separate conditions, and a mismatch is proof only with both. Having fixed "different transport" into "different credential" earlier in this design, the same correction applies again along the time axis: two reads that differ may differ because the graph changed.

**The same identity** — and a subagent worker inheriting this session's credential is the common case, not the exception — this proves nothing on its own. One credential cannot corroborate itself, which is the rule this skill states about transports and applies no less to two reads at different moments: the mismatch may be an edge that changed between the reads, or caller context that went stale. Take the ordinary corroboration path and treat it as evidence.

The direction says whose view was partial, and therefore what to fix. Yours missing an edge the worker saw means **your** frontier was computed short — recheck it for every issue that shared that read, not only this one. The worker missing an edge you had means its transport is the partial one, and the recovery below applies as written.

**A visibility disagreement is first evidence about the transport, only second about one edge.** Adding the single dependency a worker happened to find and re-deriving against the same view leaves every other hidden edge hidden — the ones absent from both native metadata and prose are still invisible, and siblings still get dispatched from a frontier built on them. So read the disagreement against that boundary's visibility proof (see Proving a transport can see the graph), because the proof's state determines which of two very different things you are looking at:

**Visibility unproven, or the proof invalidated** — treat this as truncation, not as one missing edge:

1. adopt the named dependencies **provisionally** — real enough to schedule against, not yet established;
2. invalidate the relationship-visibility proof for that credential, exactly as an authorization error would;
3. **re-establish the proof** before filling further worker slots — a read with proven visibility for the boundary, established the way the proof is established: against a case whose answer is already known. Not merely another read through another credential; that is the proxy retired below, and it can share the blind spot you are trying to escape. The point is that you do not know what else is missing, and one recovered edge is not a reason to trust the rest;
4. **re-evaluate every provisional edge against the read you just obtained.** If it proves the boundary and still shows no native edge, that edge has moved into the proven case below and needs its classification before it is kept — a stale prose edge adopted while visibility was unknown must not become permanent merely because it was adopted first. Provisional edges are not eligible for the persistence rule above until they survive this step;
5. then re-derive readiness for every issue that shared that view, and re-check calculated bases for anything already dispatched against it.

**Visibility proven for that boundary** — native metadata is trustworthy there, so prose naming an edge it does not show is more likely stale text than a hidden edge: a dependency deliberately removed from metadata and left behind in the description. Do not auto-adopt it. Classify it — verify whether the relationship still holds, not merely whether the referenced issue is implemented, which is all the worker checked — and surface it as `NEEDS_USER` where that cannot be settled from the issues themselves. Never persist an unclassified prose edge: persistence is what makes every future restart re-adopt it, so a stale edge written down once blocks the issue indefinitely.

When classifying, use the preflight you already ran. `validate-backlog` emits a warning for exactly this shape — text names a blocker with no structured edge — so check whether it flagged this edge before dispatch. An edge flagged at preflight **and** reported by a worker is two observations from different actors — but be precise about what they corroborate, because they read the *same prose*. Their agreement about the prose is not independent and establishes nothing that was in doubt.

What it does establish is on the other side: two native reads both lacked the edge. That rules out truncation only if at least one of those reads had **proven visibility for this boundary** — the proof this skill already defines. Distinct credential identities are not enough: two credentials can share the same insufficient scopes, the same repository boundary, or the same relationship transport, and then both omit the same real edge and their matching absence proves nothing. With a proven read among them, the expensive response is ruled out and the question narrows to a cheap one — the native edge was never created, or the prose is stale, both classification rather than transport. Without one, take the validated-read path as normal.

Stop reaching for proxies here. Distinct transport, then distinct credential, then distinct moment were each offered as a stand-in for independent visibility and each failed, because a proxy can always coincide with the thing it is standing in for. The property the conclusion needs is visibility, proven; ask for that.

That is the opposite of the reading it invites. Two actors agreeing does not make the prose edge more likely real; it makes a *partial view* less likely, which is a different and more useful conclusion. Correlating still costs nothing, since the warning is in hand.

The reverse also holds: a preflight warning no worker ever confirmed stays outstanding. Do not let it expire quietly because the issue it concerned happened to complete.

Either way, do the graph work **before** filling further worker slots.

One worker's disagreement is the cheapest evidence available that the graph is wrong; discarding it because that worker happened to succeed wastes the only signal the system gets.

**Persist it, or the next session repeats the mistake.** By invariant 1 conversation and run state are caches, so an edge a worker discovered lives only in this run unless it is written down — while restart re-expands the same manifest and reruns the same validator through the same transport that truncated in the first place. It would compute the identical wrong frontier and dispatch straight back into it. Record each **established** blocker — a truncation-case edge that survived re-evaluation against the validated read, or a classified prose edge confirmed to still hold — where the restart path already looks: a comment on the affected issue naming the blocker by canonical full URL and how it was verified, plus the checkpoint output. Persist nothing that is merely unclassified, for the reason above: writing it down is what makes every restart re-adopt it. Where dependency-write capability exists and the edge is high-confidence, `normalize-github-dependencies` is what makes it native — invoked explicitly, never as a side effect of this reconciliation.
- `FAILED` — retry only inside budgets; at most one reasoning escalation.
- `NEEDS_USER` — surface full issue/PR URLs, failure/review state, attempts consumed, and recommended action; stop spending tokens on that node while continuing safe independent branches.
- `NEEDS_USER` **on an unverifiable prerequisite** — not a graph error and not a failure, and you can rely on that rather than re-checking: the worker's precedence returns `BLOCKED` whenever any in-scope blocker was also unmet, so this outcome carries none. the worker could not observe the completion measure that dependency's class requires, typically a release or deploy state outside the repository and tracker. Ask the specific question, and once answered supply it as dependency context on the redispatch — the caller asserting satisfaction is the documented path for a measure the worker cannot check. What asking buys is the **end of the uncertainty**, not the clearing of the blocker. Those come apart on a negative answer: told the release has not happened, the prerequisite becomes a known unmet blocker and the redispatch returns `BLOCKED` or `BLOCKED_EXTERNAL` by its authorization membership. Only an affirmative answer clears it.

- `NEEDS_USER` **on an unproven dependency view** — the worker could not establish that its blocker list was *complete*, with or without entries in it: your context arrived without a proven read, so its sources collapsed to one native read of unknown reach. A list with one blocker in it is not the reassuring version of this — a partial list is the dangerous one. This is transport evidence, not a question about the issue, and it is the one `NEEDS_USER` you must act on before dispatching anything else. Invalidate the relationship-visibility proof for that boundary and re-establish it against a case whose answer is known, exactly as for a visibility disagreement — every sibling you judged READY through that read shares the blind spot, and the worker only stopped because you told it the view was unproven. Do not answer this one by re-asserting readiness; that suppresses the stop without changing what is invisible.

And even an affirmative answer clears only this blocker, not the issue: the precedence ranks an unverifiable prerequisite above an external wait, so this outcome can arrive with an out-of-scope blocker still unmet and reported alongside. Read the reported blockers before expecting a redispatch to proceed. Do not invalidate a visibility proof over it; nothing here says the transport is partial.

# Merge behavior

Normal orchestration never merges automatically.

If the user separately authorizes `merge-stack`, that skill owns merge ordering and descendant rebasing/restacking. Reconcile tracker completion after every merge.

# Settled tranche

A run is **settled** when no further implementation can start and every open PR is individually finished:

- no in-scope issue is READY — each unstarted issue is blocked by work that is implemented but unmerged;
- no implementation or repair worker is in flight — and a worker blocked on a permission prompt is in flight, not absent (see Blocked workers). It reads as quiet from every angle the other conditions look from, which is exactly how a run declares itself settled while one of its workers is still stopped mid-issue;
- every open PR from this run has had at least one **completed** automated review round, not merely a trigger issued;
- every actionable review finding on every open PR is resolved or answered;
- no open PR is `NEEDS_USER` or waiting on CI.

Settled is not the same as finished. The run has produced everything it can **for now**; the next move belongs to whoever holds merge authority — and when they make it, the run picks the work back up itself (see below).

On reaching settled:

1. reconcile tracker + remote state one final time, so both the summary and the ranking are computed from durable truth rather than cached run state;
2. invoke `summarize-tranche` with the manifest/scope, this run's PR set, and the worker/review findings it produced;
3. **act on its action points before ranking anything** (below);
4. invoke `plan-merge-order` with the manifest/scope, this run's PR set, and every summary item with an ordering consequence — the `MERGE_RISK` and `DECISION` items, and any other class that also carries one, so the ranking is computed against those constraints rather than around them;
5. surface the summary and action points first, then the ranking table, as the run's closing output;
6. stop dispatching work, and stop spending tokens re-deriving the same state, for as long as the frontier stays empty.

Summarize before ranking. An action point can change whether something should merge at all, and a ranking the user has already begun acting on is the wrong place to discover that. Run the summary once per settled tranche rather than saving one up for the end of a whole backlog: its findings come from run context that the next session will not have, and follow-ups need to exist while later tranches are still running, so they get picked up instead of rediscovered.

## The summary can un-settle the run

Settlement was computed before the summary existed, so the summary is capable of falsifying it. Branch on what it returns rather than proceeding to the ranking unconditionally:

| action point | effect |
|---|---|
| `IN_FLIGHT_FIX` | the tranche is **not settled** — that PR has actionable work outstanding. Return it to supervision, dispatch the repair within budget, and re-test the settled conditions before ranking |
| `MERGE_RISK` | still settled, but the ranking must carry it. Pass it to `plan-merge-order`, and raise it as `NEEDS_USER` where it blocks a merge decision outright |
| `DECISION` | pass to `plan-merge-order` and surface as `NEEDS_USER`; it gates a human, not the run |
| `NEW_ISSUE` | report it; no effect on settlement. No effect on ordering **unless the item carries an ordering consequence** — a follow-up that must land before one of this tranche's PRs is also a `MERGE_RISK`, and takes that row too. The classes answer different questions, so read the item rather than the label alone |

An `IN_FLIGHT_FIX` reaching the ranking is the same defect the settled conditions already guard against: a table that orders PRs which are not actually finished is a table the user cannot act on. Finding it one step later does not make it acceptable.

Do not merge, and do not treat the ranking as authorization to merge — invariant 12 still holds.

If a run reaches all other settled conditions but some PR still has an unresolved finding, an unfired review, or red CI, it is **not** settled. Finish that PR within budget, or surface it as `NEEDS_USER`, before ranking. Ranking PRs that are not actually finished produces a merge order the user cannot act on.

## Settled is a resting state, not an exit

Settled means the run has nothing it can start *right now*, not that the run is over. Reaching it delivers the merge-order ranking; it does not close the invocation.

A settled run has no events of its own, so reaching settled is also the point at which it must arm its wake — a PR-activity subscription plus a scheduled check-in, or an honest restartable checkpoint if it can arm neither (see Arming the wait when nothing is in flight). Everything below assumes that happened; without it the run is not resting, it is asleep.

After the ranking is delivered, supervision continues for merge/close events and for the restack work a merge triggers — and a merge that advances the frontier re-enters the dispatch loop automatically, under Frontier advance on merge, within the same run and with no new user prompt. Automatic continuation is the default; it yields only where this tranche left a genuine ask outstanding that bears on the next wave, and then only for the paths that ask reaches. The run un-settles itself: recompute readiness, re-run the preflight at the mode the escalation rules select, dispatch into free slots, and settle again when the frontier is empty. A tranche can settle, advance, and settle again several times in one invocation.

Re-run `plan-merge-order` when merges change the graph enough that the previous ordering is stale, and again when a resumed dispatch produces new PRs that the delivered ranking does not cover.

What "stop spending tokens re-deriving the same state" forbids is idle re-derivation while nothing has changed — not the reconciliation a merge event calls for. A merge is new state.

# Stop conditions

Stop starting new implementation work when:

- every in-scope issue reached its requested durable state;
- the 12-new-issue budget is exhausted;
- every remaining path is `BLOCKED`/`NEEDS_USER` **and no merge is pending that could clear it**;
- the user asks to stop;
- safety approval is required;
- infrastructure/runtime repeatedly fails.

Being settled is not one of them. A settled run stops starting new work only while the frontier is genuinely empty; with merges outstanding it stays live, because those merges are what refills the frontier (see Frontier advance on merge). Deliver the ranking on reaching settled, then keep supervising.

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
Worker sessions: 9 created / 8 archived / 1 blocked
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
- validation result/warnings, the **mode** each part of the scope was validated at, and any deep escalation — its trigger, the nodes escalated, and the result, including a clean one;
- manifest/scope;
- resume frontier;
- PRs + stack topology;
- remote checkpoint branches without PRs;
- checkpoint enforcement: workers nudged, and workers whose work the parent committed itself;
- every PR this run tracked and whether its event subscription was armed, so a PR the run was blind to is visible as such rather than indistinguishable from one where nothing happened;
- caveats a worker raised in its own report that no check expresses — a narrowed guarantee, a knowing deviation from an acceptance criterion, a limitation left unfixed — against the PR each concerns, because these reach a merge decision only if this run carries them there;
- worker-session lifecycle, where the runtime has sessions to account for: how many this run created, how many it archived, and every one still alive with the reason — naming, for each that was blocked, the exact tool it was waiting on. A run that leaks sessions should be visible in its own report rather than discovered afterwards in a session list, and the tool name is the part a user can act on;
- disk headroom against the concurrent worker count;
- CI/review states + repair budgets consumed;
- PRs left unreviewed, and whether the review trigger was deferred or unavailable;
- PRs promoted from draft to ready, and any left in draft with the reason;
- the `summarize-tranche` summary and action points, and the `plan-merge-order` table, when the run settled;
- issue-linkage/tracker-status inconsistencies;
- `NEEDS_USER` items;
- external blockers;
- dependency edges discovered by workers that the validated DAG did not contain, where each was recorded durably, and any dependency-source disagreement reported on an otherwise successful run;
- coverage findings — dependencies satisfied on paper whose capability a worker found absent — with the prerequisite issue filed for each; for every deliverable shipped degraded, the acceptance criteria left unmet, the PR's linkage form (it must be `Part of:`, never a closing keyword), and confirmation that its issue is still open;
- which edges in the scheduling graph are **verified** by a worker's own check versus still **assumed** from the preflight read, and when each was verified. This is history, not an exemption: a restart still runs the proof-and-provenance reconciliation in step 2 of Restart / resume over every edge, verified ones included, because the label records what was true when it was written and a dependency can be retired afterwards. What it buys is knowing which edges were established by observation and which rest on one preflight read — where to be sceptical, and what not to rediscover by dispatching into it;
- unstarted work and why, including any frontier that a merge unblocked after the budget was exhausted — report it as the resume frontier rather than dropping it;
- whether invoking the same manifest can safely resume.
