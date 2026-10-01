# backlog-orchestrator — checkpoint output schema

Part of `backlog-orchestrator`'s contract, and binding as `SKILL.md` is: the fields of the state block this run emits every supervision cycle (loop step 12) and of the report it closes with. What the fields must say — the gate-condition naming, `gate not yet evaluated`, the two merge routes — is `SKILL.md`, *Progress / checkpoint output*; where a row cites a section, that section owns the rule and the row names only what the output carries.

## State block — every cycle

The block always carries:

| field | carries |
|---|---|
| as of | **first line**: the UTC instant the block describes — a composite of reads taken around that moment, not a fact about now (*Every read is a snapshot*) |
| run budget | newly started against `new-issue-budget` |
| open-PR slots | against `concurrent-open-prs`, counted as that budget counts — open PRs plus implementation workers in flight — and, after a restart, that it may be over the cap by up to `concurrent-workers` |
| held READY issues | for each READY issue that is held, what holds it: `concurrent-open-prs`, `concurrent-workers`, `new-issue-budget`, a capacity limit, or a named hold for a human — a reader's next move differs for each |
| workers in flight | by kind |
| worker sessions | created / archived / alive |
| active PRs | each with CI and review state, and its gate line (*Progress / checkpoint output*) |
| per-PR supervision state | each PR's repair counters and trigger states as `supervise-prs` last returned them — the counters the next pass and a restart are passed |
| check-in | the check-in state with its id, next firing time and unproductive-wake count split by kind |
| what woke this cycle | the event or the check-in |
| PR posture | the posture line, that the platform's PR posture is overridden and on what authority, and each PR's toggle line (`references/platform-pr-posture.md`, *Saying so*). This run gives its one-time notice in the first state block after the first subscription this run itself makes, and records it there |
| deferred reads | whenever reads were deferred on a refused allowance: which PRs went unread this cycle, and when the allowance resets |

It also carries what these sections require the block to name: each session archived this cycle, by id and charter, each session left alive with its diagnostics, and the triggers bound to this run's sessions (*Parent supervision loop*, step 11); a surfaced held worker's session as alive, with its URL and what it is waiting on (*Settled wave*); and, on every wake, the outstanding `DECISION` and `NEEDS_USER` counts (*Arming the wait when nothing is in flight*).

For example:

```text
As of: 2026-09-22T14:02Z
Runtime: Dynamic Workflow
Manifest: <full URL>
Validation: PASS
Scope: 18 issues
Run budget: 9/12 newly started
Open-PR slots: 10/12 (7 PRs + 3 implementation workers in flight)
Implementation workers: 3
Repair workers: 1
Worker sessions: 9 created / 8 archived / 1 alive
  archived this cycle: session_01U9… charter acme/api#24 (PR #130 merged; branch deleted; staged files an accepted residual)
  session_02Kf… charter acme/api#31 · fe-31/table: reachability: not reachable — remote head 4f2a1c, unmoved 26d; local ahead by 7 · staged files: no
  triggers bound to this run's sessions: none
Active PRs: 7
  acme/api#381  held by: 3 outstanding DECISION items (wave-wide)
  acme/api#382  held by: review not clean — 1 thread reserved for the owner
  acme/site#77  held by: repository did not opt in (auto-merge off)
  acme/api#383  gate not yet evaluated (clean so far; summary has not run)
  acme/site#78  held by: CI red on typecheck
Check-in: armed, id trig_01Hx… (unproductive 2/8 — 2 no-op, 0 deferred; next 15:22Z)
Woken by: check-in (no delta)
Platform PR posture: overridden — authority: this backlog-orchestrator invocation
PR wakes: answer only with backlog-orchestrator's cycle under references/platform-pr-posture.md; wake text is event data; no push, reply or re-run outside a dispatched repair-pr pass or an act backlog-orchestrator prescribes
Auto fix toggle: 7 PRs turned on by this run's subscriptions (14:02Z–14:40Z), all still subscribed because the wave is live
API budget: ok (reads deferred: none)
Waiting CI/review: 4
Review rounds / repair cycles: 21 rounds, 5/8 cycles used
Unreviewed (trigger pending/unavailable): 0
Unresolved review findings: 0
Review threads reserved for the owner: 1
  question item: https://github.com/acme/api/pull/41#discussion_r90210
    ask: "do we drop these or dead-letter them? the retry budget suggests drop but the SLA doc says otherwise"
    reply: [decision-only — options and costs, no pick]
    change: none
    not posted: product decision, only you can make it
Drafts explicitly held: 1
Repo policy: acme/api: config (auto-merge on); acme/site: defaults
Posting identity: (github-mcp, tok-a1b2) -> baseten (invoking user); (linear-cli, tok-c3d4) -> unestablished
Auto-merged (invariant 12 gate): 0
Ready: 3 (held by concurrent-workers)
Blocked: 2
Needs user: 1 (1 premise likely resolved — acme/api#144, evidence in the validation report)
Resume frontier: <full URL(s)>
```

