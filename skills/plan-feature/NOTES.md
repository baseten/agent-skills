# plan-feature — design notes

Reasoning behind `SKILL.md`, keyed by its section names. NOTES explains; it never
overrides.

## Plan feature

**Why this skill exists (owner's ruling, 2026-11-04):** the conductor planned
features in one section (#201, ruling B), and planning grew past it. The owner split
the pipeline: `write-spec` → `plan-feature` → `conductor`, the conductor keeping the
portfolio and the owner's decisions. The owner asked for it to be simple.

**Why one level per run, and never split by type:** a product issue, an epic, a
project and a brief all need the same thing — PR-sized children under one parent —
so one contract serves them, and a run that also wrote the level above would be
writing product issues, which belong to whoever owns the product. The prior art
measured the per-type question directly: most of its epics mixed several kinds of
work, and a per-type route would have misfitted a quarter to nearly half of their
phases, while the type-specific lessons read as conditions inside one skill.

**The owner's drafts (owner's ruling, 2026-11-04).** The owner wrote their own
Linear planning skills from real runs — a planner, a full-ticket writer, a backend
stub writer, a project audit and a mechanics reference — and ruled that the process
lives here, generically, with their deployment's settings layered on top by a thin
skill elsewhere. The working set, comments as the home of decisions, reading at the
remote default branch, full and stub children, blockers only from real constraints,
priority as build order, estimates on full children only, human signatures never
applied, dependency-order writes with a re-read before any retry, inline design
frames, the permission rule and the report all come from those drafts, generalised
and with every deployment-specific name left out. **Overruled:** their draft
reported the plan in chat with no document; the plan stays a tracker document.

**Prior art.** The source table, the fixed research brief with its
contradiction question, the cutting principles and named cut patterns, the
manual-step definition, amend-in-place with a `changes:` list, the hand-up line, and
the single sizing authority all come from [essmahr/planet](https://github.com/essmahr/planet), a coworker's planning
plugin. It carries no licence, so nothing here is copied from it; the ideas are
paraphrased. Left behind on purpose: its CLI, hooks and private store; plan mode as
the approval gate; implementing straight after planning; re-cuts that drop and
recreate items; and recording prompts verbatim.

## Baselines (2026-11-04, before the contract was written)

Three realistic prompts, each given to a fresh subagent with no skill and no file
access, answering as a dry run:

1. **A product issue across a frontend and an API repository.** It read the code in
   its own thread, asked six questions in one message (two of them about where to
   file), cut a sensible contract-first plan with the frontend blocked by the API,
   and showed it as a chat table. Each ticket was one flat description — context,
   contract, files, tests — with no part written for a person and nothing
   collapsed. It sized tickets by its own rule of thumb (lines, days).
2. **An epic with a column rename, a backfill, an announcement and a marketing
   item.** It chose expand-contract unprompted and made the backfill its own issue,
   but turned the announcement into a checklist item on the epic and the marketing
   item into a tracked external dependency, and showed the plan only in chat.
3. **A rejection that also exposes a spec gap.** It edited the plan in place and
   re-showed only the changes — matching this contract — but treated the spec gap
   as an open question it would ask itself, then filed the blocked child anyway,
   labelled as needing a decision, and closed by offering to start the orchestrator.

**What the contract targets from them:** no human-readable top section and no
collapsed agent section (1–3); the plan living only in chat (1, 2); a size rule each
run made up (1); an announcement kept as plan work (2); a spec gap patched around
rather than handed up (3); an offer to dispatch rather than a pointer (3). What they
did well — expand-contract, frontend blocked by backend with the contract in the
ticket, edit in place — is kept.

## Configuration

**The hooks a thin skill uses** — every `feature-plan` field, passed as an invocation
argument: `tracker`, `parent-kind`, `child-labels`, `sections`, `plan-doc`,
`child-kinds`, `needs-validation-label`, `not-ready-labels`, `human-signatures`,
`priority-is-build-order`, `product-priority-prefix`, `estimate-scale` and
`evidence-sources`. A design image needs no key. **Why labels and kinds are keyed by
repository:** a child's repository is a token its own text already names, so the
mapping is mechanical and never read from prose — a deployment whose frontend is
full and backend a stub says so in two entries.

**Why a brief's draft stays in chat until the go:** a brief has no parent, and
creating one before the owner approves would be a durable write nobody asked for.
**Why `repo`, `acceptance` and `dependencies` cannot be dropped (contradiction pass,
2026-11-04):** the `Blocked by:` line is what `normalize-github-dependencies` and
`validate-backlog` read on GitHub, and a child with no repository or acceptance is not
implementable. **Why the default plan document is a project document:** the owner
ruled that the plan lives in the tracker, and a document beside the issues needs no
one's permission; a comment on someone else's parent does (*Rules*).

## Rules

**Why the permission rule exists:** a product issue belongs to whoever wrote it,
and rewriting it, however stale it looks, is not the planner's call; creating a
child under it is the whole job. Drafting rather than posting a message to a person
is protected rule 1's direction — a run never answers a person — applied to every
channel. It does not touch PRs, which protected rules 1 and 6 already govern.

**Why nothing here reads a footer (owner's ruling, 2026-11-05):** the cloud
transport appends a footer to every write, so it can carry no meaning; #206 holds
the footer rules. **Why every child's full text is still shown in chat
(contradiction pass, 2026-11-04):** the owner's go approves what it was shown;
showing only titles made "approved" a claim about text the owner may not have read.
Scenario: `the-go-approves-only-text-shown-in-chat`.

**Why the permission rule is shared (owner's ruling, 2026-11-05):** it began as
this skill's, from the owner's drafts, and binds every skill that writes to issues,
so it lives in `rules/authored-write-form.md`, *Issues the run did not create*. A
run's invocation naming an issue is the permission for the comments its contract
requires there, which keeps an orchestrator's hold items on its in-scope issues
lawful; it never reaches a description another person wrote unasked.

**Why the fallback plan document is a new plan issue (owner's ruling, 2026-11-05):**
the default once ended "else a comment on the parent" — prose on someone else's
issue, which the shared permission rule forbids unasked, and the normal path on
GitHub, where an epic has no project document. A plan issue this run creates is its
own to write and amend.

**Why human signatures are never applied:** a readiness label or title marker says
a person reviewed the issue. A run applying one forges that sign-off, and everything
downstream that trusts it inherits the forgery.

**Why grep before claiming something is missing:** the owner's runs filed tickets
for test coverage and helpers that already existed; more than once the honest answer
was that the ticket should not exist.

**Why hand up, never patch:** baseline 3 filed a child blocked on an unanswered spec
question, which leaves an issue no one can finish and a spec still saying the wrong
thing. **Why re-scope keeps off an open item's site:** a run's reply watch reads a
write under the owner's account there as a possible answer.

## 1. Choose the working set

**Why skip already-planned parents:** re-planning one creates duplicates, which is
easy to do and expensive to undo. **Why never skip silently in single-parent mode:**
the owner pointed at that parent deliberately. **Why agree the set before reading
deeply:** it is the cheapest moment to correct a wrong scope.

## 2. Read

**Why every comment:** decisions — who ruled what, and when — live in comments far
more often than in descriptions, and a child that reopens a settled point costs a
round trip. **Why a project's issues are listed, not fetched:** most are context,
and fetching all of them spends the context the plan needs. **Why ask for a missing
design rather than plan around it:** asking costs one message; speccing the wrong
thing costs a rewrite.

## 3. Research

**Why the remote default branch:** a session's checkout is a snapshot from whenever
its container started, and nothing warns that it is old. On the owner's first real
run the checkouts were about two weeks stale, which produced a confident, wrong
claim that a field did not exist — it had shipped a week earlier. **Why an
unreadable repository stops its children:** a stub's whole value is that its gap was
verified, and "this does not exist" is the claim most likely to be wrong. **Why a
generated, untracked file is never evidence:** it has no SHA and no date, so nothing
pins a claim to it and nothing says how old it is.

**Why a fixed brief on a cheaper model, five lines back:** the prior art found
research dispatches that named no model, or had grown extra instructions, ran slowly.
The questions are factual. Question (4) most often changes a plan; question (5)
stops a child for work that exists.

## 4. Ask

**Why blocking questions go together once, up front:** see
`rules/operator-output-notes.md`, *Questions*. **Why a deferred question becomes a
spike or a left-out child:** drafting a child whose shape depends on it fixes an
answer nobody gave.

## 5. Draft

**Why each principle:** dependency then uncertainty puts the work most likely to
change the plan first; merging tiny pieces avoids review overhead; shipping dark
separates merging from releasing; settling shape-neutral decisions stops the
implementer guessing.

**Why a step with no PR is an item, and an announcement is not:** a backfill or a
flag flip changes the system and has an order relative to the code. Posting a
message changes nothing; the prior art's planner proposed an "announce the change"
phase in its first live run. Such a step is an owner step under
`rules/manual-step-issues.md`, filed in its form and under its opt-in.

**Why blockers only from a real constraint:** "always filter on the server" is a
good principle and no blocker where the list is unpaginated and already carries the
field; that child could have shipped today and was parked. Every edge is work
someone cannot start, so each must be a fact about the code.

**Why priority means build order where configured, and the one defect:** product
priority and build order are two axes and are expected to disagree — a top-priority
product issue whose children sit lower means something else is being built first.
An enabler outranks what it enables, because that is what the field is for. The only
unambiguous defect is a child ranked above its own blocker: it cannot be built
first.

**Why stubs get no estimate:** sizing someone else's design anchors them and makes
a guess look like a commitment.

**Why the API contract is in both full children:** each implementing agent reads
only its own child. **Why a stub designs no API:** see *The child issue*.

## The child issue

**Why two kinds:** work this owner's side ships is written to be built unaided; work
another team owns is a question, because that team decides the design. A
confidently specced ticket for someone else's side is worse than none: they either
follow a guess worse than their own choice, or rewrite it. A stub keeps to what the
planner can state and nobody else can — what is needed, what is missing today,
what waits on it, what is settled — and carries a label saying it must be shaped.

**Why a stub's first line is a token (contradiction pass round two):** a stub under
a parent is otherwise an ordinary sub-issue, and the conductor dispatches a parent's
children as an issue set; `backlog-orchestrator` and `validate-backlog` treat an
issue whose first line begins `Stub:` as an external prerequisite, as they do a
`[Manual]` issue. A label alone could not be that token: `needs-validation-label`
is optional.

**Why two parts in a full child:** people need the problem and the acceptance in
plain words; the implementing agent needs files, decisions and a check. Collapsing
the agent part keeps the issue readable without hiding anything.

**Why one inline image per child, stubs included:** links go unclicked; an inline
frame gets looked at, and on a stub it shows the owning team what data is needed.
A flow board renders as unreadable thumbnails. **Why say "not drawn":** it tells the
implementer the shape is theirs to propose, and it separates "no design yet" from
"forgot the screenshot".

**Linear's collapsible (verified 2026-10-14):** `+++ Title` … `+++`, recorded with
its verification in `rules/linear-mechanics-notes.md`. It replaces the headed
fallback this skill's first draft used while the syntax was unestablished. GitHub's
`<details>` without `open` is closed by default.

**Why symbols, not line numbers, and a copied contract:** line numbers drift within
days, and an invented field name sends the implementer down a rabbit hole and makes
them distrust the rest.

## 6. Self-check

**Why one sizing authority:** the prior art had its cutter estimate size and its
planner re-measure it, and at least seven re-cuts came from the two disagreeing.
**Why fresh, holding only that child:** a reader who has seen the whole plan fills
gaps the implementer will not have.

## 7. Show and amend

**Why the draft lives in the tracker (owner's ruling, 2026-11-04):** a plan in chat
is gone when the session ends. **Why amend in place and re-show only the change:**
the prior art re-showed about two thousand words for one-entry changes, and
regenerating risks quietly changing what the owner accepted.

## 8. Write

**Why stubs and blockers first:** a `Blocked by:` line can name only an issue that
exists. **Why re-read before any retry, and confirm labels:** see
`rules/linear-mechanics-notes.md`; a single-select group can swap a label out. **Why
check every image after writing:** the design pass and the writing are separate
steps, and the image is the thing that quietly fails to make it across. **Why
`normalize-github-dependencies`:** it already owns proving a transport before
writing edges. **Why `validate-backlog` after the write:** it validates issues, and
the draft's children are not issues yet.

## 9. Report

**Why startable-today leads:** it is the most useful line — the work someone can
pick up now. **Why a pointer and never a dispatch:** dispatch starts work, which
only the owner's choice of an offered option releases (protected rule 3).

## One ticket

**Why a single-ticket mode (owner's ruling, 2026-11-05):** a deployment's full and
stub formats are needed outside a whole plan — one backend gap, one frontend fix —
and a separate skill per format would restate the format and drift.

## Audit

**Why an audit mode (owner's ruling, 2026-11-05):** most planning problems are
metadata a query could have caught — an issue missing the label that puts it in its
team's view goes unpicked, and the only symptom is silence. It reports first
because each fix is the owner's call, and description edits on others' issues are
not the run's to make. The graph checks are `validate-backlog`'s, not restated.

## Re-scope

**Why never delete and recreate:** an issue's URL is in PRs, comments and the
conductor's ledger; recreating it breaks every one of them.

## Decision scenarios

Pinned in `evals/evals.json`:

- blocking questions together with defer, design one at a time
  (`blocking-questions-together-design-one-at-a-time`);
- a rejection amends the plan in place (`a-rejection-amends-the-plan-in-place`);
- a spec gap hands up (`a-spec-gap-hands-up-to-write-spec`);
- a frontend and backend pair (`a-frontend-backend-pair-shares-the-contract`);
- no engineering work, nothing written
  (`a-product-issue-with-no-engineering-work-gets-nothing`);
- the agent section collapsed per tracker (`the-agent-section-is-collapsed-per-tracker`);
- one sizing authority (`the-self-check-is-the-one-sizing-authority`);
- a backfill is an item, an announcement is not
  (`a-backfill-is-a-child-an-announcement-is-not`);
- the hand-off is a pointer (`the-hand-off-is-a-pointer-not-a-dispatch`);
- re-scope edits in place (`re-scope-edits-in-place`);
- the go approves only text shown in chat (`the-go-approves-only-text-shown-in-chat`);
- the owner's rulings, 2026-11-05: audit mode (`audit-reports-and-changes-nothing-unasked`);
  one ticket (`one-ticket-writes-a-single-child-of-the-asked-kind`); arguments forwarded
  in the pointer (`the-pointer-carries-the-invocation-arguments`);
- the owner's drafts, 2026-11-04: a stub versus a full child
  (`a-stub-states-the-gap-and-designs-nothing`); a stale checkout
  (`a-stale-checkout-is-read-at-the-remote-default-branch`); an already-planned
  parent (`an-already-planned-parent-is-skipped-with-a-reason`); a blocker from a
  principle (`a-blocker-from-a-principle-is-not-set`); priority inversion
  (`no-child-ranks-above-its-own-blocker`); startable today
  (`the-report-leads-with-what-is-startable-today`); a human signature
  (`a-human-signature-label-is-never-applied`); a missing frame
  (`a-child-without-a-frame-says-it-is-not-drawn`); and permission
  (`a-correction-to-someone-elses-issue-is-drafted-not-posted`).
