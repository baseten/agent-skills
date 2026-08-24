---
name: create-pr
description: Create a GitHub pull request following repo conventions and any explicit base branch supplied by an orchestrator. Ensures tracker-specific implementation linkage, records direct stacked parent PRs with `Depends on:`, verifies the created PR, and triggers the repository's automated review convention when requested by the calling workflow.
---

# Create a GitHub Pull Request

## Task

Create a pull request: $ARGUMENTS

Determine `owner/repo` from the current git remote. Determine the default branch from the repository rather than hardcoding `main`.

## PR base branch

If the user or calling skill supplies a required PR base branch, **that base takes precedence over the repository default branch**. Validate it exists in the same repository. If it does not, stop rather than falling back.

If no explicit base is supplied, use the repository default branch. Call the resulting branch `<pr-base>`.

## Detect a stacked-PR parent

A non-default base is not automatically a stack parent because repositories may have long-lived integration branches.

Use this precedence:

1. If the caller supplies a parent PR URL, fetch it and verify its head branch is exactly `<pr-base>`.
2. Otherwise search open PRs in the same repository for a PR whose head branch is exactly `<pr-base>`.
3. If exactly one exists, it is `<parent-pr>`.
4. If none exists, treat `<pr-base>` as an ordinary integration base and do not add stack metadata.
5. If ambiguous, stop rather than writing incorrect metadata.

A parent PR must be in the same repository. Cross-repository dependencies are scheduler/tracker relationships, never Git stack parents.

## Before creating the PR

Read `CLAUDE.md`/`AGENTS.md` for pre-PR checks, branch conventions, PR templates, draft/full rules, tracker linkage, and review-trigger conventions. Run required checks before opening the PR unless the caller explicitly documents that final verification was already completed by `implement-issue-core`.

## Branch naming

Follow documented repo convention. Otherwise preserve the current branch; do not invent a convention.

# Tracker-specific issue linkage

Every implementation PR must be unambiguously linked to the exact canonical issue URL it implements.

Determine tracker from the full canonical issue URL.

## GitHub Issues

Use a GitHub-recognized closing keyword with the **full canonical issue URL**, for example:

```text
Closes: https://github.com/acme/repo/issues/123
```

`Fixes:` or `Resolves:` are acceptable when repo convention requires them. `Part of:` alone is insufficient when the implementation issue should auto-close on merge.

## Linear

Preserve the **full Linear issue URL** near the top of the PR body and follow the repository/workspace's documented Linear↔GitHub linking convention. Where the integration recognizes the Linear identifier in the PR title/body, preserve that identifier as well.

Do not invent GitHub `Closes:` semantics for a Linear issue. Linear completion/status automation is workspace-specific.

## Other trackers

Follow documented integration semantics. If no reliable linking convention exists, retain the full canonical issue URL and report that automatic status transition cannot be guaranteed.

If an implementation PR cannot be linked to an exact issue, stop rather than creating an orphan PR. Directly-invoked ad-hoc PRs with no tracked issue are the exception only after the user confirms there is no issue.

## A PR shipping against a coverage finding links but does not close

A closing keyword is a claim that merging this PR completes the issue, and GitHub acts on that claim whether or not it is true. So when the caller reports a **coverage finding** — a declared dependency satisfied on paper, closed and merged, whose capability is absent from the code, leaving acceptance criteria shipped stubbed, disabled, or omitted — a closing keyword auto-closes an issue nobody finished. The tracker then reads as complete over work that was never done, and the gap survives only in a PR body nobody re-reads.

For that PR, link without closing:

```text
Part of: https://github.com/acme/repo/issues/123
Blocked by: https://github.com/acme/repo/issues/131
```

`Part of:` instead of `Closes:`/`Fixes:`/`Resolves:`, `Blocked by:` naming the prerequisite issue the finding produced, and a body section stating which acceptance criteria are unmet and why. The issue stays **open** and carries the link to its prerequisite; closing it is a human decision once the gap is filled, not a side effect of this merge. Half-finished work must not reach a terminal state by default.

This is exactly the case the general rule above calls insufficient — "`Part of:` alone is insufficient when the implementation issue should auto-close on merge" — and it is the same test read the other way: this issue **should not** auto-close, because it is not finished. Report which form you emitted, so the caller can reconcile completion against it rather than assuming a close.

