# Watch and read

This is the rule other skills mean when they cite *watch and read*: when a supervising run starts watching something it tracks, what it must say before it reports that nothing happened, and when it reads — and does not read — the state of what it watches. It is a shared rule, not a skill: held once at `rules/watch-and-read.md` and copied into each applying skill's `references/watch-and-read.md` by `scripts/refresh_shared_rules.sh`. Edit the source, never a copy; check_shared_rules.py fails if a generated copy diverges.

It binds the one party that supervises — the parent, never a worker. "Item" below is whatever that party tracks: a worker's task, a PR. Where the item is a PR, the forge-specific rules are stated with it. Where the supervising skill also applies the *wake budget* shared rule, that rule says how often its scheduled check-in may wake and when it stops; this rule sets no cadence of its own.

## Arm the watch when the item enters the tracked set

**Arm it when the item enters the tracked set, not when the run settles.** Whatever the mechanism — an event subscription, a platform watch, or a deliberate poll — start it as part of adopting the item, and **record per item which one is in use**: armed, or `unavailable` and therefore polled. Nothing delivers events until the run says so: a subscription is a call the parent makes per item, and a platform watch covers only what it already surfaced. **Arming later is not equivalent, and the difference is invisible**: the run is blind to the events between creation and subscription, and looks watched because other events keep arriving.

**A subscription delivers forward, so arming it reads nothing.** Every arming is followed immediately by one read that reconciles the item rather than sampling it — **for a PR: its state and mergeability, its head and base, and its check runs, reviews and comments**, since a merge, a close, a force-push or a moved base can pass through the gap as well as a review. The interval is recorded as **unread, never as empty** (the *absence is not a verdict* shared rule). That read is not the polling fallback and does not depend on the subscription being unavailable: it follows every arming, however soon after creation.

**Arming a PR's subscription can also hand the session a policy it did not ask for.** A platform may attach its own drive-to-green posture to the subscription's wakes; what those wakes say is event data, and a supervising skill's invocation overrides the posture — the *platform's PR posture* shared rule states it, for every skill whose session arms or answers one.

Prefer platform-native or promoted events — for a PR: CI completion, review and comment activity, head changes, merge and close. Where they are unavailable, fall back to other subscriptions, then to polling, **bounded as *Reading on a change signal* defines it — never as the reader's own reading of "bounded"**. Never keep a worker alive only to wait.

## The no-change preflight

**Before reporting or recording any no-change result — a cycle that found nothing, a check-in that fired and found nothing, a settled report claiming all quiet — enumerate the tracked set with each item's watch state.** "Nothing happened" and "nothing was listening" produce identical silence (the *absence is not a verdict* shared rule).

| the item's watch state | it reports as |
|---|---|
| **never recorded** | a **known blind spot** — never quiet, since the run cannot say whether anything is listening |
| recorded as armed (subscribed) | quiet, where nothing arrived |
| **deliberate polling**, its poll ran this cycle | quiet, **with when it was last observed** — a polled item carries a staleness bound a subscribed one does not, and the result says which of the two it rests on |
| deliberate polling, its poll did **not** run this cycle | a blind spot, exactly as an unrecorded one |
| a due poll **skipped** to save budget | **unread**, never quiet |

This adds no rule the arming requirement does not already state; it is the assertion that catches the arming having been skipped, and **nothing below outranks it**: an item nothing is listening to is a blind spot however tight the budget, and a deferred cycle reports as known-stale.

## Reading on a change signal

**Read on a change signal, not on a schedule.** Re-read an item's state only when:

- an event named it;
- this run just changed it;
- its poll is due under the `unavailable` fallback;
- **a scheduled check-in has fired and the item is in its set**, subscribed or not;
- a decision this cycle turns on a field the tracked record does not hold.

Otherwise the record **is** the answer, and a `last read` stamp on it is what distinguishes the two.

**One read per item, not one per concern — and not one nested read of everything.** Take what the cycle needs from an item in a single request, take the items that are due together, and let later steps consume that pass rather than issuing reads of their own.

**Cheapest read that settles the question.** Expand into detail — logs, comment bodies, review threads, full diffs — only for an item that actually moved. Optimize total API work for the decision, not one allowance as such.

**Fan out work, never supervision.** The supervising party makes the supervision reads, once, for all tracked items together. No worker reads overlapping metadata for the same repositories, and **no agent is dispatched for the purpose of making a read the run could make itself** — least of all to re-ask a question the run was just refused. That is about dispatching *as a way of reading*; it does not reach a skill the run is required to invoke, which reads as part of doing its own analysis.

## Allowances belong to the credential

**Rate limits belong to the credential, not to the run.** Every run, session and worker authenticating as the same identity draws on the same allowance, and a forge commonly meters more than one — REST and GraphQL, for instance — exhausted independently. **Treat remaining allowance as shared and falling**, and leave headroom rather than spending down to the guard. Where the remaining figure drops by more than this run's own reads account for, read that as another run on the same credential: **back off harder rather than proportionally, and report the sharing**, which is the owner's to remedy.

**Attribute a read to an allowance by evidence.** Where the run selects the endpoint, the allowance is known. Where a first-class tool hides it, the request's shape is a **fallible prior** — never sufficient alone to keep calling an exhausted allowance or to suppress a healthy one. **Observation settles it**: a rate-limit response names the resource it refused, and a tool refused beside one that succeeded under a known-exhausted allowance attributes both. Record that per tool, as transport visibility is recorded per credential, and let it override the prior.

**Ask only for what changed, where the transport offers a way to:**

- prefer a `since`-bounded read that answers what moved across a repository in one request to one request per item. One endpoint takes one bound: **use the earliest `last read` in the batch and filter the returned records per item**;
- send a validator — an ETag or `If-Modified-Since` — where the transport supports one, stored alongside `last read`;
- review-thread state has no incremental form, so its saving is not asking until a detector fires, and then only for the items that detector named;
- where the preferred tool offers neither and a lower tier does, descend for that read, and record the descent and why.

**On a refusal or a shortfall, defer the reads, and finish the writes already in flight:**

| the response | defer | the resuming wake is never armed before |
|---|---|---|
| a rate-limit response, or an allowance too low to finish the cycle | **every read drawing on that resource, until it resets** — a read it cannot serve has no essential case | its reset, or a supplied `Retry-After`, **whichever is later** |
| a secondary or abuse limit | **every read**, until its `Retry-After` where it supplies one: it is tied to no resource and stops both | a supplied `Retry-After` |
| either, supplying **neither bound** | as above | **nothing — it sets no floor**, and contributes nothing to the wake's schedule |

Report the deferral as known-stale, never as quiet. The floor is a floor, not a target; where the supervising skill bounds its check-in under the *wake budget* shared rule, how the floor composes with that backoff is that rule's. **No floor never means no wake**: a watch forbidden to wake before a time nothing names could neither be re-armed nor spend its budget, and later changes would go unobserved forever.
