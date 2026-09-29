---
name: supervise-prs
description: Supervise a set of open pull requests from adoption until each is individually finished — arm a watch that actually wakes, read each PR as a snapshot, sort every CI failure into this PR's, the environment's or expected-red, route review feedback, dispatch bounded `repair-pr` passes within per-PR budgets, adopt the pushed head, re-trigger review, and return an outcome per PR. The caller passes the PR set, its resolved budgets, the posting-identity map, how repairs are dispatched and any check of its own on an adopted head; the caller's event loop runs it, or it runs its own. Invoked by backlog-orchestrator, implement-issue and npm-dependency-upgrade-orchestrator. Use when asked to watch, babysit or supervise PRs through CI and review. It never merges.
---

# Supervise PRs

Own a set of open PRs from the moment each is adopted until it is individually finished, and return what became of each.

This file is the contract; the reasoning and incident history behind its rules live in `NOTES.md` beside it, keyed by section. NOTES explains; it never overrides.

**It never merges, and it owns no loop unless it is told to.** Merging is decided by a gate its caller runs — `settle-and-merge`, *The merge gate*, or a caller's own. A caller with an event loop runs this skill's *Pass* from inside that loop and arms the one wait itself; a caller without one lets this skill run its own (*Wait*). Either way there is one supervisor per PR, and it is whoever invoked this skill.

## Inputs

**Everything that differs between callers arrives as an input; this skill never reads its caller's contract to find out what to do.** Each caller states in its own text what it passes, as a value — never a pointer this skill would have to follow. **An input the caller did not pass takes the default in the last column**, never a value inferred from which skill the caller is.

| input | what the caller passes | where it is absent |
| --- | --- | --- |
| **PR set** | the PRs to supervise, each with its repository, branch and base, the head as the caller knows it, and the canonical issue URL where there is one | nothing to supervise: return, naming the missing input |
| **budgets, per PR** | the resolved caps for `ci-repair-cycles`, `review-repair-cycles`, `finding-repair-cycles` and `repair-model-escalations`, each with its source. This skill never reads `.claude/agent-policy.json` itself (`references/agent-policy.md`, *Resolution*) | **every cap 0**: the run classifies and reports and pushes nothing, and the report says no budgets were passed. A repair is authority to push to someone's branch, and an unmentioned authority was not granted |
| **counters, per PR** | cycles and escalations already used, and review rounds completed, from the caller's record | rebuilt from the PR's durable evidence at *Adopt* |
| **posting-identity map** | the run's map (`references/posting-identity.md`) | start empty: every entry `unestablished`, and writes degrade as that rule states |
| **review routing and trigger state, per PR** | the review conventions the PR's routing requires, and per convention the trigger's state — `issued`, `verified`, `pending`, `deferred` (with who owes the round and when), or `unavailable` — and any round recorded `refused` | the routing from the repository, per `references/review-trigger.md`; the state read off the PR's timeline at *Adopt*; nothing found is `pending` |
| **repair dispatch** | `direct` — invoke `repair-pr` in this session on a dedicated checkout of the PR branch, and its result comes back; `swarm` — each pass is a worker under that skill's isolation, countermand and release, with whether a worker's return value reaches the run on its tier; or `none` — classify and report, dispatching nothing | `direct` |
| **head checks** | zero or more checks of the caller's own, each **stated in full**: what it compares, when it runs — `on-repair-head`, before a repair's pushed head is adopted, or `every-pass` — and what each result does: `adopt`, `hold as DECISION`, or `return to caller` | none |
| **caller pushes**, per pass | heads the caller pushed to a supervised branch since the last pass — a restack, a renumber, a re-resolution — each tagged `mechanical` or `substantive` by `references/mechanical-pushes.md`; and the branches the caller is about to mutate, which it holds locked | none |
| **findings to repair** | settle-time findings on a supervised PR, verbatim with their durable site: an `IN_FLIGHT_FIX` action point, or a recorded ruling that requires the PR's code to change | none |
| **wait owner** | `self` or `caller` | `self` |
| **monitoring cap** | a wall-clock bound on this skill's own loop | none: the wake budget alone bounds it |
| **return on** | `every-pass`, `any-terminal` — a PR reaches `finished` or a terminal outcome, or a `return to caller` head check fires — or `all-terminal` | `every-pass` where the caller owns the wait; `all-terminal` where this skill does |
| **state emission** | `every-pass` or `changes-only` — whether each pass reports every PR's record or only the records that changed | `every-pass` |
| **transport record** | per-tool attribution of reads to allowances, and allowance state, already observed | none known |

