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

**Why an item names the planned work waiting on it (#148, owner's ruling 2026-09-29):** `backlog-orchestrator` settles over a PR whose question has been raised as an item — the settle exists to get that question to the owner — even where unstarted work in scope depends on the PR. Settled then means "waiting on you", not "done", and nothing in a summary told the two apart: the owner read a finished-looking tranche and did not know three issues were parked behind their answer. The dependency is read from the durable graph rather than taken from the orchestrator, for the same reason as everything else here — a restarted summary must say the same thing.

**Why a claim in an action point needs a read first:** the `where` and the `why` are exactly where a recollection gets stated as a fact, and a `DECISION` is the expensive place for one — the owner rules from it, holding less of the codebase than the run does.

**The timing incident behind the outside-observer `MERGE_RISK`:** a scanner moved from manual to hourly pings left a five-minute healthcheck flapping every hour for a day.

**Why an uneditable body drift is a `MERGE_RISK` carrying a replacement (#163, owner's ruling 2026-09-30):** the run may no longer rewrite a published body a person has read, so the fix is the author's, and the replacement is what makes it a minute's work; the merge still holds on it, as it did when the run edited instead.

**Why merely-informational items are dropped:** a list padded with observations trains the reader to skim past the real items.

**Why a held worker stops holding its dependents when its item retires (#151):** `swarm`, *Blocked workers*, now retires a hold's `NEEDS_USER` item when the worker is observed to resume, be released or be redispatched. A worker that resumed is ordinary in-flight work again, so naming its issue's dependents as waiting on the owner would report a partial settle over an answer already given. The clause cites the retirement rather than restating it.

## Collapse recurring findings

N workers independently patching around one wrong shared fixture is a single follow-up with N sites: reporting it N times buries the pattern and invites N duplicate tickets. A worker keeping an unscoped shared-file edit out of its own PR is *correct* behavior — the central fix being nobody's job is precisely what the class-level action point exists to correct, which is why the report states why each worker was right to patch locally.

## Verify before reporting a defect

A defect reported by a worker is a claim about that worker's environment, which may be misconfigured in ways the worker cannot see. An unverified action point costs a person the same investigation twice — once to discover the report is wrong, once to find what was actually true.

## Deduplicate against the tracker

A run that proposes the same fixture fix in five consecutive tranche summaries has stopped being useful — hence checking existing tickets (including ones an earlier tranche of the same run opened) before proposing, and reporting the existing URL instead.

## Creating follow-up issues

Read-only by default because opening tracker issues is a separate authority, consistent with this repo's other read-only reporting skills; explicit invocation authorization is what flips it, and even then never for an issue the summary did not propose or that deduplication matched.
