---
name: swarm
description: Fan a set of independent tasks out to parallel isolated workers and supervise them — select the execution runtime from what is actually available, give each worker its own worktree off a stated base, choose a model per task by how its failure would show, bound how many run at once, and hold policy at the parent — including, on remote worker sessions, the countermand to their ambient self-supervision, the report carrier, the release test and blocked-worker handling. Use when asked to work through several independent tasks at once, to parallelise, to fan out, to swarm, or to dispatch subagents over a list. Also used by backlog-orchestrator and npm-dependency-upgrade-orchestrator for their dispatch phase, which is why the mechanics live here once rather than in each.
---

# Swarm

The mechanics that every parallel run needs and that are wrong in the same ways
each time they are rebuilt: **which runtime**, **where each worker works**,
**which model**, **who watches**, and **how many at once** — and, on the
tiers where a worker is a session of its own, what that session must be told
not to do, how its report reaches the parent, when it is released, and what
happens to one that stops. This skill owns them so the callers do not each
carry a version that drifts.

It does not own what the work *is*. A caller supplies the task set and the
per-task instructions; this decides how they are run.

This file is the contract; the reasoning and incident history behind its rules
live in `NOTES.md` beside it, keyed by section. NOTES explains; it never
overrides.

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

### Remote worker session arguments

Omit `environment_id` and the worker inherits this session's environment. That inheritance is sound, and it is where this section's one trap starts: the environment decides where the worker *runs*, not what it has *checked out*.

**Pass `source_url` and `source_revision` explicitly on every worker session.** Do not let the worker's checkout come from inheritance, which usually supplies one and is not reliable: it populates the new session's `sources` most of the time, and *sometimes does not*, with no error anywhere in the path. One run dispatched four workers with no `source_url`; three inherited a checkout and the fourth got an empty container (NOTES). A dispatch prompt cannot pin a branch in a repository that was never cloned. Passing the source also removes the one argument constraint here worth remembering — `outcome_branch` is rejected unless `source_url` accompanies it — which matters wherever a caller gives each worker session its own `outcome_branch`, as `backlog-orchestrator`, *Session branch mandates*, does.

**Then verify the checkout before treating the worker as dispatched: the `create_session` response must show `sources` populated.** This is the only signal that exists before the worker starts work, and every signal after it reads the same whether the checkout is there or not: the call returns success, the session reports `RUNNING`, and a worker with no checkout reads as *still working* — the one state under Releasing a worker that nobody acts on — for as long as it keeps looking for the code. An empty `sources` is a failed start, not a worker to watch: treat it as one (see Bounded runtime probing) rather than dispatching into it.

**And end that session before retrying, or the retry orphans it.** A failed start on this tier is not an absent worker — the session exists, holds a container and a worker slot, and reports `RUNNING`, so a retry that only creates a second one leaves the first alive — the container leak Releasing a worker exists for, once per attempt, and an orphan that is precisely the filesystem-searching worker this section is written to prevent. Interrupt it, then archive it, in that order — the order Releasing a worker fixes for every session, and the empty `sources` is the evidence its capture requirement wants: a session ended at the verification above has not run a turn, so there is no worktree to strand and no recovery ref to push. **That discharge is good only here, at creation.** The same field on a session that has been running says nothing about what the worker has produced in the meantime — a worker with no checkout may well have cloned one itself — so a checkout-less session discovered later in the run takes the ordinary inspection and capture (Blocked workers), never this shortcut. **The interrupt does not consume that task's lost-worker budget** — at creation only, on the same boundary as the discharge above — against the general rule for stopping a `RUNNING` session: that budget bounds re-attempts at work a worker may already have done, and a session ended before its first turn did none, so nothing was lost and the redispatch is the task's first real attempt rather than its second. Charging it would spend a task's recovery budget on a runtime defect before a line of its code was written.

**Two capabilities of this tier are established at startup, not assumed, because the rest of this skill, and every caller, divides on them: whether the parent can reach a worker's checkout, and whether it can send the worker a message.** Both are observable without spending a worker:

- **the checkout** — a session record's `sources` carries the repository it was given and **no filesystem path**, and each session runs in its own container (`environment_kind`), so there is nothing for the parent to inspect and no path to inspect it with. **This detection is one-directional: it establishes *cannot reach* and can never establish *can reach*** — an absent path is proof of the first and no evidence at all about the second, so **absent a path, the answer is *cannot reach***, and every rule below that depends on parent-side worktree access takes its unreachable branch. A self-hosted pool that mounts worker files where the parent can see them would be genuinely reachable, and **this document has no way to discover that**: no field it knows of carries such a path. So that configuration falls in the unreachable class too — conservatively, at the cost of the parent-side capture a reachable run would have in place of asking the worker to push — until an operator establishes a path by some means this contract does not yet define (NOTES). Do not infer reachability from `environment_kind`, which speaks to separate containers and not to shared mounts;
- **the channel** — `external_metadata.cross_session_inbound` reports whether inbound cross-session messaging is available for a session, which is cheaper than sending one and watching for nothing to happen. It is observed as the string `available` rather than a boolean, so **test for that value and treat every other reading — including the field being absent — as absent**; a truthiness test on a missing field is the silent way to get this backwards. And it is **one half of the answer**, because it reports that session's inbound availability and not this parent's ability to address it — record the caller's half too: whether this session holds a send tool at all, and whether a listing resolves the target. Enough to act on once both halves read present, never enough to wait on. Blocked workers owns that rule and what overrides the field.

Record both on the run's state and report them (see *Report*). A run that never established them is a run whose checkpoint-durability story is unknown to itself.

**What the unverified case looks like from the outside, since it is otherwise recognized only by its cost:** a worker searching the filesystem for its own source files — a `task_summary` about locating a file the dispatch prompt named, a repository-root probe, or a permission prompt for a bare `find`. That is not a worker that needs a permission; it is a worker that was never given a repository, and Blocked workers says where it goes. The run that discovered this found out that way, ~50 minutes in, with nothing pushed and the whole round to redispatch.

