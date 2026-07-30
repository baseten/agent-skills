---
name: create-pr
description: Create a GitHub pull request (draft for work repos, full for personal ones) following the current repo's branch naming, pre-PR checks, and issue-linking conventions, then trigger a Codex review. Use whenever the user asks to open/create a PR, or when the implement-issue skill reaches its PR step.
---

# Create a GitHub Pull Request

## Task

Create a pull request: $ARGUMENTS

Determine `owner/repo` from the current git remote (`git remote get-url origin`)
rather than assuming a fixed repo. Determine the default branch the same
way — repos vary between `main` and `master` (and occasionally something
else) — with `git remote show origin | sed -n '/HEAD branch/s/.*: //p'` (or
`gh repo view --json defaultBranchRef -q .defaultBranchRef.name` if `gh` is
available). Never hardcode `main`.

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

Try to determine the issue this PR closes **from the conversation context
only** — never guess from the branch name. This is usually already known:

- The user named an issue earlier in the conversation.
- This skill was invoked as the final step of `implement-issue`, which already
  has the issue URL in context.

The `Closes:` line below always needs the full issue URL, never a bare
number or identifier — a bare Linear identifier (`AGE-738`) renders as
plain, unclickable text, and a bare `#1234` only resolves correctly inside
the exact repo it's typed in. If you only have a number or identifier in
hand, resolve it to a URL first
(`https://github.com/<owner>/<repo>/issues/<n>` for GitHub; ask the user or
look it up via the Linear MCP tools for Linear) before writing the `Closes:`
line.

If no issue can be determined from context, ask the user for the issue URL.
If the user confirms there isn't one (e.g. a quick fix with no tracked
issue), proceed without a `Closes:` line — don't block PR creation on it.
For Linear-tracked work, the identifier leading the PR title (e.g.
`AGE-738 Support markdown in …`) is a separate convention Linear recognizes
on its own — keep using it if the repo does, but it doesn't substitute for a
linked `Closes:` line in the body.

## PR description template

If one or more issues were confirmed, the description must begin with one
`Closes:` line per issue, each the full URL:

```
Closes: <issue URL>
```

Never a bare `#N` or bare identifier — see "Linking the issue" above for why.
Follow with a short description of what changed and why (background,
approach, notable implementation details). If no issue was confirmed, start
straight with the description — omit the `Closes:` line entirely, don't leave
a placeholder. Mirror `.github/pull_request_template.md` if the repo has one.

## Creating the PR

Draft or full: **work-related repos get a draft; personal repos get a full
PR.** The repo's own docs decide, and they win where present — if
`CLAUDE.md`/`AGENTS.md` or the rules they point at say to open PRs as drafts,
open a draft. Where nothing is documented, open a full PR. An explicit
request from the user, or from a calling skill, overrides both.

In a remote/web session (no `gh` CLI access), use the GitHub MCP tools:

- Push the branch first: `git push -u origin <branch>`
- `mcp__github__create_pull_request` with the resolved `owner`/`repo`,
  `base: <default branch>`, `head: <branch>`, `draft` set per the rule above,
  `title`, and `body`

In a local session with `gh` CLI available:

```bash
git push -u origin <branch>
gh pr create --base <default-branch> --draft --title "Title" --body "Closes: <issue URL>

Description..."
```

(omit `--draft` for a full PR)

If invoked directly by the user, show the drafted title/description and
confirm before creating. If invoked as a chained step from `implement-issue`,
proceed without a separate confirmation — the user's request to implement the
issue already covers this step.

## Trigger the repo's PR review

Immediately after the PR is created, post a comment to trigger this repo's
automated review bot. Check `CLAUDE.md`/`AGENTS.md` for a documented
review-trigger convention (a bot-mention comment, a label, etc.) and use it.
If none is documented, default to `@codex review`.

```bash
gh pr comment <PR> --body "<trigger comment>"
```

(or the MCP equivalent, e.g. `mcp__github__add_issue_comment` on the PR
number) — do this every time a PR is created by this skill, no need to ask.

## Addressing review comments

This skill's job ends at PR creation. If review comments come in later —
whether the user asks you to address one now or you're monitoring the PR as
part of `implement-issue` step 6 — invoke the `resolve-pr-comment` skill for
each one rather than fixing it ad hoc. Don't hand-roll the fix/push/reply/
resolve flow here.

## Output

Return the PR URL and confirm the review-trigger comment was posted.
