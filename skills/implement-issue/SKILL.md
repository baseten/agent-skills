---
name: implement-issue
description: Single-issue orchestrator for one tracked issue from its canonical full URL. Composes implement-issue-core for issue→code→checks→durable PR, then supervises bounded CI/review activity and dispatches repair-pr as needed until the PR is healthy, merged where its repository opted into auto-merge, blocked, or needs user input. Budgets and review/merge policy come from the repository's .claude/backlog-orchestrator.json. Useful standalone and as a one-issue workflow.
---

# Implement Issue

Orchestrate exactly one tracked issue end-to-end: implement it to a durable PR, supervise that PR's CI and review, repair within budgets, and merge only through invariant 12's gate where the repository opted in.

This file is the contract. The reasoning behind each rule — incident history, arguments, and answers to "why not the obvious other reading?" — lives in `NOTES.md` beside it, keyed by these section names. Read a section's note before changing its rules or when applying them to a case the contract does not obviously cover. NOTES.md explains; it never overrides.

## Composed skills — all required

| skill | role |
|---|---|
| `implement-issue-core`, `create-pr` | implementation |
| `repair-pr` (+ `resolve-pr-comment` for review fixes) | one bounded repair pass: `ci`, `review`, or `finding` |
| `summarize-tranche`, then `settle-outstanding-decisions` (while `auto-request-settle` is on) | settle, in that order |
| `merge-stack` | any merge this run performs — required whenever the resolved `auto-merge` leaves the gate reachable; check at preflight where policy resolves, never discover at the gate |

- A required skill unavailable → return `BLOCKED` naming it. Never improvise a replacement workflow. A repository that never opted into `auto-merge` imposes no `merge-stack` requirement.
- `plan-merge-order` is deliberately never invoked: one PR has no ordering to rank (NOTES).
- Never schedule other backlog issues or broaden scope into another issue.

## Authority

- Invoking this skill authorizes implementation and PR creation for the supplied issue, unless the user says otherwise.
- It authorizes a merge **only** where the PR's own repository opted in via `auto-merge` in `.claude/backlog-orchestrator.json`. The key is shared with `backlog-orchestrator` deliberately — scoped to invariant 12's gate, not to the skill evaluating it — so a config predating this skill grants it too (NOTES).
- An invocation argument or caller can switch `auto-merge` off for a run, never on. Without the opt-in this skill merges nothing; everything else stays the user's separate `merge-stack` authorization.
- The issue's **full URL is canonical identity** everywhere. Short keys are display only, never durable state.

## Policy and budgets

`backlog-orchestrator`, *Per-repository policy configuration*, owns the entire config contract — key list, per-PR resolution, fail-closed rules, and the kind test that decides what a run may auto-fix. Apply it from there; never restate it (NOTES: drift).

- Preserve exactly any caller-supplied repository, worktree, branch, base, dependency context, tracker, and budgets.
- Read `.claude/backlog-orchestrator.json` **once, at run start, from the head of the repository's default branch** — never from the worktree this run writes, and never again afterwards.
- Keys consumed: `implementation-attempts`, `ci-repair-cycles`, `review-repair-cycles`, `finding-repair-cycles`, `repair-model-escalations`, `auto-merge`, `auto-request-settle`. Ignore `concurrent-workers` and `new-issue-budget` — no single-issue meaning.
- **A caller's complete resolved policy suppresses the read**: use supplied keys as given; omitted keys take the built-in defaults — except `auto-merge`, which takes **`false`**: an unmentioned permission was not granted.
- **A partial invocation override suppresses nothing**: read the file and merge the argument over it per key (`auto-merge`: off only). NOT: treating one argument as a resolved policy — that would hand a zero-repair-cycles repository two cycles because its owner narrowed something else (NOTES).
- Built-in defaults (absent file — the common case): implementation attempts **2** · CI repair **2** · review repair **2** · finding repair **2** · strongest-model repair rounds **1** · `auto-merge` **off** · `auto-request-settle` **on**. Monitoring cap: **8 hours** where persistent monitoring is supported — an invocation property, not a policy key.

# Phase 1 — durable implementation

