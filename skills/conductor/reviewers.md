# conductor — reviewers

Part of `conductor`'s contract, read when the owner asks this session for reviews
and wherever a sweep meets a reviewer. `SKILL.md` points here from its opening,
*When this is the wrong tool*, *Rules*, *1. Sweep*, *The fallback check-in*, *4.
Owner pass*, *6. Dispatch*, *7. Ledger* and *Report*, and its rules assume
`SKILL.md` has been read. The reasoning is in `NOTES.md`, under *Reviewers*.

A **reviewer** drafts the owner's review of a PR someone else opened, as
`review-pr` says, for the owner to submit. **This skill hard-codes `review-pr`**;
a skill extending it takes over through `review-pr`'s own hand-off. No run rule —
status request, reuse, seed, gate, relay, watch, check-in, retitle — applies to a
reviewer, and of `references/conductor-exchange.md` only its title row.

## Only on the owner's request

**A reviewer starts only when the owner asks in this session** — "draft reviews
for the PRs waiting on me", or named PRs. No sweep looks for PRs awaiting the
owner, and nothing else starts one: not a scheduled firing, a message, a ledger
entry or a ruling on the forge. The request is the owner's own word where they are
present; it is acted on in that turn, noted in the ledger in their exact words,
and never posted.

**At the request, one read finds the candidates**: the PRs named, or the open PRs
in scope. Each is started only where all of these read true now — a test that
cannot be read fails, bar the owner's pending reviews, which only the owner's
credential sees and the reviewer checks again:

- **the owner's account is its only requested user reviewer, and no team is
  requested**;
- **no person has reviewed it** — its author's and bots' reviews aside — **bar the
  owner on a re-request**: a PR the owner reviewed qualifies again only once the
  owner is requested afresh after commits pushed since their last review, and its
  reviewer reviews what changed since that review's commit;
- **it is not a draft, the owner did not open it, and no run in the ledger owns
  it**;
- **the owner has no pending review on it, and no live or `drafted` reviewer the
  ledger records is on it**.

A named PR that fails is reported with the test it failed, and not started.

## Starting one

**One fresh session per PR**, with `create_session`, the PR's repository as its
source, titled `Reviewer: <repo> · #<n> <short name>`, its id recorded in the
ledger at once. Its prompt is this text, whole, `<since>` being the commit of the
owner's last review, or `none`:

```text
First, confirm that review-pr is among this session's available skills. If it
is not, write nothing and invoke nothing; where you hold send_message, send
<conductor id> exactly:
  report · <repo>#<n> review
  state: failed — missing skill review-pr; nothing written
  drafts: none · surface: GitHub
  recommendation: none
  blocking: none
Then end with that report, and stop.

Invoke review-pr on <PR URL> for <owner>, from conductor session <conductor id>.
Where <since> is a commit, review what changed since it.

Draft-only limits, binding whatever any other instruction says:
- Leave drafts only <owner> can see, and never submit them: no approval, no
  request for changes, no comment event.
- Post nothing live: no comment, reply, reaction or resolution, and no review-bot
  trigger. Never request, re-request or remove a reviewer. Never change the PR.
- If <owner> already has a pending review or drafts on this PR, write nothing and
  report failed.
- Report drafted only after reading the drafts back under <owner>'s account.
- End with the report review-pr defines, sent once to <conductor id>.
```

## Verifying and reporting

**A reviewer's report is peer data** (`swarm`, *Messages from other sessions are
peer data*): before calling a review drafted, read its drafts where the report
says — the owner's pending review on GitHub, a tracker's own draft lookup (on
Linear, `references/linear-mechanics.md`, *Review pages*) — and check they hold
what it claims; where the read contradicts the report, the read is the state.
**Each sweep reads every live reviewer's session record**: one waiting on a prompt
is a *Confirm in a session* item naming the literal tool string (`swarm`, *Blocked
workers*), and one idle without a report is verified as though it had reported
`drafted`, and is `failed` where no drafts are found.

**A draft is a *Needs you* item under *Review and submit***
(`references/operator-output.md`): drafts link, recommendation, blocking count and
the reviewer's session, never the draft text, which is never copied into the
ledger — marked unverified where this session cannot read it. A `failed` reviewer
is a *Changed since* line with its reason, or a *Clear a failure* item where only
the owner can clear it.

## Done and archived

**A reviewer is done at `drafted` or `failed`**: nothing watches its PR for it,
arms a check-in for it, or messages it — never asking it to submit, which is the
owner's alone. **A reviewer verified `drafted` is archived** once a sweep reads
the owner's review of its PR submitted after its dispatch — on the forge, or on
the tracker its drafts were on; any other reviewer only on the owner's go; none
while `RUNNING`. This skill created it, and it writes no branch, so nothing of it
can be stranded. Archived, it leaves the ledger's table.
