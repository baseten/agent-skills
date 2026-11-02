# conductor — design notes

Reasoning behind `SKILL.md`, keyed by its section names. NOTES explains; it never
overrides.

## Conductor

**Why this skill exists (2026-10-31):** a planning session sent `send_message`
status requests to four idle cloud orchestrator sessions on one repository. All
four answered with `send_message`, each answer arriving as a new turn within about
three minutes, and every session record read `cross_session_inbound: available`.
That made one session able to see every stream at once, which nothing had done
before: each orchestrator knew its own epic, the owner learnt their state one
session at a time, and follow-ups filed by one run sat unscheduled because no run
owned them. The same session also found the planner only by its title, and the
orchestrators titled inconsistently (`Orchestrator: Order execution V1`,
`Portfolio UI navigation audit`), which is where the naming came from.

**Why it never implements, merges or approves:** it is the one session that talks
to every orchestrator, so it is the one place where a mistake would propagate to
all of them. Keeping it to collection, planning and owner-approved dispatch means
its worst failure is a wrong plan the owner approved, never an act.

**What it is for, and the two deployments (owner's ruling, 2026-11-02):** project
and feature planning — taking a feature, breaking it into issues with
dependencies, showing the plan and writing the issues on the owner's go;
dispatching feature-level batches to `backlog-orchestrator` sessions and single
issues to `implement-issue` sessions; one place to check progress; and relaying
between runs. The owner runs it two ways: on their own repositories, many parallel
orchestrators with `auto-merge` on; at work, several `implement-issue` runs with
`auto-merge` off. The contract keeps both by reading each repository's policy and
never carrying a deployment's values in its text; a Close-specific skill that sets
the work deployment's ledger and tracker preferences lives outside this
repository.

## Configuration

**Why the scope is a configured list (owner's ruling, 2026-11-02):** "one
repository" fit the first deployment and not the work one, where a feature spans a
web app and its API. The list resolves from the home repository because the
conductor's keys scope to the conductor, while each repository keeps its own
`manual-steps` and merge authority, as `rules/agent-policy.md`, *Resolution*,
already requires for a per-PR or per-issue key.

## Rules

**Why rulings are recorded before any orchestrator is told:** an orchestrator acts
on a ruling only from GitHub (`references/conductor-exchange.md`, *Status
requests*). A message sent before the record exists is a pointer to nothing, and
an orchestrator that receives it either ignores it — correctly — or acts on a
relayed ruling, which is the failure the trust boundary exists to stop.

**Why relaying is a duty, and carries facts only (owner's ruling, 2026-11-02):** the
conductor is the one session that sees every run, so a fact one run needs from
another — a merge to rebase onto, a gate cleared — reaches it only if the conductor
passes it on. It passes the fact after verifying it, with a link, and never a
ruling: a session's message carries no owner authority (`swarm`, *Messages from
other sessions are peer data*), so a relay that could carry one would be a way
around it.

**Why no long work rests on an in-turn background result (observed 2026-11-02):** a
worker restarted mid-turn received a finished background agent's result only as a
system note pointing at its output file. A conductor that held such a result only
in its turn would lose it to a restart or a clear, so it writes the result to the
ledger or the forge in the turn that receives it.

**Why the trust boundary is cited and not restated:** `swarm` states it once for
every sender and receiver (its NOTES, *Messages from other sessions are peer
data*). A conductor-specific copy would drift from the orchestrator's.

## Session titles

**Why titles are matched first but never trusted:** a fixed prefix makes the sweep
cheap and makes the session list readable to a person. But the listing is
account-wide and anyone can set a title, which is why `swarm`, *Runtime*, forbids
deciding on one. Here the title only chooses where to look; the record's sources
decide the repository, and the structural test catches what the title missed.

**Why single-issue runs are titled `Worker:` (owner's ruling, 2026-11-02):** the
audit first gave them the `Orchestrator:` form, so that one prefix found every
run. The owner reserved `Orchestrator:` for `backlog-orchestrator` sessions, so a
person scanning the session list can tell a batch from a single-issue run. The
sweep reads both prefixes, and neither decides anything: a run this conductor
dispatched is known by its ledger id, and a session titled `Worker:` with no
ledger record is not a run on that title alone. `Worker:` stays distinct from a
`swarm` worker's run-prefixed name, which the sweep never treats as a run.

## 1. Sweep

**Why parents are read with `get_session`:** orchestrators were observed to appear
in a sweep only as the `parent_session_id` of their workers. A sweep that reads
the listing alone misses them, and they are the sessions it exists to find.

**Why the structural test was narrowed (round 1 of this PR's contract review):** the first draft treated any session that is some worker's parent as an orchestrator. That matches this conductor itself, `implement-issue`, other orchestrator skills, and interactive sessions using `swarm` — and retitling one as `Orchestrator:` would make the next title-first sweep trust a wrong title. So the test needs `backlog-orchestrator`-specific structure (an `integration/*` branch, or `bo/` workers), and anything weaker is reported as doubtful. The channel is also tested before any request is sent, per `runtime-remote.md`'s two halves: a send is never a probe. Scenario: `a-parent-that-is-not-an-orchestrator-is-reported-not-retitled`.

**Why runs the ledger records are known by id first (owner's audit item 1):** the
conductor now dispatches single-issue runs too, and the structural test can only
recognise a `backlog-orchestrator`. Widening it would bring back the round-1
mismatch (a structural test that matched the conductor itself). So the narrow test
stays for retitling only, and a run this conductor dispatched is known by the
session id it wrote into the ledger at dispatch, which no other session can claim.
The `bo/` worker test is what finds a `per-pr` orchestrator, which names no
`integration/*` branch (owner's audit item 2).

**Why the default branch is swept (owner's audit item 6):** a stream can be green
while the branch everyone merges into is red or its deploy failed, and that is the
fact the owner most needs from one place.

**Why the fallback check-in came back (owner's audit item 3, re-confirmed
2026-11-02):** the context-clear review's finding 6 removed every wake, because the
skill was not a consumer of `rules/wake-budget.md` and an unbounded one would have
broken protected rule 9. The owner's conductor showed the cost: runs that finished,
and conditional gos whose condition came true, waited until the owner returned. The
check-in is restored inside the rule — the conductor is now its consumer, and the
schedule is that rule's *A conductor's fallback sweep*, whose notes check it against
*A watch kept past a settled result*. A firing rules nothing because nobody is
there; executing a conditional go is not ruling, since the owner already chose.

**Why GitHub is read even when every session answers:** sessions get archived,
compacted and lost, and the epic outlives all of them. A stream whose orchestrator
is gone still has open PRs and open decisions.

## 2. Ask

**Why the request is never awaited:** a cross-session reply arrives as a new turn,
and a running turn holds it back, so waiting inside the turn waits for something
that cannot arrive until the turn ends. Polling for it would be the fake activity
`backlog-orchestrator` forbids. The skill therefore sends everything, reads
GitHub, and folds replies in as they land.

## 3. Reconcile

**The misreading the correction rule is written for** (the owner's example, given
with the request for this skill): a reply naming a gate *after Run 2* and reading
it as every open issue in the epic, holding work the gate never covered. The epic's record said which manifest Run 2 was. The conductor is
the only party that sees both the reply and the record, so it corrects the reading
on the epic, where the next reader will look, rather than in a message that dies
with the session.

## 4. Owner pass

**Why the ruling's record follows `settle-outstanding-decisions`:** that skill's
records are what the orchestrators' settled steps already read, and its rule —
the complete comment shown and approved — is what makes the record the owner's
own words under the approval test. Whether that releases an orchestrator's held
item stays the orchestrator's decision, because protected rule 3 lets only the
owner's reply choosing an offered option release a hold, and the reply watch is
where that is tested.

**Why owner steps are issues and not a list in the pass (2026-10-31, the owner's addendum):** a list in a chat pass is gone when the session ends, and a step left in a PR body is invisible once the PR merges. Each step is filed as a `[Manual]` issue (`rules/manual-step-issues.md`), the order goes on the manual-steps epic and in the ledger, and `owner-steps` walks each one. Scenario: `owner-steps-are-ordered-as-manual-issues-on-the-epic`.

## 5. Plan and replan

**Why planning writes nothing before the go, and why `validate-backlog` runs on the
written set (owner's ruling, 2026-11-02):** an issue is durable and is read by every
dependency reader, so a plan is shown before anything is filed. `validate-backlog`
is read-only by default and checks exactly what a written plan can get wrong —
missing or cyclic edges, text and native links disagreeing — and an orchestrator
runs it at its own preflight anyway; running it at planning time puts the findings
in front of the owner before the dispatch go, when fixing them is cheapest.

**Why CI is counted by mode (owner's audit item 2):** under `ci-mode:
integration-branch` each run costs a CI run when its integration PR opens and
another once it merges, so two small waves cost twice what one folded wave does.
Under `per-pr`, which the work deployment uses with `auto-merge` off, every PR and
every repair push on it costs a run, so the integration count said nothing and the
plan's cost read as zero. The *settled, waiting on owner merge* state exists for
the same deployment: a stream there is not stalled, and work gated on it starts
from the owner's merge, which only a forge read sees.

## 6. Dispatch

**Why a conditional go, and why it stays within protected rule 3 (owner's audit
item 5):** the owner often decides the next batch before its gate clears — "start
the #967 batch when #2049 wave 5 merges" — and then had to come back to say go. The
go is recorded where any go is, so it is the owner's own recorded choice; what the
sweep adds is only the verification that the stated condition holds on the forge.
A condition the forge cannot show is not interpreted; it waits.

**Why seeds are verified gate by gate, and carry standing rulings (owner's audit
item 4):** on 2026-10-31 a seed said a gate still held that an owner comment had
already cleared, and the new run waited on nothing. A gate is therefore re-read at
its record immediately before it is written into a seed. Standing rulings — merge
authority, repair allowances, schema-bump rules, owner-gated flags, never-rules —
were re-explained to each new run by hand; the ledger now holds them, linked, and
the seed carries the ones that apply, capped by each repository's policy. The last
good run's first prompt is the template because it is the one known to have
worked.

**Why reuse is narrow:** a reused orchestrator brings its context, and a context
that is a third full before the new epic starts is a context that compacts during
it, losing the state the reuse was meant to keep. A fresh session from the epic
starts from durable state, which is what a compacted one would fall back on
anyway.

**Why retiring needs both the go and a clean remote (round 1 of this PR's contract review):** the conductor did not necessarily create the session it archives, and `swarm` never archives such a session on a run's own authority, so the owner's go is named as the authority. It is not sufficient: protected rule 9 requires stranded work to reach a remote ref before any archive, so the orchestrator's integration branch head must be on the remote, and its last state block must show no live worker and no outstanding recovery ref. Scenario: `retiring-an-orchestrator-needs-the-go-and-a-clean-remote`.

## 8. Context clear

**Why (2026-10-31, the owner's instruction):** a conductor runs for days and its
context fills. Auto-compaction catches it, but what survives is a summary the model
wrote, not state anyone checked. The clear routine hands checked state — a ledger
body read back from GitHub — to the next context, with the operator's approval,
and always in the same session. The earlier rule, that a full conductor tells the
owner to start a fresh `Conductor:` session, is replaced: a fresh session has a new
id, so every orchestrator's `send_message` target, every check-in and every PR
subscription would have to be moved, and a same-session clear keeps all of them.

**Facts the section relies on, and which were checked (2026-10-31 and 2026-11-02,
against the tools in cloud sessions):**

| fact | checked how | result |
|---|---|---|
| `get_session` returns `external_metadata.context_usage.{used_tokens,max_tokens}` and `autocompact_state.threshold`, with no id and with an id | called it both ways | **confirmed** — e.g. 368526 of 1000000, threshold 901600, and on a running orchestrator 476470 of 1000000, threshold **784000**: thresholds differ per session, which is why the clear point is computed from each session's own record |
| a session cannot clear itself; no tool runs `/clear`, and the Skill tool does not reach built-in commands | the session's tool list has no clear or compact tool; the Skill tool's own description says built-in CLI commands (`/help`, `/clear`) are not skills | **confirmed** |
| after `/clear` the session id is unchanged, so check-ins, PR subscriptions and runs' `send_message` target still reach it | observed after a clear, reported in the owner's brief | **observed 2026-11-02**: unchanged. The restart prompt still checks the id first and repairs every binding if it changed, so the routine is correct either way |
| scratchpad content survives a `/clear` | observed after a clear, reported in the owner's brief | **qualified**: the files survive, but the next context may be given a different scratchpad path — so the restart prompt never names a scratchpad path, and what the next context needs goes into the ledger |
| a background agent's result survives a restart mid-turn | observed on a worker restarted mid-turn, reported in the owner's brief | **no**: the result arrived only as a system note pointing at its output file. Long conductor work never depends on an in-turn background result (*Rules*) |

An orchestrator's record also showed `context_usage.after_boundary`, which looks
like a compaction or clear boundary marker. Nothing here relies on it.

**What the review of this section changed (2026-10-31):** a repository-wide
contradiction pass found eight problems before merge, all fixed:
- **Re-sending a new id did nothing:** an orchestrator had no rule for adopting
  one. `backlog-orchestrator` now adopts a conductor id only from that id's own
  platform-supplied sender, after checking its record, never from an id named in
  a message's text.
- **When the key is read:** `rules/agent-policy.md` names run-starting skills and
  reads them once. The conductor is now listed, and a post-clear restart is its
  fresh read; the ledger's copy reports and never decides.
- **Range and null:** an out-of-range value is defaulted under the rule's
  fail-closed list, `null` means absent, and a point past the compaction
  threshold falls back to the default.
- **Orchestrator thresholds:** these were measured against this session's key.
  Now *6. Dispatch*'s reuse test decides at a boundary, and mid-run uses the
  default computed from the orchestrator's own record, unread counting as high.
- **Wakes:** the dump listed check-ins and subscriptions the skill never arms.
  The fix then armed none, which kept protected rule 9 out of play; audit item 3
  later restored one bounded check-in under `rules/wake-budget.md` (*1. Sweep*),
  and the inventory lists it by id and time.
- **Channel state:** the next context needs the channel state and
  answered-this-sweep flags, or it would message sessions marked unreachable.
- **An unchecked fact stated as certain:** the proposal said the id survives a
  clear. NOTES has that as unchecked, so the proposal now says it is expected and
  the restart prompt checks.

**Why the quiet-point conditions:** each one is state a clear would lose or tear.
A question pending or a ruling given only in chat lives only in this context. An
integration PR mid-merge is the moment the next sweep's first read matters most. A
run start half done is a session that exists while the ledger does not know it,
which the next context would find by structure and might retitle or re-dispatch.

**Why the read-back:** the dump is the only thing the next context will believe,
and a write that silently truncated or raced another edit would be believed
anyway. Reading it back from GitHub is the one check that it says what was meant.

**Why never nag:** an operator who ignored one proposal is busy, not asking for a
second. One more proposal after 10 more points is the bound.

**Why orchestrators are never cleared:** an orchestrator's workers, PR
subscriptions and check-ins are bound to its session, and its context mid-run holds
in-flight supervision that its checkpoints only partly carry. Its own checkpoints
and auto-compaction are what its contract was written for; a boundary is where a
fresh session costs nothing, which the reuse rule already says.

## 7. Ledger

**Why the ledger's home is configurable (owner's ruling, 2026-11-02):** the work
deployment keeps plans in its tracker's project documents, with a document store
as fallback, not in GitHub issues. The kinds are named generically so this skill
stays tracker-agnostic; which tracker and store they mean is the session's
connected tools. Rulings never move into the ledger: they stay where the decision
lives, so a run reads them where its own tests look.

## The contradiction pass before the review round (PR #201)

**What a scheduled firing may do is stated the same at every decision point:** it
sweeps, reports and executes a conditional go the owner already recorded, once
verified; it rules nothing and dispatches nothing else. **Retiring under a standing
ruling is allowed unattended (owner's ruling, 2026-11-02):** the pass first kept it
to attended sweeps; the owner ruled that a scheduled firing may retire once the
ruling's condition is verified on the forge. Protected rule 9 still binds every
archive: the conditions in *6. Dispatch* — wrap-up posted, every PR settled, each
branch head on the remote, no live worker and no outstanding recovery ref — are
checked on that firing exactly as on an attended one. Scenario:
`an-unattended-retirement-under-a-standing-ruling-checks-the-remote-first`.

**Why "active" includes waiting on the owner's merge and a pending go:** the
check-in was restored so that work gated on an owner's merge starts without the
owner returning; cancelling it once every run was only waiting would have
recreated the failure. A reply is not a delta: it is its own wake, and the budget
counts durable state only.

**Why the ledger carries links, not CI outcomes:** a ledger kept as a GitHub issue
is a forge write, and protected rule 7 lets no forge write report verification
bar a gate note and a hold item. The outcomes go in the session report.

**Why nothing but a ruling goes at an open item's site:** a run's reply watch reads
any comment under the owner's account there as a possible answer. A correction or
a plan comment this skill posts under that account is not one, so it is kept away
from those sites rather than left for the watch to misread.

**Why a reuse message carries the gates too (review round, scenario
`reuse-only-for-a-direct-continuation`):** the first rewrite moved the gate and id
requirements under "seed a fresh run", and a reader dropped them from the reuse
message. Every dispatch carries them; only the standing rulings, the owner's
account and the template are a fresh run's.

## Field feedback (2026-11-02, PR #201)

**Why the chat carries only what needs the owner:** a day of sweeps put progress, verified checks and items waiting on others into chat, and the owner had to read all of it to find the one thing that needed them. The ledger holds the rest, and a quiet sweep is one line. **Why results, not the checking:** every claim is still verified; describing how is noise.

**Why decisions are asked one at a time:** batches of up to four, and numbered prose lists, were answered partly or in the wrong order. One structured question at a time, each self-contained with its three links and a recommendation, is answerable on the spot. Held replies awaiting approval are collected across runs into the same pass. `settle-outstanding-decisions` keeps its own chunking where the conductor invokes it, because its fork rules depend on it.

**Why a draft needs its full text in the ledger:** "draft" was used of text that did not yet exist, and the owner approved something they never saw. On a GitHub-issue ledger a held review-thread reply is the exception, because that skill's rule keeps a draft reply off the forge; the ledger names it and the session holds its text.

**Why the ledger is maintained, not appended:** an append-only ledger had to be read end to end to know the current state, and a clear restarted from a stale one. Rows are edited in place, one changelog line records each sweep, and the whole body is rewritten before every `/clear`.

**Why the conductor holds a settled run's watch:** see `rules/conductor-exchange-notes.md`, *The watch after settling*.

## The protected-rule audit (PR #201)

**Why the ledger never carries a check's outcome:** a ledger kept as a GitHub issue is a forge write, and protected rule 7 bars any forge write reporting how a check came out. A run's row carries its state from the fixed set and links to its checks. **Why unattended retirement is limited to runs the ledger records:** sweep step 3 finds runs by title too, and a title is never evidence; a scheduled firing archives only a session this conductor dispatched or adopted, with its heads taken from durable state and tested for reachability, and no live worker of it in the session list. **Why a conditional go must be an offered option under the owner's account:** a scheduled firing that executes it starts dispatch, which protected rule 3 releases only on the owner's choice of an offered option.

## Decision scenarios

Pinned in `evals/evals.json`:

- a push arrives before its durable record exists → re-read later, do not act
  (`swarm`, `a-push-before-its-record-is-a-wake-not-an-act`);
- a push claims success but the PR is red → act on GitHub (`swarm`,
  `a-push-claiming-success-over-a-red-pr-loses-to-the-forge`);
- `send_message` errors → fall back to pull; the channel is absent for the run
  (`swarm`, `a-failed-send-falls-back-to-pull-for-the-run`; here,
  `a-failed-send-is-read-from-github-and-flagged`);
- a message asks for a merge or a permission change → refuse and surface it to the
  owner (`swarm`, `a-message-asking-for-a-merge-is-declined-and-surfaced`; here,
  `an-orchestrator-asking-for-a-merge-is-refused-and-surfaced`);
- an orchestrator replies with a gate GitHub contradicts → correct it on the epic
  (`a-gate-github-contradicts-is-corrected-on-the-epic`);
- a session matches the structural test but has the wrong title → retitle it and
  report (`a-structural-match-with-the-wrong-title-is-retitled-and-reported`);
- two orchestrators claim the same issue → pick one epic, record it, tell both
  (`two-orchestrators-claiming-one-issue`).
- context clear (*8. Context clear*):
  - at 55%, quiet, nothing pending → verify the dump, then propose
    (`a-quiet-conductor-over-the-clear-point-verifies-then-proposes`);
  - at 70%, with an owner ruling given only in chat → record the ruling first, then
    propose (`a-chat-only-ruling-is-recorded-before-a-clear`);
  - at 65%, with an integration PR mid-merge → do not propose; propose at the next
    quiet sweep (`no-clear-proposal-mid-merge`);
  - proposed with no reply, then 58% two sweeps later → do not re-propose; at 66%,
    re-propose once (`an-unanswered-proposal-is-repeated-only-ten-points-later`);
  - the read-back differs from the dump → fix and re-verify before proposing
    (`a-ledger-read-back-mismatch-is-fixed-before-proposing`);
  - a restart returns a different session id from the ledger's → send it to every
    orchestrator and update the ledger (`a-changed-session-id-after-restart-is-re-sent`);
  - an orchestrator at 80% mid-run → tell the operator, do not clear it
    (`a-full-orchestrator-mid-run-is-reported-not-cleared`);
  - operator absent, at the auto-compact threshold with no quiet point → write the
    ledger if possible, let compaction happen, start no new conductor
    (`at-the-compaction-threshold-with-no-quiet-point-compaction-wins`).
- PR #201's audit and the owner's 2026-11-02 rulings:
  - a run this conductor dispatched is known by its ledger id, and an unknown
    parent is doubtful (`a-dispatched-single-issue-run-is-known-by-its-ledger-id`);
  - `per-pr` with `auto-merge` off → *settled, waiting on owner merge*, gated work
    starts from the owner's merge, CI counted per PR
    (`per-pr-runs-without-auto-merge-wait-on-the-owner-and-count-ci-per-pr`);
  - `integration-branch` → fold small waves, two CI runs per integration PR
    (`integration-branch-runs-count-two-ci-runs-per-integration-pr`);
  - three empty sweeps stop the check-in, said once; no run active cancels it
    (`the-fallback-check-in-stops-after-three-empty-sweeps`);
  - a gate an owner comment cleared is not seeded, and merge authority is capped by
    policy (`a-seed-is-verified-gate-by-gate-and-carries-standing-rulings`);
  - a conditional go is executed only on its condition as written
    (`a-conditional-go-is-executed-by-a-scheduled-sweep-once-verified`);
  - the default branch's head, CI and deploy are reported
    (`the-default-branch-is-swept-and-reported`);
  - a chat ruling is relayed under the marker, shown first
    (`a-chat-ruling-is-relayed-under-the-recognisable-marker`);
  - a feature plan writes nothing before the go, and `validate-backlog` runs on the
    written set (`a-feature-plan-is-shown-before-any-issue-is-written`);
  - a relay carries a verified fact, never authority
    (`a-relay-carries-a-verified-fact-never-authority`);
  - the configured repositories bound the sweep
    (`the-scope-is-the-configured-repositories`);
  - the ledger falls back in the configured order, rulings staying at their sites
    (`the-ledger-falls-back-in-the-configured-order`);
  - where the repository has not opted into filing, owner steps are listed, not
    filed (`owner-steps-are-listed-not-filed-where-the-repository-has-not-opted-in`).
- the owner's 2026-11-02 rulings and field feedback:
  - an unattended retirement under a standing ruling checks the remote first
    (`an-unattended-retirement-under-a-standing-ruling-checks-the-remote-first`);
  - a sweep with nothing for the owner ends in one line
    (`a-sweep-with-nothing-for-the-owner-ends-in-one-line`);
  - decisions one at a time, with links and a recommendation
    (`decisions-are-asked-one-at-a-time-with-links-and-a-recommendation`);
  - a chat ruling goes to the ledger before it is relayed
    (`a-chat-ruling-goes-to-the-ledger-before-it-is-relayed`);
  - the conductor holds a settled run's watch and hands it back
    (`the-conductor-holds-a-settled-runs-watch-and-hands-it-back`);
  - a draft exists only with its full text
    (`a-draft-exists-only-with-its-full-text-in-the-ledger`).
