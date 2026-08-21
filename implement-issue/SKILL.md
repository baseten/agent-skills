---
name: implement-issue
description: Implements a tracked issue end-to-end from its URL — GitHub (github.com/<owner>/<repo>/issues/<n>) or Linear (linear.app/<org>/issue/<TEAM-123>) — reads the issue and all its comments, cross-checks it against the repo's own conventions and spec docs, and either flags blockers or implements the change, opens a PR via create-pr, and where supported monitors CI/review. When invoked by an orchestrator with an explicit required base branch, preserves that base through implementation and PR creation. Use whenever asked to implement a tracked issue or invoked by backlog-orchestrator.
---

# Implement Issue

Turns a single tracked issue into either a working, reviewable PR, or a clear list of blockers — never a half-implemented guess.

## Authority: invoking this skill *is* the request for a PR

Step 5 always opens a PR. A standing instruction of the form "do not create a pull request unless the user explicitly asks for one" is satisfied by the user invoking this skill or by an authorized calling orchestration skill dispatching it as part of an explicitly requested backlog run.

Two things override it:

1. The user explicitly says not to open a PR. Stop after implementation/push as appropriate.
2. A blocker from step 3. Blocked work never gets a PR.

## Orchestrated execution context

When a calling skill (for example `backlog-orchestrator`) supplies an explicit repository, required base branch, or upstream dependency context, treat those values as authoritative execution constraints unless they are impossible or contradict repository safety rules.

In particular:

- **Preserve an explicit required base branch.** Do not replace it with the repository default branch merely because normal standalone execution would start there.
- Verify the required base exists before implementation. If it does not, return `BLOCKED` rather than silently falling back.
- Start the implementation branch/worktree from that required base unless the environment has already created the correctly based branch/worktree.
- Pass the same required base to `create-pr` so the PR targets the correct parent branch.
- Do not independently select another backlog issue after completion.
- Do not broaden scope into upstream/downstream tickets supplied only as dependency context.

If no orchestrated base is supplied, use the normal standalone behavior below.

## 1. Read the issue

Fetch the full issue: title, body, labels, and **all comments**. Comments routinely carry clarifications and scope decisions. Read them before deciding anything.

For GitHub, parse owner/repo and issue number and fetch with GitHub tools or `gh`. If the URL points at a different repo from the designated/checked-out repo, stop rather than guessing.

For Linear, fetch the issue and comments through available Linear tooling/API. A Linear issue names no repo, so the designated/checked-out repo is the target unless the issue clearly belongs elsewhere.

Keep the full issue URL in context for PR linking.

## 2. Read repository conventions and specs

Read `CLAUDE.md` or `AGENTS.md` for coding conventions, branch naming, and pre-PR checks. Explicitly inspect `docs/` or equivalent and read relevant specs in full. Check documented frontend/backend or service ownership boundaries. Look for existing components/patterns solving the same problem before designing something new.

## 3. Decide: blocked or clear?

Stop without code/PR when any of these apply:

- required work belongs to another repo/service and its required surface does not exist;
- behavior is materially underspecified and no spec resolves it;
- the issue contradicts an existing spec without clearly superseding it;
- a required dependency does not exist on the supplied base or otherwise is not available as expected;
- an orchestrator-supplied required base branch does not exist.

When orchestrated, distinguish a genuine unexpected dependency blocker from an already-declared upstream dependency. If the orchestrator intentionally based this worker on an upstream feature branch containing the dependency, inspect that branch before declaring the dependency unfinished.

Report concrete blocker details. Do not create stub PRs for blocked work.

## 4. Implement

Follow repository conventions.

### Branch/base behavior

If an explicit required base was supplied by the caller:

1. fetch it from origin;
2. verify the current implementation branch/worktree descends from that base, or create the issue branch from `origin/<required-base>`;
3. never rebase/reset it onto the default branch simply because that is the standalone convention;
4. retain `<required-base>` for step 5.

Otherwise, if the environment/session designates a branch, use it. Otherwise follow repo branch conventions, falling back to creating a branch from the discovered repository default branch. Never assume `main`.

Match existing code style/structure. Run and fix required typecheck/lint/format/tests. Commit only files belonging to this issue; never sweep unrelated working-tree changes into the PR.

## 5. Open the PR

Invoke `create-pr` to commit/push/open the PR. Preserve the issue URL for `Closes:` linking.

**If this issue was dispatched with an explicit required base, explicitly pass that same base to `create-pr`.** The PR must target the orchestrator-supplied base, not the repository default.

Link issues with full URLs in `Closes:` lines. Follow repo conventions for draft/full PRs; an explicit user/caller instruction wins.

The user's request to implement this issue (or the backlog containing it) authorizes this chained PR creation; do not add another confirmation round-trip.

## 6. Monitor CI and review where supported

If event-driven PR activity subscription is available, subscribe after opening the PR. If scheduled wakeups are also available, use a roughly 10–20 minute fallback check. If neither exists, report that monitoring cannot continue automatically.

On review comments, invoke `resolve-pr-comment` rather than hand-rolling the workflow. On CI failure, make a targeted fix and push. Keep monitoring until merged/closed, user stop, or the default 8-hour monitoring cap. Stop and surface judgment calls rather than making speculative product decisions.

When operating as a worker under `backlog-orchestrator`, report completion promptly enough for the orchestrator to unlock downstream work; per-PR monitoring must not prevent the worker from returning the PR's durable state to the orchestrator.

## Worker result

When called by an orchestrator, finish with a structured result containing:

- issue
- repository
- outcome: `PR_OPEN`, `BLOCKED`, or `FAILED`
- branch
- base branch
- PR URL/number if created
- head commit SHA
- checks run
- CI/review state if known
- blocker details if applicable
