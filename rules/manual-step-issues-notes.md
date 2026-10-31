# Notes — manual-step-issues

Reasoning for `rules/manual-step-issues.md`. Deliberately *not* bundled into
each skill: the audience is a person editing the rule, who has this checkout.

## Every owner step is an issue

**Why an issue, and why a shared rule (2026-10-31):** owner steps — post-deploy
checks, keys, backfills, console actions — were surfacing in PR bodies, wrap-up
comments and chat, where nothing tracked whether they had been done and the next
session could not find them. The owner asked for every one to be filed as a
`[Manual]` issue under the repository's manual-steps epic (crypto-scanner's is
#1584). Two skills produce these issues (`conductor`, `backlog-orchestrator`) and
one consumes them (`owner-steps`), so the form is stated once here rather than
three times; a producer that drifted from the consumer's expectations would file
issues `owner-steps` cannot walk.

**Why one issue per sitting:** `owner-steps` walks one issue at a time with the
owner at a server; an issue that mixes a root console step with a later check
that waits on a deploy cannot be finished in one session, and its *Done when*
never reads true at the end of one.

## The form

**Why the dependency warning:** `validate-backlog` and
`normalize-github-dependencies` read `blocked by` statements in issue text, and
the normalizer promotes them into native edges. That is wanted here — a backfill
really does block the issue that needs its data — but it means a loosely written
header manufactures real blockers. `Not for an orchestrator` keeps the issue out
of dispatch while still letting its edges hold the work that waits on it.

## Never a secret

**Why the paste-back is specified:** the owner is pasting server output into a
session that records it on GitHub. Saying in advance which output proves a step
without exposing a value is what keeps a paste from carrying one.
