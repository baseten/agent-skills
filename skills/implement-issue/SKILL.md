---
name: implement-issue
description: Single-issue orchestrator for one tracked issue from its canonical full URL. Composes implement-issue-core for issue→code→checks→durable PR, then supervises bounded CI/review activity and dispatches repair-pr as needed until the PR is healthy, merged where its repository opted into auto-merge, blocked, or needs user input. Budgets and review/merge policy come from the repository's .claude/backlog-orchestrator.json. Useful standalone and as a one-issue workflow.
---

# Implement Issue

Orchestrate exactly one tracked issue end-to-end while preserving the convenience of a single command.

This skill is intentionally a **one-issue orchestrator**. It composes reusable primitives rather than duplicating their implementation logic:

- `implement-issue-core` — issue reading, implementation, durable checkpoints, local checks, PR creation;
- `repair-pr` — one bounded CI or review repair pass;
- `create-pr` — tracker linkage, stack metadata, PR creation, review trigger;
- `resolve-pr-comment` — review-thread fix/reply/resolve mechanics used by `repair-pr`;
- `summarize-tranche` — what the run did and what a person still has to manage, at settle;
- `settle-outstanding-decisions` — the attended walkthrough of the decisions only the owner can make, at settle while `auto-request-settle` is on;
- `merge-stack` — the compliant mechanics for any merge this run is authorized to perform, at the gate.

Those are required, not optional: `implement-issue-core` and `create-pr` for implementation, `repair-pr` — and `resolve-pr-comment` for review fixes — for repair, `summarize-tranche` then `settle-outstanding-decisions`, in that order, when the run settles, the second only while `auto-request-settle` resolves on — and `merge-stack` wherever the resolved `auto-merge` leaves the merge gate reachable, checked at preflight where policy resolves rather than discovered at the gate: the stack rules require that skill for any merge or restack, so a run that could merge without it holding would have no compliant mechanism for the very merge the repository authorized, and the improvised raw merge is exactly what the next sentence forbids. A repository that never opted in imposes no such requirement — there is no gate to reach. If a required skill is unavailable, return `BLOCKED` rather than improvising a replacement workflow. `plan-merge-order` is deliberately absent from that list and never invoked (see Settle).

It does not schedule other backlog issues, and it merges only where the PR's own repository opted in (see Authority) or the user separately invokes an authorized merge workflow.

## Authority

Invoking this skill authorizes implementation and PR creation for the supplied issue unless the user explicitly says otherwise.

**It authorizes a merge only where the PR's own repository opted in**, through `auto-merge` in the per-repository policy config (see Inputs / constraints). **That key is shared with `backlog-orchestrator` rather than owned by either skill, so a config that predates this skill's ability to merge grants it too** — deliberately: the permission is scoped to invariant 12's gate, not to whichever skill evaluates it, and the `Merge` section below defers to that gate for every condition rather than carrying a copy of it. A run that satisfies the gate is not riskier for having one issue instead of twelve, and a key split per consumer would gate which skill opened the PR — not a property worth gating. An owner who wants no autonomous merge sets `auto-merge` to `false`; an invocation argument narrows it for one run. That opt-in is the only route: an invocation argument or a caller can switch `auto-merge` off for a run, narrowing the gate, never on — the rule is invariant 12's in `backlog-orchestrator`, and it holds here for the same reason it holds there, that a committed file in the repository is the only place an owner can grant merge authority once and have it mean the same thing to an unattended run they are not watching. Absent that opt-in — the common case, since most repositories carry no config file at all — this skill merges nothing, and everything outside the gate remains the user's separate `merge-stack` authorization.

The issue's **full URL is canonical identity** throughout the workflow. Short keys/numbers may be shown for readability but never replace the full URL in durable state.

## Inputs / constraints

When a caller supplies repository, worktree, branch, required base, dependency context, tracker, and budgets, preserve them exactly.

Budgets and review/merge policy come from `.claude/backlog-orchestrator.json`, the per-repository policy config `backlog-orchestrator` defines. **That document owns the contract** — the key list, the resolution scoping, the fail-closed rules, and `auto-fix-reviewers`' both-tests matching rule (see *Per-repository policy configuration* there). None of it is restated here: a second copy is how the two consumers would drift into meaning different things by the same key, which is the reason the config is one file rather than one per skill. The file's name predates its second reader; it is the same file, read the same way.

