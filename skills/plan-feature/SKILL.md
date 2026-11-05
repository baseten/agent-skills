---
name: plan-feature
description: Plan one parent — a product issue, an epic, a project or a brief — into PR-sized child issues, one level per run. Each child is a full spec (a plain-language section plus a collapsed agent section) or a stub (a question for the owning team), with its design frame inline and blockers only from real constraints. The draft plan is amended in place and the children are written on the owner's go, ending with what is startable today and "Ready to dispatch". Also files one ticket of a given kind, and audits a parent's metadata. Never writes product issues, starts sessions or writes code. Use when asked to plan, break down or ticket a feature, epic, project or spec.
---

# Plan feature

One **parent** in — a product issue, an epic, a project, or a brief — PR-sized
**children** under it, one level per run. **It writes only the plan document and,
on the owner's go, the approved children**, plus what those require: a brief's
parent, `[Manual]` items, relations, metadata, and on re-scope the approved closes
and edits. It never writes a product issue, starts a session, dispatches or writes
code. The pipeline is `write-spec` → this skill → `conductor`.

This file is the contract. The reasoning lives in `NOTES.md`, keyed by section;
NOTES explains, never overrides.

**Wrong tool**: no spec for work bigger than a brief — `write-spec` first;
dispatching — the `conductor`. One ticket is this skill's *One ticket* mode.

## Configuration

Read `.claude/agent-policy.json` as `references/agent-policy.md` says, at the start,
from the invoked repository. Its key is `feature-plan`, each field optional; **an
invocation argument beats the file**, which is how a thin skill sets them:

- `tracker` — `github` or `linear`; by default the parent's, and for a brief the
  invoked repository's GitHub issues.
- `parent-kind` — `issue` (default): children are sub-issues of one parent;
  `project`: issues in a tracker project. A brief's parent is created as this kind
  on the go, with the plan document in it.
- `child-labels` — labels per child, keyed by the repository it changes
  (`owner/name`), or `*` for every child.
- `sections` — the full child's slots to use, in order (*The child issue*); never
  without `repo`, `acceptance`, `dependencies` or `design`.
