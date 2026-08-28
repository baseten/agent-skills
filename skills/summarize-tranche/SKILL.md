---
name: summarize-tranche
description: Write a short plain-language summary of what a settled implementation tranche actually did, plus the action points a human still has to manage — follow-up issues to open, bugs found but not fixed, decisions waiting, scope deliberately left out. Runs per settled tranche, before plan-merge-order ranks the PRs. Use when a tranche settles, or when asked what a run accomplished and what still needs attention.
---

# Summarize Tranche

Report what one settled tranche did and what a person now has to do about it.

Two outputs, in this order: a **very short summary**, then **action points**. Nothing else. This is the read a colleague gets who did not watch the run.

This skill is read-only over the tranche's durable state. It ranks nothing, merges nothing, and — unless the invocation explicitly authorizes it — creates nothing.

## When it runs

**Per settled tranche, not once at the end of a whole backlog.** A tranche's findings are perishable: the worker reports, review findings, and diffs that produced them are in the current session's context, and a later session reconstructing them from PR bodies gets a thinner and less accurate account. Follow-ups also need to exist while the remaining backlog is still running, so the next tranche can pick them up instead of rediscovering the same defect.

Run it **before `plan-merge-order`**. The summary can change what should merge, or whether something should merge at all — a bug found mid-run, a follow-up that ought to land first. Ranking first and summarizing after buries that under a table the user has already started acting on. Ordering in the caller's closing output is therefore: reconcile state, summarize, then rank. Where the caller ranks nothing — `implement-issue` settles one PR, which has no ordering to produce — the constraint is satisfied trivially: what it forbids is a ranking computed before the summary, not a caller without one. A one-issue run is a tranche of one, and nothing else here reads differently at that size.

A tranche that produced nothing worth reporting still gets one line saying so. Silence is indistinguishable from a skipped step.

## Inputs

- the tranche's scope: manifest/root issue URL, or the explicit issue set;
- its PRs;
- worker outcomes and review findings from the run, where available.

## Sources

Derive the summary from durable evidence — tracker state, PR bodies, diffs and comment threads (a worker's own report comment on its PR is part of that record, and it is where a deliberately raised caveat lives), completed review findings, CI results — not from the orchestrator's recollection of its own run. A restarted session summarizing the same tranche should produce substantially the same text. Run context is welcome where it adds something durable state cannot show (why a worker abandoned an approach, what a reviewer and a worker disagreed about), but it never replaces the record.

# 1. The summary

One paragraph, or up to six bullets. Hard ceiling.

Say what changed and what it means. Do not restate each PR's description in turn — the PRs are already that record, and a per-PR recap is the failure mode this skill exists to avoid. If the tranche did one coherent thing across twelve PRs, that is one sentence, not twelve.

Include, only where true and material:

- what the tranche accomplished, in the terms the requester would use;
- the shape of the work: how many issues, how many PRs, whether independent or stacked;
- anything that turned out differently than the tickets described — a stale baseline, a mis-scoped partition, a dependency that was not real;
- anything a worker found that was not the assigned work.

Leave out: worker mechanics, retry counts, runtime tiers, token spend, and every number the caller's own checkpoint output already reports. Those belong to the orchestrator's report, not to a summary a person reads to understand the change.

# 2. Action points

Anything that still needs an owner and an action — whether that owner is a human or the orchestrator. Most action points need a person, but an `IN_FLIGHT_FIX` is dispatched by the orchestrator and belongs here too: the caller relies on that class to discover a PR is not finished, so filtering to human-only items would hide exactly the finding that stops an unfinished PR being ranked as ready.

Each one states:

- **what** — the specific thing, in one line;
- **where** — issue URL, PR URL, or `path:line`;
- **why it is not already done** — out of scope, needs a decision, needs authority this run did not have;
- **the next step** — concrete enough to act on without re-deriving it.

Classify each as:

| class | meaning |
|---|---|
| `NEW_ISSUE` | real follow-up work with no ticket yet |
| `DECISION` | blocked on a human choice, not on effort |
| `IN_FLIGHT_FIX` | belongs in an open PR from this tranche, not a new one; owned by the orchestrator rather than a person, and never omitted for that reason |
| `MERGE_RISK` | something the merge decision needs to account for |

The first three classes say **who owns the follow-up**; `MERGE_RISK` says the merge decision has to account for it. Those are different questions, so an item can carry both — a verified defect with no ticket that must land before one of this tranche's PRs is a `NEW_ISSUE` *and* a `MERGE_RISK`, and reporting only the first tells the caller to file a ticket while leaving it free to rank that PR for merge. Where an item has an ordering consequence, say so on the item, whichever class it also carries.

Drop anything that is merely informational. "Worth keeping an eye on" is not an action point, and a list padded with observations trains the reader to skim past the real items.

## Collapse recurring findings

When the same class of defect appeared across several workers, report it **once as a class**, with its instances listed under it — never once per worker. N workers independently patching around one wrong shared fixture is a single follow-up with N sites, and reporting it N times both buries the pattern and invites N duplicate tickets.

State the class, the shared root cause, every known instance, and why each worker was right to patch locally rather than fix centrally. A worker keeping an unscoped shared-file edit out of its own PR is correct behavior; the central fix being nobody's job is precisely what this action point exists to correct.

## Do not invent work

Every action point traces to something observed: a worker's finding, a review comment, a deliberate scope cut, a failing check, a verified defect. Speculative improvements, refactors nobody asked for, and general code-quality opinions are not action points. If the tranche produced no action points, say so in one line and stop — an empty list is a legitimate and common result.

## Deduplicate against the tracker

Before proposing any `NEW_ISSUE`, check whether the tracker already has one covering it, including one opened by an earlier tranche of the same run. Report an existing ticket by URL instead of proposing a duplicate. A run that proposes the same fixture fix in five consecutive tranche summaries has stopped being useful.

## Verify before reporting a defect

A defect reported by a worker is a claim about that worker's environment. Confirm it against the repository — the schema, the fixture, the type, the failing test — before it becomes an action point with someone's name on it. Report what you verified and how. An unverified action point costs a person the same investigation twice.

# Creating the follow-up issues

Read-only by default: propose `NEW_ISSUE` items, do not open them. Opening tracker issues is a separate authority, consistent with this repo's other read-only reporting skills.

When the invocation explicitly authorizes creation, open each proposed issue in the tranche's tracker, link it to the originating PR or issue, and report the created URLs in place of the proposals. Never open an issue the summary did not propose, and never open one that deduplication matched to an existing ticket.

# Boundaries

- No merge ordering, review ranking, or batching — that is `plan-merge-order`, which runs after this.
- No merging, no restacking, no PR mutation.
- No new implementation work, and no dispatching of workers.
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

Return alongside the report:

- tranche scope (manifest/issue set);
- PRs covered;
- action point counts by class;
- issues created, when creation was authorized;
- anything that could not be verified, and why.