Of its keys this skill consumes `implementation-attempts`, `ci-repair-cycles`, `review-repair-cycles`, `repair-model-escalations`, `auto-fix-reviewers`, `auto-merge` and `auto-request-settle` — the last resolving from the one repository the run is in, which is the explicit-issue-set case the resolution table already covers. Only `concurrent-workers` and `new-issue-budget` have no single-issue meaning; ignore those two rather than inventing one for them. Read the file once, at the start of the run, from the head of the repository's default branch as the run finds it — never from the worktree this run is about to write, which is the same repository at a revision this run controls, and never again afterwards.

**A caller's resolved policy wins outright, and suppresses that read entirely.** A caller supplying budgets or policy has already resolved them against the same file at its own preflight, so a read here would be a second read of a file whose whole rule is that it is read once from the state the run started in — the child would then be free to override its parent with a later timestamp. So under such a caller the file is not opened: supplied keys are used exactly as given, and keys the caller omitted take the built-in defaults, except `auto-merge` and `auto-fix-reviewers`, which take `false` — a caller that resolved a policy and left a permission out of it did not grant that permission. Standalone, with no caller-resolved policy, this skill does the read itself.

Defaults when the file is absent — the common case, and identical to the built-in defaults `backlog-orchestrator` lists, so an absent file leaves this skill behaving exactly as it always has:

- implementation attempts: **2 total**;
- CI repair cycles: **2**;
- review-fix cycles: **2**;
- strongest-model repair rounds: **1**;
- `auto-fix-reviewers`: **`true`**;
- `auto-merge`: **disabled**;
- `auto-request-settle`: **enabled**;
- monitoring cap: **8 hours** where persistent/event-driven monitoring is actually supported. This one is not a policy key and has no config equivalent: it bounds how long this skill sits watching, which is a property of the invocation rather than of the repository's PRs.

Do not broaden scope into another issue.

# Phase 1 — durable implementation

Invoke `implement-issue-core` with the canonical issue URL and all supplied execution constraints.

Do not hand-roll implementation logic here.

If core returns `BLOCKED`, `BLOCKED_EXTERNAL`, `FAILED`, or `NEEDS_USER`, surface that result. Preserve the distinction between the two block outcomes rather than flattening them: `BLOCKED_EXTERNAL` means the issue waits on work outside the authorized set, so it needs no *frontier* reasoning — only the blocker, its state, and who owns it. It still needs the relationship classification below. Whether an edge is real is a separate question from whether the work behind it is external, and a stale prose edge pointing at an unfinished external prerequisite would otherwise wait forever. If a standalone user clearly requested strongest-model retry, that can be handled by the surrounding Claude session; this skill itself should not create an unbounded model-escalation loop. The bounded repair escalation under Review feedback is a different mechanism on a different object, capped on its own.

A `PR_OPEN` can also arrive with its **dependency view unproven** — the worker could not establish that its blocker list was complete, whether it found blockers or none. That is the normal standalone case rather than a defect: this skill supplies no graph judgement, so the worker proceeds on the invocation's authority and says the absence was never proven. Pass that on in one line rather than dropping it. The PR is making a narrower claim than it appears to — that no blocker was visible, not that none exists — and a user who wants the stronger one can supply a confirmed edge as dependency context on a re-invocation, which turns the next run's silence into evidence.

A **visibility disagreement** means something specific here even though there is no frontier to re-derive: the transport may be returning a partial dependency view, so the issue you just implemented may have blockers nobody in this run could see. Say that plainly rather than filing it as a mismatch — name the edge and which sources had it against which lacked it, and note that the dependency view behind this run is unproven. The user can re-read through a different credential or check by hand; neither is available to them if the finding arrives as a generic disagreement line.

An **availability disagreement in the obsolete-constraint direction** — the caller said a blocker was unmet, the worker found the work available — deserves naming rather than passing through as a generic mismatch. In a standalone run the caller is usually the user, so it is their own constraint that may be stale, and they are the only one who can retire it. Report which dependency, what was observed, and that the block rests on their assertion rather than on anything the worker could see.

