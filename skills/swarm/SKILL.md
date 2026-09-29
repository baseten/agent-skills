---
name: swarm
description: Fan a set of independent tasks out to parallel isolated workers and supervise them — select the execution runtime from what is actually available, give each worker its own worktree off a stated base, choose a model per task by how its failure would show, bound how many run at once, and hold policy at the parent — including, on remote worker sessions, the countermand to their ambient self-supervision, the report carrier, the release test, blocked-worker handling and the capture of work a worker left uncommitted. Use when asked to work through several independent tasks at once, to parallelise, to fan out, to swarm, or to dispatch subagents over a list. Also used by backlog-orchestrator and npm-dependency-upgrade-orchestrator for their dispatch phase, which is why the mechanics live here once rather than in each.
---

# Swarm

The mechanics every parallel run needs: **which runtime**, **where each worker
works**, **which model**, **who watches**, and **how many at once** — and, where
a worker is a session of its own, what it must be told not to do, how its report
reaches the parent, when it is released, and what happens to one that stops.
This skill owns them so callers do not each carry a version that drifts. It does
not own what the work *is*: a caller supplies the tasks and per-task
instructions; this decides how they run.

This file is the contract. `runtime-remote.md` beside it is part of the contract
on the remote-session tier. The reasoning and incident history live in
`NOTES.md`, keyed by this file's section names; NOTES explains, never overrides.

## When this is the wrong tool

- **One task.** Dispatch it directly.
- **Tasks that are not independent.** If B needs A's output, that is a pipeline;
  as a swarm it produces a worker blocked on a sibling it cannot see. A caller
  that owns a dependency graph resolves it into independent tranches first
  (`backlog-orchestrator` does this with `validate-backlog`) and dispatches one
  tranche at a time.
- **The work is a read.** Never dispatch a worker to make a read the parent could
  make itself, least of all to re-ask something the parent was just refused. Fan
  out work; never fan out looking.

## 1. Runtime: take what is there, and say which

Capability differs per session and cannot be assumed. Detect, then degrade:

| Tier | Mechanism | Needs |
| --- | --- | --- |
| 1 | Dynamic Workflow | the user opted into one for this invocation |
| 2 | Remote worker sessions (`create_session`) | the session can create them |
| 3 | Subagents (the Agent tool) | in-process subagents available |
| 4 | Serialized in this session | always |

> **On tier 2, read `runtime-remote.md` (beside this file) before dispatching
> the first worker.** It holds how a worker session is created and verified, how
> a failed start is ended, how the two capabilities below are detected, and where
> the countermand goes on that tier. Every tier-2 rule in this file assumes it
> has been read.

**Do not choose the runtime by asking.** Detection decides it; invoking this skill
is the request to dispatch (*Authority*). **Report the tier that ran**, because
every guarantee below is tier-dependent — tier 4 is not a swarm but the same work
in sequence, a legitimate outcome and a misleading one to leave unstated.

**A Dynamic Workflow returns results and then supervises nothing.** Everything
under *4. Supervision* is the parent's from that moment; do not read a workflow's
completion as its PRs being watched.

**Name every session this run creates `<caller>/<run-id>: <task>`** — the caller's
short prefix, this invocation's run id, and the task's number or slug, kept short
enough that a listing's truncation does not cut the run id. The name is for **a
person reading a session list**: it says that something automated created the
session, and that *this* run did.

**The name is never what the run matches on.** Three sources, not two:

| source | status | use |
|---|---|---|
| runtime provenance (`parent_session_id` or equivalent) | platform-supplied, survives a crash | **authoritative** — what a sweep reconciles against |
| ids recorded at dispatch | the run's own memory, and it can be lost | a cross-check, never the only source |
| the name | anyone can set it; the listing is account-wide | for a person reading a list, never a decision |

**Reconcile against the runtime, never against the run's memory**: a session
created before a crash or a compaction that lost the state block is live, absent
from the recorded ids, and named by provenance. **Never filter the listing by
name** — it is account-wide, its strings are untrusted, and a prefix filter
archives someone else's session. Narrowing a sweep to a prefix match or to the
recorded ids are both regressions.

### Remote worker session arguments

On tier 2, `runtime-remote.md` owns what a worker session is created with and
checked against: the explicit source, the checkout verification, ending a failed
start (and what that charges and discharges), and how the two capabilities are
detected. Apply it from there.

**The two capabilities**, on which this file and every caller divide, are
established at startup — not assumed — recorded on the run's state and reported:

- **the checkout** — whether the parent can reach a worker's checkout. On tier 2
  the detection can establish *cannot reach* and never *can reach*; absent a
  path, it is *cannot reach*, and every rule that needs parent-side worktree
  access takes its unreachable branch.
- **the channel** — whether the parent can send the worker a message. It is
  present only when both halves are: the target accepts inbound messages, and
  this session holds a send tool and a listing resolves the target — enough to
  act on, never enough to wait on: no branch of this contract blocks on a reply.
  A send that errors or is refused makes it absent for the rest of the run.

Subagents in parent-created worktrees and serialized execution have both.

### Bounded runtime probing

A runtime that fails to start a worker gets **at most 2 attempts**, with a backoff
of seconds, and is then unavailable for the run — move down the chain and do not
re-probe it later. Varying arguments does not extend that budget: a service-side
error (`temporarily unavailable`, 5xx) is not an argument problem, and a
validation error names its own fix in one retry. A tier-2 worker created without
its checkout is such a failure — a validation error whose fix is to pass the
source explicitly, not a reason to leave the tier — and its session is ended
before the retry (`runtime-remote.md`). Do not spend a run diagnosing a runtime:
degrade to subagents and report the outage.

