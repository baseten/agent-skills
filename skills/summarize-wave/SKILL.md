---
name: summarize-wave
description: Write a short plain-language summary of what a settled implementation wave actually did, plus the action points a human still has to manage — follow-up issues to open, bugs found but not fixed, decisions waiting, scope deliberately left out. Runs per settled wave, before plan-merge-order ranks the PRs. Use when a wave settles, or when asked what a run accomplished and what still needs attention.
---

# Summarize Wave

Report what one settled wave did and what a person now has to do about it. Two outputs, in this order: a **very short summary**, then **action points**. Nothing else — this is the read a colleague gets who did not watch the run.

This file is the contract; the reasoning behind its rules lives in `NOTES.md` beside it, keyed by section. NOTES explains; it never overrides.

Read-only over the wave's durable state: it ranks nothing, merges nothing, and — unless the invocation explicitly authorizes it — creates nothing.

## When it runs

- **Per settled wave**, never saved up for the end of a whole backlog (NOTES: findings are perishable; follow-ups must exist while later waves run).
- **Before `plan-merge-order`** — the summary can change what should merge (NOTES). The caller's closing order is: reconcile state, summarize, then rank. A caller with no ranking (`implement-issue`) satisfies this trivially; a one-issue run is a wave of one, and nothing here reads differently at that size.
- A wave that produced nothing worth reporting still gets one line saying so — silence is indistinguishable from a skipped step.

## Inputs

- the wave's scope: manifest/root issue URL, or the explicit issue set;
- its PRs;
- worker outcomes and review findings from the run, where available.

## Sources