**An outcome is a ranking, not the whole finding.** Core returns one value for an issue that may have several kinds of blocker at once, and it ranks them — an in-scope blocker outranks an unverifiable prerequisite, which outranks an external wait. So a `BLOCKED` may still carry an unanswered question about a release or deployment, and you are the only thing that will ask it. Read the reported blockers, not just the outcome, and surface every one that needs the user.

`NEEDS_USER` arrives in two kinds and core says which. An **unproven dependency view** means the completeness of the blocker list was never established — it should not reach a standalone user at all, since this skill supplies no readiness judgement and the worker proceeds on the invocation's authority instead. Arriving here, it means a caller passed a READY judgement through, and the answer is to prove the view or drop the claim, not to re-assert readiness.

`NEEDS_USER` on an **unverifiable prerequisite** is its own case, and the cheapest one to resolve: the worker could not observe the measure that class needs — typically a release or deployment state that lives outside the repository and tracker. Surface the blocker, the measure, and why it was out of reach, and ask the specific question rather than reporting a generic need for input. The answer is usually seconds of a person's time, and once given it can be supplied as dependency context on a re-invocation. Say what that buys, without overstating it in either of the two available ways.

An answer ends the *uncertainty*; only a **yes** clears the blocker. Told the release has not happened, the prerequisite becomes a known unmet blocker and the next run blocks on it — so frame the question as one whose answer decides which of two states you are in, not as a step that unblocks the work. And a yes clears only this blocker: whether the re-invocation proceeds depends on what else core reported, since an unverifiable prerequisite outranks an external wait and can arrive with one still unmet. Promising a proceed the user does not get is worse than naming two things to clear.

Either block outcome on an unmet dependency is a special case: it is authoritative information about the graph rather than a worker failure, so it is never retried. Everything below applies to `BLOCKED` and `BLOCKED_EXTERNAL` alike — externality changes who resolves the blocker, not whether the edge is real. The issue was judged ready against a dependency view that turned out to be wrong — commonly a read that returned part of the blocker list with no indication it had. Surface the named blockers by canonical full URL, and pass on any source disagreement the worker reported (a dependency the prose named that native metadata did not return) even where the run otherwise succeeded: that is evidence about the transport, and this is the only place it surfaces.

Never retried is not the same as never resolved. There is no orchestrator here to re-derive a frontier, so this skill owns the classification itself, or a stale prose edge blocks the issue permanently with no route forward:

- **any blocker named only in prose** — establish whether the relationship still holds before acting on it, whatever state the referenced work is in. Prose survives edits that remove a dependency from native metadata, so a prose-only blocker is as likely to be a dependency someone deleted as one nobody built — and that is just as true when the referenced issue happens to have an open PR or an out-of-base merge. Gating this on "the work exists nowhere" would restack onto a dependency that is no longer real;
- **it still holds** — the block stands, in whichever form core returned it; report the blocker and stop;
- **it does not, or cannot be settled from the issues themselves** — `NEEDS_USER` with both readings and a recommendation, not a bare block. The user can retire a stale edge in seconds; they cannot act on a `BLOCKED` that does not say which reading it assumed.

Where the blocker's work exists but is not available — an open PR, a merge outside this base, or a non-ancestry prerequisite still incomplete — pass on what the worker named. A restack or base correction is actionable without touching the dependency graph at all. But classify first where the blocker came only from prose: restacking onto a dependency that is no longer real costs more than leaving the issue blocked, because the resulting base becomes the justification for the next one.

If core returns `PR_OPEN`, record:

- PR URL;
- branch/base;
- remote head SHA;
- tracker linkage verification;
- draft state as created;
- **every** posting-identity entry core returned, under its `(transport, credential)` key — not one pair. `create-pr` writes the PR and the review trigger through transports the exception may deliberately make different, so core returns a map and collapsing it here discards one path before the re-triggers and the final result consume it (see `backlog-orchestrator`, *Posting identity*);
- implementation attempts used.

At this point the code is already durable remotely even if the current container disappears.

# Phase 2 — single-issue PR supervision

After PR creation, this skill owns supervision **only because it is the standalone single-issue orchestrator**.

That qualifier is a boundary, not a caveat, and it is worth stating in both directions. Here there is no parent to defer to, so watching this PR — including arming a subscription or a scheduled check-in to do it — is this skill's job and the surrounding session's ambient posture agrees with it. Under `backlog-orchestrator` nothing dispatched supervises its own PR: that parent fans out `implement-issue-core` directly and countermands the ambient posture in its dispatch prompt, so a second watcher never arms itself. Read a rule against self-monitoring in the worker skills as scoped to that case; it does not reach Phase 2.

