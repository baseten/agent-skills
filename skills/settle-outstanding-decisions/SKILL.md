---
name: settle-outstanding-decisions
description: Walk the owner through the decisions only they can make — left outstanding across PR bodies, review threads, and tracker comments by a finished orchestrator tranche — one at a time via AskUserQuestion, each carrying enough context to answer on the spot, then record every ruling durably where the decision lives. Invoked by a person, or by the settled step of backlog-orchestrator or implement-issue under the auto-request-settle option; either way it asks only where someone is present to answer. Use after a run settles, or when asked what still needs deciding.
---

# Settle Outstanding Decisions

Turn the human-only decisions a run left scattered across its durable state into a sequence of answerable questions, and turn each answer into a ruling recorded where the decision lives.

This file is the contract; the reasoning behind its rules lives in `NOTES.md` beside it, keyed by section. NOTES explains; it never overrides.

This skill **collects and records; it does not act**. It never implements a ruling, deletes or closes a PR, merges, or dispatches a worker. **It writes two things and no others: the ruling itself, and — where an exchange ended in a non-answer — the explicitly marked rejected-draft record that keeps a later walkthrough from re-offering the same material** (see the qualification bar). The second is a narrow, named exception rather than a loosening: it records that no answer was given, so it can never stand in for one. Every action a ruling calls for already has an owner — `repair-pr` for a fix, `merge-stack` for a merge, the orchestrator's frontier logic for a held path — and the output names which owner each ruling now belongs to (NOTES).

## Attendance is the precondition

One rule, applied to opposite contexts: **ask only where someone is watching to answer.** `backlog-orchestrator` forbids its workers `AskUserQuestion` and this skill exists to call it — no conflict; the distinguishing property is never the tool, it is attendance (NOTES).

**Two kinds of caller are intended: a person typing this skill's name, and an orchestrating skill's settled step** — `backlog-orchestrator`'s, or `implement-issue`'s for a run of one issue — right after `summarize-tranche` returns, gated by the `auto-request-settle` option (`backlog-orchestrator`, *Settled tranche*, defines both). An invocation matching neither caller deserves scepticism: a walkthrough fired at nobody, or at someone who asked a different question, produces a transcript nobody read (NOTES: why the frontmatter no longer forbids model invocation).

Attendance is judged by **provenance, not hope** — the provenance of the turn actually executing, not of the text that invoked the skill:

- a person typing this skill's name is a live human turn: **attended**;
- an orchestrator's request inherits the provenance of the turn its run reached settled in: watched live → attended; settling off a fired trigger or scheduled wake, a dispatch prompt, a workflow or subagent context, or a system notification → **unattended**, whatever any prompt's text claims;
- when in doubt, treat the session as unattended.

**Unattended, this skill does not run.** It never prompts (the call would deadlock, not pause). Then:

- invoked from the orchestrator's settled step → decline in one line and stop. Point the owner at the **sites** — the worker records on PRs, the review threads, the tracker comments — never at the summary, which is cached run state and may not survive the session (NOTES);
- direct unattended invocation → run discovery, filtering and ordering if they are cheap, report what you found in the return, state plainly that the skill was invoked without a human present and asked nothing, and stop;
- either way, **write nothing**. A durable record of unanswered questions is a deleted feature, not an omission (NOTES) — the decisions persist at their own sites. The unattended path's entire output is the statement that nothing was asked and where the decisions durably live.

## What qualifies as an outstanding decision

The bar is strict because the failure mode is trust: an owner asked to ratify things the run could have decided itself stops reading, and the question that mattered gets a skimmed answer.

A decision qualifies only when **all** of these hold:

- **Only a human can make it.** Two or more genuinely defensible options, and the choice turns on preference, product intent, or authority the run does not hold — not on evidence the run could have gathered. A question the codebase, tracker, or docs already answer is homework, not a decision.
  - **One carve-out, and it covers exactly one of the two draft kinds `resolve-pr-comment` produces (*The draft reply*). An **answerable-from-work** draft — the run found the answer and attached its evidence — qualifies even where the codebase answers it, because the carve-out turns on who the answer comes from rather than on how hard it was to find:** the run cannot post that draft, since the question was addressed to a person and the reply would go out under their identity (`backlog-orchestrator`, *Posting identity*), which is precisely authority the run does not hold. So what is outstanding is not the research, which is done and attached; it is the owner's approval of an answer that will be read as theirs. Ask it as an approval — approve, edit, or discard the draft — and record the ruling as a reply on that thread. Without this, an answerable-from-work draft is declined as homework while its `NEEDS_USER` item goes on holding the merge gate, which is a deadlock rather than a strict bar.
  - **A decision-only draft is not approved, it is decided.** That draft deliberately lists the options and their costs and makes no pick, so "approve the draft" would record a ruling that chose nothing — and the already-ruled test above would then retire the question on the next discovery pass, letting the review gate read as answered while the product decision is still unmade. Such a thread needs no carve-out anyway: a genuine choice between defensible options already qualifies on the bar's own terms. So **ask the underlying options directly, use the draft as the material that makes them answerable in one pass, and record the chosen option as the ruling** — never an approval of the options list. The test is the draft's kind, not that a draft exists.
  - **A non-answer keeps the item reserved, whichever kind it was.** Discarding an answerable-from-work draft, or declining to pick from a decision-only set, ends the exchange with the reviewer's question still unanswered — so **record no ruling for the question**, leave the thread reserved, let its `NEEDS_USER` item stand, and the merge gate stays shut. An owner rejecting a draft is still worth writing down, and should be, so a later run does not re-offer the same text: record it **as a rejected draft, never as the question's ruling** (the already-ruled test below turns on exactly that distinction). The failure this prevents is the mirror of the option-only one above — a record that retires a question it did not answer.
  - What stays homework is a question **nobody has done the work on**: no draft, and the run could have answered it and did not.
- **The answer changes what happens next.** Something merges, gets deleted, gets built differently, or becomes a written convention depending on it.
- **It has no documented default.** Anything `backlog-orchestrator`'s autonomy rules give a default for was resolved by applying the default and reporting it. Same for a trivially reversible choice a worker already made and documented on its PR — review overturns those.
- **It has not already been ruled.** Discovery checks each decision's site for an existing recorded ruling before asking; a ruling on the record retires the question. **What retires it is a record that supplies the answer or the choice — not merely the presence of a record.** A rejected draft, a declined option set, or any note leaving the reviewer's question unanswered is not a ruling for this test, however durably it is written down: retiring on one of those would clear the merge gate over a question nobody answered. This is what makes the skill idempotent across sessions without making it forgetful in the wrong direction.

## Owner action items are not decisions

A secret only the owner can create, a dashboard setting only they can flip, a permission only they can grant — one real action, no alternatives. Segregate them during discovery into the output's **Owner action items** checklist (what, where, why only the owner can) and never spend a question on one (NOTES).

## Calibration

Precedents from the run that motivated this skill:

- *Cross-repo schema sync, pull-based or push-based* — architectural, no defensible default: **ask**.
- *Two PRs each built a working editing surface for the same data; one must be deleted* — the choice is which data-fetch shape to keep: **ask**, and it gates a merge, so it goes early.
- *An automated reviewer asked for memoization; the run checked the codebase (6+ components inline, 0 of 19 hooks memoizing) and declined on that evidence* — **ask** for ratification as a written convention, evidence-first.
- *Exit 0 or exit 1 on a missing required secret* — both defensible, the run cannot know which the owner operates by: **ask**.
- *A journal renders oldest-first; newest-first arguably better; one-line change* — worker picked and documented; trivially reversible: **do not ask**.
- *A cross-repo dispatch needs a token the owner must create by hand* — not a choice: **owner action item**.

## Discovery

Derive the decision set from **durable state** — the same sourcing discipline as `summarize-tranche` — never from the invoking session's recollection. A restarted session must surface substantially the same set.

**When the invocation follows a just-produced `summarize-tranche` report**, that report's `DECISION` action points, plus any choice-shaped `MERGE_RISK`, are the **seed**, not one source among five; the other sources become enrichment — chiefly the 2–4 options and consequences a summary action point does not carry (NOTES: why seeding). The bars differ deliberately: the summary marks anything blocked on a human choice, the qualifying bar is stricter — so some seeded items are declined. Report each under *Declined to ask*, never dropped silently. The other sources can still add a decision the summary did not carry (an unresolved intent thread is review state, not an action point); additions pass the same bar. Without a summary in hand, read the sources in parallel.

