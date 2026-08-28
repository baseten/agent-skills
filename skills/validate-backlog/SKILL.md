---
name: validate-backlog
description: Validate a bounded implementation backlog before autonomous execution. Supports GitHub Issues and Linear issues/URLs, prefers native hierarchy/dependency metadata, cross-checks text-described blockers, detects cycles/missing links/scope inconsistencies, and can run in shallow or deep mode. Use standalone for backlog QA or automatically from backlog-orchestrator before dispatch.
---

# Validate Backlog

Validate a bounded implementation tranche before work starts.

This file is the contract; the reasoning behind its rules lives in `NOTES.md` beside it, keyed by section. NOTES explains; it never overrides.

This skill is **issue-source agnostic**. Supported trackers include GitHub Issues and Linear. Preserve canonical full issue URLs in all output and internal mappings; never reduce issues to ambiguous bare keys such as `ABC-123` or `#123` when crossing repositories/trackers.

## Modes

### Shallow mode — default for orchestration

Use structured issue metadata plus issue text to verify that the declared graph is internally coherent. Do not deeply inspect implementation code unless required to resolve an obvious ambiguity.

Checks, in order:

1. enumerate the bounded issue set from the supplied manifest/root/explicit issue set — for a root/parent invocation this enumeration *is* a hierarchy read, so it is subject to the visibility gate at check 3, not exempt from it;
2. **probe the dependency transport** — see *GitHub dependency reads depend on where you are running*. Every rule downstream keys off its result, including check 3's gate; it sits ahead of that gate deliberately (NOTES);
3. **establish that the transport can see the relationships you are about to read**, including the ones enumeration just consumed — see *Transport visibility*. This gates the whole check, and the enumerated scope is never permitted to define its own boundary list. **Consume step 2's result here rather than re-deriving it, and scope it strictly:** where the probe found no dependency read, the **blocker-edge** boundary is classified `dependency transport unavailable` — explicitly not a `FAIL` (see the results rules). The gate is fatal for a transport that should return relationships and may be returning a subset; it never fires on a capability that does not exist.

   **The exception covers blocker edges and nothing else.** Hierarchy is a different transport with a different answer — on GitHub the MCP server reads sub-issues while exposing no blocked-by read — so a failed dependency probe says nothing about enumeration completeness. Hierarchy visibility stays independently required, and unproven hierarchy over dispatchable scope stays a `FAIL`, whatever the dependency probe returned (NOTES: why this is the more dangerous direction);
4. read native parent/sub-issue hierarchy where the tracker supports it;
5. read native `blocked by` / `blocking` relationships **through whatever transport step 2 found working** — on GitHub that is an authenticated `gh issue view <url> --json blockedBy,blocking`, since the MCP server exposes no such read; where step 2 found none, this source is absent and the run is classified `dependency transport unavailable`. Never decide readability from the tracker's name, in either direction;
6. scan issue bodies/comments for textual dependency phrases and linked issue URLs (`blocked by`, `depends on`, `after`, `requires`, `prerequisite`, `must land first`, and equivalents);
   - **skip any comment whose first line is exactly `**Worker report — unclassified evidence, not a dependency record.**`** — a previous worker's persisted report, not a statement about the issue's dependencies; `implement-issue-core` excludes the same comments (NOTES: the stale-edge reintroduction this prevents);
7. compare structured dependencies against text-described dependencies;
8. detect cycles, missing issue targets, contradictory ordering, closed/cancelled prerequisite inconsistencies, orphaned children, duplicates, and links outside the authorized scope;
9. distinguish an external prerequisite from an authorized implementation issue;
10. report whether the graph is safe to execute without guessing.

Structured dependency metadata is authoritative when present; textual descriptions remain a secondary consistency signal. A textual blocker absent from structured metadata is flagged as a likely missing dependency, never silently ignored.

### GitHub dependency reads depend on where you are running

**The transport question is settled by the environment** — a disjoint split, not a preference order with fallbacks (NOTES):

| | GitHub MCP | `gh` CLI | dependency edges |
|---|---|---|---|
| **cloud container** (a Claude Code web/remote session, and the workers it dispatches) | present | **absent** | **none readable** |
| **local session** | absent | present, authenticated, **cross-repo** | **fully readable** |