If Claude Code's own background PR watch/notification behavior promotes the worker-created PR into the top-level session or provides first-class PR/CI/review events, use those directly. Do not create a duplicate monitoring mechanism merely because `implement-issue-core` created the PR in a child worker. If that background behavior has GitHub's own auto-merge enabled, it will merge the PR itself once checks pass. That is a forge setting and not the `auto-merge` policy key, and it merges outside the gate whatever this run's policy resolved to — so confirm it is off, or treat a merge it performs as outside this skill's control rather than an outcome this skill produced.

Prefer, in order:

1. first-class/promoted PR events from the current Claude runtime;
2. other event-driven PR/check/review notifications;
3. bounded polling fallback when no event mechanism is available.

The platform may observe an event; this skill remains the **policy owner** deciding whether a repair is appropriate and whether the remaining repair budget permits it.

Avoid frequent no-change polling and do not keep a child agent alive solely to wait for GitHub.

Maintain explicit state:

```text
PR: <URL>
CI repair cycles: <used>/<limit>
Review repair cycles: <used>/<limit>
Strongest-model repair rounds: <used>/<limit>
Current remote head: <SHA>
First review round: pending | complete-with-findings | clean
Threads reserved for the owner: <count>
Draft state: <as-created> -> <current>
Policy: budgets <source>; auto-fix-reviewers <resolved> (<source>); auto-merge <on|off> (<source>)
State: waiting | repairing-ci | repairing-review | healthy | needs-user
```

## CI failure

When CI fails:

1. inspect enough check/log context to identify the relevant failure;
2. if the failure is attributable to this PR and the CI budget remains, invoke `repair-pr` once with `repair type = ci`, on Sonnet or — where the non-convergence trigger has fired and an escalation remains — the strongest available model (see `backlog-orchestrator`, *Model and skill policy*, which owns the trigger and the caps; an escalated round still consumes its repair cycle);
3. pass the exact failure context, remaining budget, and the run's posting-identity map as it stands — `repair-pr` selects its authorship from the caller's entry for its own pair (see `backlog-orchestrator`, *Posting identity*);
4. adopt the returned remote head SHA **and every posting-identity entry the pass observed**, merging them into the run's `(transport, credential)`-keyed map rather than replacing it — a repair can establish a path core never used, and the re-trigger in the review branch and the final result both read that map;
5. wait for the next CI result using first-class/event-driven state where available;
6. after the budget is exhausted, return `NEEDS_USER` rather than trying again.

If CI is clearly unrelated/external/flaky and no code repair is justified, report/monitor it without consuming a repair cycle.

## Review feedback

Actionable is bounded first by the resolved `auto-fix-reviewers`: a thread the **invoking user** rooted is always actionable whatever the policy resolved to, since it is their run and their instruction; any other thread only when its author passes the policy's test; a comment this run authored never is. `backlog-orchestrator` owns all three rules and the matching test itself — read them there rather than from a copy here. What follows from them for a single PR is that this skill **never roots a review thread on the PR it is supervising**: it replies inside existing threads and posts timeline comments, and on the degraded posting-identity path its own root comment would carry the invoking user's login and become indistinguishable from an instruction to itself.

A thread failing the test is **reserved for the owner** — never repaired, never resolved, reported as awaiting them. It does not stop this skill returning, since it cannot be required to resolve what policy forbids it touching, but it is an unresolved actionable finding wherever that concept is consumed here: the round it belongs to is not clean, so it blocks draft promotion below and keeps the merge gate shut.

When actionable review feedback arrives:

1. group one coherent review round;
2. if review budget remains, invoke `repair-pr` once with `repair type = review`, the relevant threads/comments, and the run's posting-identity map as it stands, on the same model rule as the CI branch above;
3. adopt the returned remote head **and every posting-identity entry the pass observed**, merged into the run's `(transport, credential)`-keyed map;
4. retrigger/request review when repository convention requires it — selecting the trigger's author from the identities observed so far, this pass's included: a repair can establish the invoking-user path core lacked, and re-triggering before adopting its observation is what makes that trigger silently fail;
5. wait for the next review state using first-class/event-driven state where available;
6. after the budget is exhausted, return `NEEDS_USER`.

