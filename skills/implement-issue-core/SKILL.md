---
name: implement-issue-core
description: Implements exactly one tracked issue from its canonical full URL through code changes, local checks, durable remote checkpoints, and creation of a correctly linked PR. It does not own long-lived CI/review monitoring. Use as the implementation primitive under implement-issue or backlog-orchestrator.
---

# Implement Issue Core

Implement exactly one tracked issue to a durable PR state. A worker primitive — not a backlog scheduler, not a long-lived PR monitor.

This file is the contract. The reasoning behind each rule — incident history, arguments, and answers to "why not the obvious other reading?" — lives in `NOTES.md` beside it, keyed by these section names. Read a section's note before changing its rules or when applying them to a case the contract does not obviously cover. NOTES.md explains; it never overrides.

## Inputs

- canonical full issue URL (GitHub, Linear, or another supported tracker) — **canonical identity everywhere**; never replace it with a short key in durable state or PR-linking context;
- repository; dedicated working directory/worktree; issue branch; exact required base branch;
- optional upstream dependency context, with three markings the caller may attach: whether it is the caller's **complete** READY dependency set or a targeted answer (unmarked = targeted); the **provenance** of each edge (caller's own native read, or recorded outside native metadata from an earlier finding); and whether the read behind a complete set had **proven relationship visibility** for the boundaries in play;
- optional authorization membership — the run's bounded authorized set, or a per-blocker in/out flag;
- implementation-attempt budget;
- draft/full PR preference when supplied;
- the caller's posting-identity map when one exists — every `(transport, credential)` entry with its per-kind observations, never a caller-selected pair. Invoked standalone with no map, every transport starts `unestablished` (degraded path per `backlog-orchestrator`, *Posting identity*).

## Hard constraints

- Own exactly one issue; work only in the supplied isolated checkout when orchestrated; preserve the exact supplied base branch.
- Never broaden scope into dependency/context tickets.
- Never merge the PR.
- Never enter a long CI/review monitoring loop, **and never delegate one**: a scheduled check-in, trigger, routine, or PR-activity subscription is monitoring arranged rather than performed, and it outlives this invocation exactly as a loop would (NOTES). Return after implementation, checks, PR creation, and durable-state verification, leaving nothing armed behind you.

## 1. Read issue + repository context

Read the issue title/body and relevant comments, tracker-native parent/dependency metadata, repository `CLAUDE.md`/`AGENTS.md`, relevant specs/docs, and existing implementation patterns.

Return `BLOCKED`/`NEEDS_USER` rather than guessing when scope is materially underspecified, the supplied base is invalid, or a destructive/product decision needs approval — and `BLOCKED_EXTERNAL` where the absent work is an external prerequisite outside the authorized set, per step 2.

## 2. Dependency precondition

Establish what this issue is blocked by and whether that work exists, **before** preparing branch state. One level deep — this issue's own blockers; transitive graph work belongs to `validate-backlog` and the orchestrator. **Do this even when the caller judged the issue READY** — that judgement can be wrong in a way it cannot detect, and this is the cheapest place in the system to notice (NOTES).

### Union of three sources — never rely on one

| source | rules |
|---|---|
| **prose** — issue body AND relevant comments (`Depends on:`, `Blocked by:`, dependencies sections, build-order wording) | comments count: a blocker found after filing usually lands there. EXCLUDE any comment whose first line is exactly `**Worker report — unclassified evidence, not a dependency record.**` — it contributes no edge, ever; read it for context only (NOTES) |
| **tracker-native metadata** — through **your own probed transport**; the caller's report describes the caller's environment, not yours | the same tracker answers differently per container (GitHub MCP: no blocked-by read; authenticated `gh`: has one). Expect the environment's profile, confirm rather than assume, and report a contradicting result as a finding about the environment. The caller's classification is context, not a determination: caller says unavailable but your probe finds a read → **use it**; only your own failed probe makes this source absent. Never let raw `curl` stand in — it drops cross-repo edges silently |
| **caller-supplied dependency context** | read per its markings (Inputs) |

Each source alone has a failure mode that resembles success, and **a partial list is more dangerous than an empty one** — it presents as a complete answer (NOTES).

