---
name: implement-issue-core
description: Implements exactly one tracked issue from its canonical full URL through code changes, local checks, durable remote checkpoints, and creation of a correctly linked PR. It does not own long-lived CI/review monitoring. Use as the implementation primitive under implement-issue or backlog-orchestrator.
---

# Implement Issue Core

Implement exactly one tracked issue to a durable PR state. This is a worker primitive, not a backlog scheduler and not a long-lived PR monitor.

## Inputs

Accept:

- canonical full issue URL (GitHub, Linear, or another supported tracker);
- repository;
- dedicated working directory/worktree;
- issue branch;
- exact required base branch;
- optional upstream dependency context, and whether the caller marks it as its **complete** dependency set or a targeted answer — the two are read differently, and unmarked means targeted. Also the **provenance** of each edge in it: produced by the caller's own native read, or recorded outside native metadata from an earlier finding. And whether the read behind a complete set had **proven relationship visibility** for the boundaries in play: a complete set from an unproven read claims to list every edge the caller could see, which is a different claim from listing every edge there is;
- optional authorization membership — the run's bounded authorized set, or a per-blocker flag saying whether each is inside it;
- implementation-attempt budget;
- draft/full PR preference when supplied.

The full issue URL is canonical identity. Never replace it with a short issue key in durable state or PR-linking context.

## Hard constraints

- Own exactly one issue.
- Work only in the supplied isolated checkout/worktree when orchestrated.
- Preserve the exact supplied base branch.
- Never broaden scope into dependency/context tickets.
- Never merge the PR.
- Never enter a long CI/review monitoring loop, and never delegate one either. A scheduled check-in, a trigger or routine, or a PR-activity subscription is monitoring arranged rather than performed, and it outlives this invocation exactly as a loop would. Return after implementation, checks, PR creation, and durable state verification, leaving nothing armed behind you.

## 1. Read issue + repository context

Read the issue title/body, relevant comments, tracker-native parent/dependency metadata, repository `CLAUDE.md`/`AGENTS.md`, relevant specs/docs, and existing implementation patterns.

Return `BLOCKED`/`NEEDS_USER` rather than guessing when scope is materially underspecified, the supplied base is invalid, or a destructive/product decision needs approval — and `BLOCKED_EXTERNAL` where the absent work is an external prerequisite outside the authorized set, per step 2.

## 2. Dependency precondition

Establish what this issue is blocked by, and whether that work exists, before preparing branch state. One level deep — this issue's own blockers. Transitive graph work belongs to `validate-backlog` and the orchestrator.

Do this even when a caller judged the issue READY. That judgement was computed from a dependency read that can be wrong in a way it cannot detect, and this is the cheapest place in the system to notice.

### Take the union of three sources

- dependencies named in prose — the issue body **and its relevant comments**: `Depends on:`, `Blocked by:`, a `Dependencies` section, build-order wording. Comments matter as much as the body, since a blocker discovered after filing is usually added as a comment rather than an edit, and step 1 has already read them;

  **One class of comment is excluded: a comment whose first line is exactly `**Worker report — unclassified evidence, not a dependency record.**`** That is a previous worker's report on this same issue, left there by older tooling or an earlier dispatch convention because its runtime gave its return value nowhere to go — current orchestration routes reports to the worker's PR, never the issue, so the marker is a backstop rather than a destination. It records what that worker *observed*, before anyone judged whether the relationship was real or stale — so reading it as prose that names a dependency would let an edge the caller already rejected block this issue again, and again on every later dispatch. Nothing is lost by excluding it: an edge it mentions was observed *in the issue's own prose*, which this step reads anyway. What the report adds beyond that — a classification, an established blocker — it is precisely not entitled to add.

  Read it for context if useful. It contributes no edge to the union.
