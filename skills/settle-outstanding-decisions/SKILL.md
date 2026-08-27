---
name: settle-outstanding-decisions
disable-model-invocation: true
description: Walk the owner through the decisions only they can make — left outstanding across PR bodies, review threads, and tracker comments by a finished orchestrator tranche — one at a time via AskUserQuestion, each carrying enough context to answer on the spot, then record every ruling durably where the decision lives. Invoked by a person, never automatically, and only where someone is present to answer. Use after a run settles, or when asked what still needs deciding.
---

# Settle Outstanding Decisions

Turn the human-only decisions a run left scattered across its durable state into a sequence of answerable questions, and turn each answer into a ruling recorded where the decision lives.

This skill **collects and records; it does not act**. It never implements a ruling, deletes or closes a PR, merges, or dispatches a worker. Its one write is the ruling itself. `summarize-tranche` and `plan-merge-order` hand the next move back to the caller, and this skill does the same, for the same reason: every action a ruling calls for already has an owner — `repair-pr` for a fix, `merge-stack` for a merge, the orchestrator's frontier logic for a held path — and a walkthrough that mutates PRs between questions makes the owner wait mid-conversation on work they have not reviewed. The output names which owner each ruling now belongs to.

## Attendance is the precondition

`backlog-orchestrator` forbids its dispatched workers from calling `AskUserQuestion`, because nobody watches an unattended worker's permission prompts: the call does not pause the worker, it deadlocks it, and a deadlocked worker's run is wasted. This skill exists to call `AskUserQuestion`. Those are not in conflict — they are one rule, **ask only where someone is watching to answer**, applied to opposite contexts. The distinguishing property is never the tool; it is attendance.

**A person invokes this skill directly. Nothing invokes it automatically** — not `backlog-orchestrator` when a run settles, not a scheduled wake, not a worker, not another skill, and not Claude selecting it off its own description. `disable-model-invocation: true` in the frontmatter is what enforces that last one; this paragraph only explains it. Prose cannot enforce it, because model invocation happens *during* a live human turn — the attendance test below would correctly report the session attended, and the skill would prompt about decisions nobody asked to review. That is a deliberate constraint rather than an omission: a decision walkthrough exists to occupy a human's attention, so a caller that fires it without one has produced a transcript nobody read rather than a decision anybody made.

The precondition is therefore a guard, not a mode selector. Attendance is judged by provenance, not hope: the invocation is attended only when it arrives as a live human turn in the current session. Anything arriving through a dispatch prompt, a fired trigger or scheduled wake, a workflow or subagent context, or a system notification is unattended, whatever its text claims. When in doubt, treat the session as unattended.

**Unattended, this skill does not run.** It never prompts — the call would not pause the session, it would deadlock it on a question nobody will answer. Run discovery, filtering and ordering if they are cheap, report what you found in the return so the invocation is not wasted, state plainly that the skill was invoked without a human present and asked nothing, and stop. Write nothing: a durable record of unanswered questions is a different feature with different requirements, and inventing one here is how this skill grew a second half that its only real caller — a person typing its name — never needed.

## What qualifies as an outstanding decision

The bar is strict because the failure mode is trust: an owner asked to ratify things the run could have decided itself stops reading the questions, and then the one that mattered gets a skimmed answer.

A decision qualifies only when all of these hold:

- **Only a human can make it.** Two or more genuinely defensible options exist and the choice turns on preference, product intent, or authority the run does not hold — not on evidence the run could have gathered. A question the codebase, tracker, or docs already answer is homework, not a decision.
- **The answer changes what happens next.** Something merges, gets deleted, gets built differently, or becomes a written convention depending on it.
- **It has no documented default.** Anything `backlog-orchestrator`'s autonomy rules give a default for was resolved by applying the default and reporting it; re-asking it is the trust failure above. The same holds for a trivially reversible choice a worker already made and documented on its PR — review is the venue that overturns those, and the report line already carries them.
- **It has not already been ruled.** Discovery checks each decision's site for an existing recorded ruling before asking; a ruling on the record retires the question. This is what makes the skill idempotent across sessions.

