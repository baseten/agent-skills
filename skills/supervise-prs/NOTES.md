# supervise-prs — design notes

Companion to `SKILL.md`. That file is the contract; this one holds the reasoning, incident history, and answers to "why not the obvious other reading?" — keyed by the contract's section names. Nothing here overrides the contract.

Extracted in #144 from the three skills that each supervised PRs in their own words — `backlog-orchestrator` (about nine thousand words of it), `implement-issue`'s *Phase 2* and `npm-dependency-upgrade-orchestrator`'s *Supervise*. Entries moved here from those skills' notes keep their original wording; "the run", "the parent" and "this skill" in them are the skill they were written for, as it stood then.

## Supervise PRs

**Why a skill and not a rule (#144):** supervision is an active loop that dispatches, spends budgets and returns outcomes — the same shape as `swarm`, which callers invoke and hand inputs to. The stateless tests that fell out of it went to rules in #146 (`ci-and-review-verdicts`, `ci-attribution`, `watch-and-read`, `wake-budget`); what is left is procedure, and procedure a caller invokes is a skill. A fix made in one of the three copies reached neither of the other two: `implement-issue` re-triggered into a refused provider, lacked the post-arming read and the one-mutator rule, and settled on a predicate that could never be met with a refused round; the npm orchestrator had the only definition of green. One copy removes that class of drift.

**Why the override is stated at the top as well as at *Adopt* (#154):** the posture arrives on the first wake after subscribing, and a session can reach a wake — after a compaction, or in a caller's loop — without having re-read *Adopt*. The top of the skill is what a reader has in view before any section, so the override is stated there once, briefly, and cited to the shared rule that holds it; the rule's reasoning, and why it is a shared rule rather than a section here, is `rules/platform-pr-posture-notes.md`.

**Why it never merges:** merging is gated, and the gates differ by caller — `settle-and-merge`'s for waves and single issues, the npm orchestrator's by kind. A supervisor that merged would need to hold every gate's conditions, which is what the gates were extracted to avoid.

## Inputs

**Why inputs are values and never pointers (#139's rule, applied here):** a skill that must read its caller to act has an upward pointer by another route, and the caller's text is not installed beside it. The head check is the sharpest case: `backlog-orchestrator`'s chartered-scope comparison is passed as the check itself, stated in full, the way `settle-and-merge` takes an integration check "with the check itself" — so this skill can run it without knowing whose it is.

**Why absent budgets are zero (#144, owner's ruling B16):** this skill never reads the policy file, so a person invoking it bare either gets no pushes or gets pushes their repository's policy may have forbidden — the built-in 2 would override a committed 0 on the strength of an invocation that never mentioned the key. A repair is authority to push to someone's branch, and an unmentioned authority was not granted: the same reading as an unmentioned `auto-merge`. Classify-only still classifies and drafts, so nothing is lost but the pushes, and the report says why.

**Why emission cadence is an input (#144, B3):** `backlog-orchestrator` prints every record every cycle, because a count that re-enters the transcript survives a compaction; the npm orchestrator emits only changes, because re-emitting unchanged state trains its reader to ignore it. Both are right for their reader, and neither is this skill's to decide.

## The per-PR record

**Why the per-PR block holds its review lines per convention.** A routed repository can owe two independent reviews on one PR, and a merge gate asks whether *every* round the routing requires has completed. A single-valued block cannot express "one of two", so the gate would read the first completion as the answer and open over a review still pending. This is the same defect the invariant's own parenthetical had, found in the same pass.

## Adopt

**Why `deferred` is a recorded value rather than an inference (round 1, Sept 2026):** the first version classified every `pending` trigger as untriggered and issued it, which overrode the caller's explicit deferral — a WIP draft would get its round 1 at the moment the parent adopted it. There is no way to tell a deliberate deferral from an unfinished one by looking at the PR: both have no trigger. So the deferral writes itself down when it is made, and everything else that looks like it is treated as unfinished. That direction is chosen: an over-eager trigger on a WIP draft costs a review round, and a missed one costs the review.

**Why a step that everyone performed correctly produced no review at all:** the worker is told to stop once the PR is pushed and open, which is right — it is what stops a worker becoming a second orchestrator. The repository opens feature PRs as drafts, which is also right. The two together mean the PR reaches its final state without anything having asked for a review, and no part of the run is in a position to notice: the worker returned its terminal outcome and was released, the parent recorded `PR_OPEN`, CI ran and reported. Four PRs sat for about seven hours with zero reviews and zero comments, one of them red within minutes of opening. Nothing failed. The section exists because the failure has no failure signal of its own — the only place left that looks at the PR is the parent's adoption, so that is where the check has to be.

**Why the parent re-checks a trigger `create-pr` owns:** not because the trigger moved. A worker can return with the PR open and the trigger not yet issued — linkage verification and the trigger both run after creation, so `FAILED` and `NEEDS_USER` both arrive with a usable PR — and once that worker is released nobody will ever go back for it. Reading the `review trigger` line at adoption costs one lookup against a field the per-PR block already carries.

**Why an unrecoverable counter is spent, not zero (#144, owner's ruling B12):** every caller's per-PR record is a cache, and until this change no contract said how its cycle counts were recovered after a restart — so the implicit reading of a lost cache was zero, which hands a PR the budget its owner already spent. The PR itself carries most of what is needed — repair reports, repair commits, trigger comments, reviewer answers, settlement records — and where it does not, failing closed costs one owner decision rather than an unbounded run.

**Why a rewrite is detected by trailer, not by force-push (#144 round 2):** a rebase or restack rewrites every SHA and keeps every commit, so a force-push alone is no evidence a pass was lost; what is evidence is a trailered commit the timeline shows was pushed and the branch no longer carries. Counting distinct pass ids rather than commits keeps a per-concern review pass from counting as several. PRs repaired before the trailers existed rebuild to 0 — a one-time fail-open recorded in `repair-pr/NOTES.md`.

**Why a rewrite that lost one type's commit taints every counter (#148):** the first statement said a rewritten history recovers `unknown` without saying whether that meant every counter or only the lost commit's type, and eval 15's scenario — a lost `ci` commit beside surviving `review` ones — was graded as though the review count and the escalation count survived intact, while round 12's reader took the rule at its word and spent them all. The reader was right. The lost commit is the one the timeline happened to still show; a rewrite that removed it could have removed others the timeline does not show, of any type and on any model, so the surviving trailers bound the count from below and no more. Reading a lower bound as the count is the zero-reading of a lost cache (B12) in a smaller form. The cost is the same one B12 accepted — an owner decision where the run might have had budget left — and a rewrite that keeps every trailered commit, a rebase or restack, costs nothing.

## One PR, one supervisor

**Why the rule counts supervisors and not mechanisms:** written as "never two monitoring loops over one PR" it contradicted the section that requires a subscription *and* a bounded check-in over each PR — two mechanisms, one owner, which is the intended shape rather than a violation of it. What is actually forbidden is a second party watching: a worker that never stopped reading, or a supervision step reading on its own instead of consuming the parent's pass.

**What the second monitoring loop costs:** the duplicate pass spends API budget on every cycle and decides nothing the first pass did not — it re-reads the same PR to reach the same conclusion, and where it does not, the two loops disagree about a PR one of them is mid-repair on. The caller's lifecycle is written out as a sequence (in `backlog-orchestrator`, its diagram of dispatch, adoption and supervision) because the failure is never a decision to run two loops; it is a worker that never stopped reading, or a supervision step that reads on its own rather than consuming the parent's pass.

**Why the platform's own auto-merge is called out:** it is a forge setting, not the `auto-merge` policy key, and it merges on CI state alone — outside the gate, whatever this run's policy resolved to. Its merges are not outcomes this skill produced.

## CI failure

**Why the head filter comes before step 1 (#154):** two failure wakes arrived for a commit that was no longer the head, whose end-to-end step had failed on purpose with "shards result: cancelled" because concurrency cancelled the superseded run. Read as failures of this PR, each would have drawn a repair pass against code that was already replaced, spent a cycle and — under the platform's posture — a comment. Retrieving context, attributing and budgeting all come after the filter because each of them is a cost the event did not earn. The filter itself is `rules/ci-and-review-verdicts.md`'s, since every skill that reads a verdict needs it.

## Deferred CI

**Why CI waits for quiescence and then runs once (#179, owner-approved spec):** orchestrated runs started 52 PR runs in one morning on one repository, about a month's allowance — every review-repair push ran CI, giving four to seven runs per PR, and merge-fix and update-branch pushes ran it again. Review does not need CI to have run, so under the opt-in every push this workflow makes carries `[skip ci]` and the run that matters is the one after the PR has stopped changing. **The trigger is quiescence, not a clean round (blind audit of #181):** waiting for a clean round stranded tokened heads with no reviewer, a refused or unavailable round, a reviewer that reviews only on open, and an unresolved held-reply thread, which reads as not clean. Quiescence asks only whether anything is still due to change the head; a held reply or a reserved question cannot, and still holds the merge gate on its own. The trigger is a base update because its merge commit carries no token, and dispatch where the branch is already current; an empty commit or a close-and-reopen would put noise in the history or the timeline for a run the forge can be asked for directly.

**Why the last push before the PR carries the token too (#181, coordinator's ruling):** the PR-opened event runs CI on whatever head the PR opens on, so without it every PR spent one run before review had said anything — the run the key exists to defer.

**Why a skipped head is its own state:** a head with no run reads, to every existing rule, as an empty rollup — not green, and easy to misread as missing or as a failure to repair. Naming it stops a pass being dispatched against CI that was deliberately not run, and keeps the PR `waiting` rather than `finished`.

**Why the repository's properties are detected, and why the key then does nothing:** a forge that ignores the token runs CI on every push anyway. A rebase merge lands the PR's tokened commits on the base unchanged, so base CI would skip; where rebase is the only method allowed, no merge message can prevent that (#181, coordinator's ruling). None is knowable from the provider's name (`rules/establish-do-not-assume.md`), so each is read or observed once per repository, and where any is missing the run reports it rather than half-applying the key.

**Why dispatchability is a per-PR condition of one path, not a repository precondition (owner's ruling, after #181):** as a precondition it switched the key off wherever CI lacked `workflow_dispatch` — no tokens, every push running CI — though only a branch already level with its base needs a dispatch; a branch behind its base gets its run from the update's merge commit. Gating to `pull_request` events matters only to a dispatch, so it moved with it. A level PR with nothing dispatchable is held until the base moves rather than pushed an empty commit, which the posture forbids; in an active repository that is soon. It is surfaced, not a stall, because nothing the run does moves it: a caller waiting it out would spend its monitoring cap and wake budget learning nothing. The suggestion to add the trigger is made once per repository so a wave of held PRs does not repeat it, and the edit stays the owner's under the workflow-edit ban. A dispatch skips path filters, so dispatching every required-check workflow would run, and spend, the ones the PR's files would never have started.

## Review feedback

**Why this skill never roots a review thread on the PR it supervises:** the actionability discriminator is thread-rootness — a thread the invoking user rooted is their instruction — and on the degraded posting-identity path this run's own comments carry the invoking user's login. A run-authored root comment would be indistinguishable from an instruction to itself, silently breaking the test. Replying in threads and posting timeline comments keeps the discriminator true by construction.

**Why a reserved thread blocks the gate but not settlement:** the run cannot be required to resolve what policy forbids it touching, so it can still finish and return — but the thread is an unresolved actionable finding wherever that concept is consumed, so its round is not clean and the merge gate stays shut.

## Draft state

**Why the trigger comment stayed unconditional:** scoping it to "where promotion is withheld" implies its converse — that promoting asks for the review — and whether a provider acts on a publish is exactly what this document refuses to assume. A run in a promote-convention repository would promote four PRs, treat that as having requested review, and sit on four PRs nobody reads: the seven-hour failure *Adopt* exists to prevent, re-opened through the section next to it.

The reasoning for the rule this section applies — why promotion is never the run's judgement, why a written convention is not a knob, and why the held-draft discriminator is read from the forge timeline — is `rules/draft-state-notes.md`'s.

**Why a promotion leaves the PR waiting rather than finished (#144 review):** publishing may start a review round in some repositories and not others, and an immediate read cannot tell *nothing was triggered* from *nothing has appeared yet*. So a promoted PR is not finished until a later delivered pass has classified the publish; what a caller's settle rule does with that is the caller's, which is why the rule itself now says so without naming a wave.

## Finding repairs

**Why a ruling is a finding whatever check or thread it resolves (#148 review):** the owner's ruling on a `needs-user` PR is how that PR moves, and the commonest one — try again on a CI failure whose budget is spent — resolves a failing check. Read literally, "work no failing check carries" left that ruling with no dispatch: the CI budget refused it and the finding path excluded it, so the PR and everything behind it stayed stranded. The work comes from the ruling, not the check, so it takes the finding path and spends the finding budget; the CI budget stays spent, and where the finding budget is spent too the caller reports what would move it. This is a behaviour change: before it, a check-resolving ruling had no route at all.

## Adopting a head

**Why a held push still consumes its cycle (#144 review):** the pass pushed — the budget bounds unattended churn, and a push that a head check refused is churn like any other. `backlog-orchestrator`'s CI and review branches compared the diff against the charter, recorded a `DECISION` in place of adopting, and incremented the cycle in the next step regardless; counting it here keeps that.

**Why a held PR stays held until released:** a `DECISION` is the owner's, and a supervisor that re-dispatched on the branch the next pass would push more work onto the thing awaiting a ruling. The caller passes the release once the ruling exists, with the ruling.

## Head moves

**Why a caller's substantive push re-triggers but a stranger's does not (#144 review):** the review-trigger rule governs what *this workflow* triggers. A re-resolved lockfile or a restack that chose between two sides is this workflow's own change to the diff, so it owes the review a repair push would. A push by the owner, a bot or another run is not this workflow's to answer for; it is adopted, reported and reset to unreviewed, and whatever that party's own convention does about review stands.

## Repair dispatch

**Why `none` exists (#144, owner's ruling B1):** the npm orchestrator supervised CI and review and never dispatched a repair — its upgrade agents are done when they return, a red check is reported, and a stale lockfile is redispatched by its own mechanism. Unifying the three copies must not start `repair-pr` passes on dependency PRs under budget keys that skill never reads, so the mechanism takes a value that dispatches nothing and reports everything a dispatch would have acted on.

## Wait

**Why one loop and one wait (#144):** a caller that also supervises workers — `backlog-orchestrator` under `swarm` — already has a loop whose wait covers worker completions, and a second loop for PRs would be the second supervisor this skill exists to rule out, and a second wake budget the one-counter rule forbids. So under a caller the skill is the PR-side handler inside that loop, and the wake it would have armed is lines in the caller's. The subscription is still armed per PR at adoption either way, because it is part of adopting the PR, not of waiting.

**Why the override is restated for a caller-owned wait (#154):** under `wait owner = caller` this skill arms the subscriptions and then runs no loop, so the wakes those subscriptions produce land in a loop whose contract is the caller's. Saying only that this skill is not following the posture would leave the session that actually answers the wake with no instruction at all. The caller carries the same shared rule and states it at its own wake; this sentence is the pointer from the side that armed it.

## Outcomes

**Why a round owed after someone else's push is surfaced (#144 round 2):** this skill may not re-trigger for a push this workflow did not make, and the reviewer may never act on it; counting that round as outstanding would leave the PR waiting with no end. Surfaced, it is reported with who moved the head and holds the merge, as a refused round does.

**Why `unrepaired` is its own outcome (#144 review):** with `repair dispatch = none` a red check is not a budget exhausted and not a judgement call — nothing was attempted — so `needs-user` would misreport it, and `waiting` would hide that nothing is going to change it. The npm orchestrator reported such a PR and did not escalate it; the outcome says exactly that.

**Why the terminal set is listed rather than implied:** `any-terminal` and `all-terminal` are what a standalone loop ends on, and a caller cannot tell `held: lock` — which ends when it drops the lock — from `held: check` — which ends only on a release — unless the contract names which outcomes the loop stops for.

**Why `finished` is defined here and cited by both settle predicates (#144, owner's ruling B7):** `backlog-orchestrator`'s settled conditions and `implement-issue`'s Settle both asked whether each PR was individually finished, in different words, and they disagreed — `implement-issue` required "a completed review round" and "CI green", which a refused round and a producer-merge red can never become, so it sat out its monitoring cap. The orchestrator already counted both as surfaced: holding the merge, never the finish. One definition, in the skill that computes it, is what stops the two drifting again.

**Why `finished` is not the end of the watch (#183):** `finished` is a settle predicate. Read as the end of supervision, it unsubscribed a PR that was still waiting for its human reviewer, and the review that came later went unseen. A caller that keeps watching passes it back in.

## Budgets

**Why the invoking user's own rounds spend no review cycle (#183, owner's ruling):** `review-repair-cycles` exists to stop a run grinding against an automated reviewer that answers every push with another round. The owner's own comments are not that loop: each round is a person deciding to comment, and it ends when they stop. Spending the budget on them meant the owner's review of a draft — the workflow the ruling describes — could exhaust the cycles the bot rounds needed, or be left as deferred repairs on the owner's own instructions. Splitting the owner's threads into their own pass is what keeps the budget binding on everything else. A trailer rebuild cannot tell the passes apart without a new trailer, and counting them all only hands back less budget, so it was left that way.

**Why the no-cycle pass is decided by the new content's author (blind audit of #184):** an owner-rooted thread that a bot follows up in is a bot round. Keyed on the root, a reviewer replying inside the owner's threads would get unbudgeted rounds, which is the loop the budget exists to bound.