## Composed skills

- `repair-pr` — one bounded repair pass: `ci`, `review` or `finding`;
- `resolve-pr-comment` — composed by `repair-pr` for review threads;
- `review-docs` — where a PR's routing names it, invoked rather than posted (`references/review-trigger.md`, *Documentation-review routing*).

A composed skill that is unavailable → the pass reports it and repairs nothing through it. Never improvise a replacement workflow.

## One PR, one supervisor

**One PR, one supervisor, and it is this skill's invoker.** A worker never supervises its own PR, and a repair pass never waits for the next CI or review event (`repair-pr`, *Hard constraints*). No PR is ever supervised by two parties at once. That is about who watches, not how many mechanisms they hold: one owner arming both a subscription and a bounded check-in over the same PR is what *Wait* requires, and is not a second loop.

**Use platform PR surfacing where it exists; the platform observes, and this skill decides.** Claude Code's background PR watch, or an explicit subscription such as `subscribe_pr_activity`, may surface CI and review events; this skill decides whether a budget allows a repair and which pass to dispatch. Do not build a duplicate monitor merely because the PR originated in a worker, and never keep an agent alive per PR only to wait.

**Surfacing and merging are separate grants.** Where the platform's background PR behavior has auto-merge enabled, it merges once checks pass — on CI state alone, outside any gate the caller runs, whatever the repository's policy says. **Confirm it is off before relying on that surface.** Where it cannot be turned off, do not rely on it: subscribe explicitly instead, and report any merge it performs as a platform merge outside the gate, never as gate-approved. A caller that wants unattended merges has a gate for them; point there rather than at the platform toggle.

## The per-PR record

For every supervised PR:

```text
PR URL, repository, canonical issue URL where there is one
branch/base
remote head SHA
CI: per check — state, and attribution where red (references/ci-attribution.md)
review trigger: issued/verified/pending/deferred/unavailable         } one set per review
review round: pending/refused (reason, reset)/complete-with-findings/clean, per round } convention
reserved threads: question items and deferred-repair items, verbatim   } the routing
no-action threads                                                      } requires
draft state: as-created -> current
promotion convention: per-repository record, or absent
CI repair cycles used/cap · review rounds completed / review repair cycles used/cap · finding repair cycles used/cap
strongest-model repair rounds used/cap, with the locus evidence for each
mutator: none / repair pass <id> / caller
event subscription: armed/unavailable
last read: <time> — event / poll / mutation
outcome
```

**The review lines are held per review convention, not per PR.** Where a repository routes documentation to a second convention alongside its code review, a PR carries two sets, and a single set cannot record that one completed while the other is still pending — which is exactly what a merge gate has to read.

A caller may keep fields of its own beside these — where the caller is `backlog-orchestrator`, a chartered scope, stack relations and a worker session. **The record is a cache**: truth is the forge, and *Adopt* can rebuild everything here from it.

## Adopt

**A PR enters the tracked set by adoption, and adoption is three things, not one.** It is complete when the PR exists, **and** round 1 of every review convention it routes to has been requested against it, **and** this skill is subscribed to it or has recorded the subscription `unavailable`. Recording the first and skipping either of the others leaves a PR nobody reviews and nobody watches, and nothing fails to say so: the PR exists, CI runs. An observed tranche sat in exactly that state for about seven hours.

