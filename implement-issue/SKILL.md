---
name: implement-issue
description: Implements a tracked issue end-to-end from its URL — GitHub (github.com/<owner>/<repo>/issues/<n>) or Linear (linear.app/<org>/issue/<TEAM-123>) — reads the issue and all its comments, cross-checks it against the repo's own conventions and spec docs, and either flags blockers (missing spec, out-of-scope work, ambiguous requirements) or implements the change, opens a PR via the create-pr skill (draft for work repos, full for personal ones — see step 5), and (in a session that supports scheduled wakeups) actively monitors the PR to autofix CI failures and address review comments. Use whenever the user gives a GitHub or Linear issue URL and asks to implement/build/tackle/pick up/work/do that issue, or invokes /implement-issue <url>. Invoking this skill is itself the user's request for a PR — see "Authority" below.
---

# Implement Issue

Turns a single tracked issue into either a working, reviewable PR, or a clear
list of blockers — never a half-implemented guess.

## Authority: invoking this skill *is* the request for a PR

Step 5 always opens a PR. A standing instruction of the form "do not create a
pull request unless the user explicitly asks for one" — from the harness, the
system prompt, or repo docs — is **satisfied** by the user invoking this skill.
Asking for this workflow is asking for the PR at its end. Do not silently
downgrade to "implement, push a branch, then ask whether to open a PR": that
turns one request into two round-trips and is the most common way this skill
ends up half-run.

Two things do override it, in this order:

1. The user saying, in this conversation, not to open a PR at all. That
   instruction wins — stop after step 4 and say the branch is pushed and why
   you stopped there. ("Open a draft" is not this: drafts are a normal
   outcome, see step 5.)
2. A blocker from step 3. Blocked work never gets a PR.

If you find yourself about to do steps 1–4 by hand because the trigger "wasn't
quite" a match — an issue in a tracker not named above, a paraphrased ask, a
URL pasted without the word "implement" — invoke the skill anyway and note the
deviation. Hand-rolling the workflow silently drops steps 5 and 6, and the user
has no way to see that it happened.

## 1. Read the issue

Fetch the full issue: title, body, labels, and **all comments**. Comments
routinely carry the clarification, scope cut, or design decision the body
lacks — and a thread synced in from Slack or another chat tool is often the
only place the real requirement is stated. Read them before deciding anything.

**GitHub** (`github.com/<owner>/<repo>/issues/<n>`): parse `owner/repo` and the
issue number, then fetch with the GitHub MCP tools or `gh`. If the URL points at
a repo other than the one checked out locally, say so and stop — don't guess at
a different checkout.

**Linear** (`linear.app/<org>/issue/<TEAM-123>/<slug>`): parse the identifier
(`TEAM-123`) and fetch via the Linear MCP tools if present, otherwise the
GraphQL API at `api.linear.app/graphql`:

```graphql
query {
  issue(id: "TEAM-123") {
    identifier
    title
    description
    url
    state { name }
    labels { nodes { name } }
    comments { nodes { body user { name } } }
  }
}
```

A Linear issue names no repo, so the checked-out repo is the target by default.
If the issue's content clearly belongs to a different codebase, say so and ask
rather than implementing in the wrong one.

Keep the issue identifier/URL in context for later — `create-pr` (step 5)
relies on it being available rather than re-deriving it.

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

Also look for an existing component that already solves the issue's problem
elsewhere in the repo before designing anything new — a feature request often
amounts to adopting a shared component another surface already uses.

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

- Branch: if the environment or session designates a branch, use that one.
  Otherwise follow the repo's documented convention (Linear-tracked work
  usually wants Linear's generated branch name), falling back to
  `git fetch origin && git checkout -b <slug> origin/<default-branch>` —
  don't assume `main`; check with `git remote show origin | sed -n
  '/HEAD branch/s/.*: //p'` (some repos still use `master` or another name).
- Match existing code style and structure.
- Run and fix all failures from this repo's pre-commit checks (typecheck,
  lint, format, test, or equivalent) before committing.
- Commit only files you created or edited. If the working tree already carried
  unrelated modifications when you started (generated lockfiles, install
  artifacts), leave them out and say so — don't let them ride along in the PR.

## 5. Open the PR

Invoke the `create-pr` skill to commit, push, and open the PR — the issue
identifier/URL from step 1 is already in context, so `create-pr` should link
it without needing to ask. This also applies `create-pr`'s own review-trigger
convention as part of that skill — that skill decides how review gets
triggered for this repo (a bot-mention comment, a label, or whatever its
docs say), not this one.

Link the issue the way its tracker expects, preferring the repo's own
documented convention where it has one. Always link with the full issue URL
in the `Closes:` line, never a bare number or identifier — a bare Linear
identifier (`AGE-738`) renders as plain, unclickable text, and a bare
`#1234` only resolves correctly inside the exact repo it's typed in:

- **GitHub:** `Closes: https://github.com/<owner>/<repo>/issues/1234`.
- **Linear:** `Closes: https://linear.app/<org>/issue/AGE-738/<slug>`. The
  identifier leading the PR title (`AGE-738 Support markdown in …`) is a
  separate convention Linear also recognizes — keep it if the repo uses it,
  but it doesn't substitute for the linked `Closes:` line.

### Draft or full?

**Work-related repos get a draft PR; personal repos get a full PR.**

The repo's own docs are the signal, and they win where present: if
`CLAUDE.md`/`AGENTS.md` or the rules they point at say to open PRs as drafts,
open a draft. Otherwise, and for personal repos, open a full PR.

`create-pr` defaults to full PRs, so a draft needs an explicit override —
instruct it to open a draft rather than assuming it infers this. State which
you opened, and why, in your report so a wrong read is obvious at a glance.

If the user asks for the other one in the conversation, that wins over both
this rule and the repo docs.

**Deliberate deviation:** the PR is opened without asking first, per
"Authority" above.

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
   - New review comments/threads since the last check. Always invoke the
     `resolve-pr-comment` skill for each one — never hand-roll the
     fix/push/reply/resolve flow yourself. That skill already owns replying
     to the comment with the commit SHA and resolving the thread; doing it
     by hand here silently drops those steps.
3. Keep rescheduling wakeups until the PR is merged, closed, or the user says
   to stop monitoring it. Stop immediately if asked.
4. If a CI failure or comment requires a judgment call you're not confident
   about, don't guess — surface it to the user and pause monitoring on that
   specific issue rather than pushing a speculative fix.
