# Notes — mechanical-pushes

Reasoning for `rules/mechanical-pushes.md`. Deliberately *not* bundled into
each skill: a copy of this per consumer would be design history with no reader,
and the audience for it is a person editing the rule, who has this checkout.

Moved here with the rule itself, from `create-pr/NOTES.md`, *Substantive vs mechanical pushes*, when the rule was split out of `create-pr` (#140).

**Why this is a shared rule (#140):** the test decides whether a push re-triggers review, and five skills act on it — `create-pr` for the trigger it owns, `backlog-orchestrator` and `implement-issue` for the re-triggers after a repair or restack, `npm-dependency-upgrade-orchestrator` for whether a clean round still counts for a later head, and `review-docs`, which never re-reviews a mechanical push. `review-docs` is invoked by `create-pr`, so its pointer into `create-pr` for the test ran upward, into a caller; the orchestrators' pointers ran into a skill they compose but whose other sections they do not need.

The re-trigger split exists because restacks and renumbers happen for reasons unrelated to a PR's own diff — most often right after a sibling merges — and re-reviewing every one spends review budget on code that did not change. The hazard is that a *botched* renumber is indistinguishable in the diff from a correct one while changing whether the artifact runs at all: a migration whose identity fields went stale in a hand-rename is **silently skipped** — it compiles, CI is green, and the schema change never happens. That is why "passes the checks" means **verified to apply** (regenerate through the repository's own generator, then exercise the artifact's apply path), why an unverified renumber is substantive, and why a repository with no deterministic check that would catch a bad renumber gets no mechanical exemption at all.

The split governs what the workflow itself triggers, not what the review provider does on its own events (e.g. re-reviewing when a draft is marked ready) — provider behavior is neither a reason to suppress a due trigger nor to issue one that is not due.
