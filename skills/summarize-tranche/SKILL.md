---
name: summarize-tranche
description: Write a short plain-language summary of what a settled implementation tranche actually did, plus the action points a human still has to manage — follow-up issues to open, bugs found but not fixed, decisions waiting, scope deliberately left out. Runs per settled tranche, before plan-merge-order ranks the PRs. Use when a tranche settles, or when asked what a run accomplished and what still needs attention.
---

# Summarize Tranche

Report what one settled tranche did and what a person now has to do about it. Two outputs, in this order: a **very short summary**, then **action points**. Nothing else — this is the read a colleague gets who did not watch the run.

This file is the contract; the reasoning behind its rules lives in `NOTES.md` beside it, keyed by section. NOTES explains; it never overrides.

Read-only over the tranche's durable state: it ranks nothing, merges nothing, and — unless the invocation explicitly authorizes it — creates nothing.

## When it runs

- **Per settled tranche**, never saved up for the end of a whole backlog (NOTES: findings are perishable; follow-ups must exist while later tranches run).
- **Before `plan-merge-order`** — the summary can change what should merge (NOTES). The caller's closing order is: reconcile state, summarize, then rank. A caller with no ranking (`implement-issue`) satisfies this trivially; a one-issue run is a tranche of one, and nothing here reads differently at that size.
- A tranche that produced nothing worth reporting still gets one line saying so — silence is indistinguishable from a skipped step.

## Inputs

- the tranche's scope: manifest/root issue URL, or the explicit issue set;
- its PRs;
- worker outcomes and review findings from the run, where available.

## Sources

Derive everything from **durable evidence** — tracker state, PR bodies, diffs and comment threads (a worker's report comment on its PR included — it is where a deliberately raised caveat lives), completed review findings, CI results — never from the orchestrator's recollection. A restarted session summarizing the same tranche must produce substantially the same text. Run context may enrich (why an approach was abandoned, what a reviewer and worker disagreed about); it never replaces the record.

# 1. The summary

One paragraph, or up to six bullets. **Hard ceiling.**

Say what changed and what it means. NOT: restating each PR's description in turn — the PRs are already that record, and a per-PR recap is the failure mode this skill exists to avoid. One coherent thing across twelve PRs is one sentence.

Include, only where true and material: what the tranche accomplished in the requester's terms; the shape of the work (issues, PRs, independent or stacked); anything that turned out differently than the tickets described (stale baseline, mis-scoped partition, unreal dependency); anything a worker found that was not the assigned work.

Leave out: worker mechanics, retry counts, runtime tiers, token spend, and every number the caller's checkpoint output already reports.

# 2. Action points

Anything that still needs an owner and an action — human **or** orchestrator. An `IN_FLIGHT_FIX` is dispatched by the orchestrator and belongs here too: filtering to human-only items would hide exactly the finding that stops an unfinished PR being ranked as ready (NOTES).

Each one states: **what** (one line) · **where** (issue URL, PR URL, or `path:line`) · **why it is not already done** (out of scope, needs a decision, needs authority this run lacked) · **the next step**, concrete enough to act on without re-deriving it.

| class | meaning |
|---|---|
| `NEW_ISSUE` | real follow-up work with no ticket yet |
| `DECISION` | blocked on a human choice, not on effort |
| `IN_FLIGHT_FIX` | belongs in an open PR from this tranche, not a new one; orchestrator-owned, never omitted for that reason |
| `MERGE_RISK` | something the merge decision must account for |

The first three say **who owns the follow-up**; `MERGE_RISK` says the merge decision must account for it. Different questions — **an item can carry both** (a verified no-ticket defect that must land before one of this tranche's PRs is `NEW_ISSUE` *and* `MERGE_RISK`; NOTES). Where an item has an ordering consequence, say so on the item, whichever class it carries.

**A review thread the run reserved for the owner is never `IN_FLIGHT_FIX`** — neither a
question item nor a repair deferred because `review-repair-cycles` was spent
(`backlog-orchestrator`, *Merge policy and review feedback*). The orchestrator already
holds that PR's merge on it and has no compliant way to dispatch it: the review path
refuses the thread on budget and re-admits it only on new content, and the finding path
exists for work no thread carries
(`backlog-orchestrator`, *A settle finding is the third repair shape*).
Classing one as `IN_FLIGHT_FIX` un-settles the tranche with nothing able to act on it. So report a **deferred repair as `MERGE_RISK`** — the requested change, the
thread URL, that the review repair budget was spent, and that the next step is to apply it
or lift the budget. A **question** thread is not an action point of its own: the
walkthrough reads it from the thread.

Drop the merely informational: "worth keeping an eye on" is not an action point.

## Collapse recurring findings

The same defect class across several workers is reported **once as a class** with its instances listed under it — never once per worker (NOTES). State the class, the shared root cause, every known instance, and why each worker was right to patch locally rather than fix centrally.

## Do not invent work

Every action point traces to something observed: a worker's finding, a review comment, a deliberate scope cut, a failing check, a verified defect. Speculative improvements, refactors nobody asked for, and code-quality opinions are not action points. No action points → say so in one line and stop; an empty list is legitimate and common.

## Deduplicate against the tracker

Before proposing any `NEW_ISSUE`, check whether the tracker already has one covering it — including one opened by an earlier tranche of the same run. Report an existing ticket by URL instead of proposing a duplicate (NOTES).

## Verify before reporting a defect

A worker-reported defect is a claim about that worker's environment. Confirm it against the repository — the schema, the fixture, the type, the failing test — before it becomes an action point with someone's name on it, and report what you verified and how (NOTES).

# Creating the follow-up issues

- **Read-only by default**: propose `NEW_ISSUE` items; open nothing (NOTES: separate authority).
- When the invocation explicitly authorizes creation: open each proposed issue in the tranche's tracker, link it to the originating PR or issue, and report the created URLs in place of the proposals. Never open an issue the summary did not propose, and never open one that deduplication matched to an existing ticket.

# Boundaries

- No merge ordering, review ranking, or batching — that is `plan-merge-order`, which runs after this.
- No merging, no restacking, no PR mutation.
- No new implementation work, no dispatching of workers.
- No status transitions on tracker issues.

# Output

```text
## Tranche summary

<one paragraph, or up to six bullets>

## Action points

1. [NEW_ISSUE] <what> — <where> — <why not done> — <next step>
2. [DECISION]  <what> — <where> — <why not done> — <next step>
```

Report `No action points.` explicitly when there are none.

Return alongside the report: tranche scope (manifest/issue set); PRs covered; action point counts by class; issues created, when creation was authorized; anything that could not be verified, and why.