Subjective product/architecture judgment returns `NEEDS_USER` immediately rather than burning repair cycles.

## Draft state

**This run does not promote drafts.** Promoting a draft PR to ready is a social act — it is how you ask a person to review — so it is never an autonomous decision of this skill's, and it is not a policy knob either: `backlog-orchestrator`'s *Draft state* owns the contract, and a run of one PR changes nothing in it. This section used to promote on a clean first review with green CI, and that behavior is removed rather than made configurable, because a run promoting when the PR "looks done" is the run deciding when a person gets asked to review — the same social act, wearing a heuristic. Promotion survives in exactly the contract's two places: the owner marks the PR ready themselves, whenever they choose; and the merge path publishes it as a step of merging (see Merge). `auto-merge` already carries the whole distinction the deleted behavior tried to serve — a repository that opted in gets publish-then-merge from the gate once its review and CI are clean, and one that did not keeps its PR a draft until the owner acts, which is the point: a repository keeping merge authority keeps review-requesting authority with it, and a second knob would encode a distinction the key already makes and could disagree with it. Nothing else changes draft state in either direction — never mark ready outside the merge path, never flip a PR back to draft — so every ready→draft transition on this PR is someone's decision. That is exactly what makes the **explicitly held draft** discriminator hold here as the orchestrator states it: currently a draft and ever ready means held, read from the forge's own timeline before the gate, never from this run's state block, which is a cache a restart or a missed event leaves wrong about the one question that matters.

# Settle

A single-issue run **settles** when its one issue reaches a terminal state: the PR individually finished — a completed review round, every actionable finding resolved, answered, or reserved for the owner, CI green, no repair this skill should still attempt — or `BLOCKED`, `BLOCKED_EXTERNAL`, `FAILED`, `NEEDS_USER`. That is `backlog-orchestrator`'s settled test collapsed onto one node: nothing further this run can start, and no worker of its own in flight. Then, in this order:

1. reconcile tracker and remote state, so everything after it is computed from durable truth rather than this session's cache;
2. invoke `summarize-tranche` with the canonical issue URL, this run's PR, and the worker and review findings it produced — and act on its action points before anything below;
3. request `settle-outstanding-decisions`, seeded with that summary and passed the run's posting-identity map, unless `auto-request-settle` resolved off — and **merge every posting-identity entry it returns into that map before continuing, all of them rather than the first**, exactly as the CI and review branches do for a `repair-pr` return. One walkthrough can rule at sites needing different transports, and a ruling can be the first authored write through a transport this run never used; step 4's merge is itself an authored write that selects its author from the map, so a run that dropped the observation carries stale or `unestablished` state into it. The entries are also the only read-back evidence those ruling writes produced, and the structured result promises the run's full map. The `auto-request-settle` gate covers the request only: whether the walkthrough may actually ask is that skill's attendance precondition, so a run settling on a scheduled wake, or inside a dispatched worker, gets its one-line decline and the decisions stay at their own durable sites;
4. translate the walkthrough's rulings into their gate consequences (below), then evaluate the merge gate where the repository opted in (see Merge);
5. return, surfacing the summary and its action points first, then the walkthrough's rulings or its decline.

**Every terminal outcome settles, not only the healthy one — including one Phase 1 returned before supervision ever began.** The two outputs are an account of what the run did and the action points a person still has to manage, and the runs that end `NEEDS_USER`, `BLOCKED` or `BLOCKED_EXTERNAL` carry the most of both: an unverifiable prerequisite somebody has to confirm, a prose-only edge to retire or keep, a product question a worker was right to refuse to guess at. Those are precisely the decision-shaped items the walkthrough exists for, and they are perishable in the same way a tranche's are — the run context that produced them dies with the session while the sites survive. A run with nothing worth reporting gets the one line `summarize-tranche` already gives the empty case, which is cheaper than a rule about when to skip the step and safer than a rule that skips it exactly where a person was needed most.