Invoke `implement-issue-core` with the canonical issue URL and every supplied constraint. Never hand-roll implementation here.

On `PR_OPEN`, the code is already durable remotely. Record: PR URL; branch/base; remote head SHA; tracker linkage verification; draft state as created; implementation attempts used; and **every posting-identity entry core returned, under its `(transport, credential)` key** — never collapsed to one pair (NOTES: Posting identity).

On a terminal outcome (`BLOCKED` / `BLOCKED_EXTERNAL` / `FAILED` / `NEEDS_USER`), surface it — Settle still runs afterwards, since it consumes every terminal outcome. Read the result by these rules:

- **Preserve `BLOCKED` vs `BLOCKED_EXTERNAL`.** Externality changes who resolves the blocker, not whether the edge is real; both get the prose-edge classification below, and `BLOCKED_EXTERNAL` needs no frontier reasoning — only the blocker, its state, and its owner.
- **An outcome is a ranking, not the whole finding.** Core ranks coexisting blockers (in-scope > unverifiable prerequisite > external wait), so read every reported blocker and surface each one that needs the user — an unverifiable prerequisite can arrive under a `BLOCKED`.
- **A block on an unmet dependency is graph information — never retried.** Surface the blockers by canonical full URL. Pass on every source disagreement core reported, even on `PR_OPEN`: it is transport evidence and this is the only place it surfaces.
- **Classify prose-only blockers yourself** — no orchestrator exists here to do it, and an unclassified stale edge blocks the issue forever. Establish whether the relationship still holds, whatever state the referenced work is in (an open PR or out-of-base merge does not settle it):

  | prose-only blocker | action |
  |---|---|
  | still holds | the block stands as core returned it — report and stop |
  | no longer holds, or cannot be settled from the issues | `NEEDS_USER` with both readings and a recommendation — never a bare block |

  Classify **before** acting on any restack or base fix the worker named: restacking onto a dead edge makes the wrong base the next run's justification. Where the blocker's work exists but is unavailable (open PR, out-of-base merge, incomplete non-ancestry prerequisite), pass on what the worker named — that is actionable without touching the graph.
- **`NEEDS_USER` has two kinds; core says which — never infer from the blocker list:**
  - *unverifiable prerequisite* — ask the specific question, naming the blocker, the measure, and why it was out of reach. An answer ends the uncertainty; only a **yes** clears the blocker — and only that blocker: others core reported can still block a re-invocation. Frame it as deciding which state you are in, not as unblocking the work.
  - *unproven dependency view* — should not reach a standalone user (this skill supplies no readiness judgement); arriving here means a caller passed a READY through. The answer is to prove the view or drop the claim, never to re-assert readiness.
- **`PR_OPEN` with an unproven dependency view is the normal standalone case.** Pass the caveat on in one line: the PR claims *no blocker was visible*, not *none exists*. Two strengthening paths, split by what the next run can observe (Merge owns the split): a dependency read existed with unproven visibility → a user-confirmed edge as dependency context is the known-true case that proves it; no dependency read at all → no edge-level answer helps, and the discharge is the whole-view answer or a transport-capable run.
- **Report disagreements by kind, with direction:** a *visibility* disagreement (a source named an edge another lacked) means the transport may be partial — name the edge and the sources, and say the run's dependency view is unproven, never a generic mismatch line. An *availability* disagreement in the obsolete-constraint direction (caller asserted unmet; worker found it available) names the dependency and that the block rests on the caller's assertion — standalone, that caller is usually the user, the only one who can retire it.
- Strongest-model retry of implementation belongs to the surrounding session, never to this skill — no unbounded model-escalation loop. The bounded repair escalation below is a separate per-PR mechanism.

# Phase 2 — single-issue PR supervision

This skill owns supervision **only as the standalone single-issue orchestrator** — here, arming a subscription or scheduled check-in is its job. Under `backlog-orchestrator` the parent owns supervision; rules against self-monitoring in the worker skills are scoped there and do not reach this phase (NOTES).

