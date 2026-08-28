---
name: repair-pr
description: Performs one bounded repair pass on an existing pull request for either CI failure or actionable review feedback, using the PR's existing branch/worktree and returning immediately after pushing the repair. Use under implement-issue or backlog-orchestrator; it does not own long-lived monitoring.
---

# Repair PR

Perform one bounded, targeted repair pass on an existing PR, then return durable state to the caller.

## Inputs

Accept:

- PR URL;
- canonical issue URL;
- repository;
- dedicated checkout/worktree for the PR branch;
- repair type: `ci` or `review`;
- exact failure logs/check summaries or review thread(s);
- remaining repair-cycle budget;
- expected branch/base when supplied.

## Hard constraints

- Do not implement unrelated backlog scope.
- Do not merge the PR.
- Do not wait indefinitely for the next CI/review event, and do not delegate the wait — no scheduled check-in, trigger, or PR-activity subscription. The caller is already supervising this PR, and a wake armed here outlives the repair pass that armed it.
- One invocation consumes at most one repair cycle.
- Any authored forge write this pass makes, directly or through `resolve-pr-comment`, follows the posting-identity rule stated in `backlog-orchestrator` (*Posting identity*). The author is decided by the entry for **this pass's own selected `(transport, credential)` pair** — taken from the map the caller passed where it carries that pair, `unestablished` (the degraded path) where it does not — never by an entry for a pair this pass is not writing under: the caller's transports may not be this pass's. A matching caller entry answers selection only; the read-back the Output contract requires still happens, and is what the caller merges. Pass that selection into `resolve-pr-comment` rather than leaving it to resolve one of its own.
- If the supplied failure/comment requires product or architecture judgment, return `NEEDS_USER` instead of guessing.

## CI repair

When `repair type = ci`:

1. inspect the smallest useful failing check/log context;
2. determine whether the failure is attributable to this PR;
3. if it is unrelated/external/flaky and no code change is justified, report that rather than changing code;
4. make one coherent targeted repair when appropriate;
5. run the smallest relevant local verification;
6. commit only issue-owned changes;
7. push the repair branch;
8. return immediately with the new head SHA and checks run.

Do not chase multiple unrelated failures speculatively in one cycle unless they share one clear root cause.

## Review repair

When `repair type = review`:

1. group the supplied actionable comments that form one coherent review round;
2. invoke `resolve-pr-comment` for threads requiring code changes/replies/resolution;
3. make only the requested/in-scope corrections;
4. run relevant local verification;
5. commit/push once for the coherent review round where practical;
6. verify required replies/thread resolutions were performed;
7. count the actionable review threads still unresolved on the PR — including any outside the round supplied to this invocation — and report the number;
8. return immediately.

Do not spend cycles arguing with subjective feedback or inventing product intent.

Never change the PR's draft state. Promoting a draft PR to ready once its first review round is fully resolved is a supervisor decision that needs the whole-PR picture — which review rounds have completed, what the PR's as-created draft state was, whether CI is green. Report the remaining-thread count and let the caller decide.

## Recovery / checkpointing

Before editing, fetch the remote PR branch and verify the assigned checkout is on/derived from the current remote head. The remote branch is durable state.

Every repair that changes code must end with a pushed commit. Never return success with repair work existing only in the local worktree.

## Output

Return:

- PR URL;
- canonical issue URL;
- repair type;
- outcome: `REPAIRED` | `NO_CODE_CHANGE` | `FAILED` | `NEEDS_USER`;
- branch/base;
- old head SHA;
- new remote head SHA if changed;
- repair cycle consumed: yes/no;
- checks run;
- review threads resolved/replied when relevant;
- **every posting-identity entry observed** for this pass's authored writes — its own and any made through `resolve-pr-comment` — under the `(transport, credential)` key each was observed on, reported whether or not it differed from the invoking user, and as `unestablished` where no authored write was read back. Read it back from the first such write rather than echoing entries from the caller's map: a repair pass can run on transports the caller never used, so its `gh` reply can establish an invoking-user path where the caller had only observed an agent-authored one. That observation is the caller's only evidence about this worker's write path, and it is what re-opens a provisionally unavailable review trigger (see `backlog-orchestrator`, *Posting identity*);
- actionable review threads still unresolved on the PR: count;
- failure/judgment details;
- recommended next action.