Derive everything from **durable evidence** — tracker state, PR bodies, diffs and comment threads (a worker's report comment on its PR included — it is where a deliberately raised caveat lives), completed review findings, CI results — never from the orchestrator's recollection. A restarted session summarizing the same wave must produce substantially the same text. Run context may enrich (why an approach was abandoned, what a reviewer and worker disagreed about); it never replaces the record.

# 1. The summary

One paragraph, or up to six bullets. **Hard ceiling.** It is a status summary, so every sentence in it about what a PR, a thread or a session *is now* needs a read behind it, or says when it was last read (`references/establish-do-not-assume.md`, *You are about to assert it*).

Say what changed and what it means. NOT: restating each PR's description in turn — the PRs are already that record, and a per-PR recap is the failure mode this skill exists to avoid. One coherent thing across twelve PRs is one sentence.

Include, only where true and material: what the wave accomplished in the requester's terms; the shape of the work (issues, PRs, independent or stacked); anything that turned out differently than the tickets described (stale baseline, mis-scoped partition, unreal dependency); anything a worker found that was not the assigned work; **that the settle is partial**, where planned work waits on an item (*2. Action points*).

Leave out: worker mechanics, retry counts, runtime tiers, token spend, and every number the caller's checkpoint output already reports.

# 2. Action points

Anything that still needs an owner and an action — human **or** orchestrator. An `IN_FLIGHT_FIX` is dispatched by the orchestrator and belongs here too: filtering to human-only items would hide exactly the finding that stops an unfinished PR being ranked as ready (NOTES).

Each one states: **what** (one line) · **where** (issue URL, PR URL, or `path:line`) · **why it is not already done** (out of scope, needs a decision, needs authority this run lacked) · **the next step**, concrete enough to act on without re-deriving it.

**A change in this wave, merged or open, to a timing something outside the diff watches is a `MERGE_RISK`, even when the change is right**: a schedule, a cron, a worker's cadence, a healthcheck's ping period, a timeout an alert or SLA is set against. Name the old and new values and what watches them. The test is the outside observer — a monitor, an alert, a downstream consumer, people's routine — so an internal retry backoff or a test timeout is not one (NOTES).

**A PR body contradicting its diff that the run may not edit is a `MERGE_RISK` that holds only its own PR** (`references/authored-write-form.md`, *Editing a PR body after it is created*): the body's claim, what the diff now does, and a suggested replacement — the next step is the author's edit.

**Every claim these items make about existing code or current state needs a read behind it before the item is written** (`references/establish-do-not-assume.md`, *You are about to assert it*; NOTES). A claim that cannot be settled first is written with that said and with what would settle it, rather than plainly or not at all.

| class | meaning |
|---|---|
| `NEW_ISSUE` | real follow-up work with no ticket yet |
| `DECISION` | blocked on a human choice, not on effort |
| `IN_FLIGHT_FIX` | belongs in an open PR from this wave, not a new one; orchestrator-owned, never omitted for that reason |
| `MERGE_RISK` | something the merge decision must account for |

**A prose reviewer's findings arrive here to be classified, and they arrive as a result rather than as threads.** `review-docs` and `review-skill` post one comment per round and never a thread per finding (`prose-review-round-budget`), so their findings reach this skill through the PR result forwarded by `create-pr` → `implement-issue-core` → `implement-issue`, not by reading the PR's threads. Classify them like any other: a false claim a repair can correct is `IN_FLIGHT_FIX`, one the merge must account for is `MERGE_RISK`, one needing an author's intent is `DECISION`. **A routed review that found nothing and no routed review at all are different states**, and only the first is evidence the prose was read — do not read the absence of findings as a clean review (`references/absence-is-not-a-verdict.md`).

The first three say **who owns the follow-up**; `MERGE_RISK` says the merge decision must account for it. Different questions — **an item can carry both** (a verified no-ticket defect that must land before one of this wave's PRs is `NEW_ISSUE` *and* `MERGE_RISK`; NOTES). Where an item has an ordering consequence, say so on the item, whichever class it carries.

**A reserved review thread with nothing able to dispatch it is never `IN_FLIGHT_FIX`** —
a question item, or a repair deferred because `review-repair-cycles` was spent
(`references/review-feedback.md`, *Reserved for the owner*). For those two the
orchestrator already holds that PR's merge and has no compliant dispatch: the review path
refuses the thread on budget and re-admits it only on new content, and the finding path
exists for work no thread carries
(`supervise-prs`, *Finding repairs*).
Classing one as `IN_FLIGHT_FIX` un-settles the wave with nothing able to act on it. So
report a **deferred repair as `MERGE_RISK`** — the requested change, the thread's
API `html_url` as the orchestrator recorded it and never rebuilt
(`references/review-feedback.md`, *Reserved for the owner*), that the review repair
budget was spent, and that the next step is to apply it or lift the budget. A
**question** thread is not an action point of its own: the walkthrough reads it from
the question item the run recorded, which is what spares the owner opening the
thread at all. **An approval-pending reply is not one either**: its fix is pushed, and
the walkthrough reads it from the item the run recorded
(`references/review-feedback.md`, *Approval-pending replies*).

**The test is the absence of a dispatch, not the reservation.** One reserved thread has
one: a thread carrying a **recorded code-changing ruling whose change has not been pushed**
is `IN_FLIGHT_FIX`, and the finding path takes it — unless that path already refused it (below) — a recorded ruling requiring this PR's
code to change is exactly what that path's evidence is. It
must be emitted, because after a restart nothing else will. **What survives is the ruling,
not the reservation** — a reservation is run state that a later invocation does not carry
(`references/review-feedback.md`, *Reserved for the owner*), so the recoverable fact is
the ruling recorded on the thread with its change still unpushed. Nothing else reaches it:
the walkthrough's already-ruled test retires the question rather than re-emitting it, and the
same-run route from the walkthrough's own output is gone with the run. Excluding it would
leave the change with no dispatch path and the merge gate shut for good.

**The same test covers work a spent budget or a failed repair already refused**, scoped to
the work the `NEEDS_USER` item on the PR names: a spent CI budget refuses that PR's CI-shaped
work; a spent finding budget refuses every finding on that PR, a recorded ruling's included;
a finding repair that returned `FAILED` or `NEEDS_USER` refuses that finding. Refused work
has no dispatch until the owner rules, so its action point is a `DECISION` — try again, which
the caller runs as a finding repair within the finding budget; take the fix over; or close
the PR — never `IN_FLIGHT_FIX`. A different finding on the same PR, with its own budget
left, stays `IN_FLIGHT_FIX`.

**An action point holding a PR that planned work waits on names that work.** Where issues in the wave's scope that have not started are blocked — directly or through their blockers — by an open PR of this wave held for the owner — a `DECISION` it waits on, a `NEEDS_USER` item raised on it, a charter hold — or by an issue whose worker is held on the owner's authority (the caller's partial-settle definition, where it has one) and whose hold's item is not retired, or survived its release restated to the work unit (`swarm`, *Blocked workers*, its last rule), name them on that item by issue URL, read from the scope's durable dependency graph (*Sources*), and say in the summary that the wave settled with that work still to come. The settle is then partial: the run resumes that work once the item is ruled and its PR moves — or, where the caller reports the ruling cannot move it, the item says what would. Without it, a wave waiting on the owner's answer reads the same as one that is done.

Drop the merely informational: "worth keeping an eye on" is not an action point.

## Collapse recurring findings

The same defect class across several workers is reported **once as a class** with its instances listed under it — never once per worker (NOTES). State the class, the shared root cause, every known instance, and why each worker was right to patch locally rather than fix centrally.

## Do not invent work

Every action point traces to something observed: a worker's finding, a review comment, a deliberate scope cut, a failing check, a verified defect. Speculative improvements, refactors nobody asked for, and code-quality opinions are not action points. No action points → say so in one line and stop; an empty list is legitimate and common.

## Deduplicate against the tracker

Before proposing any `NEW_ISSUE`, check whether the tracker already has one covering it — including one opened by an earlier wave of the same run. Report an existing ticket by URL instead of proposing a duplicate (NOTES).

## Verify before reporting a defect

A worker-reported defect is a claim about that worker's environment. Confirm it against the repository — the schema, the fixture, the type, the failing test — before it becomes an action point with someone's name on it, and report what you verified and how (NOTES).

# Creating the follow-up issues

- **Read-only by default**: propose `NEW_ISSUE` items; open nothing (NOTES: separate authority).
- When the invocation explicitly authorizes creation: open each proposed issue in the wave's tracker, link it to the originating PR or issue, and report the created URLs in place of the proposals. **Each issue body follows the authored-write-form rule** (`references/authored-write-form.md`) — short, stating intent rather than restating the wave, and **carrying the attribution footer**, because authorizing creation is not approving a body nobody has read: that rule's approval test asks whether the invoking person approved *this exact text*, and an authorization given before the text existed cannot have. Each issue's author follows the posting-identity rule (`references/posting-identity.md`). Never open an issue the summary did not propose, and never open one that deduplication matched to an existing ticket.

# Boundaries

- No merge ordering, review ranking, or batching — that is `plan-merge-order`, which runs after this.
- No merging, no restacking, no PR mutation.
- No new implementation work, no dispatching of workers.
- No status transitions on tracker issues.

# Output

```text
## Wave summary

<one paragraph, or up to six bullets>

## Action points

1. [NEW_ISSUE] <what> — <where> — <why not done> — <next step>
2. [DECISION]  <what> — <where> — <why not done> — <next step>
```

Return alongside the report: wave scope (manifest/issue set); PRs covered; action point counts by class; issues created, when creation was authorized; anything that could not be verified, and why.