On Linear and other trackers the same rule holds through a different mechanism: keep the canonical issue URL, and do not apply the workspace's completion/status automation to a PR carrying a coverage finding. Where you cannot tell whether the integration will transition the issue on merge, say so rather than assuming it will not.

Scope this narrowly. It applies to a PR carrying a **recorded** coverage finding, not to any PR whose author feels uncertain. A PR that implements its issue closes it exactly as above.

# PR description template

Put tracker relationship line(s) first. Immediately after them, if `<parent-pr>` exists, add exactly one:

```text
Depends on: <full parent PR URL>
```

Then a blank line and normal description/template.

GitHub example:

```text
Closes: https://github.com/acme/repo/issues/123
Depends on: https://github.com/acme/repo/pull/456

Description...
```

Linear example:

```text
Issue: https://linear.app/acme/issue/FEP-195/example
Depends on: https://github.com/acme/repo/pull/456

Description...
```

`Depends on:` always means the direct Git stack parent PR, not tracker issue dependencies.

# Creating and verifying the PR

Draft/full behavior follows repo docs; otherwise work repos default to draft and personal repos to full. Explicit caller/user preference wins.

Report the as-created draft state in the output. A supervising workflow uses it to decide later whether the PR is eligible to be promoted to ready once its first review round comes back clean; it cannot tell a PR this run drafted from one a human drafted unless this skill says so. This skill itself never promotes — it ends at creation.

Use GitHub MCP in remote/web environments and `gh pr create --base <pr-base>` locally when available.

When directly invoked by a user, show proposed title/body and confirm before creation. When chained from an authorized implementation workflow, no second confirmation is needed.

After creation fetch/read the PR and verify:

1. head/base are correct;
2. canonical tracker issue linkage is present exactly as intended, **in the intended form** — a closing keyword only where the issue is fully implemented, `Part of:` plus `Blocked by:` where a coverage finding was reported. A PR that links correctly but closes an issue it only partly implements passes a linkage check and still ends the issue's life;
3. `Depends on:` is correct when stacked and absent when not stacked.

Do not report success before verification.

# Automated review trigger

By default, implementation workflows (`implement-issue-core`, `implement-issue`, `backlog-orchestrator`) expect this skill to trigger the repository's documented automated review after the PR is created and final implementation state has been pushed.

Use the repo's documented trigger. If none exists, default to `@codex review` where that convention is supported.

A caller may explicitly request **deferred review trigger** (for example an intentionally early WIP draft PR). In that case create/verify the PR but do not trigger review until the caller later requests it.

Do not repeatedly trigger review merely because subsequent CI checks run. Re-trigger after a substantive review-fix round only when repo convention requires it.

## Substantive vs mechanical pushes

Re-trigger review after a **substantive** push. Do not re-trigger after a **mechanical** one.

A push is mechanical when it changes identity, location or formatting and nothing else:

- a restack or rebase onto a new base, whose conflict resolutions reproduce the original intent of both sides rather than picking between them;
- renumbering or regenerating a claimed artifact — a migration number and its index entry, a lockfile, a generated manifest or client — where the content is unchanged apart from the identity or ordering that had to move;
- formatter-only output.

Everything else is substantive. That includes a conflict resolution that had to choose between two behaviors, and a regeneration whose output differs beyond identity or ordering. When you cannot tell which one you are looking at, treat it as substantive.

A mechanical push still has to pass the repository's deterministic checks — those, not another review round, are what validate it. If the repository has no check that would catch a bad renumber or a dropped hunk, the push is not mechanical for this purpose and needs review like any other.

This governs what the workflow itself triggers, not what the review provider does on its own. A provider may re-review off its own events — marking a draft ready, for example. That is outside this skill's control, and is neither a reason to suppress a trigger that is due nor to issue one that is not.

# Addressing later review comments

This skill ends after PR creation/verification/review trigger. Later review fixes belong to `repair-pr` / `resolve-pr-comment`, with long-lived event supervision owned by whichever orchestrator invoked them.

# Output

Return:

- PR URL;
- canonical issue URL + tracker;
- PR base branch;
- parent PR URL when stacked;
- issue linkage verified: yes/no;
- draft state as created: draft/ready, and what decided it (repo docs, caller preference, default);
- review triggered/deferred and how.
