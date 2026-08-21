---
name: normalize-github-dependencies
description: Convert dependency relationships described in GitHub issue/sub-issue text into GitHub's native blocked-by/blocking issue dependencies. Scans a bounded issue tree or explicit issue set, compares text with existing native dependencies, validates direction/cycles, and applies only missing high-confidence relationships. Use when asked to normalize, migrate, or formalize GitHub issue dependencies.
---

# Normalize GitHub Dependencies

Convert text-described dependencies in a bounded GitHub issue set into first-class GitHub `blocked by` / `blocking` relationships.

This skill is GitHub-specific. For tracker-agnostic graph validation use `validate-backlog`.

## Inputs and scope

Accept one of:

- a GitHub parent/build-order issue, in which case scan its direct and recursive sub-issues;
- an explicit set of GitHub issue URLs;
- an explicitly bounded GitHub Project issue set when the user asks for it.

Preserve canonical full GitHub issue URLs in all reporting. Do not expand beyond the supplied tree/set merely because an issue references unrelated work. Out-of-scope referenced issues may be used as dependency endpoints when the text clearly declares them, but do not recursively normalize their other relationships.

## Dependency sources

For every in-scope issue:

1. read native GitHub `blocked by` / `blocking` relationships first;
2. read the issue body;
3. read comments when they contain scope/order clarification;
4. identify explicit dependency language, including:
   - `blocked by <issue>`;
   - `depends on <issue>`;
   - `requires <issue>`;
   - `after <issue>` / `must land after <issue>`;
   - `<issue> must land first`;
   - `blocking <issue>` / `blocks <issue>`;
   - structured sections such as `Dependencies`, `Blocked by`, `Prerequisites`, or build-order lists;
5. resolve every dependency endpoint to a canonical GitHub issue URL and GitHub issue ID before mutation.

Do not infer dependencies from mere mentions such as `related to`, `see also`, `context`, or links with no ordering semantics.

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

- `SAFE_TO_ADD` — explicit text, unambiguous direction, no conflict/cycle;
- `ALREADY_PRESENT` — native dependency already exists;
- `AMBIGUOUS` — wording does not establish direction strongly enough;
- `CONFLICT` — contradicts native metadata or would introduce a cycle;
- `OUT_OF_SCOPE_REFERENCE` — valid endpoint outside the normalized set; may still be added when explicitly declared, but do not traverse it further.

Do not mutate `AMBIGUOUS` or `CONFLICT` edges automatically.

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

If the available GitHub MCP exposes first-class issue dependency mutation, use it. If it only exposes ordinary issue updates and does **not** expose dependency mutation, do not emulate native dependencies by rewriting Markdown. Fall back to authenticated `gh`/REST if available; otherwise stop before mutation and report that dependency-write capability is unavailable in this environment.

## Confirmation and mutation policy

When invoked directly for conversion, first produce the proposed changes and then apply them if the user's request already clearly authorizes conversion/mutation. Do not require a second confirmation merely for the mechanical addition of high-confidence relationships.

Never remove existing native dependencies unless the user explicitly asks for cleanup/removal.

By default, **leave the original description text intact** after adding native dependencies. The prose may contain useful context and removing it is a separate editorial mutation. If the user asks to clean descriptions afterward, remove only redundant dependency boilerplate while preserving explanatory text.

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

Do not claim normalization succeeded unless post-write verification confirms the native dependency relationships.