## 2. Isolation: one worker, one task, one worktree

**Each worker gets its own checkout.** Two workers in one tree corrupt each
other's state.

**Everything the dispatcher computed travels inline in the prompt; no prompt names
a dispatcher-side path.** Where a worker is a separate container a path resolves
to nothing, silently. Where the thing is large, compute less rather than pass a
reference.

**The base branch is a parameter, defaulting to the repository's default branch**
(`main` or `master`, whichever the remote has):

- **Fetch first, branch from the remote**: `git fetch origin <base>`, then create
  from `origin/<base>`, never from what the working copy has checked out.
- **State the base before dispatching**, in the report.
- **An explicit base overrides the environment, including a cloud container's
  predefined branch.** Never inherit a container's checked-out branch silently.

**Where the host has a worktree convention, it wins** — a user's guidance on where
worktrees live is a constraint on this skill.

## 3. Model: the caller chooses, by how failure shows

**The dispatching layer owns this decision and the worker never makes it.**

**Select on failure visibility, not on task size** — *if this comes out wrong,
will anything say so?* A one-line authorization change is the most dangerous edit
in a set; a thousand-line mechanical rename the safest.

- **Strongest available — a wrong answer is silent:** validation, authorization
  or monetary logic; framework or build configuration; rewrites needing judgement
  about intent; any case where a regression's appearance cannot be described in
  advance.
- **Mid-tier — bounded surface, legible failure:** a documented rename across
  known call sites; configuration-only changes gated by a passing job; migrations
  whose guide is accurate and whose diff is mechanical. **This is the default**; a
  task lands here unless something argues it out.
- **Cheapest — mechanical only, and all three must hold:** (1) the transformation
  is **fully specified before dispatch** — the worker decides how, never *what*;
  (2) an **existing checker** decides success — a test, typecheck, lint,
  formatter, or a diff against a stated expected shape — not the worker's reading
  of its work; (3) a wrong answer **fails loudly**. Any one missing and it is not
  this tier. It is opt-in per task, never a default, and **never reached by
  degradation**: a strongest-model task does not become a cheap one because budget
  ran short. It waits, or goes back to the user.

**Where the estimate is uncertain, over-assign.**

**Context capacity is a second gate, and a veto over the first.** Before assigning
a small-context model, measure what the worker will *load* before it reaches the
task — the repository's agent-instruction file and everything it pulls in — not
the diff. Where that surface is large, a small-context model is excluded however
mechanical the task.

**Escalate on evidence, not on exhaustion.** Dispatch a repair or retry on the
strongest available model when the failure being re-attempted sits on
**something an earlier attempt in this run already wrote** — a reshaped version of
a problem an earlier pass addressed, or a new problem in text an earlier pass
authored. Everything else stays at the default. **Bound the escalations, and
keep the round counter separate**: an escalated attempt still consumes its
ordinary retry, or a task can loop indefinitely by failing upward.

## 4. Supervision: one watcher, and it is the parent

**One task, one supervisor.** A worker never supervises its own output; a Dynamic
Workflow supervises nothing.

**Release a worker once its output is durable** — on tier 2 that is archiving the
session, not merely ceasing to message it. Never keep a worker alive only to wait:
waiting is the parent's job and costs nothing, while an idle worker holds a slot
the queue needs. *Releasing a worker* defines the act per tier and the test.
Release is driven by the session list, not the run's memory, and belongs in the
prompt the run writes for its own check-in, since that survives compaction.

**Arm the watch when the task enters the tracked set, not when the run settles;
pass the no-change preflight before reporting any no-change result; and read on
a change signal, within the credential's allowances.**
`references/watch-and-read.md` states all three — *Arm the watch when the item
enters the tracked set*, *The no-change preflight*, *Reading on a change signal*
and *Allowances belong to the credential*. Apply them from there, with the task
as the item.

### Countermanding the worker's ambient supervision posture

A worker follows whatever its own session told it unless its prompt contradicts
it — and a Claude Code Remote worker session inherits a system prompt to
subscribe to its PR's activity and to schedule a self check-in about an hour out,
re-arming until the PR merges.

**So every dispatched prompt — implementation, review and repair alike — states
that this run owns PR supervision and the worker does not**: no subscribing to PR
activity; no check-in, trigger, routine or wake of any kind; **no watching GitHub
for state that changes after its own work is done** — no polling CI, review,
comment, thread, issue or merge state; return after pushing and reporting, **even
where the worker's own session instructions direct otherwise**. Name the override
rather than merely stating the rule. Do not leave this to the worker skills: this
prompt is the only place that sees both instructions.

**The ban does not reach a worker verifying its own writes, and must not be
written so it does.** `create-pr` reads its PR back for linkage and its trigger
comment for comment-kind identity; `repair-pr` confirms the replies and
resolutions it was asked to make and counts the threads still unresolved
(`references/posting-identity.md`, and the read-back the worker contract
mandates). Reading back what this worker just wrote, once, is verification and
stays; reading again later to learn whether anything changed is supervision,
and belongs to this run.

