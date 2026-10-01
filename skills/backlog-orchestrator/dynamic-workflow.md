# backlog-orchestrator — the Dynamic Workflow fan-out

Part of `backlog-orchestrator`'s contract, read before writing a Dynamic Workflow script: the first fan-out, a fresh one for a later batch (`SKILL.md`, *Parent supervision loop*, step 7), and a restart's (`restart-resume.md`, step 9). `SKILL.md` keeps what decides whether the tier is used — *Invocation*, *Preferred runtime: Claude Code Dynamic Workflows* and *Runtime selection* — and that a workflow never supervises; this file holds what the script must do once the tier is chosen. The reasoning is in `NOTES.md`, under *Runtime selection*.

## Writing the workflow script

When the user has opted into a workflow for this invocation (`SKILL.md`, *Invocation*), use it **only for the implementation fan-out**:

- write the workflow script yourself so each `agent()` call's prompt/model explicitly encodes: the exact authorized issue set and normalized dependency DAG (as separate fan-out stages honoring the DAG's ordering), the model selected for that issue (per issue, not one model for the fan-out — see `SKILL.md`, *Model and skill policy*), one issue per worker, an isolated checkout/worktree per worker, the exact calculated branch/base, remote checkpoint rules, and the retry budget. **Size the fan-out to the `concurrent-open-prs` headroom at launch, never to the whole authorized set**: a running workflow cannot be reached or paused once the cap fills, so the cap bounds nothing that runs inside it;
- make the checkpoint push a **pipeline stage of its own**, not only a rule inside the implementation prompt — the parent cannot reach into a running fan-out to enforce it (`SKILL.md`, *Where the parent cannot reach*), so the script's control flow is the only thing that can guarantee the push;
- do **not** give the workflow permission to redefine the product backlog — it must execute the already validated bounded DAG supplied by this skill;
- treat the workflow purely as an **execution substrate** for that one fan-out run, not as the source of truth for issue/PR state.