1. **Arm the watch now**, not when the run settles, and follow the arming with the reconciling read (`references/watch-and-read.md`, *Arm the watch when the item enters the tracked set*). `subscribe_pr_activity` is a call made per PR, and the background PR watch covers only what it already surfaced, so neither delivers anything for a PR until it is armed. Record the result in `event subscription`; a PR at `unavailable` is polled deliberately.
2. **Read the trigger state and act on it.** Whether a repository's reviewer starts a round when a draft is opened is that provider's behaviour, established by observation, so where it does not, the only evidence round 1 exists is a trigger somebody issued. `issued` or `verified` needs nothing here but the confirmation (*Review trigger*). **`deferred` needs nothing, and this step must not override it**: a deferral is a choice the caller recorded, naming what review is owed, and an unrecorded deferral is indistinguishable from an unfinished one. **A round recorded `refused` needs nothing either, and is never reissued** — not at adoption, not at a restart, not at a re-adoption (`references/review-trigger.md`, *A refused round*). **`pending` is an untriggered PR**: issue the trigger per `references/review-trigger.md` and the map, and confirm it took effect.
3. **Record the repository's promotion convention** for this PR, per `references/draft-state.md`.
4. **After a restart, or for a PR whose counters were not passed, rebuild the record from durable evidence**:
   - the trigger state and any refused round, from the PR's timeline — a posted trigger, a reviewer's out-of-budget answer;
   - reserved and no-action threads, from thread state and the settlement records on them;
   - cycles used, from the repair reports and repair commits on the PR;
   - **a counter this cannot recover is recorded `unknown` and treated as spent** — the cap reached, not zero — and reported. A lost cache read as zero hands a PR budget its owner already spent.

## Pass

One pass is one supervision cycle over the tracked set. In order:

1. **consume** the events already delivered, the caller's pushes, the repair passes that returned, and the findings the caller handed in;
2. **read what is due**, once, in one consolidated pass — `references/watch-and-read.md`, *Reading on a change signal* and *Allowances belong to the credential*, decide which PRs are due and how; fold the result into the records and stamp `last read`. A PR no signal named keeps the state it had. A PR observed merged or closed takes that outcome and leaves the pass;
3. **run every `every-pass` head check** and apply its disposition;
4. **CI** (*CI failure*); **review** (*Review feedback*); **findings** (*Finding repairs*); then **adopt** what came back (*Adopting a head*);
5. **promote** where a PR's recorded convention now says to (*Draft state*);
6. **pass the no-change preflight** before reporting any no-change result (`references/watch-and-read.md`, *The no-change preflight*);
7. **emit** the records per `state emission`, each stating the instant it describes (`references/establish-do-not-assume.md`, *Every read is a snapshot*), and **return** where `return on` is met.

**Read every verdict as `references/ci-and-review-verdicts.md` states it** — on the commit it describes, green as every required check concluded, clean as the summary for existence and the threads for severity — and never off an empty lookup (`references/absence-is-not-a-verdict.md`). A disagreement between a checkout and a response is settled by a third read (`references/establish-do-not-assume.md`, *Every read is a snapshot*).

### CI failure

On an actionable CI failure:

1. retrieve the smallest useful failure context;
2. **attribute it, per check, by `references/ci-attribution.md`** — a mass failure is not classified external without the confirmation that rule requires; unconfirmed, it is this PR's;
3. this PR's, `repair dispatch` not `none`, and CI budget remains → dispatch one `repair-pr` pass with `repair type = ci` (*Repair dispatch*), passing the failure context, the remaining budget and the map. With `repair dispatch = none`, report the check as this PR's failure instead;
4. adopt what it returns (*Adopting a head*) and increment the CI cycle where it pushed a repair;
5. CI budget spent → the PR's outcome is `needs-user`, with no further attempt.

**Attributed anywhere but this PR, with no justified code change, a failure consumes no cycle**: report it and keep watching. A check confirmed **expected-red after a producer merge** is reported with the refresh it waits on; it holds the PR's merge and counts as surfaced for `finished`. Bringing the PR onto that refresh is the caller's where the caller has authority over the branch — where the caller is `backlog-orchestrator`, its restack — and is reported as awaited where it has none.

**A worker's reported result is a claim; CI on the pushed head is the evidence.** Never let a merge decision rest on a failure a pass reported and nobody verified, nor on a pass it claims.

### Review feedback

