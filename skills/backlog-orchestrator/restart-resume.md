# backlog-orchestrator — restart and resume

Part of `backlog-orchestrator`'s contract, read on a restart before the validation preflight. `SKILL.md`, *Restart / resume*, says what counts as one; it points here from there and from *Mandatory validation preflight*, and cites this file from *Default usage safeguards* (resuming an adopted branch), *Arming the wait when nothing is in flight* and *Stop conditions* (a returned checkpoint), and *How a worker's report actually reaches you* (which records a restart adopts). Its rules assume `SKILL.md` has been read, and `SKILL.md` assumes them on a restart. The reasoning is in `NOTES.md`, under *Restart / resume*.

## Restart / resume

A Dynamic Workflow interrupted by session exit restarts fresh rather than resuming, so restart recovery always comes from tracker + GitHub remote state, never from workflow-runtime state:

1. re-expand the exact same bounded manifest/scope;
2. rerun `validate-backlog` at the mode the escalation rules select (`SKILL.md`, *Escalating to deep validation*; where a trigger fires, read `deep-validation.md` before this preflight) — a restart re-derives readiness from scratch, so those triggers apply here exactly as at the first preflight — then reconcile its DAG against blockers a previous run recorded on the issues themselves. What an edge's **absence** from that DAG means depends on the boundary's proof state and on the edge's provenance, and this step is the main caller of the retirement rule under `SKILL.md`, *Outcomes*. Read the proof state from the validator run you just made, never one carried over: a passing result means every boundary over dispatchable scope was proven (an unproven dispatchable boundary is a `FAIL`), and the boundaries left unproven are named. **The exception is a `PASS_WITH_WARNINGS` carrying `dependency transport unavailable`, which passes with those boundaries deliberately unproven — read that as unproven, never as proof**, or an absent prior edge would count as evidence for retirement and later workers would get a READY context marked proven when nothing proved it. Then:

   - **visibility unproven for that boundary** — re-adopt the edge rather than rediscovering it by dispatching into it again;
   - a worker's report is not a blocker record and must not be adopted as one, wherever it is found — on its PR, or in an issue comment left by older tooling. Read it for what the worker observed, then classify it here as though the worker had just returned it. An unclassified edge does not become established by having survived a session boundary;
   - **proven, and the edge is native by now** (a later run may have made it native via `normalize-github-dependencies`) — a proven read that no longer returns it is the retirement case: retire it, dated, rather than re-adopting a dependency someone deliberately removed;
   - **proven, and the edge lives only in the persisted comment record** — absence proves nothing, because native metadata was never supposed to show it. Re-adopt, then classify it here: **this step is the run adoption** the retirement rule anchors to;
3. order by normalized DAG + explicit build order;
4. fetch current tracker statuses, PRs, and remote branches;
5. skip every proven `DONE` issue — after the recovery-ref enumeration in `SKILL.md`, *Durable remote state and restart*, which is what makes `DONE` provable here, since this step precedes both PR and checkpoint adoption;
6. adopt existing open PRs through `supervise-prs`, *Adopt* — which rebuilds each one's record from the PR's durable evidence, an unrecoverable counter counting as spent — **recovering each one's `Chartered scope:` line from its body into the per-PR block, or recording the charter as unavailable where the body carries none** (see `SKILL.md`, *PR promotion and central supervision* — the chartered-scope head check is what this feeds);
7. adopt matching remote issue branches/checkpoints even when no PR exists yet;
8. identify the earliest still-unfinished executable frontier;
9. resume there, dispatching fresh workers (in a new Dynamic Workflow fan-out if the user re-opts in, sized to the headroom as `dynamic-workflow.md` requires, or via the fallback runtime chain) for whatever is not yet durable — **up to the `concurrent-open-prs` headroom**. Resuming an adopted branch is a dispatch like any other, and an adopted branch holds a slot only once a worker resumes it, so a restart adopting twelve open PRs and two branches holds twelve and resumes the branches only as slots free.

"Latest unclosed ticket" means the earliest remaining unfinished point in established build order, not the numerically newest issue. Parallel groups may have multiple resume-frontier nodes.
