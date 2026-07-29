---
name: implement-issue
description: Implements a GitHub issue end-to-end from its URL — reads the issue, cross-checks it against the repo's own conventions and spec docs, and either flags blockers (missing spec, out-of-scope work, ambiguous requirements) or implements the change, opens a full PR via the create-pr skill, and (in a session that supports scheduled wakeups) actively monitors the PR to autofix CI failures and address review comments. Use whenever the user gives a GitHub issue URL and asks to implement/build/tackle/pick up/work that issue, or invokes /implement-issue <url>.
---

# Implement Issue

Turns a single GitHub issue into either a working, reviewable PR, or a clear
list of blockers — never a half-implemented guess.

## 1. Read the issue

Parse the issue URL for `owner/repo` and issue number, then fetch the full
issue: title, body, labels, and comments (comments often carry clarifications
or scope changes made after the issue was filed). Use whatever GitHub tooling
is available in this environment (GitHub MCP tools or `gh`).

If the URL points at a repo other than the one checked out locally, say so
and stop — don't guess at a different checkout.

Keep the issue number/URL in context for later — `create-pr` (step 5) relies
on it being available rather than re-deriving it.

## 2. Read the repo's conventions and specs

Read this repo's contribution doc (`CLAUDE.md` or `AGENTS.md`) for coding
conventions, branch naming, and pre-PR checks.

Explicitly check whether a `docs/` directory (or similar spec/design-doc
location) exists — e.g. `ls docs/` — rather than assuming based on what
`CLAUDE.md`/`AGENTS.md` happens to mention; doc directories grow past what
any table lists. State plainly whether it exists.

If it exists, check whether it documents an ownership split (e.g. frontend
vs backend, service boundaries) — that split is often the biggest source of
blockers, so check it early if present. Then read whichever spec docs
actually cover the issue's area, in full — not just skimmed headers.
Skimming produces implementations that silently contradict the spec.

If the repo has no `docs/` directory or equivalent, say so and rely on the
issue body, existing code conventions, and comments for scope.

## 3. Decide: blocked, or clear to implement?

Flag it as a blocker (and stop — do not write code, do not open a PR) if any
of these are true:

- **Out-of-repo work.** The issue asks for behaviour that belongs to another
  service/repo per the documented ownership split (new contracts, schemas,
  logic owned elsewhere), and the required surface doesn't already exist in
  this repo (generated client, schema file, etc.). This repo can't invent
  another service's contracts — implementing against a guessed shape creates
  drift.
- **No spec covers it.** The issue describes behaviour that isn't documented
  anywhere, and the issue body itself doesn't fully pin down the behaviour
  (states, edge cases). Guessing here is how scope drifts from what the user
  actually wants.
- **Contradicts an existing spec.** The issue asks for something that
  conflicts with a documented design, and it's not clear whether the issue is
  intentionally superseding the doc or just out of date with it.
- **Depends on unfinished work.** The issue references another issue/PR,
  endpoint, or component that doesn't exist yet in the codebase.

When blocked, report back concretely: quote the exact doc section (or note
the total absence of one) that's missing, contradictory, or out-of-scope, and
ask the specific question(s) that would unblock it. Don't open a PR or push a
branch for blocked work — a stub PR just adds noise.

If none of the above apply, proceed.

## 4. Implement

Follow this repo's conventions from step 2:

- Branch per the repo's documented convention (or `git fetch origin && git
  checkout -b <slug> origin/main` if none is documented).
- Match existing code style and structure.
- Run and fix all failures from this repo's pre-commit checks (typecheck,
  lint, format, test, or equivalent) before committing.

## 5. Open the PR

Invoke the `create-pr` skill to commit, push, and open the PR — the issue
number/URL from step 1 is already in context, so `create-pr` should link it
without needing to ask. This also triggers the Codex review comment as part
of that skill.

**Deliberate deviation:** this always results in a full PR, never a draft —
`create-pr` already defaults to full PRs, so no override is needed here.

## 6. Monitor the PR for CI failures and review comments

This step only applies in a session that supports scheduling follow-up work
(e.g. via a wakeup/loop mechanism). If this environment can't schedule
follow-up turns, skip this step and tell the user the PR is open but won't be
auto-monitored — they'll need to ask again later to check on it.

Where supported:

1. Schedule a wakeup (roughly every 10–20 minutes) to check on the PR.
2. On each wakeup, check:
   - CI status (`gh pr checks <PR>` or MCP equivalent). If a check failed,
     investigate the failure and push a fix directly (small, targeted commit
     addressing the failure — same discipline as step 4).
   - New review comments/threads since the last check. For each, invoke the
     `resolve-pr-comment` skill to address it.
3. Keep rescheduling wakeups until the PR is merged, closed, or the user says
   to stop monitoring it. Stop immediately if asked.
4. If a CI failure or comment requires a judgment call you're not confident
   about, don't guess — surface it to the user and pause monitoring on that
   specific issue rather than pushing a speculative fix.
