# backlog-orchestrator — resolving cross-branch artifact collisions

Part of `backlog-orchestrator`'s contract. `SKILL.md`, *Cross-branch artifact collisions*, keeps detection — the comparison against every open branch, the three kinds, and the integrated-branch report — because every wave with a PR runs it. It points here on finding a collision of any kind, before dispatch wherever more than one open branch targeting a base may generate a migration (*Implementation worker contract*, step 10), and before a renumber (*Frontier advance on merge*, step 2). Its rules assume `SKILL.md` has been read, and `SKILL.md` assumes them wherever it points here. The reasoning is in `NOTES.md`, under *Cross-branch artifact collisions* and *Performing the renumber*.

## Resolving a collision

For the first two kinds, correct resolution depends on merge order:

- **where the colliding artifacts are shown independent** — sequence-numbered migrations whose bodies touch different tables and objects, with no foreign key, view, trigger, shared type or backfill reaching into the other's change — **do not ask** (the owner's ruling, NOTES). Read that off both bodies; interaction not ruled out is interaction, and the identity files the generator rewrites during a renumber (a journal, a snapshot) are not evidence either way. Any order works, so they merge in `plan-merge-order`'s ranking, each later one renumbered after the one before it lands (*Performing the renumber*), and the report names the order taken;
- **where they interact** — the same table or object, one depending on the other's change, or any shared-artifact edit that is not a sequence number — the order decides the outcome and this skill does not own it: surface the collision as `NEEDS_USER` with both PR URLs and the colliding paths. Never renumber or rewrite the artifact pre-emptively.

**The third kind does not take that remedy, because no merge order resolves it** — whichever side merges first, the final tree is the same and broken. One branch has to change: either the rename follows through into the other branch's new references, or the new code is written against the new name. Surface it as `NEEDS_USER` naming both PRs, the symbol, and the fact that **no merge order resolves it** — and where the owner picks a side, the repair is an ordinary `finding` repair on that PR, after which **the integration check is re-run**, since a repair that misses one reference produces the same clean diffs as before.

## Expecting a collision at dispatch

**Expect a sequence-number collision at dispatch rather than discover it at merge.** Where more than one open branch targeting a base may generate a migration — an issue this wave dispatches that names a table, column, index or migration, or another track's branch that already carries an added migration, since the comparison set is every open branch — each branches from the same base, runs the generator, and takes the same next free number, and each passes CI, a migration-consistency check included. Tell each such worker, in its dispatch prompt (`SKILL.md`, *Implementation worker contract*, Before dispatch, step 10), that siblings exist and that its number is provisional, so no PR body presents it as final, and record the expected renumbers against the merge order when the PRs exist.

## Performing the renumber

**Generate and verify it as `references/mechanical-pushes.md` requires for a renumbered artifact** — the repository's own generator, never a hand edit of identity fields, and a proof that it applies.

**A renumber is a mutation like a restack**: never start one on a branch whose `supervise-prs` record shows a mutator — wait for that pass to return — and hold the branch locked while it runs.

**Where the artifacts chain, the renumbers are strictly sequential.** A snapshot that records its predecessor's id cannot be renamed into place: the second PR's snapshot is regenerated against a schema including the first PR's change, the third against both. So one renumber per merge, each after the previous one lands and each followed by CI — never all at once against the same base.

**Where the artifact carries a hand-written body review read — a migration's SQL — regenerate the identity and keep that body verbatim**: a regenerated body need not reproduce it (an expression index or a partial `WHERE` can come back different). The pass regenerates the snapshot, the journal entry and the number, and carries the reviewed body across unchanged. Check that the body differs from the reviewed one only in its number and filename and that the new snapshot's predecessor id is the id of the base's latest snapshot; whether the push then needs another review round is `references/mechanical-pushes.md`'s call.

For an artifact with a reviewed hand-written body, carrying it across is the splice, done every time rather than only where the generator falls short; re-verify after it, because a carry that was skipped or partial leaves a regenerated body that silently dropped a backfill.

Until the apply verification passes, the renumber is not finished, and it is not mechanical — see `references/mechanical-pushes.md`, which grants the skip-re-review exemption only to a renumber that has cleared this.
