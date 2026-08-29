# normalize-github-dependencies — design notes

Companion to `SKILL.md`. That file is the contract; this one holds the reasoning, keyed by section. Read a section's note before changing its rules or when applying them to a case the contract doesn't obviously cover. Nothing here overrides the contract.

## Why a cloud container does not degrade gracefully

Run without a real dependency read, this skill normalizes against a view that cannot see half the graph, and writes the result into the metadata every later readiness check trusts. Concretely:

- with no read at all, `ALREADY_PRESENT` and `CONFLICT` cannot be determined, so normalizing would re-add edges that already exist and could contradict ones it cannot see;
- with the degraded `curl` read, a cross-repo edge reads as absent and gets written again — and an edge written into native metadata is the authoritative answer every later readiness check trusts, which is the most expensive place in the system to be confidently wrong.

That asymmetry — this skill *writes* what others only read — is why the probe-before-anything rule is stated more forcefully here than in `validate-backlog`, which can carry an absent read as an honest classification.

## Inputs and scope

**Why a truncated candidate set defeats its own validation:** a credential that hides children in one repository yields a truncated candidate set, and a scope derived from a possibly-partial read cannot bound its own validation — the hidden repository never appears, so no control ever tests it, and every edge written afterwards rests on a view known to be incomplete. Hence the independent cross-check, and hence a differing count *stopping writes* here where in a read-only skill it merely warns. A matching count is not the converse because two enumerations sharing a blind spot agree exactly about what neither can see.

## Dependency sources

**Why a worker-report comment never contributes an edge:** the report is a worker's persisted observation, not a statement about the issue's dependencies, and it necessarily contains dependency URLs. This skill writes native metadata, so an edge taken from a report becomes the authoritative answer every later readiness check trusts — including an edge the orchestrator has already classified as stale, which then blocks its issue with nothing prompting a re-examination. `validate-backlog` and `implement-issue-core` skip the same comments in their read-only scans; the same exclusion matters most here because the mistake is written back into the tracker.

## Precondition: trustworthy absence

**Why absence needs proof:** a relayed, proxied, scoped, or short-lived credential can return a partial relationship set with no error and no warning — a credential scoped to one repository returns one repository's worth of a graph spanning several, and the response looks complete. The edge you are about to add may already be live and simply invisible. This skill decides what to write from what it believes is missing, so an under-reporting read converts directly into duplicate writes.

**Why the proof is required at every transport tier:** a first-class tool or a CLI running on a directly scoped credential under-reports exactly as quietly as a relayed one — the hazard is the credential's scope, not the transport's shape. A higher tier lowers the odds without removing the need to check.

**Why a second read never proves:** a read behind the same credential reproduces the same blind spot and reads as confirmation — and a second read through a different transport authenticating the same way is the usual case, not the exotic one. Different credentials can still share insufficient scopes, a repository boundary, or a relationship transport, so their agreement clears nothing either. Only a known-true case proves, because its answer does not depend on any transport being trustworthy.

**Why the asymmetric-cost rule resolves doubt toward not writing:** not writing a needed edge leaves a report the user can act on; writing a duplicate of a live edge mutates the graph on the strength of a blind spot. `UNVERIFIED` with nothing written is the recoverable failure.

## Confirmation and mutation policy

**Why descriptions stay intact by default:** the prose may contain useful context, and removing it is a separate editorial mutation from adding native edges — bundling the two turns an additive, reversible normalization into a lossy rewrite nobody asked for.
