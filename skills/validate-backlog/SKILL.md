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

1. enumerate the bounded issue set from the supplied manifest/root/explicit issue set — noting that for a root/parent invocation this enumeration *is* a hierarchy read, so it is subject to the visibility gate at check 3 rather than exempt from it;
2. **probe the dependency transport** — see *GitHub dependency reads depend on where you are running* below for what the probe is and what each outcome means. It is cheap, it is environment-specific, and every rule downstream keys off its result, **including the visibility gate in the next step**. It sits ahead of that gate deliberately: a checklist is executed in order, and a validator that reaches the gate first has to judge an unproven boundary before knowing whether a readable transport exists to prove it against;
3. **establish that the transport can see the relationships you are about to read**, including the ones enumeration just consumed — see Transport visibility below. This gates the whole check, not just the mismatch case, and the enumerated scope is not permitted to define its own boundary list; **Consume step 2's result here rather than re-deriving it, and scope it strictly:** where the probe found no dependency read, the **blocker-edge** boundary is classified `dependency transport unavailable` and is explicitly not a `FAIL` — see the results rules below. This gate is fatal for a transport that should return relationships and may be returning a subset; it was never meant to fire on a capability that does not exist, and firing there would halt every such run before the classification could be reached.

   **The exception covers blocker edges and nothing else.** Hierarchy is a different transport with a different answer — on GitHub the MCP server reads sub-issues perfectly well while exposing no blocked-by read at all — so a failed dependency probe says nothing about whether enumeration was complete. Treating one class as excusing the other is the more dangerous direction of the two: a truncated hierarchy read silently shortens **the authorized set itself**, and issues that never entered scope are not blocked, they are invisible, so nothing downstream ever notices them missing. Hierarchy visibility stays independently required and unproven hierarchy over dispatchable scope stays a `FAIL`, whatever the dependency probe returned.
4. read native parent/sub-issue hierarchy where the tracker supports it;
5. read native `blocked by` / `blocking` dependency relationships **through whatever transport step 2 found working** — on GitHub that is an authenticated `gh issue view <url> --json blockedBy,blocking`, since the MCP server exposes no such read; where step 2 found none, this source is absent and the run is classified `dependency transport unavailable`. Do not decide readability from the tracker's name, in either direction;
6. scan issue bodies/comments for textual dependency phrases and linked issue URLs, including `blocked by`, `depends on`, `after`, `requires`, `prerequisite`, `must land first`, and equivalent wording;
   - **skip any comment whose first line is exactly `**Worker report — unclassified evidence, not a dependency record.**`.** That is a previous worker's persisted report on that issue, not a statement about the issue's dependencies, and it necessarily contains dependency URLs — so scanning it puts an edge the orchestrator already classified as stale back into the normalized DAG, on every validation from then on, with the report as its source. `implement-issue-core` excludes the same comments from its dependency union; this check runs earlier and would otherwise reintroduce the edge before that exclusion ever applies. Whatever the report observed, it observed in the issue's own prose, which this check reads anyway;
7. compare structured dependencies against text-described dependencies;
8. detect cycles, missing issue targets, contradictory ordering, closed/cancelled prerequisite inconsistencies, orphaned children, duplicates, and links outside the authorized scope;
9. distinguish an external prerequisite from an authorized implementation issue;
10. report whether the graph is safe to execute without guessing.

Structured dependency metadata is authoritative when present, but textual descriptions remain a secondary consistency signal. A textual blocker absent from structured metadata should be flagged as a likely missing dependency rather than silently ignored.

### GitHub dependency reads depend on where you are running

**The transport question is settled by the environment, and the two common environments have opposite capability profiles.** Not a preference order with fallbacks — a disjoint split, which is why the same tracker gives contradictory answers to two agents looking at the same issue on the same day.

| | GitHub MCP | `gh` CLI | dependency edges |
|---|---|---|---|
| **cloud container** (a Claude Code web/remote session, and the workers it dispatches) | present | **absent** | **none readable** |
| **local session** | absent | present, authenticated, **cross-repo** | **fully readable** |