**Probe divergence is reported in both directions, handled differently:** you found *more* than the caller → use the read and report the caller's view was narrower. You found *less* → reporting is not enough: say explicitly that this issue's completeness rests on the caller's **earlier** read which you could not refresh, and that accepting the result requires a **contemporaneous read on the caller's side** — a caller that cannot do that must hold the result.

### Back the completeness of the set, not only its entries

Resolving every blocker you found says nothing about whether you found them all. What backs completeness:

1. **the caller marked its context complete AND reports proven visibility** behind it for the boundaries in play — backed. (An orchestrator normally has this — except a boundary reported `dependency transport unavailable`, which its preflight passes deliberately and no worker can improve on);
2. **a known-true case, read and observed** — an edge the caller confirmed crossing the same boundary, queried **through the same transport and credential you are reading dependencies with**, and returned. The observation is the proof; the edge merely existing proves nothing, and if it does not come back you found the blind spot. Nothing weaker counts — not a second read, not another transport or credential (NOTES);
3. **neither** — completeness is **unproven**, whether the set holds three blockers or none.

Where completeness is unproven:

- **a caller supplied a READY judgement but no proven view** → return `NEEDS_USER` (kind: unproven dependency view), naming the boundary; do not implement. EXCEPTION — **the boundary is `dependency transport unavailable` for you as well** (your probe found no read either): proceed as a direct invocation and carry the limitation into the report. The carve-out keys on **your** failed probe, never the caller's: a read you found but could not prove is an ordinary unproven read and gets no exemption (NOTES);
- **nothing upstream judged readiness** (direct invocation) → proceed, resolving what the set does contain, and report completeness as unproven. The PR then claims *no blocker was visible*, never *none exists*.

### Resolve each blocker's real state

Read each referenced issue directly — a plain issue read works across repositories even where dependency-endpoint reads do not.

### Gate on availability of the work, not on issue state

An open blocker does not mean unavailable work: a stacked child is dispatched precisely while its parent is implemented but unmerged — the normal case (NOTES). The availability measure depends on the dependency's class (infer the class from the issues where the caller did not supply it):

| dependency class | availability evidence |
|---|---|
| hard same-repo code dependency | implementation reachable from this checkout's base |
| shared-parent fanout **where the parent contributes code this issue's base is cut from** | reachable from this base, exactly as a code dependency |
| shared-parent fanout with a coordination-only parent; execution-only; cross-repo scheduler; external prerequisite | its own completion state — merged, released, deployed, or the issue closed as done — independent of this checkout's ancestry |

What decides the measure is whether the dependency's code is in your base, not what the edge is called.

**Unobservable measures:** where the measure a class needs is beyond what you can see (a deploy state, a release without a tag), caller-supplied context is the authority — a caller asserting satisfaction claims something it can verify and you cannot. Absent that, the answer is a third state: **`NEEDS_USER` (kind: unverifiable prerequisite)** — subject to the precedence below — naming the blocker, the measure, and why it is out of reach. Not `BLOCKED` (blocks finished work), not proceeding (the failure this gate exists to prevent).

**Not available → `BLOCKED` or `BLOCKED_EXTERNAL`**, and what you found determines the report:

| why it is not available | report |
|---|---|
| code dep: an open, unmerged PR implements it | name that PR — a restack the caller can act on, not a dead end |
| code dep: merged, but not reachable from the supplied base | name the merge and the base — a wrong-base repair, not a missing dependency |
| non-ancestry dep: not yet complete by its own measure | name the blocker and its actual state — a wait; no restack fixes it |
| no implementation anywhere | name each unmet blocker by canonical full URL — a real gap |

**`BLOCKED_EXTERNAL` only when EVERY unmet blocker sits outside the authorized set** — whatever its class. Membership decides the outcome; class decides only the measure. Membership is a fact about the caller's run, observable only if the caller said so: where membership was not supplied, **default to `BLOCKED`**, and never infer non-membership from the blocker living in another repository or tracker (NOTES).

### Mixed blockers take the stronger outcome

Rank by what the caller loses if this outcome is the only one it sees:

1. **any unmet in-scope blocker → `BLOCKED`** — the graph correction another outcome would suppress;
2. **otherwise unproven set completeness where a caller judged readiness → `NEEDS_USER`, kind: unproven dependency view** — EXCEPT where your own probe also found no dependency read, which ranks nothing and is not an outcome (keyed on your probe, not the caller's; without this exception every orchestrated issue on such a tracker deadlocks). It outranks what follows because every sibling judged READY through that read shares the blind spot, and it forbids the weaker conclusions below;
3. **otherwise any unverifiable prerequisite → `NEEDS_USER`, kind: unverifiable prerequisite**;
4. **otherwise, every unmet blocker external → `BLOCKED_EXTERNAL`** — a known wait.

**Report all of them regardless of which outcome won** — an unverifiable prerequisite under a `BLOCKED` still needs its question asked, and unproven completeness reported under one still invalidates the caller's visibility proof — EXCEPT where neither probe found a dependency read: then it invalidates nothing (no proof was ever in play; the report restates the run's own condition). Where **you** found a read and could not prove its reach, that is a truncated read like any other and it does invalidate (NOTES).

### Assertions vs observations

- **Observation beats a "satisfied" assertion — where you observed the right thing.** Caller context settles only what you cannot check: where it asserts a blocker satisfied and **the class's own availability measure** says otherwise, the observation wins and the disagreement is reported. The class qualifier is load-bearing: unreachability contradicts "satisfied" only for a code dependency — never for execution-only, cross-repo, or external edges, whose measure was never reachability.
- **The inverse does not flip.** Where the caller asserts a blocker *unmet* and you observe the work available, the caller's assertion stands: block, and report the disagreement. Availability is presence; "unmet" may be a claim about soundness (a merge pending revert, a known-bad implementation) that presence does not refute (NOTES).
- **Never implement against a contract that does not exist yet** to keep busy: a UI ticket with a missing backend renders what exists, stubs the rest, passes mocked tests, and produces a PR that looks complete and is not.

### Report what you found

- A dependency named in prose that native metadata did not return is a **finding**, not a discrepancy to reconcile silently — either a missing native edge or a transport that cannot see one.
- **Where no dependency read is available** (your probed transport returns no edge set), the membership rules do not apply — "prose has it, native lacks it" would be true of every prose blocker and would manufacture false visibility disagreements at scale. Report instead: native was **unreadable**, prose is the whole of the evidence, completeness is **unproven** — an unwritten blocker is then undetectable by construction, and saying so is the finding. Where a read *is* available these rules apply in full, GitHub included.
- Reconcile caller context against what you found and report any disagreement — the caller's view being wrong is the information worth returning.

## 3. Prepare durable branch state

Before substantial implementation:

1. verify/fetch the exact required base;
2. verify the assigned branch/worktree descends from it;
3. create the issue branch if it does not exist;
4. **push the issue branch to the remote immediately**, even empty, so restart logic has a durable branch identity.

Follow repository branch naming conventions; prefer including the issue key/number where conventions allow (improves recovery), never violating documented naming rules to do so.

## 4. Implement with remote checkpoints

Implement only the issue scope; run required local checks.

- **Commit before you check, not after.** Once an edit is complete, commit and push before any typecheck/lint/test run — checks take minutes, and those are the minutes a container disappears in (NOTES).
- A commit is a save, not a claim of correctness: green is not a precondition, and neither is coherence. Prefer coherent checkpoints; never defer a push to obtain one.
- Checkpoint after meaningful coherent milestones (schema/API portion, component/service, tests added, before a long debugging phase). Goal: bounded loss — at most the work since the last checkpoint.
- Never checkpoint secrets, generated junk, or unrelated files; commit only issue-owned paths; push each checkpoint to the issue branch; no heartbeat commits for every tiny edit; never enter a long check or debugging phase with completed edits uncommitted. WIP history is fine — squash-merge removes it.
- Under an orchestrator, expect the parent to inspect this worktree and commit on your behalf where completed work is held back (NOTES).
- A retry uses only the caller's remaining budget. Return a reasoning-heavy repeated failure to the caller — never escalate models autonomously.

## 5. Final local verification