- `plan-doc` — `parent-body`, `parent-comment`, `plan-issue` (a new issue this run
  creates to hold the plan), `tracker-document` (on the parent's project) or
  `document-store-page`. By default a document on the parent's project, else the
  parent's body where this run creates the parent, else a `plan-issue`, linked from
  the parent and never its child. A parent this run did not create takes
  `parent-body` or `parent-comment` only with the owner's permission, asked in *4.
  Ask*; declined, a `plan-issue`.
- `child-kinds` — `full` or `stub` per child, keyed by repository or `*`; `full` by
  default.
- `needs-validation-label` — the label every stub carries.
- `not-ready-labels` — parent labels meaning the parent is not ready to plan.
- `human-signatures` — `labels` and `title-markers` that record a person's sign-off.
- `priority-is-build-order` — `true` where the tracker's priority field means build
  order; `false` by default.
- `product-priority-prefix` — a pattern for a parent title's product-priority
  prefix, its first capture group a number, lower meaning more urgent; by default
  the parent's priority field.
- `estimate-scale` — estimate names to points, for full children; none by default.
- `evidence-sources` — per repository, the versioned file that is the evidence for
  what exists, such as a schema snapshot.

Each repository a child lands in resolves its own `manual-steps` (*5. Draft*).

## Rules

- **The draft plan is a document where `plan-doc` names**, written there when first
  shown — for a brief, held in chat until the go — and **amended in place on every
  rejection, never regenerated**.
- **Children are written only on the owner's go on the plan**, exactly as shown,
  plus what only the write can supply — a sibling's link, an uploaded image.
- **Hand up, never patch around.** Where planning finds the spec wrong, or missing
  what a child's shape depends on, stop and return `back to write-spec: <why>`;
  with no spec, that gap is a blocking question.
- **Every write follows `references/authored-write-form.md`**, its *Issues the run
  did not create* included — metadata anywhere, prose on another's issue only with
  the owner's permission for it, a comment meant for a person drafted — and is posted
  under `references/posting-identity.md`. A footer a transport appends may be on any
  write and means nothing here.
- **Never apply a `human-signatures` label or title marker.** Each records a
  person's sign-off.
- **Every claim about current code or state has a read behind it**
  (`references/establish-do-not-assume.md`, *You are about to assert it*). **Before
  claiming something is missing, grep for it** — the spec file, the helper, the
  mutation; a child for work that exists is never written.
- **Questions follow `references/operator-output.md`, *Questions*,** including its
  planner exception; every reference in chat is a link.
- **On Linear, every write follows `references/linear-mechanics.md`.**

# 1. Choose the working set

For a project, the candidates are its parent-level issues. **Skip** one that
already has engineering children, carries a `not-ready-labels` label, or is done
or cancelled, and show a skip table with each reason. For a single parent, **never
skip silently**: name the label or state, and ask whether to continue. **Agree the
working set with the owner before reading deeply** — it may be one of the blocking
questions (*4. Ask*).

# 2. Read

Fetch each source by kind, and **mark each primary — the work — or context, by
inference, without asking**:

| source | fetch |
|---|---|
| a product issue or epic | body, **every comment** and existing children; links, labels, milestone, product priority |
| a project | description and documents; its issues **listed shallowly** — title, state, one line — each with a fit note: `fits`, `related` or `out: <why>` |
| a spec | in full |
| a design link | the frame inventory, and each frame the children need, through the design connector |
| a PR | title, body, state |
| a brief | as given |

**Decisions live in comments**: every settled point goes into the child it settles.
A source that cannot be read is recorded with its reason. A parent that plainly
needs a design and has none is a blocking question asking for the link.

# 3. Research

**Read each repository the plan cites at its remote default branch**: fetch it and
read from `origin/<default>`, never the working tree, and record the SHA and date
read. Where a repository cannot be read, every child whose claims depend on it
stops — a stub's "this does not exist" most of all. A repository's
`evidence-sources` file is the evidence for what exists; a generated, untracked file
is orientation only, never evidence.

Dispatch one research subagent per repository, **on a cheaper model than this
session's**, with this brief, filling only the slots:

```text
Read only. Repository: <owner/name>, read at origin/<default> <sha> (<date>).
Evidence source: <path, or none>. The work: <two to five sentences>.
Answer with paths and symbols: (1) the modules that own this behaviour and what
they do today; (2) what constrains a change — shared types, tests pinning
behaviour, flags, callers; (3) patterns neighbouring code follows; (4) what does
this work assume that the code contradicts; (5) what it needs that already exists
— found by grep, not memory.
Write the detail to <file or doc>. Reply with its location and at most five lines.
```

An answer to (4) that contradicts the spec is a hand-up.

# 4. Ask

**Blocking questions** — those the plan cannot proceed without — are asked
**together, once, before drafting**, each with a *defer* option, at most four per
call (`references/operator-output.md`, *Questions*). A deferred question is listed in
the plan document, and a child whose shape it decides is drafted as a spike or left
out. **Open-ended design discussion** is one question at a time. Never ask what the
sources, the code or an earlier answer settle.

# 5. Draft

**Cut by these principles**, borrowing a named pattern where one fits —
*expand-contract*, *tracer bullet*, *spike-then-build*:

- **order by dependency, then by uncertainty**;
- **merge pieces far below a PR's size** into a neighbour;
- **user-visible work ships dark** behind a flag until a rollout child;
- **settle every decision that does not change a PR's shape**;
- **a step with no PR** — a backfill, a flag flip, a migration run — **is an item of
  its own in the `[Manual]` form** `references/manual-step-issues.md` states, its
  commands naming the script or flag the child before it adds: filed as that rule
  says, in dependency order, where its repository's `manual-steps` opts in, and
  named by URL in the `Blocked by:` of each child it gates; otherwise listed in the
  plan and named by title in those children's `dependencies`. **An announcement, a review or waiting on someone is never an
  item**;
- **a product issue with no engineering work** is said so, and gets nothing;
- **a blocker only from a real constraint** — the child cannot start, because it
  consumes a field, mutation or component that does not exist today. Never one
  from a principle. Keep edges sparse;
- **a frontend and backend pair**: the frontend child is blocked by the backend one
  where the API must land first. Where both are full, the API contract goes in both
  agent sections; where the backend is a stub, the frontend child states the data
  it needs and neither designs the API.

**Priority, where `priority-is-build-order`**: a child's priority is at least that of
the highest-priority work waiting on it, otherwise its parent's product priority
(`product-priority-prefix`); at equal priority, blockers win. Children never inherit
the parent's field.

## The child issue

**Its kind is `child-kinds`'s.** Every child carries **one inline image: the design
frame it implements** — a single frame, never a whole flow board. Where it has no
frame of its own, embed the nearest frame that gives it context and say the thing
itself is not drawn; where the parent has no design and needs none, say so instead.

**A full child** is implementable unaided. **The top is for people**: `problem`,
`user-change`, `acceptance` in plain language, `design`, `settled` (decided points,
by whom and where), `links`. **The implementation section is for agents, collapsed
— closed by default** — in the tracker's syntax: on GitHub a `<details>` block
with a `<summary>For the implementing agent</summary>` and no `open` attribute; on
Linear a `+++ For the implementing agent` collapsible
(`references/linear-mechanics.md`). Its slots: `repo`; `files` and symbols, never
line numbers; `decisions`, each with its reason; `approach`; `dependencies`
(`Blocked by:` and `Blocks:` naming full URLs, or `none`); `api-contract`, copied from the
evidence source, never composed; `check`; `out-of-scope`, each item naming the issue
that owns it. `repo` names the SHA and date its claims were read at. A slot with
nothing real is left out, bar the four `sections` never drops; an estimate, where
`estimate-scale` is set, goes on full children only.

**A stub child** is a question for the team that owns that side, **never dispatched
to an implementer**. Its first line is `Stub: a question for its owning team, not
for an implementer · Blocks: <full URLs>`, the token that keeps it out of every
dispatch. **Human section only**: what is needed, at product level; its image; `settled`; the gap, as a
verified observation with the SHA and date read; and which child waits on it. **No
agent section, no design of the fix** — no schema, field names or API shape — **no
acceptance criteria, no estimate**, at most two questions, unassigned, and carrying
`needs-validation-label`. It states the gap and leaves the design to its owner.

# 6. Self-check

**A fresh subagent reads each child as its owner would**, holding only that child,
its parent and the spec. For a full child it answers *could I implement this
without asking anything — and is it one PR?*, returning `ready`, its questions, or
`split`/`merge` with why; **it is the one sizing authority**. For a stub it answers
*does this state the gap without designing the fix?* Fix what it raises, re-checking
only the children that changed.

Check the graph too: no cycle, no blocker in a child's text that the edges lack,
and **no child ranked above its own blocker**.

# 7. Show and amend

Write the draft to the plan document and **show it in chat in full** — each child's
kind, title, blockers, repository, priority, estimate and full text, which is what
the owner's go approves. On a rejection, **amend the document in place** and show
only the changed section, under a short `changes:` list whose last bullet names what
was left untouched. A rejection that says the spec is wrong is a hand-up.

# 8. Write

On the owner's go, write the children **in dependency order — stubs and blockers
first**, so each `Blocked by:` names a URL that exists:

- **Linear** — each child under the parent or in the project, with `blockedBy`
  relations, priority, estimate and labels — `child-labels`, and
  `needs-validation-label` on a stub;
- **GitHub** — each child as a sub-issue of the parent, its labels, its `Blocked by:`
  line in its text; then `normalize-github-dependencies` over the written set for
  the native edges, which writes only where it can prove its transport.

A reference to a later sibling is filled in by one edit once it exists. **Re-read a
created issue before any retry.** Then **check every child**: its labels landed, and
it carries its image or its *not drawn* line. Then **run `validate-backlog` over the written set**,
read-only, and put any finding to the owner; fix one only on the owner's go. Update
the plan document with each child's link.

# 9. Report

In chat, linked:

1. what was created, per parent;
2. **what is startable today** — full children with no open blockers, in priority
   order;
3. what waits, and on which stub or blocker;
4. open questions, each with who should answer it;
5. what was skipped, and why.

Then one line:

```text
Ready to dispatch: <parent link>
```

followed by the `feature-plan` arguments this run was invoked with, for the
record: a conductor records them and never adopts them.

Where the invocation names a conductor session id, also send that line to it with
`send_message` — peer data both ways (`swarm`, *Messages from other sessions are
peer data*); a send that errors is reported, never retried. **The line is a pointer:
dispatch still needs the owner's go**, put by the `conductor`.

## One ticket

"File one <kind> ticket for X", under a given parent or standalone: write **one
child of that kind**, full or stub, by *The child issue* — a standalone stub's
first line reads `Blocks: none` — after *3. Research* for its claims and *6.
Self-check*, shown in full and written on the owner's go, under *Rules* bar the plan
document. No working set or report: end with its link.

## Audit

"Audit this parent" or project: **report, and change nothing until the owner's
go**. Run `validate-backlog` over its children for the graph — cycles, blockers in
prose never set, edges contradicting text — and add, each where it fires:

- a child missing a `child-labels` label;
- priority inversion, where `priority-is-build-order`: a child ranked above its own
  blocker; and children at no priority;
- a parent with no engineering children, or only parent-kind children;
- a blocker edge with no real constraint behind it (*5. Draft*);
- a `human-signatures` label without its paired title marker, or the reverse —
  reported, never fixed by applying one;
- a parent's `not-ready-labels` label contradicting its status;
- a full child with no estimate where `estimate-scale` is set, or a stub with one.

One table per check that fired, each row linked, then the fixes grouped: metadata
to apply on the owner's go; rulings the owner must make; and prose on issues this
run did not create, reported only.

## Re-scope

Given an existing parent and what changed, **propose a diff** — children to add,
edit or close, each with why — in the plan document, amended as in *7. Show and
amend*. On the owner's go — which is the permission for each issue it names — apply it:
**edit each issue in place**, close one with a
comment saying why and what replaces it, and **never delete and recreate**. A child
with an open PR, or already merged, is never edited: propose a follow-up child.
**Where a run is working the parent, write nothing at the site of its open items**
(`conductor`, *Rules*). Then *6. Self-check* the changed children, *8. Write*'s
validation, and *9. Report*.