What a run may auto-fix, the thread-root test, the owner's reservation and what counts as unhandled are `references/review-feedback.md`'s. Apply them from there. Two consequences for this skill's own writes:

- **never root a review thread on a supervised PR** — reply inside existing threads and post timeline comments only, because the thread-root test depends on it;
- **supervision comments are unattended writes, even on an attended run**: they are posted from this skill's loop without anyone reading them first, so they are short and carry the attribution footer (`references/authored-write-form.md`), under the author the map selects (`references/posting-identity.md`). **The review trigger is the one write exempt from the footer** (`references/review-trigger.md`, *The trigger comment*).

On unhandled feedback, as `references/review-feedback.md`, *Unhandled feedback*, defines it, **dispatch on any such round, including one where nothing looks repairable from the outside**, as that rule requires:

1. group the coherent current review round;
2. dispatch one `repair-pr` pass with `repair type = review`, the threads, the remaining budget and the map (*Repair dispatch*). **The budget gates repairing, not classifying**: dispatch even where the review budget is spent, because a classify-only pass consumes no cycle and an unclassified thread has no draft for a settlement path to clear its gate with. With the budget spent the pass classifies and drafts but repairs nothing: threads that would have been repairable come back as **deferred-repair items** — `NEEDS_USER` on budget grounds, under the round's `NO_CODE_CHANGE` outcome, never a `NEEDS_USER` outcome for the PR (`repair-pr`, *Hard constraints*). With `repair dispatch = none`, record the round unhandled and report it;
3. adopt what it returns (*Adopting a head*), and **record every `NEEDS_USER` item and every no-action thread it returned** — a question item with everything `resolve-pr-comment`, *What a question item must contain*, requires, verbatim and with its `html_url` forwarded rather than rebuilt; a deferred-repair item with that same `html_url`, the change it asks for and no draft; **a thread that returned two items is recorded once per item and is handled only when both are in** (`resolve-pr-comment`, *A comment can want both*). Recording is what stops a thread being re-grouped into a later round until new content arrives on it: a no-action thread left unrecorded is re-dispatched every pass, and a classify-only pass consumes no cycle, so nothing else would stop it. A pass that escalates one thread and pushes fixes for two returns both, so a pushed head is never evidence that nothing was escalated;
4. **increment the review cycle only where the pass pushed a repair.** A pass returning `NO_CODE_CHANGE` — the classification left it nothing to repair, whatever mix the round was — consumed no repair and consumes no cycle, and its items and drafts are recorded exactly as a pushing pass's are;
5. **only where the pass pushed a repair**, re-trigger review (*Review trigger*).

Review feedback may reference a head already superseded by a rebase or restack. Locate each finding by content rather than line number, and confirm it still applies to the current head before repairing. **Never derive the classification or write the draft here instead of dispatching** — `resolve-pr-comment` owns both, and a round triaged as question-only and never dispatched would be reserved with no draft.

### Finding repairs

A finding the caller handed in names actionable work on a supervised PR that no failing check and no reviewer's thread carries — a settle-time `IN_FLIGHT_FIX`, or a recorded ruling that requires the PR's code to change. `repair-pr`'s `finding` type takes it verbatim as its evidence.

1. take the finding verbatim — the action point's what/where/why/next-step, or the recorded ruling with its site URL;
2. finding budget remains → dispatch one `repair-pr` pass with `repair type = finding`, the finding and the map (*Repair dispatch*); spent → the PR's outcome is `needs-user`, carrying the finding;
3. **merge every identity entry the pass returned into the map, whatever its outcome** — a pass can author a write without pushing one;
4. branch on the outcome:
   - **pushed** → adopt it (*Adopting a head*), increment the finding cycle, and re-trigger review (*Review trigger*) — a finding repair's push is substantive, never mechanical;
   - **`NO_CODE_CHANGE`** — the finding no longer holds against the current head → adopt nothing, increment nothing, trigger nothing;
   - **`FAILED` or `NEEDS_USER`** → the PR's outcome is `needs-user`, carrying the finding and the pass's report;
5. **return the outcome, the finding and the updated map to the caller.** Whether the caller then settles again, or returns, is the caller's own rule.

