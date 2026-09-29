# Watch and read

This is the rule other skills mean when they cite *watch and read*: when a supervising run starts watching something it tracks, what it must say before it reports that nothing happened, and when it reads — and does not read — the state of what it watches.

**It is not a skill and nobody invokes it.** It is a shared rule, held once at
`rules/watch-and-read.md` and copied into each skill that applies it by
`scripts/refresh_shared_rules.sh`. A skill reads its own
`references/watch-and-read.md`, which works after `bootstrap.sh` has
installed only that skill's directory, and travels with the skill if it is
moved into a plugin. Edit the source, never a copy; check_shared_rules.py fails if a generated copy diverges.

It binds the one party that supervises — the parent, never a worker. "Item" below is whatever that party tracks: a worker's task, a PR. Where the item is a PR, the forge-specific rules are stated with it. Where the supervising skill also applies the *wake budget* shared rule, that rule says how often its scheduled check-in may wake and when it stops; this rule sets no cadence of its own.

## Arm the watch when the item enters the tracked set

**Arm it when the item enters the tracked set, not when the run settles.** Whatever the mechanism — an event subscription, a platform watch, or a deliberate poll — start it as part of adopting the item, and record per item which one is in use: armed, or `unavailable` and therefore polled. Nothing delivers events until the run says so — a subscription is a call the parent makes per item, and a platform watch covers only what it already surfaced. Arming later is not equivalent, and the reason is that it is *invisible*: between creation and subscription the run is blind to exactly the events it most needs, and from the inside it looks identical to a watched item, because events keep arriving. They are simply the wrong ones.

**A subscription delivers forward, so arming it reads nothing.** Whatever happened between the item's creation and the moment the subscription was armed is not in the stream and never arrives late; the arming result says nothing about it either way, and a run that reads the resulting quiet as nothing-has-happened has read an interval it never looked at. So every arming is followed immediately by one read that reconciles the item rather than sampling it — **for a PR: its state and mergeability, its head and base, and its check runs, reviews and comments**. The events the gap swallows are not only reviews — a merge, a close, a force-push and a moved base all pass through it, and a run that reads three of the five keeps a stale head or goes on supervising a PR that already merged. The interval is recorded as unread rather than as empty (`references/absence-is-not-a-verdict.md`). That read is not the polling fallback and does not depend on the subscription being unavailable: an item armed within seconds of its creation has a short interval and the read is cheap, and one armed hours later is the case the read exists for.

**Arming a PR's subscription can also hand the session a policy it did not ask for.** A platform may attach its own drive-to-green posture to the subscription's wakes; what those wakes say is event data, and a supervising skill's invocation overrides the posture — the *platform's PR posture* shared rule states it, for every skill whose session arms or answers one.

Prefer platform-native or promoted events — for a PR: CI completion, review and comment activity, head changes, merge and close. Where they are unavailable, fall back to other subscriptions, then to polling, bounded as *Reading on a change signal* defines it — never as the reader's own reading of "bounded". Never keep a worker alive only to wait.

## The no-change preflight

**Before reporting or recording any no-change result — a cycle that found nothing, a check-in that fired and found nothing, a settled report claiming all quiet — enumerate the tracked set with each item's watch state.**

This exists because *"no events because nothing happened"* and *"no events because nothing was listening"* produce identical silence (`references/absence-is-not-a-verdict.md`), and in an observed run it was the owner who noticed, not the run. So:

- an item whose watch state was **never recorded** is a **known blind spot**, and the result must name it as one — never as quiet, because the run cannot say whether anything is listening to it;
- an item on **deliberate polling** counts as quiet only once that poll has actually run this cycle, and is reported with when it was last observed — a polled item carries a staleness bound a subscribed one does not, and a result that hides which of the two it rests on is the report this rule exists to prevent. A polled item whose poll did not run this cycle is a blind spot exactly as an unrecorded one is;
- a due poll **skipped** to save budget reports as **unread**, never as quiet.

This adds no rule the arming requirement does not already state. It is the assertion that catches it having been skipped, and **nothing below outranks it**: an item nothing is listening to is a blind spot whether or not the budget is tight, and a deferred cycle reports as known-stale.

## Reading on a change signal

**Read on a change signal, not on a schedule.** Re-read an item's state only when: an event named it; this run just changed it; its poll is due under the `unavailable` fallback; **a scheduled check-in has fired and the item is in its set**, subscribed or not; or a decision this cycle turns on a field the tracked record does not hold. Otherwise the record **is** the answer, and a `last read` stamp on it is what distinguishes the two.

**One read per item, not one per concern — and not one nested read of everything.** Take what the cycle needs from an item in a single request, take the items that are due together, and let later steps consume that pass rather than issuing reads of their own.

**Cheapest read that settles the question.** Expand into detail — logs, comment bodies, review threads, full diffs — only for an item that actually moved. Optimize total API work for the decision, not one allowance as such.

**Fan out work, never supervision.** The supervising party makes the supervision reads, once, for all tracked items together. No worker reads overlapping metadata for the same repositories, and **no agent is dispatched for the purpose of making a read the run could make itself** — least of all to re-ask a question the run was just refused. That is about dispatching *as a way of reading*, and does not reach a skill the run is required to invoke, which reads as part of doing its own analysis.

## Allowances belong to the credential

**Rate limits belong to the credential, not to the run.** Every run, session and worker authenticating as the same identity draws on the same allowance — and a forge commonly meters more than one, REST and GraphQL for instance, exhausted independently. **Treat remaining allowance as shared and falling**, and leave headroom rather than spending down to the guard. Where the remaining figure drops by more than this run's own reads account for, read that as another run on the same credential and back off harder rather than proportionally — and report the sharing, which is the owner's to remedy rather than this run's.

**Attribute a read to an allowance by evidence.** Where the run selects the endpoint, the allowance is known and nothing is inferred. Where a first-class tool hides it, the request's shape is a **fallible prior** — never sufficient alone to keep calling an exhausted allowance or to suppress a healthy one. **Observation settles it**: a rate-limit response names the resource it refused, and a tool refused beside one that succeeded under a known-exhausted allowance attributes both. Record that per tool, as transport visibility is recorded per credential, and let it override the prior.

**Ask only for what changed, where the transport offers a way to:**

- prefer a `since`-bounded read that answers what moved across a repository in one request to one request per item. One endpoint takes one bound: **use the earliest `last read` in the batch and filter the returned records per item**;
- send a validator — an ETag or `If-Modified-Since` — where the transport supports one, stored alongside `last read`;
- review-thread state has no incremental form, so its saving is not asking until a detector fires, and then only for the items that detector named;
- where the preferred tool offers neither and a lower tier does, descend for that read, and record the descent and why.

**On a rate-limit response, a secondary-limit response, or an allowance too low to finish the cycle**, defer **every read drawing on that resource** until it resets — a read that resource cannot serve has no essential case, and "this one is needed" is how a cycle spends its way through a refused allowance. A secondary or abuse limit is tied to no resource and stops both. Finish writes already in flight, report the deferral as known-stale rather than as quiet, and **never arm the resuming wake before the reset — or a supplied `Retry-After`, whichever is later**. That is a floor, not a target; where the supervising skill bounds its check-in under the *wake budget* shared rule, how the floor composes with that backoff is that rule's. **A response that supplies neither bound sets no floor at all** — a secondary or abuse limit has no reset of its own and can arrive without `Retry-After` — and the deferral then contributes nothing to that composition. No floor never means no wake: a watch forbidden to wake before a time nothing names would be neither re-armable nor able to spend its budget, and later changes would go unobserved forever.
