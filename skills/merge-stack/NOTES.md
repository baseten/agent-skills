# merge-stack — design notes

Companion to `SKILL.md`. That file is the contract; this one holds the reasoning, keyed by section. Read a section's note before changing its rules or when applying them to a case the contract doesn't obviously cover. Nothing here overrides the contract.

## Why base/head is authoritative and `Depends on:` is not

The base/head relationship is what Git and GitHub actually merge against; the body line is prose a human (or an earlier run) wrote and may be stale, wrong, or unedited after a retarget. Merging follows branches. The line earns its keep as a discovery aid — it locates candidate PRs cheaply and cross-checks the derived edge — but an edge that exists only in the body and not in the branch topology is a documentation bug to report, never a merge order to follow.

## Parent-before-child

Merging a child while its parent is open merges the child into the parent's **feature branch**, not into the intended integration branch — the child's work "lands" somewhere that may itself be rewritten, squashed, or closed, and the integration branch never receives it as reviewed. Requiring the parent merged and the child restacked first means every merge lands where the reviewer believed it would.

## Why the ancestry check precedes every rebase

`rebase --onto <new-base> <old-parent-head> <child>` replays exactly the commits after `<old-parent-head>`. If the parent branch was force-rewritten after the child forked, the recorded old head is no longer in the child's history: the range then includes obsolete parent commits reachable only from the child, and the rebase replays them as if they were the child's own work — force-pushing another PR's abandoned commits into the child's diff. The `merge-base --is-ancestor` check is the cheap proof that the recorded boundary is real. When it fails, a merge-base with the rewritten parent is **not** the boundary either: the last commit the rewritten parent's history and C's history share can be only their integration-branch ancestor, and rebasing from there replays the same abandoned parent commits the check exists to keep out of C. The true boundary is the tip of the parent lineage C actually forked from — the line between parent-owned and C-owned commits — which only independent evidence can establish (the parent head recorded when C was created, the parent PR's own timeline, commit-by-commit ownership), confirmed by the ancestor test before any rewrite. Hence stop-and-report rather than guess.

## Why the `--onto old-parent-head` form and not a plain retarget

After a squash merge, the integration branch contains a new squash commit rather than P's original commit IDs. A plain retarget (rebase onto the new base without excluding the old parent range) would therefore treat P's original commits as unmerged and make them reappear in C's diff. `rebase --onto new-base old-parent-head child` selects only the commits after the old parent head and replays exactly those onto the merged base — the child's diff stays the child's work.

## Why restacking recurses through every descendant

Rewriting C changes C's head SHA, so any D based on C now has an obsolete ancestor chain: restacking only the direct child leaves grandchildren containing commits that no longer exist on any parent branch. The old-head → new-head propagation must run through every descendant path or the leak the direct-child rebase prevented simply reappears one level down.

## Why status is refreshed after every rewrite

A rebase can invalidate approvals or rerun CI, so the status a PR had before its restack says nothing about whether it may merge now. Merging the next node on stale pre-rebase status is how a red or unapproved PR lands; the refresh after every rewrite is what makes entire-stack mode safe to run unattended.

## Failure and recovery

Remote branches and GitHub PR state are the durable record; a resumed session's memory of "what step I was on" is not. Rediscovering actual bases and head SHAs first — and stopping when state is ambiguous — is what prevents replaying a rebase against a branch that was already rewritten, which would rewrite it a second time and corrupt the very diffs the first pass preserved.

## Output

**Why the identity read-back is per write kind through each pair:** a merge, a base retarget, and a body edit are distinct write kinds a platform may author differently, and one stack operation routinely performs several through the same (transport, credential) pair. Reading back only a pair's first write would return the merge author while silently losing the retarget or body-edit author — and later operations would then consume the wrong kind's evidence. The full rule lives in `backlog-orchestrator`, *Posting identity*.
