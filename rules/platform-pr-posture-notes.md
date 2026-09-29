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

**Why the watch ends when the run returns:** the override lasts for the life of the run, and the posture does not. A subscription left armed after the skill returned — a single-issue run that finished with its PR still open, a checkpoint returned for a restart — keeps delivering wakes that carry the posture to a session that is no longer executing the skill, so the one instruction in view is the drive-to-green loop. Unsubscribing costs nothing a resumed run cannot rebuild, since adoption arms the watch again.

**Why the check-in stays:** the posture's standing-down rules could be read as covering the backstop too. The check-in exists because the subscription is unreliable for exactly the events that end supervision, and the override is about fixing, not about watching.

## Saying so

**Why the user is told:** the toggle is visible and says "Auto fix". A user who sees it on and a run that fixes nothing without a budget reads as a broken run; one sentence at subscription prevents the confusion, and the stop sentence answers the obvious next question — whether they can still stop it.