- Use platform-promoted PR events when present; never build a duplicate monitor. Source order: first-class promoted events → other event notifications → bounded polling. No frequent no-change polling; no child agent kept alive only to wait.
- The platform observes; this skill remains the **policy owner** — whether a repair is appropriate, and within which budget.
- If the platform's own auto-merge (a forge setting, not the policy key) is enabled, it merges outside the gate: confirm it is off, or report its merges as outside this skill's control.

Maintain explicit state:

```text
PR: <URL>
CI repair cycles: <used>/<limit>
Review repair cycles: <used>/<limit>
Finding repair cycles: <used>/<limit>
Strongest-model repair rounds: <used>/<limit>
Current remote head: <SHA>
First review round: pending | complete-with-findings | clean
Threads reserved for the owner: <count> (question items: URL, question, draft reply; deferred repairs: URL, requested change, no draft)
Draft state: <as-created> -> <current>
Policy: budgets <source>; auto-merge <on|off> (<source>)
State: waiting | repairing-ci | repairing-review | repairing-finding | healthy | needs-user
```

## CI failure

1. inspect enough check/log context to identify the relevant failure;
2. attributable to this PR and CI budget remains → invoke `repair-pr` once with `repair type = ci` — Sonnet, or the strongest model where the non-convergence trigger fired and an escalation remains (`backlog-orchestrator`, *Model and skill policy*, owns the trigger and caps; an escalated round still consumes its cycle);
3. pass the exact failure context, remaining budget, and the run's posting-identity map as it stands;
4. adopt the returned head SHA **and merge every identity entry the pass observed into the map** — never replace it;
5. wait for the next CI result, event-driven where available;
6. budget exhausted → `NEEDS_USER`, no further attempts.

Unrelated/external/flaky failure with no justified code change: report and monitor; no cycle consumed.

## Review feedback

Actionability — `backlog-orchestrator`, *Per-repository policy configuration*, owns these rules and the matching test; apply them from there:

- a thread rooting on the diff and asking for a code change this pass can make: actionable, whoever wrote it;
- a thread needing judgment rather than a diff — intent, design, rationale, a decision: `NEEDS_USER`, never answered on the run's own authority;
- a comment this run authored: never.
- Consequence: **never root a review thread on the supervised PR.** Reply inside existing threads; post timeline comments only (NOTES: the discriminator depends on it).
- A `NEEDS_USER` thread is **reserved for the owner**: never resolved, never answered, and never repaired **in the part that wants an answer** — a comment asking for a diff *and* prose is repaired and still reserved (`resolve-pr-comment`, *A comment can want both*), reported as awaiting them with its URL and what it asks. **What accompanies it depends on the item kind, and the two must not be merged:** a question item carries the draft reply from the classifying pass, verbatim (`resolve-pr-comment`, *The draft reply*); a deferred-repair item carries the change it asks for and **no draft**, because the budget ran out on work that wants a diff and there is nothing to answer (`repair-pr`). Requiring a draft of both forces a question-shaped draft to be invented for the second. It does not stop this skill returning, but its round is not clean — it keeps the merge gate shut.

On unhandled feedback — a thread rooting on the diff, not authored by this run, **still unresolved**, and not already recorded as **handled — reserved or no-action — unless new content has arrived on it since**. **A thread this run repaired and resolved is handled by being resolved**, which the recorded states do not cover: they name only the two outcomes that leave a thread open, so a predicate listing them alone re-groups every fixed thread on every cycle — new content being a write this workflow did not author, never a settlement record posted into the thread (`backlog-orchestrator`, *CI/review repair*) (`backlog-orchestrator`, *CI/review repair*, states the rule). A reviewer who follows up inside a reserved question thread with a concrete change request has made it unhandled again: excluding the thread for the life of the PR because its root was once classified leaves that request unreachable and the stale reservation holding the gate. **Dispatch on any such round, including one where nothing looks repairable from the outside:** classification and the draft need the thread body and the surrounding code, which is the pass's context, not this skill's.

