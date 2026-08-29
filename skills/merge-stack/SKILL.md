---
name: merge-stack
description: Safely merge one PR, a prefix of a stacked PR chain, or an entire same-repository PR stack, then rebase/restack every affected descendant so merged parent commits do not leak into child PR diffs. Discovers stack structure from actual PR base/head relationships and machine-readable `Depends on:` metadata. Use when asked to merge a stacked PR, merge part of a stack, merge through a PR, or merge an entire stack.
---

# Merge Stack

Safely merge stacked pull requests while preserving clean child diffs.

This file is the contract; the reasoning behind its rules lives in `NOTES.md` beside it, keyed by section. NOTES explains; it never overrides.

A stacked PR is represented durably by ordinary GitHub PR base/head relationships. A child PR may also include this machine-readable line near the top of its body:

```text
Depends on: https://github.com/<owner>/<repo>/pull/<n>
```

The base/head relationship is authoritative. `Depends on:` is human-visible metadata and a discovery aid; never trust it when it contradicts the actual PR base (NOTES).

## Authority and default scope

Invoking this skill authorizes the merges required by the requested mode and the force-with-lease pushes / PR-base updates required to restack affected descendants. Never ask again for each mechanical step.

Never merge more PRs than the requested mode permits.

Supported modes:

1. **Merge this PR** — default when given only one PR URL. Merge exactly that PR, then restack all open descendants above it. Never merge descendants.
2. **Merge through PR X** — merge the unmerged ancestor chain from the stack root through X, in dependency order, restacking after each merge. Leave descendants above X open and correctly rebased.
3. **Merge entire stack** — only when the user explicitly asks for the whole stack. Merge every reachable PR in dependency/topological order.

If the request is ambiguous between one PR and the whole stack, choose mode 1.

## Preconditions

All PRs in one stack must belong to the same repository. Cross-repository issue dependencies are not Git stacks and are out of scope.

Before making writes:

- determine the exact repository from the supplied PR;
- read `CLAUDE.md` / `AGENTS.md` for merge conventions;
- discover the repository default/integration branch;
- fetch the target PR and all open PRs that are ancestors or descendants in its stack;
- inspect each PR's state, draft state, head branch/SHA, base branch/SHA, mergeability/check state, body, and `Depends on:` line;
- fetch every involved head/base branch locally so old commit objects remain available even if GitHub deletes a branch after merge;
- require a clean working tree or use isolated temporary worktrees.

Never depend on `.git/gh-stack` or native GitHub Stack metadata.

## Discover the stack

Build a directed graph where parent -> child when the child's PR base branch equals the parent's PR head branch.

Use `Depends on:` to cross-check and to help locate candidate PRs, but validate every metadata edge against actual base/head branches.

For each open PR record at minimum:

```text
number
url
head branch
head SHA
base branch
base SHA
Depends on URL, if present
state / draft / checks / mergeability
```

Detect and stop on the affected path for:

- `Depends on:` pointing to a PR whose head is not the child's base;
- cycles;
- multiple parent PRs claiming the same child base relationship;
- a child whose base branch is not available;
- cross-repository `Depends on:` metadata;
- a branch used by unrelated open PRs where rewriting it would affect work outside the requested stack.

Fanout is valid: one parent may have multiple direct children.

## Parent-before-child rule

Never merge a child PR while its parent PR is still open.

For `merge through` or `merge entire stack`, always process the graph in parent-before-child topological order. A child can be considered for merge only after its parent has merged and the child has been successfully restacked onto the parent's former base (NOTES: what merging out of order does).

## Readiness before each merge

Immediately before merging a PR, refresh its GitHub state.

Never bypass repository protection. Stop that PR if it is:

- draft;
- closed;
- failing required checks;
- blocked by unresolved required review/change requests;
- reported unmergeable/conflicted;
- based on another still-open stack parent;
- otherwise prohibited by repository policy.

A blocked node stops only descendants that depend on it. In an entire-stack fanout, independent sibling paths may continue when safe.

Use the repository/user's requested merge method. If none is specified, follow repository conventions/settings; never invent a different method merely to simplify restacking.

## Core operation: merge one node and restack descendants

For a PR P being merged, snapshot **before the merge**:

```text
P_HEAD_OLD = P's current head SHA
P_HEAD_BRANCH = P's head branch
P_BASE_BRANCH = P's base branch
```

Also snapshot the current head SHA of every descendant before rewriting begins.

Merge P through the available GitHub integration (`merge_pull_request` / equivalent) or `gh` when available.

After GitHub confirms the merge:

1. fetch `origin/<P_BASE_BRANCH>` and verify it now contains the merged result according to GitHub;
2. identify each direct open child C whose base was `P_HEAD_BRANCH`;
3. rebase each child and then recursively restack its descendants.

### Rebase a direct child

For direct child C, preserve:

```text
C_HEAD_OLD = C's head SHA before rewrite
```

Then rebase only C's own commits, dropping P's now-merged commits:

```bash
git fetch origin
git checkout <C_HEAD_BRANCH>
git reset --hard origin/<C_HEAD_BRANCH>
git merge-base --is-ancestor <P_HEAD_OLD> <C_HEAD_BRANCH> || echo NOT_ANCESTOR
```

**Before rebasing, verify `P_HEAD_OLD` is actually an ancestor of C's current head.** If the check fails, `P_HEAD_BRANCH` was force-rewritten after C forked: stop and report the path as blocked instead of rebasing; restacking must resume from a proven old-parent boundary — the tip of the parent lineage C actually forked from, separating parent-owned commits from C's own, established from **independent evidence** (the parent head recorded when C was created, the parent PR's own timeline, commit-by-commit ownership) and confirmed by the same ancestor test — never from the recorded `P_HEAD_OLD`, and never from a mere merge-base with the rewritten parent, which can resolve to the integration-branch ancestor and replay the abandoned parent commits still in C's history as C's own (NOTES: what rebasing from a wrong boundary force-pushes into C's PR).

