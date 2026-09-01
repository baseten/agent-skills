---
name: repair-pr
description: Performs one bounded repair pass on an existing pull request for a CI failure, actionable review feedback, or a settle-time finding, using the PR's existing branch/worktree and returning immediately after pushing the repair. Use under implement-issue or backlog-orchestrator; it does not own long-lived monitoring.
---

# Repair PR

Perform one bounded, targeted repair pass on an existing PR, then return durable state to the caller.

This file is the contract; the reasoning behind its rules lives in `NOTES.md` beside it, keyed by section. NOTES explains; it never overrides.

## Inputs

- PR URL; canonical issue URL; repository; dedicated checkout/worktree for the PR branch;
- repair type: `ci`, `review` or `finding`;
- the evidence matching the type: exact failure logs/check summaries for `ci`; review thread(s) for `review`; for `finding`, the settle-time finding verbatim — a `summarize-tranche` `IN_FLIGHT_FIX` action point, or a recorded walkthrough ruling that requires this PR's code to change — with the durable site it lives at;
- remaining repair-cycle budget;
- expected branch/base when supplied.

## Hard constraints

- Never implement unrelated backlog scope; never merge the PR.
- Never wait for the next CI/review event, **and never delegate the wait** — no scheduled check-in, trigger, or PR-activity subscription: the caller supervises this PR, and a wake armed here outlives the pass that armed it (NOTES).
- One invocation consumes at most one repair cycle.
- **A supplied remaining repair-cycle budget of zero makes this a classify-only invocation, and that is enforced here rather than by the caller.** Callers dispatch a review round with the budget spent on purpose — an unclassified thread has no draft, and the settlement path needs one to clear the merge gate — so this skill must honour the zero rather than treat the dispatch as authorization to repair. Invoke `resolve-pr-comment` in its **classify-only** mode and say so in the invocation (*Classify-only invocations*) — that mode is what stops the callee's own workflow applying and pushing the fix, which skipping steps 3-5 here does not, since those steps constrain this skill and not the one it invokes. Classify and draft every supplied thread; **make no correction, run no verification, commit nothing and push nothing**; return `NO_CODE_CHANGE` and consume no cycle. Every thread that would have been repairable comes back as a **deferred-repair item**: `NEEDS_USER` on budget grounds, carrying the change it asks for and **no draft**. It is a third item kind alongside a question item and a no-action one, and it needs to be, because a draft is defined only for the two question shapes `resolve-pr-comment` produces — an answer from the work, or an owner's choice between options (*The draft reply*). A repairable change request is neither, so requiring a draft here would force a query-shaped draft to be invented for work that simply did not happen, and the caller would then put it to the owner as though there were something to decide. There is not: the thread wants a diff, and the budget ran out. Say *budget grounds* in the item, because the reason differs from the kind test and the caller reports the two differently. Nothing is resolved either: a thread is never resolved without an applied fix (`resolve-pr-comment`), and there is none. Without this branch the cap does not bind at all: steps 3-5 below would push, the caller would count and retrigger that push, and rounds would continue past the configured limit.
- Every authored forge write this pass makes — directly or through `resolve-pr-comment` — follows the posting-identity rule (`backlog-orchestrator`, *Posting identity*). Select the author from **the caller's map entry for this pass's own selected `(transport, credential)` pair** — `unestablished` where the map carries no such pair — never from an entry for a pair this pass is not writing under; pass that selection into `resolve-pr-comment` (NOTES). The Output read-back still happens and is what the caller merges.
- A supplied failure/comment requiring product or architecture judgment → return `NEEDS_USER`, never guess.
- Never select or escalate your own model. A pass that judges itself under-powered reports the locus evidence (Output) and returns (NOTES).

## CI repair (`repair type = ci`)

1. inspect the smallest useful failing check/log context;
2. determine whether the failure is attributable to this PR;
3. unrelated/external/flaky with no justified code change → report that; change nothing;
4. otherwise make one coherent targeted repair;
5. run the smallest relevant local verification;
6. commit only issue-owned changes; push;
7. return immediately with the new head SHA and checks run.

Never chase multiple unrelated failures speculatively in one cycle unless they share one clear root cause.

## Review repair (`repair type = review`)

