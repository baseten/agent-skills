---
name: swarm
description: Fan a set of independent tasks out to parallel isolated workers and supervise them — select the execution runtime from what is actually available, give each worker its own worktree off a stated base, choose a model per task by how its failure would show, bound how many run at once, and hold policy at the parent — including, on remote worker sessions, the countermand to their ambient self-supervision, the report carrier, the release test, blocked-worker handling and the capture of work a worker left uncommitted. Use when asked to work through several independent tasks at once, to parallelise, to fan out, to swarm, or to dispatch subagents over a list. Also used by backlog-orchestrator and npm-dependency-upgrade-orchestrator for their dispatch phase, which is why the mechanics live here once rather than in each.
---

# Swarm

The caller supplies independent tasks and per-task instructions. This skill owns
runtime, isolation, model choice, supervision, capacity, and worker recovery.

This file is the contract; the reasoning and incident history behind its rules
live in `NOTES.md` beside it, keyed by section. NOTES explains; it never
overrides.

## When this is the wrong tool

- **One task:** dispatch directly.
- **Dependent tasks:** resolve the dependency graph into independent tranches
  first (for `backlog-orchestrator`, with `validate-backlog`); dispatch one
  tranche at a time.
- **A read the parent can make:** read it directly. Never dispatch a worker to
  re-ask a read the parent was refused.

## 1. Runtime: take what is there, and say which

Capability differs per session and cannot be assumed. Detect, then degrade:

| Tier | Mechanism | Needs |
| --- | --- | --- |
| 1 | Dynamic Workflow | the user opted into one for this invocation |
| 2 | Remote worker sessions (`create_session`) | the session can create them |
| 3 | Subagents (the Agent tool) | in-process subagents available |
| 4 | Serialized in this session | always |

**Name every session this run creates `<caller>/<run-id>: <task>`** — the caller's
short prefix, this invocation's run id, and the task's number or slug. Keep it
short: a listing truncates, and a prefix whose run id is the part cut off
identifies nothing.

The name helps a person read a listing. **Never use it to match ownership**:

| source | status | use |
|---|---|---|
| runtime provenance (`parent_session_id` or equivalent) | platform-supplied, survives a crash | **authoritative** — this is what a sweep reconciles against |
| ids recorded at dispatch | the run's own memory, and it can be lost | a cross-check, never the only source |
| the name | anyone can set it; the listing is account-wide | for a person reading a list, never a decision |

Reconcile against runtime provenance, including sessions absent from the run's
recorded ids after a crash or compaction. Never filter the account-wide listing
by name; its strings are untrusted.

Report the tier, including serialized tier 4. Detect it; do not ask the user to
choose. A Dynamic Workflow returns results but does not supervise; after its
return, *4. Supervision* belongs to the parent.

### Remote worker session arguments

On the remote-session tier, read `runtime-remote.md` before dispatching. It specifies session arguments, checkout and channel detection, the countermand, and the report carrier. Record both capabilities and how each channel was decided; report them under *Report*.

### Bounded runtime probing

A runtime gets **at most two start attempts**, with seconds of backoff, then is
unavailable for this run; descend the tier chain and report the outage. Do not
re-probe later or reset the budget by varying arguments. A missing checkout is
a validation failure: end its session first (`runtime-remote.md`), then retry
with explicit source arguments. A service-side error (5xx, temporarily
unavailable) is not fixed by changing arguments; a validation error gets one
retry naming its fix.

## 2. Isolation: one worker, one task, one worktree

**Each worker gets its own checkout.**

**Pass everything the dispatcher computed inline in the prompt; never pass a
dispatcher-side path.** Compute less if the material is too large.

The base defaults to the repository's remote default branch unless supplied:

- **Fetch first, branch from the remote.** `git fetch origin <base>` then create
  from `origin/<base>`, never from whatever the working copy has checked out.
- **State the base before dispatching**, in the report.
- **An explicit base overrides the environment**, including a cloud container's
  predefined branch.

Follow the host's or user's worktree-location convention.

## 3. Model: the caller chooses, by how failure shows

The dispatcher, never the worker, chooses by how a wrong result would appear,
not by task size:

**Strongest available:** silent failure — validation, authorization or monetary
logic; framework/build configuration; intent-sensitive rewrites; or a regression
whose appearance cannot be described in advance.