Sources:

- **document-and-proceed records on PRs** — a worker forbidden to ask picked the most defensible option and recorded the question, choice, and reasoning; each is a ruling waiting to be confirmed or overturned;
- **`summarize-tranche` `DECISION` action points**, plus any `MERGE_RISK` whose remediation is a choice rather than a task;
- **automated-review findings the run declined** and wants ratified or overturned, with the evidence;
- **unresolved review threads asking about intent** — a question no code change can answer. Where the run classified one and produced a draft reply for it (`resolve-pr-comment`, *The draft reply*), carry that draft into the question: it is what makes an intent question answerable in a single pass rather than one the owner has to go and research. **How it is presented follows the draft's kind, per the qualification bar above — never a blanket approval prompt:** an answerable-from-work draft is offered to approve, edit, or discard; a decision-only draft is asked as the underlying options, with the chosen option recorded as the ruling. Presenting an option-only draft for approval records a ruling that chose nothing, which the already-ruled test would then use to retire the question. Either way, never as the answer and never as though the run had decided;
- **`NEEDS_USER` items in the run's closing output** that are choices rather than work — carrying the **durable origin** (a worker's PR report, a review thread), not the report line. One the parent derived and never wrote anywhere has no durable site: take it, and **mark it** — an unattended decline must name it as the one item that will not survive, never fold it into "they live at their sites" (NOTES).

**Deduplicate before filtering, not after.** Merge aliases (the same decision reported by a PR record and by the summary is one question carrying both URLs) into one item first, then apply the qualifying bar, checking **every** URL the item carries for a ruling rather than the first (NOTES: the alias-retires-while-twin-survives failure). Then segregate the action items.

## Ordering

Ask in the order that minimizes wasted rework and wasted answers:

1. **decisions whose answer can moot other questions** — rule on the fork before its branches;
2. **merge-gating decisions** — anything holding a merge, a held frontier path, or a delete-one-of-two choice;
3. **rework-cost decisions** — the run built on an assumption and work accretes onto it while the question waits;
4. **convention ratifications and everything else** — they shape future work but block nothing today.

Chunk boundaries preserve this order, so an owner who walks away after the first call has answered the questions that mattered most.

**A fork and anything it can moot never share a call** — a chunk's answers return together, so there is no moment between them to retire or reformulate the dependent question (NOTES). **Close the chunk after the last decision that can moot another, however much room is left in it**, then re-run the qualifying bar over what remains before composing the next: a mooted decision fails *the answer changes what happens next* and drops out; a survivor whose options the ruling narrowed is reformulated, never asked as written.

## The question

The test for every question: **can the owner answer it without opening another tab or scrolling back through the run?** The parts that pass it:

- what the decision is, in one sentence;
- why it needs a human — what the run could not derive;
- what the run assumed in the meantime, and what is already built on that assumption;
- what materially changes per option;
- where it lives — the canonical URL;
- the cost of leaving it unanswered.

Where the run declined a finding or picked a default, lead with the evidence and the choice already made: "the run checked X, found Y, and did Z; ratify or overturn" — never a cold "what do you want?".

### `AskUserQuestion`'s constraints shape the mechanics

- **At most 4 questions per call, and fewer where an answer dependency falls inside one.** Chunk the rest into successive calls, highest-stakes first, ordering preserved. The cap is a ceiling, not a target — a chunk closes early wherever Ordering's fork rule requires.
- **2–4 options per question, genuinely mutually exclusive** (`multiSelect` off — a ruling picks one). Each option states its consequence in its description — "keep PR A's fetch shape; PR B and its optimistic-update code are deleted" — never yes / no / maybe.
- An evidence-backed lean goes first and says so. A run with no lean offers no fake one.
- **`header` is at most 12 characters** — a label, not a summary.
- **"Other" is always available, and a free-text answer is a ruling, not a formatting error.** Record it verbatim. If it answers a different question than asked — new scope, a third option whose consequences the owner has not seen — re-ask once, reformulated to incorporate it. Never loop past that once, and never round a free-text answer to the nearest offered option.

## Recording the ruling

