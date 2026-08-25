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

1. enumerate the bounded issue set from the supplied manifest/root/explicit issue set — noting that for a root/parent invocation this enumeration *is* a hierarchy read, so it is subject to check 2 rather than exempt from it;
2. **establish that the transport can see the relationships you are about to read**, including the ones enumeration just consumed — see Transport visibility below. This gates the whole check, not just the mismatch case, and the enumerated scope is not permitted to define its own boundary list;
3. read native parent/sub-issue hierarchy where the tracker supports it;
4. read native `blocked by` / `blocking` dependency relationships where supported — **on GitHub they are not readable at all**, see *GitHub: native dependency edges are unreadable* below;
5. scan issue bodies/comments for textual dependency phrases and linked issue URLs, including `blocked by`, `depends on`, `after`, `requires`, `prerequisite`, `must land first`, and equivalent wording;
   - **skip any comment whose first line is exactly `**Worker report — unclassified evidence, not a dependency record.**`.** That is a previous worker's persisted report on that issue, not a statement about the issue's dependencies, and it necessarily contains dependency URLs — so scanning it puts an edge the orchestrator already classified as stale back into the normalized DAG, on every validation from then on, with the report as its source. `implement-issue-core` excludes the same comments from its dependency union; this check runs earlier and would otherwise reintroduce the edge before that exclusion ever applies. Whatever the report observed, it observed in the issue's own prose, which this check reads anyway;
6. compare structured dependencies against text-described dependencies;
7. detect cycles, missing issue targets, contradictory ordering, closed/cancelled prerequisite inconsistencies, orphaned children, duplicates, and links outside the authorized scope;
8. distinguish an external prerequisite from an authorized implementation issue;
9. report whether the graph is safe to execute without guessing.

Structured dependency metadata is authoritative when present, but textual descriptions remain a secondary consistency signal. A textual blocker absent from structured metadata should be flagged as a likely missing dependency rather than silently ignored.

### GitHub: native dependency edges are unreadable — prose is the only source

**On GitHub, the issue body and its comments are the only reliable source of what blocks an issue.** This is not a preference or a fallback ordering; it is the whole of the available evidence. Three separate limits stack, and each one alone would be enough:

- **The MCP server exposes no dependency read.** Blocked-by / blocking is behind a feature flag that cannot be enabled in this environment. Tracked upstream at [github/github-mcp-server#3145](https://github.com/github/github-mcp-server/issues/3145), which is being worked on — so **re-test before trusting any of this**; the day that ships, native metadata becomes a real second source and most of this section retires.
- **The `curl` fallback is worse than unavailable, because it answers.** Reading the REST endpoint directly needs credentials that a container without `gh` does not have, and the degraded result **filters cross-repository edges out invisibly** — no error, no warning, just a shorter list. That is the failure mode this skill warns about everywhere else: a partial answer wearing the shape of a complete one. Where a backlog spans repositories, the edges most likely to be dropped are exactly the ones that matter.
- **The count field is a trap, not a workaround.** `issue_read(method='get_sub_issues')` on a *parent* returns each child's raw REST payload, which happens to carry an `issue_dependencies_summary` (`blocked_by`, `blocking`, `total_blocked_by`, `total_blocking`). This is incidental passthrough of one endpoint's response body, not a dependency capability, and it is written down here **only so the next reader does not rediscover it and build on it**. It names no edge, so it can never identify a blocker; and it inherits the cross-repo filtering above, so it cannot even be trusted as a lower bound on a cross-repo graph. Do not schedule, dispatch, or clear anything on it.

So on GitHub:

- **Read prose properly** — body and comments both, since a blocker found after filing is usually a comment. It carries the identity and nothing else does.
- **Never report "prose has it, native lacks it" as a visibility disagreement.** Native could not have named it. On this transport that comparison would fire for every prose-named blocker on every issue, and each false positive invalidates a visibility proof and halts sibling dispatch.
- **Record the completeness of every GitHub blocker set as unproven**, and say why: no native source exists to corroborate prose, so an unwritten blocker is undetectable by construction. This is honest rather than paralysing — the skill already carries unproven completeness through to the caller as a judgement rather than a stop.
- **A visibility proof over a GitHub dependency boundary cannot be established at all.** There is no read to demonstrate. Do not substitute a hierarchy or issue read that happens to succeed: those prove that *some* call works, which was never in doubt, and dressing that up as a relationship proof is how a run convinces itself it can see a graph it cannot.

**This is GitHub-specific.** Linear exposes real relationship reads, so the three-source union works there as written and none of the above applies.

### Transport visibility

A scoped or relayed credential can return a partial relationship set without error — the entries it cannot reach are absent rather than refused — so an edge that exists but is invisible looks identical to one that was never created. Establish that the transport can see the relationships in scope **before consuming them**, against **a case whose answer is already known** — an edge the caller confirmed, or one this run just wrote. Only a known-true case can establish the proof, because its answer does not depend on any transport being trustworthy.

A second read is not a substitute, whatever distinguishes it. A read behind the same credential reproduces the same blind spot and returns looking like confirmation, which is worse than reading once; two different transports do exactly that when they authenticate the same way (`gh` and raw HTTP on one `GITHUB_TOKEN`); and two different credentials can still share insufficient scopes, a repository boundary, or a relationship transport. Each of those is a proxy for independent visibility and each can coincide with a shared blind spot, so a second read corroborates at best and never proves. Where no known-true case is available, the boundary is unproven — say so rather than promoting agreement into a proof. Cover **every** boundary the graph crosses, not one of them. A control inside a repository proves that repository only, and for a graph spanning A, B and C a visible A→B edge says nothing about C — so a single cross-repository control is enough to make a credential that cannot reach C look proven, while A→C and B→C vanish. One control per boundary in scope.

Bind each proof to the credential that produced it — a non-secret identity such as the authenticated account and its scopes, never the credential itself — and revalidate after a restart and on reauthentication, since a rotated or narrowed credential makes a stale proof read as applicable. An authorization error invalidates **every proof bound to that credential, across every transport using it** — not only the failed call, and not only the transport it arrived on. Grants narrow server-side, so a failure through one transport condemns the cached proofs of every other transport sharing the token, even though none of them has failed yet.

**Enumeration is itself a relationship read.** For a parent/root invocation, check 1 discovers the bounded set *through* native hierarchy — so a credential that hides children in one repository yields a truncated scope, and every later step inherits it. The boundary list then comes from the same truncated data, so the missing repository is never tested, never reported, and the result can still be `PASS`. A scope derived from a possibly-partial read cannot bound its own validation.

So the boundary list must not come only from enumerated data. Establish it from something independent: the issue set the caller supplied, the root/manifest's own prose listing of its children — a legitimate mirror for exactly this reason, since text survives transports that redact structured relationships — or a second enumeration compared against the first. A differing count is the finding; a matching count is not a check, from the same credential or a different one, since two reads sharing a blind spot agree about exactly what neither can see. Where the scope can only be derived from one unproven transport, that is itself the finding: report it and do not return `PASS`.

Do this before reading, not only when something looks wrong. A hidden edge with no prose mirror produces no mismatch to investigate, so a check that validates visibility only on disagreement will omit that edge from the normalized DAG and return `PASS` — the most damaging possible output, because `PASS` is what the caller dispatches against.

So: **an unproven boundary involving dispatchable scope is a `FAIL`**, not a warning. `PASS_WITH_WARNINGS` is for warnings whose safety a reader can weigh, and this one cannot be weighed by construction — judging whether a hidden edge would change execution order requires seeing the edge. Returning it as a warning asks the caller to assess something neither of you can observe, and the caller's own policy then reads an unassessable warning as proceedable.

`PASS_WITH_WARNINGS` remains available only where the unproven boundary touches nothing dispatchable — external prerequisites read for readiness, or issues outside the authorized set. Either way, name the transport, the credential identity, and every boundary left unproven, and report the shortfall as `not visible via <transport>`, never as a missing dependency.

This is also why prose dependencies are a legitimate **mirror** rather than redundant noise. They live in issue text, so they survive transports that redact structured relationships, and a textual blocker with no visible structured edge is as likely to be evidence of a blind spot as of a missing link. Structured edges stay authoritative wherever both are visible; a mismatch is a finding to report, never a licence to trust one side by default.

Cross-repository edges deserve the most scepticism on both counts: they are the likeliest to be redacted by scoping, and their loss changes execution order the most.

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

`FAIL` means the orchestrator must not dispatch affected work until corrected. `PASS_WITH_WARNINGS` may proceed if warnings do not make execution order unsafe — which is why unproven relationship visibility over dispatchable scope is never one of those warnings: its safety is exactly what cannot be established. It is a `FAIL`.

## Mutation

Validation is read-only by default. Do not add/remove dependency links or rewrite issues unless the user explicitly asks to apply the suggested fixes.