Only once ancestry is confirmed, proceed:

```bash
git rebase --onto origin/<P_BASE_BRANCH> <P_HEAD_OLD> <C_HEAD_BRANCH>
```

Equivalent isolated-worktree commands are preferred when other work is present.

This exact `rebase --onto new-base old-parent-head child` form is required (NOTES: why a plain retarget leaks P's commits into C after a squash merge).

If rebase conflicts:

- never guess through semantic conflicts;
- abort the rebase;
- leave the remote branch untouched;
- report the affected path as blocked;
- never merge any descendant of that child.

After a clean rebase:

```bash
git push --force-with-lease origin <C_HEAD_BRANCH>
```

Never use an unconditional `--force`.

Then update C's PR base from `P_HEAD_BRANCH` to `P_BASE_BRANCH` using GitHub MCP/API.

### Update `Depends on:` after parent merge

After retargeting C:

- if `P_BASE_BRANCH` is the head of another still-open parent PR, set C's line to that PR's full URL;
- otherwise remove C's `Depends on:` line entirely.

Preserve the rest of the PR body exactly.

### Recursively restack grandchildren

Rewriting C changes C's head SHA. Any child D based on C must be rebased from **C's old head** onto **C's new head**, while keeping its PR base branch as C's branch:

```bash
git checkout <D_HEAD_BRANCH>
git reset --hard origin/<D_HEAD_BRANCH>
git merge-base --is-ancestor <C_HEAD_OLD> <D_HEAD_BRANCH> || echo NOT_ANCESTOR
```

As with the direct-child rebase, confirm `C_HEAD_OLD` is actually an ancestor of D's current head before rebasing. If it is not, stop and treat that path as blocked rather than rebasing from an unproven boundary.

```bash
git rebase --onto <C_HEAD_NEW> <C_HEAD_OLD> <D_HEAD_BRANCH>
git push --force-with-lease origin <D_HEAD_BRANCH>
```

Its `Depends on:` URL remains C's PR URL because the logical parent PR has not changed.

Continue recursively through every descendant path — restacking only the direct child leaves grandchildren containing obsolete ancestor commits.

## Fanout example

Before:

```text
main
  -> A
      -> B
      -> C
```

After merging A:

```text
main
  -> B
  -> C
```

B and C are independently rebased with:

```text
--onto origin/main <old-A-head> B
--onto origin/main <old-A-head> C
```

Both PR bases become `main` and both lose `Depends on: A`.

## Linear stack example

Before:

```text
main -> A -> B -> C
```

After merging A:

```text
main -> B -> C
```

B is rebased from old A onto main. C is then rebased from old B onto new B. B's `Depends on: A` is removed; C continues to say `Depends on: B`.

If mode is `merge through B`, refresh B's checks after restacking, merge B, then rebase C from old B onto main and remove `Depends on: B`.

## Entire-stack mode

For `merge entire stack`:

1. discover the full reachable stack first;
2. snapshot its topology;
3. repeatedly choose currently root-most mergeable PRs;
4. merge one node;
5. fully restack its remaining descendant subtree;
6. refresh checks/mergeability for any PR that may be merged next;
7. continue until all requested nodes are merged or a blocker is reached.

A rebase can invalidate approvals or rerun CI. **Never merge the next PR on stale pre-rebase status** — refresh GitHub status after every rewrite and obey repository requirements.

## Partial-stack mode

For default `merge this PR`, first verify all stack ancestors are already merged / absent. If the supplied PR still targets an open parent PR, stop and explain that parent must be merged first; never silently expand scope.

For `merge through X`, ancestor merges are part of the explicit request. Merge only the ancestor chain through X. Restack everything above X but leave those descendants open.

## PR body metadata format

The canonical stack metadata line is exactly:

```text
Depends on: <full parent PR URL>
```

It belongs near the top of the PR body immediately after issue relationship lines such as `Closes:`, `Resolves:`, or `Part of:`.

There must be at most one `Depends on:` line because a Git branch has one direct base branch. Multiple issue dependencies belong in issue metadata, not in the PR stack-parent field.

## Failure and recovery

GitHub and remote branches are durable state. If the session dies mid-operation, rerunning this skill must first rediscover actual PR bases and remote head SHAs rather than assuming the previous step completed.

Before retrying a partially restacked branch:

- compare remote PR base/head with expected topology;
- check whether the old parent was already merged;
- inspect whether the branch was already force-pushed;
- avoid replaying the same rebase twice.

If state is ambiguous, stop rather than rewriting a branch twice.

## Output

Every authored forge write this skill makes — the merges themselves, and the retargeting and body edits on descendant PRs — follows the posting-identity rule stated once in `backlog-orchestrator` (*Posting identity*), using the map the caller passes rather than resolving an identity of its own. Read back the **first write of each kind** through each (transport, credential) pair — a merge, a base retarget, a body edit are distinct write kinds a platform may author differently, and one stack operation routinely performs several through the same pair — and report every observation alongside the result below, one entry per pair carrying each kind observed there; `unestablished` for a kind with no read-back write (NOTES: what reading back only a pair's first write loses).

Report:

- requested merge mode;
- PRs merged, in order;
- merge method used;
- branches rebased / force-with-lease pushed;
- PRs retargeted;
- posting identities observed, keyed by (transport, credential), per write kind observed through each pair;
- `Depends on:` metadata changed;
- remaining stack topology;
- CI/review blockers or rebase conflicts;
- whether the skill can be safely rerun to continue.