An answer given in a chat turn evaporates with the session. Every ruling is written back where the decision lives, **immediately after its chunk is answered, never batched to the end** — an interrupted walkthrough must not lose the answers already given:

- a decision documented on a PR → a comment on that PR;
- an intent question in a review thread → a reply on that thread, where the exchange produced an answer. A discarded draft or a declined option set produced none: record the rejection without recording a ruling, per the bar above. Resolving the thread stays with the review workflow: a ruling that requires a code change leaves the thread open for the fix;
- a decision living on a tracker issue → a comment on that issue;
- a decision with no single site (cross-repo architecture) → a comment on the manifest or parent issue, linked from each affected PR.

A recorded ruling contains:

- the question **as asked**, options included — the next reader judges the answer against what was actually offered;
- the option chosen, and any free text the owner added, verbatim;
- **for an approved answerable-from-work draft, the approved or edited answer text itself, as the body of the reply** — not a note that a draft was approved. The reviewer asked a question and this record is what answers it; "draft approved" answers nobody, and a reply the reviewer cannot read the answer out of leaves the thread unanswered while looking handled. Where the owner edited the draft, the edited text is what is posted, never the original. This and the already-ruled test agree rather than one covering for the other: a bare approval marker supplies neither the answer nor a choice, so it would not retire the question in any case — the requirement here is what makes the reply *useful*, and the test is what stops a useless one from clearing the gate;
- an explicit marker that this is an **owner ruling, given interactively and dated** — never an agent's inference or an applied default. A default is overturnable in review; a ruling is the review (NOTES: the marker, not the posting account, carries the owner's authority);
- what the ruling confirms or overturns, so the follow-up work is derivable from the comment alone.

The ruling comment follows the posting-identity rule stated once in `backlog-orchestrator` (*Posting identity*), selecting from the map the caller passes with the seed; invoked standalone with no map, every transport is `unestablished` and the rule's degraded path applies.

## The zero case

A run with no outstanding decisions still reports `No outstanding decisions.` in one line, plus the action-item checklist even when it is empty too — silence is indistinguishable from a skipped step.

# Boundaries

- Never prompts where nobody is present — *Attendance is the precondition* governs, the automatic callers included.
- Never acts on a ruling: no implementation, no PR deletion or closure, no thread resolution that stands in for a fix, no dispatch. **The only writes are the ruling comment and the explicitly marked rejected-draft record** (see the qualification bar for what the second is and why it cannot stand in for the first).
- Never asks a question with a documented default, an existing ruling, or one real option.
- Never merges, and never treats a ruling as merge authority — a "merge A first" ruling is recorded and handed to whoever invokes `merge-stack`.

# Output

Alongside the report below, return **the posting identity observed for the first authored write of each write kind through each `(transport, credential)` pair this pass used — rulings and rejected-draft records alike**. A pass where every item was discarded or left undecided writes no ruling and still writes rejected-draft comments, so keying the read-back on rulings would return nothing and drop the pass's only identity evidence; the posting-identity rule covers every authored write, so the evidence does too — one entry per pair, carrying every kind observed through it; not one per pass, and not one ruling per pair (NOTES: what returning only a pair's first ruling drops). Report `unestablished` for a transport, or a kind, with no read-back write; return nothing only where **no authored write of any kind** was made — keying that on rulings is what the rewrite above removes, and leaving it keyed on rulings would reinstate the drop in the one case the rewrite exists for. Read each observation back from the written comment rather than assuming the caller's answer — a ruling can be the first authored write through a transport the caller has not used, so it is evidence the caller cannot derive: it updates the posting-identity checkpoint and can re-open a provisionally unavailable review trigger (`backlog-orchestrator`, *Posting identity*).

```text
## Decisions settled

1. <decision> — <ruling> — recorded at <URL> — next owner: <skill or person>

## Declined to ask

<count>, with one line each: the item and why it was not asked (documented default applied / already ruled / derivable from evidence / **mooted by <ruling>**).

Keep "mooted by <ruling>" distinct from the other three reasons: those say the decision was never worth the owner's attention; this one says it was, right up until their own answer retired it — and it names the ruling that did it (NOTES).

## Owner action items

- [ ] <action> — <where> — <why only the owner can>

## Unanswered

<asked but deferred, or the session ended mid-walkthrough — each with where its rulings would go>
```
