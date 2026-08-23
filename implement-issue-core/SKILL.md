---
name: implement-issue-core
description: Implements exactly one tracked issue from its canonical full URL through code changes, local checks, durable remote checkpoints, and creation of a correctly linked PR. It does not own long-lived CI/review monitoring. Use as the implementation primitive under implement-issue or backlog-orchestrator.
---

# Implement Issue Core

Implement exactly one tracked issue to a durable PR state. This is a worker primitive, not a backlog scheduler and not a long-lived PR monitor.

## Inputs

Accept:

- canonical full issue URL (GitHub, Linear, or another supported tracker);
- repository;
- dedicated working directory/worktree;
- issue branch;
- exact required base branch;
- optional upstream dependency context;
- implementation-attempt budget;
- draft/full PR preference when supplied.

The full issue URL is canonical identity. Never replace it with a short issue key in durable state or PR-linking context.

## Hard constraints

- Own exactly one issue.
- Work only in the supplied isolated checkout/worktree when orchestrated.
- Preserve the exact supplied base branch.
- Never broaden scope into dependency/context tickets.
- Never merge the PR.
- Never enter a long CI/review monitoring loop. Return after implementation, checks, PR creation, and durable state verification.

## 1. Read issue + repository context

Read the issue title/body, relevant comments, tracker-native parent/dependency metadata, repository `CLAUDE.md`/`AGENTS.md`, relevant specs/docs, and existing implementation patterns.

Return `BLOCKED`/`NEEDS_USER` rather than guessing when scope is materially underspecified, required external work is absent, the supplied base is invalid, or a destructive/product decision needs approval.

## 2. Prepare durable branch state

Before substantial implementation:

1. verify/fetch the exact required base;
2. verify the assigned branch/worktree descends from it;
3. create the issue branch if it does not exist;
4. **push the issue branch to the remote immediately**, even if it initially contains no issue-specific commit, so restart logic has a durable branch identity.

Follow repository branch naming conventions. Prefer a branch name containing the tracker issue key/number when repo conventions allow because this improves recovery, but never violate documented repo naming rules merely to do so.

## 3. Implement with remote checkpoints

Implement only the issue scope and run required local checks.

Do not allow significant completed work to exist only in the ephemeral worktree. Create and push checkpoint commits after meaningful coherent milestones, for example:

- schema/model/API portion complete;
- component/service implementation complete;
- tests added;
- significant refactor complete;
- before entering a potentially long debugging/test phase.

Checkpoint rules:

- checkpoint commits must compile/be internally coherent where practical;
- never checkpoint secrets, generated junk, or unrelated files;
- do not commit every tiny edit merely as a heartbeat;
- commit only issue-owned paths;
- push each checkpoint to the issue branch;
- WIP checkpoint history is acceptable because normal squash-merge workflows remove it from the destination branch.

The goal is bounded data loss if a cloud container disappears: at most the work since the last meaningful checkpoint, not the entire implementation.

If an implementation retry is allowed, use only the caller's remaining budget. Return reasoning-heavy repeated failure to the caller rather than escalating models autonomously.

## 4. Final local verification

Run the repository-required typecheck/lint/format/tests. Fix in-scope failures within the implementation budget. Push the resulting final implementation commit/checkpoint.

## 5. Create and verify PR

Invoke `create-pr` with:

- canonical full issue URL;
- exact required base;
- tracker identity when useful;
- draft/full preference when supplied.

`create-pr` owns tracker-specific linkage, stack `Depends on:` metadata, review trigger policy, and PR creation.

After creation verify durable state:

- PR exists;
- expected head branch/base are correct;
- canonical issue linkage is correct;
- remote branch head contains the final pushed implementation state.

Do not wait indefinitely for CI or review after this point.

## Output

Return structured state:

- canonical issue URL;
- tracker;
- repository;
- working directory;
- outcome: `PR_OPEN` | `BLOCKED` | `FAILED` | `NEEDS_USER`;
- branch;
- base branch;
- PR URL/number;
- remote head SHA;
- issue linkage verified: yes/no;
- draft state as created, exactly as `create-pr` reported it;
- checkpoints pushed: count/SHAs when useful;
- checks run;
- implementation attempts used;
- blocker/failure details;
- recommended user action when `NEEDS_USER`.