The MCP server exposes no blocked-by read at all (feature-flagged; tracked at [github/github-mcp-server#3145](https://github.com/github/github-mcp-server/issues/3145)).

**Know which environment you are in, then confirm it — the probe verifies an expectation rather than discovering a capability** — and a result contradicting the table is itself worth reporting. Confirm with the read, never with `command -v gh`: presence is not authentication, and authentication is not cross-repo permission. `gh issue view <url> --json blockedBy,blocking` against an in-scope issue settles all three at once; where the set spans repositories, the confirming case must **cross a repository boundary**.

**A raw `curl` read is a third state, and the most dangerous one** (NOTES): from a cloud container it returns **only same-repository** blocked-by edges, dropping cross-repository ones with no error. Usable **only where the authorized scope lives in a single repository**, and then only with that limit recorded. Scope spanning repositories → prefer the honest absence (`dependency transport unavailable`) over a curl read.

Consequences of the split:

- **A cloud run's graph is strictly poorer than a local one's.** A READY computed from prose alone is a narrower claim than one computed from a corroborated graph — report it in those terms.
- **Both-cloud is first-class usage and the case to protect**: a cloud orchestrator dispatching cloud workers is symmetric — neither side reads edges. A local orchestrator dispatching cloud workers is a real mix the rules must handle, but the symmetric case is never written as an exception to it.
- **This changes when the flag ships.** Re-confirm rather than trusting the table: it describes 2026-08-25.

**Record the confirmed transport state and pass it to everything downstream** — the rules elsewhere are written against *what the transport returned*, never against the word "GitHub". Report which transport answered and what it could see, so the orchestrator carries that into every dispatch prompt.

**Where the probe classified the transport `dependency transport unavailable`** — and only then, never merely because the tracker is GitHub — the issue body and its comments are the only reliable source of what blocks an issue:

- **Read prose properly** — body and comments both; a blocker found after filing is usually a comment.
- **Never report "prose has it, native lacks it" as a visibility disagreement** — native could not have named it, and each false positive invalidates a visibility proof and halts sibling dispatch.
- **Record the completeness of every blocker set in scope as unproven**, and say why: no native source exists to corroborate prose, so an unwritten blocker is undetectable by construction. The skill carries unproven completeness to the caller as a judgement, not a stop.
- **A visibility proof over that dependency boundary cannot be established at all.** Never substitute a hierarchy or issue read that happens to succeed: those prove *some* call works, which was never in doubt.

**Where the probe found a working read** — an authenticated `gh`, or MCP once the flag ships — none of the four applies: the three-source union works as written, membership comparisons are meaningful, and a visibility proof is both possible and required, across a repository boundary if the set spans repositories. Linear is in this branch too.

Everything above is a statement about a probed transport, never about a tracker. The classification travels with the result instead of being re-derived from the tracker's name downstream.

### Transport visibility

A scoped or relayed credential can return a partial relationship set without error — an edge that exists but is invisible looks identical to one never created. So:

- **Establish that the transport can see the relationships in scope *before* consuming them, against a case whose answer is already known** — an edge the caller confirmed, or one this run just wrote. Only a known-true case proves, because its answer does not depend on any transport being trustworthy.
- **A second read is not a substitute, whatever distinguishes it** (NOTES: why each variant — same credential, different transport, different credential — can share the blind spot). A second read corroborates at best and never proves. Where no known-true case is available, the boundary is unproven — say so rather than promoting agreement into a proof.
- **One control per boundary in scope.** A control inside a repository proves that repository only; for a graph spanning A, B and C, a visible A→B edge says nothing about C.
- **Bind each proof to the credential that produced it** — a non-secret identity (authenticated account and scopes), never the credential itself — and revalidate after a restart and on reauthentication. **An authorization error invalidates every proof bound to that credential, across every transport using it** — grants narrow server-side, so a failure through one transport condemns the cached proofs of every other transport sharing the token.
- **Enumeration is itself a relationship read.** A credential that hides children in one repository yields a truncated scope every later step inherits, and the result can still be `PASS` (NOTES). So the boundary list must not come only from enumerated data — establish it from something independent: the caller-supplied issue set, the root/manifest's own prose listing of its children (a legitimate mirror: text survives transports that redact structured relationships), or a second enumeration compared against the first, where **a differing count is the finding and a matching count is not a check**. Where the scope can only be derived from one unproven transport, that is itself the finding: report it and do not return `PASS`.
- **Do this before reading, not only when something looks wrong.** A hidden edge with no prose mirror produces no mismatch to investigate; a check that validates visibility only on disagreement omits that edge and returns `PASS` — the most damaging possible output, because `PASS` is what the caller dispatches against.

**An unproven boundary involving dispatchable scope is a `FAIL`**, not a warning: its safety cannot be weighed by construction — judging whether a hidden edge would change execution order requires seeing the edge (NOTES).

`PASS_WITH_WARNINGS` remains available where the unproven boundary touches nothing dispatchable — external prerequisites read for readiness, or issues outside the authorized set — **and in one further case, different in kind from the one the gate exists for**:

**Unproven-because-untested and unavailable-by-construction are not the same finding** (NOTES). Where the tracker exposes **no dependency read at all** — GitHub today — nothing is silently short, because nothing was returned: the limitation is **uniform** across every issue, **permanent** until the capability ships, and **precisely known** (prose is the declared source; the graph is exactly as complete as prose makes it). That case returns `PASS_WITH_WARNINGS` under the named warning class **`dependency transport unavailable`**, carrying the tracker, the reason, and any upstream tracking reference. The warning is never silent: it belongs on the run's state, in every dispatch prompt, and in the report. Either way, name the transport, the credential identity, and every boundary left unproven, and report the shortfall as `not visible via <transport>`, never as a missing dependency.

Prose dependencies are a legitimate **mirror**, not redundant noise: they survive transports that redact structured relationships, and a textual blocker with no visible structured edge is as likely evidence of a blind spot as of a missing link. Structured edges stay authoritative wherever both are visible; a mismatch is a finding to report, never a licence to trust one side by default.

Cross-repository edges deserve the most scepticism on both counts: likeliest to be redacted by scoping, and their loss changes execution order the most.

### Deep mode

Deep mode performs every shallow check, then attempts to validate whether the **underlying work itself** implies missing or incorrect dependencies.

For each issue, inspect the relevant repository specs/code/interfaces as needed to understand what the issue changes or consumes. Dependency signals:

- schema/data-model changes before API/service consumers;
- API/contracts/generated types before frontend consumers;
- migrations before code requiring migrated state;
- shared types/components/utilities before dependents;
- feature flags/config before code that assumes them;
- cross-repository contracts;
- tests/fixtures/tooling that must change before dependent work can pass;
- two issues editing the same architectural surface where declared independence is implausible.

Deep mode may conclude: a declared dependency is justified; a declared dependency appears unnecessary; a missing dependency is strongly implied; ordering is ambiguous and needs human confirmation.

Never invent dependencies merely because two issues touch related areas. Give a confidence level and evidence for inferred dependency changes.

## Tracker-specific behavior

### GitHub

Prefer first-class GitHub sub-issue hierarchy and issue dependency metadata (`blocked by` / `blocking`) when exposed by the available interface, over Markdown references alone.

For **hierarchy** reads: if the current MCP/tool surface does not expose them directly, use authenticated `gh`/GitHub API when available; otherwise inspect what the environment does expose and explicitly report any metadata that could not be read. Prefer a first-class tool over a CLI and a CLI over raw HTTP, and treat a relationship set read over raw HTTP as provisional until its visibility is proven.

For **`blocked by` / `blocking`** reads that preference chain does not apply — the probe already settled the transport. An authenticated `gh` is the read that works today; raw HTTP only where the authorized scope lives in a single repository; where the probe found no read, the answer is the `dependency transport unavailable` classification, reported rather than replaced by inspecting whatever the environment returns (NOTES: how walking the chain strands a multi-repo run on an unprovable curl read).

Still parse issue descriptions/comments for textual blockers and compare them against structured metadata.

### Linear

Prefer Linear's native parent/sub-issue and blocker/dependency relationships. Preserve full `https://linear.app/.../issue/...` URLs in graph/report output and PR linkage context; bare identifiers may be displayed additionally but are not the canonical identity.

Parse descriptions/comments for textual dependency statements as a secondary consistency check.

## Scope

Validation never expands implementation authority.

When invoked with a build-order/root manifest, validate its authorized descendant/explicit implementation set plus external prerequisites required to assess readiness. External prerequisites may be inspected but must remain marked external.

## Output

Return a concise validation result:

```text
Mode: shallow | deep
Scope: 14 implementation issues + 2 external prerequisites
Result: PASS | PASS_WITH_WARNINGS | FAIL

Errors:
- <canonical issue URL> ...

Warnings:
- <canonical issue URL> text says it depends on <URL>, but no structured blocker link exists

Suggested dependency changes (deep mode only):
- Add <A URL> -> <B URL> — confidence high — reason ...
```

Also return a normalized DAG using canonical full issue URLs as node identities.

`FAIL` means the orchestrator must not dispatch affected work until corrected. `PASS_WITH_WARNINGS` may proceed if warnings do not make execution order unsafe — which is why unproven relationship visibility over dispatchable scope is never one of those warnings: its safety is exactly what cannot be established. It is a `FAIL`. **The single exception is the named `dependency transport unavailable` class**, where the tracker exposes no dependency read at all: uniform, permanent, precisely known — `PASS_WITH_WARNINGS` carrying that class (NOTES: why `FAIL` there would make this contract unsatisfiable on GitHub).

## Mutation

Validation is read-only by default. Never add/remove dependency links or rewrite issues unless the user explicitly asks to apply the suggested fixes.
