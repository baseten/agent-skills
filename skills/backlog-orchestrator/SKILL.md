---
name: backlog-orchestrator
description: Autonomously executes a bounded dependency-linked implementation tranche from GitHub Issues, Linear, or another supported tracker. Can fan the implementation phase out onto a Claude Code Dynamic Workflow when the user opts into one, while preserving a validated issue DAG, Sonnet workers, isolated worktrees, durable remote checkpoints, stacked PR topology, centralized PR supervision, bounded repairs, and restart-safe tracker/GitHub state.
---

# Backlog Orchestrator

Execute a prepared implementation tranche autonomously.

This file is the contract; the reasoning and incident history behind its rules live in `NOTES.md` beside it, keyed by section. NOTES explains; it never overrides. The checkpoint-capture sequence lives as a tested implementation in `scripts/checkpoint-capture.sh` with its test suite beside it.

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
- `repair-pr` — one bounded CI, review, or settle-finding repair pass;
- `create-pr` — issue linkage, stack metadata, PR creation, review trigger;
- `resolve-pr-comment` — thread-level review fix primitive;
- `summarize-tranche` — read-only short summary and action points for a settled tranche;
- `settle-outstanding-decisions` — attended walkthrough of a settled tranche's human-only decisions, requested between summary and ranking when `auto-request-settle` is on;
- `plan-merge-order` — read-only review/merge-order ranking for a settled tranche;
- `merge-stack` — separately authorized stack merge/restack workflow.

`implement-issue` remains the convenient standalone **single-issue orchestrator**. Do not replace it with this skill for normal one-ticket work.

# Core invariants

1. **Tracker + GitHub remote state are durable truth.** Conversation state, workflow state, and cloud worktrees are caches/conveniences, not the only source of truth.
2. **Canonical issue identity is the full issue URL.** Short keys/numbers are display helpers only.
3. **A run is bounded.** Never turn one build-order ticket into an open-ended project crawl.
4. **One implementation worker = one issue = one isolated checkout/worktree.**
5. **In-flight implementation is remotely checkpointed.** Significant completed work must not exist only in an ephemeral container. **What enforces this differs by runtime, and on one tier the parent cannot:** where it can reach a worker's checkout it verifies and captures (Checkpoint compliance), and where it cannot — the remote-session tier, normally — the invariant rests on the worker's own pushes, with the dispatch prompt and the observable remote head as the only levers. Say which of those a run is relying on rather than reporting the invariant as satisfied by machinery that was never available.
6. **Sonnet is the default implementation/repair model.** Use the strongest available reasoning model for orchestration when appropriate.
7. **Only validated READY work is dispatched.**
8. **Execution dependency is not automatically Git ancestry.** Stack only where code ancestry requires it.
9. **The parent/orchestration layer owns long-lived PR state.** Implementation and repair workers are bounded and short-lived.
10. **Retries and repairs are bounded.** Persistent failure becomes `NEEDS_USER`.
11. **Recovery is idempotent.** Never duplicate work, branches, PRs, or repairs after restart.
12. **Merges are opt-in per repository, and gated even then.** By default the run performs no merge. It may merge a PR only when that PR's own repository opted in via `auto-merge` in its policy config (see Per-repository policy configuration) — **the repository's opt-in is the only route to a merge: an invocation argument can switch `auto-merge` off for a run, narrowing the gate, but never on — an invocation cannot open it** (the precedence rule under Default usage safeguards states the same exemption) — **and** the gate holds: the tranche has no `DECISION`, `MERGE_RISK`, or `NEEDS_USER` item outstanding — anywhere in the tranche, not only on that PR, and a `DECISION` that settled without being ruled on is outstanding: unruled is not clean — **and** CI is green on the PR's current head, **and** it has no merge conflict, **and** its review is clean (a completed automated review round, every actionable finding resolved or answered, no thread reserved for the owner), **and** no recovery ref for its branch is outstanding (see Checkpoint compliance — captured work that never reached the head is work a merge would silently drop), **and** it is not an **explicitly held draft** (see Draft state) — a held draft is neither published nor merged, and is reported as held — **and** the dependency view the PR was built on is proven complete or explicitly answered for (see Merge behavior, which names each consumer's supplier; a view unproven because the run's dependency transport is unavailable is accepted for dispatch and still holds this condition — proceedable is not mergeable). This is the gate's only definition; every other site defers to it. Everything outside the gate stays where it was: the user's separate `merge-stack` authorization.
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
- a `NEEDS_USER` **outcome** on a node after the budget governing its failure is exhausted — a CI or finding repair out of cycles, an implementation out of attempts — or one that leaves no dispatchable work at all — the same shape as the `FAIL` case below. **A `NEEDS_USER` item on a review thread is never an interruption**: a question, or a repair deferred because `review-repair-cycles` is spent, is reported in the checkpoint output, holds that PR's merge, and reaches the owner at settle (see Merge policy and review feedback). Interrupting on one would stop a run that has work left and, on a fired trigger, ask a question with nobody present to answer it. Every other `NEEDS_USER` is surfaced in the closing output instead of asked mid-run, including a dependency measure the run cannot observe: those need a person eventually, not now, and the run still has work to do meanwhile. The decision-shaped items get one sanctioned exception, at the one point where the run has nothing left to do meanwhile — the settled step requests `settle-outstanding-decisions` over them when `auto-request-settle` is on (see Settled tranche), and that skill's own attendance precondition, not this list, decides whether anything is actually asked;
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

**That order buys something and gives something up, and the something given up is invariant 5's enforcement.** Tier 2 is preferred for reasons that have nothing to do with checkpointing — a container per worker, so four concurrent worktrees do not share one disk (see Capacity during the run); a worker that outlives this session's compaction; per-container tool isolation. But the parent cannot reach a tier-2 worker's checkout, so the parent-side verification that Checkpoint compliance calls *the* thing that satisfies invariant 5 is unavailable there, while on tier 3 it works. **Preferring tier 2 therefore trades an enforceable durability guarantee for capacity and resilience.** That is a defensible trade and it is not this document's to make silently: report which tier was selected and, on tier 2, that invariant 5 rests on the worker's own pushes. Where an owner would rather have the guarantee than the capacity, tier 3 is the correct selection and nothing here should be read as forbidding it.

### Remote worker session arguments

Omit `environment_id` and the worker inherits this session's environment. That inheritance is sound, and it is where this section's one trap starts: the environment decides where the worker *runs*, not what it has *checked out*.

**Pass `source_url` and `source_revision` explicitly on every worker session.** Do not let the worker's checkout come from inheritance, which usually supplies one and is not reliable: it populates the new session's `sources` most of the time, and *sometimes does not*, with no error anywhere in the path. One run dispatched four workers with no `source_url`; three inherited a checkout and the fourth got an empty container (NOTES). A dispatch prompt cannot pin a branch in a repository that was never cloned. Passing the source also removes the one argument constraint here worth remembering — `outcome_branch` is rejected unless `source_url` accompanies it — which matters because Session branch mandates gives every worker session its own `outcome_branch`.

**Then verify the checkout before treating the worker as dispatched: the `create_session` response must show `sources` populated.** This is the only signal that exists before the worker starts work, and every signal after it reads the same whether the checkout is there or not: the call returns success, the session reports `RUNNING`, and a worker with no checkout reads as *still working* — the one state under Releasing a worker that nobody acts on — for as long as it keeps looking for the code. An empty `sources` is a failed start, not a worker to watch: treat it as one (see Bounded runtime probing) rather than dispatching into it.

**And end that session before retrying, or the retry orphans it.** A failed start on this tier is not an absent worker — the session exists, holds a container and a worker slot, and reports `RUNNING`, so a retry that only creates a second one leaves the first alive — the container leak Releasing a worker exists for, once per attempt, and an orphan that is precisely the filesystem-searching worker this section is written to prevent. Interrupt it, then archive it, in that order — the order Releasing a worker fixes for every session, and the empty `sources` is the evidence its capture requirement wants: a session ended at the verification above has not run a turn, so there is no worktree to strand and no recovery ref to push. **That discharge is good only here, at creation.** The same field on a session that has been running says nothing about what the worker has produced in the meantime — a worker with no checkout may well have cloned one itself — so a checkout-less session discovered later in the run takes the ordinary inspection and capture (Blocked workers), never this shortcut. **The interrupt does not consume that issue's lost-worker budget** — at creation only, on the same boundary as the discharge above — against the general rule for stopping a `RUNNING` session: that budget bounds re-attempts at work a worker may already have done, and a session ended before its first turn did none, so nothing was lost and the redispatch is the issue's first real attempt rather than its second. Charging it would spend an issue's recovery budget on a runtime defect before a line of its code was written.

**Two capabilities of this tier are established at startup, not assumed, because the rest of this document divides on them: whether the parent can reach a worker's checkout, and whether it can send the worker a message.** Both are observable without spending a worker:

- **the checkout** — a session record's `sources` carries the repository it was given and **no filesystem path**, and each session runs in its own container (`environment_kind`), so there is nothing for the parent to inspect and no path to inspect it with. **This detection is one-directional: it establishes *cannot reach* and can never establish *can reach*** — an absent path is proof of the first and no evidence at all about the second, so **absent a path, the answer is *cannot reach***, and every rule below that depends on parent-side worktree access takes its unreachable branch. A self-hosted pool that mounts worker files where the parent can see them would be genuinely reachable, and **this document has no way to discover that**: no field it knows of carries such a path. So that configuration falls in the unreachable class too — conservatively, at the cost of retaining sessions a reachable run could have released — until an operator establishes a path by some means this contract does not yet define (NOTES). Do not infer reachability from `environment_kind`, which speaks to separate containers and not to shared mounts;
- **the channel** — `external_metadata.cross_session_inbound` reports whether inbound cross-session messaging is available for a session, which is cheaper than sending one and watching for nothing to happen. It is observed as the string `available` rather than a boolean, so **test for that value and treat every other reading — including the field being absent — as absent**; a truthiness test on a missing field is the silent way to get this backwards. And it is **evidence rather than proof**, because it reports that session's inbound availability and not this parent's ability to address it: enough to act on, never enough to wait on. Blocked workers owns that rule and what overrides the field.

Record both on the run's state and report them in the checkpoint output. A run that never established them is a run whose invariant 5 story is unknown to itself.

**What the unverified case looks like from the outside, since it is otherwise recognized only by its cost:** a worker searching the filesystem for its own source files — a `task_summary` about locating a file the dispatch prompt named, a repository-root probe, or a permission prompt for a bare `find`. That is not a worker that needs a permission; it is a worker that was never given a repository, and Blocked workers says where it goes. The run that discovered this found out that way, ~50 minutes in, with nothing pushed and the whole round to redispatch.

### Bounded runtime probing

A runtime that fails to start a worker gets **at most 2 attempts**, with a backoff measured in seconds, and is then unavailable — move down the chain. A worker created without the checkout it was supposed to get is one of these failures rather than a live worker, and it fails as a **validation error whose fix the retry names** — pass the source explicitly — not as a reason to leave the tier. Its session is ended before the retry, per Remote worker session arguments; a retry on this tier that leaves the failed start running leaks a container per attempt. Varying arguments between attempts does not extend that budget: a service-side error (`temporarily unavailable`, 5xx) is not an argument problem, and a validation error names its own fix in one retry.

Do not spend an orchestration run diagnosing a runtime. Degrading to subagents and reporting the outage in the checkpoint output always beats a ten-minute retry loop before any work has started.

Also detect:

- native worktree isolation;
- whether Claude Code's own background PR watch/notification behavior is active for this session (see PR promotion and central supervision, below) — and, if so, whether its auto-merge behavior is enabled, since a platform merging on green merges outside invariant 12's gate and should be disabled or reported before autonomous work proceeds;
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
| remote worker session | **archive the session.** A live one holds a container, a session-list entry, whatever permission prompt it may be sitting on — and any wake it armed, which is the recurring cost: a live session keeps waking on schedule and spending tokens for as long as it lives |
| in-process subagent | stop messaging it; there is no resource to reclaim |
| serialized execution | nothing to do — there was never a second actor |

On two of the four tiers release *is* the absence of an action; on the remote-session tier the same words name a real resource that leaks silently (NOTES: the nine leaked containers, and the two later runs that leaked 15 and 1).

**Archiving the session is the only thing that stops a wake the worker armed itself.** The session is what arms the wake, so deleting the scheduled trigger does not work: a leaked session whose trigger was deleted armed a replacement one minute later (NOTES). Archive the session; do not fight its triggers.

**The releasable test, stated once and referenced everywhere else that needs it.** A second copy of this test appearing anywhere is the regression to look for (NOTES: how in-situ restatements drifted).

A worker is releasable when both hold, and not before:

1. **it is done** — either of:
   - it **returned a terminal outcome**, any of them and not only the successful ones. `implement-issue-core` ends on `BLOCKED`, `BLOCKED_EXTERNAL`, `FAILED` and `NEEDS_USER` exactly as it ends on `PR_OPEN`; `repair-pr` ends on `NO_CODE_CHANGE`, `FAILED` and `NEEDS_USER` exactly as it ends on `REPAIRED`. A repair worker that correctly classified a CI failure as external returns `NO_CODE_CHANGE` with an unchanged head and nothing to push, and is as done as one that pushed a fix. Releasing only on the two successful outcomes leaks every session whose worker did its job and had nothing to show for it, which a run dispatching into a wrong graph produces in bulk;
   - or its **work reached durable remote state and it is now blocked on a prompt this run does not need answered**. No outcome arrives in this case because the prompt is what stops it arriving, and waiting for one strands the session forever.

     **That last qualifier is load-bearing, not throat-clearing.** A pushed branch, an existing PR and a clean worktree do not by themselves mean the worker is finished: `create-pr` verifies tracker linkage and issues the automated review trigger *after* creating the PR, so a worker blocked on either of those is stopped mid-deliverable rather than tidying up behind one. Archiving it there leaves a PR that is unlinked or never reviewed while the run records the issue as complete — the coverage failure this document spends a section on, arrived at through cleanup. Cleanup the run does not need — disarming a wake the worker should never have armed — releases it. Anything the deliverable still depends on takes the parent's-clear or `NEEDS_USER` branches under Blocked workers instead;
2. **nothing is stranded in its worktree** — which no outcome label can speak to, and which Checkpoint compliance is what establishes.

**Where the run cannot reach the worktree at all, condition 2 currently has no satisfier, and that is a stated gap rather than a silence.** `Checkpoint compliance` is what establishes it and is unavailable there (Remote worker session arguments), so on that tier a worker is **not releasable**: raise `NEEDS_USER` naming the session and what it returned, and keep the container. The owner decides.

That is deliberately the fail-safe direction — holding a container costs a worker slot, archiving one that stopped mid-edit costs the work in it — and it is deliberately not disguised as a mechanism. Two things make a real satisfier harder than it looks, and both were established by review rather than assumed: a terminal outcome is **not** a cleanliness claim, since `implement-issue-core` promises only **bounded** loss ("at most the work since the last checkpoint") and `repair-pr` requires a push only for a repair that **changes code and succeeds**; and a worker's own assertion about its worktree has **no carrier** to the parent on this tier, because a remote return value is unreadable here and a worker that stops before opening a PR writes nothing (How a worker's report actually reaches you). Building the satisfier therefore means giving the assertion a parent-readable carrier, narrowing step 11's archive ban to workers that actually fail this test, and requiring the assertion of repair dispatches too — which is its own change, tracked separately (NOTES).

**The cost while the gap stands is that the preferred tier does not settle on its own.** Report it as such: a run that ends with retained containers on that tier has not failed, and must not be recorded as clean either.

**Durable remote state** means the branch is pushed and a PR exists for it. **The PR's own state is irrelevant** — open, merged, or closed. Merged is the *common* case here rather than an edge one: a wake armed at PR creation outlives the PR that armed it, so by the time anyone notices the blocked session the work has usually landed (NOTES). Any test that requires the PR still be open excludes precisely the deadlock this section exists for.

A session merely reading `IDLE` asserts neither condition: idle is also what a worker looks like when it finished editing and never committed — the state Checkpoint compliance exists to catch, because workers reliably reach it.

And a worker that has not returned an outcome is not therefore lost. It is one of three things, and only the last is:

| state | who owns it |
|---|---|
| stopped on a prompt | Blocked workers — released by the test above, cleared, archived and redispatched, or raised as `NEEDS_USER` |
| still working | nobody yet — leave it and re-check next cycle |
| unreachable | Lost worker / workflow recovery |

The ordering between the two conditions is fixed rather than incidental: the checkpoint-compliance step of the supervision cycle runs first, and a session is archived only once the worktree it holds has no uncommitted work left in it. Archiving first destroys the container and the only copy of that work together, and the check that would have caught it no longer has anything to look at.

Two things are never archived. A **`RUNNING`** session — a worker that must be stopped is interrupted first, which consumes that issue's lost-worker budget and needs the same evidence any redispatch does (see Checkpoint compliance), and is archived only after its work is captured (the one carve-out is a session ended at dispatch for having no checkout to work in, under Remote worker session arguments — never one discovered later, which is captured like any other; it is stopped the same way and charged nothing). And a session **this run did not create** — the user's own sessions from every other surface share that list, and none of them are this run's to reclaim.

## Transport precedence

The detection above establishes what exists. This establishes which one to use. For every tracker/forge read and write, in order:

1. a first-class MCP tool for that operation, where one exists;
2. an authenticated CLI (`gh`, `linear`, equivalent) when running locally under the user's own credential;
3. raw HTTP against the API, only where neither of the above exposes the operation at all.

Raw HTTP is a last resort, not a default. Reaching for it must be a decision you record — which operation, and why no higher tier exposes it — not an accident of habit because `curl` is familiar and always available.