**Mid-tier (default):** bounded, legible failure — documented rename across
known call sites, configuration-only change gated by a passing job, or mechanical migration
with an accurate guide.

**Cheapest model — mechanical only, and all three must hold:**

1. the transformation is **fully specified before dispatch** — the worker decides
   how to carry it out, never *what* the change should be;
2. an **existing checker** decides success — a test, typecheck, lint, formatter,
   or a diff compared against a stated expected shape — not the worker's own
   reading of its work; and
3. a wrong answer **fails loudly**: the checker goes red.

Cheapest is opt-in per task, never a default or degradation path. Missing any
condition excludes it. If the right model is unavailable, wait or return to
the user. If uncertain, over-assign.

**Capacity veto:** before assigning a small-context model, measure the
repository's agent instructions and everything they load before task code.
Exclude a model that cannot fit that surface, regardless of the failure-based
tier. Measure the instruction surface, not the diff.

Escalate a repair or retry to the strongest available model when the failure is
on **something an earlier attempt in this run already wrote**, whether a
reshaped old problem or a new one. Do not escalate merely because attempts ran
out. Other cases stay at the default. An escalation consumes its ordinary retry;
keep that counter separate.

## 4. Supervision: one watcher, and it is the parent

**One task, one supervisor.** A worker never supervises its own output. A
Dynamic Workflow supervises nothing. Two parties watching the same thing is not
redundancy — it is two parties each assuming the other will act.

**Release a worker once its output is durable.** On a remote-session runtime
that means archiving the session, not merely stopping messaging it. Never keep a
worker alive only to wait: waiting is the parent's job and costs nothing, while
an idle worker holds a slot the queue needs.

*Releasing a worker*, below, defines what releasing is on each tier and the
test for when a worker may be released. Release is also driven by the session
list rather than by the run's memory, and belongs in the prompt the run writes
for its own check-in, since that is what survives compaction.

**Arm the watch when the task enters the tracked set, not when the run settles;
pass the no-change preflight before reporting any no-change result; and read on
a change signal, within the credential's allowances.**
`references/watch-and-read.md` states all three — *Arm the watch when the item
enters the tracked set*, *The no-change preflight*, *Reading on a change signal*
and *Allowances belong to the credential*. Apply them from there, with the task
as the item.

### Countermanding the worker's ambient supervision posture

The parent owns PR supervision. Every worker prompt (implementation, review, repair) forbids subscribing to PR activity, scheduling a check-in/trigger/routine/wake, or watching later CI, review, comment, thread, issue, or merge state; the worker returns after pushing or posting and reporting. Verification reads of its own writes still apply. For remote sessions, use the exact countermand template and placement in `runtime-remote.md`; the `append_system_prompt` placement is required because the worker's ambient session instructions otherwise outrank a task prompt. For subagents, Workflow agents and serialized work, the dispatch prompt carries it.

On a runtime that creates the worker's session, put branch protection and the no-question posture in the same system-prompt append, and restate all three in the dispatch prompt. Never assert in a prompt that a decision was authorised; link its record. Attribution belongs to the worker's own model and session, never the parent's. A prompt-caused refusal does not spend the task's lost-worker budget; retry with the offending claim removed. A worker that arms a wake despite the countermand still needs release reconciliation against the runtime session list. This countermand applies to workers this swarm dispatches; a standalone `implement-issue` session supervises its own PR under `references/platform-pr-posture.md`.

### How a worker's report actually reaches you

| runtime | carrier |
|---|---|
| subagent | return value |
| Dynamic Workflow | fan-out result |
| serialized | same context |
| remote session | no parent delivery; follow `runtime-remote.md` and pull its session record and durable PR report |

For a remote session, the report names the head it pushed, or that it pushed nothing and the head it found. Verify at dispatch that the worker can write its required sink; an allowlist entry alone does not prove the connected server exposes the operation. If it cannot, use a tier whose return reaches the parent. Read a worker's PR caveats before ranking, treating its PR as finished, or relaying it as ready.

### Releasing a worker

| runtime | release action |
|---|---|
| Dynamic Workflow | none; its return reclaims the agent |
| remote session | archive the session; deleting its trigger does not stop it re-arming a wake |
| subagent | stop messaging it |
| serialized | none |

