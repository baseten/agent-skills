# ship-branch — design notes

Companion to `SKILL.md`. That file is the contract; this one holds the reasoning, keyed by its section names. Nothing here overrides the contract.

## Ship a branch

**Why this skill exists at all (Oct 2026):** the supervised path — `supervise-prs`, settle, the merge gate — was reachable only by implementing a tracked issue through `implement-issue-core`. Work done in an ordinary session from a Slack thread or prose had no way in short of filing an issue first or hand-assembling `supervise-prs`'s inputs, which default to zero budgets when nobody passes them. The entry point belongs in `implement-issue` (its NOTES, *Phase 1, from an existing branch*, say why); this skill is the name a user asking to "ship this branch" finds.

**Why it restates nothing:** every rule it could carry — the preflight, the dependency-view hold, the issue-less confirmation — is already stated at the decision point that reads it in `implement-issue`. A summary here would serve no decision point of its own, which is the case `CLAUDE.md` says to collapse rather than reconcile.

## Inputs

**Why inputs are values:** the same reason `supervise-prs` takes them that way — the callee never reads its caller's contract to find out what to do (`supervise-prs`, *Inputs*).

## Boundaries

**Why an existing PR is not this skill's:** see `implement-issue/NOTES.md`, *Phase 1, from an existing branch* — its counters are already spent, and this path passes 0. `supervise-prs` alone is not a substitute: it defaults to zero budgets, so the boundary says so rather than pointing there as a route.