1. group one coherent review round;
2. invoke `repair-pr` once with `repair type = review`, the threads, and the map, on the same model rule as CI. **The budget gates repairing, not classifying:** invoke it even with the review budget spent, since a classify-only pass consumes no cycle and an unclassified thread has no draft for the settlement path to clear its gate with. With the budget spent it classifies and drafts but repairs nothing, and threads that would have been repairable become `NEEDS_USER` on budget grounds;
3. adopt the returned head **and merge every identity entry the pass observed** into the map, and **record every `NEEDS_USER` thread it returned — a question item with its draft verbatim, a deferred-repair item with the change it asks for and no draft — **and a thread that returned two items is recorded once per item and is handled only when both are in, since a mixed thread carries a deferred repair and a question at the same URL (`resolve-pr-comment`, *A comment can want both*)** — and every no-action thread it returned** — recording is what stops a thread being re-grouped into a later round, until new content arrives on it, and a no-action thread left unrecorded is re-dispatched on every cycle since a classify-only pass consumes none;
4. **only where the pass pushed a repair**, retrigger review where repository convention requires it — a `NO_CODE_CHANGE` pass left the head unchanged, so a retrigger asks for another review of identical code and its fresh threads would be dispatched again — selecting the trigger's author from the map **as updated in step 3**: the repair may have established the invoking-user path, and re-triggering from the pre-repair map is what makes a trigger silently fail;
5. wait event-driven;
6. budget exhausted → the pass still runs classify-only; what remains repairable comes back as **deferred-repair items**, recorded and reported, never a `NEEDS_USER` outcome for the PR (`repair-pr`, *Hard constraints*) — the rest is still classified and drafted.

A pass that returns `NO_CODE_CHANGE` — the classification left it no repair to make, whether the round was questions, acknowledgements or any mix of them (`repair-pr`, *Review repair (`repair type = review`)*, step 2) — consumes no review cycle, and its items and drafts are recorded exactly as a pushing pass's are. Never derive the classification or write the draft here instead of dispatching: `resolve-pr-comment` owns both, and a round this skill triaged as question-only and never dispatched would be reserved with no draft.

## Draft state

- **Outside the merge path, this run never changes draft state, in either direction**: never mark a PR ready, never flip one back to draft. The merge path's publish — a step of merging an open-gate PR (see Merge) — and the owner acting themselves are the only two promotion sites; `backlog-orchestrator`, *Draft state*, owns the contract. There is deliberately no policy knob for this (NOTES: why promote-on-clean-review was deleted, not made configurable).
- **Explicitly held draft discriminator**: currently a draft AND ever ready = held. Read the transition from the forge's own timeline immediately before the gate — never from this run's state block, which is a cache (NOTES).

# Settle

