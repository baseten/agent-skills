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

## 2. Dependency precondition

Establish what this issue is blocked by, and whether that work exists, before preparing branch state. One level deep — this issue's own blockers. Transitive graph work belongs to `validate-backlog` and the orchestrator.

Do this even when a caller judged the issue READY. That judgement was computed from a dependency read that can be wrong in a way it cannot detect, and this is the cheapest place in the system to notice.

### Take the union of three sources

- dependencies named in prose — the issue body **and its relevant comments**: `Depends on:`, `Blocked by:`, a `Dependencies` section, build-order wording. Comments matter as much as the body, since a blocker discovered after filing is usually added as a comment rather than an edit, and step 1 has already read them;
- tracker-native dependency metadata;
- dependency context the caller supplied.

Never rely on one alone, because they fail in different directions. Prose goes stale the moment someone edits a ticket without updating it. Native metadata can be truncated by a scoped or relayed credential, which returns a partial list with a success status and no warning — and **a partial list is more dangerous than an empty one**, because it presents as a complete answer. One blocker returned where four exist reads as "nearly ready" and suppresses exactly the doubt that would have sent you looking elsewhere. Individually each source has a failure mode that resembles success; together they are hard to fool.

### Resolve each blocker's real state

Read each referenced issue directly. A plain issue read works across repositories even where dependency-endpoint reads do not, so a cross-repository blocker stays checkable when the edge that should have declared it is invisible.

### Gate on availability of the work, not on issue state

An open blocker does not mean the work is unavailable. A stacked child is dispatched precisely while its parent is implemented but unmerged — that is the normal case, not an error. Gating on "the blocker is still open" would refuse nearly every stacked child and be worse than no gate at all.

| finding | action |
|---|---|
| the dependency's implementation is present in the supplied base, or otherwise reachable from this checkout | proceed |
| the caller supplied dependency context asserting it is satisfied | proceed — the caller owns that claim |
| no implementation anywhere: no merged PR, nothing in the base, no caller assurance | return `BLOCKED`, naming each unmet blocker by canonical full URL |

Never implement against a contract that does not exist yet in order to keep a worker busy. The behavioural catch in step 1 — `BLOCKED` when required external work is absent — only fires when the absence breaks the code. A UI ticket whose backend is missing will render against the parts that do exist, stub the rest, pass its mocked tests, and produce a PR that looks complete and is not.

### Report what you found

A dependency named in prose that native metadata did not return is a finding, not a discrepancy to reconcile silently. It means either a missing native edge or a transport that cannot see the one that exists. Surface it either way: this worker is already reading both sources for one issue, which makes it the cheapest detector in the system for a blind spot the orchestrator cannot see from above.

Where the caller supplied its own dependency context, reconcile it against what you found and report any disagreement. The caller's view being wrong is the information worth returning.

## 3. Prepare durable branch state

Before substantial implementation:

1. verify/fetch the exact required base;
2. verify the assigned branch/worktree descends from it;
3. create the issue branch if it does not exist;
4. **push the issue branch to the remote immediately**, even if it initially contains no issue-specific commit, so restart logic has a durable branch identity.

Follow repository branch naming conventions. Prefer a branch name containing the tracker issue key/number when repo conventions allow because this improves recovery, but never violate documented repo naming rules merely to do so.

## 4. Implement with remote checkpoints

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

## 5. Final local verification

Run the repository-required typecheck/lint/format/tests. Fix in-scope failures within the implementation budget. Push the resulting final implementation commit/checkpoint.

## 6. Create and verify PR

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
- dependencies checked: for each, the canonical full URL, which of the three sources named it, and how it resolved (present in base / caller-asserted / unmet);
- source disagreements: any dependency the prose named that native metadata did not return, and any mismatch against the caller's supplied dependency context — report these even on a successful run, since they are evidence about the graph rather than about this issue;
- draft state as created, exactly as `create-pr` reported it;
- checkpoints pushed: count/SHAs when useful;
- checks run;
- implementation attempts used;
- blocker/failure details;
- recommended user action when `NEEDS_USER`.
