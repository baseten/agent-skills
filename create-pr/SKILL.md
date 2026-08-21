---
name: create-pr
description: Create a GitHub pull request following repo conventions and any explicit base branch supplied by an orchestrator. For stacked PRs, automatically records the direct parent PR with a `Depends on:` line. Use whenever asked to create a PR or when implement-issue reaches its PR step.
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

## Linking the issue

Determine the issue from conversation/calling-skill context, not the branch name. Use the repository/tracker's documented relationship convention such as `Closes:`, `Resolves:`, or `Part of:` and use full issue URLs where bare identifiers would be ambiguous.

If no issue can be determined, ask when this skill was directly invoked. When chained from `implement-issue`, the issue URL should already be in context.

## PR description template

Put issue relationship line(s) first. Immediately after them, if `<parent-pr>` exists, add exactly one canonical stack line:

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

## Trigger review

Immediately trigger the repository's documented automated review convention. If none exists, default to `@codex review`, using `gh` locally or the GitHub MCP equivalent remotely.

## Addressing review comments

If comments arrive later, invoke `resolve-pr-comment` rather than hand-rolling the fix/push/reply/resolve flow.

## Output

Return the PR URL, PR base branch, parent PR URL when stacked, and confirm the review trigger was performed.
