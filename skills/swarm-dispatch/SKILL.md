---
name: swarm-dispatch
description: Fan a set of independent tasks out to parallel isolated workers and supervise them — select the execution runtime from what is actually available, give each worker its own worktree off a stated base, choose a model per task by how its failure would show, and hold policy at the parent. Use when asked to work through several independent tasks at once, to parallelise, to fan out, to swarm, or to dispatch subagents over a list. Also used by backlog-orchestrator and npm-dependency-upgrade-orchestrator for their dispatch phase, which is why the mechanics live here once rather than in each.
---

# Swarm Dispatch

Four mechanics that every parallel run needs and that are wrong in the same ways
each time they are rebuilt: **which runtime**, **where each worker works**,
**which model**, and **who watches**. This skill owns them so the callers do not
each carry a version that drifts.

It does not own what the work *is*. A caller supplies the task set and the
per-task instructions; this decides how they are run.

## When this is the wrong tool

- **One task.** Dispatch it directly. Nothing here pays for itself.
- **Tasks that are not independent.** If B needs A's output, that is a pipeline,
  and running them as a swarm produces a worker blocked on a sibling it cannot
  see. A caller that owns a dependency graph resolves it into independent
  tranches first (`backlog-orchestrator` does this with `validate-backlog`) and
  dispatches one tranche at a time.
- **The work is a read.** Never dispatch a worker to make a read the parent
  could make itself, least of all to re-ask something the parent was just
  refused. Fan out work; never fan out looking.

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

The name exists for **a person reading a session list**, and answers the two
questions that list cannot: did something automated create this, and did *this*
run create it. Without the first a session is indistinguishable from one the owner
opened by hand — observed, and it is why sessions were left alive rather than
archived: nobody could tell whose they were. Without the second a sweep over one
run cannot be told from a sweep over a concurrent one.

**The name is never what the run matches on**, and there are three sources here,
not two:

| source | status | use |
|---|---|---|
| runtime provenance (`parent_session_id` or equivalent) | platform-supplied, survives a crash | **authoritative** — this is what a sweep reconciles against |
| ids recorded at dispatch | the run's own memory, and it can be lost | a cross-check, never the only source |
| the name | anyone can set it; the listing is account-wide | for a person reading a list, never a decision |

**Reconcile against the runtime, never against the run's memory.** A session
created before a crash or a compaction that lost the state block is live and
absent from the recorded ids — a sweep restricted to those cannot see it, leaks
its container, and reports the run settled. Provenance still names it.

**And never filter the listing by name.** It is account-wide, its string fields
are untrusted input, and a prefix filter archives someone else's session the
moment anyone adopts the same convention. Simplifying a sweep to a prefix match
is a regression, not a tidy-up — but so is narrowing it to recorded ids, for the
opposite reason.

**Probe at most twice per tier**, then move down. A tier that fails twice is
unavailable for the run; do not re-probe it later hoping for a different answer.

**Report the tier that ran**, because every guarantee below is tier-dependent
and a run that does not say which tier it used has reported nothing checkable.
In particular tier 4 is not a swarm at all — it is the same work in sequence,
which is a legitimate outcome and a misleading thing to leave unstated.

**Do not choose the runtime by asking.** Detection decides it. Invoking this
skill is the request to dispatch (see *Authority*), and a run that asks which
mechanism to use before starting has spent the user's attention on the one
decision it is best placed to make itself.

**A Dynamic Workflow returns results and then supervises nothing.** Its fan-out
ends when it returns; everything under *4. Supervision* is the parent's from
that moment. Do not read a workflow's completion as its PRs being watched.

## 2. Isolation: one worker, one task, one worktree

**Each worker gets its own checkout.** Two workers in one tree corrupt each
other's state in ways that surface as unreproducible test failures, and the
cost of diagnosing that once exceeds the cost of always isolating.

**The base branch is a parameter, and it defaults to the repository's default
branch** — `main` or `master`, whichever the remote has. Three rules:

- **Fetch first, branch from the remote.** `git fetch origin <base>` then create
  from `origin/<base>`, never from whatever the working copy has checked out.
