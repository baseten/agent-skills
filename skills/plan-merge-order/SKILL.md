---
name: plan-merge-order
description: Rank the open PRs of a settled implementation tranche by how much downstream work each one unblocks, and emit a review order, a merge batching plan, and the hard sequencing constraints as a table. Use when a tranche is settled — no further work can start until existing PRs merge — or whenever asked what to review or merge first to unblock a backlog.
---

# Plan Merge Order

Turn a set of open, finished PRs into an explicit answer to "what do I review first, and what do I merge first, to unblock the most work?"

This file is the contract; the reasoning behind its rules lives in `NOTES.md` beside it, keyed by section. NOTES explains; it never overrides.

This skill is **read-only advice**. It never merges, never reviews, never edits a PR or an issue, and never grants merge authority. `merge-stack` owns merging; the user owns the decision.

It is tracker-agnostic (GitHub Issues, Linear, or another supported tracker) and technology-agnostic. Preserve canonical full issue and PR URLs in all output.

## When to run

Run when a tranche is **settled**: every remaining unstarted issue is blocked by work that is implemented but not merged, and the open PRs are individually finished. `backlog-orchestrator` invokes this at that point. A user may also invoke it directly at any time — answer with whatever state exists rather than refusing because the tranche is not formally settled (NOTES).

NOT a merge readiness gate: top of this ranking says nothing about whether a PR is correct.

## Inputs

Accept:

- a manifest/parent/build-order issue URL, an explicit issue set, or an explicit PR set;
- the repositories in scope;
- optionally, the run's own PR/branch/stack state when a caller already holds it;
- optionally, `MERGE_RISK` and `DECISION` action points from `summarize-tranche`.

Supplied action points are **hard constraints on the ordering**, not commentary: a `MERGE_RISK` is stated in its PR's row; a PR gated by a `DECISION` is never batched ahead of the decision it waits on; one an action point makes unmergeable as it stands is said to be so in the table, never ranked as ready.

When given a manifest, derive the PR set from it. Work the caller did not open is context, not a candidate.

## Hard constraints

- Never merge, never enable auto-merge, never mark a PR ready, never change a base branch.
- Never report a ranking as approval, and never imply the top PR is safe to merge.
- Never silently drop a candidate PR. A PR that unblocks nothing still appears, with a count of zero.
- Distinguish evidence from inference everywhere: a dependency read from the tracker's native relationships and one inferred from issue prose are not interchangeable.

# Method

## 1. Collect the PR set and stack topology

For each candidate PR record: URL, canonical issue URL, head branch/SHA, base branch, draft state, CI state, review state (triggered / complete / findings outstanding), and mergeability.

Derive stack edges the way `merge-stack` does: parent → child when the child's base branch equals **another candidate PR's head branch**. Use a `Depends on:` line to locate candidates and to cross-check, never as the edge itself.

A non-default base alone does not make a PR a stack child — it may target a long-lived integration or release branch that is no candidate's head (NOTES). Where a real parent exists, it merges first regardless of leverage.

## 2. Map PRs to issues

Resolve each PR to the canonical issue it completes, using the tracker's own linkage (a closing reference, a linked issue, a tracker field), never title matching. A PR with no resolvable issue is reported separately and excluded from leverage arithmetic — it cannot unblock a dependency edge that does not exist.

## 3. Build the remaining-work graph

Let `U` be the in-scope issues still open and not yet implemented, plus the issues of the open PRs.

For each issue in `U`, collect its blockers, in this order of confidence:

1. the tracker's **native** dependency relationships (GitHub `blocked by`/`blocking`, Linear relations);
2. blockers **stated in the issue text** ("Depends on:", "Blocked by:", explicit prose);
3. blockers **implied by scope** — the issue's own description names a capability another in-scope issue delivers.

Record the confidence level per edge. An empty native blocker list is not evidence of an unblocked issue — check the text before concluding it (NOTES: native edges are frequently incomplete, cross-repository ones especially).