- tracker-native dependency metadata — **on GitHub this returns counts and never edge identities**, and only via `issue_read(method='get_sub_issues')` on the issue's *parent*; `issue_read(method='get')` on the issue itself returns no dependency data whatever. So a native read cannot tell you *which* issue blocks this one, prose is the only source of that identity, and a non-zero `total_blocked_by` with nothing in prose is an unidentified blocker to report rather than a set you can resolve. Read `total_blocked_by`, not `blocked_by` — they differ, and the short one omits already-closed blockers. See `validate-backlog`, *GitHub: dependency edges are counts, not identities*;
- dependency context the caller supplied.

Never rely on one alone, because they fail in different directions. Prose goes stale the moment someone edits a ticket without updating it. Native metadata can be truncated by a scoped or relayed credential, which returns a partial list with a success status and no warning — and **a partial list is more dangerous than an empty one**, because it presents as a complete answer. One blocker returned where four exist reads as "nearly ready" and suppresses exactly the doubt that would have sent you looking elsewhere. Individually each source has a failure mode that resembles success; together they are hard to fool.

### Back the completeness of the set, not only its entries

Resolving every blocker you found says nothing about whether you found them all, and it is completeness that readiness depends on.

Three sources are hard to fool only while they carry information. Where prose names nothing and no caller context arrived, the union collapses to a single native read: the sources agree because two are silent, not because they corroborate. And a union with entries in it is not the safe case — **a partial list is more dangerous than an empty one**, exactly as above, so a read that returned one blocker has supplied no evidence that it returned the rest. Finding a blocker is not backing.

So establish what backs the set's completeness:

- **the caller marked its context complete and reports the read behind it as having proven visibility** for the boundaries this issue's blockers could cross — backed. An orchestrator normally has this by its own contract: an unproven boundary over dispatchable scope is a `FAIL` at its preflight, so a dispatch either carries a proven view or should not have happened;
- **a known-true case, read and observed** — an edge the caller confirmed crossing the same boundary, which you query **through the same transport and credential you are reading dependencies with**, and which comes back. Having such an edge available proves nothing; the observation is the proof. If it does not come back you have found the blind spot rather than ruled it out, and that is a finding. Nothing weaker establishes this: not a second read, not another transport or credential, for the reasons the orchestrator's proof rules give at length;
- **neither** — completeness is unproven, whether the set holds three blockers or none.

In that last case, what to do turns on whether anything upstream computed readiness from a graph:

- **a caller supplied a READY judgement but no proven view** — return `NEEDS_USER`, naming the boundary, and do not implement. Its own rules required a proven view before dispatch, so the mismatch is upstream information it needs more than it needs this PR, and one confirmed edge or a marked-complete context settles it.
- **nothing upstream judged readiness** — a direct invocation on one issue. Proceed, resolving whatever the set does contain, and report the completeness as unproven. Refusing every issue whose dependency view cannot be proven would refuse nearly all of them, which is the same error as gating on issue state; the invocation is the authority here. What the report must not do is let the PR make the stronger claim — no blocker was visible, not none exists.

### Resolve each blocker's real state

Read each referenced issue directly. A plain issue read works across repositories even where dependency-endpoint reads do not, so a cross-repository blocker stays checkable when the edge that should have declared it is invisible.

### Gate on availability of the work, not on issue state

An open blocker does not mean the work is unavailable. A stacked child is dispatched precisely while its parent is implemented but unmerged — that is the normal case, not an error. Gating on "the blocker is still open" would refuse nearly every stacked child and be worse than no gate at all.

**What counts as available depends on the kind of dependency.** Git reachability is the right test only for an edge whose code this issue builds on. An execution-only ordering, a cross-repository scheduler dependency, or an external prerequisite is *never* reachable from this checkout — not even when it is entirely finished — so testing those by reachability would block every one of them and misreport a completed cross-repo dependency as a wrong base. Use the classes the orchestrator already defines (hard same-repo code dependency, execution dependency only, shared-parent fanout, cross-repo scheduler dependency, external prerequisite), inferring the class from the issues where the caller did not supply it.

