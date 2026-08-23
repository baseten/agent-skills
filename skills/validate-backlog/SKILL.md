---
name: validate-backlog
description: Validate a bounded implementation backlog before autonomous execution. Supports GitHub Issues and Linear issues/URLs, prefers native hierarchy/dependency metadata, cross-checks text-described blockers, detects cycles/missing links/scope inconsistencies, and can run in shallow or deep mode. Use standalone for backlog QA or automatically from backlog-orchestrator before dispatch.
---

# Validate Backlog

Validate a bounded implementation tranche before work starts.

This skill is **issue-source agnostic**. Supported trackers include GitHub Issues and Linear. Preserve canonical full issue URLs in all output and internal mappings; do not reduce issues to ambiguous bare keys such as `ABC-123` or `#123` when crossing repositories/trackers.

## Modes

### Shallow mode — default for orchestration

Use structured issue metadata plus issue text to verify that the declared graph is internally coherent. Do not deeply inspect implementation code unless required to resolve an obvious ambiguity.

Checks:

1. enumerate the bounded issue set from the supplied manifest/root/explicit issue set;
2. read native parent/sub-issue hierarchy where the tracker supports it;
3. read native `blocked by` / `blocking` dependency relationships where supported;
4. scan issue bodies/comments for textual dependency phrases and linked issue URLs, including `blocked by`, `depends on`, `after`, `requires`, `prerequisite`, `must land first`, and equivalent wording;
5. compare structured dependencies against text-described dependencies;
6. detect cycles, missing issue targets, contradictory ordering, closed/cancelled prerequisite inconsistencies, orphaned children, duplicates, and links outside the authorized scope;
7. distinguish an external prerequisite from an authorized implementation issue;
8. report whether the graph is safe to execute without guessing.

Structured dependency metadata is authoritative when present, but textual descriptions remain a secondary consistency signal. A textual blocker absent from structured metadata should be flagged as a likely missing dependency rather than silently ignored.

#### When text and structured metadata disagree

Before reporting a structured edge as missing, establish whether the transport in use can see structured cross-repository edges **at all**. A relayed or scoped credential can return a partial relationship set without error — the entries it cannot reach are absent rather than refused — so an edge that exists and is merely invisible looks identical to one that was never created. Prove visibility against a case whose answer is known (an edge the caller confirmed, or one visible through a second transport) before concluding anything from an absence.

Skipping that step turns this check into a confident generator of false findings, precisely where it is trusted most: cross-repository edges are both the ones most likely to be redacted by scoping and the ones whose loss most changes execution order.

This is why prose dependencies are a legitimate **mirror** rather than redundant noise. They live in issue text, so they survive transports that redact structured relationships, and a textual blocker with no visible structured edge is as likely to be evidence of a blind spot as of a missing link. Structured edges stay authoritative wherever both are visible; a mismatch is a finding to report, never a licence to trust one side by default.

Report an unproven absence as `not visible via <transport>`, not as a missing dependency.

### Deep mode

Deep mode performs every shallow check, then attempts to validate whether the **underlying work itself** implies missing or incorrect dependencies.

For each issue, inspect the relevant repository specs/code/interfaces as needed to understand what the issue changes or consumes. Look for dependency signals such as:

- schema/data-model changes before API/service consumers;
- API/contracts/generated types before frontend consumers;
- migrations before code requiring migrated state;
- shared types/components/utilities before dependents;
- feature flags/config before code that assumes them;
- cross-repository contracts;
- tests/fixtures/tooling that must change before dependent work can pass;
- two issues editing the same architectural surface where declared independence is implausible.

Deep mode may conclude:

- a declared dependency is justified;
- a declared dependency appears unnecessary;
- a missing dependency is strongly implied;
- ordering is ambiguous and needs human confirmation.

Do not invent dependencies merely because two issues touch related areas. Give a confidence level and evidence for inferred dependency changes.

## Tracker-specific behavior

### GitHub

Prefer first-class GitHub sub-issue hierarchy and issue dependency metadata (`blocked by` / `blocking`) when exposed by the available GitHub interface. GitHub supports native issue dependencies and hierarchy; use these instead of relying only on Markdown references.

If the current MCP/tool surface does not expose those relationship fields directly, use authenticated `gh`/GitHub API when available; otherwise inspect issue relationship information available through the environment and explicitly report any metadata that could not be read. Prefer a first-class tool over a CLI and a CLI over raw HTTP, and treat a relationship set read over raw HTTP as provisional until its visibility is proven — dependency fields are exactly the data a scoped credential returns in part.

Still parse issue descriptions/comments for textual blockers and compare them against structured metadata.

### Linear

Prefer Linear's native parent/sub-issue and blocker/dependency relationships. Preserve full `https://linear.app/.../issue/...` URLs in graph/report output and PR linkage context. Bare Linear identifiers may be displayed additionally for readability but are not the canonical identity.

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

`FAIL` means the orchestrator must not dispatch affected work until corrected. `PASS_WITH_WARNINGS` may proceed if warnings do not make execution order unsafe.

## Mutation

Validation is read-only by default. Do not add/remove dependency links or rewrite issues unless the user explicitly asks to apply the suggested fixes.