### Bounded runtime probing

A runtime that fails to start a worker gets **at most 2 attempts**, with a backoff measured in seconds, and is then unavailable for the run — move down the chain, and do not re-probe it later hoping for a different answer. A worker created without the checkout it was supposed to get is one of these failures rather than a live worker, and it fails as a **validation error whose fix the retry names** — pass the source explicitly — not as a reason to leave the tier. Its session is ended before the retry, per Remote worker session arguments; a retry on this tier that leaves the failed start running leaks a container per attempt. Varying arguments between attempts does not extend that budget: a service-side error (`temporarily unavailable`, 5xx) is not an argument problem, and a validation error names its own fix in one retry.

Do not spend an orchestration run diagnosing a runtime. Degrading to subagents and reporting the outage always beats a ten-minute retry loop before any work has started.

## 2. Isolation: one worker, one task, one worktree

**Each worker gets its own checkout.** Two workers in one tree corrupt each
other's state in ways that surface as unreproducible test failures, and the
cost of diagnosing that once exceeds the cost of always isolating.

**Everything the dispatcher computed travels inline in the prompt, and no prompt
names a dispatcher-side path.** On the tiers where a worker is a separate
container the dispatcher's filesystem is not the worker's, so a path resolves to
nothing there — and the failure is silent, because a worker that cannot read what
it was pointed at falls back to whatever it can find and reports success. Where
the thing is large, that is an argument for computing less, not for passing a
reference to it.

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

**Context capacity is a second gate, and it does not correlate with the first.**
Before assigning a small-context model, ask what the worker will *load* before it
reaches the task — the repository's agent-instruction file and everything that
file pulls in. Where that surface is large, a small-context model is excluded
whatever the task looks like: the most mechanical item in an observed fan-out, a
three-line guard, was its only outright failure, because the repository's
instruction set pulled in roughly fifteen specification documents and exhausted a
200K window before the worker reached any code. **Measure the instruction
surface, not the diff**, and treat capacity as a veto on the tier the first gate
chose rather than as an input to it — a task can be genuinely mechanical and
still not fit.

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

*Releasing a worker*, below, defines what releasing is on each tier and the
test for when a worker may be released. Release is also driven by the session
list rather than by the run's memory, and belongs in the prompt the run writes
for its own check-in, since that is what survives compaction.

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

### Countermanding the worker's ambient supervision posture

Prompt literalism cuts both ways. A prompt that omits a required default gets a worker that skips it; a prompt that omits a required **contradiction** gets a worker that follows whatever its own session already told it to do. A Claude Code Remote worker session inherits a system prompt instructing every session to subscribe to PR activity and to schedule a self check-in roughly an hour out, re-arming it silently until the PR merges. That instruction arrives with the runtime rather than from any skill this run dispatches, and it is correct for the sessions it was written for.

So every dispatched prompt — implementation, review and repair alike — must state that this run owns PR supervision and the worker does not: do not subscribe to PR activity, do not schedule a check-in, trigger, routine or wake of any kind, **and do not watch GitHub for state that changes after its own work is done** — no polling for CI, review, comment, thread, issue or merge state — and return after pushing and reporting, **even where the worker's own session instructions direct otherwise**. Name the override rather than merely stating the rule.

**That ban does not reach a worker verifying its own writes, and must not be written so it does.** The worker skills' contracts require exactly such reads, and this run consumes their results: `create-pr` reads its PR back for linkage and its trigger comment back for comment-kind identity, and `repair-pr` confirms the replies and resolutions it was asked to make and counts the threads still unresolved (`backlog-orchestrator`, *Posting identity*, and the read-back the worker contract already mandates). The line is **watching versus verifying**: reading back what this worker just wrote, once, is verification and stays; reading again later to learn whether anything has changed since is supervision, and belongs to this run (NOTES: what cutting those reads costs this run).

**But put it where it can actually outrank what it countermands.** A dispatch prompt is a task instruction, and a task instruction is the weaker side of an argument with a session's own system prompt — telling a worker in its task to disregard its session instructions does not, by itself, make it do so. So on a runtime where this run *builds* the worker's session, write the countermand into that session's system prompt: `create_session` takes an `append_system_prompt` for exactly this purpose, and it is the only lever here that sits at the same level as the instruction it is answering. The dispatch prompt then restates it rather than carrying it alone.

