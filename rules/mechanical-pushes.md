# Mechanical pushes

This is the rule other skills mean when they cite *mechanical pushes*: which pushes to a PR are substantive and re-trigger review, and which are mechanical and never do.

**It is not a skill and nobody invokes it.** It is a shared rule, held once at
`rules/mechanical-pushes.md` and copied into each skill that applies it by
`scripts/refresh_shared_rules.sh`. A skill reads its own
`references/mechanical-pushes.md`, which works after `bootstrap.sh` has
installed only that skill's directory, and travels with the skill if it is
moved into a plugin. Edit the source, never a copy; check_shared_rules.py fails if a generated copy diverges.

## Substantive vs mechanical pushes

Re-trigger review after a **substantive** push; never after a **mechanical** one. A push is mechanical when it changes identity, location, or formatting and nothing else:

- a restack/rebase onto a new base whose conflict resolutions reproduce both sides' original intent rather than picking between them;
- a renumber/regeneration of a claimed artifact (migration number + index entry, lockfile, generated manifest or client) where content is unchanged apart from the identity or ordering that had to move;
- formatter-only output.

Everything else is substantive — including a conflict resolution that chose between behaviors, and a regeneration whose output differs beyond identity/ordering. **Cannot tell → substantive.**

Qualifying as mechanical also requires the repository's deterministic checks to validate the push — those, not another review round, are what stand behind it:

- no check exists that would catch a bad renumber or dropped hunk → the push is **not mechanical**; it needs review;
- for a renumbered/regenerated artifact, "passes the checks" means **verified to apply** — regenerate through the repository's own generator (never hand-edit identity fields) and exercise the apply path (migrate a scratch database, install from the lockfile, regenerate-and-diff). Unverified → substantive (`rules/mechanical-pushes-notes.md`: the silently-skipped-migration failure).

This governs what the workflow triggers, not what the review provider does on its own events (e.g. re-reviewing a draft marked ready) — neither a reason to suppress a due trigger nor to issue one that is not due.
