---
name: ship-branch
description: Take work already committed to a branch that has no PR through the same supervised path implement-issue gives a tracked issue — open the PR with create-pr, supervise it through CI and review with bounded repairs, settle, and merge where the repository opted into auto-merge. For work implemented from a Slack thread, prose, or an issue outside an orchestrated run. A thin entry point to implement-issue's *Phase 1, from an existing branch*; it holds no rule of its own. Use when asked to ship, supervise or "put through the PR process" a branch that has no PR yet.
---

# Ship a branch

Invoke `implement-issue` with the current branch as its **existing branch**, and the issue URL or brief the user gave. Its *Phase 1, from an existing branch* holds every rule this run follows — the preflight, the PR, supervision, settle, the merge gate and the result. This file adds none, and reading any of them here instead of there is how a copy starts to drift.

## Inputs

Pass `implement-issue`, as values:

- **existing branch**: the branch named, otherwise the current one;
- **base**: the one the user named, otherwise none — `implement-issue` takes the default branch;
- **source**: the issue URL, or the brief verbatim — a Slack permalink, or the user's prose — with whether the user said there is no issue;
- any narrowing the user stated — `auto-merge` off, a draft preference.

`implement-issue` unavailable → stop, naming it. Never run its phases from memory.

## Boundaries

- A branch that already has an open PR is refused by that entry's preflight, not adopted. To supervise an existing PR, use `supervise-prs` directly.
- Return `implement-issue`'s structured result unchanged.
