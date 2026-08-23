---
name: plan-merge-order
description: Rank the open PRs of a settled implementation tranche by how much downstream work each one unblocks, and emit a review order, a merge batching plan, and the hard sequencing constraints as a table. Use when a tranche is settled — no further work can start until existing PRs merge — or whenever asked what to review or merge first to unblock a backlog.
---

# Plan Merge Order

Turn a set of open, finished PRs into an explicit answer to "what do I review first, and what do I merge first, to unblock the most work?"

This skill is **read-only advice**. It never merges, never reviews, never edits a PR or an issue, and never grants merge authority. `merge-stack` owns merging; the user owns the decision.

It is tracker-agnostic (GitHub Issues, Linear, or another supported tracker) and technology-agnostic. Preserve canonical full issue and PR URLs in all output.

## When to run

Run when a tranche is **settled**: every remaining unstarted issue is blocked by work that is implemented but not merged, so no further implementation can begin, and the open PRs are individually finished. `backlog-orchestrator` invokes this at that point. A user may also invoke it directly at any time — answer with whatever state exists rather than refusing because the tranche is not formally settled.

Do not run it as a merge readiness gate. A PR being top of this ranking says nothing about whether it is correct.

## Inputs

Accept:

- a manifest/parent/build-order issue URL, an explicit issue set, or an explicit PR set;
- the repositories in scope;
- optionally, the run's own PR/branch/stack state when a caller already holds it.

When given a manifest, derive the PR set from it rather than listing every open PR in the repository. Work the caller did not open is context, not a candidate.

## Hard constraints

- Never merge, never enable auto-merge, never mark a PR ready, never change a base branch.
- Never report a ranking as approval, and never imply the top PR is safe to merge.
- Never silently drop a candidate PR. A PR that unblocks nothing still appears in the output with a count of zero.
- Distinguish evidence from inference everywhere. A dependency read from the tracker's native relationships and one inferred from issue prose are not interchangeable.

# Method

## 1. Collect the PR set and stack topology

For each candidate PR record: URL, canonical issue URL, head branch/SHA, base branch, draft state, CI state, review state (triggered / complete / findings outstanding), and mergeability.

Derive stack edges the way `merge-stack` does: parent -> child when the child's base branch equals **another candidate PR's head branch**. Use a `Depends on:` line to locate candidates and to cross-check, never as the edge itself.

A base that is merely not the repository default branch does not make a PR a stack child. A PR can legitimately target a long-lived integration or release branch that is no candidate's head, and treating that as a stack edge invents a parent-first constraint that does not exist. Where a real parent does exist, it must merge first regardless of leverage.

## 2. Map PRs to issues

Resolve each PR to the canonical issue it completes, using the tracker's own linkage (a closing reference, a linked issue, a tracker field) rather than title matching. A PR with no resolvable issue is reported separately and excluded from leverage arithmetic — it cannot unblock a dependency edge that does not exist.

## 3. Build the remaining-work graph

Let `U` be the in-scope issues that are still open and not yet implemented, plus the issues of the open PRs.

For each issue in `U`, collect its blockers, in this order of confidence:

1. the tracker's **native** dependency relationships (GitHub `blocked by`/`blocking`, Linear relations);
2. blockers **stated in the issue text** ("Depends on:", "Blocked by:", explicit prose);
3. blockers **implied by scope** — the issue's own description names a capability another in-scope issue delivers.

Record the confidence level per edge. Native edges are frequently incomplete: cross-repository dependencies in particular often exist only in prose, because writing them natively can require permissions the run does not have. An empty native blocker list is not evidence of an unblocked issue — check the text before concluding it.

Mark an edge `inferred` when it came from source 2 or 3, and list every inferred edge the ranking depends on so the user can overrule it.

## 4. Compute leverage per PR

For a candidate PR `p` completing issue `i`, compute two distinct numbers:

- **Unblocks now** — issues in `U` whose *only* remaining unmet blocker is `i`. These become startable the moment `p` merges.
- **Gated behind** — the transitive closure of issues in `U` that cannot start until `i` merges, whether or not other blockers also stand in the way. This is the size of the subtree sitting behind that PR.

Report both. They diverge in the case that matters most: a PR can unblock nothing on its own and still gate a large subtree, because its downstream issue is waiting on several in-flight PRs at once.

## 5. Find all-or-nothing sets

Group the issues in `U` by their set of unmet blockers restricted to in-flight issues. Any group whose blocker set has more than one member is an **all-or-nothing set for the issues in that group**: until every member of the set merges, none of those particular issues becomes startable.

Scope the claim to the group and no further. A member of an all-or-nothing set can still unblock other issues that do not need the whole set — if X needs `{A, B}` and Y needs only `A`, then merging `A` starts Y even though it does nothing for X. Before describing a partial merge as buying nothing, check the rest of `U` and report whatever leverage it does have.

State these sets explicitly. They are the most common reason a "merge the biggest one first" instinct wastes a cycle.

## 6. Find hard sequencing constraints

Independent of leverage, identify constraints that force an order:

- **Stack ancestry** — a child PR cannot merge before its parent.
- **Claimed artifacts** — two branches that each add or amend an artifact whose identity or ordering is claimed rather than derived (a numbered migration, a generated manifest, a lockfile, a registry or index). These collide only on the second merge, and which branch must yield depends on merge order. Name the colliding paths, both PR URLs, and what has to be renumbered or regenerated once the order is fixed.
- **Anything the orchestrator surfaced as `NEEDS_USER`** on a candidate PR.

A hard constraint outranks every leverage number. Say so where it applies rather than burying it in a note.

## 7. Rank

Order candidates by:

1. hard sequencing constraints;
2. within a stack, always bottom-up;
3. higher **unblocks now**;
4. higher **gated behind**;
5. smaller/simpler diff, so a review cycle returns sooner.

Then separate the two questions the user is actually asking:

- **Review order** — which PR deserves a human's attention first. Free of stack ordering: a child can be reviewed before its parent even though it cannot merge first.
- **Merge order** — constrained by ancestry and by hard constraints.

For merge batching, prefer completing a chain over stopping partway — but do not claim that completing it avoids restacking. `merge-stack` merges one node, fully restacks the remaining descendant subtree, and refreshes checks and mergeability before selecting the next node, so an N-PR chain performs those rewrites whether it is merged in one sitting or several, and may wait on CI after each one.

What one sitting actually saves is work **outside** the chain: every other open PR absorbs one base movement per sitting rather than one per merge, and a tail left open restacks now and then again when you return to it. Estimate turnaround from the per-node rewrite-and-recheck cost, not from the batch count.

Recommend holding a chain's tail only when there is a review reason to hold it, not to sequence it.

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
- Do not invent a downstream issue to make a ranking look decisive. Zero is a legitimate answer and a useful one.
- Do not restate the ranking as a recommendation to merge now. The output is an ordering, not a go-ahead.