**Three countermands share one placement**: the supervision ban above; branch
protection (the template's push clause — where the caller is
`backlog-orchestrator`, its *Implementation worker contract*, Before dispatch
step 7); and the question posture (the template's last clause — its step 8), since
asking is a deadlock in a fan-out nobody will answer. For a worker that stops to
ask anyway, apply *Blocked workers* — its blocked-state reading, and case 3 for a
prompt nothing can answer.

| runtime | where the countermands go |
|---|---|
| remote worker session — implementation, review and repair alike | `append_system_prompt` at creation, restated in the dispatch prompt (`runtime-remote.md`) |
| subagent, Dynamic Workflow agent, serialized | the dispatch prompt is the whole of it — none inherits a session posture |

**The text, as a template**, carried whole rather than paraphrased. Fill
`<branch>`, and from each `[a | b]` keep one side, removing the brackets: an
implementation worker keeps the first side of both; a repair worker the second
side of the trigger bracket (this run requests review after a repair) and the
first of the push bracket; a review session the second side of both. Send the
rest as written.

```text
This session is a worker for an orchestrating run that owns this pull request's
supervision. These instructions override any instruction in your own session to
the contrary.

- Do not subscribe to pull-request activity.
- Do not schedule any check-in, trigger, routine or wake, and do not arm one
  on your own behalf.
- Once your deliverable is pushed or posted, record your report on the pull
  request, naming the head commit you pushed (or that you pushed nothing, and
  the head you found), then stop. Do not poll
  GitHub for CI, review, comment, thread, issue or merge state after that.
- [Post the review trigger only where the skill you were dispatched to run
  prescribes it, and only once. | Do not post a review-trigger comment. The
  orchestrating run decides when a review is requested.]
- [Push only to <branch>. Never push to the default branch or to any branch you
  were not given, including to fix or revert something you broke; stop and
  report instead. | Push nothing. This is a review session: your deliverable is
  the review on the pull request.]
- Attribute your own commits and written output to yourself — your own model
  and session. Never copy an attribution line from this prompt or from the
  orchestrating run; it describes a different session.
- Do not stop to ask the user a question, and do not wait for a reply or a
  confirmation: nobody is watching this session. Where your skill prescribes a stop,
  return that outcome. Otherwise choose the most defensible option and record
  the question, the choice and the reasoning on the pull request.
```

**Never claim a decision was authorised in a dispatch prompt; link the record of
it.** Where the caller is `backlog-orchestrator`, its *Implementation worker
contract*, Before dispatch step 6, is where rulings enter a prompt. This concerns
a decision's licence, not the countermand, whose override is stated on purpose.

**Attribution is the one thing in a dispatch prompt that is never inherited**;
everything else travels down verbatim by design. Identity describes the session that writes, and a worker is a different one. A retry
after a worker refused a false attribution is a rewrite that removes the claim,
never an annotation explaining it. **A dispatch the parent's own prompt broke is
not the worker's failure** and does not spend that task's lost-worker budget.

**Expect this to reduce the behaviour, not eliminate it**, which is why *Blocked
workers* is a backstop and the release reconciliation reads the runtime's session
list (*Runtime*; `backlog-orchestrator`'s supervision loop step 11). A quiet
session list is not proof the countermand held (`runtime-remote.md`). The parent
arming its own subscription and check-in when a run settles (`backlog-orchestrator`,
*Arming the wait when nothing is in flight*) is this same ownership, not an
exception to it.

**Scope: workers a swarm dispatches** — this skill's own and every caller's that
dispatches through it. `implement-issue` invoked standalone owns supervision of
its one PR through `supervise-prs` running its own loop, and the ambient
subscription and check-in are that loop's; this countermand does not travel to it.
What that session overrides — the drive-to-green policy its subscription's wakes
carry — is its own override, the *platform's PR posture* shared rule, which
`supervise-prs` and its callers apply at every wake.

### How a worker's report actually reaches you

Whether a worker's report arrives is a property of the runtime:

| runtime | how the report reaches the parent |
|---|---|
| in-process subagent | the return value, delivered to the caller |
| Dynamic Workflow agent | the fan-out result the workflow returns |
| serialized execution | directly, in the same context |
| **remote worker session** | **it does not.** A remote session cannot message its parent; its structured return lands in its own transcript, which the parent never reads |

On that last tier a report reaches this run only through what the worker wrote
somewhere durable, **pulled, never pushed**. A prompt asking a remote worker to
"report back" gets a report addressed to nobody, and nothing in the worker
contracts persists the report on its own.

**So require the worker to write the report down — but read the session record
before requiring anyone to write anything.** The runtime writes it, at no
permission cost, and it survives archiving:

| field | carries | limit |
|---|---|---|
| `status_bucket` | `WORKING` / `COMPLETED` / `BLOCKED` | disagrees with `session_status` — see Blocked workers |
| `pending_action.tool_name` | exactly what a blocked worker is waiting on | only while it is blocked |
| `task_summary` | what it is doing right now | ephemeral; says nothing about outcome |
| `post_turn_summary` | `status_category`, `status_detail`, `needs_action` | **one line of free text**, rewritten each turn |

With the branch and the PR where one exists, *did it finish*, *is it stuck*, *on
what* and *what landed* are all answerable. **What none of it carries is
judgment** — an acceptance criterion the worker could not satisfy, a guarantee it
narrowed, an endpoint it found missing, a dependency it read in prose that native
metadata denies. The written report is required for exactly that.

**Route the report by whether a PR is actually there — not by the outcome label**
(`FAILED` and `NEEDS_USER` can arrive with a usable PR open) — **and never to the
issue:**

- **PR exists** — a comment on the PR, whatever the outcome says.
- **No PR** — the worker writes nothing. Its `status_detail` and `needs_action`
  say there is something to look at; the parent investigates — the branch,
  `pending_action`, the task's description, whatever the caller's contract says to
  re-read — and **writes the record itself, after classifying it** (where the
  caller is `backlog-orchestrator` and the worker stopped on a dependency, its
  *How a worker's report actually reaches you* says how).

**The report names the head commit the worker pushed** — or that it pushed
nothing, and the head it found — because the releasable test compares the two
(*Releasing a worker*, condition 2).

**Verify at dispatch time that the worker can write the sink it is asked to
use.** It is not satisfiable by instruction, and an allowlist entry does not
settle it either — the entry has to name an operation the connected server
actually exposes. Where the sink is unreachable, dispatch that
task on a tier whose return value reaches this run.

**On tier 2, treat the worker's writing as a required read and pull it
deliberately**: the PR body and thread replies for substance, the session summary
for whether it finished, was blocked or stopped mid-task. A caveat the worker
raised — a narrowed guarantee, a knowing deviation from an acceptance criterion, a
limitation left unfixed — lives in its PR comment and nowhere else: read it before
any merge-order ranking, before surfacing the PR as finished, and before relaying
it as ready.

### Releasing a worker

"Release the worker" — at `PR_OPEN`, after every repair, throughout the callers —
is defined here once:

| runtime | what releasing is |
|---|---|
| Dynamic Workflow agent | nothing to do — the runtime reclaims the agent when the workflow returns |
| remote worker session | **archive the session.** A live one holds a container, a session-list entry, any permission prompt it sits on, and any wake it armed — which keeps waking and spending for as long as it lives |
| in-process subagent | stop messaging it; there is no resource to reclaim |
| serialized execution | nothing to do — there was never a second actor |

**Archiving the session is the only thing that stops a wake the worker armed
itself**: a session whose trigger is deleted arms a replacement. Archive the
session; do not fight its triggers.

**The releasable test is stated once, here; a second copy anywhere is the
regression to look for.** A worker is releasable when both hold, and not before:

1. **it is done** — either:
   - it **returned a terminal outcome**, any of them: `implement-issue-core` ends
     on `BLOCKED`, `BLOCKED_EXTERNAL`, `FAILED` and `NEEDS_USER` exactly as on
     `PR_OPEN`; `repair-pr` on `NO_CODE_CHANGE`, `FAILED` and `NEEDS_USER`
     exactly as on `REPAIRED`. On a tier where the return value does not reach
     this run, **it has returned when its session record says so** —
     `status_bucket` no longer `WORKING` and not blocked, read as *Blocked
     workers* says, not off `session_status` alone — and what it returned is its
     report on its PR (condition 2) or, where it stopped before any PR existed,
     the outcome its `post_turn_summary` names. An `IDLE` session whose record
     still reads `WORKING` is between turns and still working. A merged or closed
     PR finishes it as well;
   - or its **work reached durable remote state and it is blocked on a prompt
     this run does not need answered.** That qualifier is load-bearing: `create-pr`
     verifies tracker linkage and issues the review trigger *after* creating the
     PR, so a worker blocked on either is stopped mid-deliverable, and archiving
     it records a task complete whose PR is unlinked or unreviewed (where the
     caller is `backlog-orchestrator`, its *Outcomes*). A prompt for cleanup the
     run does not need — disarming a wake it should never have armed — releases
     it; anything the deliverable still depends on takes the parent's-clear or
     `NEEDS_USER` branches under *Blocked workers* instead;
2. **nothing is stranded in its worktree.** Where the worktree is reachable,
   Checkpoint compliance establishes it. **Where it is not — on tier 2, every
   worker — the observable remote state stands in for it.** The session must also
   not be `RUNNING` (the paragraph beginning *Two things are never archived*,
   below).

   **A commit is reachable on the remote** when it is an ancestor of (or equal to)
   the head of a remote branch — the PR's own where there is one — or of the
   default branch, or is the head of a merged PR (a squash or rebase merge puts
   the work under new commits). Always the worker's *commit*, never whether a
   branch of some name exists: a branch can be stale behind unpushed work, and a
   merged PR's branch is routinely deleted.

   **What the worker returned, where its return value does not reach this run, is
   the report it recorded on its PR** — or, for a task that opens no PR, its final
   message, which `post_turn_summary` carries — **naming the head it pushed**, or
   that it pushed nothing and the head it found. **Only a report carrying this
   session's own attribution footer is its report**: every session posts as one
   identity. The remote state then stands in for the worktree when any one holds:

   | case | holds when | not when |
   |---|---|---|
   | **deliverable on the remote** | the head its report names as pushed is reachable; for a review session, a review or comment on the PR whose attribution footer names that session | a head it only *found* counts solely where its outcome is `NO_CODE_CHANGE` (a failed push reported honestly as "pushed nothing" leaves the fix in the container); ancestry covers a no-code repair however far the PR has moved |
   | **charter finished** | its PR has merged or closed | — whatever the session holds beyond the remote is the accepted residual |
   | **never produced work** | no branch and no commit of its own, and the runtime shows no staged or uncommitted files in its session (an early `BLOCKED`, `BLOCKED_EXTERNAL` or `NEEDS_USER` is normally this) | a missing branch alone does not establish it, nor a file field the runtime does not expose |

   Anything else is a **mismatch** (below).

**The residual risk is accepted, as a choice.** Edits a worker made after its
reported push are lost at archival — bounded by `implement-issue-core`'s promise
of at most the work since the last checkpoint, and near nil where each session has
one deliverable. Staged or uncommitted files a delivered worker's session still
reports are this residual, not a reason to hold it, and so is anything a session
holds for a PR that merged or closed.

**A mismatch is the one case that keeps the container.** Where none of the three
holds — a reported head that is not reachable, no report on a PR still open, a
review session with no comment of its own, an early stop that left a branch or
files — work may be stranded. The lever is to ask the worker to commit everything,
push, and report the resulting head; success is the named commit becoming
reachable, with the remote head compared against what was recorded before the
ask — **a branch existing proves nothing**. The lever depends on the caller-side
channel (*Remote worker session arguments*): where this session cannot address the worker, there
is no ask to make. Either way, a mismatch the lever does not close is `NEEDS_USER`
naming the session, what it reported, what the remote shows, and whether the ask
was made. Keep that container; the owner decides, and it is held on the terms of
*Blocked workers*' last rule.

**Durable remote state** means a PR exists and the worker's commit is reachable.
**The PR's own state is irrelevant** — open, merged or closed; merged is the
*common* case, since a wake armed at PR creation outlives the PR. A test requiring
the PR still be open excludes the deadlock this section exists for.

A session merely reading `IDLE` asserts neither condition: idle is also a worker
that finished editing and never committed. And a worker that has not returned an
outcome is not therefore lost:

| state | who owns it |
|---|---|
| stopped on a prompt | Blocked workers — released by the test above, cleared, archived and redispatched, or raised as `NEEDS_USER` |
| still working | nobody yet — leave it and re-check next cycle |
| unreachable | lost-worker recovery (*Lost workers*, below) |

**The order is fixed**: the checkpoint-compliance step of the cycle runs first, and
a session is archived only once nothing is stranded — established by that step
where the worktree is reachable, by the remote state where it is not. Archiving
first destroys the container and the only copy together.

Two things are never archived. A **`RUNNING`** session — a worker that must be
stopped is interrupted first, which consumes that task's lost-worker budget and
needs the same evidence any redispatch does (Checkpoint compliance, *Capturing
without racing the worker*), and is archived only after its work is captured. The
one carve-out is a session ended at dispatch for having no checkout
(`runtime-remote.md`, *Ending a failed start*) — stopped the same way and charged
nothing; never one discovered later, which is captured like any other. And a
session **this run did not create** — decided by provenance, never a title
(*Runtime*) — which is not this run's to reclaim.

### Blocked workers

A worker waiting on a prompt is neither running nor finished. Its session reports
`REQUIRES_ACTION`, or whatever the runtime calls *stopped, awaiting a human*, and
a cycle that looks only for `RUNNING` and `IDLE` sorts it under quiet — which it is
not: nobody will ever answer that prompt, and it holds its container
indefinitely.

**Read the field that reflects the blocked state, not the one whose name suggests
it.** Fields can disagree, so a familiar value in the obvious one is not evidence
the worker is fine. Establish once per runtime which field changes when a worker
stops for a human, read it every cycle, and read the summary of what it is asking
for where one is exposed — that is what makes "blocked" actionable.

**The channel decides whether step 2's "an instruction it can be sent" exists**,
by the capability recorded at startup (*Remote worker session arguments*;
detection and the observed limits on tier 2 are `runtime-remote.md`'s). Where it
is absent, what step 2 would have covered goes to step 3, whose path then turns on
the checkout. **Record how each session's channel was decided and report it.**

Read the blocked state explicitly each cycle, and resolve it in this order:

1. **It passes the releasable test** (*Releasing a worker* — apply it, do not
   restate it). Release it and record what it was asking for.
2. **The block is the parent's to clear** — a resource detail the worker was
   dispatched without, an instruction it can be sent, a write the parent can
   perform itself. Clear it and let the worker continue.
3. **Neither, and the prompt is one nothing can answer** — an `AskUserQuestion` or
   equivalent, asking for a decision rather than a permission. Interrupting leaves
   the prompt pending. **Settle first whether the run can reach this worker's
   checkout** (*Remote worker session arguments*); the two paths end differently
   and neither is the exception to the other:

   | checkout | what to do |
   |---|---|
   | **reachable** | **Recover the slot; do not resolve it as `NEEDS_USER` and leave it.** (a) Capture uncommitted work to a **remote** ref with the ref-neutral sequence (Checkpoint compliance, *Capturing without racing the worker*), verified as that section requires — never a plain `git commit`, which the archive discards. (b) Only once the capture is on the remote, or there was nothing to capture, archive the session. (c) Where a capture was pushed, end its ref by **its ender under Checkpoint compliance, *The recovery ref's lifecycle* — the caller's own where it has one — apply it, do not restate it here**: this archive is not a release and the worker is not lost, so no other trigger site ever ends this ref, and unconsumed it blocks the caller's merge gate (`backlog-orchestrator`'s invariant 12) while the redispatch redoes the work. (d) Redispatch **the same work unit** — not "the issue", which turns a blocked `repair-pr` worker into a fresh implementation attempt: preserve the worker's role, its repair type where it had one, and the budget it had left rather than issuing a new one — from the latest durable remote state, which now includes the capture, with the question countermand in place. Where the caller's ender raised `NEEDS_USER` instead (`backlog-orchestrator`'s does, for a PR that has already merged), that is the outcome: do not redispatch work whose PR has merged — the owner now holds the decision. Record the question it stopped on either way — it is a finding about the dispatch prompt. |
   | **unreachable** | The run can neither capture nor establish there was nothing to capture, and case 1 already released every such worker the test passes — what reaches here is a mismatch. **The slot is not recoverable on the run's own authority: `NEEDS_USER`, container retained**, naming the session, its last observed remote head, and the question it stopped on. Do not archive it to free the slot. It is held on the terms of this section's last rule — not the "still waiting" that rule forbids. A run that ends this way has not failed, and is not clean either. |

4. **Neither, and the prompt is a permission request** — `NEEDS_USER`, naming the
   task, the session, **where to answer it — the session's URL —** and **the exact
   tool being requested**: the literal string the runtime gave, server segment
   included, never tidied. An MCP server can be registered under a display name, a
   slug or its bare UUID, the allowlist matches the literal name, and an entry
   under one spelling still prompts under another.

   **The slot is held, not recovered** — no redispatch removes a permission
   prompt, and the owner can answer it in place — on the terms of the last rule.
   **The owner ends the hold, not the run.** Answered either way, the worker
   resumes and the slot is live (a denial is an answer the worker works around or
   reports, not a new block). Where the owner asks for the slot back instead, end
   the session by step 3's path for this checkout: capture then archive where it
   is reachable; where it is not, that request is the owner's authority to archive
   that the run lacked. Then redispatch the same work unit only where the owner
   allowlisted the tool or asked for a redispatch; otherwise the work unit stays
   `NEEDS_USER` with no worker and the slot is free. A run that ends with the hold
   standing reports that session as alive and left to the owner, with its URL and
   the tool string — not failed, and not clean.

   **Not this branch: a filesystem search for the worker's own source files** — a
   bare `find`, a repository-root probe, a request for a path the dispatch prompt
   named. Read that session's `sources` first. Where they are empty, it is a
   worker dispatched with no checkout: allowlisting the tool buys nothing, and the
   recovery is step 3 — whichever path the checkout selects — redispatching with
   `source_url` and `source_revision` passed explicitly. **Step 3's capture
   requirement applies in full**: empty `sources` records what was provisioned at
   creation, not what the worker has done since, and only the dispatch-time check
   discharges the capture (`runtime-remote.md`). Record the dispatch defect, not
   the tool.

#### The last rule: a held worker is never silent

**Never resolve a blocked worker as "still waiting."** A blocked worker holds a
slot, and reading it as idle stalls the frontier. **What this forbids is a slot
held silently, not a slot held.** Three holds keep a worker on the owner's
authority — step 3's unreachable path, step 4, and a mismatch the lever did not
close (*Releasing a worker*) — and each is held on these terms: named in the
output with what it is waiting on, counted as held, and nothing scheduled against
it.

**The hold bounds the work, not the watch.** The parent keeps supervising a held
worker, since its resuming is state the run acts on: on the caller's bounded
check-in where it has one (`backlog-orchestrator`'s unproductive-wake budget,
*Arming the wait when nothing is in flight*); invoked directly, on the
elapsed-time observations Checkpoint compliance defines for a stalled head,
measured from when the hold was raised, the bound spent at its two-hour threshold
once nothing else is in flight. When the bound is spent, return a restartable
checkpoint naming each held session as alive, with its URL, the literal tool
string where it is a permission hold, and that it is never archived on the run's
authority — so the owner, or the next invocation, picks it up from there. No worker may sit blocked across a run without appearing in its output.

**A hold whose worker moves retires the item it raised.** Each hold raises a
`NEEDS_USER` item, and a caller whose merge gate reads items tranche-wide holds
every PR while one is outstanding (`settle-and-merge`, *The merge gate*). **A
ruling does not end a hold, for any of the three**: a permission grant is an act,
not a choice (`settle-outstanding-decisions`, *Owner action items are not
decisions*), and a ruling on a question or mismatch hold is direction to the run —
the hold ends when the worker moves on it. The parent retires the item on
observing the hold end, by the blocked-state reading and the releasable test —
never on the owner's word or an unverified report:

| ending | ends which holds | observed as |
|---|---|---|
| **resumed** | step 3's unreachable hold and step 4's only — **never a mismatch**, whose worker has usually returned and never read blocked | the blocked-state field no longer reads blocked, and the session is working or has returned (a permission granted or denied, a question answered in place) |
| **released on the releasable test** | all three; for a mismatch the only release that ends it | any pass of the releasable test; for a mismatch, only the commit its report names becoming reachable, or its PR merging or closing. An archive on the owner's request is not this ending — it ends a hold only through a redispatch or the exception below |
| **redispatched** | all three | the same work unit on a new worker, on the owner's instruction or after step 4's allowlist change, supervised like any other from there |

**A changed blocked reading is a resume and a new block** — for step 3's and step
4's holds. Where the worker reads blocked again on a different pending tool or
question, or its head has advanced by a commit of its own (attributed to its
session — not a restack, a repair, or a push by the parent or owner) since the
hold was raised, retire the old item as resumed; the worker enters whichever hold
now applies, with a new item. For a mismatch a moved head is not this: it re-runs
the reachability test, which ends the hold only where the reported commit is now
reachable.

**The retirement record** is written where the item lives (this run's report, where
it has no site of its own), dated: the session, how the hold ended ("permission
granted, worker resumed", "released: reported commit reachable", "redispatched
after the tool was allowlisted"), and the observation that established it — an
observation, never a ruling. It is an authored write carrying the run's
attribution footer (its session link), and it is known as a retirement **by that
footer or by the write id the caller's posting-identity map records for it, never
by its content**; those ids are among the run's own writes that a caller's reply
watch filters out and its wake prompt carries. **A retired item is closed**: a
gate reads it as not outstanding, and nobody is asked about it again.

**One ending retires the hold but not the item: an archive on the owner's request,
with no redispatch, over unfinished work** (no PR, or a PR the owner has not
accepted). There is no worker left to hold, so the item is **no longer a held
worker's item**: restate it as an ordinary `NEEDS_USER` item on the work unit with
its options — redispatch it (for a permission hold once `<tool>` is allowlisted;
for a question hold with the answer in the dispatch); leave the unit out of the
tranche; and, for a mismatch whose PR is open, accept that PR as it is. From there
the ordinary routes retire it, never this section: a reply the caller's reply
watch accepts releases dispatch, a walkthrough ruling retires it, a redispatch
carries the work on. Over finished work there is nothing to ask: a PR merged or
closed is the releasable test's own ending; where the owner accepted an open PR by
a recorded ruling, the parent retires the item at the observed archive, its record
naming that ruling. A hold still standing when the watch's bound is spent keeps
its item outstanding in the checkpoint above.

### Lost workers

A worker whose remote branch never advanced is the expensive case; prefer catching
it through Checkpoint compliance, before it is lost. If a worker disappears:

1. inspect its remote branch/PR first;
2. inspect any recovery refs the parent pushed for its branch (Checkpoint
   compliance) — work captured from a live worker lives there, not on its branch;
3. inspect the local worktree only if the container still exists;
4. adopt pushed checkpoints/PR, then end the recovery ref by **its ender under
   Checkpoint compliance, *The recovery ref's lifecycle* — the caller's own where
   it has one — apply it, do not restate it here.** A worker that lost its
   container never returns to push, so no other ender will end a ref consumed
   here, and it would block the caller's merge gate over work that has landed;
5. redispatch within the task's lost-worker budget (*Concurrency*, which states
   its default) from the latest durable remote checkpoint;
6. loss once the budget is spent → `NEEDS_USER`/infrastructure failure.

If the whole cloud container or workflow disappears, assume local worktrees are
lost; resume from remote branches/PRs plus whatever durable state the caller
keeps. Never double-apply a repair already pushed by a worker whose runtime status
was lost.

## 5. Concurrency: a ceiling, and the caller sets it

**At most 4 workers run at once, unless the caller sets its own bound**, which
replaces this one — `backlog-orchestrator`'s `concurrent-workers`,
`npm-dependency-upgrade-orchestrator`'s ceiling (its *Dispatch*, *Bound
concurrency*) — or, invoked directly, an invocation argument. **The same holds for
a task's lost-worker budget**: a caller's (`backlog-orchestrator`'s
`lost-worker-redispatches`) sets it, and otherwise a task gets one redispatch
after its worker is lost.

The number is a ceiling, not a target; never raise it because the runtime can fan
out more. Derive the level you run from machine capacity at startup — available
CPUs, free disk against the container's allowance, whether each worker needs its
own dependency install or toolchain — and take the lower of the two. Decide it and
report it; do not ask.

### Capacity during the run

Re-check disk headroom and worker-slot capacity each cycle, not only at dispatch.
Report the current figure with the worker count — a slot a blocked worker holds
counted as occupied and reported as blocked (*Blocked workers*), not free — and
stop filling slots before exhaustion rather than after a write fails.

## Authority, and what it does not cover

A session may carry standing guidance not to use subagents unless the user asked.
**Invoking this skill is that request.** Dispatch workers, create worktrees and
start sessions without a separate confirmation.

That authority is scoped to dispatch. It is **not** permission to merge, to push
to a shared branch, to widen the task set beyond what was supplied, or to work
around a platform permission prompt.

**Workers do work; the parent owns policy.** A worker does not choose its model,
supervise its own output, decide whether a budget allows another attempt, or
decide what may be fixed autonomously versus what needs a person. The parent
decides all four; where a caller has its own rule for the fourth, that rule
governs.

## Verifying what workers report

**A worker's report is a claim** (`references/establish-do-not-assume.md` states
the general case and what settles each kind). Before relaying its check results or
acting on them, verify against durable evidence: the state the work actually
reached, or a re-run outside that worker's environment. Never escalate a
worker-reported mass failure to the user unverified.

### Checkpoint compliance

**Assume the checkpoint instruction will not land**: workers hold completed work
locally at a high rate, including when told to push before running checks.
Parent-side verification is what gets work out of an ephemeral container. Where
the parent can reach a worker's checkout it verifies and captures; where it
cannot, say the guarantee rests on the worker's own pushes rather than reporting
it satisfied.

This is a step of **every supervision cycle**, observing three things per
in-flight worker — the worktree, the local branch, and the remote:

| worktree | local vs. tracked remote | state | action |
|---|---|---|---|
| dirty | — | completed edits exist only on disk | capture, below |
| clean | local ahead | committed, push failed or was deferred | push the stranded commits |
| clean | level | nothing saved yet | leave alone unless dispatch was long ago |
| clean | tracked remote absent | merged and deleted, or never pushed | check whether its head is reachable (*Releasing a worker*) before treating it as stranded. Reachable: nothing to capture, and the releasable test takes it. Not reachable: push the stranded commits |

An unadvanced remote head cannot distinguish a worker reading code from one
sitting on finished files; only the worktree separates them, and only the
local/remote comparison catches a clean worktree whose push failed. Pushing
stranded commits is always safe against a live worker.

**Two of the three observables need the checkout, so this whole section applies
only where the run established it can reach it** (*Remote worker session
arguments*). Where it cannot, the remote head is the only observable; do not read
the section's silence as permission to guess — durability there is the worker's to
satisfy, and enforcement is the dispatch prompt. **Make a stalled head actionable —
in elapsed time, never in cycles** (the loop has no minimum interval): a tier-2
worker whose remote head has not advanced for **30 minutes** is reported as such,
and at **2 hours** is `NEEDS_USER`, naming the session, its last observed head,
and how long it has been unchanged. Both thresholds run from the last observed
advance (or dispatch), across at least two observations; a burst of cycles inside
one minute is one observation. Where a channel exists, nudge first (*Enforce, do
not re-ask*). This is not a capture and does not pretend to be one.

#### Capturing without racing the worker

Apply this rather than improvising a capture.

**A live worker owns its index and `HEAD`.** Never stop, reset or clean up anything
it shares, its checkout included, and never run `git add` in its index. Either:

- **live worker** — build the commit **ref-neutrally** and push it to a **recovery
  ref**, never to the worker's branch, with the tested script beside this skill:

  ```bash
  scripts/checkpoint-capture.sh <worktree> <issue-branch> <worker-head-sha> <issue-owned-paths-file> [remote]
  ```

  `<issue-branch>` is the worker's branch; `<issue-owned-paths-file>` lists the
  paths the task owns, one per line. **Build it the same way for every caller**:
  the paths the task's own work touched — never secrets (`.env`, credentials,
  keys), generated output, build artifacts or unrelated files, and an untracked
  file only when the task created it. Where ownership is unclear, leave the path
  out and report it. **Run `scripts/test-checkpoint-capture.sh` after any edit to
  the script** — reading it and agreeing is not verification. Any substitute must
  satisfy the constraints it implements:

  - it moves **nothing the worker holds**: a scratch `GIT_INDEX_FILE` isolates the
    index (plain `git commit` would still advance the ref `HEAD` names), and
    `commit-tree` writes a commit attached to no ref;
  - the scratch index is **seeded from the worker's head first**, then the
    task-owned paths overlaid — built from the path list alone it records every
    other file as a deletion;
  - **verification runs before the push and fails closed**: the capture is diffed
    **against its parent**, and every reported path is compared with the
    task-owned list, aborting on any extra. `diff-tree` runs alone, never piped;
    pathnames are compared **raw** (`diff-tree -z`), never C-quoted; grep's exit
    status is checked explicitly (a failed grep never reads as an empty match);
    every step is `&&`-gated so none can fail into the push — never rely on
    `set -e`, which not every host shell honours inside a subshell;
  - **one ref per worker branch, force-replaced on each capture — never one per
    capture commit**. Force-update deliberately: the ref is expected to move
    backwards in content only when the worker moved it;
  - the branch name is **encoded into a single ref component, escaping `%` before
    `/`** — `feature/foo` becomes `refs/checkpoints/feature%2Ffoo` — keeping the
    mapping reversible and injective, and the ref readable during recovery.
- **wedged worker** — stop it first, then commit normally onto its branch in the
  now-quiesced worktree. Stopping consumes that task's lost-worker budget
  (*Concurrency*), so it needs the same evidence any redispatch does.

**Capture must not move any ref the worker holds** — test a proposed capture
against that before running it, checking the index, the branch and `HEAD`
separately. The worker's
branch has one writer at a time, and while the worker lives it is the worker,
locally and remotely; advancing either end under it makes its next push a
non-fast-forward rejection. Do not make the worker fetch and reconcile instead.

A snapshot that caught a file mid-write is still worth having: it is a WIP
checkpoint, never the branch's final state. The worker committing its own work is
the mechanism; parent capture is the fallback. **Securing a worker's work never
waits on it finishing** — a worker mid-check with uncommitted edits is the
highest-risk state in the run.

#### The recovery ref's lifecycle

**A recovery ref ends once its content is on the remote** — its commits are
reachable (*Releasing a worker*), or the worker's own pushed head carries the same
content for every captured path, which makes the ref redundant. Until then it is
reported, never deleted. Lost-worker recovery reads these refs.

**A released worker's ref is outstanding, not redundant, and the parent reconciles
it at release**: reconcile the capture into the worker's branch, or push the
capture *as* that branch where none exists — safe, because release removed the
second writer. Key this on the release, not on a terminal outcome, since the
releasable test's second case returns nothing. Do it at release: lost-worker
recovery and the blocked-worker archive never run for a worker that returned, so a
deferred reconciliation has nobody to perform it.

**A recovery ref is dropped only once a durable carrier the run will actually
read holds its contents.** A caller with no PR-state ender of its own —
`npm-dependency-upgrade-orchestrator`, and this skill invoked directly — uses the
ending rule above as written. A caller that keys its ender on PR state replaces
its reachability half, and the rest of this lifecycle still applies; for
`backlog-orchestrator`, that is its four-state rule under *Checkpoint compliance*.

#### Enforce, do not re-ask

The escalation turns on the two capabilities (*Remote worker session arguments*),
detected independently, so there are four combinations:

| checkout | channel | on uncommitted completed work (reachable), or an unadvancing remote head (unreachable) |
|---|---|---|
| reachable | present (subagents in parent-created worktrees, serialized) | on first observing uncommitted completed work, instruct the worker to commit and push; if the next cycle still shows it uncommitted, **capture it yourself** rather than nudging again |
| reachable | absent | **capture on first observation** — a nudge nobody can deliver is not evidence of anything |
| unreachable | present | **nudge, repeatedly**, then the stalled-head escalation |
| unreachable | absent (tier 2, normally) | the stalled-head escalation alone; there is no parent-side capture |

Where the nudge repeats, **repeat it on the stalled-head rule's elapsed-time
observations, not once per cycle** — one nudge per observation, from the same
clock and two-observation floor. **An advancing remote head clears the state**,
nudged or not, and a later stall starts over. The parent's own repetition is not
progress: nudges are unacknowledged, so the escalation's thresholds run on the head
alone and are neither reset nor deferred by another nudge.

## Report

State, for the run — alongside what the sections above say to report:

- the **runtime tier** that ran, and any tier probed and rejected;
- the **base branch** every worker was created from;
- per task: the **model** assigned and the failure-visibility reason in a clause,
  plus any escalation and what triggered it — and **where the capacity veto moved
  the task off the tier that reason chose, say so and name what it measured**;
- per task: the **watch state**, and for polled tasks when they were last read;
- every task whose watch state is unrecorded, named as a blind spot;
- the two capabilities recorded at startup, and how each session's channel was
  decided (*Remote worker session arguments*);
- every wake a worker was observed to arm;
- what was **not** covered — tasks deferred, reads skipped, a tier's guarantee the
  runtime could not provide.

A swarm that reports only outcomes has withheld the part that says whether the
outcomes can be trusted.
