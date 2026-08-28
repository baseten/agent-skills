# plan-merge-order — design notes

Companion to `SKILL.md`. That file is the contract; this one holds the reasoning, keyed by section. Read a section's note before changing its rules or when applying them to a case the contract doesn't obviously cover. Nothing here overrides the contract.

## When to run

Direct invocation answers with whatever state exists — rather than refusing because the tranche is not formally settled — because the user asking "what should I merge first?" mid-run deserves the best available ordering, not a lecture about lifecycle. The settled-tranche timing is the orchestrator's contract, not a precondition on the analysis being useful.

## Collect the PR set and stack topology

**Why a non-default base is not evidence of a stack edge:** a PR can legitimately target a long-lived integration or release branch that is no candidate's head, and treating that as a stack edge invents a parent-first constraint that does not exist. The edge definition (child's base equals another *candidate's* head branch) is `merge-stack`'s, kept identical so the ordering this skill recommends matches the topology the merging skill will actually act on. `Depends on:` lines locate candidates and cross-check the derived edges, but branch topology is the edge: a body line can be stale or wrong, and merging follows branches, not prose.

## Build the remaining-work graph

**Why an empty native blocker list proves nothing:** native dependency data is frequently incomplete — cross-repository dependencies in particular often exist only in prose, because writing them natively can require permissions the run does not have (the same asymmetry `normalize-github-dependencies` exists to fix). Concluding "unblocked" from missing data inverts the burden of evidence, which is why the text check is mandatory before an issue is declared free.

## Compute leverage per PR

**Why two numbers instead of one:** "unblocks now" and "gated behind" diverge exactly where a single score misleads — a PR whose downstream issue waits on several in-flight PRs at once unblocks nothing by itself yet gates a large subtree. One number would rank it dead last (nothing starts when it merges) or dead first (everything sits behind it), and both are wrong in isolation; the pair lets the user see it is a necessary-but-not-sufficient merge.

## Find all-or-nothing sets

These sets exist in the output because they are the most common reason a "merge the biggest one first" instinct wastes a cycle: merging one member of the set buys nothing *for the issues in that group* until the rest follow. The scoping rule (check the rest of `U` before describing a partial merge as buying nothing) exists because the claim over-generalizes easily — a member can still start other work that never needed the whole set, and reporting "buys nothing" without that check overstates the constraint and can bury real leverage.

## Find hard sequencing constraints

**Why claimed artifacts are a sequencing constraint and not a code conflict:** two branches that each add migration `0012` (or amend the same generated index) merge cleanly one at a time — the collision appears only on the second merge, after the order has been chosen. That is why the constraint must be surfaced now, with both PR URLs and the rework the losing branch needs, rather than discovered as a surprise conflict mid-merge-stack.

## Rank

**Why review order is free of stack ordering:** review and merge answer different questions — where a human's attention goes first versus what the branch topology permits. A child PR can be the riskiest, most review-worthy item in the tranche while being unable to merge until its parent lands; collapsing the two orders hides that.

**Why batching does not avoid restacking:** `merge-stack` merges one node, fully restacks the remaining descendant subtree, and refreshes checks and mergeability before selecting the next node — so an N-PR chain performs those rewrites whether merged in one sitting or several, and may wait on CI after each one. What one sitting actually saves is work *outside* the chain: every other open PR absorbs one base movement per sitting rather than one per merge, and a tail left open restacks now and then again when you return to it. Hence the rule to estimate turnaround from the per-node rewrite-and-recheck cost, and to hold a chain's tail only for a review reason.

## Honesty rules

The all-inferred disclosure goes *before* the table because a reader who sees a confident ranking first anchors on it; the caveat read afterward becomes a footnote instead of a frame. Zero-leverage candidates stay in the output because "merge whenever" is itself useful ordering information, and silently dropping rows makes the table look like a filter rather than a census.