The finding budget is its own counter, and an escalated round still consumes its cycle (`references/repair-rounds.md`, *The finding budget*). A finding requiring product or architecture judgment is `NEEDS_USER`, never a speculative repair.

### Adopting a head

Before any pass's pushed head is adopted:

- **one mutator per branch**: dispatch no pass to a branch the record shows another pass on, or the caller holding locked; and before dispatching, verify the remote head has not moved unexpectedly;
- **run every `on-repair-head` head check** against the pushed diff. `hold as DECISION` → adopt nothing: the PR's outcome is `held`, naming the check and what it found. `return to caller` → return with it. `adopt` → continue;
- **adopt the pushed remote head, and merge every posting-identity entry the pass returned into the map** — never replace the map: a pass runs on its own transports, so this is the only evidence about them;
- **forward the pass's body-drift flag** — whether the repair changed a behaviour the PR body asserts — to the caller, as a prompt for its reconcile before publish or merge and never as a precondition;
- release the pass through the dispatch mechanism.

### Pushes this skill did not make

A caller's push is adopted from the `caller pushes` input. **A `mechanical` push** (`references/mechanical-pushes.md`) consumes no review cycle, does not reset the PR's reviewed state, and re-triggers no review. A `substantive` one is reviewed like any other push. **Cannot tell → substantive.**

### Review trigger

Every trigger and re-trigger follows `references/review-trigger.md`: which convention, from which account, and never after a CI run or a mechanical push. **Confirm each took effect** (*Confirming a trigger took effect*), at adoption and after every re-trigger, and read a reviewer's out-of-budget answer as a refused round (*A refused round*).

Re-trigger **only where a pass pushed a repair**, and never where the round is `deferred`, a round on the PR is recorded `refused`, or triggering was suppressed in its repository. A `NO_CODE_CHANGE` pass left the head unchanged, so a re-trigger would ask for another review of identical code and its fresh threads would be dispatched against a pass that deliberately consumed no cycle. **Select the trigger's author from the map as it stands after the pass's entries were merged** — a repair can establish the invoking-user path the run lacked, and a re-trigger from the pre-repair map is what makes a trigger silently fail.

### Draft state

`references/draft-state.md` owns draft state and applies as written — promotion, including where a repository's convention instructs it; that a supervised PR is never returned to draft; and the only definition of an explicitly held draft. What is this skill's own:

- **the convention recorded at adoption is evaluated every pass**, where this skill re-reads the PR's CI, review and thread state;
- **a repair pass never touches draft state**: `repair-pr` reports how many actionable threads remain, and the PR's draft state stays with this skill;
- **an explicitly held draft is reported as held**, awaiting the owner.

**The review trigger is never optional, promotion or not.** Whether a provider acts on a publish is a property of the repository, established rather than assumed, and on a draft nobody promotes the trigger is the only path left.

## Repair dispatch

**This skill decides the pass and its model; the `repair dispatch` input performs it.**

- **Model**: Sonnet, or the strongest available model where *Escalation on evidence* has fired and an escalation remains (`references/repair-rounds.md`, which owns the trigger, the cycle cap and who decides). Read the remaining budget off the record and pass it (`references/repair-rounds.md`, *The remaining budget*).
- **Checkout**: every pass works on a dedicated checkout of the current PR branch, as `repair-pr`'s Inputs require.
- **`swarm`**: each pass is a worker under that skill's isolation, countermand and release. **Where a worker's return value does not reach the run**, its dispatch prompt carries the requirement to record its judgment on the PR under repair before returning: `repair-pr`'s Output contract minus what the run can read for itself, plus the head it pushed or found. That report carries what the pushed head cannot say — whether the failure belonged to this PR, why a `NO_CODE_CHANGE` pass changed nothing, whether a cycle was consumed, what a `NEEDS_USER` needs — and **it names each question item's thread and kind and leaves its draft reply out**: a PR comment is public, and a draft is never posted on any path (`resolve-pr-comment`, *The draft reply*).
- **`none`**: no pass is dispatched; every branch above that would dispatch reports instead.

## Budgets

