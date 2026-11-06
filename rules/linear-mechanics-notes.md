# Notes — linear-mechanics

Reasoning behind `rules/linear-mechanics.md`. NOTES explains; it never overrides.

**Where it came from (owner's ruling, 2026-11-04):** the owner's own Linear planning
skills, drafted from real runs, kept a reference of what went wrong writing to
Linear, "hard-won, all of it from things that went wrong". It is a shared rule
rather than a skill's side file because both `plan-feature` and `conductor` write
to Linear — a plan's children, and a ledger kept as a tracker document — and a copy
in each would drift. Workspace-specific label groups are left out: which groups are
single-select is read from the workspace, never from this file.

**The collapsible, verified (2026-10-14):** the owner wrote a `+++ Title` … `+++`
block to a live issue and read it back. It rendered closed, and
Linear had re-serialised it with its own closing fence — the sign it parsed. A
`<details>` block on the same surface rendered its tags as text. This settles what
`plan-feature`'s first draft recorded as not established.

**Why re-read before a retry:** a save that echoed a stale description looked like
a silent failure, the retry landed, and the issue held the body twice — harder to
remove than it was to add.

**Why patch rather than rewrite:** a description with an uploaded image carries
that image's URL, and a full rewrite breaks it; a patch leaves it alone.

**Why `P-` identifiers are projects:** Linear's own MCP `get_issue` description says
so, giving a `P-` example.

**Why links rather than bare identifiers:** Linear rewrote a bare identifier into a
chip, and the next patch, anchored on the original text, matched nothing.

**Review pages, read (2026-11-06):** `list_diffs`, `get_diff` and `get_diff_threads`
were run against a live linked repository. `get_diff`, given the PR's forge URL,
returned `url` (the forge PR), `appUrl` (the review page) and `linkedIssues`; for a
PR in a repository not linked to Linear it errored with "Diff not found".
`get_diff_threads` returned `threads` and `drafts`, its description scoping `drafts`
to the authenticated user. `plan-feature` bundles this rule and carries the section
without reading it; that cost was accepted over a second copy in the conductor. The
`conductor`'s work queue reads them (its NOTES, *The work queue*), because a review
draft left in Linear is invisible from the forge, and an item linking only the
forge PR told the owner nothing was waiting there.
