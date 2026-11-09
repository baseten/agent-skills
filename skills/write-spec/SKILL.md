---
name: write-spec
description: Turn a brief — prose, a Slack thread, a pitch document, a design link or a product issue — into one spec document and return its link. Reads code through subagents that return conclusions only, asks the owner only what changes the spec, shows the full draft, and writes it on the owner's go where the repository's `spec` policy says — by default a markdown file on a branch with a draft PR. Never writes issues; breaking a spec into issues is `plan-feature`'s. Use when asked to write, draft or turn something into a spec, design doc or feature brief.
---

# Write spec

One brief in, one spec document out, its link returned. **It writes the spec and
nothing else** — under the default storage, the branch and draft PR that carry it —
and only on the owner's go. **It never writes an issue**, starts a session or
implements anything: the next step is `plan-feature`, which the owner starts.

This file is the contract. The reasoning lives in `NOTES.md`, keyed by section;
NOTES explains, never overrides.

**First, `references/run-start.md`**: hand off to an installed skill that extends
this one where that rule says to, then open this run's first output with the
version line.

## When this is the wrong tool

- **A spec exists and the work needs issues** — `plan-feature`. Where planning finds
  this spec wrong or short, it hands back here with `back to write-spec: <why>`:
  amend the spec as below, never start a second one.
- **A change one issue can hold** — write the issue.

## Configuration

Read `.claude/agent-policy.json` as `references/agent-policy.md` says, at the start,
from the repository this skill was invoked on. Its key is `spec`, an object whose
fields are each optional; **an invocation argument beats the file**, which is how a
thin skill layered on this one sets them:

- `storage` — where the spec lives:
  - `repo-file` (the default): a markdown file at `location` + `naming`, committed on
    a new branch off the fetched default branch, with a draft PR opened through
    `create-pr`;
  - `tracker-document`: a document in the tracker, on the project `location` names,
    or the project the brief's issue belongs to;
  - `document-store`: a page in the connected document store, under the database
    or parent page `location` names.
- `location` — `docs/specs/` by default for `repo-file`; for the other two, none:
  where neither the file nor the brief gives one, it is a blocking question
  (*2. Ask*).
- `template` — a repository path or URL whose headings replace the default
  template's (*3. Draft*), kept in their order.
- `naming` — the document's name, with `<slug>` and `<date>` (`YYYY-MM-DD`)
  placeholders; by default `<slug>.md` for a file and the spec's title otherwise.

**Storage this session cannot write** — no connector for it, no push access — is
said, and the owner chooses; never fall back to another kind silently.

## Rules

- **Nothing is written before the owner's go on the full text.** The draft is shown
  in this chat; a change after the go is shown and approved again.
- **Code is read through subagents**, never in this thread beyond what a question
  needs (*1. Gather*). **Every claim the spec makes about current code or behaviour
  has a read behind it** (`references/establish-do-not-assume.md`, *You are about
  to assert it*).
- **A decision the brief or the owner already made is a constraint**, recorded with
  where it was made, never reopened or offered alternatives to.
- **Questions follow `references/operator-output.md`, *Questions*,** including its
  planner exception; every reference in chat is a link. This skill writes no
  *Needs you* report: a turn ends with the draft, a question, or the link.
- **Authored writes** — the spec, its commit, the draft PR's body — follow
  `references/authored-write-form.md` and are posted under
  `references/posting-identity.md`.
- **Quote a source only where its exact words are the requirement**; otherwise
  summarise it and link it. Never record the owner's prompts verbatim.

# 1. Gather

Read every input, by kind:

| input | read |
|---|---|
| prose or a pasted thread | as given |
| a tracker issue | its body and comments; its children listed by title only |
| a pitch or other document | in full, through its connector |
| a design link | the frame and a screenshot through the design connector where one is connected; otherwise the link only |
| a PR | its title, body and state |

**An input that cannot be read is recorded with its reason** in the draft's
*Sources* and said once; carry on with the rest.

**Then dispatch one research subagent**, on a cheaper model than this session's,
with this brief, filling only the slots:

```text
Read only. Repository: <owner/name>, checked out at <path>.
The work: <two to four sentences from the inputs>.
Answer with file paths: (1) which modules own the behaviour this touches and what
they do today; (2) what constrains a change there — shared types, tests pinning
behaviour, flags, callers; (3) related earlier work in the history; (4) what does
this work assume that the code contradicts?
Write the detail to <file>. Reply with the file path and at most five lines.
```

Read the five lines, not the file, unless a question needs it. Where the work spans
repositories, one subagent per repository.

# 2. Ask

**Ask only what changes the spec** — never what the inputs or the code already
answer, and never to confirm a decision already made. **Blocking questions** — the
ones the spec cannot be drafted without, such as which users, which surface, or a
storage location — are asked together, once, before drafting, each with a *defer*
option (`references/operator-output.md`, *Questions*). A deferred question goes in
*Open questions*. **Design discussion** — choosing between approaches — is asked one
question at a time, the recommended option first.

# 3. Draft

The default template, in this order. **A section with nothing real to say is left
out; no section has a length cap**:

- **Problem** — who has it, what is wrong or missing, how it shows up.
- **Goal** — what done looks like, in the owner's terms.
- **Non-goals** — what is deliberately out.
- **Success criteria** — observable checks: a behaviour, a metric, a query.
- **Approach** — the chosen approach and why.
- **Considered** — each option rejected, with why not.
- **Constraints** — each marked where it was decided: `(brief)`, `(owner,
  <date>)`, `(code: <path>)`, `(decided in review)`.
- **Open questions** — only those the owner deferred.
- **Sources** — every input as a link, an unread one with its reason.

**Show the whole draft in chat.** On a rejection, **amend that draft in place** —
never regenerate it — and show only the changed sections, under a short `changes:`
list whose last bullet names what was left untouched. A decision in the owner's
reply becomes a constraint marked `(decided in review)`.

# 4. Write

On the owner's go, write exactly the approved text where *Configuration* says:

- **`repo-file`** — fetch the default branch, branch from it (`spec/<slug>` unless
  the repository documents a branch convention), commit
  the file, push, and open a draft PR with `create-pr` at once;
- **`tracker-document`** or **`document-store`** — create the document or page.

**Read it back** before returning; a write that cannot be read back is reported as
unconfirmed. A `back to write-spec` hand-up amends the existing spec — a new commit
on its branch, or an edit to its document — shown and approved as in *3. Draft*.

# 5. Return

```text
Spec: <link>
Next: plan-feature <link>
```

Plus the draft PR's link under `repo-file`, and any input left unread.
