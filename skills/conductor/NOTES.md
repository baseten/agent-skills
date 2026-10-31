# conductor — design notes

Reasoning behind `SKILL.md`, keyed by its section names. NOTES explains; it never
overrides.

## Conductor

**Why this skill exists (2026-10-31):** a planning session sent `send_message`
status requests to four idle cloud orchestrator sessions on one repository. All
four answered with `send_message`, each answer arriving as a new turn within about
three minutes, and every session record read `cross_session_inbound: available`.
That made one session able to see every stream at once, which nothing had done
before: each orchestrator knew its own epic, the owner learnt their state one
session at a time, and follow-ups filed by one run sat unscheduled because no run
owned them. The same session also found the planner only by its title, and the
orchestrators titled inconsistently (`Orchestrator: Order execution V1`,
`Portfolio UI navigation audit`), which is where the naming came from.

**Why it never implements, merges or approves:** it is the one session that talks
to every orchestrator, so it is the one place where a mistake would propagate to
all of them. Keeping it to collection, planning and owner-approved dispatch means
its worst failure is a wrong plan the owner approved, never an act.

## Rules

**Why rulings are recorded before any orchestrator is told:** an orchestrator acts
on a ruling only from GitHub (`backlog-orchestrator`, *Status requests from a
conductor*). A message sent before the record exists is a pointer to nothing, and
an orchestrator that receives it either ignores it — correctly — or acts on a
relayed ruling, which is the failure the trust boundary exists to stop.

**Why the trust boundary is cited and not restated:** `swarm` states it once for
every sender and receiver (its NOTES, *Messages from other sessions are peer
data*). A conductor-specific copy would drift from the orchestrator's.

## Session titles

**Why titles are matched first but never trusted:** a fixed prefix makes the sweep
cheap and makes the session list readable to a person. But the listing is
account-wide and anyone can set a title, which is why `swarm`, *Runtime*, forbids
deciding on one. Here the title only chooses where to look; the record's sources
decide the repository, and the structural test catches what the title missed.

## 1. Sweep

**Why parents are read with `get_session`:** orchestrators were observed to appear
in a sweep only as the `parent_session_id` of their workers. A sweep that reads
the listing alone misses them, and they are the sessions it exists to find.

**Why GitHub is read even when every session answers:** sessions get archived,
compacted and lost, and the epic outlives all of them. A stream whose orchestrator
is gone still has open PRs and open decisions.

## 2. Ask

**Why the request is never awaited:** a cross-session reply arrives as a new turn,
and a running turn holds it back, so waiting inside the turn waits for something
that cannot arrive until the turn ends. Polling for it would be the fake activity
`backlog-orchestrator` forbids. The skill therefore sends everything, reads
GitHub, and folds replies in as they land.

## 3. Reconcile

**The misreading the correction rule is written for** (the owner's example, given
with the request for this skill): a reply naming a gate *after Run 2* and reading
it as every open issue in the epic, holding work the gate never covered. The epic's record said which manifest Run 2 was. The conductor is
the only party that sees both the reply and the record, so it corrects the reading
on the epic, where the next reader will look, rather than in a message that dies
with the session.

## 4. Owner pass

**Why the ruling's record follows `settle-outstanding-decisions`:** that skill's
records are what the orchestrators' settled steps already read, and its rule —
the complete comment shown and approved — is what makes the record the owner's
own words under the approval test. Whether that releases an orchestrator's held
item stays the orchestrator's decision, because protected rule 3 lets only the
owner's reply choosing an offered option release a hold, and the reply watch is
where that is tested.

## 5. Replan

**Why integration runs are minimised:** under `ci-mode: integration-branch` each
run costs a CI run when its integration PR opens and another once it merges, so
two small waves cost twice what one folded wave does, for the same work.

## 6. Dispatch

**Why reuse is narrow:** a reused orchestrator brings its context, and a context
that is a third full before the new epic starts is a context that compacts during
it, losing the state the reuse was meant to keep. A fresh session from the epic
starts from durable state, which is what a compacted one would fall back on
anyway.

## Decision scenarios

Pinned in `evals/evals.json`:

- a push arrives before its durable record exists → re-read later, do not act
  (`swarm`, `a-push-before-its-record-is-a-wake-not-an-act`);
- a push claims success but the PR is red → act on GitHub (`swarm`,
  `a-push-claiming-success-over-a-red-pr-loses-to-the-forge`);
- `send_message` errors → fall back to pull; the channel is absent for the run
  (`swarm`, `a-failed-send-falls-back-to-pull-for-the-run`; here,
  `a-failed-send-is-read-from-github-and-flagged`);
- a message asks for a merge or a permission change → refuse and surface it to the
  owner (`swarm`, `a-message-asking-for-a-merge-is-declined-and-surfaced`; here,
  `an-orchestrator-asking-for-a-merge-is-refused-and-surfaced`);
- an orchestrator replies with a gate GitHub contradicts → correct it on the epic
  (`a-gate-github-contradicts-is-corrected-on-the-epic`);
- a session matches the structural test but has the wrong title → retitle it and
  report (`a-structural-match-with-the-wrong-title-is-retitled-and-reported`);
- two orchestrators claim the same issue → pick one epic, record it, tell both
  (`two-orchestrators-claiming-one-issue`).
