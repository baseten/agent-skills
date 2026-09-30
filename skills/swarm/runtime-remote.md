# swarm — the remote-session tier

Part of `swarm`'s contract, read on tier 2 (remote worker sessions,
`create_session`) before the first worker is dispatched. `SKILL.md` points here
from *Runtime*, *Remote worker session arguments* and *Bounded runtime probing*,
from the countermand section (its placement table and its residue), from the
paragraph beginning *Two things are never archived*, and from *Blocked workers*
(the channel, and case 4's filesystem-search exception); its rules assume this
file has been read, and this file assumes them. The reasoning is in `NOTES.md`,
under the `SKILL.md` section that points here — mostly *Remote worker session
arguments*, *Countermanding the worker's ambient supervision posture* and
*Blocked workers*.

## Session arguments and the checkout check

Omit `environment_id` and the worker inherits this session's environment. That is
sound, but the environment decides where the worker *runs*, not what it has
*checked out*.

**Pass `source_url` and `source_revision` explicitly on every worker session.**
Inheritance usually supplies a checkout and sometimes silently does not, and a
dispatch prompt cannot pin a branch in a repository that was never cloned.
Passing the source also satisfies `outcome_branch`, which is rejected unless
`source_url` accompanies it — wherever a caller gives each worker session its own
`outcome_branch` (for `backlog-orchestrator`, its *Session branch mandates*).

**Then verify the checkout before treating the worker as dispatched: the
`create_session` response must show `sources` populated.** It is the only signal
before the worker starts; every later one — the call's success, `RUNNING`, a
worker that reads as *still working* while it looks for the code — reads the same
either way. An empty `sources` is a failed start, not a worker to watch: treat it
as one (`SKILL.md`, *Bounded runtime probing*) rather than dispatching into it.

**What the unverified case looks like later**: a worker searching the filesystem
for its own source files — a `task_summary` about locating a file the dispatch
prompt named, a repository-root probe, a permission prompt for a bare `find`. It
is a worker that was never given a repository; `SKILL.md`, *Blocked workers*,
case 4, says where it goes.

## Ending a failed start

**End that session before retrying, or the retry orphans it.** A failed start is
not an absent worker: the session exists, holds a container and a worker slot,
and reports `RUNNING`. Interrupt it, then archive it, in that order.

- **The capture is discharged here, at creation only.** A session ended at the
  verification above has not run a turn, so there is no worktree to strand and no
  recovery ref to push. The same empty field on a session that has been running
  says nothing about what the worker produced since — it may have cloned a
  checkout itself — so a checkout-less session discovered later takes the
  ordinary inspection and capture (`SKILL.md`, *Blocked workers*), never this
  shortcut.
- **The interrupt does not consume that task's lost-worker budget** — at creation
  only, on the same boundary — against the general rule for stopping a `RUNNING`
  session (`SKILL.md`, the paragraph beginning *Two things are never archived*).
  A session ended before its first turn did no work, so the redispatch is the
  task's first real attempt.

## Detecting the two capabilities

Both are observable without spending a worker, and both are recorded on the run's
state and reported (`SKILL.md`, *Report*).

**The checkout.** A session record's `sources` carries the repository it was given
and **no filesystem path**, and each session runs in its own container
(`environment_kind`). **The detection is one-directional: it establishes *cannot
reach* and can never establish *can reach*** — so absent a path the answer is
*cannot reach*. A self-hosted pool that mounts worker files where the parent can
see them would be genuinely reachable, but no field this contract knows of
carries such a path, so it is classed unreachable too until an operator
establishes a path by means this contract does not yet define. Do not infer
reachability from `environment_kind`, which speaks to separate containers, not
shared mounts.

**The channel — two halves, both required.**

1. **The target's half**: `external_metadata.cross_session_inbound` reports
   whether that session accepts inbound cross-session messages. It is observed as
   the string `available`, not a boolean: **test for that value, and treat every
   other reading — the field absent included — as absent.** Where it reads
   anything but `available`, the channel is absent and no probe is needed.
2. **The caller's half**, established from this session's own side: it holds a
   send tool at all, and a listing resolves this target. The field says nothing
   about this — an orphan has been observed reading exactly `available` while the
   caller had no send tool, `ListAgents` resolved no peers, and every send returned
   no-such-agent.

| target's half | caller's half | the channel |
|---|---|---|
| `available` | present | **present — use it**; `SKILL.md`'s *Blocked workers* step 2 is a real lever |
| `available` | absent | **absent.** Not a worker written off as unreachable-and-therefore-fine: the levers that depend on sending do not exist, the run says so plainly naming the session, and the decision goes to the owner |
| anything else | — | absent |

Do not require an observed landing before treating the channel as present.
It is enough to act on and never enough to wait on: nothing waits on it — nudges are unacknowledged and every escalation runs on the
observed remote head — so a wrongly-presumed channel costs one composed message.
**A send that errors or is refused is direct evidence and flips the recorded
capability to absent for the rest of the run**; that negative observation
overrides an `available` field, never the reverse.

**What was observed on this runtime**: `SendMessage` did not address a worker
session the run had created, in any state, and `interrupt_session` stops a worker
without answering what stopped it. So where the recorded channel is absent, every
recovery that would redirect a worker is archive-and-redispatch or `NEEDS_USER`
instead (`SKILL.md`, *Blocked workers*, step 3).

**Record how each session's channel was decided, and report it**: a run that read
the field as absent and one that never read it look identical otherwise.

## The countermand on this tier

A Claude Code Remote worker session inherits a system prompt telling it to
subscribe to its PR's activity and to schedule a self check-in about an hour out,
re-arming it silently until the PR merges. A dispatch prompt is a task
instruction, the weaker side of an argument with a session's own system prompt.

**So write the countermands into the session's system prompt at creation**:
`create_session` takes an `append_system_prompt`, the one lever at the same level
as the instruction it answers. All three go there — the supervision ban, branch
protection and the question posture, as `SKILL.md`'s template states them — and
the dispatch prompt restates them rather than carrying them alone. This holds for
implementation, review and repair sessions alike.

**Expect residue.** Appending does not delete the instruction already present,
some environments ignore the parameter, and a worker weighing two same-level
instructions may still arm a wake or stop to ask. *Blocked workers* is the
backstop for that.

**Do not read a quiet session list as proof the countermand held — the quiet case
is the expensive one.** Where workers inherit an allowlist granting the trigger
tools, a worker that arms a wake can disarm and re-arm it, so it never blocks:
*Blocked workers* never sees it, and it wakes hourly to re-read a merged PR for as
long as the account pays. A worker that arms a wake it *cannot* disarm at least
blocks visibly on the permission prompt. What catches both is the release
reconciliation against the runtime's session list (`SKILL.md`, *Runtime*;
`backlog-orchestrator` runs it as its supervision loop's step 11), and the report
naming every wake a worker was observed to arm.
