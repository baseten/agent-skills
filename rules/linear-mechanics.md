# Linear mechanics

This is the rule other skills mean when they cite *Linear mechanics*: how a write to,
or a read from, Linear through its API or MCP actually behaves, where that differs from what the
tool's parameters suggest.

**It is not a skill and nobody invokes it.** It is a shared rule, held once at
`rules/linear-mechanics.md` and copied into each skill that applies it by
`scripts/refresh_shared_rules.sh`. A skill reads its own
`references/linear-mechanics.md`, which works after `bootstrap.sh` has
installed only that skill's directory, and travels with the skill if it is
moved into a plugin. Edit the source, never a copy; check_shared_rules.py fails if a generated copy diverges.

## Markdown, not HTML

**Linear takes Markdown and no HTML.** A `<details>` block does not collapse: its
tags render as literal text. **A collapsible is `+++`, a space and its title, the
content, then `+++` on its own line**:

```text
+++ For the implementing agent

…content, fenced code blocks included…

+++
```

It renders closed. Linear appends the closing fence itself where it is missing and
re-serialises the block in that form — reading back that form is how a write is
known to have parsed rather than passed through as text.

**A bare issue identifier is rewritten into an issue chip** on save, so a later
patch anchored on that text fails to match: write every issue reference as a
Markdown link from the start.

## Editing

- **Patch a description that carries an uploaded image, never resend it whole**: a
  full rewrite breaks the signed image URLs embedded in it. Strike through plain text only: strikethrough breaks
  across inline code.
- **`addLabels` appends; `labels` replaces the whole set.** Adding a label with
  `labels` silently strips the rest.
- **A label in a single-select group displaces the group's other label** rather
  than stacking. Read the workspace's label groups before assuming which labels
  stack.
- **Saves are eventually consistent.** A save's response can echo a stale
  description, so a save can look like a no-op when it landed. **Re-read the issue
  before any retry**: a blind retry double-inserts the body.

## Images

**Embed inline; never only attach** — attachments sit in a rail and go unopened.
Upload with `prepare_attachment_upload`, then `PUT` the bytes with every signed
header it returned, verbatim, inside its window, then embed the **unsigned** asset
URL: Linear re-signs on every read, so the unsigned URL is the durable one and a
signed URL in a description expires.

## Reading

- **A completed blocker still counts as a blocker** in Linear's relation filters, so
  a blocked list can be stale rather than wrong. "Blocked issues" filters issues
  that are blocked; "Blocking issues", issues that block others.
- **An identifier with a `P-` prefix is a project**, not an issue.
- **A windowed query paginates**: where a result contradicts what you believe, check
  whether the item paginated out before asserting it.
- **There is no tool to delete a document**: say it must be deleted in the UI.

## Review pages

**Where a repository is linked to Linear, a PR has a review page there**, its diff
view. `get_diff`, given the PR's forge URL, returns it as `appUrl`, and the issues
the PR closes as `linkedIssues`; where that is empty, an issue identifier in the
PR's title is the fallback. **A PR `get_diff` cannot find has no review page
there**: the call errors with "Diff not found". **`get_diff_threads` returns the
calling account's unsubmitted review drafts as `drafts`**, not every reviewer's: a
draft there is in Linear, not on the forge, until it is submitted. One `get_diff`
and one `get_diff_threads` per PR.
