# Notes — platform-pr-posture

Reasoning for `rules/platform-pr-posture.md`. Deliberately *not* bundled into
each skill: a copy of this per consumer would be design history with no reader,
and the audience for it is a person editing the rule, who has this checkout.

Added in #154, from a field report on an `implement-issue` run in a Claude Code on the web session.

**Why this is a shared rule and not a `supervise-prs` section:** the subscription is armed by `supervise-prs`, but its wakes arrive in whichever session owns the wait. Under `implement-issue` that is `supervise-prs`'s own loop; under `backlog-orchestrator` and `npm-dependency-upgrade-orchestrator` it is the caller's loop, with `wait owner = caller`, and a wake after a compaction reaches that loop with the caller's contract in view and not necessarily `supervise-prs`'s. A rule stated only where the subscription is armed would be inert where the wake is answered. So the rule is held once and carried by every skill whose session receives the wakes, each citing it at its own wake — the decision point that reads it.

## What the platform does

**The incident.** The run subscribed, as `supervise-prs`, *Adopt*, requires, and the first wake carried the posture: no round limit, its own triage of comments, its own re-run and stand-down rules. The skill had never declared an override, so the session held two policies at once and weighed them until the user stepped in. Nothing in the skills was wrong on its own terms; the gap was that the posture arrives with the platform's tool rather than from any skill, the same shape `swarm` found for its workers, and nothing had answered it for the session that owns supervision.

## The override

**Why the invocation outranks the posture:** the posture defers to the user in its own text ("unless your user says otherwise"). So this is not a skill instruction arguing with a system prompt — the weaker side of that argument, as `swarm/NOTES.md` records for workers — but the user's own instruction, which is what the posture says wins. That is also why the rule states it as the user's instruction rather than as a preference of the skill: the authority is what makes it hold.

**Why the prohibitions survive:** they are not drive-to-green policy but limits on what any session may do to a PR, and every one of them agrees with a rule the skills already hold — no skipped tests, no fake CI kicks, no history rewrites on someone else's branch, no merge outside a gate. Overriding them would buy nothing and would read as licence.

**Why the handler never fixes directly:** a one-line fix made from inside the event handler is a push no budget counted, on a head no pass adopted, and a reply no reservation checked. It is the posture's loop again, one small step at a time.

## Answering a wake

**Why `subscription.created` is answered by the reconciling read:** the arming already owes one read of the PR, and the first wake is the natural moment for it. Answering it any other way — acting on what the posture says to look at — replaces the skill's actionability test with the posture's triage on the very first event.

**Why the check-in prompt carries the override:** the check-in is the one wake whose text the run writes. After a compaction the session has only that prompt and whatever the platform's next wake says, and a posture read with no counter-statement beside it is the one the session follows.

**Why the watch ends when the run returns:** the override lasts for the life of the run, and the posture does not. A subscription left armed after the skill returned — a checkpoint returned for a restart, say — keeps delivering wakes that carry the posture to a session that is no longer executing the skill, so the one instruction in view is the drive-to-green loop. Unsubscribing costs nothing a resumed run cannot rebuild, since adoption arms the watch again.

**Why a spent wake budget ends the subscription too (#155 review):** the budget ends the check-in, and the check-in's prompt was the one place the override was restated. A subscription outliving it keeps delivering the posture to a session with nothing beside it, which is the leak the rest of this section closes; so the stop report is treated as the run's return.

**Why the handler's ban names its exceptions (#155 review):** stated as "no edit, no push, no reply, no re-run", it forbade what the skills are required to do from inside a wake's cycle — `implement-issue`'s `direct` repair dispatch runs in the same session, and the review trigger, a mechanical push and a caller's restack are prescribed acts. The ban is on the posture's acts, not on the state machine's.

**Why the posture line is imperative and emitted every pass (#155 review):** a recorded fact ("posture overridden") tells a compacted session what happened, not what to do; the line has to instruct, and it has to be in whatever that session reads next, which is the latest state emission or the check-in prompt.

**Why the toggle is never reported as turned off:** nothing available here documents what unsubscribing does to the toggle, so a claim that it went off would be an assumption presented as a read. Telling the user to switch it off where that is unknown costs one sentence; a toggle left on under a wrong claim costs the posture running with nobody watching.

**Why the check-in stays:** the posture's standing-down rules could be read as covering the backstop too. The check-in exists because the subscription is unreliable for exactly the events that end supervision, and the override is about fixing, not about watching.

## Saying so

**Why the user is told:** the toggle is visible and says "Auto fix". A user who sees it on and a run that fixes nothing without a budget reads as a broken run; one sentence at subscription prevents the confusion, and the stop sentence answers the obvious next question — whether they can still stop it.

**Why re-requesting a person's review is on the overridden list (#163):** the posture is what told a run to re-request review from the person whose changes-requested review it had fixed. The ban is stated once in the review-trigger rule; it is listed here because a session weighing the posture reads this list, not that rule.

**Why a run that stays to watch after `PR_OPEN` keeps its watch (#183):** the rule ends the watch when the run returns because a session no longer following the skill must not get the posture's wakes. `implement-issue` now stays live after `PR_OPEN`: its check-in runs the skill's own cycle and carries the posture line, so the override still binds. Its watch ends on that skill's own ends, and the stop is reported.