The run settles when its one issue reaches a terminal state: the PR individually finished — a completed review round; every actionable finding resolved, answered, or reserved for the owner; CI green; no repair left to attempt — or `BLOCKED` / `BLOCKED_EXTERNAL` / `FAILED` / `NEEDS_USER`. **Every terminal outcome settles, including one Phase 1 returned before supervision began** (NOTES: the failure outcomes carry the most decision-shaped material; the empty case gets `summarize-tranche`'s one line). Then, in order:

1. **reconcile** tracker and remote state — everything after computes from durable truth, not this session's cache;
2. **invoke `summarize-tranche`** (canonical issue URL, this PR, the worker and review findings) and **act on its action points before anything below**. A one-issue run is a tranche of one; nothing in that skill reads differently at this size;
3. **request `settle-outstanding-decisions`**, seeded with the summary and passed the run's posting-identity map, unless `auto-request-settle` resolved off — and **merge every identity entry it returns into the map, all of them**: a ruling can be the first authored write through a transport this run never used, and step 4's merge reads the map. The option gates only the request; attendance is that skill's own precondition — an unattended settle gets its one-line decline, and the decisions stay at their durable sites;
4. **translate rulings into gate consequences** (below), then evaluate the merge gate where the repository opted in (see Merge);
5. **return** — the summary and action points first, then the rulings or the decline.

**Re-entry rule: settle consumes terminal outcomes but never re-enters on one of its own.** An outcome the settle phase itself produced — a missing-skill `BLOCKED`, a spent-budget `NEEDS_USER` — **returns directly**, naming the step it stopped at, carrying everything the completed steps produced, and pointing at the durable sites for what the missing step would have covered. Provenance decides, not outcome type: a `BLOCKED` from Phase 1 settles; the same value from a settle step does not, and a settle-phase failure invented later inherits the test (NOTES: the two loops this breaks). Settling again *from step 1* after a repair is the phase's own instruction, not the loop — each pass consumes budget, so it terminates.

**Ruling translation.** The gate sees only outstandingness, so an untranslated ruling reads as clean — the adverse ones included (NOTES). Every ruling lands in exactly one of three outcomes; read the **consequence**, not the topic (a ruling about something else implies one of these here, or implies nothing and drops out with the report):

| the ruling… | consequence |
|---|---|
| requires nothing here to change — ratifies the documented default, the declined finding, the built-on assumption | retire its decision; the **only** outcome step 4 may treat as clean |
| changes this PR's disposition without its content — close it, hold it, leave the merge to the owner, sequence it behind other work | hold the gate exactly as a `MERGE_RISK` would. The run performs **no** disposition — it returns, gate held, the ruling and its next owner in the structured result |
| requires this PR's code to change | `IN_FLIGHT_FIX` — the run un-settles (below) |

- Translation only narrows: a ruling can hold or retire a constraint, **never open the gate** — a "merge it" ruling is recorded for `merge-stack`.
- Unruled — deferred, declined, never asked — is still outstanding; unruled is not clean, and the gate already refuses it.
- A free-text ruling that cannot be confidently placed takes the disposition row (NOTES: the misreadings are not symmetric).

**Un-settling** — a summary `IN_FLIGHT_FIX`, or a code-changing ruling; identical handling from either source, and **never a thread reserved for the owner, deferred repairs included** (`backlog-orchestrator`, *A settle finding is the third repair shape*):

- dispatch `repair-pr` once with `repair type = finding` — the finding **verbatim** (the action point, or the recorded ruling with its site URL) plus the map, on the same model rule as CI and review;
- a **pushed** repair consumes a `finding-repair-cycles` cycle and retriggers review where convention requires (substantive, never mechanical); **`NO_CODE_CHANGE`** consumes no cycle and triggers no review. Merge returned identity entries whatever the outcome. `backlog-orchestrator`, *A settle finding is the third repair shape*, owns the type, the budget, and the branching;
- then settle again **from step 1** — the re-run recomputes the summary, so the gate never sees evidence the repair invalidated, and re-asks nothing (a recorded ruling retires its question at discovery);
- finding budget already spent → `NEEDS_USER` carrying the finding beside the summary in hand; that is a settle-phase outcome and returns directly.
- A draft→ready transition also un-settles the run, whoever performed it — the rule lives in Merge.

## Merge

Where the repository opted in through `auto-merge`, evaluate **invariant 12's gate exactly as `backlog-orchestrator` defines it** — apply it as written, carry no copy. Two tranche-phrased clauses read for one issue: "no `DECISION`/`MERGE_RISK`/`NEEDS_USER` outstanding anywhere in the tranche" resolves to this issue's own items; the ordering after summary, walkthrough, and ranking lands as step 4 of Settle, with no ranking in between. A gate evaluated before the summary has no `DECISION`/`MERGE_RISK` inputs to test — a guess wearing the gate's name.

**Dependency-view condition — supplied here by core's completeness report** (the orchestrator's preflight is its supplier there; a standalone run has none of that machinery):

- core reported completeness **unproven**, on any boundary → the condition holds the gate exactly as a `MERGE_RISK`. The PR does not merge; return naming the boundary and the discharge.
- The discharge must answer for the **whole view**: a re-run whose dependency transport can read the graph and prove the boundary, or the owner explicitly answering for the view itself — a decision-shaped hold the walkthrough can put to them and record, the recorded ruling retiring the hold as any translated constraint, never opening the gate. NOT: one confirmed edge — a targeted answer proves no omissions, and the known-true-case proof needs a working transport (`implement-issue-core`, *Back the completeness of the set*).
- NOT: routing the hold through `summarize-tranche`'s classification — its bar treats the caveat as reportable, not as a mandatory `MERGE_RISK` (NOTES).
- A **proven** view discharges the condition; nothing to hold.

