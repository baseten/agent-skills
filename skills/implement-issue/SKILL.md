---
name: implement-issue
description: Single-issue orchestrator for one tracked issue from its canonical full URL. Composes implement-issue-core for issue→code→checks→durable PR, then supervises the PR through supervise-prs, with bounded repair-pr passes, until it is healthy, merged where its repository opted into auto-merge, blocked, or needs user input. Budgets and review/merge policy come from the repository's .claude/agent-policy.json. Useful standalone and as a one-issue workflow.
---

# Implement Issue

Orchestrate exactly one tracked issue end-to-end: implement it to a durable PR, supervise that PR's CI and review through `supervise-prs`, repair within budgets, and merge only through invariant 12's gate (`settle-and-merge`, *The merge gate*) where the repository opted in.

This file is the contract. The reasoning behind each rule — incident history, arguments, and answers to "why not the obvious other reading?" — lives in `NOTES.md` beside it, keyed by these section names. Read a section's note before changing its rules or when applying them to a case the contract does not obviously cover. NOTES.md explains; it never overrides.

## Composed skills — all required

| skill | role |
|---|---|
| `implement-issue-core`, `create-pr` | implementation |
| `supervise-prs`, composing `repair-pr` (+ `resolve-pr-comment` for review fixes) | the PR's supervision, and its bounded repair passes: `ci`, `review`, or `finding` |
| `settle-and-merge`, composing `summarize-tranche`, then `settle-outstanding-decisions` (while `auto-request-settle` is on) | settle, in that order, then the merge gate |
| `merge-stack` | any merge this run performs — required whenever the resolved `auto-merge` leaves the gate reachable; check at preflight where policy resolves, never discover at the gate |

- A required skill unavailable → return `BLOCKED` naming it. Never improvise a replacement workflow. A repository that never opted into `auto-merge` imposes no `merge-stack` requirement.
- `plan-merge-order` is deliberately never invoked: one PR has no ordering to rank (NOTES).
- Never schedule other backlog issues or broaden scope into another issue.

## Authority

- Invoking this skill authorizes implementation and PR creation for the supplied issue, unless the user says otherwise.
- It authorizes a merge **only** where the PR's own repository opted in via `auto-merge` in `.claude/agent-policy.json`. The key is shared with `backlog-orchestrator` deliberately — scoped to invariant 12's gate, not to the skill evaluating it — so a config predating this skill grants it too (NOTES).
- An invocation argument or caller can switch `auto-merge` off for a run, never on. Without the opt-in this skill merges nothing; everything else stays the user's separate `merge-stack` authorization.
- The issue's **full URL is canonical identity** everywhere. Short keys are display only, never durable state.

## Policy and budgets

`references/agent-policy.md` owns the entire config contract — the file, per-PR resolution, precedence and fail-closed rules. Apply it from there; never restate it (NOTES: drift).

- Preserve exactly any caller-supplied repository, worktree, branch, base, dependency context, tracker, and budgets.
- Read the policy file (`references/agent-policy.md` names it, and *Fail-closed handling* its old-name fallback) **once, at run start, from the head of the repository's default branch** — never from the worktree this run writes, and never again afterwards.
- Keys consumed: `implementation-attempts`, `ci-repair-cycles`, `review-repair-cycles`, `finding-repair-cycles`, `repair-model-escalations`, `auto-merge`, `auto-request-settle`. Ignore `concurrent-workers`, `concurrent-open-prs` and `new-issue-budget` — no single-issue meaning.
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

**This skill supervises its one PR through `supervise-prs`, and lets that skill run its own loop** — there is no parent here to own one, so arming the subscription and the bounded check-in is that loop's job (NOTES). Invoke it with:

- **PR set**: the one PR, with its repository, branch/base, remote head and the canonical issue URL — adopted on the first pass, which issues any owed trigger and arms the subscription at once;
- **budgets**: `ci-repair-cycles`, `review-repair-cycles`, `finding-repair-cycles` and `repair-model-escalations`, as *Policy and budgets* resolved them, each with its source;
- **counters**: 0 on a fresh run, since this run created the PR; on any later invocation, the counters in `supervise-prs`'s last returned record;
- **posting-identity map**: the run's map, every entry core returned included; **merge** the map it returns into the run's, never replace it;
- **review routing and trigger state**: as core's `create-pr` left them;
- **repair dispatch**: `direct`; **head checks**: none;
- **wait owner**: `self`; **monitoring cap**: 8 hours where persistent monitoring is supported, none otherwise; **return on**: `any-terminal`; **state emission**: `every-pass`;
- **findings to repair**: none now — Settle hands one in when it un-settles (below).

