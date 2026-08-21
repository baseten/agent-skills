---
name: create-pr
description: Create a GitHub pull request following repo conventions and any explicit base branch supplied by an orchestrator. Ensures the PR is canonically linked to its implementation issue so merging auto-closes that issue, and for stacked PRs records the direct parent PR with a `Depends on:` line. Use whenever asked to create a PR or when implement-issue reaches its PR step.
---

# Create a GitHub Pull Request

## Task

Create a pull request: $ARGUMENTS

Determine `owner/repo` from the current git remote. Determine the default branch from the repository rather than hardcoding `main`.

## PR base branch

If the user or a calling skill explicitly supplies a required PR base branch, **that base takes precedence over the repository default branch**. Validate it exists in the same repository. If it does not, stop rather than falling back.

If no explicit base is supplied, use the repository default branch. Call the resulting branch `<pr-base>`.

## Detect a stacked-PR parent

A non-default base is not automatically a stack parent because repositories may have long-lived integration branches.

Use this precedence:

1. If the user/calling skill supplies a parent PR URL, fetch it and verify its head branch is exactly `<pr-base>`.
2. Otherwise search open PRs in the same repository for a PR whose head branch is exactly `<pr-base>`.
3. If exactly one exists, it is `<parent-pr>`.
4. If none exists, treat `<pr-base>` as an ordinary base/integration branch and do not add stack metadata.
5. If the relationship is ambiguous, stop rather than writing incorrect metadata.

A parent PR must be in the same repository. Cross-repository dependencies are DAG/issue dependencies, not Git stack parents.

## Before creating the PR

Read `CLAUDE.md` or `AGENTS.md` for pre-PR checks, branch conventions, PR templates, and draft/full rules. Run and fix required checks before opening the PR. If no contribution doc exists, run the repository's normal check scripts.

## Branch naming

Follow the repository's documented branch convention. Otherwise preserve the current branch; do not invent a convention.

## Canonical issue linkage and auto-close invariant

Every implementation PR must be unambiguously linked to the exact issue it implements.

For GitHub issues, use a GitHub closing keyword with the **full canonical issue URL**, for example:

```text
Closes: https://github.com/acme/repo/issues/123
```

`Fixes:` or `Resolves:` are also acceptable when repository convention requires them, but the chosen syntax must be one that GitHub recognizes for automatic issue closure when the PR is merged into the repository's default branch.

Do not use `Part of:` as the sole relationship for an implementation issue that should auto-close; it is descriptive only and does not satisfy this invariant.

Determine the issue from conversation/calling-skill context, never from a guessed branch name. When chained from `implement-issue` or `backlog-orchestrator`, the canonical implementation issue URL must already be supplied.

If an implementation PR cannot be linked to an exact issue, stop rather than creating an orphan PR. Directly-invoked ad-hoc PRs with no tracked implementation issue are the only exception, and only after the user confirms there is no issue to close.

### Stacked PR caveat

A stacked child PR can target a non-default parent branch. Keep its canonical `Closes:` line on the PR anyway so the issue relationship is durable and remains correct when the PR is later retargeted/restacked to the default branch before merge.

Before any merge workflow treats an issue as complete, verify the merged PR contained the correct closing relationship and that the GitHub issue is closed after merge. If GitHub did not auto-close it because of unusual repository/base behavior, explicitly close the issue only after confirming the PR that implements it has merged.

## PR description template

Put canonical issue relationship line(s) first. Immediately after them, if `<parent-pr>` exists, add exactly one canonical stack line:

```text
Depends on: <full parent PR URL>
```

Then add a blank line and the normal description.

Example:

```text
Closes: https://github.com/acme/repo/issues/123
Depends on: https://github.com/acme/repo/pull/456

Description...
```

Rules:

- `Depends on:` means the **direct Git stack parent PR**, not every issue dependency.
- There is at most one `Depends on:` line because a Git branch has one direct base branch.
- Always use the full canonical parent PR URL.
- Do not add the line when `<pr-base>` is merely an integration branch with no open PR owning it.
- Preserve the repository PR template while keeping relationship lines at the top.

## Creating the PR

Draft/full behavior follows repository docs; otherwise work repos default to draft and personal repos to full. Explicit user/caller instruction wins.

In a remote/web session, push with git and create the PR with GitHub MCP using `base: <pr-base>` and `head: <branch>`.

Locally, use the equivalent `gh pr create --base <pr-base>` flow when `gh` is available.

If invoked directly by the user, show the proposed title/body and confirm before creating. If chained from `implement-issue`, proceed without a second confirmation.

After creation, fetch/read the resulting PR and verify:

1. the head/base are correct;
2. the canonical implementation issue closing line is present exactly as intended;
3. `Depends on:` is present when stacked and absent when not stacked.

Do not report success until those relationships are verified.

## Trigger review

Immediately trigger the repository's documented automated review convention. If none exists, default to `@codex review`, using `gh` locally or the GitHub MCP equivalent remotely.

## Addressing review comments

If comments arrive later, invoke `resolve-pr-comment` rather than hand-rolling the fix/push/reply/resolve flow.

## Output

Return the PR URL, implementation issue URL, PR base branch, parent PR URL when stacked, and confirm both canonical issue linkage and review trigger were verified.