**Settle consumes terminal outcomes; it never re-enters on one of its own.** The rule above routes every outcome the rest of the run produces through this sequence, and read against two other rules it loops: a required settle skill being unavailable returns `BLOCKED` (see Inputs / constraints), and `BLOCKED` settles, which invokes the unavailable skill again; a spent repair budget below returns `NEEDS_USER`, which settles again, recomputes the same summary, and rediscovers the unchanged finding. The exemption that breaks both is provenance, not outcome type: **an outcome the settle phase itself produced returns directly rather than settling again** — the phase has already run as far as it can, and re-entering re-runs it against inputs nothing has changed. A `BLOCKED` from Phase 1 still settles, exactly as the rule above requires; a `BLOCKED` from a settle step does not, and a settle-phase failure invented later inherits the same test without a new clause here. The exempt return still carries the most the phase got to, because the fallback is only useful if it says what was lost: a missing-skill `BLOCKED` names the skill and the step it stopped at, carries everything the completed steps produced — the summary and its action points where step 2 finished — and points at the durable sites for what the missing step would have covered, the same guarantee the walkthrough's unattended decline leans on. The exemption covers outcomes the phase *returns*, never passes it *runs*: settling again from step 1 after a repair is the phase's own instruction, follows a repair that changed the PR, and terminates on its own because every pass consumes repair budget — that re-entry is the mechanism working, not the loop.

**`plan-merge-order` is deliberately not invoked, and its absence is not an asymmetry to fix.** It ranks a settled tranche's open PRs by downstream leverage and emits a review order, merge batches, and forced sequencing. One PR has no ordering to rank, nothing to batch it with, and no descendant to restack; the table would be a single row restating the PR this skill just reported. Where a single-issue run's PR is stacked under work this run cannot see, the ordering belongs to whoever holds the whole stack — a run that can see one node of it is the wrong place to compute one.

**A one-issue run is a tranche of one.** `summarize-tranche` takes its scope as a manifest or an explicit issue set, and one issue is the smallest legitimate set rather than a special case: the durable sourcing, the length ceiling, and the action-point classes all read unchanged at that size.

**Every ruling is translated into its consequence for this run before step 4, because the gate cannot see a ruling — only outstandingness.** `settle-outstanding-decisions` records rulings and performs none of them, and recording is exactly what stops a `DECISION` reading *outstanding* — the one state invariant 12's gate tests a decision for. Untranslated, every ruling therefore reads as clean, the adverse ones included: a ruling to close this PR, or to hold it, retires the outstanding item and changes nothing else any gate condition looks at, so step 4 would merge the PR against the owner's explicit instruction — and the record afterwards looks tidier than any unruled case, because nothing is left outstanding to notice. The contract is `backlog-orchestrator`'s — its settled step translates each ruling before invoking `plan-merge-order`, and this document does not copy it: a settled decision either stops being a constraint and drops out, or becomes the constraint its answer implies, or requires code to change and is an `IN_FLIGHT_FIX`. Those three outcomes are the whole set, and the closure is structural rather than observed: a ruling's consequence for this PR is a change to its content, a change to its disposition, or neither, and a PR has nothing else for an answer to change. Read the consequence, not the topic — a ruling on something other than this PR, a convention ratified for future work or a cross-repo choice, implies one of the same three here or implies nothing and drops out with the report. Where the orchestrator carries the middle outcome as a ranking constraint, this skill has no ranking, so every outcome lands against the gate directly:

- a ruling that **requires nothing here to change** — it ratifies the worker's documented default, the declined finding, or the assumption the code was built on — retires its decision and drops out. This is the only outcome step 4 may treat as clean;
- a ruling that **changes what should happen to this PR without changing what is in it** — close it, delete it, hold it, leave the merge to the owner, let other work land first — becomes the constraint its answer implies, and the constraint's home here is the gate: hold the ruling against this PR exactly as the gate holds a `MERGE_RISK`, so step 4 cannot merge contrary to it however green everything else reads. The run performs none of these dispositions, for the walkthrough's own reason — every action a ruling calls for already has an owner, and the walkthrough's output names it — so the run returns instead, gate held, the ruling and its next owner carried in the structured result rather than left to evaporate with the session. The translation only ever narrows: a ruling can hold a constraint or retire one, never open the gate — merge authority stays with the repository's opt-in, and a "merge it" ruling is recorded for `merge-stack`, exactly as `settle-outstanding-decisions`' Boundaries have it;
- a ruling that **requires this PR's code to change** means the PR is not finished after all: the run un-settles — the paragraph below.

