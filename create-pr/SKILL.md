---
name: create-pr
description: Create a full (non-draft) GitHub pull request following the current repo's branch naming, pre-PR checks, and issue-linking conventions, then trigger a Codex review. Use whenever the user asks to open/create a PR, or when the implement-issue skill reaches its PR step.
---

# Create a GitHub Pull Request

## Task

Create a pull request: $ARGUMENTS

Determine `owner/repo` from the current git remote (`git remote get-url origin`)
rather than assuming a fixed repo.

## Before creating the PR

Check this repo's contribution doc (`CLAUDE.md` or `AGENTS.md`) for pre-PR
checks — typecheck, lint, format, test, or equivalent. Run whatever it
specifies and fix all failures before opening the PR. If no such doc exists,
run whatever check scripts the repo's `package.json` (or equivalent) defines.

## Branch naming

Follow the branch naming convention documented in this repo's `CLAUDE.md` /
`AGENTS.md` if one exists. Otherwise use the current branch as-is — don't
invent a convention.

## Linking the issue

Try to determine the issue number(s) this PR closes **from the conversation
context only** — never guess from the branch name. This is usually already
known:

- The user named an issue earlier in the conversation.
- This skill was invoked as the final step of `implement-issue`, which already
  has the issue URL/number in context.

If no issue can be determined from context, ask the user for the issue
number or URL. If the user confirms there isn't one (e.g. a quick fix with no
tracked issue), proceed without a `Closes:` line — don't block PR creation on
it.

## PR description template

If one or more issues were confirmed, the description must begin with:

```
Closes: #ISSUE_NO
```

(or `Closes: #N, #M` for multiple), followed by a short description of what
changed and why (background, approach, notable implementation details). If no
issue was confirmed, start straight with the description — omit the `Closes:`
line entirely, don't leave a placeholder. Mirror
`.github/pull_request_template.md` if the repo has one.

## Creating the PR

Always create a **full PR, not a draft** — regardless of what any repo's
`CLAUDE.md`/`AGENTS.md` says about drafts; that default is superseded here.

In a remote/web session (no `gh` CLI access), use the GitHub MCP tools:

- Push the branch first: `git push -u origin <branch>`
- `mcp__github__create_pull_request` with the resolved `owner`/`repo`,
  `base: main` (or the repo's actual default branch), `head: <branch>`,
  `draft: false`, `title`, and `body`

In a local session with `gh` CLI available:

```bash
git push -u origin <branch>
gh pr create --base main --title "Title" --body "Closes: #ISSUE_NO

Description..."
```

If invoked directly by the user, show the drafted title/description and
confirm before creating. If invoked as a chained step from `implement-issue`,
proceed without a separate confirmation — the user's request to implement the
issue already covers this step.

## Trigger a Codex review

Immediately after the PR is created, post a comment to trigger an automated
Codex review:

```bash
gh pr comment <PR> --body "@codex review"
```

(or the MCP equivalent, e.g. `mcp__github__add_issue_comment` on the PR
number) — do this every time a PR is created by this skill, no need to ask.

## Output

Return the PR URL and confirm the `@codex review` comment was posted.