One further reason counts as "no higher tier exposes it": **a higher tier that cannot ask incrementally where a lower one can** — no `since` bound and no conditional request, where a lower tier offers one (see API budget and read discipline). Descending for that reason is recorded like any other (NOTES).

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
- **Absence observed through an unvalidated transport is not evidence of absence.** Report it as "not visible via `<transport>`", never as "does not exist" — the graph is what the run schedules against, so a false absence there dispatches work whose prerequisites are unbuilt.

Record which transport was validated for which class of relationship read and across which boundaries, so a later read in the same run, or a restart, does not silently fall back to an unvalidated one.

## Posting identity

Transport precedence decides which surface a write travels through; this decides which **author** it carries. **Where a distinct agent identity is available for posting, the run posts as that identity rather than as the invoking user — except a comment whose purpose is to trigger the repository's automated review convention, which must come from the invoking user or the trigger does not fire** (`create-pr` owns the trigger convention, and the exception travels with it). The rule covers every authored forge/tracker write made on the run's behalf — timeline comments, review replies, worker reports, recorded rulings — whichever skill or worker performs it. This section is the rule's only statement; the skills that post defer here rather than restating it. The reason is attribution honesty, and a distinct identity also removes an identity collision at its source (NOTES); the structural tests under Merge policy and review feedback stay regardless (below).

**Identity is established only by observed write authorship — read the author off an authored write the run made anyway, never by asking the credential who it is.** A credential's authenticated account is a **predictor** of authorship, not the answer: relayed and integration transports re-author writes (NOTES). Nor is an identity ever established by a claim — a dispatch prompt, platform doc, or inherited constraint asserting some surface "posts as a bot" has been observed flatly false (NOTES); with no authored write observed to resolve to a distinct account, none is available, whatever any text says.

**The run holds a map, not an answer: `(transport, credential identity)` → the author observed writing through that pair, recorded per write kind** (PR creation, timeline comment, review reply, …). Both halves of the key and the per-kind split are load-bearing — one transport has no single author across credentials, and one pair has none across kinds (NOTES: the overwrite and collapse failures this prevents). The rules that follow all read this map:

- **every skill returns the observations it made**, one entry per pair it wrote through; every consumer reads the entry for the pair it is about to use, never a run-wide value;
- **an observation answers only for later writes of its own kind through its own pair**; for a kind not yet observed there it is a predictor — the same standing as the credential record — and the entry is `unestablished` for that kind;
- **staleness**: an observation is bound to the credential whose write established it and expires exactly when that credential's proofs do (reauthentication, narrowing, restart — see Proving a transport can see the graph); the next authored write re-establishes it;
- **`unestablished` is a pair-and-kind state, not a run state, and is preserved as its own value** — never resolved to "invoking user" by inference, which would overwrite a real observation with a guess.

**Availability is per write, and it never reorders transport precedence.** A distinct identity is available for a write precisely when the entry the write will actually go out under — the transport precedence already selects, paired with its current credential — has an observed author **of the kind being made** other than the invoking user. A transport whose current credential has no entry is `unestablished`; never borrow another credential's answer. An identity on a tier precedence does not select is **not** available: rerouting or probing a tier to discover its author is forbidden, and the run reports nothing about a tier it never wrote through (NOTES: why the reporting requirement cannot re-admit the credential self-report). Where such an identity **was** observed — on a tier selected for some other operation — name it in the checkpoint as present but unusable. If attribution should influence transport choice, that is a change to Transport precedence itself, argued there.

**Degrading is the common case, silent in behavior and loud in the record.** Degrade where the selected entry's authorship for the kind being written is `unestablished`, or was read back as the invoking user. Everything then posts as the invoking user, and **no post is ever withheld, delayed, or rerouted to a lower tier for want of a better author**. The condition is observational, never a second credential test: a credential that identifies as the invoking user is not evidence of degradation — the observation decides (NOTES). What changes is only the reporting: the checkpoint names the identity the run's writes resolved to.

### The review trigger

The trigger comment is the one write whose authorship is functional rather than cosmetic: authored by anything but the invoking user, the convention does not fire, and it fails **silently** (NOTES). So it is an exception to precedence as well as to the identity rule, bounded to the trigger comment alone — it licenses rerouting no other write:

- **Selection**: the highest-precedence transport whose entry for its current credential was **observed to author a comment as the invoking user** — the trigger's own write kind, because a pair whose PR creation carried the invoking user can still have its comments re-authored (NOTES) — even where ordinary precedence would select another.
- **Unobserved is not wrong-authored.** Comment-kind authorship observed as someone else is a known wrong author; comment-kind authorship merely unobserved is the bootstrap case below.
- **Bootstrap — the first trigger cannot be gated on comment-kind evidence, because only a comment can produce it** (NOTES: the deadlock). The first trigger attempt is its own establishing write: where no candidate pair has comment-kind authorship observed either way, select the highest-precedence transport whose current credential **predicts** the invoking user (a credential predicting a distinct agent identity is not a candidate — that attempt is known-wrong before it is made), send the trigger, and **read the comment back at once**. Invoking user observed → the trigger fired and the entry answers for every later trigger. Any other author → the trigger did not fire: record the observation (real wrong-author evidence barring that pair from further trigger attempts) and repeat the bootstrap through the next candidate.
- **Unavailable for now**: only when every candidate's comment-kind evidence is wrong-authored, or no remaining credential predicts the invoking user. Report `NEEDS_USER` once per repository, never issue the trigger through a pair observed to author comments wrongly — and **never carry the suppression for the remainder of the run**: record the escalation as **provisional and identity-based**, never as the repository refusing. A reviewer refusal is repository-scoped and stable, which is what earns it a run-long suppression; this is only what the run has observed so far (NOTES).
- **Re-evaluate trigger selection whenever the observed transport set or its authorship changes** — a new authored write establishing an identity, a credential reauthenticating, rotating or narrowing, a worker under a different validated transport set, a restart. These are the staleness rule's events, so this adds no watch of its own; re-evaluating on change is what keeps it from becoming a poll.

**A distinct posting identity does not retire the thread-root test or the no-new-threads rule** (Merge policy and review feedback). The test also separates feedback-to-act-on from conversation — a comment-kind distinction no author identity can make — and because availability degrades, its collision-closing job returns whenever the condition fails (NOTES). Both rules hold under either identity.

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

Projects are discovery surfaces, not execution graphs. Combine FE/BE/shared projects into one candidate DAG. Prefer an identifiable selected build-order/root issue before dispatching broad project work.

# Mandatory validation preflight

Before dispatching any **new** implementation worker, invoke `validate-backlog` on the entire bounded scope — `shallow` by default, deeper over the nodes the escalation rules below reach.

**The run's first preflight** is also where per-repository policy is read — each in-scope repository's `.claude/backlog-orchestrator.json`, per Per-repository policy configuration, which owns the schema, resolution, and failure rules. **Later preflights do not re-read it, and reuse that snapshot.** This is deliberately asymmetric with the rest of the preflight: a re-run after a frontier advance revalidates the *graph*, which the merge genuinely changed, while policy is owner-authored configuration that can authorize merges. Re-reading it there would make a mid-run merge the route by which a run adopts a config its own workers wrote — which is exactly what the section below forbids when it fixes the read to the repository state the run started from and bars re-reading for the remainder. A restart is a new run and takes a fresh snapshot.

Use the validator's normalized DAG as the scheduling graph. Do not let the execution runtime independently invent a competing decomposition.

That prohibition is about re-planning, not about evidence. A worker reporting a blocker it verified against its own issue is not inventing a decomposition — it is correcting one, from a position the validator did not have (see Outcomes). Accept an edge a worker verified; reject a runtime's attempt to reorder or re-scope the backlog.

**One validator warning is expected rather than exceptional, and must not be treated as a stop.** `dependency transport unavailable` says the probe found no dependency read on this run's transport — GitHub in a container without an authenticated `gh`, today; the same tracker elsewhere may not be in this class at all. It is not a boundary you can prove later, so holding paths for it would halt every GitHub backlog permanently. Dispatch may proceed, on three conditions: record it on the run's state, carry it into **every** dispatch prompt so no worker reports a false visibility disagreement or waits for a proof that cannot exist, and state it wherever this run reports readiness — a READY computed from prose alone is a narrower claim than a READY computed from a corroborated graph, and only saying so keeps the two distinguishable.

Results:

- `PASS` -> proceed;
- `PASS_WITH_WARNINGS` -> proceed only where warnings do not make ordering unsafe;
- `FAIL` -> stop affected paths; continue only validator-confirmed independent safe branches.

One warning is never proceedable at any level: **unproven relationship visibility over dispatchable scope.** A current validator returns that as `FAIL`, but treat it as blocking wherever it arrives, including from an older validator or another tool. Every other warning can be weighed because you can see what it is about; this one asks you to weigh what you cannot see, so "it probably does not affect ordering" is not a judgement available to you.

**The one exception is `dependency transport unavailable`, above** — and it is an exception because it fails the sentence's own test. That rule bites where a transport *might* be short and you cannot tell by how much. Where the tracker exposes no dependency read at all, you are not being asked to weigh something invisible: you know exactly what you cannot see, uniformly, for every issue, until the capability ships. Blocking on it stops every GitHub backlog forever rather than making one safer. Do not let the general rule swallow it — that is precisely how this correction gets undone by a reader applying the stricter-sounding line.

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

Escalation changes the **mode** of the preflight, never whether one runs, and it reads more deeply *within* the bounded manifest — it never widens scope. `PASS` / `PASS_WITH_WARNINGS` / `FAIL` are handled exactly as above at either mode, unproven relationship visibility stays unproceedable at either mode — with the same `dependency transport unavailable` exception, since a deeper read cannot conjure a capability the tracker does not expose — and the deeper read consumes model budget, not the 12-new-issue budget.

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

- maximum concurrent implementation workers (`concurrent-workers`): **4**;
- maximum newly started issues per invocation (`new-issue-budget`): **12**;
- maximum implementation attempts per issue (`implementation-attempts`): **2 total**;
- maximum strongest-model *implementation* escalations per issue (`model-escalations`): **1**;
- maximum CI repair cycles per PR (`ci-repair-cycles`): **2**;
- maximum review-fix cycles per PR (`review-repair-cycles`): **2**;
- maximum settle-finding repair cycles per PR (`finding-repair-cycles`): **2**;
- maximum strongest-model repair rounds per PR (`repair-model-escalations`): **1**;
- maximum lost-worker redispatches per issue (`lost-worker-redispatches`): **1**;
- automatic merges (`auto-merge`): **disabled** — the opt-in invariant 12's gate requires;
- requesting the `settle-outstanding-decisions` walkthrough at settle (`auto-request-settle`): **enabled**. The option gates only whether this run makes the request; whether the walkthrough may actually ask stays with that skill's attendance precondition (see Settled tranche).

These are the built-in defaults. Two mechanisms override them, and the precedence is stated here and nowhere else: **an explicit invocation argument beats repo config, which beats the built-in defaults — for every key but `auto-merge`.** For `auto-merge` the repository's opt-in is the only route to a merge, exactly as invariant 12 states: an invocation argument can switch `auto-merge` off for a run, narrowing the gate, but never on — an invocation cannot open it. Without the exemption, an invocation could authorize merges in a repository that never opted in, which is precisely what invariant 12 exists to prevent.

Dynamic Workflows do not override these limits. Do not increase concurrency merely because the runtime can fan out more agents.

The concurrency number is a ceiling, not a target. Derive the level you actually run from machine capacity at startup — available CPUs, free disk against the container's fixed allowance, and whether each worker needs its own dependency install or test toolchain — and take the lower of the two. Decide that yourself and report it; do not ask.

When the bounded scope exceeds the 12-new-issue limit, do not ask which issues to drop. Start the first 12 in scheduling order — DAG readiness first, then how much downstream work each unblocks — and defer the rest, naming the deferred issues in the checkpoint output so the next invocation adopts them. A user who wants a different cap says so in the invocation.

When the 12-new-issue limit is reached, allow active workers/repairs to reach durable state, stop starting new issues, reconcile, and return a checkpoint. Restarting does not count already-adopted work as newly started.

Budget exhaustion on a node -> `NEEDS_USER`, not another speculative attempt — as an **outcome** where a CI, finding or implementation budget is spent, and as **items** where a review budget is: a spent `review-repair-cycles` produces deferred-repair items under a `NO_CODE_CHANGE` round (see Merge policy and review feedback), never a `NEEDS_USER` outcome for the PR. Continue unrelated DAG branches safely.

## Per-repository policy configuration

Personal and work repositories legitimately want opposite behavior from the same run — merge on settle versus leave every merge to the owner, a generous repair budget versus a tight one — so this policy belongs to the repository it governs, not to the run. A repository declares it in `.claude/backlog-orchestrator.json`:

```json
{
  "concurrent-workers": 4,
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

Every key is optional, and the values shown are the built-in defaults. One file carries every option the defaults list above names as well as the merge policy, deliberately: a second option surface is exactly how two mechanisms drift apart. If an option of this skill's is configurable at all, it is configurable here.

**There is no reviewer-identity option, and its absence is deliberate.** Whether a review comment may be auto-fixed is decided by what the comment asks for, never by who wrote it — see Merge policy and review feedback. A key that gated on the author was removed because it answered a question the kind test already answers, and answered it worse: it reserved fixable comments from vetted humans while admitting unanswerable design questions from vetted bots.

**It is policy that can authorize merges, so it is a config file and not prose** — never a `CLAUDE.md` paragraph, and never a project-level skill override (NOTES: why neither mechanism works).

### Resolution

**Policy resolves per PR, from the repository that PR lives in.** A run can span repositories — the manifest in one, PRs landing in several — and per-repo difference is the entire point, so there is no run-wide policy read once from the manifest's repo. In a tranche where one repository carries a config and another does not, the first repository's PRs follow its file and the second's follow the built-in defaults, in the same run, at the same settle. One config, resolved once and applied run-wide, would do the opposite of what the file is for: work-repo rules on a personal repo's PRs, or the reverse.

Keys scope to different objects, and each resolves from the repository that owns its object:

| keys | scope | resolved from |
| --- | --- | --- |
| `ci-repair-cycles`, `review-repair-cycles`, `finding-repair-cycles`, `repair-model-escalations`, `auto-merge` | per PR | the PR's repository |
| `implementation-attempts`, `model-escalations`, `lost-worker-redispatches` | per issue | the issue's repository |
| `concurrent-workers`, `new-issue-budget`, `auto-request-settle` | per run | the manifest's repository; an explicit issue set contained in one repository uses that repository; a multi-repo set with no manifest uses the built-ins |

Read the file at the validation preflight, once per repository in the bounded scope, from the head of that repository's default branch as the run finds it at start — and never again during the run. **This file can authorize merges, so it is owner-authored configuration, and a run must never honour a version written by one of its own workers**: not from a worker's branch, not from a PR, not re-read after a mid-run merge moves the default branch. The policy governing a run is the one in the repository state it started from; a config change takes effect at the next run's preflight. A restart's preflight is a fresh read — that is the restart re-deriving from durable truth, not a worker write leaking in.

A file that is absent means the built-in defaults, unchanged — the file is opt-in and absence is the common case. A file that is present but cannot be honoured **fails closed**, and since this file no longer carries a key whose built-in default is the permissive reading, closed and built-in now coincide for every key: an unparseable file resolves to the built-in defaults for that repository, reported as unreadable in the checkpoint output rather than guessed at, and an unrecognized key or a wrong-typed value fails the same way at key granularity — defaulted and reported, because a misspelled `auto-merge` must produce no merges, not a guess. Nothing needs a guard beyond that. `auto-merge`'s built-in `false` is already its closed end, so its misspelling produces no merges; the budget keys and `auto-request-settle` fall back to built-ins that grant no authority the owner withheld — a missed tighter budget costs bounded extra attempts and a missed settle opt-out costs a request made to a present user, where zeroing every budget on any stray key would turn a typo into a dead run rather than a closed one. **This simplicity is a consequence of removing the reviewer-identity key and should not be reintroduced casually:** any future key whose permissive value is its default brings back a fail-closed special case, because a corrupt file must never grant more than a parsed one would.

Report the resolved policy per PR in the checkpoint output, with its source — invocation argument, repo config, or built-ins — so an auto-merge is visible in the record before it is a surprise.

### Merge policy and review feedback

**`auto-merge`** — whether invariant 12's gate can open for this repository's PRs at all. `false` is today's behavior: the run never merges. `true` permits a merge only through the gate invariant 12 defines — the key is the opt-in the gate requires, never a bypass of its other conditions. This file is the only place `true` can come from: the precedence rule under Default usage safeguards exempts `auto-merge` from invocation override, so an invocation argument can narrow the gate, never open it. Execution mechanics, including the publish-before-merge step, live in Merge behavior.

**One grant covers every consumer of this key, `implement-issue` included, and that is deliberate.** The permission is scoped to the *gate*, not to the skill that evaluates it: `auto-merge` does not say "this orchestrator may merge", it says a PR this owner's agentic workflow produced may merge **when invariant 12's whole gate holds** — nothing outstanding in scope, green CI on the current head, no conflict, a clean review with no thread reserved for the owner, no outstanding recovery ref, not an explicitly held draft, a proven or answered-for dependency view, published before merging, and evaluated only once a summary has supplied the gate's `DECISION`/`MERGE_RISK` inputs. Every consumer defers to this section for all of it rather than carrying a copy, so a run that satisfies the gate is not riskier because a different skill drove it (NOTES: why not per-consumer keys). What the invocation-override exemption guards *is* a real distinction, and it stands: an argument's authority comes from whoever composed the prompt, a committed file from someone with write access to the repository.

The consequence is worth naming rather than discovering: a config written before a consumer existed grants that consumer too, from the moment the skills are reinstalled. An owner who wants no autonomous merging at all sets `auto-merge` to `false`, and an invocation argument narrows it for a single run.

**What the run may auto-fix is decided by the comment, not by its author.** A review thread is **repairable** when what it asks for is a code change this pass can make and verify: a rename, a missing guard, an off-by-one, a test, a lint fix, a bounded refactor the comment itself specifies. A thread is **`NEEDS_USER`** when answering it requires something other than a code change — a question about intent, a design or product judgment, a request for rationale, an objection needing a decision, or anything whose correct response is prose rather than a diff. The run fixes the first kind and escalates the second, whoever wrote it: a human reviewer's typo fix is repaired, an automated reviewer's architecture question is escalated. **There is no bot test and no reviewer allowlist.** Author identity predicts the *kind* of comment only loosely — automated reviewers ask design questions and humans file one-line nits — so gating on it reserved work the run could safely do while admitting work it could not. The judgment rule under CI/review repair is the same rule stated for the repair path, not a second gate: a thread that needs judgment is `NEEDS_USER` there for the same reason it is here.

**A review thread's root comment is feedback; a timeline comment is conversation.** This is the structural test that decides what the run treats as feedback at all, and it survives independently of anything above — it is not part of the removed reviewer policy and must not be removed with it. A review thread whose **root comment** someone wrote is feedback on the diff, and the run classifies it by the rule above; a comment on the PR's conversation timeline (a GitHub issue comment) is conversation, not feedback to act on. The test is thread-rootness, not "is it a review comment" — a reply inside a thread is also a review comment, and the run posts replies into threads constantly, so the weaker test would qualify the run's own replies. The invoking user's own rooted thread is feedback like any other and classified by the same kind test: their instruction directs the run, and a question they root is still a question, answered by them rather than guessed at.

**And the run never opens a review thread on a PR it is driving.** It posts timeline comments and replies into existing threads; it never roots a new thread. Nothing today makes it want to, which is exactly why this must be a stated rule rather than an observed habit: wherever no distinct posting identity is available the run posts as the invoking user's own account (see Posting identity — that degraded path is the common case), so the moment anything it does can root a thread, a run-authored root becomes indistinguishable from an instruction and the test above silently breaks. The prohibition is what keeps the discriminator true by construction rather than by accident.

**That comments this run authored are never reviewer feedback is a consequence of the two rules above, not a mechanism of its own.** No author test could provide it — on Posting identity's degraded path the orchestrator's comments carry the invoking user's login and `author_association: OWNER`, and the bot test sees a human account — but the thread-root test does not need one: every review comment the run posts is a reply (the prohibition above), and a reply roots nothing; every timeline comment it posts — worker reports, repair replies, trigger comments — is conversation by kind. Do not restate the carve-out as a parallel rule anywhere; it holds exactly as long as the root test and the no-new-threads rule hold, and would drift the moment it were maintained separately. A restart gets it for free, too: thread structure and comment kind are durable forge state, readable after the predecessor's record of its own writes is gone — where an author-side carve-out would have to fall back to recognizing this skill's own report and reply forms.

A thread classified `NEEDS_USER` is **reserved for the owner**: never resolved and never answered on the run's own authority, and never auto-fixed **for the part that wants an answer** — a comment asking for a diff *and* prose is repaired and still reserved, its fix pushed and its thread left open (`resolve-pr-comment`, *A comment can want both*); what is reserved is the question, and a pushed fix never stands in for one — the question is put to them rather than guessed at, reported in the checkpoint output with the thread's URL, its root author, what it asks, and **what its item kind carries**: a question item, the draft reply the classifying pass produced for it (`resolve-pr-comment`, *The draft reply*), carried through verbatim, so the owner answers from what the run already worked out rather than starting cold; a deferred-repair item, the change it asks for and **no draft** (`repair-pr`), since a thread wanting a diff has nothing to answer and a draft demanded of it could only be invented. `settle-outstanding-decisions` consumes the **question items** at settle as intent questions, and the draft is what lets it put one to the owner answerably in a single question. **It does not consume a deferred repair**, and cannot: its bar takes `NEEDS_USER` items that are choices rather than work, and a deferred repair is work (`settle-outstanding-decisions`, *What qualifies as an outstanding decision*). Such an item is reported for the owner to apply themselves or to lift the budget on, rather than implying the walkthrough will clear it. A reserved thread does not block settlement — the run cannot be required to resolve what only a person can answer — but it is an unresolved actionable finding everywhere else that concept is consumed: it fails invariant 12's clean-review condition, so the gate does not open over it, and it is a `NEEDS_USER` item outstanding, which that gate independently refuses. Both conditions now name the same threads, which is why removing the reviewer policy did not loosen the gate. **A reservation is run state, so it ends in two ways within a run and does not survive one.** Invariant 1 classifies the per-PR block as a cache: a later invocation holds no reservation at all, re-classifies the thread from the forge, and repairs it where it now has budget — which is what makes *lift the budget* an actionable next step on a deferred repair rather than advice with no mechanism behind it. Within a run, the two ways are read from the forge when the gate is evaluated: the thread is resolved — by the owner, or by the review workflow where a reviewer's follow-up superseded the question and the re-classified thread wanted only a diff — or an answer is recorded on it, **a walkthrough ruling (`settle-outstanding-decisions`, *Recording the ruling*) or the owner's own reply in the thread, which the already-ruled test treats alike** (*What qualifies as an outstanding decision*), **and** any code change it implies has been pushed by the `finding` repair its row routes to. Counting only the ruling would hold the gate over the commonest case: an owner who simply answers the reviewer leaves a record that retires the question, so the walkthrough has nothing left to ask and nothing else would clear it. A rejected-draft record ends nothing. Ending a reservation does not make the thread unhandled — a settlement record is not new content — so nothing re-dispatches it. Without this the gate reads a thread as reserved after the owner has answered it, which is the deadlock the carve-out exists to prevent, one step later. The classification is made where the thread body is actually read — `resolve-pr-comment` owns it, `repair-pr` propagates the items, and this skill reports and gates on them. Nothing here replaces the repository's review *trigger* convention, which `create-pr` owns: triggering a reviewer and acting on its findings are separate concerns.

# Model and skill policy

The orchestration/lead context may use the strongest available reasoning model.

Normal implementation and repair workers must use **Sonnet explicitly** when the runtime supports per-worker model selection. Do not accidentally inherit the lead's stronger model.

At most one strongest-model implementation escalation is allowed per issue for a reasoning-heavy repeated failure (`model-escalations`).

**Repair escalates on evidence, not on exhaustion** (`repair-model-escalations`, per PR). Dispatch a repair round on the strongest available model when the round about to be dispatched carries a finding on a **locus an earlier repair on this PR already wrote** — a reshaped version of a finding an earlier round addressed, or a new finding in text an earlier repair authored. That is the signal that the previous repair was shallow and the root was never understood, and it is the one place in the repair path where model strength is the binding constraint. Everything else about the round is unchanged, and Sonnet remains the default for all the others.

The trigger is that evidence and nothing else, so it fires on the earliest round where the evidence can exist rather than after the cheaper rounds have been spent, and it never fires merely because the budget is nearly gone. Exhaustion and non-convergence are different failure modes wearing the same counter: a round that fixes real findings while genuinely new ones keep surfacing is breadth, and a stronger model buys nothing there; a round whose fix draws a reshaped finding back onto the same locus is a reasoning failure. A count-based ladder cannot tell them apart (NOTES: the observed spec-PR case).

**The round cap is a separate mechanism, and an escalated round still consumes its repair cycle.** `ci-repair-cycles`/`review-repair-cycles`/`finding-repair-cycles` bound unattended churn, which is model-independent; a round that skipped the counter because it escalated would make "escalate" a way to buy extra rounds. At the round cap the PR goes to the owner whatever model ran. `repair-model-escalations` bounds only how many of a PR's rounds may be escalated, so exhausting it does not end the repairs — it returns them to Sonnet.

**The dispatching layer owns the decision.** `repair-pr` never selects or escalates its own model, exactly as `implement-issue-core` returns a reasoning-heavy repeated failure instead of escalating one. The evidence is readable here from durable state — the PR's own commit history against where each finding sits — so a restart evaluates the same trigger its predecessor would have; the repair worker reports what it saw as corroboration, not as the record.

Implementation workers require `implement-issue-core` and `create-pr`.
Repair workers require `repair-pr` and, for review fixes, `resolve-pr-comment`.
The parent layer requires `validate-backlog` at preflight, and `summarize-tranche`, `settle-outstanding-decisions` and `plan-merge-order`, in that order, when the run settles — the middle one only while `auto-request-settle` is on (see Settled tranche). It also requires `merge-stack` wherever any repository's resolved `auto-merge` leaves invariant 12's gate reachable — checked at the run's first preflight, where policy is read, rather than discovered at the gate, exactly as `implement-issue` checks it for its one PR: the stack rules require that skill for any merge or restack, so a run that could merge without it holding would have no compliant mechanism for the very merge the repository authorized.

Where `merge-stack` is unavailable with the gate reachable, the parent does not stop the tranche the way a one-issue run returns `BLOCKED` — that asymmetry is deliberate, not drift: `implement-issue` blocks one issue's worth of nothing at an invocation its user is typically attending, while blocking here trades twelve issues of authorized implementation for the tool their optional final step needs. It does not improvise a raw merge either. Apply the documented default: the gate is unreachable for this run — the narrowing direction an invocation is always permitted — reported at the preflight and again wherever the gate would have been evaluated, with a closing `NEEDS_USER` naming the missing skill so the owner can install it or keep merging themselves. A parent-required settle skill that is unavailable degrades the same way, never by improvisation: that step's outputs are absent and reported, and a gate whose summary inputs never existed stays shut (see Merge behavior).

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
- `NEEDS_USER`
- `NOT_READY`

Prefer durable evidence in this order:

1. merged linked implementation PR + tracker terminal state;
2. open linked implementation PR;
3. remote issue branch with pushed checkpoints;
4. runtime/workflow-local state;
5. local worktree only.

A cloud worktree is ephemeral. Never claim restart safety for unpushed local changes.

**An outstanding recovery ref overrides all of it, completion evidence included.** Enumerate the recovery refs matching an issue's branch (see Checkpoint compliance) **before** classifying it, not after: a merged PR with terminal tracker state is the strongest evidence in the list and is exactly what an issue carrying rescued, unlanded work looks like from the outside. So an issue with a ref outstanding against it is never `DONE`, whatever items 1–5 say. This is the durable half of that rule — the `NEEDS_USER` a run raises for it lives in run state, which invariant 1 classifies as a cache, so without the check here a restart re-derives `DONE` from the merge and drops the only copy of that work while reporting the issue complete.

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
7. state branch protection explicitly: the worker pushes **only** to its assigned branch, never to the repository's default branch or to any branch it was not assigned — including to fix or revert something it just broke. A worker convinced a change must land on the default branch directly stops and reports instead of pushing it. The branch assignment does not imply any of this (NOTES: the observed default-branch push);
8. countermand interactive questions explicitly, and state the substitute: the worker never calls `AskUserQuestion` or otherwise stops to put a question to a human. Nobody watches an unattended worker's permission prompts, so the call does not pause the worker — it deadlocks it (NOTES: the observed twenty-minute deadlock). The prohibition alone is half the instruction, because a worker holding a genuine open question still has to put it somewhere — but where it puts it depends on whether its own skill already owns that stop. `implement-issue-core` returns `BLOCKED`/`BLOCKED_EXTERNAL`/`NEEDS_USER` rather than guessing when scope is materially underspecified, a supplied base is invalid, a prerequisite cannot be observed, or a product decision needs approval; there the worker returns and documents that outcome. **The substitute never licenses implementing past a stop a worker skill prescribes**, because a guess at one of those produces a PR built against a missing dependency or invented product intent — worse than the deadlock it was meant to avoid, and harder to see. For every other open question — the ordinary judgement calls a task leaves open — tell it to pick the most defensible option, implement that, and record the question, the choice, and the reasoning on the PR, where a human can overturn the call in review. The prohibition on asking is absolute in both cases; what differs is whether the worker proceeds or returns. Where this countermand goes is decided with the others (see Countermanding the worker's ambient supervision posture, below);
9. include **the dependency context used to judge this issue READY** — the blockers considered, how each was resolved, which transport and credential produced that view, and **the provenance of each edge**: your own native read, or a blocker you established from a previous worker's evidence and recorded outside native metadata. The worker compares its native read against yours, and an edge you deliberately kept out of native metadata is one its native read is supposed to lack; unmarked, that comes back as a visibility disagreement against the very corrections you recorded. **Mark the context as your complete READY dependency set**, because it is: unmarked context is treated as a targeted answer whose omissions mean nothing, so an edge you never saw would come back unreported and your frontier would stay wrong. State too whether the read behind it had **proven visibility** for the boundaries this issue's blockers could cross. Marked complete, that is what makes the worker's own silent read meaningful — otherwise its three sources collapse to one unproven native read, agree because two are empty, and readiness rests on an absence nobody established. You will normally have the proof, since an unproven dispatchable boundary is a preflight `FAIL`; where you are dispatching without it, saying so is what lets the worker stop instead of building against it;
10. include **authorization membership**: the bounded authorized set, or a per-blocker flag for whether each is inside it. Only you know this, and the worker's block outcome turns on it — without it, an external-looking prerequisite you did authorize comes back as an out-of-scope wait and you skip the frontier re-derivation it needed. A worker given nothing defaults to the stronger outcome, which is safe but costs you the distinction;
11. include, on any runtime where a worker's return value does not reach this run, the requirement that it **record the judgment part of its result on its PR before returning** — not on the issue, and not the run state, which the session record and the branch already carry; see How a worker's report actually reaches you. **Do not enumerate what the report contains. State it as a subtraction, because enumerating it fails in one direction.** The report is `implement-issue-core`'s entire Output contract *minus* what this run can already read for itself — the branch, the PR, and the session record's `status_bucket`, `pending_action`, `task_summary` and `post_turn_summary`. Everything else in that contract is judgment, and judgment is exactly what has no other carrier.

The reason for the subtraction is empirical: four review rounds against an enumerated list each found a different item missing from it, and every one of them was something a **clean** run still has to say (NOTES: the four omissions, kept there as the shape to watch for).

Any terminal outcome reached before a PR exists writes nothing and simply returns — investigating it, and recording anything that comes of it, is this run's job, not the worker's;
12. dispatch Sonnet worker with `implement-issue-core`.

A dispatch prompt that enumerates a required process is followed literally: a default left out of that enumeration is a default skipped, and the worker will accurately report that the task never asked for it. The same literalism decides what the worker does with instructions this run did not write (see Countermanding the worker's ambient supervision posture, below). Every dispatched prompt must therefore carry the automated review trigger instruction — `create-pr` owns the trigger rules, do not restate them here — unless this run explicitly defers review. Deferral is a conscious choice recorded in run state, naming what review is owed and on which PRs; it is never an omission.

**By the same literalism, every dispatched prompt carries the run's whole posting-identity map** — every (transport, credential) entry, not one selected pair, plus the instruction to read the worker's own first authored write back and report what it observed (see Posting identity). Passing one entry is not a smaller version of this: the worker's `create-pr` may need an agent-authored entry to create the PR and an invoking-user entry for the author-sensitive review trigger, so selecting here either gives the PR the wrong author or leaves a valid trigger path unavailable, and the worker cannot recover what it was not sent. The worker's report is itself an authored write, normally a PR comment, and it is the most common one this run causes: enumerate the requirement to report while omitting the identity to report under, and the worker posts it as the invoking user, correctly, because the prompt never asked otherwise. A distinct identity observed at `create-pr` does not reach that write on its own.

Issuing the trigger is not the end of that step. Confirm it took effect: a review from the repository's automated reviewer materializes within a bounded window, and the reviewer does not instead answer indicating it is not configured or not authorized. Verify per attempt, on every PR — one review arriving elsewhere in the run is not evidence the trigger works. A trigger that silently no-ops is worse than one that fails loudly, because the run then reports PRs as reviewed and clean when nothing reviewed them.

An elapsed window is not a refusal. A reviewer that is merely queued or slow leaves the PR unreviewed-pending, reconciled through ordinary event supervision and visible as such in checkpoint output; only an explicit not-configured/not-authorized response marks the trigger unavailable.

A refusal is first evidence of the wrong write path, not of insufficient authority. Where the platform offers more than one way to perform the write, reissue the trigger once through a different available mechanism before drawing any conclusion. Where the platform exposes only one write mechanism, the available paths are already exhausted. Do not otherwise repeat the same write path: it will not start working on the next PR, and each failed attempt leaves trigger and refusal comments behind on the PR.

Only once every available path has failed, record it as `NEEDS_USER`: surface once, with the affected PRs, that review could not be triggered, and stop issuing the trigger for the remainder of the run in that repository. One escalation per affected repository, not one per PR; suppression is scoped to the repository that refused, because review configuration is repository-specific. Never conclude from a refusal alone that review cannot be triggered from this run at all — that conclusion is cheap to draw, hard to disprove afterwards, and costs precisely the reviews it skips.

This generalizes past review triggers. When the platform offers several ways to perform the same write, prefer its first-class integration tooling over raw transport: attribution, permissions, and downstream automation can all differ between them, and the difference is invisible until a write is made and read back. Where identity matters to a workflow, verify it by inspecting an object the run actually created and reading its author — never by asking the credential who it is, which can answer differently from what its writes carry.

Under Dynamic Workflows, provide these constraints to every workflow worker explicitly. Do not let a worker select another backlog ticket when it finishes.

## Countermanding the worker's ambient supervision posture

Prompt literalism cuts both ways. A prompt that omits a required default gets a worker that skips it; a prompt that omits a required **contradiction** gets a worker that follows whatever its own session already told it to do. A Claude Code Remote worker session inherits a system prompt instructing every session to subscribe to PR activity and to schedule a self check-in roughly an hour out, re-arming it silently until the PR merges. That instruction arrives with the runtime rather than from any skill this run dispatches, and it is correct for the sessions it was written for.

So every dispatched prompt — implementation and repair alike — must state that this run owns PR supervision and the worker does not: do not subscribe to PR activity, do not schedule a check-in, trigger, routine or wake of any kind, **and do not watch GitHub for state that changes after its own work is done** — no polling for CI, review, comment, thread, issue or merge state — and return after pushing and reporting, **even where the worker's own session instructions direct otherwise**. Name the override rather than merely stating the rule.

**That ban does not reach a worker verifying its own writes, and must not be written so it does.** The worker skills' contracts require exactly such reads, and this run consumes their results: `create-pr` reads its PR back for linkage and its trigger comment back for comment-kind identity, and `repair-pr` confirms the replies and resolutions it was asked to make and counts the threads still unresolved (see Posting identity, and the read-back the worker contract already mandates). The line is **watching versus verifying**: reading back what this worker just wrote, once, is verification and stays; reading again later to learn whether anything has changed since is supervision, and belongs to this run (NOTES: what cutting those reads costs this run).

**But put it where it can actually outrank what it countermands.** A dispatch prompt is a task instruction, and a task instruction is the weaker side of an argument with a session's own system prompt — telling a worker in its task to disregard its session instructions does not, by itself, make it do so. So on a runtime where this run *builds* the worker's session, write the countermand into that session's system prompt: `create_session` takes an `append_system_prompt` for exactly this purpose, and it is the only lever here that sits at the same level as the instruction it is answering. The dispatch prompt then restates it rather than carrying it alone.

Branch protection (step 7 of Before dispatch) belongs at this level too. Where a push may go is a rule the worker applies exactly when something has gone wrong — mid-mistake, mid-revert — which is when a task instruction is at its weakest against the session's own posture. On a runtime that builds the worker's session, write it into `append_system_prompt` alongside this countermand, restated in the dispatch prompt in the same way.

The question posture (step 8 of Before dispatch) is the third countermand that belongs here, for the same reason: asking the user is correct behavior in the attended sessions the worker's instructions were written for, and a deadlock in a fan-out where nobody will ever answer. Apply "Read the field that reflects the blocked state" (Blocked workers) rather than restating it here, and archive-and-redispatch for a prompt nothing can answer is a branch of Blocked workers in its own right. A documented assumption is recoverable; a deadlocked worker is not (NOTES: the unreachable-worker incident in full, and why the substitute is what made the redispatch succeed).

The tier decides which lever exists, and only one tier has the problem:

| runtime | where the countermand goes |
|---|---|
| remote worker session | `append_system_prompt` at creation, restated in the dispatch prompt |
| subagent, Dynamic Workflow agent, serialized | the dispatch prompt is the whole of it — none of these inherits a session posture to countermand |

Expect this to reduce the behavior, not to eliminate it. Appending does not delete the instruction already present, some environments ignore the parameter outright, and a worker resolving two same-level instructions may still arm a wake or stop to ask. That residue is why **Blocked workers** is a backstop rather than a redundancy: the run has to be able to notice a worker that did either anyway and clear it, not merely to have forbidden it.

**And do not read a quiet session list as proof this worked — the quiet case is the expensive one.** Where workers inherit an allowlist that grants the trigger tools, a worker that arms a wake can also disarm and re-arm it, so it never blocks on anything: Blocked workers never sees it, the session list shows nothing stuck, and the worker wakes every hour to re-read a merged PR, find nothing, and re-arm — for as long as the account will pay (NOTES: the $33.45 and $59.60 sessions). A worker that arms a wake it *cannot* disarm at least blocks visibly on the permission prompt, where Blocked workers finds it. So an absence of blocked sessions is the signature of the costlier branch, not evidence the countermand held. What catches both branches is the release reconciliation step of the parent supervision loop — reading the runtime's session list, not the run's memory — and the state block, which reports every wake a worker was observed to arm.

Do not leave this to the worker skills (NOTES: how a worker satisfied the duration-only wording while leaving a watcher armed). The gap is **delegation, not duration**, and this prompt is the only place in the system that sees both instructions at once.

It is also the only place the problem is visible. The instruction being countermanded appears in none of the worker skills, so searching them for the behavior finds nothing that could be causing it.

The parent arming its own subscription and check-in when a run settles (see Arming the wait when nothing is in flight) is this same ownership stated from the other side, not an exception to it. One watcher, held by the layer that owns supervision.

Two costs — duplicated supervision, and a worker deadlocked on the disarm prompt after its own work merged — and the second is the one observed (NOTES).

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

If Claude Code's background PR behavior has auto-merge enabled, it will merge PRs itself once checks pass — a merge decided outside invariant 12's gate, on CI state alone, whatever the repository's policy config says. **Confirm it is off before relying on that background behavior for CI/review surfacing.** There is no user carve-out here, because **surfacing and merging are separate grants**: authorizing the run to use the platform's event stream is not authorizing merges that skip every gate condition but one. A watcher that merges on green cannot see an unclean review, a tranche-level `DECISION` or `MERGE_RISK`, an explicitly held draft, or a repository that never opted in — so a session-level authorization to use the surface would silently authorize merges no one evaluated.

A user who wants merges to happen without them has a designed path for it: the repository's `auto-merge` key and invariant 12's gate, which apply those conditions. Point them there rather than at the platform toggle — the watcher is a strictly weaker duplicate of a mechanism that now exists. Where the platform's auto-merge cannot be turned off, do not rely on that surface: subscribe explicitly instead (`subscribe_pr_activity`), and report any merge it performs as a platform merge outside the gate, never as gate-approved.

Once an implementation worker reaches `PR_OPEN`, release that implementation worker — on a remote-session runtime that is an archive call, not merely ceasing to message it (see Releasing a worker). Long-lived PR supervision belongs to the parent/runtime orchestration layer.

**One PR, one supervisor, and it is this run.** The lifecycle is:

```text
parent  -> dispatch implementation workers (a Dynamic Workflow only for this fan-out, only on the user's opt-in)
worker  -> implement -> open PR -> report it back -> stop reading GitHub -> released
parent  -> adopt the PR, arm its subscription, and own it from there:
           react to delivered events, check in occasionally and consolidated,
           and resume only the specific worker a change actually needs
```

A worker never supervises its own PR, and a Dynamic Workflow never supervises anything: it returns its fan-out results and supervision is the parent's from that moment (see Parent supervision loop). No PR is ever supervised by two parties at once (NOTES). That is about who watches, not how many mechanisms they hold: one owner arming both a subscription and a bounded check-in over the same PR is what Arming the wait when nothing is in flight requires, and is not a second loop.

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
finding repair cycles used/remaining
stack parent/children
event subscription: armed/unavailable
last read: <time> — event / poll / mutation by this run
worker session: <session id, or none on tiers without one> — archived: yes/no
```

The worker-session line is what makes the loop's release reconciliation a lookup instead of guesswork: without a session id on the record, matching sessions to PRs means fuzzy-matching session titles, which is what an actual recovery had to script its way through (NOTES).

## Event handling

**Arm the subscription when the PR enters the tracked set, not when the run settles.** A PR becomes trackable the moment this run learns of it — a worker's return, or on a remote runtime the pull that stands in for one — and every rule below about consuming events assumes something is delivering them. Nothing is, until this run says so: `subscribe_pr_activity` is a call the parent makes per PR, and Claude Code's background PR watch covers only what it already surfaced. Arm it as part of adopting the PR, alongside recording its head and base, and record the result in the per-PR block above — a PR whose subscription is `unavailable` is one this run must poll deliberately rather than assume it will hear about.

Arming later is not equivalent. Between a PR's creation and its subscription the run is blind to exactly the events it most needs: a merge someone performs, a review that lands, a base that moves underneath it. A tranche whose first PRs were subscribed and whose later ones were not looks identical from the inside — events keep arriving, they are simply the wrong ones — and the run reads its own quiet as nothing having happened. The settled-state arming under Arming the wait when nothing is in flight is a backstop for the empty-frontier case, not the primary mechanism, and treating it as the moment subscriptions begin leaves every PR unwatched for the whole of its active life.

**No no-change result leaves this run without passing a preflight over the subscription column.** Everything above already mandates the arming; what it cannot do is make its own absence visible, and an observed run proved that absence is silent: "no events because nothing happened" and "no events because nothing was listening" produce the same quiet, and it was the owner who noticed, not the run (NOTES: the 18:20Z incident). So before reporting or recording any no-change result — a supervision cycle that found nothing, a check-in that fired and found nothing, a settled checkpoint claiming all quiet — enumerate the tracked PR set with each PR's `event subscription` state from the per-PR block. A PR whose field was never recorded is a known blind spot the result must name as such, never a quiet PR: an unrecorded field means the run cannot say whether anything is listening to it. A PR at `unavailable` is different — the fallback below sanctions polling it, and the arming paragraph above requires it — so it counts as quiet only once that deliberate poll has actually run against it this cycle, and it is reported with the time it was last observed. A polled PR carries a staleness bound a subscribed one does not, and a no-change result that hides which of the two it rests on is the report the incident above produced. An `unavailable` PR that was not polled this cycle is a blind spot exactly as an unrecorded one is. This adds no rule the block and the arming above do not already state; it is the assertion that catches them being skipped.

Prefer platform-native/promoted PR events (Claude Code's background PR watch behavior, or an explicit subscription such as `subscribe_pr_activity`) for:

- CI/check completion/failure;
- review/comment activity;
- branch/head changes;
- merge/close events.

If those are unavailable, fall back to other event subscriptions, then parent polling — bounded as the discipline below defines, never as the reader's own reading of "bounded" (NOTES).

The parent remains the **policy owner** even when the platform performs the observation. The platform may surface that CI failed or review feedback arrived; this skill decides whether budgets allow repair and what worker to dispatch.

Do not keep one Sonnet worker alive per PR merely to wait.

### API budget and read discipline

The forge meters REST and GraphQL as two allowances, exhausted independently, and each belongs to the **credential rather than to this run**: every run, session and worker authenticating as the same identity draws on the same buckets (NOTES: the incident and its arithmetic).

**Attribute a read to a bucket by evidence.** Where this run selects the endpoint, the bucket is known and nothing is inferred. Where a first-class tool hides it, the request's shape is a **fallible prior** — never sufficient alone to keep calling an exhausted bucket or to suppress a healthy one. **Observation settles it**: a rate-limit response names the resource it refused, and a tool refused beside one that succeeded under a known-exhausted bucket attributes both. Record that per tool, as transport visibility is recorded per credential, and let it override the prior (NOTES).

**Treat remaining allowance as shared and falling.** Leave headroom rather than spending down to the guard. Where the remaining figure drops by more than this run's own reads account for, read that as another run on the same credential and back off harder rather than proportionally — and report the sharing, which is the owner's to remedy rather than this run's.

**Read on a change signal, not on a schedule.** Re-read a PR only when: an event named it; this run just mutated it; its poll is due under the `unavailable` fallback; **a scheduled check-in has fired and this PR is in its set**, subscribed or not; or a decision this cycle turns on a field the per-PR block does not carry. Otherwise the block **is** the answer, and `last read` is what distinguishes the two (NOTES: why the check-in belongs on this list, and what a PR waiting on CI costs without it).

**One read per PR, not one per concern — and not one nested read of everything.** Take what the cycle needs from a PR in a single request, take the PRs that are due together, and let later loop steps consume that pass rather than issuing reads of their own.

**Cheapest read that settles the question.** Expand into review threads, comment bodies or check logs only for a PR that actually moved. Optimize total API work for the decision, not GraphQL usage as such (NOTES).

**Ask only for what changed, where the transport offers a way to:**

- prefer a `since`-bounded read that answers what moved across a repository in one request to one request per PR. One endpoint takes one bound: **use the earliest `last read` in the batch and filter the returned records per PR** (NOTES);
- send a validator — an ETag or `If-Modified-Since` — where the transport supports one, stored alongside `last read`;
- thread state has no incremental form, so its saving is not asking until a detector fires, and then only for the PRs that detector named;
- where the preferred tool offers neither and a lower tier does, descend for that read, recorded as Transport precedence requires of any deliberate descent.

**Fan out implementation, never supervision.** The parent makes the supervision reads, once, for all active PRs together. No worker reads overlapping metadata for the same repositories, and **no agent is dispatched for the purpose of making a read this run could make itself** — least of all to re-ask a question this run was just refused (NOTES). That is about dispatching *as a way of reading*, and does not reach the skills this run is required to invoke: `validate-backlog` at preflight and the settle skills read as part of doing their own analysis, and are mandatory where they are mandated, budget or no.

**On a rate-limit response, a secondary-limit response, or an allowance too low to finish the cycle**, defer **every read drawing on that resource** until it resets — a read that resource cannot serve has no essential case, and "this one is needed" is how a cycle spends its way through a refused bucket. A secondary or abuse limit is tied to no resource and stops both. Finish writes already in flight, report the deferral, and **never arm the resuming wake before the reset — or a supplied `Retry-After`, whichever is later**. That is a floor, not a target: how it composes with the check-in's backoff is stated once, under Arming the wait when nothing is in flight, and not restated here (NOTES). **A response that supplies neither bound sets no floor at all** — a secondary or abuse limit, tied to no resource as above, has no reset of its own, and it can arrive without `Retry-After` — and the deferral then contributes nothing to that composition: the backoff's own next step stands, and its 20-minute first step already outwaits the pause such limits ask for. No floor never means no wake — a watch forbidden to wake before a time nothing names would be neither re-armable nor able to spend its budget, and later PR changes would go unobserved forever (NOTES).

**A wake that defers under that rule draws on the single check-in budget in Arming the wait when nothing is in flight** and carries no budget of its own. Whether it counts or clears is that rule's to state and is not restated here — it turns on what the wake observed, so a wake that saw a delta before being refused is not made unproductive by the refusal. On exhausting the budget this way, stop re-arming and report it as blocked on the allowance, naming the contention — never as settled or quiet (NOTES: why this was a second counter, and what the seam between the two cost).

**None of this outranks the no-change preflight.** A PR nothing is listening to is a blind spot whether or not the budget is tight; a due poll skipped to save calls reports as unread, never as quiet; a deferred cycle reports as known-stale.


# CI/review repair

On an actionable CI failure:

1. retrieve the smallest useful failure context;
2. decide whether it belongs to this PR;
3. if repair is justified and budget remains, allocate an isolated checkout of the current PR branch;
4. dispatch one `repair-pr` worker with `repair type = ci` — Sonnet, or the strongest available model where the non-convergence trigger has fired and an escalation remains (see Model and skill policy);
5. adopt its pushed remote head, **and merge every posting-identity entry it returned into the run's transport-and-credential-keyed map** (see Posting identity) — a repair runs on its own transports, so this is the run's only evidence about them;
6. increment the CI repair cycle;
7. release the repair worker (see Releasing a worker) and resume event supervision.

External/flaky failure with no justified code change does not consume a repair cycle.

On unhandled review feedback — a thread roots on the diff, this run did not author it (a consequence of the thread-root test), **it is still unresolved**, and it is not already recorded as **handled — reserved or no-action — unless new content has arrived on it since**. **A thread this run repaired and resolved is handled by being resolved**, and naming that matters because the recorded states enumerate only the two outcomes that leave a thread open: a predicate listing them alone re-groups every thread the run just fixed, on every cycle. **New content means a write this workflow did not author.** A reviewer's follow-up re-opens the thread; a settlement record does not — an approved answer, a recorded choice or a rejected-draft record posted into a reserved thread by `settle-outstanding-decisions` is this workflow answering the thread, and treating it as new content would re-admit the thread, re-classify the question that was just answered, and re-offer a draft that was just rejected, all while holding the merge gate. This is the same principle as the thread-root test's carve-out that comments this run authored are never reviewer feedback (Merge policy and review feedback), applied to re-admission rather than to actionability. Both classifications mark a thread handled: a reserved one awaits the owner, a no-action one wants nothing from anybody, and a predicate that recorded only the first re-dispatches every acknowledgement on every cycle, without bound, because a classify-only pass consumes no cycle. The exception belongs in the predicate and not only in step 5's mechanism sentence: a reviewer who follows up inside a reserved thread with a concrete change request has made it unhandled again, and a predicate that excludes the thread on its root's old classification never reaches the step that would have re-admitted it. Author identity decides nothing (Per-repository policy configuration owns these rules). **Dispatch on any such round, including one where nothing looks repairable from the outside.** A reserved thread is never dispatched *for repair* — but reserving it is a conclusion, not a precondition: classification and the draft reply need the thread body and the code around it, which is the dispatched pass's context and not the parent's (Per-repository policy configuration). A parent that triaged a round as question-only and skipped dispatch would reserve it with no draft, which is the one outcome the reservation exists to avoid:

1. group the coherent current review round;
2. allocate an isolated checkout of the current PR branch. **The repair budget gates repairing, not classifying:** dispatch even where `review-repair-cycles` is zero or spent, because a classify-only pass consumes no cycle (step 5) and an unclassified thread has no draft, which leaves the settlement path nothing to clear its gate with. With the budget spent the pass classifies and drafts but repairs nothing: threads that would have been repairable become `NEEDS_USER` on budget grounds — an **item** under the round's `NO_CODE_CHANGE` outcome, never a `NEEDS_USER` outcome for the PR (`repair-pr`, *Hard constraints*) — and not a kind-test result;
3. dispatch one `repair-pr` worker with `repair type = review`, on the same model rule as the CI branch above;
4. `repair-pr` uses `resolve-pr-comment` where relevant;
5. adopt the new remote head, **merge every posting-identity entry the repair returned into the run's map**, and **record every `NEEDS_USER` thread the repair returned — **a question item with its draft reply verbatim, a deferred-repair item with the change it asks for and no draft — **and a thread that returned two items is recorded once per item and is handled only when both are in, since a mixed thread carries a deferred repair and a question at the same URL (`resolve-pr-comment`, *A comment can want both*)**** (`repair-pr` distinguishes them) — and every no-action thread it returned**. The second is what stops an acknowledgement being re-dispatched forever; it needs no draft and asks nothing of the owner, and it is not an unresolved finding, so it never holds the merge gate. A repair pass that escalates a thread and pushes a fix for two others returns both, so a pushed head is never evidence that nothing was escalated. **Increment the review cycle only where the pass pushed a repair:** a pass returning `NO_CODE_CHANGE` — the classification left it no repair to make, whether the round was questions, acknowledgements or any mix of them (`repair-pr`, *Review repair (`repair type = review`)*, step 2) — consumed no repair attempt and consumes no cycle, exactly as an external CI failure does not. **The recorded threads are what stops it re-dispatching:** a thread already recorded as reserved is no longer unhandled, so it is not grouped into a later round unless new content arrives on it, and a question-only round classified once is not classified again;
6. **only where the pass pushed a repair**, retrigger/request review when repo convention requires it, unless review is still deferred for this PR or triggering was suppressed for this run. A `NO_CODE_CHANGE` pass left the head unchanged, so a retrigger would ask for another review of identical code — and any fresh threads it produced would be dispatched again, against a pass that deliberately consumed no cycle. This matches the finding branch, which on `NO_CODE_CHANGE` adopts nothing, increments nothing and triggers nothing, and the mechanical-push rule, which re-triggers no review — **selecting the trigger's author from the map as it stands after step 5**, since a repair can establish the invoking-user path the run lacked, and re-triggering on the pre-repair map is what makes that trigger silently fail;
7. release the worker (see Releasing a worker) and resume event supervision.

Review feedback may reference a head already superseded by a rebase/restack. Locate each finding by content rather than line number, and confirm it still applies to the current head before repairing.

A thread needing judgment rather than a diff -> `NEEDS_USER` with its draft reply, never a speculative repair.

A PR branch may have only **one active mutating worker** at a time. Before repair, verify the remote head has not moved unexpectedly.

## A settle finding is the third repair shape

**A thread reserved for the owner is not a source of an `IN_FLIGHT_FIX` where nothing can dispatch it:** a deferred repair is review-shaped work the review budget already refused, so it is reported and holds the gate rather than being re-dispatched under the finding budget (`summarize-tranche`, *Action points*). **A thread carrying a recorded code-changing ruling is the exception and does belong here** — the finding path is its dispatch, and after a restart it is the only one left. `summarize-tranche` can derive an `IN_FLIGHT_FIX` action point solely from durable evidence that is neither CI- nor review-shaped — a worker's documented caveat, the diff itself, a coverage finding — and a walkthrough ruling that requires code to change arrives the same way, routed through the `IN_FLIGHT_FIX` row (see Settled tranche). Both name actionable work on an open PR with no failing check and no reviewer's review thread behind it, so neither dispatch above has a compliant invocation for them — and `repair-pr` is required, so "improvise something else" is not an answer either. `repair-pr`'s `finding` repair type exists for exactly this: it takes the action point or recorded ruling verbatim as its evidence, the way `ci` takes logs and `review` takes threads, under the same bounded one-pass contract.

On an `IN_FLIGHT_FIX` action point, or a code-changing ruling its row routes here:

1. take the finding verbatim — the action point's what/where/why/next-step, or the recorded ruling with its site URL;
2. if the finding budget remains, allocate an isolated checkout of the current PR branch;
3. dispatch one `repair-pr` worker with `repair type = finding`, on the same model rule as the two branches above;
4. **merge every posting-identity entry the repair returned into the run's map** (see Posting identity), whatever its outcome — a pass can author a write without pushing one;
5. branch on the outcome. On a pushed repair: adopt the new remote head, increment the finding cycle, and retrigger/request review when repo convention requires it — a finding repair's push is substantive, never mechanical — selecting the trigger's author from the map as it stands after step 4. On `NO_CODE_CHANGE` — the finding no longer held against the current head: adopt nothing, increment nothing, trigger nothing. `FAILED` and `NEEDS_USER` are handled as they are for the other two repair types;
6. release the worker (see Releasing a worker), and re-test the settled conditions before ranking anything (see The summary can un-settle the run).

**The budget is its own counter (`finding-repair-cycles`), not a draw on `review-repair-cycles`** — the two budgets bound different loops (reviewer convergence versus the settle-repair-resettle loop this skill drives itself), and one counter over both lets either loop starve the other (NOTES: the argued choice, including the case for sharing and why it loses). The default is **2**, parallel to the other two: one pass to fix, one to answer a reshaped finding, then the owner. An escalated round still consumes its finding cycle, exactly as for the other two types (see Model and skill policy).

A finding that no longer holds against the current head — a later push already fixed or mooted it — comes back `NO_CODE_CHANGE` and consumes no cycle, exactly as an external CI failure does not. And the judgment rule above applies unchanged: a finding that requires product or architecture judgment is `NEEDS_USER`, not a speculative repair.

## Mechanical pushes do not consume review

A restack, or a renumber/regeneration of a claimed artifact, moves identity or ordering rather than behavior. Such a push:

- does not consume a review repair cycle;
- does not re-trigger automated review;
- does not reset the PR's reviewed state.

The repository's deterministic checks are what validate it. Where the repository has no check that would catch a bad renumber, treat the push as substantive instead — `create-pr` carries the full test for which is which.

A renumber earns the mechanical label only once its regeneration has been **verified to apply** (see Performing the renumber once a human decides). "Moves identity or ordering rather than behavior" describes what a *correct* renumber does; the hazard is that a botched one is indistinguishable from it in the diff while changing whether the artifact runs at all. So an unverified renumber is not a mechanical push, it is an unvalidated one, and skipping review over it is the shortcut that makes the failure invisible. Verify first, then claim the exemption.

This matters most right after a sibling merges. Descendants restack and claimed artifacts renumber for reasons that have nothing to do with their own diffs, and re-reviewing every one of them spends the review budget on code that did not change.

## Draft state

**The run does not promote drafts.** Promoting a draft PR to ready is a social act — it is how you ask another person to review — so it is never an autonomous orchestrator decision. It is not a policy knob with two settings; it is a thing the orchestrator does not do. Promotion survives in exactly two places: the owner promotes a PR themselves, whenever they choose; and the merge path, where publishing is a step of merging (see Merge behavior). Nothing else changes a PR's draft state in either direction — never mark ready, never flip a PR back to draft. A repair worker never touches draft state either: `repair-pr` reports how many actionable threads remain unresolved, and what happens to the PR stays with this parent layer.

**An explicitly held draft** is a PR that a decision outside this run keeps in draft: an explicit user instruction to hold it, a repository's prose convention about draft state, a draft preference a caller passed through `implement-issue-core`, or a human returning the PR to draft after it was ready. This is the term's only definition; invariant 12's gate and the checkpoint output consume it. An explicitly held draft is reserved from the merge path — excluded from the gate, neither published nor merged, however clean its review and CI — and reported in the checkpoint output as held, awaiting the owner. **A PR that is currently a draft and has ever been ready is held**, and that is the discriminator to use — not as-created versus current, which cannot see it. Created-as-draft, marked ready by a human, returned to draft by them leaves both values reading `draft`, identical to a PR nobody ever touched, so a run that consults only those two publishes and merges exactly the PR a person deliberately withdrew. The stronger reading is available because of the rule above: the run never marks a PR ready except by merging it, and never flips one back to draft, so **every** ready-to-draft transition on a PR of this run's is someone's decision. Track as-created and current draft state in the per-PR block (`create-pr` reports the as-created state) for reporting, but read the transition from the forge's own timeline before applying the gate: the per-PR block is run state, which invariant 1 classifies as a cache, and a restart or a missed event leaves it unable to answer the one question that matters here.

# Parent supervision loop

Long-lived PR/CI/review supervision always runs in this parent loop, never inside a Dynamic Workflow: a workflow run accepts no external input once started and does not persist past the current Claude Code session, so it cannot sit and wait across hours/days for CI or review to come back. This holds even for a run whose implementation fan-out did execute inside a Dynamic Workflow — once that workflow returns its worker results (PR URLs, branches, heads), supervision reverts to this same parent loop.

The main parent thread must remain active while mutating workers run or active PR events can lead to more in-scope work.

Each cycle performs real work:

1. consume worker completions (including a Dynamic Workflow's returned fan-out results, if one was used), extracting each one's dependency evidence — unmet blockers, source disagreements, **and the resolutions that confirmed your view** — and **merging every posting-identity entry it returned into the run's transport-and-credential-keyed map** (see Posting identity), regardless of its outcome. Do this before releasing the worker: the worker's transports are not this run's, so its observations are the only evidence the run will ever have about them, and a released worker cannot be asked again;
2. consume the events already delivered, then reconcile tracker + remote branches/PRs **only where this cycle has a reason to**, in one consolidated pass rather than a sweep of the tracked set. **The reasons are the ones under API budget and read discipline and are not restated here** (NOTES);
3. fold that pass into the per-PR blocks, stamping `last read`; a PR no event named and no poll was due for keeps the state it already had, and is neither re-fetched nor treated as unknown;
4. update heads/budgets;
5. dispatch repairs;
6. recompute READY frontier;
7. fill available worker slots (optionally via a fresh Dynamic Workflow fan-out if the user re-opts in for the next batch);
8. inspect stack ancestry changes;
9. inspect every in-flight worktree for uncommitted work and enforce checkpoints (see Checkpoint compliance — this is a mandatory step, and the parent commits on the worker's behalf when a nudge has already failed) — **mandatory wherever worktrees are reachable, and inapplicable where the run established they are not**, in which case this step is the remote-head reading and the report saying so, never a skipped step recorded as a passed one;
10. read every worker's runtime state, not only its work state — release the finished (see Releasing a worker) and act on the blocked (see Blocked workers);
11. **reconcile released-vs-alive against the runtime, never against the run's memory.** On a runtime with a session list, list the sessions whose provenance marks them as created by this run (`parent_session_id` on Claude Code Remote — never "sessions that look like workers"), and compare against the per-PR records. Three outcomes, and only three: **mine and archived** — done; **mine and still alive** — act on it this cycle: the releasable test, a Blocked workers branch, or `NEEDS_USER` — and where its worktree cannot be inspected from here, never archive it (*cannot verify* is not *verified clean*) and raise it as `NEEDS_USER` instead, because a live session this run created is this run's cost and stays this run's problem; **not mine** — a session whose provenance proves it belongs to another run or to the user: report it and never reclaim it, whether or not its worktree is inspectable. The comparison must read the runtime because the run's own record of releasing is not evidence: of the two runs that leaked sessions, one never reached step 10, and the other wrote "archived" into its notes and never called the tool. Reporting an action is not performing it (NOTES: the two mechanisms);
12. **emit the state block** (see Progress / checkpoint output) — every cycle, including the long one-PR supervision tail, not only in closing output;
13. re-check disk/slot capacity;
14. check sibling branches for colliding added or modified claimed artifacts;
15. surface `NEEDS_USER`;
16. wait using native task/event wait, then repeat.

Do not use CPU loops, file-touch loops, detached sleeps, meaningless commits, or other fake activity solely to prevent idling.

Remote Git checkpoints remain mandatory regardless of runtime, because no platform/runtime persistence substitutes for durable source control.

## Arming the wait when nothing is in flight

Step 16's native task/event wait is sufficient while workers are running: their completions are the events. A **settled** run has none. No worker will finish, no CI will fire, and the merge it is waiting on may be a day away — so a settled run that simply waits has no event source of its own, and "the run advances its own frontier" quietly becomes conditional on something nothing required it to arrange.

Before a settled-and-empty run stops doing work, it arms both of:

1. **a PR-activity subscription over this run's own PR set** — the platform-native watch or an explicit `subscribe_pr_activity` (see Event handling). This is what delivers the merge that advances the frontier. Normally these are already armed, because Event handling arms each PR when it enters the tracked set; this step confirms the set is complete rather than establishing it, and arms anything missing;
2. **a scheduled self check-in, as the backstop**, because that subscription does not cover everything. CI success, new pushes and merge-conflict transitions are the known-unreliable deliveries, and a merge whose event never arrives is a merge the run never acts on. The check-in re-reads durable state — PR states, mergeability, the frontier — and acts on what it finds, instead of treating silence as evidence that nothing happened.

Both, not either. The subscription is the fast path; the check-in is what makes the slow path terminate — and the check-in itself is bounded, because "re-arm forever until the merge comes" is the same unbounded loop this skill forbids workers to run, written from the parent's side (NOTES: what two of these cost). Stop once every PR in the set is merged or closed; until then, **every recurring check-in this skill's runs arm — parent-side or worker-side — carries one unproductive-wake budget and a backoff**:

- **budget: 8 consecutive unproductive wakes**, then stop re-arming. **A wake is unproductive whether it read and found nothing or could not read at all** — one counter over both, because both spend money to learn nothing and a watch that alternates between them is as pointless as one that does either (NOTES: why this was two counters and is now one);
- **backoff: start at 20 minutes, double on each unproductive wake, cap at 4 hours.** Eight at that shape (20m, 40m, 80m, 160m, then 4h × 4) spans roughly 21 hours — long enough to wait out a night and a working day for a human reviewer, short enough that a forgotten watch dies in single-digit dollars. **Where the wake was deferred under API budget and read discipline, it goes at whichever is later: the backoff's next step, or that rule's reset/`Retry-After` floor, where the deferral has one** (that rule also defines when it has none) — waking before the reset is refused again, and waking before the backoff would have is the frequency the backoff exists to cut. The budget is one; the schedule is still per cause;
- **only an observed delta clears the count, and "nothing changed" means durable state only** — PR head, CI conclusions, the review-thread set and each thread's resolved state, mergeability, tracker status. Any delta resets it to zero, including a delta the run has no budget left to act on: a red CI it cannot fix is a change observed, never a no-op. **The test is what the wake observed, not how it ended** — a wake that saw a delta on one PR and was then refused reading another has observed a delta and clears the count, while a wake that observed none counts against the budget whether it read and found nothing or could not read at all;
- **write the count into the wake's own prompt.** The session's context does not survive between firings, and a compaction can drop it mid-run; a counter kept in memory resets silently and the budget never binds. Each re-armed prompt carries the consecutive-unproductive count and the durable state the next firing compares against;
- **stopping is reported, never silent**: which watch stopped, on which PRs, after how many unproductive wakes, **which kind they were**, and what would restart it — a new event, a fresh invocation, or the owner acting on the PR. A watch that expired against a contended allowance and one that expired on a quiet PR call for different remedies, so the report must not collapse them;
- **this is a cost guard, not a verdict on the PR.** An expired watch says nothing about the work: the PR it watched is still an open item in the closing report, and its expiry must never be read as settled, merged, or finished.

This is not a licence to keep a loop warm, and the ban above is unchanged. A subscription and a scheduled wake do not require this run to keep asking, which is what separates them from spinning, touching files, or committing to look busy. **Do not assume a subscription is free.** Absent documentation saying it is webhook-backed, treat its cost as unknown rather than zero — and do not hedge it with polling of this run's own invention. **The bounded scheduled check-in is not such a hedge and is not optional**: it is the backstop item 2 above requires alongside every subscription. What is banned is inventing a second, unbounded watch on top of both (NOTES). The two rules point the same way: fake activity is what a run resorts to when it has no real wake mechanism, so arming one is the fix rather than the exception.

**When neither can be armed** — no subscription available, no scheduler — do not hold the session open reporting supervision that is not happening; the run would sleep through the merge while the user believed it was watching. Reconcile durable state and return a restartable checkpoint naming the resume frontier and the PRs whose merges would advance it, exactly as Stop conditions already requires when the runtime cannot safely stay active. Restart / resume adopts that and re-derives readiness from durable truth, so what is lost is the automation, not the work.

## Frontier advance on merge

A merge someone else performed is a **frontier-advancing event**, not a terminal one: it is the thing that turns in-scope `BLOCKED` issues into READY work. Steps 6 and 7 of the loop above are how the run consumes it, and they stay reachable after the tranche settles. On every merge/close event:

1. reconcile tracker + GitHub remote state, so readiness is recomputed from durable truth rather than cached run state — **once per batch of merge/close events, not once per event**. **The batch is every such event already delivered when this step is reached**: drain the queue first, then reconcile once over all of them, and fold an event arriving mid-reconciliation into the next pass rather than starting a fresh one. A later event whose reconciliation would repeat one this cycle already performed over the same graph is consumed by it rather than repeating it. Where events genuinely arrive minutes apart each still gets its own reconciliation (NOTES);
2. restack affected descendants exactly as today (see Stack mutation while PRs are open) — this step is unchanged;
3. recompute the READY frontier over the **same bounded manifest**, crediting merges only (below). A merge never widens scope: an issue the invocation did not adopt does not become in-scope because something it depends on merged;
4. if new nodes became READY, re-run the preflight over the bounded scope before dispatching — **at the mode the escalation rules select**, not shallow by default (see Escalating to deep validation) — then fill free worker slots in scheduling order. The preflight is not optional here: it is mandatory before **any** new implementation worker, the merge changed the graph the previous run validated, and this is the case that needs the escalation most (NOTES). **What is optional is rebuilding what you already hold.** This run has a validated DAG and knows exactly what the merge changed; hand the validator that prior graph and the change, so it verifies the delta rather than re-enumerating hierarchy, project structure and every dependency edge from scratch (NOTES). Where the validator cannot accept prior state, the full re-derivation stands: the correctness rule is not negotiable and the cost is a tooling limitation to report, not a reason to skip it;
5. if nothing became READY, stay settled and keep supervising.

This requires no new user prompt. While the run still holds budget and in-scope work remains, the merge resumes dispatch inside the same invocation.

**Only a merge advances the frontier; step 3 credits merges alone.** A close is worth reconciling but is never an advance: completion is a closed issue **plus a merged** implementation PR (see Completion semantics), so crediting a close dispatches a fresh worker to recreate the PR a human just declined (NOTES), and an unmerged close unblocks nothing downstream — a descendant is not released by an ancestor that never landed. On an unmerged close, reconcile and stop there: hold that issue and everything downstream, surface it as `NEEDS_USER` naming the closed PR — abandonment, a rejected approach, and work superseded elsewhere are indistinguishable from the event and call for opposite next moves — and redispatch that path only on an answer, never on the close itself.

### When the advance waits for a human

Continuing is the default, and the advance never manufactures a question the skill has a documented default for (see Autonomy and interactive prompts). What it must not do is dispatch *through* an ask the previous tranche already left outstanding — starting the work is one way of answering it. Hold a path where an outstanding item bears on the work about to start:

- a `DECISION` action point, or a `MERGE_RISK` raised as `NEEDS_USER`, **whose answer would change what or how the newly-READY node gets built**. Dispatching commits the run to one answer before the human gives it;
- an unverifiable-prerequisite `NEEDS_USER` the merge did not satisfy — a merge retires only the blockers it actually satisfied;
- an **unproven dependency view** `NEEDS_USER`, which holds the whole advance rather than one path: step 3 recomputes readiness through the same transport whose reach is in doubt, so every node it just called READY shares the blind spot. **A worker cannot raise this against a boundary you classified `dependency transport unavailable`, and if one does, read it as a report rather than a hold** — there is no proof to re-establish, so holding the advance would stop the run permanently on a condition accepted at the preflight. Where a dependency transport does exist, re-establish the visibility proof before dispatching anything, exactly as at the preflight; where it does not, there is nothing to re-establish.

Everything else continues. A `NEW_ISSUE` follow-up, a question about how the merged PRs themselves are handled, or a `NEEDS_USER` on an unrelated branch does not hold a node it has no bearing on — and holding one path never holds the others: dispatch the unaffected newly-READY nodes in the same pass.

Read the merge itself as evidence. A user asked to choose between two approaches who then merged one has answered; do not hold work on a question their merge settled. What survives is the ask the merge left genuinely open.

Holding is not idling. Name the outstanding item, the node it holds, and what answer releases it — in the checkpoint output and as a live `NEEDS_USER` — and treat the answer as its own resume signal: the held node dispatches on the reply, in the same run, with no re-invocation.

Nothing about the advance relaxes the safeguards it dispatches under:

- **invariant 12 still holds.** Auto-advance is triggered by observing a merge — whoever performed it, a merge invariant 12's gate authorized included — never by deciding one should happen. The advance itself merges nothing.
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

Everything below about consuming a worker's outcome — its dependency evidence, its coverage findings, its disagreements — assumes the report arrives. Whether it does is a property of the runtime:

| runtime | how the report reaches the parent |
|---|---|
| in-process subagent | the return value, delivered to the caller |
| Dynamic Workflow agent | the fan-out result the workflow returns |
| serialized execution | directly, in the same context |
| **remote worker session** | **it does not.** A remote session cannot message its parent. Its structured return lands in its own transcript, which the parent never reads |

On that last tier — the one the degrade chain most often lands on — a report reaches this run only through what the worker wrote somewhere durable, all of it **pulled**, never pushed. A dispatch prompt asking a remote worker to "report back" gets a report addressed to nobody. Nothing in the worker contract persists the report on its own (`implement-issue-core` returns its structured state to its caller; `create-pr` writes only the PR's metadata), so pulling recovers whatever happened to land in an artifact — not the report, and where the worker stopped before a PR existed, none of it (NOTES: where the gap is worst).

**So require the worker to write the report down, before relying on being able to read it — but read the session record before requiring anyone to write anything.** The runtime writes that record itself: it costs no permission, needs no tracker write, and survives the session being archived:

| field | carries | limit |
|---|---|---|
| `status_bucket` | `WORKING` / `COMPLETED` / `BLOCKED` | disagrees with `session_status` — see Blocked workers |
| `pending_action.tool_name` | exactly what a blocked worker is waiting on | only while it is blocked |
| `task_summary` | what it is doing right now | ephemeral; says nothing about outcome |
| `post_turn_summary` | `status_category`, `status_detail`, `needs_action` | **one line of free text**, rewritten each turn |

With the branch — commits, diff, messages — and the PR where one exists, *did it finish*, *is it stuck*, *on what*, and *what landed* are all answerable without the worker writing a word to the tracker. **What none of it carries is judgment**: an acceptance criterion the worker could not satisfy, a guarantee it narrowed, an endpoint it found missing, a dependency it read in prose that native metadata denies. That is the only thing the written report is required for, and the requirement is scoped to exactly that (NOTES: what "persist the run state" would cost instead).

**Route the report by whether a PR is actually there — not by the outcome label, since linkage verification and the review trigger run after creation, so `FAILED` and `NEEDS_USER` can both arrive with a perfectly usable PR already open — and never to the issue:**

- **PR exists — a comment on the PR, whatever the outcome says.** That is where a reviewer and a merge decision look, it exists exactly when there is a body of work to qualify, and it is inert to every dependency reader. This is the large majority of reports.
- **No PR — the worker writes nothing.** Its one line of `status_detail` and `needs_action` tells this run there is something to look at; the parent investigates — the branch, `pending_action`, the issue's own prose, the dependency read repeated under its own credential — and **writes the record itself, after classifying it.**

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

None of this is implementation-specific. A repair worker's return value is lost on the same tier in the same way, so its dispatch prompt — CI and review repairs alike — carries the same requirement, with `repair-pr`'s Output contract as the base of the subtraction and the routing already decided, since a repair presupposes a PR: the judgment goes in a comment on the PR under repair. That report carries exactly what the pushed head cannot say — whether the failure belonged to this PR, why a `NO_CODE_CHANGE` pass changed nothing, whether a cycle was consumed, what a `NEEDS_USER` needs.

**Verify at dispatch time that the worker can write the sink it is being asked to use.** The requirement is not satisfiable by instruction, and an allowlist entry does not settle it either — the entry has to name an operation the connected server actually exposes. A worker told to write a sink it cannot reach either stops on a permission gap or returns with the result in its transcript, arriving here as silence. Where the sink is unreachable, the runtime choice is what gives: dispatch that issue on a tier whose return value reaches this run.

**A worker's report is evidence; a blocker record is a conclusion. Keeping them apart is what the routing above is for.**

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

This is the same division of labour as the ambient-posture countermand: the worker skills are runtime-agnostic and cannot know whether their return value goes anywhere, so the obligation belongs in the dispatch prompt, written by the only layer that knows the runtime.

So on a remote-session runtime, treat the worker's own writing as a required read rather than a courtesy copy, and pull it deliberately: the PR body and thread replies for substance, the session's summary for whether it finished, was blocked, or stopped mid-issue. A run that waits for a report to arrive from a remote worker waits forever, and reads the silence as nothing having happened. **This bites hardest on the things no check expresses**: CI says nothing about a caveat the worker deliberately raised, so a narrowed guarantee, a knowing deviation from an acceptance criterion, or a limitation flagged and left unfixed lives in the worker's PR comment and nowhere else. Read it before any merge-order ranking, before surfacing the PR as finished, and before relaying a PR as ready — never after the decision it should have informed. A green PR whose worker flagged a scope caveat is not the same object as one whose worker flagged nothing, and only the report distinguishes them.

## Verifying worker reports

A worker's reported check results are a claim about its own environment, which may be misconfigured in ways the worker cannot see. Before relaying or acting on reported results, verify them against durable evidence: CI on the pushed head, or a re-run outside that worker's environment. Never escalate a worker-reported mass failure to the user, or block a merge decision on it, unverified.

## Checkpoint compliance

**Assume the checkpoint instruction will not land.** Across observed runs, workers hold completed work uncommitted at a high rate — including workers whose dispatch prompt explicitly told them to push before running checks. Sonnet workers treat committing as something that follows green checks rather than something that protects work in progress, and no amount of prompt emphasis has reliably changed that. Parent-side verification, not the worker's instructions, is what actually satisfies invariant 5.

So this is a step of every supervision cycle, not a periodic spot check, and it observes three things per in-flight worker — the worktree, the local branch, and the remote:

**Two of those three require reaching the worker's checkout, so this whole section applies only where the run established that it can** (Remote worker session arguments). Where it cannot, the remote head is the only observable, and it is the one that "tells you nothing" below: a head that has not advanced cannot distinguish a worker still reading code from a worker sitting on eight finished files, and on that tier nothing else is available to separate them. Do not read this section's silence as permission to guess — the honest position is that invariant 5 there is the worker's to satisfy, enforcement is the dispatch prompt, and a worker whose head does not advance is the one thing the parent can still act on. **Make it actionable rather than quiet — measured in elapsed time, never in cycles — and where a channel exists, nudge first (Enforce, do not re-ask, which owns the four capability combinations).** The supervision loop has no minimum interval: sibling completions and PR events can drive several cycles back to back, so a cycle count would raise a legitimately-working worker minutes after dispatch and then block settlement on it. So: a tier-2 worker whose remote head has not advanced for **30 minutes** of observed elapsed time is reported as such, and at **2 hours** it is `NEEDS_USER` — naming the session, its last observed head, and how long it has been unchanged. Both thresholds are measured from the last observed advance (or from dispatch, if there has been none) across at least two observations, so a burst of cycles inside one minute is one observation, not four. It is not a capture and does not pretend to be one; it converts the state that currently reads as *still working* into one somebody sees, which is the same hole a worker with no checkout at all falls through.

| worktree | local vs. tracked remote | state | action |
|---|---|---|---|
| dirty | — | completed edits exist only on disk | capture, below |
| clean | local ahead | committed, push failed or was deferred | push the stranded commits |
| clean | level | nothing saved yet | leave alone unless dispatch was long ago |

A remote head that has not advanced tells you nothing arrived; it cannot distinguish a worker still reading code from a worker sitting on eight finished files. Only the worktree separates those. And a clean worktree is not proof of durability on its own: a worker that committed but whose push failed leaves `git status` clean while the remote stays put, so the local/remote comparison is what catches that case. Pushing stranded commits is always safe against a live worker — it touches neither its index nor its working tree.

### Enforce, do not re-ask

On first observing uncommitted completed work, instruct that worker to commit and push immediately. If the next cycle still shows it uncommitted, the parent captures the work itself rather than nudging again: a second nudge is evidence the instruction is not landing, and the parent already holds worktree path, branch and base in the tracking record.

**Both halves of that escalation depend on a capability, and the tier a degraded run most often lands on has neither.** The nudge needs a channel to the worker; the capture needs a path into its worktree. Where only the channel is missing, the parent **captures on first observation** — the same capture, one cycle earlier — and none of the nudge's reasoning transfers: a nudge nobody can deliver is not evidence about anything. Where the worktree is unreachable too, as on the remote-session tier normally is (Remote worker session arguments), there is no parent-side capture to bring forward: invariant 5 is the worker's own to satisfy and an unadvancing remote head is the only symptom the parent will ever see.

**But the two capabilities are detected independently, so there are four combinations and not three, and the fourth is the one worth naming: a channel and no path.** There the nudge is a real act even though the capture is not — so use it. Instruct that worker to commit and push before escalating on its head, and repeat it, because repeating is all that is available: the "a second nudge is evidence the instruction is not landing" rule exists to stop the parent nudging *instead of* capturing, and where there is nothing to escalate to it forbids nothing. A nudge that may not land still beats a stall report that certainly does nothing, and it is the difference between work exposed and work pushed. **Repeat it on the elapsed-time observations the stalled-head rule already defines, not once per cycle** (Checkpoint compliance): the supervision loop has no minimum interval, so sibling completions and PR events can drive several cycles inside a minute, and a per-cycle nudge would deliver a burst of identical reminders to a worker whose only offence is being three minutes into reading the code. One nudge per observation, from the same clock and the same two-observation floor that governs the escalation it leads to. **And an advancing remote head clears the state, nudged or not** — that is the acknowledgement this loop gets, since no reply is readable here: the work the nudge asked for is now pushed, so the count resets to nothing and a later stall starts over. What the parent must not do is treat its own repetition as progress: the nudges are unacknowledged by construction, so the escalation's thresholds run on the head alone and are neither reset nor deferred by having sent another one.

So: **both** — nudge, then capture (subagents in parent-created worktrees, and serialized execution). **Path, no channel** — capture on first observation. **Channel, no path** — nudge, repeatedly, then the stalled-head escalation. **Neither** — the stalled-head escalation alone.

**Capture without racing the worker.** A live worker owns its index and `HEAD`, and the shared-resource rule above applies to its own checkout as much as to a service — two actors staging into one `.git/index` can capture a half-written tree, or make each other's commits fail. So never run `git add` in a live worker's index. Either:

- **live worker** — build the commit **ref-neutrally** and push it to a **recovery ref**, never to the issue branch, using the tested implementation beside this skill:

  ```bash
  scripts/checkpoint-capture.sh <worktree> <issue-branch> <worker-head-sha> <issue-owned-paths-file> [remote]
  ```

  The script is this section's former prose sequence, extracted because every defect the sequence has had was found by executing it and none by reading it (NOTES: the six-defect history). **Run `scripts/test-checkpoint-capture.sh` after any edit to the script** — reading it and agreeing is not verification. The constraints it implements, which any substitute must satisfy:

  - it moves **nothing the worker holds**: the scratch `GIT_INDEX_FILE` isolates the index and nothing else (plain `git commit` would still advance whatever ref `HEAD` names — the worker's branch), and `commit-tree` writes a commit attached to no ref;
  - the scratch index is **seeded from the worker's head first**, then the issue-owned paths overlaid — an index built from the path list alone records every other file in the repository as a deletion, and recovery merging that checkpoint would delete most of the repo;
  - **verification runs before the push and fails closed**: the capture is diffed **against its parent** — content being present says nothing about what else the tree dropped — and every reported path is compared with the issue-owned list, aborting on any extra. `diff-tree` runs alone, never piped (in a pipeline only the last status survives, and a bare `diff-tree` displays a diff without asserting one); pathnames are compared in **raw** form (`diff-tree -z`), never the C-quoted line form, which would misclassify every non-ASCII or backslash-carrying issue-owned file as unexpected and abort its capture; grep's exit status is checked explicitly (a failed grep must never read as an empty match); and every step is `&&`-gated so none can fail into the push — never rely on `set -e`, which is not honoured inside a subshell in every host shell. A verification step that cannot fail is worse than none, because it reads as protection (NOTES: why validation precedes the push rather than following it);
  - **one ref per issue branch, force-replaced on each capture — never one per capture commit** (NOTES: why sibling refs have no safe ender and why replacement is safe for commits built this way). Force-update deliberately: the ref is expected to move backwards in content only when the worker moved it;
  - the branch name is **encoded into a single ref component, escaping `%` before `/`** — `feature/foo` becomes `refs/checkpoints/feature%2Ffoo` — keeping the mapping reversible and injective, and the ref readable during recovery (NOTES: the prefix-collision and injectivity arguments);
- **wedged worker** — stop it first, then commit normally onto the issue branch in the now-quiesced worktree. Stopping consumes that issue's lost-worker budget, so it needs the same evidence any redispatch does.

The issue branch has exactly one writer at a time, and while a worker lives that writer is the worker — locally as well as remotely. Advancing either end underneath it is not a neutral act even when its index and worktree are untouched: its next push becomes a non-fast-forward rejection, and a worker that reacts by force-pushing destroys the snapshot that was protecting it. A recovery ref buys durability without a second writer. Making the worker fetch and reconcile instead would put the fix back in the worker's hands — the same hands that did not commit when told to.

The general rule behind all three cases: **capture must not move any ref the worker holds.** Test a proposed capture against that before running it, because several plausible sequences violate it silently — the index, the branch, and `HEAD` each have to be checked separately.

Once the worker pushes its own commit covering that work, its recovery refs are redundant; drop them when the PR reaches durable state. Lost-worker recovery reads them.

**But a recovery ref outlives the worker it was captured from, and redundancy is not the only way it ends.** That rule assumes the worker comes back and pushes. A **released** worker that has not already done so never will — and this must key on the release, not on the outcome, because the releasable test has two cases and only one of them produces an outcome at all. The second releases a worker whose work reached durable remote state and which is blocked on a prompt this run does not need answered; it returns nothing, and it is archived deliberately, so lost-worker recovery never runs for it either. Keyed on terminal outcomes, this rule would leave that case with no ender whatsoever, and invariant 12 would then reject an otherwise mergeable PR permanently. The capture that made the worker releasable is, in either case, the only copy of that work. Such a ref is **outstanding**, not redundant, and the parent owns reconciling it into the issue branch — and can, because releasing the worker removed the second writer the one-writer rule above exists to protect against. Do it at release rather than deferring it: the only other consumers of these refs — lost-worker recovery, and the blocked-worker archive under Blocked workers — never run for a worker that returned an outcome, so a deferred reconciliation has nobody left to perform it.

**The principle behind every case below: a recovery ref is dropped only once a durable carrier the run will actually read holds its contents.** The four PR states differ solely in whether such a carrier exists, and enumerating them explicitly is deliberate — this rule was built one case at a time and each missing case left a ref with no ender, which invariant 12 then converts into a PR that can never merge.

- **PR open.** Reconciling advances the branch, so the PR's CI and review evidence now describes a head that no longer exists — the same staleness publishing produces, and handled the same way: that PR re-enters ordinary supervision and is re-evaluated on a later pass. Until the reconciliation lands the PR carries an outstanding recovery ref, which the gate excludes; merging there would drop work the run itself decided was worth rescuing. Once it is on the branch, **verify the capture's commit is an ancestor of the branch head, then delete the ref.**
- **No PR yet** — a worker that returned `BLOCKED` or `FAILED` before creating one. Releasing a worker says PR state is irrelevant to release, so this worker is as released as any other. Reconcile into the issue branch, or push the capture *as* that branch where none exists; then verify and delete exactly as above. The branch is a carrier the run reads — it is item 3 of the durable-evidence order — so a redispatch picks the work up, and no issue is at risk of being called complete, since nothing here looks like completion.
- **PR closed without merging.** Same handling as no-PR: the branch is still the carrier, nothing merged, the issue is not complete. Reconcile, verify, delete — and **report it**, because a closed PR usually means a person decided against that line of work and a capture landing on its branch is worth their knowing about. Do not treat the closure as authority to discard the capture; that decision is theirs and this path does not ask them for it.
- **PR already merged.** Here **branch reconciliation is not a fix and must not be performed as though it were.** Releasing a worker treats a merged PR as eligible and *common* — a wake armed at PR creation outlives the PR that armed it, so the work has usually landed by the time anyone finds the session. The merge commit is already in the base; pushing the capture to the issue branch afterwards moves nothing that matters, no CI or review round runs on a merged PR, and the gate has nothing left to withhold. Every mechanism the open case relies on is absent, and so is the carrier: the branch of a merged PR is not read again.

  So this case is `NEEDS_USER`, and it carries a second correction: **that issue is not complete**, whatever the merged PR implies, and must not be reconciled to complete while the ref is outstanding. Surface the issue, the merged PR, and the ref name. Do not open a follow-up PR automatically — the capture is a WIP snapshot of unknown completeness by the paragraph below, and landing it under the authority of a review that never saw it is the one outcome worse than reporting it. **Delete nothing** until the owner decides; here the ref is the only copy, and this is the branch where dropping it would be irreversible.

A snapshot that caught a file mid-write is still worth having: it is a WIP checkpoint, never the PR's final state, and a partial save beats an empty branch. Prefer the worker doing its own commit precisely because it has no such hazard — parent capture is the fallback, not the mechanism.

Securing a worker's work never waits on that worker finishing. A worker mid-check with completed edits uncommitted is the highest-risk state in the run, because a long check is exactly when a container is most likely to disappear.

### Where the parent cannot reach

This contract assumes two capabilities the parent has to have — that it can **see** a worker's checkout and **send it an instruction** — and they come apart, so it is worth naming which tier has which. Both are established at startup rather than assumed (Remote worker session arguments). **Subagents in parent-created worktrees**: both, and the escalation above runs as written. **Remote worker sessions**: normally neither, and never assumed either way — the channel is whichever the recorded capability says, absent for every worker session the observed runtime was asked about, and the checkout is not reachable — the session record hands out a repository and no path, and the container is not shared — so the escalation has no first step *and* no second one, and what remains is the worker's own pushes plus `NEEDS_USER`. **A Dynamic Workflow fan-out**: neither half — workflow agents accept no input mid-run, and the worktrees the runtime creates for them are not paths the parent was given.

So the remote-session tier belongs beside the workflow tier for this section's purposes, not beside subagents, which is the opposite of where it sat while the *see* half was assumed. The two tiers differ in what substitutes: a workflow run can be made to checkpoint **structurally**, by splitting implementation into stages the script pushes between (below), and a remote worker session cannot — nothing in the parent's reach interposes on it, so its dispatch prompt is the only lever and the honest guarantee is weaker. State that in the checkpoint output rather than reporting invariant 5 as enforced.

So under a Dynamic Workflow, enforcement has to be structural — encoded in the script's control flow, which is deterministic, rather than in an agent prompt, which is the thing that does not land.

**Checkpoint granularity equals stage granularity.** A script can only interpose where it has a stage boundary, so a single checkpoint stage after implementation is not a checkpoint at all — it is the final push, which the worker was going to make anyway. If implementation hangs or the container dies inside that one long stage, the stage never returns and nothing was saved. Bounded loss requires implementation split into several bounded stages, each ending with a push: the number of boundaries is the granularity, and one boundary at the end is none.

That only works where the issue's work decomposes into units the script can name in advance — per-file tranches, per-module conversions, work already sliced by the ticket. Where it does not, the workflow runtime **cannot** satisfy invariant 5 for that issue, and no arrangement of stages changes that.

So the runtime preference is conditional, not absolute. A Dynamic Workflow suits the fan-out shape, but invariant 5 outranks that convenience: prefer a runtime whose workers the parent can reach whenever the implementation cannot be staged into script-visible units. Unreachable-mid-run is a real cost of the workflow runtime, the same one that already disqualifies it for PR supervision — this is the second thing it cannot do, not a footnote on the first.

## Blocked workers

A worker waiting on a permission prompt is neither running nor finished. Its session reports `REQUIRES_ACTION` — or whatever the runtime calls *stopped, awaiting a human* — and a supervision cycle that looks only for `RUNNING` and `IDLE` sorts it under quiet and moves on.

**Read the field that reflects the blocked state, not the one whose name suggests it.** A runtime may expose several, and they can disagree (NOTES: the observed IDLE/BLOCKED disagreement and the six-hour incident). Checking the obvious field and finding a familiar value is therefore not evidence the worker is fine — it is the reading this failure mode produces. Establish once, per runtime, which field actually changes when a worker stops for a human, and read that one every cycle; where a summary of what the worker was last asking for is exposed, read it too, because that is what turns "blocked" into something a user can act on. Quiet is the one thing it is not: nobody is watching that prompt, so nothing will ever answer it, and the worker holds its container indefinitely.

**On the remote-session tier, one of the levers below may not exist at all — and on the runtime this was observed against, for the worker sessions a run had created, it did not.** The limitation is not a property of being mid-prompt, which is merely where it was first seen: on Claude Code Remote, `SendMessage` does not address a worker session this run created, in any state, and `interrupt_session` stops a worker without answering what stopped it. So step 2's "an instruction it can be sent" is unavailable wherever the criterion below says absent, and the recovery for anything it would have covered is not *redirect*: it is step 3, **whose own path then turns on the other capability** — archive-and-redispatch where the checkout is reachable, and `NEEDS_USER` where it is not, because an archive nobody could capture from trades an unknown amount of work for a slot. It has one consequence outside this section, on the same split: the checkpoint escalation's nudge is not an act on this tier, so where the checkout *is* reachable the parent captures on first observation, and where it is not there is no parent-side capture at all (Checkpoint compliance, *Enforce, do not re-ask*). **The capability the run recorded at startup is the criterion, here as everywhere else that branches on it** (Remote worker session arguments). Where `cross_session_inbound` reads anything but `available`, the channel is absent, step 2 is unavailable, and no probe is required to establish it. Where it reads `available`, the channel is present and step 2 is a real lever again — **use it.** Requiring an observed landing first would leave the field unable to ever establish presence, which is a detection that decides nothing; worse, it splits the verdict, so the checkpoint escalation nudges the very worker this path had written off as unreachable (Enforce, do not re-ask, which branches on the recorded capability).

**What makes it safe to act on evidence that weak is that nothing waits on it.** The field speaks to a session's inbound availability, not to this parent's ability to address that session, so it can be right about the runtime and wrong about the pair. No branch of this document blocks on a reply: nudges are unacknowledged by construction and every escalation runs on the observed remote head. So a channel wrongly presumed present costs one composed message — and the failure absent-until-proven was buying protection from, a worker stranded while the run waits for an answer that cannot come, is not reachable from here any more. **A send that errors or is refused is the observation that counts, and it flips the recorded capability to absent for the rest of the run**: unlike the field, that is direct evidence about this parent and this worker. The observation this section was written from is exactly that shape and it stands — no send reached a worker session the run had created — which is why a negative observation overrides an `available` field and not the reverse.

**Both errors are silent, so record how each session was decided and report it.** A run that read the field as absent and a run that never read it look identical in the output otherwise, and the second is the one whose invariant 5 story is unknown to itself.

Read the blocked state explicitly each cycle, and resolve it in this order:

1. **it passes the releasable test** in Releasing a worker — apply that test, do not restate it here. Every version of this rule that was written out a second time drifted from the first, including the one that required a PR still be open and so excluded the merged-PR case this section is written from. Release it and record what it was asking for;
2. **the block is the parent's to clear** — a resource detail the worker was dispatched without, an instruction it can be sent, a write the parent can perform itself. Clear it and let the worker continue;
3. **neither, and the prompt is one nothing can answer** — an `AskUserQuestion` or equivalent, where the worker is asking for a decision rather than for permission. No lever reaches it: interrupting the session leaves the prompt pending, and on a remote runtime there is no message channel to it at all (above). **Which recovery this is turns on whether the run can reach that worker's checkout, so settle that first** (Remote worker session arguments) — the two branches end in different places, and stating either one as *the* rule makes the other read as a violation of it. 

   **Where the checkout is reachable, recover the slot, and do not resolve the worker as `NEEDS_USER` and leave it:** that holds a container and a worker slot for however long the human takes, and the capture below is what makes holding them unnecessary. Archiving destroys the container, and with it the local worktree lost-worker recovery would otherwise read, so uncommitted work must reach a **remote** ref before the archive rather than merely a local commit. Capture it with the ref-neutral sequence under Checkpoint compliance, which pushes to a recovery ref and moves nothing the worker holds, and verify that capture the way that section requires; do not substitute a plain `git commit`, whose result the archive then discards. Only once the capture is on the remote — or you have established there was nothing uncommitted to capture — archive the session, then — where a capture was pushed — end its ref by **the four-state rule under Checkpoint compliance — apply it, do not restate it here.** This archive is not a release by the releasable test — case 1 above took every worker that passes it — and the worker is not lost, so neither of that rule's other trigger sites will ever fire for this ref; unconsumed here, it stays outstanding forever, blocking invariant 12's gate over the very work it rescued, while the redispatch below starts from a head the capture never reached and redoes the work. Then redispatch **the same work unit** from the latest durable remote state — which the reconciliation has just made include the capture — with the step 8 countermand in place; where the four-state rule's merged-PR ender raised `NEEDS_USER` instead, that is the outcome: do not redispatch work whose PR has already merged — the owner now holds the decision. The same work unit, not the same issue: this section covers every worker, and a blocked `repair-pr` worker redispatched as "the issue" becomes a fresh implementation attempt under `implement-issue-core`'s contract instead of the bounded repair it was. Preserve the archived worker's role, its repair type where it had one, and the budget it had left rather than issuing a new one. This is the only recovery observed to work, and a redispatch costs one worker where a session left blocked costs a slot for the rest of the run. Record the question it stopped on either way: a worker reaching for this tool is a finding about the dispatch prompt that produced it, not just an incident.

   **Where the run established it cannot reach that worker's checkout at all** (Remote worker session arguments), none of that is available: it can neither perform the capture nor establish there was nothing to capture, and *cannot verify* is not *verified clean*, exactly as in step 11. **The slot is therefore not recoverable on the run's own authority, and this is the one blocked worker that is `NEEDS_USER` with its container retained** — naming the session, its last observed remote head, and the question it stopped on. Do not archive it to free the slot: that trades an unknown amount of work for one worker slot, and the decision belongs to the owner. Nor does case 1 rescue it while the gap under Releasing a worker stands — an unreachable worktree is exactly what leaves that test's second condition unsatisfiable there, so no worker on this tier passes it. **This is not the "still waiting" the last rule in this section forbids,** and the difference is what that rule actually asks for: the worker is named in the run's output with its cost stated, the held slot is reported as the price of a documented gap (Releasing a worker) rather than absorbed silently, and the run does not schedule against the capacity it is holding. A run that ends this way has not failed and is not clean either;
4. **neither, and the prompt is a permission request** — `NEEDS_USER`, naming the issue, the session, and **the exact tool being requested**. "A worker needs permission" is not actionable; the tool's name is what lets a user allow it once and unblock every run after this one. Report the literal string the runtime gave you, server segment included, and never a tidied version of it: an MCP server can be registered under a display name, a slug, or its bare UUID, the allowlist matches the literal name, and a tool already allowlisted under one of those spellings still prompts under another. Normalizing the name to the one you expected is how that reads as an entry that exists and does not work.

   **One permission request does not belong to this branch at all, and it is the one most likely to arrive in it:** a filesystem search for the worker's own source files — a bare `find`, a repository-root probe, a request for a path the dispatch prompt already named. Read that session's `sources` before reporting it. Where they are empty, the worker was dispatched into a container with no checkout (see Remote worker session arguments): the tool it is asking for is a symptom two steps downstream of that, allowlisting it buys the next worker a faster search of an empty container, and the recovery is step 3 — taking whichever of its two paths the checkout's reachability selects, and redispatching with `source_url` and `source_revision` passed explicitly. **Step 3's capture requirement applies here in full — the empty `sources` does not discharge it.** That field records what the runtime provisioned at creation and says nothing about what the worker has done since: a worker that could not find its checkout is exactly the one liable to have cloned or initialized one itself, and after an hour of trying that container can hold the only copy of real work. Only the dispatch-time check discharges the capture, because there the session has not run yet (see Remote worker session arguments); a session discovered this way has, so inspect and capture it like any other. Record the dispatch defect, not the tool.

Never resolve it as "still waiting". A blocked worker holds a slot, so reading it as idle also stalls the frontier: the run keeps scheduling against capacity that is not in use. It must not be possible for a worker to sit blocked across an entire run without appearing anywhere in its output.

## Capacity during the run

Re-check disk headroom and worker-slot capacity each cycle, not only at dispatch. Worktrees, dependency installs, and build caches accumulate as the run proceeds, so startup headroom does not predict headroom at the fifth concurrent worker. Report the current figure with the worker count in the checkpoint output, and stop filling slots before exhaustion rather than after a write fails.

## Cross-branch artifact collisions

After each PR reaches durable state, compare it against sibling branches in the same run and flag two things: files that two branches both **add** under the same name or sequence number, and incompatible edits two branches make to a shared claimed artifact — a generated manifest, lockfile, registry or index that branches amend rather than create, and which therefore collides with no added path in common. The general class is any artifact whose identity or ordering is claimed rather than derived.

Two chains cut from the same base can each be internally consistent and both pass CI while colliding, because neither can see the other; the conflict only materializes when the second one merges. Dependency edges and stack ancestry do not detect this — the branches are siblings, not ancestors.

Correct resolution depends on merge order, which this skill does not own. Surface the collision as `NEEDS_USER` with both PR URLs and the colliding paths. Never renumber or rewrite the artifact pre-emptively.

### Performing the renumber once a human decides

**Produce it with the repository's own generator. Never hand-edit the artifact's identity fields.** A claimed identity is rarely stored in one place, and the copies that are not the visible filename are usually the ones that decide whether the artifact runs — a hand-rename that misses one makes the artifact **silently skipped**: no error, no log, green CI, and the change never applies (NOTES: the five-place Drizzle example and the observed renumber incident).

The class generalizes past migrations: any artifact whose identity is **claimed rather than derived and spread across more than one file** — a migration with its journal and snapshot, a lockfile with its manifest, a generated client with its registry entry. Renaming what you can see is precisely the operation that leaves the rest stale.

Then verify the result **applies**, not that it compiles and not that CI is green. A skipped migration passes both, which is why neither is the check. Run the artifact's own apply path — migrate against a scratch database, install from the lockfile, regenerate and diff against the committed copy — and confirm the effect the artifact was supposed to have is actually present. Where the generator cannot reproduce hand-written content the original carried, splice it back and re-verify; a regenerated artifact that silently dropped a backfill is the same failure with the sign flipped.

Until that verification passes, the renumber is not finished, and it is not mechanical — see Mechanical pushes do not consume review, which grants the skip-re-review exemption only to a renumber that has cleared this.

# Lost worker / workflow recovery

A worker whose remote branch never advanced is the expensive case; prefer catching it through the checkpoint-compliance check above, before it is lost.

If a worker disappears:

1. inspect remote branch/PR first;
2. inspect any recovery refs the parent pushed for that issue (see Checkpoint compliance) — work captured from a live worker lives there, not on the issue branch;
3. inspect local worktree only if the container still exists;
4. adopt pushed checkpoints/PR, then end the recovery ref by **the four-state rule under Checkpoint compliance — apply it, do not restate it here.** All four states reach this consumer: a worker can disappear before opening a PR, after its PR was closed unmerged, while it is open, or after it merged, and each has a different ender (NOTES: the two-state copy that lived here and what it missed). This consumer needs saying separately: the worker that lost its container can never return to push, so neither the redundancy rule nor the release-time branch will ever end a ref consumed here, and it would stay outstanding — rediscovered by every later pass, and blocking invariant 12's gate over work that has already landed;
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

# Merge behavior

By default orchestration never merges. Invariant 12 defines the one gate under which it may, and a repository's `auto-merge` key (see Per-repository policy configuration) is what makes that gate reachable for its PRs.

Where the gate is reachable, evaluate it at the settled step, after the summary, the walkthrough, and the ranking — the gate's `DECISION` and `MERGE_RISK` inputs do not exist before `summarize-tranche` produces them, so an earlier evaluation is a guess wearing the gate's name. Merge the PRs it passes in the ranking's order, bottom-up within a stack, restacking descendants exactly as any merge requires; each merge is then an ordinary frontier-advancing event (see Frontier advance on merge). A PR in a repository that did not opt in is untouched whatever its siblings did — the gate resolves per PR, from that PR's repository.

**The gate's dependency-view condition names its supplier per consumer, because the machinery differs and the condition must not.** Here it is discharged by the validated preflight: an unproven relationship boundary over dispatchable scope is a `FAIL` that never reaches dispatch, a proof invalidated mid-run raises the *unproven dependency view* `NEEDS_USER` that the gate's outstanding-item test already refuses, and a frontier advance re-validates before anything new dispatches — so for boundaries with a working dependency transport the condition costs the gate nothing it was not already paying. What it changes is the one case the preflight deliberately accepts: **`dependency transport unavailable` is proceedable for dispatch and is not discharged for merge.** The acceptance argument does not carry over, because both of its premises stop at the gate. Blocking dispatch on the warning would halt every GitHub backlog permanently, while holding a merge degrades exactly to the default no-merge behavior the run has anyway — the PRs still get built, reviewed, summarized and ranked. And dispatch leaves a person standing between every PR and the default branch, which the gate is precisely the removal of. A READY computed from prose alone is a narrower claim than one computed from a corroborated graph, and the merge is where the difference stops being reportable and starts being landed: a blocker nobody wrote into prose is undetectable by construction, and nobody is left downstream to catch it. So a PR whose dependency view rests on such a boundary holds this condition exactly as a `MERGE_RISK` holds the gate — reported with the boundary and the discharge path — and its merge stays the owner's. **The discharge must answer for the whole view, because completeness is what is unproven.** A single user-confirmed edge discharges nothing here: under this boundary caller context is a targeted answer whose omissions prove nothing, and the known-true-case proof needs a working transport to observe the edge through (see `implement-issue-core`, *Back the completeness of the set*), so a re-invocation carrying one edge returns the same unproven report and the gate stays closed while the record claims a path out. Two things actually discharge it: a run whose dependency transport can read the graph and prove the boundary; or the owner explicitly answering for the view itself — a decision-shaped hold the settled step already knows how to carry, surfaced as a `DECISION` naming the boundary, ruled through the walkthrough or answered directly, with the recorded ruling retiring the hold exactly as the translation rules retire a constraint. That ruling retires this condition and nothing more: the repository's opt-in and every other gate condition still govern, since a ruling never opens the gate. `implement-issue` supplies the same condition from its worker's completeness report (see its Merge section), so the gate means the same thing whichever consumer evaluates it — which is the point of the shared `auto-merge` grant.

**A merge never happens on a draft.** For each PR the gate passes, the merge path **publishes it to ready first, then merges** — publishing is part of the merge path, not a precondition that might already hold, so a PR still in draft when its gate opens is published by the act of merging it, never skipped for being a draft. This is one of the two surviving forms of promotion (see Draft state; the other is the owner doing it themselves), and it never reaches an **explicitly held draft**: the gate already excludes those, so the merge path neither publishes nor merges one — report each as held, awaiting the owner.

**Publishing is not inert, so the gate is evaluated again after it.** Marking a draft ready is an event review providers and CI act on — `create-pr` says so explicitly, naming a provider that re-reviews when a draft is marked ready — so the clean-review and green-CI evidence the gate just accepted describes the PR as it was one moment before it changed. Merging on it is merging on a reading that publishing invalidated. **So publishing un-settles the tranche for that PR, and the merge waits for a later pass — it is not awaited inline.** Do not hold the settled step open waiting for the review to appear: a wait with no observable completion condition either re-reads the same stale evidence a moment later and merges anyway, or blocks the run indefinitely, and Arming the wait when nothing is in flight already forbids the second outright — do not hold the session open reporting supervision that is not happening.

Publishing therefore returns the PR to ordinary supervision, exactly as a code-changing ruling does. The gate is re-evaluated when fresh post-publish evidence arrives through the machinery that already exists for it — the PR's own subscription and the settled-state check-in — and the merge happens on that later pass, which the run reaches by the same settle-advance-settle path it already uses several times per invocation. Where neither a subscription nor a scheduler can be armed, the restartable checkpoint under that section applies unchanged, naming the PR as published and awaiting re-evaluation. **Never merge on evidence gathered before the publish**, whichever path delivers the next pass: that is the whole of the rule, and the mechanism is the ordinary one rather than a new wait invented here.

A re-review that finds something is the system working: that PR is no longer clean, it does not merge, and it returns to the ordinary repair path — now as a ready PR, since publishing is not undone.

`merge-stack` authors forge writes of its own — the merges, and the retargeting and body edits it makes on descendant PRs — so pass it the run's posting-identity map and merge the observations it returns, exactly as for implementation and repair workers. It is easy to miss because it is invoked as an operation on the graph rather than as a worker that reports; the writes are no less authored for that.

**Invariant 12's gate is itself the authorization `merge-stack` needs, for exactly the PRs it passed.** The stack rules require that skill for any merge or restack, and a gate-approved merge must restack its descendants like any other, so without this a repository that opted in would have no compliant way to perform the merge its own policy authorized. The grant is scoped to the gate-approved set and nothing wider: it does not extend to a sibling the gate excluded, to a repository that did not opt in, or to any stack operation outside that merge. Where the user separately authorizes `merge-stack`, that authorization is the ordinary one and is unaffected by this. Reconcile tracker completion after every merge, gate-authorized ones included.

# Settled tranche

A run is **settled** when no further implementation can start and every open PR is individually finished:

- no in-scope issue is READY — each unstarted issue is blocked by work that is implemented but unmerged;
- no implementation or repair worker is in flight — and a worker blocked on a permission prompt is in flight, not absent (see Blocked workers): it reads as quiet from every angle the other conditions look from, which is how a run declares itself settled over a worker stopped mid-issue;
- every open PR from this run has had at least one **completed** automated review round, not merely a trigger issued;
- every actionable review finding on every open PR is resolved or answered — a thread reserved for the owner — by the kind test or on budget grounds (see Merge policy and review feedback) — counts here as surfaced, not outstanding: it blocks that PR's merge, never settlement;
- no open PR is `NEEDS_USER` or waiting on CI;
- **no worker session this run created is still alive** — verified against the runtime's session list by the reconciliation step of the supervision loop, never against the run's memory of having archived. A run holding a live session it created is not settled, cannot emit a clean settled report, and does not reach invariant 12's gate; this is what makes a skipped or merely-reported release detectable rather than forbidden. An owned session whose worktree cannot be verified still counts: it is never archived unverified, so it stands as a blocking `NEEDS_USER` for the owner — settling over it would leave this run's own session, and any wake it armed, alive and billing with a documented excuse. Only sessions proven to belong to another run or to the user are excluded — reported, never reclaimed, and never counted, so someone else's leak cannot wedge this run's settlement.

Settled is not the same as finished. The run has produced everything it can **for now**; the next move belongs to whoever holds merge authority — the owner, or invariant 12's gate where a repository granted it — and when it is made, the run picks the work back up itself (see below).

On reaching settled:

1. reconcile tracker + remote state one final time, so both the summary and the ranking are computed from durable truth rather than cached run state;
2. invoke `summarize-tranche` with the manifest/scope, this run's PR set, and the worker/review findings it produced;
3. **act on its action points before ranking anything** (below);
4. request `settle-outstanding-decisions`, passing the summary as its seed **and the run's posting-identity map — its recorded rulings are authored writes, and the map is what they select from** (see Posting identity) — unless `auto-request-settle` was turned off for this invocation. The gate covers only the request; whether the walkthrough may actually ask is that skill's call — its *Attendance is the precondition* section governs, and a run settling on a scheduled wake gets a one-line decline. **The decline relies on the decisions being durable at their own sites, not in the summary**: the summary and this run's closing report are cached run state by invariant 1, while the worker records, review threads and tracker comments they were read *from* survive and are what the walkthrough's own discovery reads later; what is lost is the aggregation and run-context enrichment — **the draft reply attached to a reserved thread is exactly that**, so a later walkthrough regenerates it from the thread — reading any rejected-draft record there first — rather than treating its absence as work nobody did (`settle-outstanding-decisions`, *What qualifies as an outstanding decision*) — a real cost, accepted deliberately (NOTES: the removed decision docket and what it cost). **Merge every posting-identity entry it returns into the run's map before continuing** — all of them, not the first: one walkthrough can rule at sites needing different transports, a ruling can be the first authored write through a transport this run has not used, and the observation can re-open a review trigger marked provisionally unavailable — which matters immediately, since step 6 and any later frontier advance issue further writes under whatever identity the map then holds. This step sits between summary and ranking because a ruling changes what the ranking is computed from: it can retire a `DECISION`, reshape a `MERGE_RISK`, or reverse which of two PRs should merge;
5. invoke `plan-merge-order` with the manifest/scope, this run's PR set, and every summary item with an ordering consequence — the `MERGE_RISK` and `DECISION` items as the walkthrough left them, and any other class that also carries one. **Translate each ruling back into an action point before invoking** — `plan-merge-order` accepts summary action points and nothing else, and a raw ruling's likely readings are both wrong: keep ranking a PR the owner just rejected, or hold a merge behind a gate they just opened. A settled decision either drops out as a constraint, or becomes the constraint its answer implies — a `MERGE_RISK` carrying the consequence, an ordering requirement stated on the item. **A ruling that requires code to change is neither: it is an `IN_FLIGHT_FIX`, and the tranche is no longer settled.** Take that row — return to supervision, dispatch the `finding` repair within the finding budget, and re-test the settled conditions before ranking anything (NOTES: why translating it into a ranking constraint is the step-3 defect arriving one step later) — so the ranking is computed against answers where answers exist and against the open constraint where they do not;
6. evaluate invariant 12's gate for each open PR whose repository opted into `auto-merge`, and merge the PRs it passes (see Merge behavior). This step exists here and not earlier because the walkthrough's rulings and the ranking are its inputs; each merge it performs is consumed as a frontier-advancing event like any other;
7. surface the summary and action points first, then the walkthrough's report where one was requested — rulings recorded, or its one-line decline — then the ranking table, as the run's closing output, with every gate-authorized merge and every explicitly held draft named beside it, and name the still-unruled `DECISION` and decision-shaped `NEEDS_USER` items as the set the owner can settle by running `settle-outstanding-decisions` themselves: it is idempotent, so running it after a declined or interrupted walkthrough re-asks nothing already ruled;
8. stop dispatching work, and stop spending tokens re-deriving the same state, for as long as the frontier stays empty.

Summarize before ranking. An action point can change whether something should merge at all, and a ranking the user has already begun acting on is the wrong place to discover that. Run the summary once per settled tranche rather than saving one up for the end of a whole backlog: its findings come from run context that the next session will not have, and follow-ups need to exist while later tranches are still running, so they get picked up instead of rediscovered.

## The summary can un-settle the run

Settlement was computed before the summary existed, so the summary is capable of falsifying it. Branch on what it returns rather than proceeding to the ranking unconditionally:

| action point | effect |
|---|---|
| `IN_FLIGHT_FIX` | the tranche is **not settled** — that PR has actionable work outstanding. Return it to supervision, dispatch it as a `finding` repair within the finding budget (see A settle finding is the third repair shape), and re-test the settled conditions before ranking |
| `MERGE_RISK` | still settled, but the ranking must carry it. Pass it to `plan-merge-order`, and raise it as a `NEEDS_USER` **item** where it blocks a merge decision outright — never an outcome for the PR, and a deferred repair already is such an item |
| `DECISION` | the settled step's walkthrough request (step 4 above) is where it gets ruled when someone is present; unruled, pass to `plan-merge-order` and surface as `NEEDS_USER` — it gates a human, not the run |
| `NEW_ISSUE` | report it; no effect on settlement. No effect on ordering **unless the item carries an ordering consequence** — a follow-up that must land before one of this tranche's PRs is also a `MERGE_RISK`, and takes that row too. The classes answer different questions, so read the item rather than the label alone |

An `IN_FLIGHT_FIX` reaching the ranking is the same defect the settled conditions already guard against: a table that orders PRs which are not actually finished is a table the user cannot act on. Finding it one step later does not make it acceptable.

The ranking is never authorization to merge — invariant 12's gate is the only thing that is, it is evaluated after the ranking (see Merge behavior), and a repository that did not opt in gets no merge from this run at all.

If a run reaches all other settled conditions but some PR still has an unresolved finding, an unfired review, or red CI, it is **not** settled — with the one exception the settled conditions above already state: a thread reserved for the owner is surfaced, not unresolved, and holds that PR's merge rather than the tranche's settlement. A repository whose only open threads are reserved still reaches the summary — a thread the run may not answer on its own authority cannot also forbid it to finish. Everything else: finish that PR within budget, or surface it as `NEEDS_USER`, before ranking. Ranking PRs that are not actually finished produces a merge order the user cannot act on.

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

**Emit the state block at the end of every supervision cycle.** It is a required step of the parent supervision loop with a named actor and moment — this run, each cycle — not a convention that holds while the numbers are interesting. The observed failure is exactly that convention lapsing: runs printed the block mid-fan-out and stopped once they narrowed to a one-PR supervision tail, which is the long part of a run and the part a context compaction lands in — so both runs that leaked sessions reported their session count zero times (NOTES). Emitting each cycle is also what carries budgets, worker state and PR state across a compaction: a count that re-enters the transcript survives; one held in run memory does not.

The block always carries: run budget, workers in flight by kind, worker sessions created / archived / alive, active PRs with CI and review state, repair budgets consumed, and the check-in state with its unproductive-wake count split by kind — plus, whenever reads were deferred under API budget and read discipline, which PRs went unread this cycle and when the allowance resets. For example:

```text
Runtime: Dynamic Workflow
Manifest: <full URL>
Validation: PASS
Scope: 18 issues
Run budget: 9/12 newly started
Implementation workers: 3
Repair workers: 1
Worker sessions: 9 created / 8 archived / 1 alive (blocked on a prompt — see below)
Active PRs: 7
Check-in: armed (unproductive 2/8 — 2 no-op, 0 deferred; next in 80m)
API budget: ok (reads deferred: none)
Waiting CI/review: 4
Unreviewed (trigger pending/unavailable): 0
Unresolved review findings: 0
Review threads reserved for the owner: 1 (acme/api#41 thread r90210: "drop or dead-letter failed webhooks?" — decision-only draft attached)
Drafts explicitly held: 1
Repo policy: acme/api: config (auto-merge on); acme/site: defaults
Posting identity: (github-mcp, tok-a1b2) -> baseten (invoking user); (linear-cli, tok-c3d4) -> unestablished
Auto-merged (invariant 12 gate): 0
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
- checkpoint enforcement: workers nudged, workers whose work the parent committed itself, and any worker that pushed outside its assigned branch — what landed where, and how it was undone;
- every PR this run tracked and whether its event subscription was armed, so a PR the run was blind to is visible as such rather than indistinguishable from one where nothing happened;
- every watch that expired on its unproductive-wake budget — which check-in stopped, on which PRs, after how many wakes and of which kind, and what would restart it. A watch that ran out against a contended allowance names the contention; one that ran out on a quiet PR does not, and the two call for different remedies. An expired watch is a cost decision, not an outcome: the PR it watched is still open work;
- the release reconciliation's findings: sessions this run created and archived, any it found alive and what it did about each, and every session it reported but did not reclaim — another run's, or one whose worktree could not be verified from here;
- caveats a worker raised in its own report that no check expresses — a narrowed guarantee, a knowing deviation from an acceptance criterion, a limitation left unfixed — against the PR each concerns, because these reach a merge decision only if this run carries them there;
- worker-session lifecycle, where the runtime has sessions to account for: how many this run created, how many it archived, and every one still alive with the reason — naming, for each that was blocked, the exact tool it was waiting on. A run that leaks sessions should be visible in its own report rather than discovered afterwards in a session list, and the tool name is the part a user can act on;
- disk headroom against the concurrent worker count;
- CI/review states + repair budgets consumed, naming any round that ran on the strongest model and the locus evidence that triggered it;
- PRs left unreviewed, and whether the review trigger was deferred or unavailable;
- PRs left in draft, naming each explicitly held one and what holds it (see Draft state);
- the posting identity observed **per `(transport, credential)` pair the run wrote through**, each entry naming the transport, the credential identity that is half its key, and the author observed there — per write kind where the kinds observed differ — a distinct account, the invoking user, or `unestablished` where that transport has no read-back write yet. Report the map, never a single run-wide identity: transports with different observed authors are the ordinary case, none of them is wrong, and collapsing them hides whichever entry the provisional review-trigger decision needs. Name separately any distinct identity **observed** on a tier precedence selected elsewhere but not for these writes, as present but unusable — never an inference about a tier the run never wrote through (see Posting identity);
- the policy each PR resolved to and its source — invocation argument, repo config, or built-in defaults — plus any policy file that was unreadable or carried invalid keys, every merge invariant 12's gate authorized with the conditions it passed on, including any PR it published from draft on the way to merging, and every review thread reserved for the owner;
- the `summarize-tranche` summary and action points, the `settle-outstanding-decisions` report — rulings recorded, or its one-line decline, or that `auto-request-settle` was off — and the `plan-merge-order` table, when the run settled;
- issue-linkage/tracker-status inconsistencies;
- `NEEDS_USER` items;
- external blockers;
- dependency edges discovered by workers that the validated DAG did not contain, where each was recorded durably, and any dependency-source disagreement reported on an otherwise successful run;
- coverage findings — dependencies satisfied on paper whose capability a worker found absent — with the prerequisite issue filed for each; for every deliverable shipped degraded, the acceptance criteria left unmet, the PR's linkage form (it must be `Part of:`, never a closing keyword), and confirmation that its issue is still open;
- which edges in the scheduling graph are **verified** by a worker's own check versus still **assumed** from the preflight read, and when each was verified. This is history, not an exemption: a restart still runs the proof-and-provenance reconciliation in step 2 of Restart / resume over every edge, verified ones included, because the label records what was true when it was written and a dependency can be retired afterwards. What it buys is knowing which edges were established by observation and which rest on one preflight read — where to be sceptical, and what not to rediscover by dispatching into it;
- unstarted work and why, including any frontier that a merge unblocked after the budget was exhausted — report it as the resume frontier rather than dropping it;
- whether invoking the same manifest can safely resume.