Branch protection (the template's push clause below; `backlog-orchestrator`, *Implementation worker contract*, states it as Before dispatch step 7) belongs at this level too. Where a push may go is a rule the worker applies exactly when something has gone wrong — mid-mistake, mid-revert — which is when a task instruction is at its weakest against the session's own posture. On a runtime that builds the worker's session, write it into `append_system_prompt` alongside this countermand, restated in the dispatch prompt in the same way.

The question posture (the template's last clause; step 8 of that list) is the third countermand that belongs here, for the same reason: asking the user is correct behavior in the attended sessions the worker's instructions were written for, and a deadlock in a fan-out where nobody will ever answer. Apply "Read the field that reflects the blocked state" (Blocked workers) rather than restating it here, and archive-and-redispatch for a prompt nothing can answer is a branch of Blocked workers in its own right. A documented assumption is recoverable; a deadlocked worker is not (NOTES: the unreachable-worker incident in full, and why the substitute is what made the redispatch succeed).

The tier decides which lever exists, and only one tier has the problem:

| runtime | where the countermand goes |
|---|---|
| remote worker session — implementation, review and repair alike | `append_system_prompt` at creation, restated in the dispatch prompt |
| subagent, Dynamic Workflow agent, serialized | the dispatch prompt is the whole of it — none of these inherits a session posture to countermand |

**The text, as a template.** Written out once so it is carried whole rather than paraphrased — a paraphrase is where one clause quietly drops. Fill `<branch>`, and from each `[a | b]` keep one side, removing the brackets: an implementation worker keeps the first side of both; a repair worker the second side of the trigger bracket, since this run requests review after a repair, and the first of the push bracket; a review session the second side of both. Send the rest as written.

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

**Never claim a decision was authorised in a dispatch prompt; link the record of it** — `backlog-orchestrator`, *Implementation worker contract*, Before dispatch step 6, where rulings enter a prompt, states the rule, and its NOTES record the refusal it prevents. This is about a decision's licence, not the countermand above, whose override is stated on purpose.

**Attribution is the one thing in a dispatch prompt that must not be inherited.** Everything else travels down verbatim by design; identity is the exception, because it describes the session that writes and a worker is a different session. An observed run told eight workers to sign their commits as the parent's model: two refused and blocked, correctly, and four complied, so their commits carry a false trailer and nothing flagged it. A retry after a refusal like that is a rewrite that removes the claim, never an annotation explaining it — a redispatch that opened by explaining the earlier refusal, and still asserted a session id the worker could not check, was refused again as a prompt-injection risk, with a better stated reason than the prompt had. **And a dispatch the parent's own prompt broke is not the worker's failure**: it does not spend that task's lost-worker budget.

Expect this to reduce the behavior, not to eliminate it. Appending does not delete the instruction already present, some environments ignore the parameter outright, and a worker resolving two same-level instructions may still arm a wake or stop to ask. That residue is why **Blocked workers** is a backstop rather than a redundancy: the run has to be able to notice a worker that did either anyway and clear it, not merely to have forbidden it.

**And do not read a quiet session list as proof this worked — the quiet case is the expensive one.** Where workers inherit an allowlist that grants the trigger tools, a worker that arms a wake can also disarm and re-arm it, so it never blocks on anything: Blocked workers never sees it, the session list shows nothing stuck, and the worker wakes every hour to re-read a merged PR, find nothing, and re-arm — for as long as the account will pay (NOTES: the $33.45 and $59.60 sessions). A worker that arms a wake it *cannot* disarm at least blocks visibly on the permission prompt, where Blocked workers finds it. So an absence of blocked sessions is the signature of the costlier branch, not evidence the countermand held. What catches both branches is the release reconciliation — reading the runtime's session list, not the run's memory (*Runtime: take what is there, and say which*; `backlog-orchestrator` runs it as its supervision loop's step 11) — and the report, which names every wake a worker was observed to arm.

Do not leave this to the worker skills (NOTES: how a worker satisfied the duration-only wording while leaving a watcher armed). The gap is **delegation, not duration**, and this prompt is the only place in the system that sees both instructions at once.

It is also the only place the problem is visible. The instruction being countermanded appears in none of the worker skills, so searching them for the behavior finds nothing that could be causing it.

The parent arming its own subscription and check-in when a run settles (`backlog-orchestrator`, *Arming the wait when nothing is in flight*) is this same ownership stated from the other side, not an exception to it. One watcher, held by the layer that owns supervision.

Two costs — duplicated supervision, and a worker deadlocked on the disarm prompt after its own work merged — and the second is the one observed (NOTES).

Scope this to workers **a swarm dispatches** — this skill's own, and those of every caller that dispatches through it. `implement-issue` invoked standalone owns supervision of its one PR by design, and the ambient posture is right there; this countermand does not travel to it.

### How a worker's report actually reaches you

Everything below about consuming a worker's outcome — its dependency evidence, its coverage findings, its disagreements — assumes the report arrives. Whether it does is a property of the runtime:

| runtime | how the report reaches the parent |
|---|---|
| in-process subagent | the return value, delivered to the caller |
| Dynamic Workflow agent | the fan-out result the workflow returns |
| serialized execution | directly, in the same context |
| **remote worker session** | **it does not.** A remote session cannot message its parent. Its structured return lands in its own transcript, which the parent never reads |

On that last tier — the one the degrade chain most often lands on — a report reaches this run only through what the worker wrote somewhere durable, all of it **pulled**, never pushed. A dispatch prompt asking a remote worker to "report back" gets a report addressed to nobody. Nothing in the worker contract persists the report on its own (`implement-issue-core` returns its structured state to its caller; `create-pr` writes only the PR's metadata), so pulling recovers whatever happened to land in an artifact — not the report, and where the worker stopped before a PR existed, none of it (NOTES: where the gap is worst).

**So require the worker to write the report down, before relying on being able to read it — but read the session record before requiring anyone to write anything.** The runtime writes that record itself: it costs no permission, needs no tracker write, and survives the session being archived:

| field | carries | limit |
|---|---|---|
| `status_bucket` | `WORKING` / `COMPLETED` / `BLOCKED` | disagrees with `session_status` — see Blocked workers |
| `pending_action.tool_name` | exactly what a blocked worker is waiting on | only while it is blocked |
| `task_summary` | what it is doing right now | ephemeral; says nothing about outcome |
| `post_turn_summary` | `status_category`, `status_detail`, `needs_action` | **one line of free text**, rewritten each turn |

With the branch — commits, diff, messages — and the PR where one exists, *did it finish*, *is it stuck*, *on what*, and *what landed* are all answerable without the worker writing a word to the tracker. **What none of it carries is judgment**: an acceptance criterion the worker could not satisfy, a guarantee it narrowed, an endpoint it found missing, a dependency it read in prose that native metadata denies. That is the only thing the written report is required for, and the requirement is scoped to exactly that (NOTES: what "persist the run state" would cost instead).

**Route the report by whether a PR is actually there — not by the outcome label, since linkage verification and the review trigger run after creation, so `FAILED` and `NEEDS_USER` can both arrive with a perfectly usable PR already open — and never to the issue:**

- **PR exists — a comment on the PR, whatever the outcome says.** That is where a reviewer and a merge decision look, it exists exactly when there is a body of work to qualify, and it is inert to every dependency reader. This is the large majority of reports.
- **No PR — the worker writes nothing.** Its one line of `status_detail` and `needs_action` tells this run there is something to look at; the parent investigates — the branch, `pending_action`, the issue's own prose, the dependency read repeated under its own credential — and **writes the record itself, after classifying it** (for a worker that stopped on a dependency, `backlog-orchestrator`, *How a worker's report actually reaches you*, says how).

**The report names the head commit the worker pushed** — or that it pushed nothing, and the head it found — because the branch shows what reached the remote and not what the worker holds, and the releasable test compares the two (*Releasing a worker*, condition 2).

**Verify at dispatch time that the worker can write the sink it is being asked to use.** The requirement is not satisfiable by instruction, and an allowlist entry does not settle it either — the entry has to name an operation the connected server actually exposes. A worker told to write a sink it cannot reach either stops on a permission gap or returns with the result in its transcript, arriving here as silence. Where the sink is unreachable, the runtime choice is what gives: dispatch that task on a tier whose return value reaches this run.

This is the same division of labour as the ambient-posture countermand: the worker skills are runtime-agnostic and cannot know whether their return value goes anywhere, so the obligation belongs in the dispatch prompt, written by the only layer that knows the runtime.

So on a remote-session runtime, treat the worker's own writing as a required read rather than a courtesy copy, and pull it deliberately: the PR body and thread replies for substance, the session's summary for whether it finished, was blocked, or stopped mid-issue. A run that waits for a report to arrive from a remote worker waits forever, and reads the silence as nothing having happened. **This bites hardest on the things no check expresses**: CI says nothing about a caveat the worker deliberately raised, so a narrowed guarantee, a knowing deviation from an acceptance criterion, or a limitation flagged and left unfixed lives in the worker's PR comment and nowhere else. Read it before any merge-order ranking, before surfacing the PR as finished, and before relaying a PR as ready — never after the decision it should have informed. A green PR whose worker flagged a scope caveat is not the same object as one whose worker flagged nothing, and only the report distinguishes them.

### Releasing a worker

"Release the worker" appears throughout this skill and the callers that dispatch through it — at `PR_OPEN`, after every repair — and it names a different act on every tier, so it is defined here once rather than at each call site:

| runtime | what releasing is |
|---|---|
| Dynamic Workflow agent | nothing to do — the runtime reclaims the agent when the workflow returns |
| remote worker session | **archive the session.** A live one holds a container, a session-list entry, whatever permission prompt it may be sitting on — and any wake it armed, which is the recurring cost: a live session keeps waking on schedule and spending tokens for as long as it lives |
| in-process subagent | stop messaging it; there is no resource to reclaim |
| serialized execution | nothing to do — there was never a second actor |

On two of the four tiers release *is* the absence of an action; on the remote-session tier the same words name a real resource that leaks silently (NOTES: the nine leaked containers, and the two later runs that leaked 15 and 1).

**Archiving the session is the only thing that stops a wake the worker armed itself.** The session is what arms the wake, so deleting the scheduled trigger does not work: a leaked session whose trigger was deleted armed a replacement one minute later (NOTES). Archive the session; do not fight its triggers.

**The releasable test, stated once and referenced everywhere else that needs it.** A second copy of this test appearing anywhere is the regression to look for (NOTES: how in-situ restatements drifted).

A worker is releasable when both hold, and not before:

1. **it is done** — either of:
   - it **returned a terminal outcome**, any of them and not only the successful ones. `implement-issue-core` ends on `BLOCKED`, `BLOCKED_EXTERNAL`, `FAILED` and `NEEDS_USER` exactly as it ends on `PR_OPEN`; `repair-pr` ends on `NO_CODE_CHANGE`, `FAILED` and `NEEDS_USER` exactly as it ends on `REPAIRED`. A repair worker that correctly classified a CI failure as external returns `NO_CODE_CHANGE` with an unchanged head and nothing to push, and is as done as one that pushed a fix. Releasing only on the two successful outcomes leaks every session whose worker did its job and had nothing to show for it, which a run dispatching into a wrong graph produces in bulk. On a tier where the return value does not reach this run, **it has returned when its session record says so** — `status_bucket` no longer `WORKING` and not blocked, read as *Blocked workers* says to read it, not off `session_status` alone — and what it returned is its report on its PR (condition 2), or, where it stopped before any PR existed and so wrote none, the outcome its `post_turn_summary` names. An `IDLE` session whose record still reads `WORKING` is between turns — waiting on a subagent, say — and is still working. A merged or closed PR finishes it as well;
   - or its **work reached durable remote state and it is now blocked on a prompt this run does not need answered**. No outcome arrives in this case because the prompt is what stops it arriving, and waiting for one strands the session forever.

     **That last qualifier is load-bearing, not throat-clearing.** A pushed branch, an existing PR and a clean worktree do not by themselves mean the worker is finished: `create-pr` verifies tracker linkage and issues the automated review trigger *after* creating the PR, so a worker blocked on either of those is stopped mid-deliverable rather than tidying up behind one. Archiving it there leaves a PR that is unlinked or never reviewed while the run records the task as complete — the coverage failure `backlog-orchestrator`, *Outcomes*, spends a section on, arrived at through cleanup. Cleanup the run does not need — disarming a wake the worker should never have armed — releases it. Anything the deliverable still depends on takes the parent's-clear or `NEEDS_USER` branches under Blocked workers instead;
2. **nothing is stranded in its worktree** — which no outcome label can speak to. Where the worktree is reachable, Checkpoint compliance establishes it. **Where it is not — which on the remote-session tier is every worker — the observable remote state stands in for it.** The session must also not be `RUNNING` (the paragraph beginning *Two things are never archived*, below).

   **A commit is reachable on the remote** when it is an ancestor of (or equal to) the head of a remote branch — the PR's own, where there is one — or of the default branch, or is the head of a merged PR. Always the worker's *commit*, never whether a branch of some name exists: a branch can exist and be stale behind unpushed work, and a merged PR's branch is routinely deleted. Ancestry rather than equality, because a later repair, a restack or the parent's own push moves the head past a commit that is still perfectly safe. The head of a merged PR is named separately because a squash or rebase merge puts the work on the default branch under new commits, which are no ancestors of anything the worker made.

   **What the worker returned, on a tier where its return value does not reach this run, is the report it recorded on its PR** (*How a worker's report actually reaches you*) — its structured return lands in a transcript the parent never reads — **and that report names the head commit it pushed**, or, where it pushed nothing, the head it found. **Only a report carrying this session's own attribution footer is its report**: every session posts as one identity, so an implementation worker's report on the same PR would otherwise stand in for a repair session that never wrote one. The remote state then stands in for the worktree when any one of these holds:

   - **its deliverable is on the remote** — the head its report names as pushed is reachable; a head it *found* counts only where its outcome claims no code change (`NO_CODE_CHANGE`), since a failed push reported honestly as "pushed nothing" leaves the fix in the container; or, for a review session, a review or comment is on the PR whose attribution footer names that session. Every session posts as one identity, so the footer's session link is what tells its comment from the parent's own and from an earlier round's. Ancestry covers a no-code repair as well: the head it found is reachable however far the PR has moved since;
   - **its charter is finished** — its PR has merged or closed. A merged PR takes no more commits, and a closed one's branch is what any redispatch resumes from, so whatever the session holds beyond the remote is the accepted residual. That is the shape of every documented leak: finished workers idle for weeks on merged PRs, report or no report;
   - **it never produced work** — no branch and no commit of its own, and the runtime shows no staged or uncommitted files in its session. An early `BLOCKED`, `BLOCKED_EXTERNAL` or `NEEDS_USER` is normally this, and a run dispatched into a wrong graph produces them in bulk. A missing branch alone does not establish it — a push can fail while the worker goes on editing — and neither does a file field the runtime does not expose.

   Anything else is a **mismatch** (below).

**The residual risk is accepted, and it is stated so it stays a choice.** A worker that reported pushing a commit and then kept editing without pushing again loses those edits at archival. That is bounded by `implement-issue-core`'s own promise — at most the work since the last checkpoint — and on a tier that dispatches separate implementation, review and repair sessions it is close to nil: each session has one deliverable, and once it is delivered the PR belongs to this run, so edits after the reported push are work nobody asked for. Staged or uncommitted files a delivered worker's session still reports are this residual, not a reason to hold it, and so is anything a session holds for a PR that has merged or closed. The alternative this replaced was keeping every remote container pending an owner answer, on a tier where the worktree is never reachable, so every worker hit it. **That was not a fail-safe, because it always fired**: it produced either a `NEEDS_USER` per worker or silent retention, and every documented incident on record is a leak — fifteen sessions after their work merged, two billed $33.45 and $59.60 waking hourly on merged PRs, fourteen more in a later run — and not one is lost work (NOTES).

**A mismatch is the one case that keeps the container.** Where none of the three holds — a reported head that is not reachable, no report at all on a PR still open, a review session with no comment of its own, or an early stop that left a branch or files — work may really be stranded, and the lever that remains is to ask the worker to commit everything, push, and report the resulting head. Its success is the commit named becoming reachable, by the definition above, with the remote head compared against what was recorded before the ask; **a branch existing proves nothing**, since a stale branch from an earlier push passes an existence test immediately. The lever depends on the caller-side channel (Remote worker session arguments): where this session cannot address the worker, there is no ask to make. Either way, a mismatch that the lever does not close is `NEEDS_USER` naming the session, what it reported, what the remote shows, and whether the ask was made. Keep that container. The owner decides.

**Durable remote state** means a PR exists and the worker's commit is reachable on the remote, by the definition above. **The PR's own state is irrelevant** — open, merged, or closed. Merged is the *common* case here rather than an edge one: a wake armed at PR creation outlives the PR that armed it, so by the time anyone notices the blocked session the work has usually landed (NOTES). Any test that requires the PR still be open excludes precisely the deadlock this section exists for.

A session merely reading `IDLE` asserts neither condition — on the remote-session tier condition 1 is read off its session record, above, not off `IDLE`: idle is also what a worker looks like when it finished editing and never committed — the state Checkpoint compliance exists to catch, because workers reliably reach it.

And a worker that has not returned an outcome is not therefore lost. It is one of three things, and only the last is:

| state | who owns it |
|---|---|
| stopped on a prompt | Blocked workers — released by the test above, cleared, archived and redispatched, or raised as `NEEDS_USER` |
| still working | nobody yet — leave it and re-check next cycle |
| unreachable | the caller's lost-worker recovery (`backlog-orchestrator`, *Lost worker / workflow recovery*) |

The ordering between the two conditions is fixed rather than incidental: the checkpoint-compliance step of the supervision cycle runs first, and a session is archived only once nothing is stranded in its worktree — established by that step where the worktree is reachable, and by the remote state standing in for it where it is not (condition 2). Archiving first destroys the container and the only copy of that work together, and the check that would have caught it no longer has anything to look at.

Two things are never archived. A **`RUNNING`** session — a worker that must be stopped is interrupted first, which consumes that task's lost-worker budget and needs the same evidence any redispatch does (`backlog-orchestrator`, *Checkpoint compliance*), and is archived only after its work is captured (the one carve-out is a session ended at dispatch for having no checkout to work in, under Remote worker session arguments — never one discovered later, which is captured like any other; it is stopped the same way and charged nothing). And a session **this run did not create** — decided by provenance, never a title (*Runtime: take what is there, and say which*) — the user's own sessions from every other surface share that list, and none of them are this run's to reclaim.

### Blocked workers

A worker waiting on a permission prompt is neither running nor finished. Its session reports `REQUIRES_ACTION` — or whatever the runtime calls *stopped, awaiting a human* — and a supervision cycle that looks only for `RUNNING` and `IDLE` sorts it under quiet and moves on.

**Read the field that reflects the blocked state, not the one whose name suggests it.** A runtime may expose several, and they can disagree (NOTES: the observed IDLE/BLOCKED disagreement and the six-hour incident). Checking the obvious field and finding a familiar value is therefore not evidence the worker is fine — it is the reading this failure mode produces. Establish once, per runtime, which field actually changes when a worker stops for a human, and read that one every cycle; where a summary of what the worker was last asking for is exposed, read it too, because that is what turns "blocked" into something a user can act on. Quiet is the one thing it is not: nobody is watching that prompt, so nothing will ever answer it, and the worker holds its container indefinitely.

**On the remote-session tier, one of the levers below may not exist at all — and on the runtime this was observed against, for the worker sessions a run had created, it did not.** The limitation is not a property of being mid-prompt, which is merely where it was first seen: on Claude Code Remote, `SendMessage` does not address a worker session this run created, in any state, and `interrupt_session` stops a worker without answering what stopped it. So step 2's "an instruction it can be sent" is unavailable wherever the criterion below says absent, and the recovery for anything it would have covered is not *redirect*: it is step 3, **whose own path then turns on the other capability** — archive-and-redispatch where the checkout is reachable, and, for a worker step 1 did not release, `NEEDS_USER` where it is not, because an archive nobody could capture from trades an unknown amount of work for a slot. It has one consequence outside this section, on the same split: the checkpoint escalation's nudge is not an act on this tier, so where the checkout *is* reachable the parent captures on first observation, and where it is not there is no parent-side capture at all (Checkpoint compliance, *Enforce, do not re-ask*). **The capability the run recorded at startup is the criterion, here as everywhere else that branches on it** (Remote worker session arguments). Where `cross_session_inbound` reads anything but `available`, the channel is absent, step 2 is unavailable, and no probe is required to establish it. **Where it reads `available`, one half of the channel is established and the other half is not.** That field reports the *target's* willingness to accept inbound messages; whether anything can be sent is a property of *this* session's toolset, and the two are independent — an observed orphan read exactly `available` while the caller had no send tool at all, `ListAgents` resolved no peers, and every send returned no-such-agent. So the field is necessary and never sufficient: establish the caller's half from the caller's own side — a send tool present, and a listing that resolves this target — and only then is step 2 a real lever again. **Both halves present: use it.** The field `available` with no caller-side channel is **not** a worker written off as unreachable-and-therefore-fine: the levers that depend on sending do not exist, the run says so plainly naming the session, and the decision goes to the owner. Requiring an observed landing first would leave the field unable to ever establish presence, which is a detection that decides nothing; worse, it splits the verdict, so the checkpoint escalation nudges the very worker this path had written off as unreachable (Enforce, do not re-ask, which branches on the recorded capability).

**What makes it safe to act on evidence that weak is that nothing waits on it.** The field speaks to a session's inbound availability, not to this parent's ability to address that session, so it can be right about the runtime and wrong about the pair. No branch of this document blocks on a reply: nudges are unacknowledged by construction and every escalation runs on the observed remote head. So a channel wrongly presumed present costs one composed message — and the failure absent-until-proven was buying protection from, a worker stranded while the run waits for an answer that cannot come, is not reachable from here any more. **A send that errors or is refused is the observation that counts, and it flips the recorded capability to absent for the rest of the run**: unlike the field, that is direct evidence about this parent and this worker. The observation this section was written from is exactly that shape and it stands — no send reached a worker session the run had created — which is why a negative observation overrides an `available` field and not the reverse.

**Both errors are silent, so record how each session was decided and report it.** A run that read the field as absent and a run that never read it look identical in the output otherwise, and the second is the one whose checkpoint-durability story is unknown to itself.

Read the blocked state explicitly each cycle, and resolve it in this order:

1. **it passes the releasable test** in Releasing a worker — apply that test, do not restate it here. Every version of this rule that was written out a second time drifted from the first, including the one that required a PR still be open and so excluded the merged-PR case this section is written from. Release it and record what it was asking for;
2. **the block is the parent's to clear** — a resource detail the worker was dispatched without, an instruction it can be sent, a write the parent can perform itself. Clear it and let the worker continue;
3. **neither, and the prompt is one nothing can answer** — an `AskUserQuestion` or equivalent, where the worker is asking for a decision rather than for permission. No lever reaches it: interrupting the session leaves the prompt pending, and on a remote runtime there is no message channel to it at all (above). **Which recovery this is turns on whether the run can reach that worker's checkout, so settle that first** (Remote worker session arguments) — the two branches end in different places, and stating either one as *the* rule makes the other read as a violation of it. 

   **Where the checkout is reachable, recover the slot, and do not resolve the worker as `NEEDS_USER` and leave it:** that holds a container and a worker slot for however long the human takes, and the capture below is what makes holding them unnecessary. Archiving destroys the container, and with it the local worktree lost-worker recovery would otherwise read, so uncommitted work must reach a **remote** ref before the archive rather than merely a local commit. Capture it with the ref-neutral sequence under `backlog-orchestrator`, *Checkpoint compliance*, which pushes to a recovery ref and moves nothing the worker holds, and verify that capture the way that section requires; do not substitute a plain `git commit`, whose result the archive then discards. Only once the capture is on the remote — or you have established there was nothing uncommitted to capture — archive the session, then — where a capture was pushed — end its ref by **the four-state rule under `backlog-orchestrator`, *Checkpoint compliance* — apply it, do not restate it here.** This archive is not a release by the releasable test — case 1 above took every worker that passes it — and the worker is not lost, so neither of that rule's other trigger sites will ever fire for this ref; unconsumed here, it stays outstanding forever, blocking `backlog-orchestrator`'s merge gate (invariant 12) over the very work it rescued, while the redispatch below starts from a head the capture never reached and redoes the work. Then redispatch **the same work unit** from the latest durable remote state — which the reconciliation has just made include the capture — with the question countermand (*Countermanding the worker's ambient supervision posture*) in place; where the four-state rule's merged-PR ender raised `NEEDS_USER` instead, that is the outcome: do not redispatch work whose PR has already merged — the owner now holds the decision. The same work unit, not the same issue: this section covers every worker, and a blocked `repair-pr` worker redispatched as "the issue" becomes a fresh implementation attempt under `implement-issue-core`'s contract instead of the bounded repair it was. Preserve the archived worker's role, its repair type where it had one, and the budget it had left rather than issuing a new one. This is the only recovery observed to work, and a redispatch costs one worker where a session left blocked costs a slot for the rest of the run. Record the question it stopped on either way: a worker reaching for this tool is a finding about the dispatch prompt that produced it, not just an incident.

   **Where the run established it cannot reach that worker's checkout at all** (Remote worker session arguments), none of that is available: it can neither perform the capture nor establish there was nothing to capture, and case 1 has already released every such worker the releasable test passes. What reaches here is a worker whose work the remote cannot vouch for, which is the mismatch under Releasing a worker. **The slot is therefore not recoverable on the run's own authority, and this is the blocked worker that is `NEEDS_USER` with its container retained** — naming the session, its last observed remote head, and the question it stopped on. Do not archive it to free the slot: that trades an unknown amount of work for one worker slot, and the decision belongs to the owner. **This is not the "still waiting" the last rule in this section forbids,** and the difference is what that rule actually asks for: the worker is named in the run's output with its cost stated, the held slot is reported as the price of work that may be stranded (Releasing a worker) rather than absorbed silently, and the run does not schedule against the capacity it is holding. A run that ends this way has not failed and is not clean either;
4. **neither, and the prompt is a permission request** — `NEEDS_USER`, naming the issue, the session, and **the exact tool being requested**. "A worker needs permission" is not actionable; the tool's name is what lets a user allow it once and unblock every run after this one. Report the literal string the runtime gave you, server segment included, and never a tidied version of it: an MCP server can be registered under a display name, a slug, or its bare UUID, the allowlist matches the literal name, and a tool already allowlisted under one of those spellings still prompts under another. Normalizing the name to the one you expected is how that reads as an entry that exists and does not work.

   **One permission request does not belong to this branch at all, and it is the one most likely to arrive in it:** a filesystem search for the worker's own source files — a bare `find`, a repository-root probe, a request for a path the dispatch prompt already named. Read that session's `sources` before reporting it. Where they are empty, the worker was dispatched into a container with no checkout (see Remote worker session arguments): the tool it is asking for is a symptom two steps downstream of that, allowlisting it buys the next worker a faster search of an empty container, and the recovery is step 3 — taking whichever of its two paths the checkout's reachability selects, and redispatching with `source_url` and `source_revision` passed explicitly. **Step 3's capture requirement applies here in full — the empty `sources` does not discharge it.** That field records what the runtime provisioned at creation and says nothing about what the worker has done since: a worker that could not find its checkout is exactly the one liable to have cloned or initialized one itself, and after an hour of trying that container can hold the only copy of real work. Only the dispatch-time check discharges the capture, because there the session has not run yet (see Remote worker session arguments); a session discovered this way has, so inspect and capture it like any other. Record the dispatch defect, not the tool.

Never resolve it as "still waiting". A blocked worker holds a slot, so reading it as idle also stalls the frontier: the run keeps scheduling against capacity that is not in use. It must not be possible for a worker to sit blocked across an entire run without appearing anywhere in its output.

## 5. Concurrency: a ceiling, and the caller sets it

**At most 4 workers run at once, unless the caller sets its own bound.** A
caller's bound replaces this one — `backlog-orchestrator`'s `concurrent-workers`,
and `npm-dependency-upgrade-orchestrator`'s begin-narrow-and-widen rule (its
*Dispatch*, *Bound concurrency*) — and invoked directly, an invocation argument
does. Without a default, thirty tasks is thirty workers.

Do not increase concurrency merely because the runtime can fan out more agents.

The concurrency number is a ceiling, not a target. Derive the level you actually run from machine capacity at startup — available CPUs, free disk against the container's fixed allowance, and whether each worker needs its own dependency install or test toolchain — and take the lower of the two. Decide that yourself and report it; do not ask.

### Capacity during the run

Re-check disk headroom and worker-slot capacity each cycle, not only at dispatch. Worktrees, dependency installs, and build caches accumulate as the run proceeds, so startup headroom does not predict headroom at the fifth concurrent worker. Report the current figure with the worker count, and stop filling slots before exhaustion rather than after a write fails.

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

**A worker's report is a claim** (`references/establish-do-not-assume.md` states the general case and what settles
each kind). It describes an environment the worker may not be able to see
correctly, so before relaying its check results or acting on them, verify against
durable evidence: the state the work actually reached, or a re-run outside that
worker's environment. Never escalate a worker-reported mass failure to the user
unverified.

### Checkpoint compliance

**Assume the checkpoint instruction will not land.** Across observed runs,
workers hold completed work locally at a high rate — including workers whose
dispatch prompt explicitly told them to push before running checks. Sonnet workers in particular treat committing as something that follows green checks rather than something that protects work in progress, and no amount of prompt emphasis has reliably changed that. Parent-side
verification, not the worker's instructions, is what actually gets work out of an
ephemeral container. Where the parent can reach a worker's checkout it verifies
and captures; where it cannot, say the guarantee rests on the worker's own pushes
rather than reporting it as satisfied by machinery that was never available.

So this is a step of every supervision cycle, not a periodic spot check, and it observes three things per in-flight worker — the worktree, the local branch, and the remote:

**Two of those three require reaching the worker's checkout, so this whole section applies only where the run established that it can** (Remote worker session arguments). Where it cannot, the remote head is the only observable, and it is the one that "tells you nothing" below: a head that has not advanced cannot distinguish a worker still reading code from a worker sitting on eight finished files, and on that tier nothing else is available to separate them. Do not read this section's silence as permission to guess — the honest position is that durability there is the worker's to satisfy, enforcement is the dispatch prompt, and a worker whose head does not advance is the one thing the parent can still act on. **Make it actionable rather than quiet — measured in elapsed time, never in cycles — and where a channel exists, nudge first (Enforce, do not re-ask, which owns the four capability combinations).** The supervision loop has no minimum interval: sibling completions and PR events can drive several cycles back to back, so a cycle count would raise a legitimately-working worker minutes after dispatch and then block settlement on it. So: a tier-2 worker whose remote head has not advanced for **30 minutes** of observed elapsed time is reported as such, and at **2 hours** it is `NEEDS_USER` — naming the session, its last observed head, and how long it has been unchanged. Both thresholds are measured from the last observed advance (or from dispatch, if there has been none) across at least two observations, so a burst of cycles inside one minute is one observation, not four. It is not a capture and does not pretend to be one; it converts the state that currently reads as *still working* into one somebody sees, which is the same hole a worker with no checkout at all falls through.

| worktree | local vs. tracked remote | state | action |
|---|---|---|---|
| dirty | — | completed edits exist only on disk | capture, below |
| clean | local ahead | committed, push failed or was deferred | push the stranded commits |
| clean | level | nothing saved yet | leave alone unless dispatch was long ago |
| clean | tracked remote absent | merged and deleted, or never pushed | check whether its head is reachable, by the definition under *Releasing a worker*, before treating it as stranded — a forge deletes merged branches routinely. Reachable: nothing to capture, and the releasable test takes it. Not reachable: push the stranded commits |

A remote head that has not advanced tells you nothing arrived; it cannot distinguish a worker still reading code from a worker sitting on eight finished files. Only the worktree separates those. And a clean worktree is not proof of durability on its own: a worker that committed but whose push failed leaves `git status` clean while the remote stays put, so the local/remote comparison is what catches that case. Pushing stranded commits is always safe against a live worker — it touches neither its index nor its working tree.

**How to capture is `backlog-orchestrator`, *Checkpoint compliance*:** the sequence
that captures without racing a live worker, the tested script beside that skill,
and what becomes of the recovery ref it pushes. Apply it from there rather than
improvising a capture.

#### Enforce, do not re-ask

On first observing uncommitted completed work, instruct that worker to commit and push immediately. If the next cycle still shows it uncommitted, the parent captures the work itself rather than nudging again: a second nudge is evidence the instruction is not landing, and the parent already holds worktree path, branch and base in the tracking record.

**Both halves of that escalation depend on a capability, and the tier a degraded run most often lands on has neither.** The nudge needs a channel to the worker; the capture needs a path into its worktree. Where only the channel is missing, the parent **captures on first observation** — the same capture, one cycle earlier — and none of the nudge's reasoning transfers: a nudge nobody can deliver is not evidence about anything. Where the worktree is unreachable too, as on the remote-session tier normally is (Remote worker session arguments), there is no parent-side capture to bring forward: durability is the worker's own to satisfy and an unadvancing remote head is the only symptom the parent will ever see.

**But the two capabilities are detected independently, so there are four combinations and not three, and the fourth is the one worth naming: a channel and no path.** There the nudge is a real act even though the capture is not — so use it. Instruct that worker to commit and push before escalating on its head, and repeat it, because repeating is all that is available: the "a second nudge is evidence the instruction is not landing" rule exists to stop the parent nudging *instead of* capturing, and where there is nothing to escalate to it forbids nothing. A nudge that may not land still beats a stall report that certainly does nothing, and it is the difference between work exposed and work pushed. **Repeat it on the elapsed-time observations the stalled-head rule already defines, not once per cycle** (Checkpoint compliance): the supervision loop has no minimum interval, so sibling completions and PR events can drive several cycles inside a minute, and a per-cycle nudge would deliver a burst of identical reminders to a worker whose only offence is being three minutes into reading the code. One nudge per observation, from the same clock and the same two-observation floor that governs the escalation it leads to. **And an advancing remote head clears the state, nudged or not** — that is the acknowledgement this loop gets, since no reply is readable here: the work the nudge asked for is now pushed, so the count resets to nothing and a later stall starts over. What the parent must not do is treat its own repetition as progress: the nudges are unacknowledged by construction, so the escalation's thresholds run on the head alone and are neither reset nor deferred by having sent another one.

So: **both** — nudge, then capture (subagents in parent-created worktrees, and serialized execution). **Path, no channel** — capture on first observation. **Channel, no path** — nudge, repeatedly, then the stalled-head escalation. **Neither** — the stalled-head escalation alone.

## Report

State, for the run — alongside what the sections above say to report:

- the **runtime tier** that ran, and any tier probed and rejected;
- the **base branch** every worker was created from;
- per task: the **model** assigned and the failure-visibility reason in a clause,
  plus any escalation and what triggered it — and **where the capacity veto moved
  the task off the tier that reason chose, say so and name what it measured**,
  since the failure-visibility reason alone then reads as an argument for a tier
  the task did not get, and the assignment cannot be audited from it;
- per task: the **watch state**, and for polled tasks when they were last read;
- every task whose watch state is unrecorded, named as a blind spot;
- what was **not** covered — tasks deferred, reads skipped, a tier's guarantee
  the runtime could not provide.

A swarm that reports only outcomes has withheld the part that says whether the
outcomes can be trusted.