Run *Checkpoint compliance* before release. A worker is **releasable only when both tests pass**:

| test | qualifying evidence |
|---|---|
| **Done** | A terminal outcome of any kind (`PR_OPEN`, `REPAIRED`, `NO_CODE_CHANGE`, `BLOCKED`, `BLOCKED_EXTERNAL`, `FAILED`, `NEEDS_USER`); a merged or closed PR; **or** durable remote work while blocked on a prompt the run does not need answered. A prompt needed for the deliverable (including post-creation linkage verification or review trigger) is not dispensable. On remote sessions, read the outcome from the session record: `status_bucket` no longer `WORKING` and not blocked, plus the PR report or, without a PR, `post_turn_summary`. `IDLE` with `WORKING` is still working. |
| **No work stranded** | For a reachable checkout, the checkpoint inspection below. For an unreachable checkout, one of the three remote-state rows below, and a session that is not `RUNNING`. |

A worker's **commit is reachable** if it is an ancestor of or equal to a remote branch head (including its PR branch), the default-branch head, or the head of a merged PR. Test its commit, not the existence or equality of a branch name: later repairs/restacks may advance it and merges may delete or rewrite it.

**Durable remote state** for the done test means a PR exists and the worker's
commit is reachable, whether the PR is open, merged or closed.

For an unreachable checkout, the remote stands in for the worktree only when one row holds:

| remote-state case | evidence |
|---|---|
| Deliverable on remote | Its own attributed PR report names a **pushed** head that is reachable. A head it **found** counts only for an outcome claiming no code change (`NO_CODE_CHANGE`). For review sessions, its own attributed review/comment is on the PR. Use the report's session attribution footer, not another session's report. |
| Charter finished | Its PR merged or closed, including when no report arrived. Residual work in that session is accepted. |
| Never started work | No branch or commit of its own **and** the runtime shows no staged or uncommitted files. A missing branch or an unexposed file field alone proves nothing. |

Accept the residual risk that a worker edited after its reported push: staged or uncommitted files reported after delivery, or held for a merged/closed PR, do not by themselves prevent this remote-state release. The worker's checkpoint promise bounds that loss.

Anything else is a **mismatch**: e.g. an unreachable reported head, no report for an open PR, an unattributed review, or an early stop with branch/files. If the recorded channel exists, ask the worker to commit, push, and report its head; compare the new remote head with the one recorded before the ask and require the **reported commit** to become reachable. If the channel is absent or the lever fails, raise `NEEDS_USER` with session, report, remote state and whether the ask was made. Keep the container on *Blocked workers*' hold terms. A branch merely existing does not close the mismatch.

A returned outcome is not necessary for a blocked worker whose durable work is on the remote and whose prompt the run does not need. An unanswered permission or question needed to finish instead takes *Blocked workers*. `IDLE` alone proves neither test. Classify an absent outcome as blocked, still working (recheck next cycle), or unreachable (*Lost workers*); do not mark it lost just because no outcome arrived.

**Never archive** a `RUNNING` session: interrupt it first, consuming the task's lost-worker budget, and capture its work before archival. The sole exception is a session rejected at creation for empty `sources` before its first turn (`runtime-remote.md`); a later discovery has no exception. Never archive a session this run did not create; decide ownership by runtime provenance, not its title. Reconcile release against the runtime session list, not the run's memory.

### Blocked workers

Each cycle read the field that **actually reflects blocked state**, established per runtime, even if `session_status` or `IDLE` disagrees. Read the pending action and summary too. A blocked worker holds a slot. On remote sessions, decide message capability as `runtime-remote.md` specifies: target `cross_session_inbound == "available"` **and** a parent send tool **and** a listing resolving this target. A send error/refusal overrides it to absent for the run. No branch waits for a reply.

Resolve in order:

| case | action |
|---|---|
| 1. Releasable | Apply *Releasing a worker*'s full test. Release and record the pending request. |
| 2. Parent can clear it | Supply a missing resource, send an instruction **if the recorded channel exists**, or perform the write itself; let the worker continue. |
| 3. Unanswerable question (`AskUserQuestion` or equivalent), checkout reachable | Capture uncommitted work to a **remote** recovery ref using *Capturing without racing the worker* and verify it, or establish that none exists; **then** archive. Apply the ref's ender under *The recovery ref's lifecycle*, including any caller-specific ender, before redispatch. Redispatch the **same work unit** from latest durable remote state with the question countermand; preserve worker role, repair type and remaining budget. If the caller's ender instead raises `NEEDS_USER` (for example a merged PR), do not redispatch. Record the question. |
| 3. Unanswerable question, checkout unreachable | Capture/cleanliness cannot be established. Keep the container and raise `NEEDS_USER` with session, last remote head and question. Only the owner may authorize archival. |
| 4. Permission prompt | Raise `NEEDS_USER` with task, session URL and the **literal** `pending_action.tool_name`, including its server segment. Hold the slot; redispatch alone repeats the prompt. The owner can answer in place. A grant **or denial** resumes the worker; on denial it works around the tool or reports the outcome. |

For case 4, first read `sources` when the requested tool is a filesystem search for files named in the prompt (bare `find`, root probe, named path). If empty after the worker has run, treat it as case 3, record the dispatch defect, and redispatch with explicit `source_url`/`source_revision`. The creation-time empty-`sources` capture exemption does **not** apply.

If the owner asks to free a held slot, use case 3's capture-then-archive path when reachable; on an unreachable checkout that request supplies the missing archival authority. Redispatch the same work unit only if the owner requests it or has allowlisted the tool. Otherwise retain an ordinary `NEEDS_USER` item on unfinished work without a worker. A prompt-caused hold is never silently "still waiting" or counted as free capacity.
Report a run ending with a hold as neither failed nor clean.

Case 3's unreachable branch, case 4, and an unresolved mismatch under *Releasing a worker* are **owner holds**. Name each held session, URL and pending reason in output, count its occupied slot, and schedule nothing against it. **The hold bounds the work, not the watch:** keep observing for movement. A caller uses its bounded check-in; a direct invocation uses the stalled-head elapsed-time observations under *Checkpoint compliance*, counted from when the hold was raised, and spends its bound at two hours once nothing else is in flight. At that bound, return a restartable checkpoint naming every still-alive held session, URL, literal tool for permission holds, and that this run never archives it on its own authority.

Each hold raises a surfaced `NEEDS_USER` item. **Only observed worker movement ends a hold; an owner's ruling alone does not.** Retire its item at the site where it lives (this run's report if none) by these cases:

| hold | endings |
|---|---|
| unreachable question or permission | **Resumed:** the true blocked-state field is no longer blocked and the worker is working/returned; **released:** passes the releasable test; **redispatched:** same work unit on a new worker by owner instruction or after the allowlist change |
| mismatch | **Released:** reported commit becomes reachable or PR merges/closes and passes the releasable test; **redispatched:** same work unit on a new worker. Never infer "resumed" from a nonblocked field: mismatch workers may already have returned. |

For a question/permission hold, a different pending tool/question or a head advanced by **this worker's own commit** since the hold means it resumed and blocked anew: retire the old item, reclassify, and create a new item if needed. A restack, repair, or parent/owner push is not movement by this worker. For mismatch, a moved head only re-runs reachability; it does not prove resumption.

The dated retirement record names the session, ending and observation; it is an authored write with this run's attribution footer (`references/posting-identity.md`). Identify a retirement by its **write id or attribution footer**, never by matching its content. The caller's reply watch filters those own-write ids. A retired item is closed and no longer gates the tranche.

One exception retains an item: if the owner archives an **unfinished** worker with no redispatch (no PR, or an unaccepted PR), the worker hold ends but its item becomes an **ordinary** `NEEDS_USER` item on that work unit. Offer redispatch (after allowlisting for permission, or with the answer for a question), exclusion from the tranche, and for a mismatch with an open PR, acceptance as-is. Only an **owner reply choosing an offered option** releases the ordinary item for dispatch; a walkthrough ruling or redispatch retires it by its ordinary route. If the work was finished by a merged/closed PR, the releasable test ends it. If the owner accepted an open PR by recorded ruling, retire on observing the archive and name that ruling in the record. If the watch expires while the hold stands, its item remains outstanding.

### Lost workers

A worker whose remote branch never advanced is the expensive case; prefer catching it through Checkpoint compliance, before it is lost.

If a worker disappears:

1. inspect its remote branch/PR first;
2. inspect any recovery refs the parent pushed for that worker's branch (see Checkpoint compliance) — work captured from a live worker lives there, not on its branch;
3. inspect local worktree only if the container still exists;
4. adopt pushed checkpoints/PR, then apply the recovery ref's ender under
   *The recovery ref's lifecycle* (the caller's where it has one); a lost
   worker cannot return to push it, so neither redundancy nor release will
   end it;
5. redispatch within the task's lost-worker budget (*Concurrency: a ceiling, and the caller sets it*, which states its default) from latest durable remote checkpoint;
6. loss once the budget is spent -> `NEEDS_USER`/infrastructure failure.

If the whole cloud container/workflow disappears, assume local worktrees are lost. Resume from remote branches/PRs, plus whatever durable state the caller keeps.

Never double-apply a repair already pushed by a worker whose runtime status was lost.

## 5. Concurrency: a ceiling, and the caller sets it

**At most 4 workers run at once**, unless a caller bound replaces it
(`backlog-orchestrator`'s `concurrent-workers`, the npm orchestrator's *Dispatch*,
*Bound concurrency*, or a direct invocation argument). The caller also sets a
task's lost-worker budget when it has one (`lost-worker-redispatches` for
`backlog-orchestrator`); otherwise allow **one redispatch** after loss.

Do not increase concurrency merely because the runtime can fan out more agents.

The cap is a ceiling, not a target. At startup choose the lower of it and
machine capacity: CPUs, free disk against the container allowance, and per-worker
dependency installs/test toolchains. Decide and report it without asking.

### Capacity during the run

Recheck disk headroom and worker-slot capacity each cycle. Report current
capacity and worker count; count blocked workers as occupied and report them
as blocked (*Blocked workers*). Stop filling slots before exhaustion.

## Authority, and what it does not cover

A session may carry standing guidance not to use subagents unless the user asked.
**Invoking this skill is that request**: fanning a task set out to isolated
workers is its documented mechanism. Dispatch workers, create worktrees and start
sessions without a separate confirmation.

That authority is scoped to dispatch. It is **not** permission to merge, to push
to a shared branch, to widen the task set beyond what was supplied, or to work
around a platform permission prompt.

**Workers do work; the parent owns policy:** model, supervision, retry budget,
and what can be fixed autonomously. Workers report. The caller's own rule for
autonomous repair governs, never the worker's judgment.

## Verifying what workers report

**A worker's report is a claim** (`references/establish-do-not-assume.md`).
Before relaying or acting on its check results, verify durable state or rerun
outside its environment. Never escalate a reported mass failure unverified.

### Checkpoint compliance

Inspect each in-flight worker on **every supervision cycle**. Where the checkout
is reachable, compare worktree, local branch and remote below; verify/capture
rather than trusting the worker's checkpoint instruction. Where unreachable
(`runtime-remote.md`), only the remote head is observable. Report that
durability depends on worker pushes. For a tier-2 worker with no advancing head,
report at **30 minutes** and raise `NEEDS_USER` at **2 hours**, naming session,
last observed head and unchanged duration. Measure elapsed time since the last
observed advance (or dispatch), across at least two observations, never cycle
count; several cycles within one minute count as one observation. A head
advance clears the stall. Where a channel exists, nudge first as
*Enforce, do not re-ask* specifies; the stall thresholds remain head-based.

| worktree | local vs. tracked remote | state | action |
|---|---|---|---|
| dirty | — | completed edits exist only on disk | capture, below |
| clean | local ahead | committed, push failed or was deferred | push the stranded commits |
| clean | level | nothing saved yet | leave alone unless dispatch was long ago |
| clean | tracked remote absent | merged and deleted, or never pushed | check whether its head is reachable, by the definition under *Releasing a worker*, before treating it as stranded — a forge deletes merged branches routinely. Reachable: nothing to capture, and the releasable test takes it. Not reachable: push the stranded commits |

A clean worktree alone does not establish durability; compare local and remote.
Pushing stranded commits does not change a live worker's index or worktree.

#### Capturing without racing the worker

Never stop, reset, clean or stage into a live worker's checkout/index. A live
worker owns its index and `HEAD`. Capture by worker state:

