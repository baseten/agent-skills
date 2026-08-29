# summarize-tranche — design notes

Companion to `SKILL.md`. That file is the contract; this one holds the reasoning, keyed by section. Read a section's note before changing its rules or when applying them to a case the contract doesn't obviously cover. Nothing here overrides the contract.

## When it runs

**Per settled tranche, not once at the end of a whole backlog**, because a tranche's findings are perishable: the worker reports, review findings, and diffs that produced them are in the current session's context, and a later session reconstructing them from PR bodies gets a thinner, less accurate account. Follow-ups also need to exist while the remaining backlog is still running, so the next tranche picks them up instead of rediscovering the same defect.

**Before `plan-merge-order`**, because the summary can change what should merge, or whether something should merge at all — a bug found mid-run, a follow-up that ought to land first. Ranking first buries that under a table the user has already started acting on. Where the caller ranks nothing (`implement-issue` settles one PR), the constraint is satisfied trivially: what it forbids is a ranking computed *before* the summary, not a caller without one. A one-issue run is a tranche of one, and nothing in this skill reads differently at that size.

**The empty case still gets one line** because silence is indistinguishable from a skipped step.

## Sources

Durable evidence, not the orchestrator's recollection, because a restarted session summarizing the same tranche must produce substantially the same text — the summary participates in restart-safe workflows. Run context is welcome only as enrichment (why a worker abandoned an approach, what a reviewer and worker disagreed about); it never replaces the record. A worker's own report comment on its PR is part of the durable record, and it is where a deliberately raised caveat lives.

## Action points

**Why `IN_FLIGHT_FIX` is included even though the orchestrator owns it:** the caller relies on that class to discover a PR is not finished, so filtering the list to human-only items would hide exactly the finding that stops an unfinished PR being ranked as ready.

**Why the classes and `MERGE_RISK` answer different questions:** the first three classes say who owns the follow-up; `MERGE_RISK` says the merge decision must account for it. An item can carry both — a verified defect with no ticket that must land before one of this tranche's PRs is a `NEW_ISSUE` *and* a `MERGE_RISK`, and reporting only the first tells the caller to file a ticket while leaving it free to rank that PR for merge.

**Why merely-informational items are dropped:** a list padded with observations trains the reader to skim past the real items.

## Collapse recurring findings

N workers independently patching around one wrong shared fixture is a single follow-up with N sites: reporting it N times buries the pattern and invites N duplicate tickets. A worker keeping an unscoped shared-file edit out of its own PR is *correct* behavior — the central fix being nobody's job is precisely what the class-level action point exists to correct, which is why the report states why each worker was right to patch locally.

## Verify before reporting a defect

A defect reported by a worker is a claim about that worker's environment, which may be misconfigured in ways the worker cannot see. An unverified action point costs a person the same investigation twice — once to discover the report is wrong, once to find what was actually true.

## Deduplicate against the tracker

A run that proposes the same fixture fix in five consecutive tranche summaries has stopped being useful — hence checking existing tickets (including ones an earlier tranche of the same run opened) before proposing, and reporting the existing URL instead.

## Creating follow-up issues

Read-only by default because opening tracker issues is a separate authority, consistent with this repo's other read-only reporting skills; explicit invocation authorization is what flips it, and even then never for an issue the summary did not propose or that deduplication matched.
