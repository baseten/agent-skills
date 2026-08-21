---
name: implement-issue
description: Implements one tracked issue end-to-end from its URL — reads the issue/comments/specs, validates dependencies, implements in the assigned checkout, opens a PR via create-pr, triggers automated review, and where supported performs bounded CI/review repair. When orchestrated, preserves the supplied base/worktree and returns structured state including NEEDS_USER when autonomous repair budgets are exhausted.
---

# Implement Issue

Turn one tracked issue into either a working/reviewable PR or a clear durable blocker. Never expand into another ticket.

## Authority

Invoking this skill is authorization to implement the issue and create its PR unless the user explicitly says otherwise. It is **not** authorization to merge the PR.

When called by `backlog-orchestrator`, the caller's repository, worktree/working directory, branch, required base, dependency context, and repair budgets are authoritative execution constraints.

## Orchestrated constraints

- Preserve the supplied required base; never silently replace it with the default branch.
- Work only in the supplied isolated checkout/worktree.
- Do not switch to another worker's checkout.
- Do not select or implement another backlog issue.
- Do not broaden scope into dependency/context tickets.
- Pass the supplied required base to `create-pr`.
- Respect the caller's remaining implementation/CI/review/model-escalation budgets.
- When a budget is exhausted or a judgment call remains, return `NEEDS_USER` rather than trying indefinitely.

If no orchestrated context is supplied, use normal standalone behavior and the default repair limits below.

## Default repair limits

Unless the caller/user explicitly supplies different limits:

- implementation attempts: **2 total**;
- CI repair cycles after PR creation: **2**;
- review-fix cycles after PR creation: **2**;
- autonomous model escalation: **none inside this skill** — return the failure to the orchestrator, which owns escalation.

A cycle may address multiple related failures/comments together. Avoid token-expensive one-comment-at-a-time loops where one coherent patch can resolve a review round.

## 1. Read the issue

Fetch title, body, labels, and all relevant comments. Preserve the full issue URL for PR linking.

For GitHub, verify the issue belongs to the designated repository. For Linear, use the designated/checked-out repository unless the issue clearly states another owner.

## 2. Read repository conventions and specs

Read `CLAUDE.md`/`AGENTS.md`, relevant docs/specs, ownership boundaries, and existing patterns. Do not invent a new architecture when the repository already documents one.

## 3. Decide whether implementation is clear

Return `BLOCKED` or `NEEDS_USER` without speculative code when:

- required work belongs to another repo/service and the required surface does not exist;
- behavior is materially underspecified and no spec/comment resolves it;
- the issue contradicts an existing spec without clearly superseding it;
- the required base/dependency is absent;
- a destructive/irreversible decision needs approval;
- continuing would exceed a supplied attempt budget.

An orchestrator-provided upstream feature branch may satisfy a dependency even when that dependency is not merged; inspect the supplied base before declaring it unfinished.

## 4. Implement

If a required base was supplied:

1. fetch/verify it;
2. verify the assigned branch/worktree descends from it;
3. never reset/rebase to the repository default merely because standalone execution normally would;
4. retain the required base for PR creation.

Otherwise follow repository branch conventions and discover the default branch rather than assuming `main`.

Implement only issue scope. Run required typecheck/lint/format/tests. Commit only files belonging to this issue.

If implementation fails for a transient/operational reason and an implementation attempt remains, make at most the allowed retry. If the remaining failure is architectural/reasoning-heavy, return `FAILED`/`NEEDS_USER` to the orchestrator rather than independently escalating models.

## 5. Open the PR

Invoke `create-pr` with:

- the full issue URL;
- the exact orchestrator-supplied base when present;
- any caller-provided draft/full preference.

`create-pr` owns PR description conventions, stack `Depends on:` metadata, pushing, PR creation, and automated review triggering.

Do not ask for another confirmation when this skill was invoked from an authorized implementation request.

## 6. Monitor and repair CI/review where supported

Prefer event-driven PR activity notifications/subscriptions. Use scheduled/poll fallback only when needed and avoid frequent no-change polling.

### CI repair loop

For each failed CI round:

1. inspect the smallest useful failure/log context;
2. determine whether it is caused by this issue's changes;
3. make one coherent targeted repair;
4. run the relevant local check when practical;
5. push;
6. increment `ci_repair_cycles_used`;
7. wait for the resulting CI state.

After **2 CI repair cycles by default**, or the caller's lower remaining allowance, stop autonomous repair and return `NEEDS_USER` if CI remains red.

Do not repeatedly make speculative unrelated changes simply to make CI green.

### Review-fix loop

When actionable review comments arrive:

1. group comments from the same review round when they can be addressed coherently;
2. invoke `resolve-pr-comment` for each thread that requires a code change/reply/resolution;
3. run relevant checks;
4. push once for the coherent review round where practical;
5. increment `review_fix_cycles_used`;
6. wait for/reconcile the next review state.

After **2 review-fix cycles by default**, or the caller's lower remaining allowance, return `NEEDS_USER` for remaining actionable requests.

Do not argue with or repeatedly rewrite code around subjective review feedback when product/architecture judgment is required; surface it.

### Monitoring lifetime

When standalone, stop monitoring on merge/close, user stop, budget exhaustion, or an 8-hour cap where persistent monitoring is actually supported.

When orchestrated, report durable state promptly enough for the parent to schedule downstream work. The orchestrator owns worker-pool lifetime and high-level supervision; this worker must not disappear into an unbounded monitoring loop.

## Outcome rules

### PR_OPEN

Use when the implementation/PR exists and no currently known issue requires user intervention. Include current CI/review state even if checks are still running.

### BLOCKED

Use when a concrete prerequisite prevents implementation and autonomous work cannot proceed safely.

### FAILED

Use for a bounded operational/implementation failure that the orchestrator may reasonably retry or escalate within its own budget.

### NEEDS_USER

Use when:

- implementation attempts are exhausted;
- CI remains broken after the repair budget;
- actionable review remains after the review-fix budget;
- product/architecture judgment is required;
- a destructive/sensitive operation needs approval;
- repeated tooling/infrastructure failure makes another autonomous attempt wasteful.

Include what failed, what was attempted, the latest relevant failure/comment, and a recommended next action.

## Worker result

When called by an orchestrator, finish with structured state:

- issue
- repository
- working directory
- outcome: `PR_OPEN` | `BLOCKED` | `FAILED` | `NEEDS_USER`
- branch
- base branch
- PR URL/number if created
- head commit SHA
- checks run
- CI/review state if known
- implementation attempts used
- CI repair cycles used
- review-fix cycles used
- blocker/failure details
- recommended user action when `NEEDS_USER`