A question the walkthrough deferred, declined to ask, or never asked produces no ruling and needs no translation — that decision is simply still outstanding, and unruled is not clean: the gate already refuses it. A free-text ruling the run cannot confidently place takes the disposition outcome, gate held and the ruling surfaced, because the misreadings are not symmetric: filed there wrongly, a mergeable PR waits for a person; filed anywhere else wrongly, the run does or permits something the owner just refused.

**The summary and a code-changing ruling can each un-settle this run, and both do it before the gate.** An `IN_FLIGHT_FIX` action point means the PR is not finished after all; a ruling in the third outcome above means the same thing arriving one step later, and it hides better: the summary case leaves an action point in view, while an owner answering "no, do it the other way" leaves a PR whose decision reads *ruled* while the code still says what they just rejected — only the translation above stands between step 4 and merging the very PR the ruling was against. The handling is identical from either source, which is why it is stated once: return the PR to supervision, repair it within the remaining budget, and settle again **from step 1**, so the re-run recomputes the summary and the gate is never evaluated against evidence the repair invalidated — and the re-run re-asks nothing, since a recorded ruling retires its question at discovery. Where the repair budget is already spent, return `NEEDS_USER` carrying the finding beside the summary already in hand — no repair ran, so nothing invalidated it — rather than proceeding to a gate over a PR known to be unfinished; that is a settle-phase outcome, and it returns directly under the exemption above rather than settling again into the same finding. `backlog-orchestrator`'s *The summary can un-settle the run* governs the summary's classification, minus its ranking consequences — its version of this rule routes through the ranking step, which this skill does not have, so here the un-settling lands against the gate directly. A draft→ready transition un-settles this run as well, whichever site performed it — the owner's own publish included, not only the gate's; that rule lives in Merge, where the gate consumes it.

## Merge

Where the repository opted in through `auto-merge`, evaluate invariant 12's gate over this PR. `backlog-orchestrator` defines that gate and every condition in it; this skill does not carry a copy, so read it there and apply it as written. Two of its clauses are phrased for a tranche and need reading for one issue: the requirement that no `DECISION`, `MERGE_RISK` or `NEEDS_USER` item is outstanding anywhere in the tranche resolves to this issue's own, there being no sibling whose unruled decision could hold this merge; and the ordering that defers the gate to the settled step, after the summary, the walkthrough and the ranking, lands here as step 4 of Settle — after the first two, with no ranking in between. That reason survives the collapse intact: a gate evaluated before `summarize-tranche` has run has no `DECISION` or `MERGE_RISK` inputs to test, and is a guess wearing the gate's name.

**A draft→ready transition is an event, not a formality — wherever it happens — so the gate accepts no evidence older than this PR's latest one.** Marking a PR ready is something review providers and CI act on (see `backlog-orchestrator`, *Merge behavior*, which owns the observation and the machinery), so a clean review and green CI gathered while the PR was still a draft describe a PR one transition older than the one a merge would land. Two sites can perform it, and the rule binds the transition rather than either site: the owner marking the PR ready themselves — the case to watch now that this run never promotes, because it happens outside the run's control at any moment, and a run that does not re-read the forge before the gate discovers it only by merging on evidence from before it — and a still-draft PR passing an open gate, which the merge path publishes as part of merging it, per the orchestrator's *A merge never happens on a draft*, and which is then this same rule's next instance rather than a separate step. Whichever site it was, the transition returns the PR to ordinary supervision exactly as a code-changing ruling does: settle again on the next pass the machinery this skill already uses delivers — the PR's subscription and its check-ins, never an inline wait — and evaluate the gate there on evidence post-dating the transition. What counts as post-dating it is fixed by what the rule protects — the correspondence between the evidence and the PR being merged, not the artifacts' timestamps. A review round or CI run the transition triggered must complete and come back clean like any other. Where a read taken after the transition — no earlier than the next check-in, so an in-flight round has had time to become visible — shows it triggered nothing, no new round and no new run against an unchanged head, that read is itself the post-transition evidence: it re-establishes that the pre-transition clean state still describes this PR, which is everything freshness was for. The terminating case is stated deliberately, because without it the rule rejects every artifact older than the transition while nothing ever produces a newer one, and the gate becomes a hold nobody ordered — re-reading stale artifacts is not fresh evidence, but verifying they still describe the PR is, and re-triggering a review just to manufacture post-dated artifacts would spend a review cycle to learn what the read already established. A run that cannot keep watching returns the checkpoint path unchanged, the PR named as published and awaiting re-evaluation. A re-review that finds something is the system working: the PR is not clean, does not merge, and takes the ordinary repair path as a ready PR, since the transition is not undone. An explicitly held draft (see Draft state) reaches none of this: the gate excludes it outright — neither published nor merged, reported as held.