1. group the supplied actionable comments forming one coherent review round;
2. invoke `resolve-pr-comment` for every supplied thread, in unattended mode — and in **classify-only** mode where the remaining budget is zero (above), which is the only thing that keeps the callee from pushing a fix this invocation is not allowed to make — so each is classified and a thread needing a human comes back as a `NEEDS_USER` item with its draft rather than being answered (`resolve-pr-comment`, *Unattended callers*). **Invoke it even where the whole round looks like questions** — the caller dispatches such rounds precisely to get them classified and drafted, so returning early without invoking it defeats the dispatch. Where every supplied thread classifies `NEEDS_USER`, there is nothing to fix: push nothing, return `NO_CODE_CHANGE` with the items and their drafts, and consume no cycle;
3. make only the requested/in-scope corrections — **skipped entirely on a classify-only invocation** (zero remaining budget, above);
4. run relevant local verification — same;
5. commit/push once for the coherent round where practical — same, and there is nothing to push;
6. verify required replies/thread resolutions were performed;
7. count the actionable review threads still unresolved on the PR — **including any outside the round supplied to this invocation** — and report the number;
8. return immediately.

- Never spend cycles arguing with subjective feedback or inventing product intent.
- **Never change the PR's draft state.** Promotion is a supervisor decision needing the whole-PR picture; report the remaining-thread count and let the caller decide (NOTES).

## Finding repair (`repair type = finding`)

The evidence is a settle-time finding — an `IN_FLIGHT_FIX` action point from `summarize-tranche`, or a recorded `settle-outstanding-decisions` ruling that requires this PR's code to change — supplied verbatim, the way `ci` supplies logs and `review` supplies threads. It names actionable work on this PR that no failing check and no review thread carries (NOTES; the caller's budget is its own counter, `finding-repair-cycles`).

1. read the supplied finding and its durable site;
2. verify it still holds against the current head — a later push may already have fixed or mooted it. Where it no longer applies → return `NO_CODE_CHANGE` with the reason; change nothing; no cycle is consumed;
3. make one coherent targeted repair scoped to the finding — for a ruling, the change the owner's answer implies, never a reopening of the question they ruled on;
4. run the smallest relevant local verification;
5. commit only issue-owned changes; push;
6. return immediately with the new head SHA and checks run.

Never widen into other action points or findings the caller did not supply, and never resolve or reply to review threads here — a finding is not a thread; where a thread carries the same work, the caller dispatches `review` instead.

## Recovery / checkpointing

- Before editing, fetch the remote PR branch and verify the assigned checkout is on/derived from the current remote head — the remote branch is durable state.
- Every repair that changes code ends with a **pushed commit**. Never return success with repair work existing only in the local worktree (NOTES).

## Output

Return:

- PR URL; canonical issue URL; repair type;
- outcome: `REPAIRED` | `NO_CODE_CHANGE` | `FAILED` | `NEEDS_USER`;
- branch/base; old head SHA; new remote head SHA if changed;
- repair cycle consumed: yes/no;
- checks run; review threads resolved/replied when relevant;
- **every posting-identity entry observed** for this pass's authored writes — its own and any made through `resolve-pr-comment` — under the `(transport, credential)` key each was observed on, whether or not it differed from the invoking user, and `unestablished` where no authored write was read back. Read it back from the first such write rather than echoing the caller's map: this pass's transports may not be the caller's, and the observation is the caller's only evidence about this worker's write path (NOTES);
- actionable review threads still unresolved on the PR: count;
- **every thread classified no-action**, one entry each, forwarded from `resolve-pr-comment` (*A comment that wants nothing*): thread URL and why it wants nothing, no draft. Forward these even though they ask nothing of anyone — **this contract is the only path by which they reach the caller**, and a caller that never records one re-groups the thread on its next supervision cycle, classifies it again, and loops without bound because a classify-only pass consumes no cycle. Dropping them here is silent: the pass looks clean and the acknowledgement never stops coming back;
- **every thread classified `NEEDS_USER`**, one entry each: thread URL, root author, what it asks, and the draft reply `resolve-pr-comment` produced for it (`resolve-pr-comment`, *The draft reply*). Pass the draft through **verbatim** — do not summarise it, and do not post it: the caller hands it to the owner, and a compressed draft is one they have to redo. A count alone is not enough here either, since the caller reports these individually and holds the merge gate on them (`backlog-orchestrator`, *Per-repository policy configuration*, owns the classification rule). Report them whether or not this pass pushed anything; a round that fixed three threads and escalated one has both results;
- **whether any finding supplied to this pass sits on a locus an earlier repair of this PR wrote** — a reshaped version of something an earlier round addressed, or a new finding inside text a previous repair authored — naming the file, region, and earlier commit. The caller uses this for the next round's model; it can read the same signal from commit history, so this is corroboration (NOTES);
- failure/judgment details; recommended next action.
