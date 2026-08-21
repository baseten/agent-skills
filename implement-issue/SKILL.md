---
name: implement-issue
description: Single-issue orchestrator for one tracked issue from its canonical full URL. Composes implement-issue-core for issue→code→checks→durable PR, then owns bounded CI/review monitoring and dispatches repair-pr as needed until the PR is healthy, blocked, or needs user input. Useful standalone and as a one-issue workflow.
---

# Implement Issue

Orchestrate exactly one tracked issue end-to-end while preserving the convenience of a single command.

This skill is intentionally a **one-issue orchestrator**. It composes reusable primitives rather than duplicating their implementation logic:

- `implement-issue-core` — issue reading, implementation, durable checkpoints, local checks, PR creation;
- `repair-pr` — one bounded CI or review repair pass;
- `create-pr` — tracker linkage, stack metadata, PR creation, review trigger;
- `resolve-pr-comment` — review-thread fix/reply/resolve mechanics used by `repair-pr`.

It does not schedule other backlog issues and never merges unless the user separately invokes an authorized merge workflow.

## Authority

Invoking this skill authorizes implementation and PR creation for the supplied issue unless the user explicitly says otherwise. It does **not** authorize merging.

The issue's **full URL is canonical identity** throughout the workflow. Short keys/numbers may be shown for readability but never replace the full URL in durable state.

## Inputs / constraints

When a caller supplies repository, worktree, branch, required base, dependency context, tracker, and budgets, preserve them exactly.

Defaults when standalone:

- implementation attempts: **2 total**;
- CI repair cycles: **2**;
- review-fix cycles: **2**;
- monitoring cap: **8 hours** where persistent/event-driven monitoring is actually supported.

Do not broaden scope into another issue.

# Phase 1 — durable implementation

Invoke `implement-issue-core` with the canonical issue URL and all supplied execution constraints.

Do not hand-roll implementation logic here.

If core returns `BLOCKED`, `FAILED`, or `NEEDS_USER`, surface that result. If a standalone user clearly requested strongest-model retry, that can be handled by the surrounding Claude session; this skill itself should not create an unbounded model-escalation loop.

If core returns `PR_OPEN`, record:

- PR URL;
- branch/base;
- remote head SHA;
- tracker linkage verification;
- implementation attempts used.

At this point the code is already durable remotely even if the current container disappears.

# Phase 2 — single-issue PR supervision

After PR creation, this skill owns monitoring **only because it is the standalone single-issue orchestrator**.

Prefer event-driven PR/check/review notifications where available. Use bounded polling fallback only when no event mechanism is available. Avoid frequent no-change polling.

Maintain explicit state:

```text
PR: <URL>
CI repair cycles: <used>/<limit>
Review repair cycles: <used>/<limit>
Current remote head: <SHA>
State: waiting | repairing-ci | repairing-review | healthy | needs-user
```

## CI failure

When CI fails:

1. inspect enough check/log context to identify the relevant failure;
2. if the failure is attributable to this PR and the CI budget remains, invoke `repair-pr` once with `repair type = ci`;
3. pass the exact failure context and remaining budget;
4. adopt the returned remote head SHA;
5. wait for the next CI result;
6. after the budget is exhausted, return `NEEDS_USER` rather than trying again.

If CI is clearly unrelated/external/flaky and no code repair is justified, report/monitor it without consuming a repair cycle.

## Review feedback

When actionable review feedback arrives:

1. group one coherent review round;
2. if review budget remains, invoke `repair-pr` once with `repair type = review` and the relevant threads/comments;
3. adopt the returned remote head;
4. retrigger/request review when repository convention requires it;
5. wait for the next review state;
6. after the budget is exhausted, return `NEEDS_USER`.

Subjective product/architecture judgment returns `NEEDS_USER` immediately rather than burning repair cycles.

# Completion

Return `PR_OPEN`/healthy when the PR is implemented, linked correctly, and has no currently known CI/review item requiring autonomous repair. When persistent monitoring is supported, continue until healthy, merge/close, user stop, budget exhaustion, or monitoring cap.

Return `NEEDS_USER` with the exact PR/issue URLs, remaining failure/comment, attempts performed, and recommended next action when autonomous repair cannot safely finish.

## Structured result

Return:

- canonical issue URL;
- tracker;
- repository;
- outcome: `PR_OPEN` | `BLOCKED` | `FAILED` | `NEEDS_USER`;
- branch/base;
- PR URL/number;
- remote head SHA;
- issue linkage verified;
- implementation attempts used;
- CI repair cycles used;
- review-fix cycles used;
- final CI/review state;
- blocker/failure details;
- recommended user action when needed.
