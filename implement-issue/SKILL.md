---
name: implement-issue
description: Implements one tracked issue end-to-end from its canonical URL (GitHub, Linear, or another supported tracker) — reads issue/comments/specs, validates dependencies, implements in the assigned checkout, opens a PR via create-pr, triggers automated review, and where supported performs bounded CI/review repair. When orchestrated, preserves supplied base/worktree and returns structured state including NEEDS_USER when repair budgets are exhausted.
---

# Implement Issue

Turn one tracked issue into either a working/reviewable PR or a clear durable blocker. Never expand into another ticket.

## Authority

Invoking this skill authorizes implementation and PR creation unless the user explicitly says otherwise. It does **not** authorize merging.

When called by `backlog-orchestrator`, the caller's repository, worktree, branch, required base, dependency context, tracker issue URL, and repair budgets are authoritative.

## Canonical issue identity

The issue's full URL is its canonical identity throughout the workflow.

Examples:

- GitHub: `https://github.com/owner/repo/issues/123`
- Linear: `https://linear.app/workspace/issue/TEAM-123/slug`

A short key (`#123`, `TEAM-123`) may be shown additionally for readability but must not replace the full URL in worker results, PR-linking context, dependency maps, or recovery state.

Determine tracker from the URL and use its native issue API/integration when available.

## Orchestrated constraints

- Preserve the supplied required base; never silently replace it with default.
- Work only in the supplied isolated checkout/worktree.
- Do not switch to another worker checkout.
- Do not choose or implement another issue.
- Do not broaden scope into dependency/context tickets.
- Pass the canonical issue URL and supplied required base to `create-pr`.
- Respect implementation/CI/review/escalation budgets.
- When a budget is exhausted or a judgment call remains, return `NEEDS_USER`.

## Default repair limits

Unless overridden:

- implementation attempts: **2 total**;
- CI repair cycles: **2**;
- review-fix cycles: **2**;
- model escalation: owned by orchestrator, not this skill.

A cycle may address multiple related failures/comments coherently.

## 1. Read the issue

Fetch title, body, state, labels/properties, native parent/sub-issue relationships, native blocker/dependency relationships, and relevant comments using the issue tracker appropriate to the canonical URL.

For GitHub, verify repository ownership. For Linear, use the designated repository unless issue/spec/project metadata indicates another repo.

Preserve the full URL for PR linkage and results.

## 2. Read repository conventions/specs

Read `CLAUDE.md`/`AGENTS.md`, relevant docs/specs, ownership boundaries, and existing patterns.

## 3. Decide whether implementation is clear

Return `BLOCKED` or `NEEDS_USER` rather than speculative code when required work is missing, behavior is materially underspecified, the issue contradicts current specs, a required base is absent, a destructive decision needs approval, or budgets are exhausted.

An orchestrator-supplied upstream feature branch may satisfy an otherwise-unmerged dependency; inspect the supplied base first.

## 4. Implement

If a required base was supplied, fetch/verify it and ensure the assigned worktree/branch descends from it. Never reset/rebase it to default just because standalone behavior normally would.

Otherwise follow repo branch conventions and discover default branch rather than assuming `main`.

Implement only issue scope. Run required typecheck/lint/format/tests. Commit only files belonging to this issue.

For transient failure, retry only within remaining implementation budget. Return reasoning-heavy repeated failure to the orchestrator for its single allowed escalation.

## 5. Open the PR

Invoke `create-pr` with:

- the **full canonical issue URL**;
- tracker identity when useful;
- exact orchestrator-supplied base when present;
- draft/full preference when supplied.

`create-pr` owns tracker-specific linkage semantics:

- GitHub issues use a full-URL closing relationship so merge can auto-close the issue;
- Linear issues retain the full Linear URL and use the Linear issue ID/magic-word convention needed for GitHub integration/status automation;
- other trackers follow documented integration rules.

`create-pr` also owns stack `Depends on:` metadata, pushing, PR creation, verification, and automated review triggering.

## 6. Monitor and repair CI/review where supported

Prefer event-driven activity. Use bounded polling only when needed.

### CI repair

For each failed CI round: inspect minimal useful logs, decide whether failure belongs to this PR, make one coherent targeted repair, run relevant local checks, push, increment cycle count, and reconcile resulting CI. After the allowed cycles, return `NEEDS_USER` if still red.

### Review repair

Group coherent comments by review round. Invoke `resolve-pr-comment` for actionable threads, run checks, push coherently, increment cycle count, and reconcile. After the allowed cycles, return `NEEDS_USER` for remaining actionable requests.

Do not burn cycles on subjective/product judgment; surface it.

### Monitoring lifetime

Standalone monitoring stops on merge/close, user stop, budget exhaustion, or the supported monitoring cap. Under orchestration, return durable state promptly; parent owns worker-pool lifetime.

## Outcome rules

- `PR_OPEN`: implementation/PR exists and no known item requires user intervention.
- `BLOCKED`: concrete prerequisite prevents safe implementation.
- `FAILED`: bounded operational failure orchestrator may retry/escalate.
- `NEEDS_USER`: budgets exhausted, persistent CI/review failure, product/architecture decision, destructive operation, or repeated infrastructure failure.

## Worker result

When orchestrated return:

- canonical issue URL
- short issue key/number if useful
- tracker (`github`, `linear`, ...)
- repository
- working directory
- outcome: `PR_OPEN` | `BLOCKED` | `FAILED` | `NEEDS_USER`
- branch
- base branch
- PR URL/number
- head SHA
- issue linkage verified: yes/no
- checks run
- CI/review state
- implementation attempts used
- CI repair cycles used
- review-fix cycles used
- blocker/failure details
- recommended user action when `NEEDS_USER`