| dependency class | availability evidence |
|---|---|
| hard same-repo code dependency | its implementation is reachable from this checkout's base |
| shared-parent fanout, **where the parent contributes code that this issue's base is cut from** | reachable from this base, exactly as a code dependency — the parent being unmerged is the normal state for a stacked child, and waiting for it to merge would defeat the parallel dispatch the topology exists for |
| shared-parent fanout with a coordination-only parent, execution-only, cross-repo, external prerequisite | its own completion state — merged, released, deployed, or the issue closed as done — independent of this checkout's ancestry |

The split inside shared-parent fanout is the point: what decides the measure is whether the dependency's code is in your base, not what the edge is called. A parent that carries code your base was cut from is a code dependency by any useful definition; a parent that only groups tickets is not a code dependency at all.

Some of those measures are not observable from an issue and a repository. A merge or a closed issue is; a deployment usually is not, and a release only where the repository carries the tag. Where the measure a class needs is beyond what you can see, caller-supplied context is the authority — a caller asserting the prerequisite is satisfied is claiming something it can verify and you cannot.

Absent that, the answer is neither available nor unavailable, and that third state gets its own outcome: **`NEEDS_USER`** — subject to the precedence below, since an in-scope blocker found elsewhere on the same issue outranks it — naming the blocker, the measure, and why it is out of reach. Not `BLOCKED`, because treating an unobservable measure as unmet blocks finished work and invites a caller to go looking for a dependency gap that may not exist. Not proceeding, because treating it as met is the failure this whole gate exists to prevent. A person can check a deploy dashboard in seconds; the value here is asking them rather than guessing in either direction.

Answer by observation, not by claim, and the answer has three values rather than two. Available — proceed. Not determinable — `NEEDS_USER`, per the observability rule below. Not available — return `BLOCKED`, or `BLOCKED_EXTERNAL` per the rule below that, and what you found determines what to report, which is the useful part:

| why it is not available | report |
|---|---|
| code dependency: an open, unmerged PR implements it | name that PR — the work exists and is not available *here*, so this is a restack the caller can act on, not a dead end |
| code dependency: merged, but that merge is not reachable from the supplied base — it landed on another branch, or this base is obsolete | name the merge and the base — the caller calculated the wrong base, which is a different repair from a missing dependency |
| non-ancestry dependency: not yet complete by its own measure | name the blocker and the state it is actually in — waiting on a release or a deploy is not a base problem and no restack fixes it |
| no implementation anywhere: nothing merged, no open PR, nothing in the base | name each unmet blocker by canonical full URL — a real dependency gap |

Return `BLOCKED_EXTERNAL` rather than `BLOCKED` **only when every unmet blocker sits outside the authorized set** — whatever its class. Membership decides the outcome; class decides only the availability measure, and conflating the two leaves a same-repo code dependency pointing at an unauthorized issue with no outcome at all. A worker that recovers an omitted edge aiming outside the bounded set hits exactly that case. The caller routes the two differently and only one of them means its readiness computation was wrong: waiting on work nobody in this run was authorized to do is a known state, not a graph error, and reporting it as one sends the caller off re-deriving a frontier that was correct.

"Outside the authorized set" is a fact about the caller's run, not about the issue, so it is only observable if the caller said so. Where authorization membership was supplied, use it. Where it was not — a standalone invocation has no bounded set — **default to `BLOCKED`**: an external-looking prerequisite the root did in fact authorize would otherwise be reported as an out-of-scope wait, and the caller would skip the frontier re-derivation an in-scope blocker requires. Never infer non-membership from the blocker living in another repository or another team's tracker; that is what "external" looks like from here whether or not it is in scope.

**Mixed blockers take the stronger outcome**, across all the block-ish outcomes rather than only the two external ones. One outcome cannot describe several states, so rank them by what the caller loses if that outcome is the one it sees:

1. **any unmet in-scope blocker → `BLOCKED`.** A graph correction is the only response that another outcome would suppress: the caller reads `NEEDS_USER` and `BLOCKED_EXTERNAL` as *not* graph errors and may skip re-deriving its frontier, so choosing either would lose the correction entirely;
2. **otherwise unproven set completeness, where a caller judged readiness → `NEEDS_USER`, kind: unproven dependency view.** It outranks what follows because it is the only one whose consequence is not confined to this issue: every sibling judged READY through that read shares the blind spot. It also forbids the conclusions below — "just a known external wait" is not available from a set you cannot trust to be complete. On a direct invocation this is a report line rather than an outcome, so it does not enter the ranking at all;
3. **otherwise any unverifiable prerequisite → `NEEDS_USER`, kind: unverifiable prerequisite.** A question a person answers in seconds, which nothing else in the report will prompt;
4. **otherwise, every unmet blocker external → `BLOCKED_EXTERNAL`.** A known wait.

Report all of them regardless of which outcome won. The ranking exists because a single value cannot carry three states, not because the others stopped mattering — an unverifiable prerequisite reported under a `BLOCKED` still needs its question asked, and unproven completeness reported under one still invalidates the caller's visibility proof. The reverse precedence would let a single external prerequisite mask an in-scope dependency the caller's graph got wrong — the caller would skip the frontier re-derivation, and its siblings would stay scheduled against a graph already known to be incomplete. Choose the outcome that demands the most of the caller; the per-blocker detail carries the rest.

Externality changes what the block *means*, not whether a source disagreement is worth reporting. A prerequisite some source named that the native read did not return is still evidence about the transport, external or not — report the disagreement either way.

**Observation beats assertion — where you observed the right thing.** Caller-supplied dependency context settles only what you cannot check, so where it asserts a blocker is satisfied and **the availability measure for that dependency's class** says otherwise, the observation wins and the disagreement is reported. Deferring to the assertion would disable this reconciliation exactly when it matters — when the caller chose the wrong base — and would trade a restack the caller could act on for an implementation built without its dependency.

The class qualifier is load-bearing, not a hedge. Overriding a satisfied assertion because a dependency is not Git-reachable, when that dependency is execution-only, cross-repository or external, blocks a prerequisite that is complete — reachability was never its measure. Unreachability is only contrary evidence for a code dependency.

**The inverse does not flip.** Where the caller asserts a blocker is *unmet* and you observe the work is available, the caller's assertion stands: block, and report the disagreement. That is not inconsistent with the rule above, because the two observations are about different things. Unavailability is a fact that refutes "satisfied". Availability is a fact about presence, and "unmet" may be a claim about soundness — a merge pending revert, a known-bad implementation, a semantic incompatibility the worker cannot see from the code being there. Presence does not refute it. The cost asymmetry agrees: a needless block costs a cycle, while building against something the caller knows is unsound costs a wrong PR and everything stacked on it.

Never implement against a contract that does not exist yet in order to keep a worker busy. The behavioural catch in step 1 — blocking when required work is absent — only fires when the absence breaks the code. A UI ticket whose backend is missing will render against the parts that do exist, stub the rest, pass its mocked tests, and produce a PR that looks complete and is not.

### Report what you found

A dependency named in prose that native metadata did not return is a finding, not a discrepancy to reconcile silently. It means either a missing native edge or a transport that cannot see the one that exists. Surface it either way: this worker is already reading both sources for one issue, which makes it the cheapest detector in the system for a blind spot the orchestrator cannot see from above.

Where the caller supplied its own dependency context, reconcile it against what you found and report any disagreement. The caller's view being wrong is the information worth returning.

## 3. Prepare durable branch state

Before substantial implementation:

1. verify/fetch the exact required base;
2. verify the assigned branch/worktree descends from it;
3. create the issue branch if it does not exist;
4. **push the issue branch to the remote immediately**, even if it initially contains no issue-specific commit, so restart logic has a durable branch identity.

Follow repository branch naming conventions. Prefer a branch name containing the tracker issue key/number when repo conventions allow because this improves recovery, but never violate documented repo naming rules merely to do so.

## 4. Implement with remote checkpoints