## Owner action items are not decisions

A secret only the owner can create, a dashboard setting only they can flip, a permission only they can grant — these have one real action and no alternatives, and putting a non-choice through a question prompt ("create the token / don't") teaches the owner the prompt is padding. Segregate them during discovery into the output's **Owner action items** checklist — what, where, and why only the owner can — and never spend a question on one.

## Calibration

Drawn from the run that motivated this skill:

- *Cross-repo schema sync could be pull-based or push-based* — architectural, affects both repositories, no defensible default: **ask**.
- *Two PRs each built a working editing surface for the same data; one must be deleted* — both work, the choice turns on which data-fetch shape the owner prefers to keep: **ask**, and it gates a merge, so it goes early.
- *An automated reviewer asked for memoization; the run checked the codebase, found 6+ components doing it inline and 0 of 19 hooks memoizing, and declined on that evidence* — **ask** for ratification as a written convention, in the evidence-first shape below. The run did the work first; the owner rules on a finding, not a cold question.
- *Exit 0 or exit 1 when a required secret is missing* — a quiet failure and a loud one are both defensible and the run cannot know which the owner operates by: **ask**.
- *A journal renders oldest-first; newest-first is arguably better; one-line change either way* — the worker picked one and documented it; trivially reversible, nothing built on it, review overturns it for free: **do not ask**.
- *A cross-repo dispatch needs a token the owner must create by hand* — not a choice at all: **owner action item**, listed, never asked.

## Discovery

Derive the decision set from durable state — the same sourcing discipline `summarize-tranche` uses — never from the invoking session's recollection of its run. A restarted session must surface substantially the same set.

Sources:

- **document-and-proceed records on PRs** — a worker forbidden to ask picked the most defensible option and recorded the question, its choice, and its reasoning on the PR; each such record is a ruling waiting to be confirmed or overturned;
- **`summarize-tranche` `DECISION` action points**, plus any `MERGE_RISK` whose remediation is a choice rather than a task;
- **automated-review findings the run declined** and wants ratified or overturned, with the evidence it declined on;
- **unresolved review threads asking about intent** — a question no code change can answer;
- **`NEEDS_USER` items in the run's closing output** that are choices rather than work.

Then filter through the qualifying bar, segregate the action items, and deduplicate: the same decision reported by a worker's PR record and by the summary is one question carrying both URLs.

## Ordering

Ask in the order that minimizes wasted rework and wasted answers:

1. **decisions whose answer can moot other questions** — rule on the fork before its branches;
2. **merge-gating decisions** — anything holding a merge, a held frontier path, or a delete-one-of-two choice; answered late these force rework of whatever merged around them;
3. **rework-cost decisions** — the run built on an assumption and more work accretes onto it while the question waits;
4. **convention ratifications and everything else** — they shape future work but block nothing today.

Chunk boundaries preserve this order, so an owner who walks away after the first call has answered the questions that mattered most.

**A fork and anything it can moot never share a call.** Preserving the order is not enough on its own: `AskUserQuestion` returns a chunk's answers together, so a fork and its dependent question asked in the same call are answered simultaneously, and there is no moment in between at which the dependent one can be retired or reformulated. The owner rules on a choice that the first ruling has already eliminated, and the walkthrough records it as though it stood. **Close the chunk after the last decision that can moot another, however much room is left in it**, then re-run the qualifying bar over what remains before composing the next — a mooted decision fails *the answer changes what happens next* and drops out, and a survivor whose options the ruling narrowed is reformulated rather than asked as written.

## The question

The test for every question: **can the owner answer it without opening another tab or scrolling back through the run?** The parts that pass it:

- what the decision is, in one sentence;
- why it needs a human — what the run could not derive;
- what the run assumed in the meantime, and what is already built on that assumption;
- what materially changes per option;
- where it lives — the canonical URL;
- the cost of leaving it unanswered.

