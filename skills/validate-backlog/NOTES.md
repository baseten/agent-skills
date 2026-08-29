# validate-backlog — design notes

Companion to `SKILL.md`. That file is the contract; this one holds the reasoning, keyed by section. Read a section's note before changing its rules or when applying them to a case the contract doesn't obviously cover. Nothing here overrides the contract.

## Shallow mode

**Why the probe (check 2) sits ahead of the visibility gate (check 3):** a checklist is executed in order, and a validator that reaches the gate first has to judge an unproven boundary before knowing whether a readable transport exists to prove it against. The gate was built for a transport that should return relationships and may be returning a subset; fired on a capability that does not exist, it would halt every such run before the `dependency transport unavailable` classification could be reached.

**Why the hierarchy exception is scoped to blocker edges and nothing else:** treating one class as excusing the other is the more dangerous direction of the two. A truncated hierarchy read silently shortens **the authorized set itself** — issues that never entered scope are not blocked, they are invisible, so nothing downstream ever notices them missing. A failed dependency probe says nothing about whether enumeration was complete, because hierarchy is a different transport with a different answer (on GitHub, MCP reads sub-issues fine while exposing no blocked-by read).

**Why worker-report comments are skipped in the prose scan:** a worker's persisted report necessarily contains dependency URLs, so scanning it puts an edge the orchestrator already classified as stale back into the normalized DAG — on every validation from then on, with the report as its source. This check runs earlier than `implement-issue-core`'s identical exclusion and would otherwise reintroduce the edge before that exclusion ever applies. Whatever the report observed, it observed in the issue's own prose, which the scan reads anyway — skipping the report loses nothing.

## GitHub dependency reads depend on where you are running

**Why this is a disjoint split rather than a preference order:** the two common environments have opposite capability profiles — the cloud container has the interface that cannot answer (MCP, no blocked-by read) and lacks the one that can (`gh`); a local session is the mirror image. That is why the same tracker gives contradictory answers to two agents looking at the same issue on the same day, and why no fallback chain converges on the right answer.

**Why the curl read is the most dangerous state:** it answers. A partial answer wearing the shape of a complete one — same-repo edges present, cross-repo edges dropped with no error — on exactly the edges a multi-repo backlog turns on. An absent read classifies honestly as `dependency transport unavailable` and every downstream rule handles that; a curl read reports a complete-looking edge set that quietly excludes the cross-repo blockers, and nothing downstream has reason to doubt it. Hence: single-repo scope only, limit recorded, and the honest absence preferred the moment scope spans repositories.

**Why the confirming case must cross a repository boundary:** a credential can return same-repo edges perfectly while silently dropping cross-repo ones, so a same-repo confirmation proves nothing about the edges that matter most.

**Why both-cloud is the case to protect:** a cloud orchestrator dispatching cloud workers is the common shape, and its limitation is symmetric — neither side reads edges. A local orchestrator dispatching cloud workers (a proven view up top its workers cannot reproduce) is real but rarer; writing the rules around it would demote the common case to an exception of the rare one.

## Transport visibility

**Why a second read never proves:** a read behind the same credential reproduces the same blind spot and returns looking like confirmation — worse than reading once. Two different transports do exactly that when they authenticate the same way (`gh` and raw HTTP on one `GITHUB_TOKEN`). Two different credentials can still share insufficient scopes, a repository boundary, or a relationship transport. Each of those is a proxy for independent visibility, and each can coincide with a shared blind spot — so agreement corroborates and only a known-true case proves.

**Why enumeration truncation is the worst case:** for a parent/root invocation the bounded set is discovered *through* native hierarchy, so a credential that hides children in one repository yields a truncated scope every later step inherits. The boundary list then comes from the same truncated data, so the missing repository is never tested, never reported — and the result can still be `PASS`, which is what the caller dispatches against. A scope derived from a possibly-partial read cannot bound its own validation; hence the independent boundary list. A matching second count is not a check because two reads sharing a blind spot agree about exactly what neither can see.

**Why unproven-over-dispatchable is `FAIL`, not a warning:** `PASS_WITH_WARNINGS` is for warnings whose safety a reader can weigh, and this one cannot be weighed by construction — judging whether a hidden edge would change execution order requires seeing the edge. Returning it as a warning asks the caller to assess something neither of you can observe, and the caller's own policy then reads an unassessable warning as proceedable.

**Why unavailable-by-construction is different in kind:** the gate is aimed at a transport that *should* return edges and may be silently returning a subset — an unobservable risk, patchy across the graph. Where no dependency read exists at all, nothing is silently short because nothing was returned: the limitation is uniform, permanent until the capability ships, and precisely known (the graph is exactly as complete as prose makes it). An honest, weighable warning — hence the named class instead of a stop.

**Why the named class is `PASS_WITH_WARNINGS` and never `FAIL`:** treating it as `FAIL` would not make the run safer; it would stop **every** GitHub backlog permanently, on a gap no amount of re-reading will close — refusal dressed as rigour, and a contract unsatisfiable on GitHub. What the warning must never be allowed to become is silent, which is why it travels on the run's state, in every dispatch prompt, and in the report.

**Why prose is a legitimate mirror:** prose lives in issue text, so it survives transports that redact structured relationships. That is also why a textual blocker with no visible structured edge is as likely to be evidence of a blind spot as of a missing link — and why the mismatch is a finding, never a licence to trust one side by default.

## Tracker-specific behavior

**Why the hierarchy preference chain does not apply to blocker reads:** the probe already settled the transport. Walking the chain instead is how a multi-repo run ends holding a curl read whose visibility proof can never pass — an unproven boundary and a `FAIL`, where the honest absence would have passed with the named warning.