Implement only the issue scope and run required local checks.

Do not allow significant completed work to exist only in the ephemeral worktree. Create and push checkpoint commits after meaningful coherent milestones, for example:

- schema/model/API portion complete;
- component/service implementation complete;
- tests added;
- significant refactor complete;
- before entering a potentially long debugging/test phase.

**Commit before you check, not after.** Once an edit is complete, commit and push it before running any typecheck, lint, or test run. Checks take minutes, and those minutes are exactly when an ephemeral container is most likely to disappear — running a full suite over uncommitted work is the single most expensive habit available here.

A commit is a save, not a claim that the work is correct. Green is not a precondition for committing, and neither is coherence: a checkpoint that exists and is imperfect always beats a perfect one that was never made. Prefer coherent checkpoints, but never defer a push to obtain one.

Checkpoint rules:

- never checkpoint secrets, generated junk, or unrelated files;
- do not commit every tiny edit merely as a heartbeat;
- commit only issue-owned paths;
- push each checkpoint to the issue branch;
- never enter a long check or debugging phase with completed edits uncommitted;
- WIP checkpoint history is acceptable because normal squash-merge workflows remove it from the destination branch.

The goal is bounded data loss if a cloud container disappears: at most the work since the last meaningful checkpoint, not the entire implementation.

Under an orchestrator, expect the parent to inspect this worktree for uncommitted work and to commit on your behalf when it finds completed work held back. Holding a change until it is tidy does not keep it tidy — it hands the commit to something with less context about what you were doing.

If an implementation retry is allowed, use only the caller's remaining budget. Return reasoning-heavy repeated failure to the caller rather than escalating models autonomously.

## 5. Final local verification

Commit and push the implementation first, then run the repository-required typecheck/lint/format/tests. Fix in-scope failures within the implementation budget, committing each fix as it lands rather than accumulating them. Push the resulting final implementation commit/checkpoint.

## 6. Create and verify PR

Invoke `create-pr` with:

- canonical full issue URL;
- exact required base;
- tracker identity when useful;
- draft/full preference when supplied;
- **any coverage finding this issue's implementation carried** — a declared dependency satisfied on paper whose capability was absent, and the acceptance criteria left unmet as a result. `create-pr` decides the linkage form from this, and it cannot decide correctly if you do not pass it: the default is a closing keyword, so silence here auto-closes an issue you knowingly did not finish.

`create-pr` owns tracker-specific linkage, stack `Depends on:` metadata, review trigger policy, and PR creation.

After creation verify durable state:

- PR exists;
- expected head branch/base are correct;
- canonical issue linkage is correct, and in the form the coverage finding required — closing keyword only where the issue was fully implemented;
- remote branch head contains the final pushed implementation state.

Do not wait indefinitely for CI or review after this point, and do not arrange for anything else to wait on your behalf — the caller supervises this PR, whether that caller is `implement-issue` or an orchestrator. Bounding your own wait and declining to schedule one are two separate requirements, and only the first is obvious: arming a check-in before returning satisfies "do not wait" on a fair reading while still leaving a watcher the caller did not ask for, and one this worker may lack the permissions to disarm.

## Output

Return structured state:

- canonical issue URL;
- tracker;
- repository;
- working directory;
- outcome: `PR_OPEN` | `BLOCKED` | `BLOCKED_EXTERNAL` | `FAILED` | `NEEDS_USER`;
- branch;
- base branch;
- PR URL/number;
- remote head SHA;
- issue linkage verified: yes/no, and the linkage form emitted — closing keyword, or non-closing `Part of:` because a coverage finding was reported;
- whether the **completeness** of the blocker set was backed — by a caller's proven complete set, or by a known-true case read and observed — or left unproven, and on what boundary. A `PR_OPEN` carrying an unproven absence is making a narrower claim than it looks like it is making, and this line is the only place that distinction survives;
- the transport tier used for relationship reads and a **non-secret identity of the credential behind it** — the authenticated account and its scopes, never the credential itself. A caller comparing this against its own identity is what turns a caller/native mismatch into a cross-credential demonstration rather than a coincidence, and it cannot make that comparison if you do not say;
- dependencies checked: for each, the canonical full URL, which of the three sources named it, **the class you judged it under**, and how it resolved by that class's measure — for a code dependency: reachable from base / open PR not in base, with that PR's URL / merged but not reachable, with the merge and base; for a non-ancestry dependency: complete by its own measure / incomplete, with the state it is in / **unverifiable, naming the measure that was out of reach**; or unmet entirely — plus any caller assertion the observation contradicted. Naming the class matters because it tells the caller which measure was applied, and therefore whether a block is a base problem, a wait, or a real gap;
- source disagreements, reported as **two distinct kinds** because they mean different things and warrant different responses:
  - **visibility** — a source disagrees with another about **which edges exist**. Report the edge with the sources that had it and the sources that lacked it, since that pairing says whose read was short. But **only a source that claims to be exhaustive can contribute an absence**, and that asymmetry decides what counts:
    - **native metadata** claims exhaustiveness — it is the structured edge set — so an edge missing from it is a real signal;
    - **caller context** contributes an absence only for the edges its own native read produced. An edge marked as recorded outside native metadata — a blocker the caller established from an earlier worker's evidence and kept out of native by design — is one your native read is *supposed* to lack, so its absence is not a disagreement about anything. And caller context claims exhaustiveness at all **only when the caller marks it as its complete READY dependency set.** Marked, an edge missing from it says the caller's own view was short. Unmarked — and it is optional, and is also how a user answers one previously unverifiable prerequisite — it is a targeted answer, so it contributes edges and availability assertions and never an absence. Treating an unmarked answer as exhaustive would report every unrelated native dependency as a visibility disagreement and tell the user their view was partial when they had simply answered a narrow question;
    - **prose** claims nothing. It mentions edges; it never purports to list them all. A blocker in native metadata that nobody wrote into the description is the ordinary case, not a finding.

    So: prose has it and native lacks it is a disagreement, because prose can only *add* information. Native has it and prose lacks it is **not** — treating that as one would fire on nearly every issue and stop the run for a structured-only dependency, which is exactly what structured metadata is for.

    The rule behind all three: **a source's properties are declared, not inferred, and an undeclared property is assumed absent.** Exhaustiveness is the case here; independence and contemporaneity are the same kind of claim. Assuming any of them is how a check that exists to catch a silent partial view starts inventing them;
  - **availability** — a mismatch against the caller's supplied dependency context, **in either direction**, naming which way it went: it asserted a blocker satisfied and observation disagreed, or it asserted one unmet and observation found the work available. Evidence that the caller's base or completion claim no longer holds, and nothing at all about what the transport can see. Say "no longer holds" rather than "was wrong": the claim may have been true when made and overtaken since — a revert landed, a branch was force-pushed, a release was rolled back. The caller cannot tell those apart from its own error, so report what you observed and when, and leave the diagnosis to the side that knows what it claimed and why. Direction matters because the resolutions differ — the first says the caller's base needs fixing, the second says its constraint may be obsolete — and a caller that cannot tell which way the mismatch went cannot act on either.

  Report both even on a successful run, since each is evidence about something beyond this issue. Do not collapse them into one label: a caller that cannot tell them apart must treat a stale base as a possible transport failure, which is a far more expensive response than the situation needs;
- draft state as created, exactly as `create-pr` reported it;
- checkpoints pushed: count/SHAs when useful;
- checks run;
- implementation attempts used;
- blocker/failure details;
- on `NEEDS_USER`, **which kind** it is — an unverifiable prerequisite, or an unproven dependency view — and the recommended user action. The two demand opposite things of a caller: one is a question to put to a person, the other is transport evidence that invalidates a visibility proof and holds up every sibling dispatched through the same read. Leaving the caller to infer it from whether the blocker list is empty is how the expensive one gets handled as the cheap one.