- **live worker** — build the commit **ref-neutrally** and push it to a **recovery ref**, never to the worker's branch, using the tested implementation beside this skill:

  ```bash
  scripts/checkpoint-capture.sh <worktree> <issue-branch> <worker-head-sha> <issue-owned-paths-file> [remote]
  ```

  `<issue-branch>` means the worker's branch. The paths file lists paths owned
  by this task, one per line: exclude secrets (`.env`, credentials, keys),
  generated/build output and unrelated files; include an untracked file only
  if the task created it. Omit and report uncertain ownership. **Run
  `scripts/test-checkpoint-capture.sh` after editing the script.** Any
  substitute must meet these constraints:

  - Move **no ref the worker holds**. Use scratch `GIT_INDEX_FILE`; write with
    `commit-tree`, not `git commit` (which advances `HEAD`'s ref).
  - Seed the scratch index from worker `HEAD` before overlaying task-owned paths.
  - Before pushing, diff the capture **against its parent** and abort on any
    path outside that list. Run `diff-tree` alone, not piped; use raw `-z`
    pathnames; check grep's exit explicitly; `&&`-gate every step, never rely
    on subshell `set -e`.
  - Keep **one ref per worker branch**, force-replaced on each capture, not one
    per commit. A replacement may move backward in content only when the worker
    changed it. Encode the branch reversibly and injectively in one ref
    component, escaping `%` before `/`: `feature/foo` becomes
    `refs/checkpoints/feature%2Ffoo`.
- **wedged worker** — stop it first, then commit normally onto its branch in the now-quiesced worktree. Stopping consumes that task's lost-worker budget (*Concurrency: a ceiling, and the caller sets it*), so it needs the same evidence any redispatch does.

The worker is the sole writer of its branch while it lives, locally and remotely;
never advance either end underneath it.
Check index, branch and `HEAD` separately before any substitute capture. A
parent snapshot may catch a mid-write file: treat it as WIP, not final. Prefer
the worker's own commit but capture completed edits without waiting for its
checks to finish.

#### The recovery ref's lifecycle

A recovery ref ends when its commits are reachable on the remote (*Releasing a
worker*) or the worker's pushed head carries the same content for **every
captured path**. Until then, report it; never delete it. **At worker release**,
whether or not the worker returned an outcome, reconcile any outstanding
capture into its branch, or push it as that branch if none exists, before ending
the ref. A released worker will not return to push it.

Drop a ref only once a durable carrier the run will read holds its contents.
Direct invocations and `npm-dependency-upgrade-orchestrator` use the generic
ending above. A caller with a PR-state ender (for `backlog-orchestrator`, its
four-state *Checkpoint compliance* rule) replaces the reachability half, while
redundancy and release-time reconciliation still apply. *Blocked workers* and
*Lost workers* apply that caller's ender after consuming a capture.

#### Enforce, do not re-ask

Use the two capabilities established under *Remote worker session arguments*:

| checkout path | channel | action on completed work not pushed |
|---|---|---|
| reachable | present | On first observation, instruct commit and push; if still uncommitted next cycle, parent captures instead of nudging again. |
| reachable | absent | Parent captures on first observation. |
| unreachable | present | Nudge to commit/push once per elapsed-time observation (the same clock and two-observation floor as the stalled-head rule), repeatedly while stalled; then apply stalled-head escalation. |
| unreachable | absent | Apply stalled-head escalation without parent-side capture. |

For an unreachable path, durability rests on the worker's own pushes. An
advancing remote head clears the stall and nudge state. Repeated nudges neither
reset nor defer the head-based thresholds; none waits for acknowledgment.

## Report

State, for the run — alongside what the sections above say to report:

- the **runtime tier** that ran, and any tier probed and rejected;
- the **base branch** every worker was created from;
- per task: assigned **model** and failure-visibility reason; any escalation
  and trigger; if capacity veto changed the tier, what instruction surface was
  measured and which tier it prevented;
- per task: the **watch state**, and for polled tasks when they were last read;
- every task whose watch state is unrecorded, named as a blind spot;
- the two capabilities recorded at startup — whether the parent can reach a
  worker's checkout, and whether it can message the worker — and how each
  session's channel was decided (*Remote worker session arguments*);
- what was **not** covered — tasks deferred, reads skipped, a tier's guarantee
  the runtime could not provide.