Commit and push the implementation first, then run the repository-required typecheck/lint/format/tests. Fix in-scope failures within budget, committing each fix as it lands. Push the final implementation commit.

## 6. Create and verify PR

Invoke `create-pr` with:

- canonical full issue URL; exact required base; tracker identity when useful; draft/full preference when supplied;
- **any coverage finding this implementation carried** — a declared dependency satisfied on paper whose capability was absent, and the acceptance criteria left unmet. `create-pr` decides the linkage form from this and cannot decide correctly unseen: the default is a closing keyword, so silence auto-closes an issue you knowingly did not finish (NOTES);
- **the posting-identity map as this skill holds it** — every entry, as received or `unestablished`. An invocation is read literally: a map left out is a map `create-pr` does not have, and its writes need different entries (agent-authored for the PR; invoking-user for the review trigger), so omitting it degrades both (NOTES).

`create-pr` owns tracker linkage, stack `Depends on:` metadata, review-trigger policy, and creation.

After creation verify durable state: PR exists; head/base correct; canonical linkage correct **and in the form the coverage finding required** (closing keyword only where fully implemented); remote head contains the final pushed state.

Then return. Do not wait for CI or review, and do not arrange for anything else to wait on your behalf (see Hard constraints) — the caller supervises this PR.

## Output

Return structured state:

- canonical issue URL; tracker; repository; working directory;
- outcome: `PR_OPEN` | `BLOCKED` | `BLOCKED_EXTERNAL` | `FAILED` | `NEEDS_USER`;
- branch; base branch; PR URL/number; remote head SHA;
- issue linkage verified yes/no, and the form emitted — closing keyword, or non-closing `Part of:` because a coverage finding was reported;
- **whether the blocker set's completeness was backed** — by a caller's proven complete set, or a known-true case read and observed — **or left unproven, and on what boundary.** This line is the only place the narrower-claim distinction survives (NOTES);
- the transport tier used for relationship reads and a **non-secret identity of the credential** behind it (authenticated account and scopes; never the credential) — what turns a caller/native mismatch into a cross-credential demonstration;
- dependencies checked: per blocker — canonical full URL, which sources named it, **the class judged under**, and how it resolved by that class's measure (code dep: reachable / open PR with URL / merged-but-unreachable with merge and base; non-ancestry: complete / incomplete with state / **unverifiable, naming the out-of-reach measure**; or unmet), plus any caller assertion the observation contradicted. The class tells the caller which measure applied — whether a block is a base problem, a wait, or a real gap;
- **source disagreements, as two distinct kinds, never collapsed** (NOTES: why a caller that cannot tell them apart over-responds):
  - **visibility** — sources disagree about **which edges exist**. Report the edge with the sources that had it against those that lacked it. Only a source claiming exhaustiveness can contribute an absence: native metadata claims it (where a native edge set exists at all — where your transport returned none, report native unreadable instead and make no membership claims); caller context claims it only when marked complete (unmarked context is a targeted answer contributing edges and assertions, never absences; an edge marked recorded-outside-native is one your read is *supposed* to lack); prose claims nothing. So prose-has-it-native-lacks-it is a disagreement; native-has-it-prose-lacks-it is not;
  - **availability** — a mismatch against caller-supplied context, **in either direction, naming which**: satisfied-but-observed-otherwise (its base or completion claim no longer holds — say "no longer holds", not "was wrong": it may have been overtaken by a revert or force-push), or unmet-but-found-available (its constraint may be obsolete). Report both even on a successful run;
- draft state as created, exactly as `create-pr` reported it;
- the posting identities `create-pr` observed, **every entry under its `(transport, credential)` key, carried through unchanged** — invoking-user and `unestablished` entries included. This is an observation about *writes*, distinct from the read-side credential identity above, and the caller cannot re-derive it: your transports are not its transports;
- checkpoints pushed (count/SHAs when useful); checks run; implementation attempts used;
- blocker/failure details;
- on `NEEDS_USER`, **which kind** — unverifiable prerequisite, or unproven dependency view — and the recommended user action. The kinds demand opposite caller responses, and inferring the kind from an empty blocker list is how the expensive one gets handled as the cheap one.