A merge the gate authorizes is performed through `merge-stack` — the gate is itself the authorization that skill needs, scoped to exactly this PR, and the stack rules require it for any merge or restack (see `backlog-orchestrator`, *Merge behavior*, which owns both statements) — never as a raw forge call, which is what the required-skills rule exists to prevent. Pass it the run's posting-identity map and merge every observation it returns into that map, exactly as for a `repair-pr` return and the step 3 walkthrough: its merges, retargetings and descendant body edits are authored writes, easy to miss because it is invoked as an operation on the graph rather than as a worker that reports, and its entries are the last ones the structured result's map can carry. A merge ends supervision for this PR: reconcile tracker completion, then return the merge with the gate conditions it passed on.

# Completion

Return `PR_OPEN`/healthy when the PR is implemented, linked correctly, and has no currently known CI/review item requiring autonomous repair — after the settle step (see Settle), which is where the merge gate is evaluated and whose summary and walkthrough are the gate's own inputs. Return `MERGED` where it opened and the merge completed. When persistent monitoring is supported, continue until healthy, merge/close, user stop, budget exhaustion, or monitoring cap.

If the runtime cannot remain active while waiting only on external events, return a durable checkpoint rather than pretending background monitoring will continue.

Return `NEEDS_USER` with the exact PR/issue URLs, remaining failure/comment, attempts performed, and recommended next action when autonomous repair cannot safely finish.

## Structured result

Return:

- canonical issue URL;
- tracker;
- repository;
- outcome: `PR_OPEN` | `MERGED` | `BLOCKED` | `BLOCKED_EXTERNAL` | `FAILED` | `NEEDS_USER`;
- branch/base;
- PR URL/number;
- remote head SHA;
- issue linkage verified, and the linkage form emitted — closing keyword, or non-closing `Part of:` because a coverage finding was reported;
- implementation attempts used;
- CI repair cycles used;
- review-fix cycles used;
- strongest-model repair rounds used against the limit, and the locus evidence that triggered each;
- the resolved policy actually applied — budgets, `auto-fix-reviewers`, `auto-merge` — each with its source: caller, repo config, or built-in default, plus a policy file that was present and could not be honoured, since that is what silently narrowed `auto-fix-reviewers` to `false`. An owner should see the authority a run had before they see what it did with it;
- review threads reserved for the owner: count and URLs;
- the merge, where one happened: the gate conditions it passed on, whether the PR was published from draft on the way, and the tracker reconciliation;
- the `summarize-tranche` summary and action points, and the `settle-outstanding-decisions` report — rulings recorded, its one-line decline, or that `auto-request-settle` was off;
- final CI/review state;
- draft state as created and current, and any draft-state transition observed with who performed it — the owner, or the merge path's publish, this run never promoting (see Draft state);
- the run's full posting-identity map — every entry observed by core, by each repair pass, and by a gate-authorized `merge-stack` invocation where one ran, under its `(transport, credential)` key, since a repair or a merge can run on transports core never used and the entries are answers about different write paths rather than versions of one. Carry all of them rather than the latest: an invoking-user path observed in any of them is what this skill's own review re-triggering needs, and there is no orchestrator here to hold that evidence instead. Report `unestablished` where no authored write was read back (see `backlog-orchestrator`, *Posting identity*);
- whether the completeness of the blocker set was backed or left unproven, and on what boundary;
- dependencies checked, and any source disagreements, exactly as core reported them — including on `PR_OPEN`. A run that succeeded while its transport returned a partial dependency view is the case where this evidence is easiest to drop and most worth keeping: nothing else in a standalone run will surface it, and dropping it here means neither the user nor a surrounding workflow ever learns the view was partial;
- blocker/failure details, including the dependency class each block was judged under;
- recommended user action when needed.