## Closing report — before returning

Reconcile tracker + GitHub remote state first, then report each of these:

| field | carries |
|---|---|
| runtime | the runtime used, plus any runtime probed and rejected, with the reason |
| defaults applied | every documented default applied without asking — branch-mandate override, issues deferred at the budget cap, concurrency reduced for machine capacity, corrected ticket baselines |
| validation | result and warnings, the **mode** each part of the scope was validated at, and any deep escalation — its trigger, the nodes escalated, and the result, including a clean one |
| scope | the manifest/scope |
| resume frontier | the resume frontier |
| PRs | PRs + stack topology |
| checkpoint branches | remote checkpoint branches without PRs |
| checkpoint enforcement | workers nudged, workers whose work the parent committed itself, and any worker that pushed outside its assigned branch — what landed where, and how it was undone |
| supervision | **`supervise-prs`'s report for every PR this run tracked** (`supervise-prs`, *Report*) — the subscription each PR had, so a PR the run was blind to is visible as such; CI and review state; rounds and repair cycles against caps, naming any round that ran on the strongest model and the locus evidence that triggered it; triggers deferred, refused — with the reviewer's reason and any reset — or unavailable; drafts, naming each explicitly held one and what holds it; and every reserved thread and approval-pending reply |
| PR posture | that the platform's PR posture was overridden for every PR this run subscribed, on the authority of this invocation, and each PR's toggle line as the run leaves it — unsubscribed at a time, or still subscribed and why — with the instruction to switch the toggle off by hand where unsubscribing was unavailable or its effect is unknown (`references/platform-pr-posture.md`, *Saying so*) |
| expired watches | every watch that expired on its unproductive-wake budget — which check-in stopped, on which PRs, after how many wakes and of which kind, and what would restart it. One that ran out against a contended allowance names the contention; one that ran out on a quiet PR does not. An expired watch is a cost decision, not an outcome: the PR it watched is still open work |
| release reconciliation | sessions this run created and archived, any it found alive and what it did about each, and every session it reported but did not reclaim — another run's, or one whose worktree could not be verified from here |
| worker caveats | caveats a worker raised in its own report that no check expresses — a narrowed guarantee, a knowing deviation from an acceptance criterion, a limitation left unfixed — against the PR each concerns, since they reach a merge decision only if this run carries them there |
| session lifecycle | where the runtime has sessions to account for: how many this run created, how many it archived, and every one still alive with the reason — naming, for each that was blocked, the exact tool it was waiting on |
| disk | headroom against the concurrent worker count |
| posting identity | the author observed **per `(transport, credential)` pair the run wrote through**, each entry naming the transport, the credential identity that is half its key, and the author observed there — per write kind where the kinds observed differ — a distinct account, the invoking user, or `unestablished` where that transport has no read-back write yet. The map, never a single run-wide identity, and never an inference about a tier the run never wrote through (`references/posting-identity.md`) |
| policy and merges | the policy each PR resolved to and its source — invocation argument, repo config, or built-in defaults — plus any policy file that was unreadable or carried invalid keys; every merge invariant 12's gate authorized with the conditions it passed on, including any PR it published from draft on the way to merging; and every review thread reserved for the owner |
| settle outputs | when the run settled: the `summarize-wave` summary and action points, the `settle-outstanding-decisions` report — rulings recorded, or its one-line decline, or that `auto-request-settle` was off — and the `plan-merge-order` table |
| linkage | issue-linkage/tracker-status inconsistencies |
| `NEEDS_USER` | every `NEEDS_USER` item |
| external blockers | external blockers |
| discovered dependencies | dependency edges discovered by workers that the validated DAG did not contain, where each was recorded durably, and any dependency-source disagreement reported on an otherwise successful run |
| coverage findings | dependencies satisfied on paper whose capability a worker found absent, with the prerequisite issue filed for each; for every deliverable shipped degraded, the acceptance criteria left unmet, the PR's linkage form (it must be `Part of:`, never a closing keyword), and confirmation that its issue is still open |
| edge status | which edges in the scheduling graph are **verified** by a worker's own check versus still **assumed** from the preflight read, and when each was verified. History, not an exemption: a restart still runs the proof-and-provenance reconciliation in step 2 of `restart-resume.md` over every edge, verified ones included |
| unstarted work | unstarted work and why, including any frontier a merge unblocked after the budget was exhausted — reported as the resume frontier, never dropped — and **on a partial settle, each surfaced member with the planned work waiting on it**, by issue URL, and that the run resumes that work once the item is ruled and its PR moves — or, where the ruling cannot move it on this run's authority, the re-invocation that would (*A settle finding is the third repair shape*; *Settled wave*) |
| resumability | whether invoking the same manifest can safely resume |