**A repair cycle is a pushed repair pass, not a review round.** A PR can take many more rounds than its `review-repair-cycles` without exceeding it: a round that produced questions, acknowledgements or nothing to repair returns `NO_CODE_CHANGE` and consumes nothing. **Report both numbers — rounds and cycles — and state the cycle count against the cap in every status line that mentions a repair round** (`#176 repair 2 of 2`), because either alone reads as a budget blown through or a PR barely reviewed. A round count is never evidence for raising a cap.

**Exhaustion is an outcome for CI and finding repairs, and items for review.** A spent CI or finding budget makes the PR `needs-user`; a spent review budget produces deferred-repair items under a `NO_CODE_CHANGE` round and never a `needs-user` outcome for the PR.

## Wait

**The subscription is armed per PR at *Adopt*, whoever owns the wait.** What differs is who arms the check-in and runs the loop.

**`wait owner = self`.** This skill runs its own loop: *Pass*, then wait, then *Pass* again. While a pass is in flight its completion is the event; otherwise arm the wake `references/wake-budget.md` requires — the subscriptions plus a bounded scheduled check-in — under that rule's budget and backoff. The durable state each wake compares is every supervised PR's head, CI conclusions, review-thread set and each thread's resolved state, mergeability and review rounds. The loop ends when `return on` is met, when the `monitoring cap` elapses, or when the wake budget is spent — reported as that rule requires, with every PR still open named. **When neither a subscription nor a scheduler can be armed**, return the restartable checkpoint that rule requires, outcome `cannot-watch`, rather than holding the session open reporting supervision that is not happening.

**`wait owner = caller`.** This skill arms no check-in and runs no loop: **one loop and one wait per session, and both are the caller's.** The caller's single wake re-runs *Pass*, and its prompt carries, beside its own lines, what this skill's comparison needs — the PR set and the durable state per PR above. A change on a supervised PR is a delta on the caller's one counter; this skill keeps no counter of its own.

Do not use CPU loops, file-touch loops, detached sleeps or meaningless commits to keep a loop warm.

## Outcomes

Per PR, one of:

- **`finished`** — the PR is individually finished:
  - CI is green on the head, or every red check is confirmed expected-red after a producer merge and reported;
  - every review round its routing requires is completed — **or recorded `refused`, which counts as surfaced**: it holds the PR's merge and never its finishing;
  - every unhandled thread is handled — resolved, recorded no-action, or reserved for the owner, **which counts as surfaced**: it holds the merge and never the finishing;
  - no pass is in flight, and no remaining budget could make another.
- **`waiting`** — on CI, a review round or an allowance reset, naming which and since when.
- **`repairing`** — a pass is in flight.
- **`held`** — a head check held it, or the caller holds its branch.
- **`needs-user`** — a CI or finding budget is spent, a CI failure or finding needs judgment, or a pass returned `FAILED` or `NEEDS_USER`. **A reserved thread is an item, never this outcome.**
- **`merged`** / **`closed`** — observed, whoever did it.
- **`cannot-watch`** — nothing could be armed; a restartable checkpoint was returned.

## Report

This is a status report: what it says a PR, a thread or a check *is now* needs a read behind it, or says when it was last read (`references/establish-do-not-assume.md`, *You are about to assert it*). Per PR:

- the outcome, the record, and whether it changed this pass;
- CI per check with its attribution; every expected-red check with the refresh it waits on;
- review rounds per convention, and cycles against caps; every strongest-model round with the locus evidence that triggered it;
- **every reserved thread, per item kind** — a question item's required fields verbatim; a deferred-repair item's `html_url` and requested change, with no draft — and every no-action thread;
- every refused round with its reason and reset; every repository whose triggering was suppressed; every PR left unreviewed and why;
- promotions performed, and every explicitly held draft;
- the body-drift flags passes returned;
- the subscription column and `last read`, and any reads deferred with when the allowance resets;
- the watch's state — armed, its unproductive count by kind, or expired and why.

And for the run: **the posting-identity map with every entry passes observed**, under its `(transport, credential)` key, `unestablished` where no write was read back — never collapsed to one pair.