**Every later invocation re-passes all of these**, with the counters and map `supervise-prs` last returned.

Its outcome decides what happens next:

| `supervise-prs` returns | this skill |
| --- | --- |
| `finished` | settles |
| `needs-user` | settles — every terminal outcome does. Its outcome is **the pass's own result where a pass produced it** — `FAILED` returns as `FAILED`, `NEEDS_USER` as `NEEDS_USER` — and `NEEDS_USER` otherwise |
| `held`, `returned`, `unrepaired`, `merged` or `closed` | settles |
| `waiting` or `repairing` at the monitoring cap, or `cannot-watch` | returns the durable checkpoint (Completion) |

Keep the PR's policy line beside that skill's record: `Policy: budgets <source>; auto-merge <on|off> (<source>)`.

# Settle

The run settles when its one issue reaches a terminal state: the PR `finished` as `supervise-prs`, *Outcomes*, defines it — what that definition counts as surfaced holds the merge gate and never the settlement — or a terminal outcome: `BLOCKED` / `BLOCKED_EXTERNAL` / `FAILED` / `NEEDS_USER`. **A `needs-user` PR settles too**, as a terminal outcome: the walkthrough is where its question is put to the owner. With one issue in scope nothing waits behind it, so no settle here is partial, and a ruling on it takes the Ruling translation below like any other. **Every terminal outcome settles, including one Phase 1 returned before supervision began** (NOTES: the failure outcomes carry the most decision-shaped material; the empty case gets `summarize-tranche`'s one line). Then run `settle-and-merge`, *The settle sequence*, over this one PR, passing it every input its *Inputs* names, as this skill supplies them:

- **PR set and scope**: scope, the canonical issue URL; PR set, its one PR — or none, where Phase 1 returned before creating one;
- **findings**: the worker and review findings the run produced;
- **posting-identity map**: the run's map;
- **resolved policy**: `auto-merge` and `auto-request-settle`, resolved for its one PR (Policy and budgets);
- **ranking**: `caller translates` — nothing is ranked, since one PR has no ordering to rank. This skill runs the ruling translation below over the rulings handed back at its step 5 and passes back the translated action points;
- **dependency view**: the value core's completeness report gives — proven, or unproven on the named boundary with the discharge Merge describes;
- **freshness checks**: none apply — this skill runs no integration check and has no authority to update a branch, so the stale-green re-check and the tool-bump rule do not apply;
- **publish rule**: `hand back` — this skill runs its own evidence-freshness rule (Merge, *Evidence freshness across draft→ready*) on the PR returned as published, and settles again when that rule says;
- **outstanding recovery refs**: none — this skill captures nothing, so `swarm`'s generic lifecycle decides;
- **un-settling**: nothing to pass; on a hand-back, Un-settling below governs, with the re-entry rule.

Its steps, in order, as this skill reads them:

1. **reconcile** tracker and remote state — everything after computes from durable truth, not this session's cache (its step 1);
2. **invoke `summarize-tranche`** (canonical issue URL, this PR, the worker and review findings) and **act on its action points before anything below** (its steps 2–3). A one-issue run is a tranche of one; nothing in that skill reads differently at this size;
3. **request `settle-outstanding-decisions`**, seeded with the summary and passed the run's posting-identity map, unless `auto-request-settle` resolved off — and **merge every identity entry it returns into the map, all of them** (`references/posting-identity.md`): a ruling can be the first authored write through a transport this run never used, and step 4's merge reads the map. The option gates only the request; attendance is that skill's own precondition — an unattended settle gets its one-line decline, and the decisions stay at their durable sites (its step 4);
4. **translate rulings into gate consequences** (below) when its step 5 hands them back, passing back the translated action points, then evaluate the merge gate where the repository opted in (its step 6; see Merge);
5. **return** — the summary and action points first, then the rulings or the decline (its step 7).

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

**Un-settling** — a summary `IN_FLIGHT_FIX`, or a code-changing ruling; identical handling from either source, and **never a thread reserved for the owner with nothing able to dispatch it — questions and deferred repairs** (`summarize-tranche`, *2. Action points*, which never emits one as an `IN_FLIGHT_FIX`). A thread carrying a recorded code-changing ruling un-settles as it always did: the ruling is the evidence and the finding path takes it:

- **re-invoke `supervise-prs` with every Phase 2 input and the finding as a finding to repair** — verbatim, the action point or the recorded ruling with its site URL — and merge the map it returns. That invocation returns as soon as the finding's pass has returned, whatever `return on` says; that skill dispatches the `finding` pass, counts the `finding-repair-cycles` cycle and re-triggers review where a pushed repair calls for it;
- a **pushed** repair or a **`NO_CODE_CHANGE`** → settle again **from step 1** — the re-run recomputes the summary, so the gate never sees evidence the repair invalidated, and re-asks nothing (a recorded ruling retires its question at discovery);
- **`needs-user`** — the finding budget already spent (`NEEDS_USER`), or the pass returned `FAILED` or `NEEDS_USER` (that result) → that is the outcome, carrying the finding and the pass's report beside the summary in hand. It is a settle-phase outcome and returns directly: never settle again on it, so a failed finding repair is never re-dispatched.
- A draft→ready transition also un-settles the run, whoever performed it — the rule lives in Merge.

## Merge

Where the repository opted in through `auto-merge`, evaluate **invariant 12's gate exactly as `settle-and-merge`, *The merge gate*, defines it** — apply it as written, carry no copy. Two tranche-phrased clauses read for one issue: "no `DECISION`/`MERGE_RISK`/`NEEDS_USER` outstanding anywhere in the tranche" resolves to this issue's own items; the ordering after summary, walkthrough, and ranking lands as step 4 of Settle, with no ranking in between. A gate evaluated before the summary has no `DECISION`/`MERGE_RISK` inputs to test — a guess wearing the gate's name.

**Before publishing or merging, reconcile the PR body against the current diff (`settle-and-merge`, *Merge behavior*) — unconditionally, not only where a repair reported drift.** `repair-pr` returns that flag and it is useful as a prompt, but it is not a precondition here and must not become one: this skill records selected fields from each repair return and checkpoints a fixed schema, so a flag raised in round two is gone by the time the gate is evaluated after a checkpoint or a re-entry. A comparison that depends on recovering it would pass precisely when the state was lost. The unconditional read costs one look at a body this skill already has, and `repair-pr` does not edit it, because a PR with rounds left does not need its body correct yet. This is the last point at which it is cheap, and the body is the first artifact a human reviewer reads — one spent six rounds arguing for a default that review had already reverted. Update it, or hold the PR and say why: a body that contradicts its own diff is not a clean PR, whatever CI says.

**Dependency-view condition — supplied here by core's completeness report** (passed as `settle-and-merge`'s per-PR dependency-view input, Settle; its *Merge behavior* says what discharges the condition — a standalone run has no preflight to answer it):