The MCP server exposes no blocked-by read at all — it is behind a feature flag, tracked upstream at [github/github-mcp-server#3145](https://github.com/github/github-mcp-server/issues/3145) — so a cloud container has the interface that cannot answer and lacks the one that can. A local session is the mirror image: no MCP, but `gh issue view <url> --json blockedBy,blocking` returns edge identities, and its credential reaches across repositories.

So **know which you are in, then confirm it — the probe verifies an expectation rather than discovering a capability**, and a result that contradicts the table above is itself worth reporting. Confirm with the read, not with `command -v gh`: presence is not authentication, and authentication is not cross-repo permission. `gh issue view <url> --json blockedBy,blocking` against an in-scope issue settles all three at once, and where the set spans repositories the confirming case must **cross a repository boundary** — a credential can return same-repo edges perfectly while silently dropping cross-repo ones.

**A raw `curl` read is a third state, and the most dangerous one, because it answers.** From a cloud container it does return blocked-by edges — but **only same-repository ones**, dropping cross-repository edges with no error and no indication anything was omitted. A partial answer wearing the shape of a complete one, on exactly the edges a multi-repo backlog turns on.

So it is usable **only where the authorized scope lives in a single repository**, and then only with that limit recorded. The moment the scope spans repositories it is worse than no read at all: an absent read classifies honestly as `dependency transport unavailable` and every downstream rule handles that, while a curl read reports a complete-looking edge set that quietly excludes the cross-repo blockers — and nothing downstream has reason to doubt it. Prefer the honest absence.

Three consequences that follow from the split rather than from GitHub:

- **A cloud run's graph is strictly poorer than a local one's**, and knowing this is what stops a cloud run reporting the weaker graph in the same terms as the stronger. A READY computed from prose alone is a narrower claim than one computed from a corroborated graph.
- **A parent and its workers can sit on different sides of the table, but usually do not.** **Both-cloud is first-class usage and the case to protect**: a cloud orchestrator dispatching cloud workers, where neither side reads dependency edges and the limitation is symmetric. A local orchestrator dispatching cloud workers is a real mix the rules must handle — a proven view up top its workers cannot reproduce — but it is not the common shape, and the symmetric case must not be written as an exception to it.
- **This changes when the flag ships.** Re-confirm rather than trusting the table: it describes 2026-08-25, and the upstream issue is being worked on.

**Record the confirmed transport state and pass it to everything downstream, because the whole system keys off it and none of it can probe on the caller's behalf.** The rules elsewhere are written against *what the transport returned*, never against the word "GitHub" — a tracker name is not a capability. Report which transport answered and what it could see, and let the orchestrator carry that into every dispatch prompt.

**Where no dependency read is available, the issue body and its comments are the only reliable source of what blocks an issue.**

**Where the probe classified the transport `dependency transport unavailable`** — and only then, never merely because the tracker is GitHub:

- **Read prose properly** — body and comments both, since a blocker found after filing is usually a comment. It carries the identity and nothing else does.
- **Never report "prose has it, native lacks it" as a visibility disagreement.** Native could not have named it. That comparison would fire for every prose-named blocker on every issue, and each false positive invalidates a visibility proof and halts sibling dispatch.
- **Record the completeness of every blocker set in scope as unproven**, and say why: no native source exists to corroborate prose, so an unwritten blocker is undetectable by construction. This is honest rather than paralysing — the skill already carries unproven completeness through to the caller as a judgement rather than a stop.
- **A visibility proof over that dependency boundary cannot be established at all.** There is no read to demonstrate. Do not substitute a hierarchy or issue read that happens to succeed: those prove that *some* call works, which was never in doubt, and dressing that up as a relationship proof is how a run convinces itself it can see a graph it cannot.

**Where the probe found a working read — an authenticated `gh`, or MCP once the flag ships — none of the four applies.** The three-source union works as written, membership comparisons are meaningful, and a visibility proof is both possible and required: prove it across a repository boundary if the set spans repositories. Linear is in this branch too, since it exposes real relationship reads.

Everything above is a statement about a probed transport, never about a tracker. The same tracker lands in different branches in different containers, which is why the classification travels with the result instead of being re-derived from the tracker's name downstream.

### Transport visibility

A scoped or relayed credential can return a partial relationship set without error — the entries it cannot reach are absent rather than refused — so an edge that exists but is invisible looks identical to one that was never created. Establish that the transport can see the relationships in scope **before consuming them**, against **a case whose answer is already known** — an edge the caller confirmed, or one this run just wrote. Only a known-true case can establish the proof, because its answer does not depend on any transport being trustworthy.

A second read is not a substitute, whatever distinguishes it. A read behind the same credential reproduces the same blind spot and returns looking like confirmation, which is worse than reading once; two different transports do exactly that when they authenticate the same way (`gh` and raw HTTP on one `GITHUB_TOKEN`); and two different credentials can still share insufficient scopes, a repository boundary, or a relationship transport. Each of those is a proxy for independent visibility and each can coincide with a shared blind spot, so a second read corroborates at best and never proves. Where no known-true case is available, the boundary is unproven — say so rather than promoting agreement into a proof. Cover **every** boundary the graph crosses, not one of them. A control inside a repository proves that repository only, and for a graph spanning A, B and C a visible A→B edge says nothing about C — so a single cross-repository control is enough to make a credential that cannot reach C look proven, while A→C and B→C vanish. One control per boundary in scope.

Bind each proof to the credential that produced it — a non-secret identity such as the authenticated account and its scopes, never the credential itself — and revalidate after a restart and on reauthentication, since a rotated or narrowed credential makes a stale proof read as applicable. An authorization error invalidates **every proof bound to that credential, across every transport using it** — not only the failed call, and not only the transport it arrived on. Grants narrow server-side, so a failure through one transport condemns the cached proofs of every other transport sharing the token, even though none of them has failed yet.

**Enumeration is itself a relationship read.** For a parent/root invocation, check 1 discovers the bounded set *through* native hierarchy — so a credential that hides children in one repository yields a truncated scope, and every later step inherits it. The boundary list then comes from the same truncated data, so the missing repository is never tested, never reported, and the result can still be `PASS`. A scope derived from a possibly-partial read cannot bound its own validation.

So the boundary list must not come only from enumerated data. Establish it from something independent: the issue set the caller supplied, the root/manifest's own prose listing of its children — a legitimate mirror for exactly this reason, since text survives transports that redact structured relationships — or a second enumeration compared against the first. A differing count is the finding; a matching count is not a check, from the same credential or a different one, since two reads sharing a blind spot agree about exactly what neither can see. Where the scope can only be derived from one unproven transport, that is itself the finding: report it and do not return `PASS`.

Do this before reading, not only when something looks wrong. A hidden edge with no prose mirror produces no mismatch to investigate, so a check that validates visibility only on disagreement will omit that edge from the normalized DAG and return `PASS` — the most damaging possible output, because `PASS` is what the caller dispatches against.

So: **an unproven boundary involving dispatchable scope is a `FAIL`**, not a warning. `PASS_WITH_WARNINGS` is for warnings whose safety a reader can weigh, and this one cannot be weighed by construction — judging whether a hidden edge would change execution order requires seeing the edge. Returning it as a warning asks the caller to assess something neither of you can observe, and the caller's own policy then reads an unassessable warning as proceedable.

`PASS_WITH_WARNINGS` remains available where the unproven boundary touches nothing dispatchable — external prerequisites read for readiness, or issues outside the authorized set — **and in one further case, which is different in kind from the one the gate exists for.**

**Unproven-because-untested and unavailable-by-construction are not the same finding.** The gate above is aimed at a transport that *should* return edges and may be silently returning a subset: there, the caller is asked to weigh a risk whose size is unobservable, on a graph where some issues may be affected and others not, and no honest assessment is possible. Where the tracker exposes **no dependency read at all** — GitHub today, see *GitHub dependency reads depend on where you are running* — none of that holds. Nothing is silently short, because nothing was returned. The limitation is **uniform** across every issue in the tree, **permanent** until the capability ships, and **precisely known**: prose is the declared source and the graph is exactly as complete as prose makes it.

So that case returns `PASS_WITH_WARNINGS` under a named warning class — **`dependency transport unavailable`** — carrying the tracker, the reason, and any upstream tracking reference. Treating it as `FAIL` would not make the run safer; it would stop **every** GitHub backlog permanently, on a gap no amount of re-reading will close, which is refusal dressed as rigour. What the warning must never be allowed to become is silent: it belongs on the run's state, in every dispatch prompt, and in the report, so that a reader is told the graph rests on prose alone rather than discovering it. Either way, name the transport, the credential identity, and every boundary left unproven, and report the shortfall as `not visible via <transport>`, never as a missing dependency.

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

`FAIL` means the orchestrator must not dispatch affected work until corrected. `PASS_WITH_WARNINGS` may proceed if warnings do not make execution order unsafe — which is why unproven relationship visibility over dispatchable scope is never one of those warnings: its safety is exactly what cannot be established. It is a `FAIL`. **The single exception is the named `dependency transport unavailable` class**, where the tracker exposes no dependency read at all: there the limitation is uniform, permanent and precisely known rather than unassessable, so it is `PASS_WITH_WARNINGS` carrying that class. Emitting `FAIL` for it would make this contract unsatisfiable on GitHub.

## Mutation

Validation is read-only by default. Do not add/remove dependency links or rewrite issues unless the user explicitly asks to apply the suggested fixes.
