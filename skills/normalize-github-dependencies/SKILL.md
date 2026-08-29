---
name: normalize-github-dependencies
description: Convert dependency relationships described in GitHub issue/sub-issue text into GitHub's native blocked-by/blocking issue dependencies. Scans a bounded issue tree or explicit issue set, compares text with existing native dependencies, validates direction/cycles, and applies only missing high-confidence relationships. Use when asked to normalize, migrate, or formalize GitHub issue dependencies.
---

# Normalize GitHub Dependencies

Convert text-described dependencies in a bounded GitHub issue set into first-class GitHub `blocked by` / `blocking` relationships.

This file is the contract; the reasoning behind its rules lives in `NOTES.md` beside it, keyed by section. NOTES explains; it never overrides.

This skill is GitHub-specific. For tracker-agnostic graph validation use `validate-backlog`.

**This skill is only useful from an environment with an authenticated `gh` CLI — in practice a local session.** It needs `gh` for *both* halves: reading existing edges to classify `ALREADY_PRESENT`/`CONFLICT`, and writing new ones. A cloud container has neither — the MCP server exposes no dependency read or write, and a raw `curl` read returns same-repo edges only, silently omitting cross-repository ones. Run from a cloud container this does not degrade gracefully (NOTES).

**Establish first that native dependency reads work here at all.** The GitHub MCP server exposes no blocked-by read (feature-flagged; [github/github-mcp-server#3145](https://github.com/github/github-mcp-server/issues/3145)), and the `curl` fallback drops cross-repository edges with no error. Both matter more to this skill than to any other, because it *writes* native edges (NOTES: what each failure converts into). So probe the read before applying anything: a known-true edge — one this run just wrote, or one the user confirmed — queried through the transport you will normalize with, **crossing a repository boundary if the set spans repositories**. If it does not come back, stop and report; never fall back to writing edges you could not check. See `validate-backlog`, *GitHub dependency reads depend on where you are running*.

## Inputs and scope

Accept one of:

- a GitHub parent/build-order issue, in which case scan its direct and recursive sub-issues;
- an explicit set of GitHub issue URLs;
- an explicitly bounded GitHub Project issue set when the user asks for it.

Preserve canonical full GitHub issue URLs in all reporting. Never expand beyond the supplied tree/set merely because an issue references unrelated work. Out-of-scope referenced issues may serve as dependency endpoints when the text clearly declares them, but never recursively normalize their other relationships.

**Scanning a parent's sub-issues is itself a hierarchy read**, so the first input form is subject to the visibility precondition below, not exempt from it (NOTES: how a truncated candidate set defeats its own validation). Cross-check the enumerated child set against the parent's own prose listing, an explicitly supplied issue set, or a second enumeration before treating it as the scope — **a differing count is a finding that stops writes**; a matching count clears nothing unless one of the enumerations had proven visibility. A second transport sharing the credential (`gh` and raw HTTP both on `GITHUB_TOKEN`) is not a cross-check: same scope, same blind spot, two coats.

## Dependency sources

For every in-scope issue:

1. read native GitHub `blocked by` / `blocking` relationships first;
2. read the issue body;
3. read comments when they contain scope/order clarification — but **skip any comment whose first line is exactly `**Worker report — unclassified evidence, not a dependency record.**`**. A report never contributes a candidate edge, at any confidence (NOTES: why an edge from a report is the most expensive to be wrong about);
4. identify explicit dependency language, including:
   - `blocked by <issue>`;
   - `depends on <issue>`;
   - `requires <issue>`;
   - `after <issue>` / `must land after <issue>`;
   - `<issue> must land first`;
   - `blocking <issue>` / `blocks <issue>`;
   - structured sections such as `Dependencies`, `Blocked by`, `Prerequisites`, or build-order lists;
5. resolve every dependency endpoint to a canonical GitHub issue URL and GitHub issue ID before mutation.

Never infer dependencies from mere mentions such as `related to`, `see also`, `context`, or links with no ordering semantics.

## Direction normalization

Represent every edge as:

```text
A -> B
```

meaning **B is blocked by A** / **A is blocking B**.

Examples:

```text
B: "Blocked by A"     => A -> B
B: "Depends on A"    => A -> B
A: "Blocks B"        => A -> B
"A before B"         => A -> B, only when clearly an implementation-order statement
```

Never add both directions separately; GitHub represents the same dependency relationship from both issue perspectives.

## Preflight before mutation

Build the complete candidate graph before writing anything.

For each candidate edge:

- verify both issues exist;
- verify it is not already represented natively;
- verify direction is unambiguous;
- reject self-dependencies;
- check that adding it does not create a dependency cycle;
- compare against existing native edges for contradiction;
- distinguish dependency statements from parent/sub-issue hierarchy — being a sub-issue does not by itself imply sequential blocking.

Classify candidates:

- `SAFE_TO_ADD` — explicit text, unambiguous direction, no conflict/cycle. Text inside a worker-report comment is never explicit text for this purpose: that exclusion happens at the read, above, so such an edge should never reach classification at all;
- `ALREADY_PRESENT` — native dependency already exists;
- `AMBIGUOUS` — wording does not establish direction strongly enough;
- `CONFLICT` — contradicts native metadata or would introduce a cycle;
- `OUT_OF_SCOPE_REFERENCE` — valid endpoint outside the normalized set; may still be added when explicitly declared, but never traversed further;
- `UNVERIFIED` — the edge looks absent, but the read that showed it absent came from a transport whose visibility is unproven (see below).

Never mutate `AMBIGUOUS`, `CONFLICT`, or `UNVERIFIED` edges automatically.

## Precondition: the read that showed the edge missing must be trustworthy

**Never create an edge because a read showed it absent, unless that read came from a validated transport.** This skill decides what to write from what it believes is missing, so a read that under-reports existing relationships converts directly into duplicate writes (NOTES: how a scoped credential's partial answer looks complete).

Before any mutation:

1. read existing relationships through the highest transport tier available — a first-class tool, else an authenticated CLI, and raw HTTP only where neither exposes dependency fields at all;
2. prove that read can see the class of edge you intend to write, using a case whose answer is known: an edge already confirmed to exist, crossing the same repository boundaries the candidate set crosses (see 4). **Required at every tier** — the hazard is the credential's scope, not the transport's shape, so a higher tier lowers the odds without removing the need to check;
3. a second read behind the same **credential** does not count — it reproduces the same blind spot and reads as confirmation, including a second read through a different transport authenticating the same way. Only a known-true case proves visibility; a second read corroborates at best, however it differs (NOTES). Absent a known-true case the boundary is unproven, and on a skill that writes, **unproven means write nothing**;
4. a control inside one repository proves that repository only. Where candidates span repositories, prove **every** boundary the write set touches — one visible A→B edge says nothing about C;
5. a proof is bound to the credential that produced it. Revalidate after a restart and on reauthentication. **An authorization error invalidates every proof bound to that credential, across every transport using it** — a 403 through `gh` condemns cached raw-HTTP proofs on the same token; revalidating just the failed boundary, or just the failed transport, keeps writing against stale controls elsewhere.

If visibility cannot be proven, report the candidate edges as `UNVERIFIED` and write nothing. Absence observed through an unvalidated transport is not evidence of absence, and the cost is asymmetric: not writing a needed edge leaves a report the user can act on; writing a duplicate of a live edge mutates a graph on the strength of a blind spot.

## Applying dependencies

Prefer GitHub's native dependency interfaces.

### With modern `gh`

For an existing issue B blocked by A:

```bash
gh issue edit <B URL> --add-blocked-by <A URL>
```

Equivalent blocking form when useful:

```bash
gh issue edit <A URL> --add-blocking <B URL>
```

Use one form for the relationship, not both.

### With GitHub REST

GitHub exposes issue-dependency REST endpoints. To make B blocked by A, POST to:

```text
/repos/{owner}/{repo}/issues/{B_NUMBER}/dependencies/blocked_by
```

with:

```json
{"issue_id": <A_DATABASE_ISSUE_ID>}
```

Use the current documented GitHub API version supported by the environment. The credential requires Issues write permission.

### With MCP

If the available GitHub MCP exposes first-class issue dependency mutation, use it. If it only exposes ordinary issue updates and does **not** expose dependency mutation, never emulate native dependencies by rewriting Markdown. Fall back to authenticated `gh`/REST if available; otherwise stop before mutation and report that dependency-write capability is unavailable in this environment.

## Confirmation and mutation policy

When invoked directly for conversion, first produce the proposed changes and then apply them if the user's request already clearly authorizes conversion/mutation. Never require a second confirmation merely for the mechanical addition of high-confidence relationships.

Never remove existing native dependencies unless the user explicitly asks for cleanup/removal.

By default, **leave the original description text intact** after adding native dependencies (NOTES). If the user asks to clean descriptions afterward, remove only redundant dependency boilerplate while preserving explanatory text.

## Post-write verification

After mutations:

1. re-read native `blocked by` / `blocking` metadata;
2. verify every `SAFE_TO_ADD` relationship now exists;
3. rerun cycle detection on the normalized graph;
4. report any edge that failed to persist;
5. leave ambiguous/conflicting edges listed for human review.

## Output

Return:

```text
Scope: 12 issues
Existing native dependencies: 8
Text dependency candidates: 11
Added: 6
Already present: 4
Ambiguous: 1
Conflicts/cycles: 0

Added:
- <A full URL> -> <B full URL>

Needs review:
- <issue URL>: "after X" may describe rollout rather than code dependency
```

Never claim normalization succeeded unless post-write verification confirms the native dependency relationships.
