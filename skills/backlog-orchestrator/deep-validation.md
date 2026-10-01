# backlog-orchestrator — escalating to deep validation

Part of `backlog-orchestrator`'s contract, read when an escalation trigger fires — `SKILL.md`, *Escalating to deep validation*, keeps the triggers and the rule that a wave no trigger reaches does not escalate, because every preflight reads them to decide — before the escalated preflight runs, whether that is the first preflight, a restart's or a frontier advance's; and read before acting on a coverage finding (`SKILL.md`, *Outcomes*). Its rules assume `SKILL.md` has been read, and `SKILL.md` assumes them wherever it points here. The reasoning is in `NOTES.md`, under *Escalating to deep validation*.

## Running an escalation

Scope the escalation to the affected subgraph: the triggering node and the dependencies it consumes, leaving unrelated branches shallow.

Escalation changes the **mode** of the preflight, never whether one runs, and it reads more deeply *within* the bounded manifest — it never widens scope. `PASS` / `PASS_WITH_WARNINGS` / `FAIL` are handled exactly as `SKILL.md`, *Mandatory validation preflight*, handles them, at either mode, unproven relationship visibility stays unproceedable at either mode — with the same `dependency transport unavailable` exception — and the deeper read consumes model budget, not `new-issue-budget`.

### Coverage is not visibility

A coverage gap is not the unproven-visibility case, and that doctrine cannot catch it. There, an edge may exist that your read cannot show. Here the read was complete, the edge is real, the dependency is genuinely satisfied, and every transport proof over the boundary stays valid; what is missing is **coverage** — the closed issue's deliverable does not include the part the consumer needs (a backend wave that satisfies every declared edge and ships no route for the frontend to call). `CLOSED` and `MERGED` mean the scoped work got done, not that it exposes what something downstream was written against. Only reading the code behind the edge reveals that, which is why the answer is a mode change. Do not invalidate a visibility proof over a coverage finding.

### Reporting

- **Escalation that finds nothing is still reported** — name the trigger, the nodes escalated, and the clean result in the checkpoint output.
- **Escalation on one node does not force deep validation of unrelated branches.** Nodes no trigger reaches are validated shallow in the same preflight, and the checkpoint says which nodes got which mode.
- **If deep mode is unavailable** for any reason, the escalated nodes are **not dispatchable**: a shallow `PASS` over them is no answer. Take the escalation's `FAIL` path — stop those paths, raise `NEEDS_USER`, and continue only the branches no trigger reached, which shallow validated on its own terms. Report the condition, the nodes owed the deeper read, and what blocked it. Never fall back to shallow and dispatch on its `PASS`.
