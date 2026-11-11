# Operator output

This is the rule other skills mean when they cite *operator output*: what an orchestration run, or a planner, writes to the owner in its own chat.

**It is not a skill and nobody invokes it.** It is a shared rule, held once at
`rules/operator-output.md` and copied into each skill that applies it by
`scripts/refresh_shared_rules.sh`. A skill reads its own
`references/operator-output.md`, which works after `bootstrap.sh` has
installed only that skill's directory, and travels with the skill if it is
moved into a plugin. Edit the source, never a copy; check_shared_rules.py fails if a generated copy diverges.

It governs the chat only. A forge or tracker write — a ledger kept as a forge issue included, whose SHAs stay bare — follows the *authored write form* shared rule; a message to another session follows its own form (the *conductor exchange* shared rule, *Reports*).

## What reaches the chat

**Only what needs the owner, what changed state since the last report, and answers to the owner's questions.** The report never carries:

- **process narration** — what the run is reading or about to do, a check-in's or trigger's id, a sweep count;
- **the checking** — the chat says *verified*, never how;
- **unchanged status the owner cannot act on** — a PR still waiting on a named reviewer, a run still working — beyond a count. A change into such a state is reported once;
- **a list reprinted unchanged** (*Needs you*, below).

## The report

A reporting turn ends with these, in this order, each omitted when empty:

1. **Needs you**, grouped by what the owner does, each group a bold line, one line per item with its links:
   - **Merge**
   - **Review or assign a reviewer**
   - **Review and submit** — a review drafted for the owner (`conductor`, `reviewers.md`): its drafts link, the recommendation and the blocking count; the line never carries the draft text, and the draft is never under *Approve drafts*
   - **Decide** — asked as *Questions* says
   - **Confirm in a session** — a prompt a run's or a reviewer's session waits on, naming the literal tool string (`swarm`, *Blocked workers*)
   - **Approve drafts** — each linked to its full text, or naming where it is held; the line never carries the text
   - **Owner steps**
   - **Clear a failure** only the owner can clear

   **Reprint it only when its items changed since the last report printed it**; otherwise one line, `3 still waiting on you, unchanged`, linking the ledger and any work queue beside it — its questions not asked again (*Questions*). Where the last printed list has left context, reprint.
2. **Changed since <time>** — since the last report, or the run's start — each state change once, by work stream, then issue, within a stream's cap (*Headings and links*). **A table only here**, where rows share columns: runs started, each with its session and its go's record, placed under the label and before the streams; a run in it gets no block of its own until a later report.
3. **`Unchanged: …`** — one line of linked counts.
4. **A link to the ledger**, or for a run without one, to its epic or issue — and beside it the consumer's work queue, a page rendering *Needs you*, where it keeps one.

**Times** are the owner's local time where the session knows their timezone, otherwise UTC, labelled either way; a title's times excepted. **A `---` line separates top-level groups** — a record, a meta answer, each report section, and each work stream's block, so a `---` always precedes a stream's heading. **A blank line goes before and after every `---`**: directly under a line of text, `---` turns that line into a heading.

**The report is the turn's last text**, bar, in this order: questions nothing earlier in the turn needed; a consumer's closing proposal, such as a `conductor`'s context-clear proposal; and a coordinated run's `final status:` line (the *conductor exchange* shared rule, *Reports*), always last.

## Records

**A record a consumer's contract requires** — a state block, a closing report, a structured result, settle outputs — keeps its contract's fields and form, ids and tables included; *What reaches the chat* does not bind it, and the link form below fills only what its contract leaves open. It prints before the report, headed where its contract sets no heading. **A record emitted every cycle or pass prints only when it changed** — a new as-of time, check-in id, wake count, next firing or waking event alone is no change — and once more whenever the last printed one has left the session's context — after a compaction, a restart or a clear — so it is never lost from view; otherwise the last printed one stands. The report restates no record, but an item needing the owner is always under *Needs you*.

## Headings and links

**Every block opens with a line naming its subject.** A report section's label — *Needs you*, *Changed since <time>* — is a short bold line, never a heading; **a work stream is a `##` heading, linked** — a session the report follows: a run, by its session's title, its repository and its epic, or its issue for a single-issue run; a reviewer, by its session's title, its repository and its PR; an issue is a bullet under its stream — its tracker issue and its PR, with its worker session where it has its own. A run's own report uses the same levels, with its one stream heading under *Changed since*; *Needs you* groups by action, not by stream.

**A stream's block is one status sentence and at most four bullets.** A change to the stream itself — dispatched, retired, failed, archived — is its status sentence, linked to its record; each bullet is an issue's change, most consequential first. What does not fit is left out, one closing line giving the count and linking where the full list is kept — for a `conductor`, the run's session, whose own report lists it; for a run, its record (`+3 more in the session`).