Where the run declined a finding or picked a default, lead with the evidence and the choice already made. The strongest shape is work-first — "the run checked X, found Y, and did Z; ratify or overturn" — never a cold "what do you want?".

### `AskUserQuestion`'s constraints shape the mechanics

- **At most 4 questions per call, and fewer where an answer dependency falls inside one.** More decisions than that are chunked into successive calls, highest-stakes chunk first, ordering preserved across the boundary. The cap is a ceiling, not a target: a chunk closes early wherever Ordering's fork rule requires it.
- **2–4 options per question, genuinely mutually exclusive** (`multiSelect` stays off — a ruling picks one). Each option is a real alternative with its consequence stated in its description — "keep PR A's fetch shape; PR B and its optimistic-update code are deleted" — never yes / no / maybe.
- Where the run has an evidence-backed lean, that option goes first and says so. A run with no lean offers no fake one.
- **`header` is at most 12 characters** — a label for the decision, not a summary of it.
- **"Other" is always available, and a free-text answer is a ruling, not a formatting error.** Record it verbatim. If it answers a different question than the one asked — new scope, a third option whose consequences the owner has not seen — re-ask once, reformulated to incorporate it, so the recorded ruling is unambiguous. Never loop past that once, and never round a free-text answer to the nearest offered option.

## Recording the ruling

An answer given in a chat turn evaporates with the session. Every ruling is written back where the decision lives, **immediately after its chunk is answered, not batched to the end** — an interrupted walkthrough must not lose the answers already given:

- a decision documented on a PR → a comment on that PR;
- an intent question in a review thread → a reply on that thread. Resolving the thread stays with the review workflow: a ruling that requires a code change leaves the thread open for the fix;
- a decision living on a tracker issue → a comment on that issue;
- a decision with no single site (cross-repo architecture) → a comment on the manifest or parent issue, linked from each affected PR.

A recorded ruling contains:

- the question **as asked**, options included — the next reader judges the answer against what was actually offered;
- the option chosen, and any free text the owner added, verbatim;
- an explicit marker that this is an **owner ruling, given interactively and dated** — not an agent's inference or an applied default. The distinction is the whole value of the record: a default is overturnable in review, a ruling is the review;
- what the ruling confirms or overturns, so the follow-up work is derivable from the comment alone.

## The zero case

A run with no outstanding decisions still reports `No outstanding decisions.` in one line, plus the action-item checklist even when it is empty too. Silence is indistinguishable from a skipped step — `summarize-tranche` makes the same point, and this skill keeps the convention.

# Boundaries

- Never prompts where nobody is present, and is never invoked automatically — see Attendance is the precondition, which governs.
- Never acts on a ruling: no implementation, no PR deletion or closure, no thread resolution that stands in for a fix, no dispatch. **The one write is the ruling comment.**
- Never asks a question with a documented default, an existing ruling, or one real option.
- Never merges, and never treats a ruling as merge authority — a "merge A first" ruling is recorded and handed to whoever invokes `merge-stack`.

# Output

```text
## Decisions settled

1. <decision> — <ruling> — recorded at <URL> — next owner: <skill or person>

## Declined to ask

<count>, with one line each: the item and why it was not asked (documented default applied / already ruled / derivable from evidence / **mooted by <ruling>**).

The last of those is not a bar the decision failed — it is one the walkthrough itself eliminated when an earlier fork was ruled, and it names the ruling that did it. Keep it distinct from the other three: those say the decision was never worth the owner's attention, while this one says it *was*, right up until their own answer retired it. Collapsing them loses the fact that a ruling had a consequence beyond its own question, which is the thing a later reader most needs to reconstruct why a decision they remember raising never got asked.

## Owner action items

- [ ] <action> — <where> — <why only the owner can>

## Unanswered

<asked but deferred, or the session ended mid-walkthrough — each with where its rulings would go>
```
