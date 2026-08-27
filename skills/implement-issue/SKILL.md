---
name: implement-issue
description: Single-issue orchestrator for one tracked issue from its canonical full URL. Composes implement-issue-core for issue→code→checks→durable PR, then supervises bounded CI/review activity and dispatches repair-pr as needed until the PR is healthy, blocked, or needs user input. Useful standalone and as a one-issue workflow.
---

# Implement Issue

Orchestrate exactly one tracked issue end-to-end while preserving the convenience of a single command.

This skill is intentionally a **one-issue orchestrator**. It composes reusable primitives rather than duplicating their implementation logic:

- `implement-issue-core` — issue reading, implementation, durable checkpoints, local checks, PR creation;
- `repair-pr` — one bounded CI or review repair pass;
- `create-pr` — tracker linkage, stack metadata, PR creation, review trigger;
- `resolve-pr-comment` — review-thread fix/reply/resolve mechanics used by `repair-pr`.

It does not schedule other backlog issues and never merges unless the user separately invokes an authorized merge workflow.

## Authority

Invoking this skill authorizes implementation and PR creation for the supplied issue unless the user explicitly says otherwise. It does **not** authorize merging.

The issue's **full URL is canonical identity** throughout the workflow. Short keys/numbers may be shown for readability but never replace the full URL in durable state.

## Inputs / constraints

When a caller supplies repository, worktree, branch, required base, dependency context, tracker, and budgets, preserve them exactly.

Defaults when standalone:

- implementation attempts: **2 total**;
- CI repair cycles: **2**;
- review-fix cycles: **2**;
- monitoring cap: **8 hours** where persistent/event-driven monitoring is actually supported.

Do not broaden scope into another issue.

# Phase 1 — durable implementation

Invoke `implement-issue-core` with the canonical issue URL and all supplied execution constraints.

Do not hand-roll implementation logic here.

If core returns `BLOCKED`, `BLOCKED_EXTERNAL`, `FAILED`, or `NEEDS_USER`, surface that result. Preserve the distinction between the two block outcomes rather than flattening them: `BLOCKED_EXTERNAL` means the issue waits on work outside the authorized set, so it needs no *frontier* reasoning — only the blocker, its state, and who owns it. It still needs the relationship classification below. Whether an edge is real is a separate question from whether the work behind it is external, and a stale prose edge pointing at an unfinished external prerequisite would otherwise wait forever. If a standalone user clearly requested strongest-model retry, that can be handled by the surrounding Claude session; this skill itself should not create an unbounded model-escalation loop.

A `PR_OPEN` can also arrive with its **dependency view unproven** — the worker could not establish that its blocker list was complete, whether it found blockers or none. That is the normal standalone case rather than a defect: this skill supplies no graph judgement, so the worker proceeds on the invocation's authority and says the absence was never proven. Pass that on in one line rather than dropping it. The PR is making a narrower claim than it appears to — that no blocker was visible, not that none exists — and a user who wants the stronger one can supply a confirmed edge as dependency context on a re-invocation, which turns the next run's silence into evidence.

A **visibility disagreement** means something specific here even though there is no frontier to re-derive: the transport may be returning a partial dependency view, so the issue you just implemented may have blockers nobody in this run could see. Say that plainly rather than filing it as a mismatch — name the edge and which sources had it against which lacked it, and note that the dependency view behind this run is unproven. The user can re-read through a different credential or check by hand; neither is available to them if the finding arrives as a generic disagreement line.

An **availability disagreement in the obsolete-constraint direction** — the caller said a blocker was unmet, the worker found the work available — deserves naming rather than passing through as a generic mismatch. In a standalone run the caller is usually the user, so it is their own constraint that may be stale, and they are the only one who can retire it. Report which dependency, what was observed, and that the block rests on their assertion rather than on anything the worker could see.

**An outcome is a ranking, not the whole finding.** Core returns one value for an issue that may have several kinds of blocker at once, and it ranks them — an in-scope blocker outranks an unverifiable prerequisite, which outranks an external wait. So a `BLOCKED` may still carry an unanswered question about a release or deployment, and you are the only thing that will ask it. Read the reported blockers, not just the outcome, and surface every one that needs the user.

`NEEDS_USER` arrives in two kinds and core says which. An **unproven dependency view** means the completeness of the blocker list was never established — it should not reach a standalone user at all, since this skill supplies no readiness judgement and the worker proceeds on the invocation's authority instead. Arriving here, it means a caller passed a READY judgement through, and the answer is to prove the view or drop the claim, not to re-assert readiness.

