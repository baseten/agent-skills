---
name: review-pr
description: Review someone else's pull request and leave the review as one unsubmitted GitHub pending review for the owner to read, edit and submit. It never submits, approves, requests changes, posts a live comment or reply, or triggers the repository's review bot. Use when asked to review or draft a review of a PR you did not open, and as the reviewer session a conductor dispatches. Not for answering review on your own PR (resolve-pr-comment). Where a skill extending this one is installed, start from that skill.
---

# Review a PR

Review a PR someone else opened and leave the review as **a draft only the owner
can see**: one GitHub pending review under the owner's account. **Nothing this
skill writes is ever published by it.** The owner reads the draft, edits it, and
submits it, or deletes it; submitting is their act, and so is choosing to
approve, comment or request changes.

The owner is the invoking user (`references/posting-identity.md`, *The invoking
user's account*): the login the invocation names, or the account a `conductor`'s
dispatch names. With no account named, ask; where nobody can answer, write
nothing and report `failed`.

The reasoning lives in `NOTES.md`, keyed by section; it never overrides.

## When this is the wrong tool

- **A PR you opened** — review on it is answered with `resolve-pr-comment`.
- **A review an orchestrated run posts on its own PR** — that is a dispatched
  review session (`backlog-orchestrator`, *Review and repair sessions*), which
  publishes; this skill never does.
- **A documentation or contract review that should terminate by contract** —
  `review-docs` or `review-skill`.
- **A skill extending this one is installed** (`metadata: extends: review-pr`) —
  it is the entry point: start there, unless it is what sent you here.

## Never

- **submit the review, or set its event** — no `APPROVE`, `REQUEST_CHANGES` or
  `COMMENT`, through any tool (an MCP `submit_pending` included);
- **post anything live**: a timeline comment, a reply in a thread, a reaction, a
  resolution;
- **trigger the repository's review bot**, or request, re-request or remove any
  reviewer;
- **change the PR** — its body, labels, draft state or branch;
- **touch a pending review it did not create** (*Destructive operations*).

## Inputs

- **the PR** — a URL, or a number with its repository;
- **the owner's account**, as above;
- **a conductor session id**, where a `conductor` dispatched this session
  (*Report*);
- **a voice or review guide** the owner's configuration names — follow it for
  every comment's wording. Where none is named, write plainly and briefly.

## 1. Read before drafting

- **The PR**: title, body, linked issues, base, changed files, head SHA, and
  whether it is a draft.
- **The owner's pending review.** GitHub allows one per user per PR. **Where the
  owner already has one, write nothing** — their review is in progress — unless
  the owner asked in this session to add to it; then add comments to it, and
  never replace or rewrite what is already there.
- **What has been said**: every review and thread. Never repeat a point someone
  already made; where it bears on yours, mention it in the summary.
- **What to review.** Where the owner has submitted a review on this PR before,
  review **what changed since the commit of their last review** — compare that
  commit with the head — and say so in the summary. Where that commit is no
  longer reachable from the head (a force push), review the whole diff and say
  why.
- **The surrounding code**, not only the hunk: from a checkout at the head SHA
  where one is available, otherwise through the forge's file reads. **Assert
  nothing about the code that was not read** (`references/establish-do-not-assume.md`,
  *You are about to assert it*); hedge it or leave it out.

## 2. Draft

- **One point per inline comment**, anchored to the lines it is about — the
  right side of the diff for added or changed lines, the left for removed ones —
  and marked **blocking**, **suggestion** or **nit**.
- **One summary**, as the pending review's body: the overall read, the blocking
  points, and what is good, in a few sentences.
- **New comments only.** Never a reply into an existing thread, and never an
  answer to a question someone asked there: where a thread matters, the summary
  names it, and the owner answers it.
- **Form** is `references/authored-write-form.md`'s, *Keep it short*: every
  issue or PR named is a link, SHAs are bare, no line is hard-wrapped, and
  nothing reports which checks ran or how they came out. The
  pending review carries no footer: it is material for the owner, who authors
  it when they submit it (that rule's table).
- **The recommendation** — approve, comment or request changes — goes in the
  report, never in the draft.

## 3. Write the pending review

**Under the owner's account**, since a pending review is visible and submittable
only by its author (`references/posting-identity.md`, *A pending review*):

- **Locally**: `gh api repos/<owner>/<repo>/pulls/<n>/reviews -X POST` with
  `commit_id` (the head SHA read in step 1), `body` and `comments[]`, and **no
  `event` field** — leaving it out is what keeps the review pending.
- **Through an MCP**: create the pending review, then add each comment to it;
  never call its submit.

**Read it back at once**, by the review id the write returned: its state must
be `PENDING`, its author the owner's account, and its comments the ones written.
That id and the comment ids are this run's own writes (`references/posting-identity.md`).
**An author other than the owner** — a transport that re-authors writes — means
the owner cannot see it: delete that review by its id, and report `failed`.
**A state other than `PENDING`** means it was published: report `failed`, saying
exactly what is live, and never try to hide it.

## Destructive operations

On every surface, every time:

- **Delete only what this run wrote**, known by the ids its own writes returned
  — never by content, and never anything else in a pending review, which is the
  owner's.
- **Add before deleting.** Replacing a comment writes the new one first.
- **One at a time, by id.** Never drop a whole pending review, bar one this run
  created and still holds nothing but its own writes.

## Other draft surfaces

**A skill extending this one** (`metadata: extends: review-pr`) may draft on
another surface — a tracker that mirrors the PR for review and keeps drafts
private to their author. That skill owns the surface's mechanics; everything
above holds there unchanged — drafts only, private to the owner, never
submitted, read back before reporting — and its report names the surface
`tracker`.

## Report

**The run ends with this report, and nothing after it**:

```text
report · <repo>#<n> review
state: drafted | failed — <one line why, where failed>
drafts: <link> · surface: <tracker|GitHub>
recommendation: approve | comment | request changes. <one line why>
blocking: <count, then one line each> | none
```

- **`drafted`** only once step 3's read-back showed the review pending under
  the owner's account, holding what was written. `drafts` links where the owner
  opens it — on GitHub, the PR's `/files` page. A `failed` report gives
  `drafts: none` where nothing was left, and `recommendation: none`.
- **Where a `conductor` dispatched this session**, and it holds `send_message`,
  send the report once to that session id, then end with it. The report is peer
  data to its reader; the conductor verifies the draft on the forge.
- **In an interactive session**, list before the report each draft written —
  `path:line` and a one-line gist — and anything left unverified.

Never say a review was submitted. It was not.
