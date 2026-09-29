# supervise-prs — design notes

Companion to `SKILL.md`. That file is the contract; this one holds the reasoning, incident history, and answers to "why not the obvious other reading?" — keyed by the contract's section names. Nothing here overrides the contract.

Extracted in #144 from the three skills that each supervised PRs in their own words — `backlog-orchestrator` (about nine thousand words of it), `implement-issue`'s *Phase 2* and `npm-dependency-upgrade-orchestrator`'s *Supervise*. Entries moved here from those skills' notes keep their original wording; "the run", "the parent" and "this skill" in them are the skill they were written for, as it stood then.

## Supervise PRs

**Why a skill and not a rule (#144):** supervision is an active loop that dispatches, spends budgets and returns outcomes — the same shape as `swarm`, which callers invoke and hand inputs to. The stateless tests that fell out of it went to rules in #146 (`ci-and-review-verdicts`, `ci-attribution`, `watch-and-read`, `wake-budget`); what is left is procedure, and procedure a caller invokes is a skill. A fix made in one of the three copies reached neither of the other two: `implement-issue` re-triggered into a refused provider, lacked the post-arming read and the one-mutator rule, and settled on a predicate that could never be met with a refused round; the npm orchestrator had the only definition of green. One copy removes that class of drift.

**Why it never merges:** merging is gated, and the gates differ by caller — `settle-and-merge`'s for tranches and single issues, the npm orchestrator's by kind. A supervisor that merged would need to hold every gate's conditions, which is what the gates were extracted to avoid.

## Inputs

**Why inputs are values and never pointers (#139's rule, applied here):** a skill that must read its caller to act has an upward pointer by another route, and the caller's text is not installed beside it. The head check is the sharpest case: `backlog-orchestrator`'s chartered-scope comparison is passed as the check itself, stated in full, the way `settle-and-merge` takes an integration check "with the check itself" — so this skill can run it without knowing whose it is.

**Why absent budgets are zero (#144, owner's ruling B16):** this skill never reads the policy file, so a person invoking it bare either gets no pushes or gets pushes their repository's policy may have forbidden — the built-in 2 would override a committed 0 on the strength of an invocation that never mentioned the key. A repair is authority to push to someone's branch, and an unmentioned authority was not granted: the same reading as an unmentioned `auto-merge`. Classify-only still classifies and drafts, so nothing is lost but the pushes, and the report says why.

**Why emission cadence is an input (#144, B3):** `backlog-orchestrator` prints every record every cycle, because a count that re-enters the transcript survives a compaction; the npm orchestrator emits only changes, because re-emitting unchanged state trains its reader to ignore it. Both are right for their reader, and neither is this skill's to decide.

## The per-PR record

**Why the per-PR block holds its review lines per convention.** A routed repository can owe two independent reviews on one PR, and invariant 12 asks whether *every* round the routing requires has completed. A single-valued block cannot express "one of two", so the gate would read the first completion as the answer and open over a review still pending. This is the same defect the invariant's own parenthetical had, found in the same pass.

## Adopt

**Why `deferred` is a recorded value rather than an inference (round 1, Sept 2026):** the first version classified every `pending` trigger as untriggered and issued it, which overrode the caller's explicit deferral — a WIP draft would get its round 1 at the moment the parent adopted it. There is no way to tell a deliberate deferral from an unfinished one by looking at the PR: both have no trigger. So the deferral writes itself down when it is made, and everything else that looks like it is treated as unfinished. That direction is chosen: an over-eager trigger on a WIP draft costs a review round, and a missed one costs the review.

**Why a step that everyone performed correctly produced no review at all:** the worker is told to stop once the PR is pushed and open, which is right — it is what stops a worker becoming a second orchestrator. The repository opens feature PRs as drafts, which is also right. The two together mean the PR reaches its final state without anything having asked for a review, and no part of the run is in a position to notice: the worker returned its terminal outcome and was released, the parent recorded `PR_OPEN`, CI ran and reported. Four PRs sat for about seven hours with zero reviews and zero comments, one of them red within minutes of opening. Nothing failed. The section exists because the failure has no failure signal of its own — the only place left that looks at the PR is the parent's adoption, so that is where the check has to be.

**Why the parent re-checks a trigger `create-pr` owns:** not because the trigger moved. A worker can return with the PR open and the trigger not yet issued — linkage verification and the trigger both run after creation, so `FAILED` and `NEEDS_USER` both arrive with a usable PR — and once that worker is released nobody will ever go back for it. Reading the `review trigger` line at adoption costs one lookup against a field the per-PR block already carries.

**Why an unrecoverable counter is spent, not zero (#144, owner's ruling B12):** every caller's per-PR record is a cache, and until this change no contract said how its cycle counts were recovered after a restart — so the implicit reading of a lost cache was zero, which hands a PR the budget its owner already spent. The PR itself carries most of what is needed — repair reports, repair commits, trigger comments, reviewer answers, settlement records — and where it does not, failing closed costs one owner decision rather than an unbounded run.

## One PR, one supervisor

**Why the rule counts supervisors and not mechanisms:** written as "never two monitoring loops over one PR" it contradicted the section that requires a subscription *and* a bounded check-in over each PR — two mechanisms, one owner, which is the intended shape rather than a violation of it. What is actually forbidden is a second party watching: a worker that never stopped reading, or a supervision step reading on its own instead of consuming the parent's pass.

**What the second monitoring loop costs:** the duplicate pass spends API budget on every cycle and decides nothing the first pass did not — it re-reads the same PR to reach the same conclusion, and where it does not, the two loops disagree about a PR one of them is mid-repair on. Writing the lifecycle out as a sequence exists because the failure is never a decision to run two loops; it is a worker that never stopped reading, or a supervision step that reads on its own rather than consuming the parent's pass.

**Why the platform's own auto-merge is called out:** it is a forge setting, not the `auto-merge` policy key, and it merges on CI state alone — outside the gate, whatever this run's policy resolved to. Its merges are not outcomes this skill produced.

## Review feedback

**Why this skill never roots a review thread on the PR it supervises:** the actionability discriminator is thread-rootness — a thread the invoking user rooted is their instruction — and on the degraded posting-identity path this run's own comments carry the invoking user's login. A run-authored root comment would be indistinguishable from an instruction to itself, silently breaking the test. Replying in threads and posting timeline comments keeps the discriminator true by construction.

**Why a reserved thread blocks the gate but not settlement:** the run cannot be required to resolve what policy forbids it touching, so it can still finish and return — but the thread is an unresolved actionable finding wherever that concept is consumed, so its round is not clean and the merge gate stays shut.

## Draft state

**Why the trigger comment stayed unconditional:** scoping it to "where promotion is withheld" implies its converse — that promoting asks for the review — and whether a provider acts on a publish is exactly what this document refuses to assume. A run in a promote-convention repository would promote four PRs, treat that as having requested review, and sit on four PRs nobody reads: the seven-hour failure *Adopting a PR is three things* exists to prevent, re-opened through the section next to it.

**Why the old promote-on-clean-review behavior was deleted rather than made configurable:** promoting a draft is a social act — how you ask a person to review — so a run promoting when the PR "looks done" is the run deciding when a person gets asked, the same social act wearing a heuristic. And `auto-merge` already carries the whole distinction a knob would have served: a repository that opted in gets publish-then-merge from the gate once review and CI are clean; one that did not keeps its PR a draft until the owner acts — a repository keeping merge authority keeps review-requesting authority with it. A second knob would encode a distinction the key already makes and could disagree with it.

**Why deferring to a written convention is not that knob (Sept 2026):** the deleted behaviour had the run deciding, from a heuristic, when a person gets asked to review. A repository's documented convention is the person having decided already, in writing, with the conditions stated — so carrying it out is not the run exercising judgement, which is the whole objection. The knob would have let an invocation turn promotion on; the convention cannot be set by an invocation, and it comes with its own conditions rather than this skill's. Two repositories' `CLAUDE.md` said to mark a PR ready once CI was green, the review was back and every finding was resolved, while this document said the run does not promote — a contradiction with no tiebreak, which left one PR promoted and three not.

**Why the held-draft discriminator is "currently draft and ever ready", read from the forge timeline:** as-created versus current cannot see the case that matters — created-as-draft, marked ready by a human, returned to draft by them leaves both values reading `draft`, identical to a PR nobody touched, and a run consulting only those two would publish and merge exactly the PR a person deliberately withdrew. The stronger reading is available *because* this run never moves a PR ready→draft, for any reason — it survives the run promoting under a repository's convention, since what the discriminator reads is that direction alone: every ready→draft transition on this PR is someone's decision, whoever made the draft→ready one before it. The forge timeline, not the state block, because the state block is cached run state — a restart or missed event leaves it wrong about the one question that matters.

## Repair dispatch

**Why `none` exists (#144, owner's ruling B1):** the npm orchestrator supervised CI and review and never dispatched a repair — its upgrade agents are done when they return, a red check is reported, and a stale lockfile is redispatched by its own mechanism. Unifying the three copies must not start `repair-pr` passes on dependency PRs under budget keys that skill never reads, so the mechanism takes a value that dispatches nothing and reports everything a dispatch would have acted on.

## Wait

**Why one loop and one wait (#144):** a caller that also supervises workers — `backlog-orchestrator` under `swarm` — already has a loop whose wait covers worker completions, and a second loop for PRs would be the second supervisor this skill exists to rule out, and a second wake budget the one-counter rule forbids. So under a caller the skill is the PR-side handler inside that loop, and the wake it would have armed is lines in the caller's. The subscription is still armed per PR at adoption either way, because it is part of adopting the PR, not of waiting.

## Outcomes

**Why `finished` is defined here and cited by both settle predicates (#144, owner's ruling B7):** `backlog-orchestrator`'s settled conditions and `implement-issue`'s Settle both asked whether each PR was individually finished, in different words, and they disagreed — `implement-issue` required "a completed review round" and "CI green", which a refused round and a producer-merge red can never become, so it sat out its monitoring cap. The orchestrator already counted both as surfaced: holding the merge, never the finish. One definition, in the skill that computes it, is what stops the two drifting again.
