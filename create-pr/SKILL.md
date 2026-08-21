---
name: create-pr
description: Create a GitHub pull request following repo conventions and any explicit base branch supplied by an orchestrator. Links the PR canonically to the tracked implementation issue (GitHub or Linear), records direct stack parent metadata when applicable, and triggers automated review.
---

# Create a GitHub Pull Request

## Task

Create a pull request: $ARGUMENTS

Determine `owner/repo` from the current git remote. Determine the default branch from repository metadata rather than hardcoding `main`.

## PR base branch

If the user/calling skill supplies an explicit base, it takes precedence over the repository default. Validate it exists in the same repository. Otherwise use the discovered default branch. Call it `<pr-base>`.

## Detect a stacked parent PR

A non-default base is not automatically a stack parent.

1. If a parent PR URL was supplied, verify its head branch equals `<pr-base>`.
2. Otherwise search open PRs in the same repo whose head branch equals `<pr-base>`.
3. Exactly one match => `<parent-pr>`.
4. No match => ordinary integration/base branch; no stack metadata.
5. Ambiguous match => stop rather than guessing.

Cross-repository issue dependencies are never Git stack parent relationships.

## Before creating the PR

Read `CLAUDE.md`/`AGENTS.md` for checks, branch conventions, PR template, draft/full behavior, and issue-linking rules. Run required checks first.

## Canonical tracked-issue identity

Every implementation PR must be linked to the **exact tracked issue** using its canonical full URL. Never rely only on an ambiguous bare `#123` or `ABC-123` in reporting/context.

Determine tracker from the canonical issue URL.

### GitHub issue

For `https://github.com/<owner>/<repo>/issues/<n>`, use a GitHub closing keyword plus the full URL, e.g.:

```text
Closes: https://github.com/acme/repo/issues/123
```

`Fixes:`/`Resolves:` are acceptable when repo convention prefers them. The relationship must be valid for GitHub auto-close when the implementation PR ultimately merges to the closing branch/default branch.

### Linear issue

For `https://linear.app/.../issue/TEAM-123/...`, preserve the **full Linear URL** and also include the Linear issue ID in a linking/closing magic-word form understood by the Linear GitHub integration. Prefer repository/team convention; otherwise use:

```text
Fixes TEAM-123 — https://linear.app/<workspace>/issue/TEAM-123/<slug>
```

The full URL is canonical identity; the issue ID is included because Linear's GitHub integration uses IDs in PR titles/branches or magic-word references to link PRs and drive configured status automation. Do not reduce the relationship to only `TEAM-123`.

If the repo convention puts the Linear ID in the PR title or branch, preserve that too, but still include the full Linear URL in the body.

Linear completion semantics are controlled by the workspace/team GitHub integration and workflow automation; do not pretend GitHub itself closes a Linear issue.

### Other trackers

If another tracker is supplied, preserve its full canonical issue URL and follow documented repository/tracker integration conventions. If no reliable linkage rule exists, stop rather than inventing one.

If a directly invoked ad-hoc PR genuinely has no tracked issue, proceed only after the user confirms that exception. Chained implementation PRs must always have an exact issue URL.

## PR description layout

Put tracked-issue relationship line(s) first. Immediately after them, if `<parent-pr>` exists, add:

```text
Depends on: <full parent PR URL>
```

Then a blank line and the normal description/template.

Examples:

```text
Closes: https://github.com/acme/repo/issues/123
Depends on: https://github.com/acme/repo/pull/456

Description...
```

```text
Fixes TEAM-123 — https://linear.app/acme/issue/TEAM-123/example
Depends on: https://github.com/acme/repo/pull/456

Description...
```

`Depends on:` means only the direct Git stack parent PR, never arbitrary issue dependencies.

## Create the PR

Follow repo draft/full rules. Push the branch, then create the PR with explicit `base: <pr-base>` and `head: <branch>` using authenticated `gh` or GitHub MCP depending on environment.

If invoked directly, show title/body before creation when confirmation is normally required. If chained from `implement-issue`, the original implementation request authorizes PR creation.

## Verify after creation

Fetch the PR and verify:

1. head/base are correct;
2. full canonical issue URL is present;
3. tracker-specific link/closing syntax is present;
4. `Depends on:` is correct when stacked and absent when not stacked.

For GitHub issues, verify the closing keyword relationship is syntactically correct. For Linear, verify the full URL plus issue ID/magic-word relationship is present; actual status transition happens through configured Linear integration automation.

## Trigger review

Immediately trigger the repository's documented automated review convention. If none exists, default to `@codex review`, using `gh` or the GitHub MCP equivalent.

## Review comments

Later review fixes must use `resolve-pr-comment` rather than hand-rolling the workflow.

## Output

Return PR URL, canonical issue URL, tracker type, base branch, parent PR URL when stacked, and confirmation that issue linkage + review trigger were verified.