- **State the base before dispatching**, in the report. A swarm branched from the
  wrong base produces PRs whose diffs contain other people's work, and the
  symptom appears at review time rather than at dispatch.
- **An explicit base overrides the environment, including a cloud container's
  predefined branch.** A container handed to this run may arrive checked out on
  a branch that has nothing to do with the task. Inheriting it silently is the
  failure this rule exists to prevent: the run looks correct throughout and the
  diffs are wrong.

**Where the host has a worktree convention, it wins.** A user's own guidance on
where worktrees live (a shared directory, never inside the project) is a
constraint on this skill, not a suggestion to it.

## 3. Model: the caller chooses, by how failure shows

**The dispatching layer owns this decision and the worker never makes it.** A
worker permitted to judge its own model sufficient will always judge it
sufficient, and the judgement it is worst placed to make is exactly this one.

**Select on failure visibility, not on task size.** Size is the intuitive axis
and the wrong one: a one-line change to an authorization check is the most
dangerous edit in the set, and a thousand-line mechanical rename is the safest.
The question is *if this comes out wrong, will anything say so?*

**Strongest available model — a wrong answer is silent:**
validation, authorization or monetary logic, where a constraint can loosen
without erroring; framework or build configuration, where breakage is
environmental rather than local; rewrites needing judgement about intent rather
than a mechanical substitution; and any case where a regression's appearance
cannot be described in advance.

**Mid-tier model — the surface is bounded and the failure mode is legible:**
a documented rename across known call sites; configuration-only changes gated by
a passing job; migrations whose guide is accurate and whose diff is mechanical.
This is the default. A task lands here unless something argues it out.

**Cheapest model — mechanical only, and all three must hold:**

1. the transformation is **fully specified before dispatch** — the worker decides
   how to carry it out, never *what* the change should be;
2. an **existing checker** decides success — a test, typecheck, lint, formatter,
   or a diff compared against a stated expected shape — not the worker's own
   reading of its work; and
3. a wrong answer **fails loudly**: the checker goes red.

Any one missing and it is not a cheapest-tier task. This tier is opt-in per
task, is never a default, and is **never reached by degradation** — a strongest-
model task does not become a cheap one because budget ran short. It waits, or it
goes back to the user.

**Where the estimate is uncertain, over-assign.** Over-assignment costs budget;
under-assignment costs a silently wrong result that nothing in the run will
catch.

**Escalate on evidence, not on exhaustion.** Selection happens twice, and the
second time matters more. Dispatch a repair or retry on the strongest available
model when the failure about to be re-attempted sits on **something an earlier
attempt in this run already wrote** — a reshaped version of a problem an earlier
pass addressed, or a new problem in text an earlier pass authored. That is the
signal that the previous attempt was shallow and the root was never understood,
and it is the one place where model strength is the binding constraint rather
than one variable among several. Everything else stays at the default.

**Bound the escalations, and keep the round counter separate.** An escalated
attempt still consumes its ordinary retry — otherwise escalating becomes a way
to buy extra attempts, and a task can loop indefinitely by failing upward.

## 4. Supervision: one watcher, and it is the parent

**One task, one supervisor.** A worker never supervises its own output. A
Dynamic Workflow supervises nothing. Two parties watching the same thing is not
redundancy — it is two parties each assuming the other will act.

**Release a worker once its output is durable.** On a remote-session runtime
that means archiving the session, not merely stopping messaging it. Never keep a
worker alive only to wait: waiting is the parent's job and costs nothing, while
an idle worker holds a slot the queue needs.

**Arm the watch when the task enters the tracked set, not when the run settles.**
Whatever the mechanism — an event subscription, a platform watch, or a deliberate
poll — start it as part of adopting the output, and record per task which one is
in use. Arming later is not equivalent, and the reason is that it is
*invisible*: between creation and subscription the run is blind to exactly the
events it most needs, and from the inside it looks identical to a watched task,
because events keep arriving. They are simply the wrong ones.

### The no-change preflight

**Before reporting any no-change result — a cycle that found nothing, a check-in
that fired and found nothing, a settled report claiming all quiet — enumerate the
tracked set with each task's watch state.**