- core reported completeness **unproven**, on any boundary → the condition holds the gate exactly as a `MERGE_RISK`. The PR does not merge; return naming the boundary and the discharge.
- The discharge must answer for the **whole view**: a re-run whose dependency transport can read the graph and prove the boundary, or the owner explicitly answering for the view itself — a decision-shaped hold the walkthrough can put to them and record, the recorded ruling retiring the hold as any translated constraint, never opening the gate. NOT: one confirmed edge — a targeted answer proves no omissions, and the known-true-case proof needs a working transport (`implement-issue-core`, *Back the completeness of the set*).
- NOT: routing the hold through `summarize-tranche`'s classification — its bar treats the caveat as reportable, not as a mandatory `MERGE_RISK` (NOTES).
- A **proven** view discharges the condition; nothing to hold.

**Evidence freshness across draft→ready.** The gate accepts no evidence older than this PR's latest draft→ready transition, whichever site performed it — the owner at any moment (re-read the forge before the gate), or the merge path's own publish (`settle-and-merge`, *Merge behavior*), which is the rule's next instance rather than a separate step. Settle passes `hand back` as its publish rule, so this rule — not the three-state rule — governs that publish:

- the transition returns the PR to ordinary supervision: settle again on the next delivered pass (the PR's subscription and check-ins), **never an inline wait**;
- a review round or CI run the transition triggered must complete and come back clean like any other;
- terminating case: a read taken no earlier than the next check-in showing the transition triggered nothing — no new round, no new run, head unchanged — **is** the post-transition evidence. Do not re-trigger a review just to manufacture newer artifacts;
- a run that cannot keep watching returns the durable checkpoint, the PR named as published and awaiting re-evaluation;
- a re-review that finds something: the PR is not clean, does not merge, and takes the ordinary repair path as a ready PR;
- an **explicitly held draft** reaches none of this: excluded from the gate outright — neither published nor merged, reported as held.

**Executing the merge** follows `settle-and-merge`, *Merge behavior*, which scopes the gate's `merge-stack` authorization to exactly this PR. A merge ends supervision: reconcile tracker completion, then return the merge with the gate conditions it passed on.

# Completion

- Return `PR_OPEN`/healthy when the PR is implemented, correctly linked, and has no known CI/review item a remaining budget could repair — a thread reserved for the owner, deferred repairs included, does not stop `PR_OPEN`; it holds the merge gate — after Settle, whose summary and walkthrough are the gate's own inputs.
- Return `MERGED` where the gate's merge completed.
- With persistent monitoring, `supervise-prs`'s loop continues until the PR is finished or terminal, the user stops it, its wake budget is spent, or the monitoring cap elapses.
- Where it returns `cannot-watch`, or stops with the PR still waiting, return a durable checkpoint — never pretend background monitoring continues.
- Return `NEEDS_USER` with exact PR/issue URLs, the remaining failure, attempts performed, and the recommended next action. **A reserved thread is not a remaining failure** — a comment never yields this outcome (`supervise-prs`, *Outcomes*); it is reported and holds the merge gate.

## Structured result

This is a status report, so what it says a PR, a thread or a check *is now* needs a read behind it, or says when it was last read (`references/establish-do-not-assume.md`, *You are about to assert it*).

Return:

- canonical issue URL; tracker; repository;
- outcome: `PR_OPEN` | `MERGED` | `BLOCKED` | `BLOCKED_EXTERNAL` | `FAILED` | `NEEDS_USER`;
- branch/base; PR URL/number; remote head SHA;
- issue linkage verified, and the form emitted — closing keyword, or non-closing `Part of:` because a coverage finding was reported;
- **any design finding core returned in place of a re-siting**, forwarded whole — the value, the objecting call sites and where it belongs; a caller that does not carry it is the only reader it would have had;
- implementation attempts used, and **`supervise-prs`'s report for the PR** (`supervise-prs`, *Report*) — review rounds and CI, review and finding repair cycles against their caps, strongest-model rounds with the locus evidence for each, every review thread reserved for the owner per item kind, final CI and review state, and draft state as created and current with any transition observed and who performed it (a ready-to-draft transition is never this run's);
- the resolved policy actually applied — budgets, `auto-merge` — each with its source (caller, repo config, built-in default), plus any policy file present but unhonourable (an unreadable file is authority the owner meant to grant and did not);
- the merge, where one happened: the gate conditions it passed on, whether the PR was published from draft on the way, and the tracker reconciliation;
- the `summarize-tranche` summary and action points, and the `settle-outstanding-decisions` report — rulings recorded, its one-line decline, or that `auto-request-settle` was off;
- the run's **full posting-identity map** — every entry observed by core, each repair pass, the walkthrough, and a gate-authorized `merge-stack` invocation, under its `(transport, credential)` key; carry all entries, `unestablished` where no authored write was read back (NOTES: why nothing may be collapsed);
- whether the blocker set's completeness was backed or left unproven, and on what boundary;
- the routed documentation review's result, exactly as core reported it — round, status, and any findings with their evidence. It reaches `summarize-tranche` through this line and nowhere else, and **no routed review** is a different state from **a routed review that found nothing**;
- dependencies checked and any source disagreements, exactly as core reported them — including on `PR_OPEN` (NOTES);
- blocker/failure details, including the dependency class each block was judged under;
- recommended user action when needed.