Mark an edge `inferred` when it came from source 2 or 3, and list every inferred edge the ranking depends on so the user can overrule it.

## 4. Compute leverage per PR

For a candidate PR `p` completing issue `i`, compute and report two distinct numbers:

- **Unblocks now** — issues in `U` whose *only* remaining unmet blocker is `i`; startable the moment `p` merges.
- **Gated behind** — the transitive closure of issues in `U` that cannot start until `i` merges, whether or not other blockers also stand in the way.

They diverge in the case that matters most: a PR can unblock nothing on its own and still gate a large subtree (NOTES).

## 5. Find all-or-nothing sets

Group the issues in `U` by their set of unmet blockers restricted to in-flight issues. Any group whose blocker set has more than one member is an **all-or-nothing set for the issues in that group**: until every member merges, none of those issues becomes startable. State these sets explicitly.

Scope the claim to the group and no further: a member can still unblock other issues that do not need the whole set — if X needs `{A, B}` and Y needs only `A`, merging `A` starts Y. Before describing a partial merge as buying nothing, check the rest of `U` and report whatever leverage it does have.

## 6. Find hard sequencing constraints

Independent of leverage, identify constraints that force an order:

- **Stack ancestry** — a child PR cannot merge before its parent.
- **Claimed artifacts** — two branches that each add or amend an artifact whose identity or ordering is claimed rather than derived (a numbered migration, a generated manifest, a lockfile, a registry or index). Name the colliding paths, both PR URLs, and what must be renumbered or regenerated once the order is fixed (NOTES: these collide only on the second merge).
- **Anything the orchestrator surfaced as `NEEDS_USER`** on a candidate PR.

A hard constraint outranks every leverage number. Say so where it applies, never buried in a note.

## 7. Rank

Order candidates by:

1. hard sequencing constraints;
2. within a stack, always bottom-up;
3. higher **unblocks now**;
4. higher **gated behind**;
5. smaller/simpler diff, so a review cycle returns sooner.

Then separate the two questions the user is actually asking:

- **Review order** — which PR deserves a human's attention first. Free of stack ordering: a child can be reviewed before its parent even though it cannot merge first.
- **Merge order** — constrained by ancestry and hard constraints.

For merge batching, prefer completing a chain over stopping partway — but never claim that completing it avoids restacking: `merge-stack` fully restacks the remaining descendant subtree after every node, so an N-PR chain performs those rewrites however it is batched. What one sitting saves is work **outside** the chain (NOTES). Estimate turnaround from the per-node rewrite-and-recheck cost, not the batch count.

Recommend holding a chain's tail only for a review reason, never to sequence it.

# Output

Lead with the table. One row per candidate PR, most valuable first:

```text
| PR | Issue | Chain | Review | CI | Unblocks now | Gated behind | Note |
```

`Chain` is the stack position (`root`, `2/3`, `standalone`). `Note` carries the hard constraint or all-or-nothing membership when one applies.

Follow the table with, and only with, the sections that have content:

- **Recommended review order** — the ranked list, one line of justification each.
- **Recommended merge batches** — grouped, in order, with the restack work each batch triggers.
- **All-or-nothing sets** — each set, and what it unlocks once complete.
- **Hard constraints** — each forced ordering and the remediation it requires.
- **Inferred edges** — every edge the ranking depends on that is not native tracker data, so the user can overrule it.
- **Unblocks nothing** — candidates with zero downstream, merge whenever.

Close with the single highest-leverage action in one sentence.

## Honesty rules

- If the tracker exposes no dependency data at all and every edge is inferred from prose, say that before the table, not after it.
- If a candidate's leverage rests on one inferred edge, mark the row.
- Never invent a downstream issue to make a ranking look decisive. Zero is a legitimate answer and a useful one.
- Never restate the ranking as a recommendation to merge now. The output is an ordering, not a go-ahead.
