# backlog-orchestrator — design notes

Companion to `SKILL.md`. That file is the contract; this one holds the reasoning and the incident history behind its rules, keyed by section. Read a section's note before changing its rules or when applying them to a case the contract doesn't obviously cover. Nothing here overrides the contract.

## Runtime selection

**Why the runtime preference was not reordered (review finding on the #59 PR):** the preference list puts remote worker sessions above subagents, and this change establishes that the parent can enforce invariant 5 on the second and not the first — so followed literally it prefers the tier where the guarantee is unenforceable. Reordering was rejected here on two grounds. It is a scope change rather than a correction: which tier a run uses affects disk, resilience and isolation, none of which invariant 5 settles alone. And the throughput argument for the remote tier, the one usually reached for, does not hold — subagents run genuinely concurrently, so the real purchase is a container per worker (four worktrees not sharing one disk, per `swarm`, *Capacity during the run*), a worker that outlives this session's compaction, and per-container tool isolation. Capacity and resilience, not speed. Getting that wrong in the first telling is what made the trade look one-sided.

What landed instead is the trade stated where the preference is made, plus the one lever the parent still has on that tier: a remote head that does not advance is reported after 30 minutes and raised at two hours. Measured in elapsed time, deliberately: the supervision loop has no minimum interval, so a cycle count is really a count of how busy the run is, and a burst of sibling events would have raised a working worker minutes after dispatch. That is not a capture and is not offered as one — it converts a state that reads as *still working* into one somebody sees. The knob that would let an owner prefer the enforceable tier is deliberately not here; it is policy, and it is tracked separately.

## Review and repair sessions

**Why a review session spends no repair cycle.** The same prompt had both review and repair sessions count against `review-repair-cycles`. That key counts pushed repair passes, and a review session pushes nothing — charging it would make every review round look like a spent repair and exhaust the budget on reading alone.

## Invocation and bounded scope

**Why the tracker's declared priority is the recommended scope (Sept 2026):** a run offered "audit the remainder" as its recommended scope while the tracker's own epic declared itself the immediate build priority. The tracker is the owner's statement of what they want built; an option the run composed from reading the code is the run's view, and recommending it by default quietly substitutes one for the other.

## Transport precedence

**Why an incremental gap counts as "no higher tier exposes it":** precedence buys attribution and permission handling, not efficiency, so a first-class tool with no `since` bound and no conditional-request support is not the cheaper choice merely by being first-class. Without that carve-out written down the two rules disagree in silence — precedence says stay on the tool, the budget rules say ask incrementally, and a run splitting the difference re-fetches everything through the preferred tier every cycle and calls it compliance.

## Authored write form

**Why the outbound claim check is stated at this decision point and in the dispatch prompt (round 12, Sept 2026):** the shared rule explains the general case; what belongs here is why this orchestrator's own writes need it and why the workers' do too. The orchestrator's expensive artifact is the `DECISION` item — the owner rules from it, holding less of the codebase than the run does — and the workers author almost everything else this run is judged by. This section's own literalism settles the second half: a requirement left out of a dispatch prompt is a requirement skipped, and the worker will accurately report that the task never asked for it, so constraining only the writes made here leaves most of the run's claims unchecked.

The rule moved to `rules/authored-write-form.md` and its reasoning to
`rules/authored-write-form-notes.md`. What remains here is the reasoning for the
parts that did **not** move: the interaction with the posting-identity rule
(`rules/posting-identity.md`) — identity
decides who a write appears to come from, that rule decides what it looks like
once authored — and the two below, which explain rules this skill implements and
the shared rule never states.

The `html_url` provenance rule is the one that is not obvious. A review-comment thread and a PR-level comment carry different fragment forms, so a URL assembled from a PR number and a comment id resolves — to the top of the PR, or to a different comment — and **the failure is invisible from the run's side**: the link is well-formed, it returns 200, and only the person clicking it discovers it went nowhere useful. There is no way to detect that from here, which is why the rule is provenance ("the string the API returned") rather than shape ("a valid URL"). It applies to every thread URL the skill emits, not only a question item's, because a no-action entry and a deferred repair name the same threads and are read by the same person.

The notification half is deliberately subordinate. A subscription dies with the session that armed it, so a notification is unobservable-in-principle from a later run: nothing may treat it as delivery, and the item is complete when it is *recorded*. Reporting whether one was sent is useful; depending on it having been seen is the failure mode.

## Mandatory validation preflight

**Why a resolved-premise node is `NEEDS_USER` and not a new state (Sept 2026):** it has to be somewhere the existing machinery already reaches, or it wedges the run — a node that is neither READY nor blocked-by-unmerged-work satisfies no settled condition, no stop condition and no restart classification, so the run can neither settle nor stop and a reader resolving that the cheap way dispatches it. `NEEDS_USER` is already surfaced in the closing output rather than asked mid-run, already handled by the settled predicate and the stop conditions, and already the right meaning: a person decides whether the issue is done, because this pass concluded it from outside the issue's own history.

**Why an issue being closed is not a trigger:** issue state is queryable, which is exactly why it slips through as a fact. It is still someone's assertion one step removed, and a waiver discharged by an assertion is a gate removed by whoever closed a ticket. The tracking issue is a coordination point the removal closes.

## Default usage safeguards

**Why the cycle keys are never called round caps (Sept 2026):** they count pushed repair passes, and a round producing questions, acknowledgements or nothing to repair consumes none. Calling them round caps in the one section that talks about them as limits is what makes a run at its sixth review round conclude the budget is spent when zero cycles are consumed and repairs are still authorised — the exact misread the counting rule exists to prevent, surviving beside it.

**Why one budget became two (Sept 2026):** `new-issue-budget` was doing two jobs and only one of them well. What actually hurt was the number of PRs open at once — reviewer load, merge-order complexity, conflict surface, thirteen across two repositories — and cumulative starts is a poor proxy for that. Worse, it made invariant 13 inert: a run that started twelve and merged all twelve watched its frontier advance onto work it was no longer permitted to begin, which is the opposite of a run advancing off merges.

**Why the reset is not routed through settle (revised, Sept 2026).** The first version restored flow-control capacity only once the settle sequence had run, to stop a run dispatching its way past settling. Review found two deadlocks in it and a third problem underneath them: a budget that withholds capacity from merged PRs is no longer a count of what is open, it is a hidden ledger of slots consumed since the last settle — unobservable, divergent from the checkpoint's own number, and lost on restart, which made restarting a free bypass. A closed-unmerged PR also never returned its slot, wedging the run with no exit.

The simpler shape has none of that. A slot is held while one of this run's PRs is open and released when it is not, whatever the reason, so any pass recomputes it by counting and nothing can be lost or laundered. The circularity that the earlier design routed the release through settle to avoid (the paragraph above) does not need it: `new-issue-budget` is the spend ceiling, no merge or close ever restores it, and it is what bounds the invocation. Flow control did not need a second mechanism to make it terminate — it needed to stop pretending to be one.

The spend ceiling deliberately does not move on a merge. Merging work already paid for is not authorization to pay for more, and keeping that separate is what stops the flow-control fix quietly turning a bounded invocation into an unbounded one.

**Why the predicate is a positive condition and not a list (round 5, Sept 2026):** it had wedged the run five times, and the last two were the same mistake in the statement rather than the design. The bullet was headed "nothing in scope is dispatchable", which was right, and then defined that by listing the kinds of unstarted issue allowed to remain — blocked by unmerged work, `NEEDS_USER`, blocked only by such an issue, READY and budget-held. Every list of that shape is one class short. The fifth wedge was a READY issue held by the open-PR cap with a child blocked by it: the child is none of the four, so the run could not settle, and with auto-merge on it could not merge its way out either. Defining *dispatchable* directly — what the run could start this cycle — makes "nothing is dispatchable" closed by construction, because anything not dispatchable is waiting on something by definition. The lesson generalises past this bullet: a condition that must hold for a run to rest should be stated as what forbids resting, never as an inventory of what is allowed to be left over.

**Why the definition names every hold, and why each is put to someone (round 6):** the first positive definition was READY, not `NEEDS_USER`, within budget — and was still one term short: a validation stop, a `DECISION` reaching an issue, and a capacity limit each held READY work without making it non-dispatchable, so the run could neither start it nor settle. Naming them fixed that and exposed the inverse: a hold that settles the run and is told to nobody is a stop nobody can clear, because a settled run wakes only on PR events. So every hold for a human is an item the owner has, and a limit that nothing will free is raised as one; a limit that resets on its own is simply re-tested. The restart count went the other way: counting live sessions from a checkpoint would have made recovery trust a cache, so the overshoot a previous parent's live workers can cause is bounded and reported instead.

**Why the settled predicate is one bullet, and why this is written down (round 4):** the fourth wedge in this section was not in any design — it was introduced by a merge. Merging main into this branch brought main's settled bullet in beside this branch's, each correct alone and answering the same question: which unstarted issues may remain. Every bullet in that list must hold at once, so the two were ANDed and neither could be satisfied — a budget-held READY issue failed one, a `NEEDS_USER` issue failed the other — and with auto-merge on the run could never reach the gate that would free a slot. The merge had been resolved by keeping both sides of every conflict, which is the right default for two paragraphs added at the same anchor and the wrong one for two statements of one condition. A mechanical merge cannot tell those apart. The bullet now says it must stay one, for whoever resolves the next conflict here.

**Why the release rule is a numbered step and not a paragraph (round 3):** stated as prose under a subsection about waiting for humans, it was 19 lines away from the decision point a close actually lands on — which still said *reconcile and stop there* — and a reader following the numbered procedure reached step 5, *stay settled*, and stopped. Three designs have now wedged in the same place, and twice the mechanism was right while its placement was not. It is step 5 itself now, and the close paragraph carries the scoping clause that stops *never on the close itself* reading as a prohibition on the dispatch the rule requires.

**Why the count includes in-flight workers (round 3):** counting open PRs alone lets two dispatches target the same future slot, because a worker that has not yet opened its PR is invisible to the count. With four concurrent workers that is three PRs over a cap whose whole justification is that thirteen was the number that hurt. Both halves are re-derived from durable truth at restart, so the count stays recomputable, which was the property the design was chosen for.

**Why a released slot is itself a dispatch trigger (round 2):** removing the settle-routing made the release real and left nothing acting on it. Every re-entry rule was keyed on the frontier *advancing*, so a run settled against the cap would watch its PRs merge as leaves that unblock nothing, each ending at a step that forbids dispatch, and hand off with spend unused and dispatchable work never started — the same wedge a third time, in the one place the simplification had not looked. The axis was every statement written on "settled means the frontier is empty", which the new predicate had made false by construction.

## Model and skill policy

**Why selection moved in front of the ladder (Sept 2026):** the ladder catches a worker that keeps failing, and the observed losses were workers that did not fail. One patched the single site its ticket named where the defect was restated at three — a green PR fixing a third of the bug. Another declined its own ticket's preferred option, correctly, by reading the spec over the issue text; a cheaper worker doing what the ticket said would have looked exactly as successful. No trigger that keys on repeated failure can reach either, which is why the assignment is made up front and the ladder is the floor under it rather than the mechanism.

**Why the axes live in `swarm` and not here:** that skill already owned model selection by failure visibility, and a second copy of the tiers in this file is the drift this repository keeps finding. What is genuinely this skill's is the implementation escalation ladder, which stays. The repair-escalation evidence trigger and the cycle interaction moved to `rules/repair-rounds.md` (#140), with their notes, because `implement-issue` applies them too.

## Implementation worker contract

**Why a recorded design choice names its failure paths (Sept 2026):** a run ruled that a submit path should create a plan and then submit against its id — right on the reason it beat the alternative, and silent on what persists when the submit fails after the plan exists, or what a retry does to it. The worker implemented the ruling as given, which is what a ruling is for, so the one party positioned to check the shape's failure paths was the one that chose it.

**Why a refused review is its own state here:** the shared rule explains why a refusal is an answer; what is skill-specific is that this run's remedy — report the PR as owing a round — is only reachable from a state that does not block settlement, and that every re-trigger path had to be closed for the rule to mean anything.

**Why the gate travels inline in the dispatch prompt (round 1, Sept 2026):** the
proposal that introduced this suggested the parent write the derived set to a
file and hand workers the path. On the tiers where a worker is a separate
container that path resolves to nothing, and the failure is silent — the worker
falls back to the `AGENTS.md` list the derivation existed to replace and reports
success. The general form is `swarm`'s: nothing a dispatcher computed
may reach a worker as a reference.

**Why an incomplete gate report is a rejection rather than a note:** it is the
cheapest moment a skipped check can be caught. The alternative is CI finding it,
which costs a round, or nothing finding it, which costs a merge. (It was a PR-body
table until issue #158; `rules/authored-write-form-notes.md` says why it moved.) The report says
which checks ran and is not a claim that they passed — that is CI on the pushed
head, kept separate because a worker reported all gates green on a PR already
failing `format:check`.

**Why this section names no source for the derivation (round 2):** it did, and
the source was the workflow file — a paraphrase of the rule `implement-issue-core`
was in the middle of correcting, sitting one skill away from the correction. It
now points at the owning section instead of restating it, which is the only shape
that cannot drift.

**The incident behind branch protection (step 7):** a worker dispatched with its `outcome_branch` correctly set pushed four commits of unreviewed implementation straight to the repository's default branch, noticed, and self-reverted — the tree was recovered exactly, the default branch's history permanently carries the five extra commits, and a sibling worker briefly cut its PR from the polluted base. The branch assignment does not imply the prohibition; it has to be stated.

**The incident behind the question countermand (step 8):** a worker dispatched for one issue called `AskUserQuestion` four minutes in and held its container some twenty minutes until a check-in caught it, with nothing durable pushed, so the whole run was wasted.

**Why the report requirement is a subtraction (step 11):** four review rounds against an enumerated list each found a different item missing from it, and every one of them was something a **clean** run still has to say. An enumeration written by someone thinking about failures keeps quietly scoping itself to exceptions, and the omissions are invisible precisely when nothing went wrong. The four that were lost this way, kept as the shape to watch for rather than as the list:

- **every dependency checked, with its class and how it resolved** — the matches too, not only the misses. Outcomes requires the run to record verified edges and has no other source for them, so a fully-checked set otherwise reads identically to one nobody checked;
- **whether the completeness of the blocker set was backed** — by a caller's proven complete set, or by a known-true case read and observed — or left unproven, and on what boundary. A `PR_OPEN` with an empty blocker list and a proof behind it, and one with an empty blocker list because nothing was visible, are different claims that look the same;
- **the transport tier and a non-secret credential identity** — account and scopes, never the credential. Outcomes branches on whether the worker's identity differs from the run's, because a mismatch under a *different* credential shows one of the two views is partial while the same mismatch under the *same* credential merely repeats a read already made;
- the criteria it could not satisfy, the guarantees it narrowed, the sources that disagreed.

**Why a dispatch prompt never claims a decision was authorised (Sept 2026):** "The orchestrator has authorised…" is exactly the shape of an injected instruction, and a Sonnet worker right to distrust it refused; the same task worded neutrally, pointing at the ruling's record, went through.

## Confirming a trigger that is a skill invocation

The notes on confirming a trigger that is a skill invocation, and why a declined pass is completed, moved to `rules/review-trigger-notes.md` with the confirmation step (#144).

The note on why the per-PR record holds its review lines per convention moved to `supervise-prs/NOTES.md` (#144).

## Shared environment

**Why workers are told the environment hypothesis comes first (Sept 2026):** the repository that produced this had already absorbed the lesson — a script ensures the service is up before the suite, and its `CLAUDE.md` documents the tell. A worker has none of that context. It sees thirty unrelated files red, concludes its own change broke everything, and either thrashes against a codebase that is fine or returns `FAILED` on one. The instruction costs a sentence in the dispatch prompt.

**Why raising the hypothesis is separated from confirming it (round 1):** a PR that changes connection configuration or client setup produces refused connections across every unrelated test file, with the same error and the same breadth as a dead service. Treating the signature as conclusive hands that PR a free pass on exactly the failure it caused. The confirmation lives in `repair-pr` rather than here because that is where a pass has the diff and the branch comparison in front of it.

## Parent supervision loop

**Why step 16 states the override (#154):** `supervise-prs` arms each PR's subscription, but runs here with `wait owner = caller`, so every wake those subscriptions produce lands in this loop — and the first one carries the platform's drive-to-green posture. A session that has been compacted since adoption has this contract and the wake's text in view, not `supervise-prs`'s; stating the override where this loop waits is what puts it beside the posture at the moment it is read. The rule and its reasoning are `rules/platform-pr-posture.md` and its notes.

**Why the trigger sweep detects rather than deletes.** The incident prompt proposed deleting any trigger bound to a worker session on each cycle. This file already records that deleting a leaked session's trigger caused it to arm a replacement one minute later: the session arms the wake, so only archiving stops it. With finished sessions now archived on a match, archival kills their triggers anyway. A trigger on a worker still working is a finding about the dispatch prompt, not something to fight.

**The seven unreclaimable sessions:** doing the reconciliation by hand found seven `IDLE` sessions belonging to a *different* orchestrator run, checked out on repositories outside the recovering session's GitHub scope — so whether their branches were ever pushed was unreadable from there. Those are report-never-reclaim on ownership alone. Without that branch, a forcing function on live sessions either wedges a clean run behind someone else's leak or teaches runs to archive sessions the safety rules protect. **"Cannot verify" splits by ownership, though** (a review correction to #50's original framing): an unverifiable session belonging to *another* run is excluded from settlement like any other not-mine session, but an unverifiable session *this run created* still blocks settlement as `NEEDS_USER` — it is this run's cost and possibly this run's armed wake, and settling over it would recreate the leak with a documented excuse. Safety still forbids archiving it unverified; the human resolves the standoff. (Since the 2026-09-23 ruling, above, *unverifiable* no longer means *uninspectable worktree*: a session this run created is verified by its remote state, and only one the releasable test fails — a mismatch — is held this way.)

## Every read is a snapshot

The notes on why every read is a snapshot moved to `rules/establish-do-not-assume-notes.md` with the rule (#144).

## Draft state

The reasoning for the shared rule this section applies — the forge-timeline read, the scoped three-state reference, when the convention is read, and why the repository's convention wins — moved with the rule to `rules/draft-state-notes.md` (#138). What stays here is about what stays here.

The note on why the trigger comment stays unconditional moved to `supervise-prs/NOTES.md`, *Draft state* (#144).

## Arming the wait when nothing is in flight

**Why the settle trigger is conditioned on attendance (round 1, Sept 2026):** written as an unconditional trigger it ran the settle sequence from every quiet unattended wake — and `settle-outstanding-decisions` declines there for want of anybody to ask, while step 8 forbids re-deriving settled state that has not changed. So each wake would recompute a summary, a walkthrough and a ranking, ask nobody, change nothing, and do it again until the wake budget died. The reporting half is what has to be unconditional; the sequence needs either a person or a real delta.

**Why a quiet wake still reports the owner's queue (Sept 2026):** the unproductive-wake machinery is built entirely around *durable* state, and an outstanding `DECISION` is not durable state — it is a thing that does not change, which is precisely why the backoff cannot see it. A run can be correct on every wake, report no delta, back off to four-hourly, and never once say that three decisions have been sitting with the owner the whole time. The counts ride the same lengthening cadence, so they cost nothing extra and they cannot go silent. Making quiescence-with-open-decisions a settle trigger is the other half: a run whose only remaining movement needs an answer nobody has asked for is not waiting for anything, and backing off around it is waiting for the wrong thing.

The notes on what two unbounded check-ins cost, why a subscription is not free, and why the count lives in the wake's prompt moved to `rules/wake-budget-notes.md` with the budget (#144).

## Progress / checkpoint output

**Why the gate condition is named per PR (Sept 2026):** a run reported its tranche as "awaiting merge authorisation" for four days and raised it to the owner three times. Both repositories had carried `"auto-merge": true` for a week; what actually held every PR was invariant 12's other conjunct, three outstanding `DECISION` items anywhere in the tranche. Nothing merged, which was correct, and every account of why was wrong. "Awaiting merge" is compatible with every condition and with none, so it cannot be checked against the truth by the owner reading it or by the run writing it — naming the first unmet condition makes the error visible on day one to both.

**Why the third state is narrow (round 2):** written as "report it as not-yet-evaluated, naming anything already known to hold it" it said two things at once, and a reader taking the second clause would emit `gate not yet evaluated` over a PR that is red — losing an actionable, currently-true blocker behind a hedge. Only `mergeable` genuinely needs the summary's inputs. A known condition is true before the summary and the summary cannot make it untrue, so it is named.

**Why there is a third state and not two (round 1, Sept 2026):** the first version gave every unmerged PR either a named unmet condition or `mergeable`, and the parent loop emits this block on every cycle — including cycles before `summarize-tranche` has produced the gate's `DECISION` and `MERGE_RISK` inputs. A clean-looking PR there has neither a known unmet condition nor the evidence to be called mergeable, and reporting it mergeable would be the same false account this section exists to stop, with the sign flipped. `gate not yet evaluated` says which of the three it is.

**Why the two merge routes are distinguished here:** the run collapsed `merge-stack`'s user authorisation with the gate's repository opt-in and defaulted to asking. That is the same failure *Autonomy and interactive prompts* names at the dispatch end — a run that asks before doing the thing it promised — arriving at the merge end, where the document had not named it.

**Why the field is reachability of the head commit and not branch existence (round 1, Sept 2026; named `reachability` since, and defined under `swarm`, *Releasing a worker*):** a branch-exists field plus a clean worktree reports the `clean | local ahead` case as healthy — the worker pushed once, committed more since, staged nothing — which `Checkpoint compliance` already names as the unpushed-commit case. That is the same cheap-half mistake as testing a push by whether the branch exists, arriving in the diagnostic that was supposed to catch it. What discriminates is the head: local against remote where the worktree is reachable, and where it is not, the remote head with how long since it last advanced, which says the same thing from outside.

**Why the live-session report is per session and not a count (Sept 2026):** "8 live sessions" is compatible with eight warm containers mid-turn and with eight containers holding a month of unpushed work, and the check exists entirely to tell those apart. The session that prompted this had been `IDLE` and unarchived for four weeks, chartered for a single issue — and it surfaced because the owner asked whether it was ours, not because any count moved. Three fields settle it: charter, **reachability** of the worker's head commit — not whether a branch exists, per the paragraph above — and staged files. An unread field is named as unread rather than omitted, because omission reads as clean.

**The convention that lapsed:** both leaking runs used to print the state block mid-run — while the fan-out made the numbers interesting — and stopped once they narrowed to a one-PR supervision tail. Nothing removed the block; nothing had ever required it. The tail is the long part of a run and the part a compaction lands in, so both runs reported their worker-session count exactly zero times, and the line that would have exposed the leak ("N created / N archived") never appeared. That is why emission is now a numbered loop step with an actor and a moment rather than an example.

**Why the per-PR record carries the session id:** the recovery that cleaned up the leaks had to match sessions to PRs by fuzzy-matching session titles with a script over a truncated tool result. A session id and archived flag on the record the run already keeps makes the reconciliation a lookup.

## PR promotion and central supervision

**Why the charter lives in the PR body and not only in the per-PR block (round 1, Sept 2026):** invariant 1 classifies that block as a cache, so a run recording the charter only there loses it at the session boundary — and a resumed run would rebuild one from the issue as it now stands, after the diff expanded and quite possibly after the issue was edited to match. That reconstruction agrees with anything, which is the same defect as recording it late. The body is durable, is written at creation anyway, and is where the comparison already had to look. Where no charter line is recoverable, the check is reported **unavailable** rather than performed against a guess: an unavailable check is a known blind spot, a check against a reconstructed charter is a clean result that means nothing.

**Why the charter is recorded at creation and not derived later (Sept 2026):** a charter written after the rounds would be written from the diff, and could only ever agree with it. Recorded at creation, from the issue, it is the one description of the PR that predates every fix — which is what makes the comparison mean anything.

**Why the ratchet needs a rule at all, when every round was correct:** it is the failure mode with no wrong step. The reviewer finds problems in what it is shown; each fix enlarges what it is shown; six rounds later a one-clause guard carries a clock-synchronisation module. Nothing in the document bounded one PR's diff — invariant 3 bounds the run, the frontier rule bounds what starts, dispatch authority bounds what may be worked on — so the growth happened in the one place nobody was counting. The predicate is deliberately about the *kind* of thing added rather than its size: a new module, a new build or CI step, a new cross-cutting invariant. Those are the three shapes the observed growth took, and all three are decisions about the shape of the codebase rather than fixes to a finding.

**Why the body comparison is unconditional in both consumers (round 2, Sept 2026):** the first fix made `implement-issue`'s read conditional on the drift flag, which gave the flag a job no carrier supported — that skill records selected fields from each repair return and checkpoints a fixed schema, so a flag raised in round two is gone by the time the gate is evaluated after a checkpoint or a re-entry, and a conditional read would pass exactly when the state was lost. The flag stays as a prompt and never as a precondition. The unconditional read costs one look at a body the consumer already has, against a class of failure that is invisible when it happens.

**Why `repair-pr` reports the body drift instead of fixing it:** the repair pass is the only party that knows — it made the change with the body's claim in front of it, while a caller sees a head SHA — but it is the wrong party to act, because a PR with four rounds left does not need its body correct yet and editing it each round spends a write on text about to change again. Reporting it makes the knowledge travel; the caller holds the reconciliation until the body is about to be read. Stating it only here left the standalone `implement-issue` path able to reach its own merge gate with a round-0 body, since that consumer never reads this section.

**Why the body re-read is placed before promote/merge rather than in the repair pass:** a repair that will be followed by four more rounds does not need its body correct yet, and requiring it each round spends a write per round on text that is about to change again. The last moment before a human is asked to read it is where it is both cheap and necessary — and the charter comparison is already open there.

The notes on why supervisors are counted rather than mechanisms, and what a second monitoring loop costs, moved to `supervise-prs/NOTES.md` (#144).

## Adopting a PR is three things, not one

The notes on adoption — why `deferred` is recorded, why a correct step produced no review, and why the trigger is re-checked at adoption — moved to `supervise-prs/NOTES.md`, *Adopt* (#144).

The note on why the post-arming read reconciles rather than samples moved to `rules/watch-and-read-notes.md` (#144).

## Event handling

The notes on the arming read, the 18:20Z incident behind the no-change preflight, and the polling bound moved to `rules/watch-and-read-notes.md` with the rules (#144).

## API budget and read discipline

The notes on the allowance incident, read discipline and deferral moved to `rules/watch-and-read-notes.md`, and those on collapsing the wake's two counters into one to `rules/wake-budget-notes.md`, with the rules (#144).

## CI/review repair

The note on why the remaining budget is read off the block at dispatch moved to `rules/repair-rounds-notes.md` with the rule it explains (#140), as did the one on the escalation trigger's observed case. What *Unhandled feedback* means moved to `rules/review-feedback.md` in the same change.

The note on why a producer merge's red is expected-red moved to `rules/ci-attribution-notes.md` with the classification (#144); the refresh-PR remedy it describes is still this skill's.

## A settle finding is the third repair shape

The argument for `finding-repair-cycles` being its own counter moved to `rules/repair-rounds-notes.md` with the rule it explains (#140).

**Why a finding whose repair returned `needs-user` is never handed back (#148):** once a `needs-user` PR with its item raised settles, the next settle's summary reads the same durable evidence and re-derives the same `IN_FLIGHT_FIX`. A `FAILED` pass that pushed nothing consumes no finding cycle, so without this the run loops summary → repair → settle without bound — the loop `implement-issue`'s re-entry rule closes for its one PR. The item carries the finding to the owner instead, and `summarize-tranche` classes it a `DECISION`. An owner's "try again" is not that loop: it is a recorded ruling, new evidence, and it takes the finding path within the finding budget. Where that budget is spent too, the ruling cannot move the PR on the run's authority, since policy is read once at preflight, so the report names the re-invocation that would rather than promising a resume that will not come (#149 review).

## Frontier advance on merge

**Why the resumed dispatch needs the escalation most:** nobody is watching it — the run resumed on an event, not on a human's attention — and the merge that triggered it is itself the event that makes a stale cross-tranche dependency look satisfied. The preflight at the selected mode is the only check between that illusion and a dispatched worker.

**Why reconciliation is per batch of merge events:** a landing stack delivers one event per PR, and reconciling on each re-reads the same graph as many times as the stack is deep. Draining first and reconciling once is the whole saving; there is deliberately no debounce timer, because delaying the frontier advance to batch better trades correctness for cost in the direction this skill does not accept. Events genuinely minutes apart each get their own pass, and that is correct — the burst is the case this was written for.

**Why the validator is handed the prior graph:** re-enumerating hierarchy, project structure and every dependency edge is among the most expensive reads the run makes, and re-running it per advance is how a landing stack pays for the same graph repeatedly. The correctness rule is untouched — the preflight still runs, at the escalated mode — what changes is that it verifies a delta it was given rather than rebuilding state the run already holds validated.

**What crediting a close would do:** a recompute that treats close like merge sees a dependency-free node and dispatches a fresh worker for the work a human just declined — recreating the PR they closed and spending budget to do it.

## How a worker's report actually reaches you

**The truncation case:** a worker whose credential reached edges the parent's cannot may have found three hidden blockers and had room to summarise one. If that one happens to be an edge the parent already holds, a reconcile-and-stop ends the decision on the strength of a line that had room for one — and the other two are never learned while every sibling stays scheduled against the same truncated graph.

**The redispatch loop:** a worker blocks on a native edge the parent's own credential cannot see. The parent's re-read reproduces the blind spot exactly and returns looking like confirmation: it reconstructs the same short DAG, concludes the issue is ready, and redispatches it — and every retry does the same, because nothing in the loop can see what stopped the worker. This is why absent inputs resolve to the last branch of the ordered decision: falling through to the cheap outcome is precisely what resumes the loop.

**Why the parent writes the record (the inversion argument):** *record each established blocker, naming how it was verified* — and establishing is the parent's job, needing a visibility proof the worker does not hold. A worker writing unclassified findings onto an issue was always the parent's duty performed by the wrong party. Every failure that followed from it — the next dispatch re-adopting a rejected edge, validation's preflight reintroducing it, dependency normalization promoting it into native metadata where nothing later re-examines it — followed from that inversion, not from any detail of how the writing was labelled.

**What the routing costs, stated plainly:** on any terminal outcome without a PR the worker's verbatim reasoning compresses to a line, and the rest goes with its transcript. That is a real loss. It is the right trade because the parent cannot adopt that reasoning unclassified in any case — it has to re-establish the finding before recording it — and a line saying *where to look* is what it actually needs in order to start.

**How the three issue-comment readers were found:** one at a time, each after the previous fix looked complete — which is why the table in the contract enumerates them and why the marker is a property, not a patch in three files.

## Checkpoint compliance

**The capture itself, and the reasoning for it, moved to `swarm` (#136):** the defect history of the capture sequence, why validation precedes the push, why one ref per branch, and why the branch name is encoded are in `swarm` NOTES, *Checkpoint compliance*, beside the section and the script they explain. What stays here is the reasoning for the ender this skill keeps.

**Why the four-state ref-ender rule is enumerated:** the rule was built one case at a time and each missing case left a ref with no ender, which invariant 12 then converts into a PR that can never merge. A two-state copy that lived in Lost worker recovery covered only open and merged, so a lost worker with no PR or a closed one had its capture merged into the branch and its ref neither verified nor deleted.

## Cross-branch artifact collisions

**Why a sequence collision is expected at dispatch rather than only detected after (Sept 2026):** detection was already here, and it fires only once the PRs exist, by which point every one of them is green. Four workers each took the next free migration number from the same base and each passed its migration-consistency check, because each was consistent with the base in isolation. The collision was knowable the moment more than one schema-touching issue was dispatched. The renumbers are strictly sequential because the snapshots chain by predecessor id, so the second has to be regenerated against a schema including the first — which is also why they cannot be batched. The reviewed body is kept verbatim because it is the thing review read: regenerating it risks an expression index or partial `WHERE` coming back different, and keeping it is what keeps any re-review down to the identity files.

**The `NEEDS_USER` for merge order, first left unchanged and then narrowed by the owner's ruling of 2026-09-24:** the owner is asked only where the colliding migrations interact. Independent ones follow the ranking, since any order works and asking spent the owner's attention on a question with no answer worth giving. The original reasoning, superseded by that ruling and kept for the record: For independent migrations the ordering question arguably has no answer worth asking — any order works and `plan-merge-order` already ranks. Whether to stop asking it is a policy change, and the finding that proposed it was not an owner ruling, so it is left for the owner.

**Why the third collision kind is detected by running rather than by reading (Sept 2026):** the first two kinds leave a trace in the diffs — a shared added path, a shared claimed artifact — so a comparison can find them. The third leaves nothing: one branch renamed a string, another added code depending on it by name, no line in common, git merged cleanly and both PRs were green against a base containing neither change. The only artefact holding both changes at once is the merged tree, so the check is to build that tree and run the suite over it. There is no cheaper detector, because there is no signal to detect.

**Why the third kind gets its own remedy (round 1, Sept 2026):** it was first written into a section whose resolution rule routes collisions to a merge-order decision, and ordering cannot resolve this one — whichever of the two names merges first, the final tree is identical and broken. Surfacing it for an ordering call spends the owner's decision on a question with no answer. One branch has to change, and the re-run afterwards is not ceremony: a repair that fixes one reference and misses another produces exactly the clean diffs that hid it the first time.

**Why the input set is every open branch and not the run's members:** the check already existed in an observed tranche, over the branches it had dispatched, and it caught a genuine conflict. It missed this one because the colliding branch belonged to a concurrently running track. A run's own graph is not the repository. Naming the integrated branches in the output is what makes a partial set legible as partial — otherwise a clean result over the wrong set is indistinguishable from a clean result.

## Performing the renumber

**The worked example behind the generator rule:** a Drizzle migration's identity lives in five places — the `.sql` filename, the journal's `idx`, `tag` and `when`, and the snapshot's `id`/`prevId` chain. A hand-rename that updates four and misses `when` makes the migration **silently skipped**: no error, no log, green CI, and the schema change never applies. Renumbering `0011` to `0014` in `crypto-scanner-api` was exactly this; the repair was regenerating through `pnpm db:generate` and splicing the hand-written backfill back in. A regenerated artifact that silently drops hand-written content is the same failure with the sign flipped, hence splice-and-re-verify.

## Outcomes

**Why the verified-availability record must never become a skip:** the worker's dependency precondition runs on every dispatch regardless, and it would be a contradiction to build a record whose purpose was to let a caller skip the very check that produced it. The record informs restarts; it exempts nothing.

**Why shipping silently against a coverage gap is the failure mode:** a worker that finds the capability absent and ships anyway — disabled UI, a stubbed call, an acceptance criterion quietly dropped — has produced a permanently partial deliverable and left the prerequisite invisible. The missing capability is recoverable; the invisibility is what is not.

**Why a closed-over coverage finding gets no further attention:** the prerequisite sits open beside an issue the tracker calls complete — nothing routine ever re-examines a `DONE` issue, so the gap persists exactly as long as nobody happens to look.

**Why the mixed-case asymmetry must not pass as a difference in reporting detail:** a PR from a worker that could re-read carries a check yours did not; a PR from a worker that could not carries your preflight and nothing since. Accepting both on the same terms is how a blocker added mid-run reaches `main`, and it is invisible from either side alone — which is why `implement-issue-core` has the worker say so explicitly, and why the answering duty sits with the parent.

**Why the dispatch gate and the outcome duty must not be confused:** they read almost identically and permit opposite things. Carrying unproven completeness forward is the rule at the *dispatch* gate, where knowing an unwritten blocker is undetectable is the thing you weigh; by the time an outcome is in front of you it is a PR to reconcile against a fresh read or hold, and re-deciding dispatch there would let the PR through on the stale preflight the decision was taken from.

**The time axis as the second proxy correction:** having fixed "different transport" into "different credential" earlier in this design, the same correction applies along the time axis — two reads that differ may differ because the graph changed in between. Independence and contemporaneity are separate conditions.

**The proxy ladder, and what corroboration actually establishes:** distinct transport, then distinct credential, then distinct moment were each offered as a stand-in for independent visibility and each failed, because a proxy can always coincide with the thing it is standing in for — ask for the property the conclusion needs, visibility, proven. And when a preflight warning and a worker report coincide, the reading it invites is backwards: two actors agreeing does not make the prose edge more likely real (they read the same prose); it makes a *partial view* less likely — a different and more useful conclusion. Correlating costs nothing, since the warning is already in hand.

## Settled tranche

**Why a held, surfaced worker does not block settlement (#66, review round one on swarm's #145):** `swarm`, *Blocked workers*, now holds a worker on the owner's authority in three cases — a permission request, a blocked worker whose checkout cannot be reached, and an unclosed mismatch — and before this the in-flight and live-session conditions both counted it, so one permission prompt kept an entire tranche from settling: no summary, no walkthrough, no ranking, and no merge gate for PRs that had nothing to do with it. That is the run waiting on the owner without having asked, which is what the settle sequence exists to end. (The gate still reads the held worker's `NEEDS_USER` item tranche-wide while it is outstanding, so what settling buys the other PRs is the summary, the walkthrough and the ranking; their merge still waits on the item, #148, until the hold ends and retires it, #151.) The fix follows the reserved-thread precedent: once the hold is raised as a `NEEDS_USER` item it is surfaced, it holds its own work unit, and the rest of the tranche settles. The live-session condition keeps its force for every other session, because its purpose — making a skipped release detectable — is met here by naming the held session as alive in every report, not by blocking. The check-in watches the held session, and its resuming is a delta and un-settles the run, so the exception cannot turn into a worker nobody is watching.

**Why a `needs-user` PR with its question raised is surfaced, and why the set is stated once (#148, owner's ruling 2026-09-29):** the predicate carried "no open PR is `NEEDS_USER`" as its own bullet while the paragraph under the un-settle table said an unfinished PR could be finished "or surfaced as `NEEDS_USER`" before ranking — one text refusing to settle over the PR, the other settling over it. #147 kept the bullet because no ruling covered the change. The owner's ruling: the question raised as an item is surfaced — it holds that PR's merge, never settlement — because the owner is asked at the walkthrough, and a run that will not settle until the owner answers never reaches the step that asks them. That made three members of one set, each written into its own bullet with its own "exactly as a reserved thread does" (the held worker from #145, `held: check` from #147, and now this), so the set is stated once under the predicate and the bullets cite it; a fourth member is a line in the list, not a new bullet with its own wording to drift. The older paragraph was a summary of the predicate serving no decision point of its own, and is deleted rather than reconciled.

**Why a held worker's item leaves the set by retirement, not by the walkthrough (#151):** with the gate reading items tranche-wide (#148), a held worker's `NEEDS_USER` item held every PR in the tranche, and nothing retired it once the owner granted the permission — the walkthrough records rulings, and a grant is an owner action item, not one. So `swarm`, *Blocked workers*, now retires the item itself on observing the worker resume, be released or be redispatched, and this skill cites that rule at the three places that read the item: the surfaced-set member, the check-in's re-read, and the reply watch, whose "a reply releases dispatch only" would otherwise have kept a retired item outstanding until an attended walkthrough that has nothing to rule on. Review round one on #153 added two things. An archive with no redispatch leaves the item restated to the work unit as an ordinary item, which this skill's reply watch and walkthrough retire like any other, so the exception stops at it and the unit stays a member so its dependents are still reported as waiting. And retirement records are the run's own writes, so the check-in carries their ids and the reply watch filters them, exactly as it does every other write the run makes under the owner's account.

**Why a settle with work waiting behind a surfaced PR is taken and reported partial (the same ruling's refinement):** the alternative — holding the settle until the dependents can run — waits on the very answer the settle exists to obtain. So the run settles early, and is explicit that it has not finished: the report names, per item, the planned work behind it. Nothing new is needed for the continuation: a code-changing ruling is already a finding repair that un-settles the run, a charter release already re-adopts the head, and a merge already advances the frontier, so the ruling's "the run un-settles and continues" is those rules running, cited rather than restated.

**Why the predicate admits budget-held READY work (Sept 2026):** a run whose only remaining work is held by a budget can do nothing, and a predicate demanding an empty READY set would leave it unable to settle and therefore unable to reach the merges that release the budget. Settled means nothing is dispatchable *now*, not that nothing remains. A future editor reading "settled = nothing can start" is the reason this is written down.