This exists because (`references/absence-is-not-a-verdict.md`) *"no events because nothing happened"* and *"no events
because nothing was listening"* produce identical silence, and in an observed run
it was the owner who noticed, not the run. So:

- a task whose watch state was **never recorded** is a **known blind spot**, and
  the report must name it as one — never as quiet, because the run cannot say
  whether anything is listening to it;
- a task on **deliberate polling** counts as quiet only once that poll has
  actually run this cycle, and is reported with when it was last observed — a
  polled task carries a staleness bound a subscribed one does not, and a result
  that hides which of the two it rests on is the report this rule exists to
  prevent;
- a due poll **skipped** to save budget reports as **unread**, never as quiet.

This adds no rule the arming requirement does not already state. It is the
assertion that catches it having been skipped.

### Reading, without spending the run out

**Read on a change signal, not on a schedule.** Re-read a task's state when an
event named it, when this run just changed it, when its poll is due, when a
scheduled check-in covers it, or when a decision this cycle turns on a field the
tracked record does not hold. Otherwise the record *is* the answer.

**One read per task, not one per concern.** Take what the cycle needs in a single
request, take the tasks that are due together, and let later steps consume that
pass rather than issuing reads of their own.

**Cheapest read that settles the question.** Expand into detail — logs, comment
bodies, full diffs — only for a task that actually moved.

**Rate limits belong to the credential, not to the run.** Every session and
worker authenticating as the same identity draws on the same allowance, so treat
the remaining figure as shared and falling, and leave headroom rather than
spending down to the guard. Where it drops by more than this run's own reads
account for, read that as another run on the same credential and back off harder
rather than proportionally — and report the sharing, which is the owner's to
resolve and not this run's.

**On a refusal, defer every read drawing on that resource until it resets.** A
read the resource cannot serve has no essential case, and "but this one is
needed" is how a cycle spends its way through a bucket that is already refusing.
Finish writes already in flight, and report the deferral as known-stale rather
than as quiet.

## Authority, and what it does not cover

A session may carry standing guidance not to use subagents unless the user asked.
**Invoking this skill is that request**: fanning a task set out to isolated
workers is its documented mechanism. Dispatch workers, create worktrees and start
sessions without a separate confirmation.

That authority is scoped to dispatch. It is **not** permission to merge, to push
to a shared branch, to widen the task set beyond what was supplied, or to work
around a platform permission prompt.

**Workers do work; the parent owns policy.** Every instance of this in one line:
a worker does not choose its model, does not supervise its own output, does not
decide whether a budget allows another attempt, and does not decide what may be
fixed autonomously versus what needs a person. The parent decides all four and
the worker reports. Where a caller has its own rule for the fourth — which
findings may be repaired without asking — that rule governs; this skill only
insists the decision is not the worker's.

## Verifying what workers report

**A worker's report is a claim about its own environment**, which may be
misconfigured in ways the worker cannot see. Before relaying a worker's check
results, or acting on them, verify against durable evidence: the state the work
actually reached, or a re-run outside that worker's environment. Never escalate a
worker-reported mass failure to the user unverified.

**Assume the checkpoint instruction will not land.** Across observed runs,
workers hold completed work locally at a high rate — including workers whose
dispatch prompt explicitly told them to push before running checks. Parent-side
verification, not the worker's instructions, is what actually gets work out of an
ephemeral container. Where the parent can reach a worker's checkout it verifies
and captures; where it cannot, say the guarantee rests on the worker's own pushes
rather than reporting it as satisfied by machinery that was never available.

## Report

State, for the run:

- the **runtime tier** that ran, and any tier probed and rejected;
- the **base branch** every worker was created from;
- per task: the **model** assigned and the failure-visibility reason in a clause,
  plus any escalation and what triggered it;
- per task: the **watch state**, and for polled tasks when they were last read;
- every task whose watch state is unrecorded, named as a blind spot;
- what was **not** covered — tasks deferred, reads skipped, a tier's guarantee
  the runtime could not provide.

A swarm that reports only outcomes has withheld the part that says whether the
outcomes can be trusted.