**Evidence freshness across draft→ready.** The gate accepts no evidence older than this PR's latest draft→ready transition, whichever site performed it — the owner at any moment (re-read the forge before the gate), or the merge path's own publish, which is the rule's next instance rather than a separate step:

- the transition returns the PR to ordinary supervision: settle again on the next delivered pass (the PR's subscription and check-ins), **never an inline wait**;
- a review round or CI run the transition triggered must complete and come back clean like any other;
- terminating case: a read taken no earlier than the next check-in showing the transition triggered nothing — no new round, no new run, head unchanged — **is** the post-transition evidence. Do not re-trigger a review just to manufacture newer artifacts;
- a run that cannot keep watching returns the durable checkpoint, the PR named as published and awaiting re-evaluation;
- a re-review that finds something: the PR is not clean, does not merge, and takes the ordinary repair path as a ready PR;
- an **explicitly held draft** reaches none of this: excluded from the gate outright — neither published nor merged, reported as held.

**Executing the merge**: through `merge-stack` only — the gate is itself the authorization that skill needs, scoped to exactly this PR; never a raw forge call. Pass it the run's posting-identity map and merge every observation it returns (its merges, retargetings, and body edits are authored writes). A merge ends supervision: reconcile tracker completion, then return the merge with the gate conditions it passed on.

# Completion

- Return `PR_OPEN`/healthy when the PR is implemented, correctly linked, and has no known CI/review item requiring autonomous repair — after Settle, whose summary and walkthrough are the gate's own inputs.
- Return `MERGED` where the gate's merge completed.
- With persistent monitoring: continue until healthy, merge/close, user stop, budget exhaustion, or the monitoring cap.
- If the runtime cannot stay active waiting only on external events, return a durable checkpoint — never pretend background monitoring continues.
- Return `NEEDS_USER` with exact PR/issue URLs, the remaining failure or comment, attempts performed, and the recommended next action.

## Structured result

Return:

- canonical issue URL; tracker; repository;
- outcome: `PR_OPEN` | `MERGED` | `BLOCKED` | `BLOCKED_EXTERNAL` | `FAILED` | `NEEDS_USER`;
- branch/base; PR URL/number; remote head SHA;
- issue linkage verified, and the form emitted — closing keyword, or non-closing `Part of:` because a coverage finding was reported;
- implementation attempts used; CI, review, and finding repair cycles used; strongest-model repair rounds used against the limit, with the locus evidence that triggered each;
- the resolved policy actually applied — budgets, `auto-merge` — each with its source (caller, repo config, built-in default), plus any policy file present but unhonourable (an unreadable file is authority the owner meant to grant and did not);
- review threads reserved for the owner: count, URLs, what each asks, and **per item kind** — a question item's draft reply verbatim (`resolve-pr-comment`, *The draft reply*), a deferred-repair item's requested change with no draft (`repair-pr`). For a question the draft is the point of reporting it, so a run that drops it has escalated without handing over the work it already did; for a deferred repair there is no draft to drop, and demanding one would make the budget-exhaustion case unsatisfiable;
- the merge, where one happened: the gate conditions it passed on, whether the PR was published from draft on the way, and the tracker reconciliation;
- the `summarize-tranche` summary and action points, and the `settle-outstanding-decisions` report — rulings recorded, its one-line decline, or that `auto-request-settle` was off;
- final CI/review state;
- draft state as created and current, and any transition observed with who performed it — the owner, or the merge path's publish; this run never promotes;
- the run's **full posting-identity map** — every entry observed by core, each repair pass, the walkthrough, and a gate-authorized `merge-stack` invocation, under its `(transport, credential)` key; carry all entries, `unestablished` where no authored write was read back (NOTES: why nothing may be collapsed);
- whether the blocker set's completeness was backed or left unproven, and on what boundary;
- dependencies checked and any source disagreements, exactly as core reported them — including on `PR_OPEN` (NOTES);
- blocker/failure details, including the dependency class each block was judged under;
- recommended user action when needed.