**Every reference is a link** — an issue, a PR, a session (`https://claude.ai/code/<session id>`, its title as the link text), a repository, a commit — never a bare id, a raw session id, or a title standing in for a link; text shown for approval exactly as it will be posted is shown as it will be posted. **Name each repository once per block** — in the run's heading, or on a *Needs you* group's line where its items share one — then write short `#N` refs, always linked. In a table cell a session's link text may drop its title's prefix, so it does not wrap.

A `conductor`'s turn:

```text
**Needs you**

**Merge** · [acme/api](…)
- [#841](…) — settled · [Worker: acme-api · #810 export](…)

**Review and submit** · [acme/web](…)
- [#93](…) — request changes, 1 blocking · [drafts](…) · [Reviewer: acme-web · #93 cache keys](…)

---

**Changed since 14:00 (UTC)**

---

## [Orchestrator: acme-api · #2005 exports](…) · [acme/api](…) · [#2005](…)
Two issues merged; four still in flight.
- [#2011](…) · [#2040](…) — merged
- [#2012](…) · [#2041](…) — merged

---

## [Worker: acme-web · #77 search box](…) · [acme/web](…) · [#77](…)
PR opened, waiting on CI.
- [#77](…) · [#91](…) — PR opened

---

Unchanged: [3 runs](…) · [1 PR waiting on a reviewer](…)
[Ledger](…)
```

A run's turn, after its record:

```text
**Changed since 09:00 (UTC)**

---

## [Orchestrator: acme-api · #2005 exports](…) · [acme/api](…) · [#2005](…)
One issue merged; three still in flight.
- [#2012](…) · [#2041](…) — merged

---

[#2005](…)
```

## Questions

**One question per call**, through the platform's structured question tool (`AskUserQuestion` in Claude Code), never a numbered prose list, ordered by what each unblocks unless the consumer orders its own. **A planner's blocking questions are the one exception**: `write-spec` and `plan-feature` ask the questions their document cannot proceed without together, once, before drafting — at most four per call, each with a *defer* option; their open-ended design discussion stays one per call. **A question a flow needs answered is asked where the flow needs it**; the rest follow the report. **A question already asked is not asked again** while its item is unchanged, unless the owner asks for it; a walkthrough a contract runs (`settle-outstanding-decisions`) asks what its own bar qualifies. Where nobody is present, nothing is asked: each item stays under *Needs you* with its site.

- **Before each question, the chat repeats that item's heading and link line**, because links may not render inside the question.
- **The question text stands alone, naming the repository, the issue id and its title in plain words**; its `header` chip is the issue id (`#812`), or the PR's; a question about no single issue — a plan, a dispatch go — names its repository and subject under a short label.
- **2–4 options, one marked recommended** — the evidence-backed lean, first; where the run has none it says so rather than invent one — each stating its consequence, never also listed in prose.

## Meta answers

**A question the owner asks that is not about a run's state** — how a skill works, why it did something — **is answered in its own block, before the report**. A turn that only answers one writes no report, bar a closing line its consumer requires.

## Quiet turns

**A check-in is quiet when it read everything it tracks and found nothing new**: no delta (the *wake budget* shared rule's unproductive wake), no deferred read and no blind spot (the *watch and read* shared rule's no-change preflight), nothing acted on beyond sending status requests and updating its own ledger, no watch stopped or ended — a held watch reaching its deadline included — its last printed record still in context, and nothing newly needing the owner — a closing proposal included. **A `conductor`'s turn for a run's reply is quiet when the reply, verified, changes nothing its ledger records**; it reports and records no no-change result, so it owes no preflight. An attended turn is never quiet, and a wake that stops or ends a watch is not: it is reported as the *wake budget* rule requires.

**A quiet turn writes one minimal line and nothing else** — whether a turn can end with no text is not established: a coordinated run's `final status:` line where its contract requires one, otherwise `quiet`. It prints no record; a quiet check-in's no-change preflight result — the tracked set, each item's watch state, a polled item's last-observed time — rides the re-armed wake's prompt with the count.

**A quiet check-in updates the session's title**, the one surface that changes in place: where the session has `set_session_title`, it appends a suffix beginning ` · quiet` that says since when, how many items wait on the owner, and when it next checks — `Conductor: acme-api · quiet since 22:59 · 3 waiting on you · next 00:59`. Everything before ` · quiet` stays exactly as it was and is what a sweep matches; the first turn that reports, and the watch stopping, remove the suffix. A quiet reply turn leaves the title alone. Where the title cannot be set, the minimal line is the suffix's text, except that a coordinated run's stays its `final status:` line. A title is a finding aid, never evidence.

## Collapsing

**Leave content out — to the ledger or the record, linked — rather than collapse it.** `<details>` shows raw tags where HTML does not render: use it only on a surface established to render it — a GitHub body or comment, not this chat.