`NEEDS_USER` on an **unverifiable prerequisite** is its own case, and the cheapest one to resolve: the worker could not observe the measure that class needs — typically a release or deployment state that lives outside the repository and tracker. Surface the blocker, the measure, and why it was out of reach, and ask the specific question rather than reporting a generic need for input. The answer is usually seconds of a person's time, and once given it can be supplied as dependency context on a re-invocation. Say what that buys, without overstating it in either of the two available ways.

An answer ends the *uncertainty*; only a **yes** clears the blocker. Told the release has not happened, the prerequisite becomes a known unmet blocker and the next run blocks on it — so frame the question as one whose answer decides which of two states you are in, not as a step that unblocks the work. And a yes clears only this blocker: whether the re-invocation proceeds depends on what else core reported, since an unverifiable prerequisite outranks an external wait and can arrive with one still unmet. Promising a proceed the user does not get is worse than naming two things to clear.

Either block outcome on an unmet dependency is a special case: it is authoritative information about the graph rather than a worker failure, so it is never retried. Everything below applies to `BLOCKED` and `BLOCKED_EXTERNAL` alike — externality changes who resolves the blocker, not whether the edge is real. The issue was judged ready against a dependency view that turned out to be wrong — commonly a read that returned part of the blocker list with no indication it had. Surface the named blockers by canonical full URL, and pass on any source disagreement the worker reported (a dependency the prose named that native metadata did not return) even where the run otherwise succeeded: that is evidence about the transport, and this is the only place it surfaces.

Never retried is not the same as never resolved. There is no orchestrator here to re-derive a frontier, so this skill owns the classification itself, or a stale prose edge blocks the issue permanently with no route forward:

- **any blocker named only in prose** — establish whether the relationship still holds before acting on it, whatever state the referenced work is in. Prose survives edits that remove a dependency from native metadata, so a prose-only blocker is as likely to be a dependency someone deleted as one nobody built — and that is just as true when the referenced issue happens to have an open PR or an out-of-base merge. Gating this on "the work exists nowhere" would restack onto a dependency that is no longer real;
- **it still holds** — the block stands, in whichever form core returned it; report the blocker and stop;
- **it does not, or cannot be settled from the issues themselves** — `NEEDS_USER` with both readings and a recommendation, not a bare block. The user can retire a stale edge in seconds; they cannot act on a `BLOCKED` that does not say which reading it assumed.

Where the blocker's work exists but is not available — an open PR, a merge outside this base, or a non-ancestry prerequisite still incomplete — pass on what the worker named. A restack or base correction is actionable without touching the dependency graph at all. But classify first where the blocker came only from prose: restacking onto a dependency that is no longer real costs more than leaving the issue blocked, because the resulting base becomes the justification for the next one.

If core returns `PR_OPEN`, record:

- PR URL;
- branch/base;
- remote head SHA;
- tracker linkage verification;
- draft state as created;
- **every** posting-identity entry core returned, keyed by transport — not one pair. `create-pr` writes the PR and the review trigger through transports the exception may deliberately make different, so core returns a map and collapsing it here discards one path before the re-triggers and the final result consume it (see `backlog-orchestrator`, *Posting identity*);
- implementation attempts used.

At this point the code is already durable remotely even if the current container disappears.

# Phase 2 — single-issue PR supervision

After PR creation, this skill owns supervision **only because it is the standalone single-issue orchestrator**.

That qualifier is a boundary, not a caveat, and it is worth stating in both directions. Here there is no parent to defer to, so watching this PR — including arming a subscription or a scheduled check-in to do it — is this skill's job and the surrounding session's ambient posture agrees with it. Under `backlog-orchestrator` nothing dispatched supervises its own PR: that parent fans out `implement-issue-core` directly and countermands the ambient posture in its dispatch prompt, so a second watcher never arms itself. Read a rule against self-monitoring in the worker skills as scoped to that case; it does not reach Phase 2.

If Claude Code's own background PR watch/notification behavior promotes the worker-created PR into the top-level session or provides first-class PR/CI/review events, use those directly. Do not create a duplicate monitoring mechanism merely because `implement-issue-core` created the PR in a child worker. If that background behavior has auto-merge enabled, it will merge the PR itself once checks pass — since this skill never authorizes merging (see Authority above), confirm auto-merge is off, or treat an auto-merge as outside this skill's control rather than an outcome it produced.

Prefer, in order:

1. first-class/promoted PR events from the current Claude runtime;
2. other event-driven PR/check/review notifications;
3. bounded polling fallback when no event mechanism is available.

The platform may observe an event; this skill remains the **policy owner** deciding whether a repair is appropriate and whether the remaining repair budget permits it.

Avoid frequent no-change polling and do not keep a child agent alive solely to wait for GitHub.

Maintain explicit state:

```text
PR: <URL>
CI repair cycles: <used>/<limit>
Review repair cycles: <used>/<limit>
Current remote head: <SHA>
First review round: pending | complete-with-findings | clean
Draft state: <as-created> -> <current>
State: waiting | repairing-ci | repairing-review | healthy | needs-user
```

## CI failure

When CI fails:

1. inspect enough check/log context to identify the relevant failure;
2. if the failure is attributable to this PR and the CI budget remains, invoke `repair-pr` once with `repair type = ci`;
3. pass the exact failure context and remaining budget;
4. adopt the returned remote head SHA **and every posting-identity entry the pass observed**, merging them into the run's transport-keyed map rather than replacing it — a repair can establish a path core never used, and the re-trigger in the review branch and the final result both read that map;
5. wait for the next CI result using first-class/event-driven state where available;
6. after the budget is exhausted, return `NEEDS_USER` rather than trying again.

If CI is clearly unrelated/external/flaky and no code repair is justified, report/monitor it without consuming a repair cycle.

## Review feedback

When actionable review feedback arrives:

1. group one coherent review round;
2. if review budget remains, invoke `repair-pr` once with `repair type = review` and the relevant threads/comments;
3. adopt the returned remote head **and every posting-identity entry the pass observed**, merged into the run's transport-keyed map;
4. retrigger/request review when repository convention requires it — selecting the trigger's author from the identities observed so far, this pass's included: a repair can establish the invoking-user path core lacked, and re-triggering before adopting its observation is what makes that trigger silently fail;
5. wait for the next review state using first-class/event-driven state where available;
6. after the budget is exhausted, return `NEEDS_USER`.

Subjective product/architecture judgment returns `NEEDS_USER` immediately rather than burning repair cycles.

## Draft promotion after a clean first review

A PR opened as a draft is signalling "not finished yet". Once its **first** automated review round has completed and every actionable finding from it is resolved, that signal is stale and the PR should be marked ready for review.

Promote when all of these hold:

- the PR was created as a draft by this run (`create-pr` reports its as-created draft state through `implement-issue-core`);
- the review trigger was issued and a review round actually came back — a review that was deferred, suppressed, or never fired is not a completed round;
- no actionable finding from that round is unresolved, whether it was fixed, or answered with a reply explaining why no change is warranted — `repair-pr` reports the remaining count;
- CI is green on the current remote head;
- the PR is not `NEEDS_USER` and has no unanswered product/architecture question.

Then mark the PR ready for review once, and record the transition.

Rules:

- Promote at most once. Never flip a PR back to draft, and never re-promote one a human returned to draft.
- Never promote a PR this run did not open.
- Repository convention or an explicit user/caller draft preference overrides this.
- Later review rounds do not re-trigger promotion; the PR is already ready.
- Promotion is not merge authorization — this skill still never merges (see Authority above).

# Completion

Return `PR_OPEN`/healthy when the PR is implemented, linked correctly, and has no currently known CI/review item requiring autonomous repair. When persistent monitoring is supported, continue until healthy, merge/close, user stop, budget exhaustion, or monitoring cap.

If the runtime cannot remain active while waiting only on external events, return a durable checkpoint rather than pretending background monitoring will continue.

Return `NEEDS_USER` with the exact PR/issue URLs, remaining failure/comment, attempts performed, and recommended next action when autonomous repair cannot safely finish.

## Structured result

Return:

- canonical issue URL;
- tracker;
- repository;
- outcome: `PR_OPEN` | `BLOCKED` | `BLOCKED_EXTERNAL` | `FAILED` | `NEEDS_USER`;
- branch/base;
- PR URL/number;
- remote head SHA;
- issue linkage verified, and the linkage form emitted — closing keyword, or non-closing `Part of:` because a coverage finding was reported;
- implementation attempts used;
- CI repair cycles used;
- review-fix cycles used;
- final CI/review state;
- draft state as created, and whether it was promoted to ready (or why not);
- the run's full posting-identity map — every entry observed by core and by each repair pass, keyed by transport, since a repair can run on transports core never used and the entries are answers about different write paths rather than versions of one. Carry both rather than the latest: an invoking-user path observed in any of them is what this skill's own review re-triggering needs, and there is no orchestrator here to hold that evidence instead. Report `unestablished` where no authored write was read back (see `backlog-orchestrator`, *Posting identity*);
- whether the completeness of the blocker set was backed or left unproven, and on what boundary;
- dependencies checked, and any source disagreements, exactly as core reported them — including on `PR_OPEN`. A run that succeeded while its transport returned a partial dependency view is the case where this evidence is easiest to drop and most worth keeping: nothing else in a standalone run will surface it, and dropping it here means neither the user nor a surrounding workflow ever learns the view was partial;
- blocker/failure details, including the dependency class each block was judged under;
- recommended user action when needed.
