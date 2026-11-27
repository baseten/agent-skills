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
to every orchestrator of its workstream, so it is the one place where a mistake would propagate to
all of them. Keeping it to collection, planning and owner-approved dispatch means
its worst failure is a wrong plan the owner approved, never an act. (Planning left
it on 2026-11-04; see *Why planning moved out*.)

**What it is for, and the two deployments (owner's ruling, 2026-11-02; its planning
half superseded on 2026-11-04, below):** project
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

**Why planning moved out (owner's ruling, 2026-11-04):** the conductor's jobs are
the portfolio — which epics run, in what order and how many at once, the conflicts
and gates between them — relaying between sessions, and being the one place the
owner decides. Feature planning is a different job with its own conversation, and it
grew past what a section here could hold, so it became `plan-feature`, after
`write-spec`. The conductor keeps intake: an epic arrives as a link or a planner's
pointer, joins the ledger, and waits on the owner's *dispatch?*. It may still write
one small issue, shown in full first, because sending one issue through a planner
costs more than it saves. Its worst failure stays a wrong dispatch the owner
approved, never an act.

**Why one conductor per workstream, with no shared ledger (owner's ruling, 2026-11-16):** the
first version assumed one conductor overall — one ledger, runs on other projects
tracked in that same ledger, and a second `Conductor:` session on a repository in
scope treated as a conflict. The owner ruled the other way: one conductor per
project or workstream, several in parallel, each with its own ledger, and two may
cover the same repositories — at work every project runs on the same two. A
single ledger across projects grows past what one session can keep in context,
and one owner pass across unrelated projects interleaves decisions nobody is
weighing together. So the peer rule is stated once at the top, and each section
says only what a peer changes there. Scenarios: `a-peer-conductors-run-on-the-same-repo-is-not-adopted-or-retitled`,
`a-peer-conductor-found-in-the-sweep-is-a-peer-not-a-conflict`,
`an-epic-of-another-workstream-is-not-taken-in`.

## The `status` mode

**Why a `status` mode (owner, 2026-11-16):** the owner wanted the conductor's state
on demand without being walked through decisions. The owner pass is the one step
that needs them to answer, so `status` is the sweep with that step left out: it asks
nothing and rules nothing, and acts within the bounds a scheduled firing already
has, since executing an already-recorded conditional go is not ruling (*1. Sweep*).
It is not a second process: it renders through the same snapshot every sweep does
(*The status snapshot*), so on-demand and scheduled status cannot disagree.

**Why an argument, not a command:** a skill is entered through its own name, and
`/status` is already the client's own command, so the mode is `conductor`'s argument
like `validate-backlog`'s modes are. A layer that extends `conductor` is handed it
verbatim (`references/run-start.md`) and must pass it back when it invokes
`conductor`, since a layer decides how its arguments combine. **Why it is never
recorded:** the ledger and the restart prompt carry invocation arguments so a restart
resumes the same configuration (*Configuration*); a recorded `status` would turn
every restart into a status turn. **Why it always rebuilds the work queue:** the
owner asking for status is asking for the page too, and republishing from this
turn's snapshot is what repairs a page that drifted. **Why it stops with no
ledger:** a status request is not a start, and a ledger created by one would be a
conductor nobody configured.

Scenario: `status-sweeps-asks-nothing-and-rebuilds-the-queue`.

## Configuration

**Why the scope is a configured list (owner's ruling, 2026-11-02):** "one
repository" fit the first deployment and not the work one, where a feature spans a
web app and its API. The list resolves from the home repository because the
conductor's keys scope to the conductor, while each repository keeps its own
`manual-steps` and merge authority, as `rules/agent-policy.md`, *Resolution*,
already requires for a per-PR or per-issue key.

## Runtime

**Why the app route comes first (owner's request, 2026-11-20):** *Runtime* was a
binary, cloud or local, and local meant the CLI. A Claude Code session in the
desktop app is local too — same machine, same checkouts — but it also holds
`start_session`, and the binary sent it down the CLI branch. On 2026-11-20 a
dispatched orchestrator sat blocked on a question for six minutes while the owner
could not find it: a `claude --bg` process shows nowhere in the app. A run made
with `start_session` is in the sidebar, can be opened and stopped there, reports
back when its turn ends, and has its worktree archived with it.

**Why fall through silently:** the earlier contract asked nothing about the
runtime, and the owner's go names the work, not the mechanism. **Why confirm by
listing:** the same day, on the owner's machine, bare `claude` was a wrapper that
printed a redirect and exited 0 having started nothing; the first dispatch was
caught only by listing sessions. **Why one more listing before falling through:**
a create that worked but lists late would otherwise be made twice. **Why the
route is recorded per run:** `claude agents --json` does not list an app session
and the app's `list_sessions` does not list a `claude --bg` one, so reading a run
by the other route reports a live run as gone.

**What the app tools were read as (2026-11-20, from the owner's own app sessions,
since this repository's sessions run in the CLI):** `start_session` takes
`initiation` (`user_asked`, `own_initiative`, `offer` — an offer puts a card to
the owner and waits for an answer), `context` (`fresh` needs a `background` of 80
characters or more), `cwd`, `use_worktree`, `name`, `title` and `prompt`, and
returns "Started session … (session_id: local_…)"; `list_sessions` rows carry
`sessionId`, `cwd`, `isRunning`, `isArchived`, `permissionMode`, `link` and
`startedBy`; `get_session` takes a `session_id` or `self`; `list_events` returns
a session's recent turns; `send_message` and `archive_session` take the
`local_…` id. Whether `list_events` shows a held permission prompt's literal tool
string was not seen, so the read-one row says the item reports it unread rather
than guess it. An app run, holding `send_message`, reports with it, which is why
the shared rule's `SendMessage` clause is now the CLI's alone.

**Why a local runtime (owner's request and rulings, 2026-11-19):** the contract was
written around the cloud session tools — `list_sessions`, `get_session`,
`create_session`, `send_message`, `set_session_title`, `send_later` and
`cross_session_inbound` — and a conductor started in a local Claude Code session
has none of them, so it could not run locally at all, though the runs it
dispatches already do. The owner ruled: runs are dispatched in the conductor's own
environment by default; a local conductor sends a run to the cloud only where the
owner says so, in the invocation or that run's go, and the ledger records it; a
cloud conductor cannot start a session on the owner's machine and says so; cloud
behaviour is unchanged. **Why one table, not a second copy of the steps:** every
step already names what it does to a session — list, read, create, message,
release, check in — so the mapping lives once, and each step points at its
operation; a runtime-specific branch appears only where the decision differs
(provenance in *1. Sweep*, the clear point in *8. Context clear*, the
conductor-posted go). Scenarios:
`a-local-conductor-dispatches-local-by-default`,
`an-owner-named-cloud-run-from-a-local-conductor`,
`a-local-release-never-discards-unpushed-work`,
`a-cloud-conductor-cannot-start-a-local-session`.

**What was run to establish each local mechanic (2026-11-19, Claude Code
2.1.327, macOS; the CLI was invoked through a wrapper, `claude-work`, which the
contract calls `claude`).** Every test session was a throwaway on Haiku, stopped
and removed at once, and `claude agents --json --all` afterwards listed none.

| mechanic | command | observed |
|---|---|---|
| this session's record | `env`; `claude agents --json` | `CLAUDE_PID`, `CLAUDE_CODE_SESSION_ID` and `CLAUDE_CODE_MESSAGING_SOCKET=/tmp/cc-socks/<pid>.sock` are set in the Bash tool; the listing's row with that `pid` carries the same `sessionId`, a `name`, `cwd`, `kind`, `status`. No row field carries context usage, a parent session or a repository |
| create | `claude --bg -n "bgtest: trivial" -w bgtest-wt --model haiku --permission-mode dontAsk --allowedTools "Bash(git commit:*)" -- "<prompt>"`, in a checkout | printed `backgrounded · d31ae0f0 · bgtest: trivial` and returned; the session ran in `.claude/worktrees/bgtest-wt` on branch `worktree-bgtest-wt`. **Without `--`** the prompt was read as an `--allowedTools` value; **in an untrusted directory** it refused: `Workspace not trusted. Run claude in <dir> once and accept the trust prompt` |
| survives the conductor | `ps` on the session's ancestry | `bg-spare` ← `bg-pty-host` ← `claude daemon run --origin transient --spawned-by {"label":"claude --bg",…}`, whose parent is `launchd` (pid 1): the launching process had already exited, so a run does not depend on the session that dispatched it |
| read one | `claude agents --json`; `claude logs <id>` | a background row adds `id` (short), `kind: background` and `state` (`working`, `done`); one blocked on a permission prompt read `status: waiting`, `waitingFor: "permission prompt"`. `logs` prints raw terminal output, ANSI included, legible once stripped |
| message, same mode | `SendMessage` to `bgtest: message` (both sessions in `bypassPermissions`) | delivered; the session answered with `SendMessage` to the `from` it was given, `uds:/tmp/cc-socks/<conductor pid>.sock`, and the reply reached the sending session. A name with `: ` in it addresses fine |
| message, other mode | `SendMessage` to a session started `--permission-mode manual` | held, not delivered: the session showed an approval prompt for the message and read `waitingFor: "permission prompt"`; the delivery notice, which reaches the sending session, said the usual cause is differing permission modes and that a hold in a session nobody attends expires undelivered. Hence *Runtime*'s same-mode rule and *2. Ask*'s held-notice clause |
| release with unpushed work | `claude rm d31ae0f0`, after the session committed in its worktree | exit 1: `kept d31ae0f0 — 1 unpushed commit on "worktree-bgtest-wt" … It exists on no remote, so deleting the worktree would lose it`, offering `--discard-unpushed <sha>@<worktree-id>`. `claude stop` then kept the worktree; `rm --discard-unpushed` (used only on this throwaway) removed the worktree and its branch |
| check-in | a background session called `CronCreate` one-shot for 19:00, then `CronList` | listed `[session-only]`, `next run 6:59pm`; it fired at 18:58 as a new turn in the idle background session. The tool's description: session-only, gone when Claude exits, fires only while idle, recurring jobs expire after 7 days |
| tools present | a `claude -p` session's `ToolSearch` | `CronCreate`, `CronList`, `CronDelete`, `ListAgents`, `ScheduleWakeup` (only in `/loop`), `Monitor`; **no tool renames a session** — hence `-n` at creation and the operator's `/rename` |
| cloud from local | `claude -p --output-format json --cloud "<prompt>"`; `claude --bg --cloud "<prompt>"` | both refused, creating nothing: `Starting a new cloud session with --cloud is interactive only` and `--bg and --cloud can't be combined`. The first error names `claude -p "message" --cloud <session-id>` for messaging an existing one |

**Taken from documentation, not run here:** `claude -p "<message>" --cloud <id>`
queues one message and exits without a reply, printing the session id (`--output-format
json` gives `{ok, session_id, url}`), and a cloud session "receives your message but
cannot message any session back yet" (`ListAgents`'s description) — so the channel
to a cloud run from a local conductor is one-way, its status the forge's, which is
the existing absent-channel reading; `/clear` locally starts a new conversation in the
same process (the commands reference), so the restart's id check stays; a
`CronCreate` job is restored on `--resume` but not otherwise carried past exit (the
scheduled-tasks reference). **Not established:** whether a `CronCreate` job survives
`/clear` — the restart prompt re-arms it where `CronList` shows it gone, so either
answer is safe; whether a local conductor's `ListAgents` lists cloud sessions without
Remote Control (a local parent observed on 2026-11-12 listed none, `swarm`'s
`runtime-remote.md`) — so a cloud run under a local conductor is read from the forge,
never the listing; what nothing fires while the machine sleeps means for a daemon
session mid-turn.

**Why `rm` is archiving, and the discard value is never passed:** `rm` deletes the
session's worktree, which is what protected rule 9 guards; its own refusal on
unpushed commits is a backstop, and the `--discard-unpushed` value it offers is
exactly the act that rule forbids, so the retirement conditions bind before it, as
for any archive.

**Why a local conductor posts no go itself:** a conductor-posted go is accepted only
after the run reads the conductor's transcript with `list_events` and finds the
owner's input (`rules/conductor-exchange.md`, *A conductor-posted go*, check (d)). No
run, local or cloud, can read a local session's transcript that way, so such a go
would stay pending for ever; owner-posted is the form that works, and nothing in
protected rule 3 changes.

**Why no provenance locally:** `claude agents --json` names no parent, so the
mark *1. Sweep*, step 2, rests on is missing; a session the ledger lacks is then
found, if at all, by title or structure, and it stays a doubtful match until the
owner's go adopts it, peer or not — more cautious, never less. The first draft sent
it on to steps 3 and 4 as a run; the blind audit on #227 found that a peer local
conductor not yet renamed `Conductor:` would then have its runs asked for status.

**Why the local release, cloud-run retirement and permission mode read as they do
(blind audit on #227):** `claude stop` is only reached once every archive condition
holds, `RUNNING` read from `status`/`state` `working`, since swarm never archives a
running session. A cloud run under a local conductor is listed only on what the
forge and its state block show, and its unread conditions are the owner's to check
on claude.ai before archiving, rather than disclosed and skipped. A held prompt's
literal tool string is read from `claude logs`, since `waitingFor` names only
"permission prompt" (protected rule 9). Dispatching in the conductor's own mode
means a bypass-mode conductor's runs meet no prompt; that is the operator's choice,
so the go's question says so rather than this skill picking a mode.
A local run's own `swarm` workers are subagents or serialized, never listed
sessions, so the `bo/` parent test has nothing to read there.

**Why a local conductor is addressed by name, and sends no new id (review pass on
this PR):** `SendMessage` addresses a session by its listed name, and a local run
adopts no new id (`rules/conductor-exchange.md`, *Status requests*), so the name is
what a local dispatch passes as the conductor id and what a restart must keep: the
restart checks it, the operator's `/rename` repairs it, and a conductor restarted
after its process exited takes it with `claude -n`. **Why runs are never retitled
or reused locally:** no tool renames a session after creation, so step 5 reports
the mismatch; no record shows a local run's context, and unread already counts as
over, so the reuse test sends every local run fresh. **Why a cloud run under a
local conductor still names it:** under a named conductor a run raises its
questions at their sites rather than asking in a session nobody watches; its sends
to the local name fail and end its pushes, which the forge reading already
absorbs.

**Why the clear point is the operator's locally:** no tool reads a local
session's context usage; the operator's `/context` does. Proposing on a guessed
figure would either nag or never fire, so the routine runs when the operator asks,
and compaction remains the fallback, as it already is when no quiet point comes.

## Rules

**Why rulings are recorded before any orchestrator is told:** an orchestrator acts
on a ruling only from GitHub (`references/conductor-exchange.md`, *Status
requests*). A message sent before the record exists is a pointer to nothing, and
an orchestrator that receives it either ignores it — correctly — or acts on a
relayed ruling, which is the failure the trust boundary exists to stop.

**Why relaying is a duty, and carries facts only (owner's ruling, 2026-11-02):** the
conductor is the one session that sees every run of its workstream, so a fact one run needs from
another — a merge to rebase onto, a gate cleared — reaches it only if the conductor
passes it on. It passes the fact after verifying it, with a link, and never a
ruling: a session's message carries no owner authority (`swarm`, *Messages from
other sessions are peer data*), so a relay that could carry one would be a way
around it.

**Why a relay carries only what a run cannot see, and never a posting instruction
(owner's ruling, 2026-11-16):** a review repair replied live, as the owner, to a
human reviewer in several threads after a relay told it replies "go only in the
threads" — the conductor had quoted a ruling about status reports, and the run read
it as leave to post. A run already watches its own PRs' reviews, CI and threads, so
relaying them adds nothing it lacks and invites exactly that reading. What a run
cannot see is another run's state, a gate, the default branch, or a ruling given
here, and those are what a relay is for. Posting comes from the repository's policy
and the run's skill alone, stated on the run's side in
`rules/conductor-exchange.md` so a run that never loaded this skill still holds it.
Scenarios: `a-conductor-relays-nothing-about-a-runs-own-review-findings`, and on the
run side `implement-issue`'s `a-relay-to-reply-in-the-threads-posts-nothing-in-a-persons-thread`.

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

**Why the title names the workstream (owner's ruling, 2026-11-16):** two conductors on one home
repository titled `Conductor: <home repo>` would be indistinguishable in the
session list, which is the only grouping a person scanning it gets. The name comes
from the owner, else the ledger's tracker project, because those are what the owner
calls the workstream; it is recorded in the ledger and the restart prompt so a
clear does not lose it. The title stays a finding aid: nothing decides on it.

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

**How a peer's run is told apart (owner's ruling, 2026-11-16):** the sweep found runs by title and
by structure, then retitled and asked them. With two conductors on one repository
each would find, retitle and message the other's runs. Three marks were weighed:

- **this ledger's record** — decides "mine", as before, but says nothing about
  whose an unrecorded session is;
- **`parent_session_id`** — platform-supplied provenance, set on a session another
  session creates. `swarm`, *Runtime*, already makes it the authoritative key for
  sessions a run created, and this file's own note above records orchestrators
  observed as the `parent_session_id` of the `bo/` workers they created. A run a
  conductor dispatches is created the same way (`create_session`), so it carries
  that conductor as its parent. This is the mark used;
- **the dispatch prompt's conductor id** — every run records it in its state block,
  but that lives in the run's own output, which a sweep cannot read without asking,
  and asking is the message a peer's run must not get.

So a session whose parent is another session is that session's, whatever its title
or structure, and a session whose parent is this conductor (or an earlier id of
it, which the ledger now keeps for this purpose) is this conductor's even where a
crash lost its ledger row. **What provenance cannot see** is a run nobody created
from a session — one the owner started by hand, then adopted by a peer; adoption is
recorded only in the adopting ledger, which no peer reads. Where a peer covers the
repository, such a run is therefore a doubtful match, as a non-structural match
already was, and the owner's go adopts it. Where no peer is in sight the sweep
behaves exactly as before, so a single-conductor deployment loses nothing. The
`Conductor:` title is used here only to narrow what this conductor does — a wrong
title can make it more cautious, never make it act — which is why a finding aid is
enough for it. Not yet observed: a `get_session` on a run a conductor created,
showing the conductor as its parent; the first two-conductor sweep should confirm
it, and where it does not, every peer's run falls to the doubtful-match case,
which still never acts.

**Why a peer is not a conflict (owner's ruling, 2026-11-16):** the earlier text made a second
`Conductor:` session something to put to the owner. Under the ruling it is the
expected state, so reporting it each sweep would be noise; it is noted in the
ledger, and never messaged, because what a peer conductor would do with a message
is not this contract's to define.

**Why step 7 reads the owner's pending review (owner's report, 2026-11-18, FE Testing
Guild run):** the owner had draft comments on a run's PR, unsubmitted, and nothing
put them in front of them, no run acts on an unsubmitted review, and a sweep on
2026-11-17 had read such drafts as edits to a run's comments. The sweep now reads it
per run's PR and *Report* makes it a *Review and submit* item labelled as the
owner's unsubmitted review. It shares the group with a reviewer's drafted review
because the act is the same, and the two cannot meet on one PR: `reviewers.md`
starts a reviewer only on a PR no run owns. **Why "unread" is tested by `gh api
user` (review round 1 on this PR):** GitHub shows a pending review only to its
author's account, so a sweep reading as any other account would see "none" where
there is one; a run under the owner's account can read it, which is why the item
says no run acts on it, not that none can see it. **Why step 7 reads the reviews
itself:** the first version took the count from `prdata.py`, which runs only over
the PRs the merge section or a held reply names, so a run's PR outside both was
never read; the review read is now part of step 7's read of each run's PR, and
`prdata.py` keeps its field for the merge section. Scenario:
`an-owner-pending-review-is-surfaced-not-misread`.

**Why step 6 compares a run's version with the install (owner's request,
2026-11-18, a close-conductor run):** the ledger recorded each run's version line
and nothing read it. Two `backlog-orchestrator` runs reported a093d8f7
(2026-11-11), older than the 2026-11-13 change that moved worker reports from PR
comments to messages (`swarm` NOTES, *Why the carrier is chosen by runtime*), and
their workers posted "Worker report" and "Repair r1" comments on
closeio/close-ui#30068 under the owner's account; the next repair would have posted
again. **Why the compare API decides, not "committed later" (review round 1 on
this PR, a deliberate departure from the request's wording):** the owner asked for
a run to be stale where the install's `committed` is later. Read literally, any
later commit to the repository — a README, a script — flags every live run, and a
run's line carries only a day, in its committer's offset, so dates mis-order
across timezones. So the compare route on the agent-skills repository (the `repo`
in the install stamp, never a workstream's) decides: stale only where the install
is ahead by a change under `skills/` or `rules/`, the paths a run's contract is
made of. Where it cannot be read, dates still give a warning, marked unconfirmed,
and a gap under two days orders nothing. A missing stamp or line is unreadable
rather than stale, because absence is not a verdict. A run's layer line is skipped
because a layer's `metadata.version` stamps another repository; the conductor's
own version is read by `rules/run-start.md`'s whole order, `metadata.version`
included, since an uploaded conductor is still agent-skills. **Why the conductor's own `.source` comes first (owner's ruling,
2026-11-18, on this PR):** the request named `.agent-skills-install`, but
`rules/run-start.md` reads that only where the skill's own directory cannot be
found, because a merge-only install can leave it describing a different install.
Compared against a stale stamp, a run older than the skills the conductor itself
runs could read as current. So the comparison reads `committed` in
the order the conductor's own version line does, and the restatement points at
that rule. **Why the owner is asked before anything goes to the run, and the run
never told to post differently:** a relayed ruling or a submitted review wakes the
run, and it then acts under the contract it loaded; the conductor cannot stop the
owner submitting a review, so the line says that a review wakes it, and the
conductor holds everything it would send. That hold first sat only in the owner
pass; review round 1 on this PR found the relay duty, *3. Reconcile*'s messages and
the post-clear id message each sending without it, and a firing or `status` turn
having no owner pass at all. So it is stated in *Rules*, where every send reads it,
pointed at from each, and what falls due unanswered waits in the ledger. Telling
the run to post otherwise would be a message changing posting, which
`rules/conductor-exchange.md` rules out; the remedy is a redispatch on the current
skills. **Why the redispatch waits for the archive:** dispatched at once, both runs
would work the same PRs; so the answer is a go that executes only once the stale
run is retired under the existing conditions (protected rule 9), which waive only
its wrap-up, and its PRs move to the new run then. *(Since 2026-11-27 the waiver covers only the wrap-up comment, the handover comes first, and each PR's move, to the replacement or a single-issue run, is recorded before the archive: `Why a run is not retired without its handover`, below.)* The option carries what
*6. Dispatch* puts in any go's question, so choosing it is a valid go rather than
one assembled afterwards. Scenarios: `a-stale-run-is-flagged-before-its-next-repair`,
`nothing-goes-to-a-stale-run-before-the-owner-answers`,
`a-docs-only-gap-is-not-a-stale-run`.

**Why a handed-back watch keeps the check-in hourly, and a merge is named (owner's report, 2026-11-18):** a run on a contract older than #214 may report that it handed its PR watch to the conductor, which holds none, so those PRs are watched by nothing but the fallback check-in. The check-in therefore keeps its hourly schedule while any is open, not stopped by empty sweeps until the 7-day bound that rule keeps, when the PR becomes a *Needs you* item (`rules/wake-budget.md`, *A conductor's fallback sweep*; owner's ruling, review round 1 on #226), and the report says so, so the owner knows the latency is an hour. The stale item names a merge beside a submitted review because the owner's merge is the other act that wakes such a run, which then wraps up under its old contract. Scenario: `a-handed-back-watch-keeps-the-check-in-hourly`.

## The status snapshot

**Why one snapshot (owner, 2026-11-16):** in a real run the conductor's chat
summary, its work-queue page and its ledger drifted apart. The page dropped items
the chat still showed, and the check-in prompt went stale, still carrying
comparands an earlier turn had read. Each output had been assembled separately —
the chat from one pass, the page from another read, the prompt from whenever the
check-in was last armed — so nothing made them agree. One snapshot per sweep,
rendered by every output of that turn, makes agreement a property of the
construction rather than of care.

**Why a structure in the turn, not a record:** *7. Ledger* says the body is the
state, and the work queue is a view because a second store drifts from the first
(*The work queue*). A snapshot persisted anywhere would be a third store. Held in
the turn and read by no later one, it cannot outlive the sweep that took it; the
ledger, updated from it, stays what a restart reads.

**Why "every output that shows that kind of item", not "every output":** the outputs
legitimately differ in what they carry — a forge ledger never holds a check's
outcome (protected rule 7), a `github-issue` ledger only names held replies, and
the chat reprints *Needs you* only when it changed (`references/operator-output.md`).
The rule binds membership within a kind, which is what drifted, and makes every
abbreviation count from the same snapshot, so an unchanged line's count matches the
page it links.

**Why the check-in prompt is replaced when it differs:** the prompt is the next
firing's comparison baseline. Re-armed only after a delta, it kept the comparands
of the turn that armed it while attended turns moved the ledger, so a firing could
report as new what the owner had already seen, or miss a change. The armed check-in
is replaced, keeping its time, so one check-in remains (*The fallback check-in*);
`rules/wake-budget.md`'s re-arm at an attended invocation's first step is
unchanged and is simply superseded by the turn's own snapshot at its end.

Scenarios: `a-needs-you-item-in-the-chat-is-on-the-queue-from-one-snapshot`,
`a-firing-refreshes-the-check-in-prompt-from-its-own-snapshot`.

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

**Why held replies are listed, not asked, and a ruling for a person's thread is
drafted (owner's ruling, 2026-11-16):** no run posts in a review thread a person
other than the owner is in, not even a reply the owner approved
(`resolve-pr-comment/NOTES.md`, *Replies held for the owner*). Asking approve, edit
or reject before a post nobody may make only adds a step, so the pass lists each
held reply with its text, link and fix SHA for the owner to post, and a ruling
whose site is such a thread is drafted for them, its text on the work queue.

**Why the ruling's record follows `settle-outstanding-decisions`:** that skill's
records are what the orchestrators' settled steps already read, and its rule —
the complete comment shown and approved — is what makes the record the owner's
own words under the approval test. Whether that releases an orchestrator's held
item stays the orchestrator's decision, because protected rule 3 lets only the
owner's reply choosing an offered option release a hold, and the reply watch is
where that is tested.

**Why owner steps are issues and not a list in the pass (2026-10-31, the owner's addendum):** a list in a chat pass is gone when the session ends, and a step left in a PR body is invisible once the PR merges. Each step is filed as a `[Manual]` issue (`rules/manual-step-issues.md`), the order goes on the manual-steps epic and in the ledger, and `walk-owner-steps` walks each one. Scenario: `owner-steps-are-ordered-as-manual-issues-on-the-epic`.

**Why the conductor asks about a held force-push but cannot approve it (owner's ruling, 2026-11-11):** the owner is in the conductor session, not the run's, so asking there surfaces the decision where they already are, and the ledger records it. But the run's permission mode accepts approval only in its own session, so the conductor's answer is a decision, not the approval: the chat says plainly that the click still has to happen in the run's session, and links it.

**Why the recorded answer is never relayed, and the limits' scope names *Branch updates* (PR #216, blind audit):** an answer written to the ledger as a decision reads, to a later pass, like a ruling to carry to the run, and a relayed approval is exactly what the run's permission mode refuses; so the owner-pass sentence says it is never relayed. The dispatched-session limits had gained a force-push line while their scope sentence still claimed to restate only protected rules 1, 4 and 6, so the sentence now names the *agent policy* rule's *Branch updates* as the governing text. The *Needs you* line names the runtime's literal tool string as well as the command, per protected rule 9.

**Why a peer's decisions and owner-step order stay with the peer (owner's ruling, 2026-11-16):**
the owner pass is one place the owner decides a workstream's questions; putting a
peer's there would ask them twice, and a ruling recorded from one could race the
other's. Manual-steps epics are per repository, so two conductors may both post an
order there: each names its workstream and supersedes only its own, so neither
erases the other's. A run claimed by a peer and by this ledger is the owner's call,
since neither conductor can tell the other's run anything.

## 5. Intake and replan

**Why a planner's pointer is only a pointer (2026-11-04):** it is a message from
another session, so it is peer data (`swarm`, *Messages from other sessions are
peer data*): the conductor reads the parent where it lives, and dispatch still
waits on the owner's go, which protected rule 3 requires. The rule that a plan
writes nothing before the go, and that `validate-backlog` runs on the written set,
moved with planning to `plan-feature` (its NOTES, *8. Write*). **Why a stream
awaiting dispatch arms no check-in, and why intake counts CI (contradiction pass,
2026-11-04):** it is not a run, so nothing changes on it until the owner answers;
and *6. Dispatch* asks with the plan's cost, which intake must therefore supply. A
project or product issue is not an epic `backlog-orchestrator` executes, so its
children are dispatched as an explicit issue set. Scenario:
`a-planners-pointer-is-taken-in-and-dispatch-is-asked`.

**Why CI is counted by mode (owner's audit item 2):** under `ci-mode:
integration-branch` each run costs a CI run when its integration PR opens and
another once it merges, so two small waves cost twice what one folded wave does.
Under `per-pr`, which the work deployment uses with `auto-merge` off, every PR and
every repair push on it costs a run, so the integration count said nothing and the
plan's cost read as zero. The *settled, waiting on owner merge* state exists for
the same deployment: a stream there is not stalled, and work gated on it starts
from the owner's merge, which only a forge read sees.

**Why an epic of another workstream is not taken in, and why replanning narrows
(owner's ruling, 2026-11-16):** an epic belongs to the workstream whose tracker project or recorded go
holds it; taking it in here would put one stream in two ledgers. Every conductor
on a repository also sees every issue opened there, so "unscheduled issues since
the last sweep" would pull a peer's follow-ups into this DAG. The set narrows to
this workstream's, and an issue under none goes to the owner rather than to
whichever conductor swept first. Collisions with a peer's PRs — files, version
bumps, migrations — stay each run's own preflight's, and are reported where seen.
**The default branch's CI and deploy are swept by every conductor on it**, which
duplicates a read but no write, and each owner report needs that fact; it is left
as is.

## 6. Dispatch

**Why a conditional go, and why it stays within protected rule 3 (owner's audit
item 5):** the owner often decides the next batch before its gate clears — "start
the #967 batch when #2049 wave 5 merges" — and then had to come back to say go. The
go is recorded where any go is, so it is the owner's own recorded choice; what the
sweep adds is only the verification that the stated condition holds on the forge.
A condition the forge cannot show is not interpreted; it waits.

**Why a verified plain go needs no second confirmation (owner, 2026-11-15):** a plain go the owner posted after the pass that drafted it waited for the owner to say "go" again in chat, while a conditional go verified the same way was already executed by a scheduled firing. Both are the owner's recorded word, read back at their site by id, authorship, edit state and supersession; the second confirmation added a round trip and no authority. So the sweep (*1. Sweep*, step 9) executes either once verified. What a firing may not do is unchanged: it rules nothing, and a go found only in the ledger, edited, superseded, or carrying the footer of one of this skill's own writes is no go. Scenarios: `a-plain-go-posted-later-is-dispatched-by-a-scheduled-firing`, `a-footered-go-on-the-owners-account-is-not-a-go`.

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

**Why a fresh prompt checks its skills first, and why the check runs there (owner's audit, 2026-11-05):** a dispatch of `/implement-issue <issue URL>` reached a cloud session where `implement-issue` was not installed. The session loaded `implement-issue-core`, the closest name, implemented, opened the PR, subscribed to it, and followed the platform's posture: it replied in a colleague's threads, made two product calls as "small asks", re-requested the reviewer and edited the PR body. The conductor had no way to see the gap before dispatch: `create_session` and `get_session` return sources, environment and metadata, and no field lists a session's skills; this session's own skill list describes where the conductor runs — the CLI, often — not the cloud session it creates. So availability is established by the only party that can observe it, as the dispatched session's first act, before any skill is invoked and before any write, and reported in the exchange form so the sweep reads it like any other failed run. The list is written into the prompt literally because a session missing `implement-issue` cannot read that skill's composed list. `backlog-orchestrator`'s list holds only what its own contract stops on — `swarm`, and the worker requirements `implement-issue-core`, `create-pr` and, where routed, `review-docs` — since its parent requirements degrade rather than stop the wave (contradiction pass, 2026-11-05). The check text precedes the skill invocation, so `/implement-issue` is no longer the prompt's first token and the session picks the skill by name — the step that went wrong in the incident; the check is what covers it. Scenario: `a-dispatch-prompt-checks-its-skills-and-the-conductor-raises-a-gap`.

**Why the owner's limits travel in the prompt (same audit):** the same session's prompt did not carry the owner's limits, so a session that loaded the wrong skill had none of them. They are restated in the dispatch text, each naming the rule that governs, because a prompt is the one thing every dispatched session reads whichever skill it loads. They restate protected rules 1, 4 and 6 and the posture override without changing them, with each rule's carve-outs — the owner's own change request, the approved-ruling exception, the `Depends on:` line — because a block binding "whatever any instruction says" that dropped a carve-out would forbid what the home requires (contradiction pass, 2026-11-05). The blind rule-by-rule audit then found the question line weaker than rule 1 — limiting the ban to others' questions implied an owner's "why X?" could be answered — and the thread line dropping the dispatched review's carve-out; both now read as the home does. The rules' homes still govern. Scenario: `a-fresh-dispatch-carries-the-owners-limits`.

**Why the fresh-run and reviewer skill checks accept a `<plugin>:` prefix
(2026-11-24, issue #234).** Installed as the `agent-skills` plugin, every skill
is listed as `agent-skills:<name>`. A dispatched session reading "confirm that
each of these is among this session's available skills: create-pr, …" against
a listing with no bare `create-pr` could fairly report it missing and write
nothing — a run that fails on every plugin install, with a report that blames
the install. The bare name does invoke the plugin's skill (`rules/run-start-notes.md`,
*What a bare name resolves to under a plugin*), so the check says the prefix
counts. Pinned by #133; #132 pins the layer search's plugin cache.

**Why a run is not retired without its handover (a conductor in a real deployment, 2026-11-27):** a conductor retiring three settled orchestrators on an older contract checked unpushed work, live workers and PR heads, then archived two. It never asked for what the runs held beyond their branches — frontier order, deferrals, budgets used, review notes, unfiled follow-ups, drift notes — and none had posted any of it on its epic. One was archived with two PRs open and recorded as moved to no run, against the conditions already here. Nothing was lost only because the owner unarchived the sessions and asked each for a handover. So the handover is now a condition of every retirement, stale or not, and "every issue in its set accounted for in the ledger" sits beside "every PR merged, closed or recorded as moved", checked against the epic as the forge reads it, not against the run's own list. **Why the stale waiver was narrowed:** "needs no wrap-up" was read as "needs nothing of its state"; it now waives only the comment on the epic, which an older contract never posts. **Why the request spells out its parts:** the runs most often retired this way are stale, and a stale run's contract may predate *The handover*, so the request carries the parts itself. **Why an unobtainable handover goes to the owner, not to a best effort:** an absent channel or a gone session means part of the run's state may exist nowhere else; only the owner can accept that loss, so the item names what is unrecoverable beside what the checkpoint comment and the forge do show. **Why the PR moves are recorded before the archive:** the incident archived a run whose open PRs were moved to nothing; "recorded as moved on archiving" let the archive happen first. **From the blind protected-rule audit of this change:** an owner's answer retiring a run without its handover was first written with no limit, which could read as waiving the stranded-work checks too; it now waives the handover alone (protected rule 9). Only a reply from the run's recorded session is its handover, since it now decides a replacement's scope and budgets, and a prompt or handover written to a forge ledger withholds any check's outcome (protected rule 7). Scenarios: `retire-and-redispatch-takes-the-handover-first`, `no-handover-means-no-retirement-until-the-owner-rules`, `retiring-without-a-handover-waives-only-the-handover`; conductor #5 #31 #38 #39 now state the handover as present, and #115's expected answer names it.

**Why the replacement is an orchestrator, not one run per issue (same incident):** the conductor replaced the retired orchestrators with one single-issue run per conflicted PR. That fits new work; mid-epic it drops what the orchestrator was holding — the frontier order, the deferrals, the budget used, the cross-issue drift notes — because no single-issue run reads them. So the default is a fresh `backlog-orchestrator` on the same epic, started from the handover (`backlog-orchestrator`, *Started from a handover*), with a single-issue run offered only for a PR that needs work before that run would reach it, and that PR named in the new run's prompt as owned elsewhere so two runs never push to it.

## Reviewers

Keyed to `reviewers.md`, which holds the rules; it sits beside `SKILL.md` so the
conductor's contract stays readable, as `backlog-orchestrator` keeps
`integration-branch.md` (owner's ruling, 2026-11-09).

**Why reviewer sessions (owner's rulings, 2026-11-05 and 2026-11-06):** the owner is
asked to review colleagues' PRs every day, and many wait on nobody else. A session
that drafts the review turns each into one read and one submit. The drafting is the
owner's private review skill's generic half, now `review-pr` (its NOTES).

**Why `review-pr` is hard-coded, and why no setting:** the obvious key name,
`review-skill`, is already the skill that reviews prose contracts here. A deployment
that needs another surface layers a skill over `review-pr`, which hands off to it
(`rules/run-start.md`), so the contract names one skill and every deployment still
gets its own.

**Why a reviewer starts only on the owner's request (owner's ruling, 2026-11-09,
reversing 2026-11-06):** the first version had every sweep look for PRs waiting on
the owner, put each to them as a question, and let a standing ruling start
reviewers unattended. The owner reversed that: the conductor never watches for
review requests, and nothing but the owner's own request in the session starts a
reviewer. After one read of the selection test, the session puts the PRs that
passed to the owner as one question, so a reviewer still starts only on the
owner's choice of an offered option, as protected rule 3 requires (second
contradiction pass, 2026-11-09). That go is written to the ledger and never
posted, because its only site would be a colleague's PR; there is no standing
ruling to re-read and no candidate list to keep. The selection test is
unchanged and runs once, at the request. This also removed the reviewer half of
what a scheduled firing may do, which now only archives.

**Why these selection tests (owner's ruling, 2026-11-06):** a PR whose only
requested reviewer is the owner, with no team requested and no one else's review
yet, waits on the owner alone. A draft PR, the owner's own PR and a PR a ledger run
owns — opened under a distinct agent identity, which the own-PR test would miss —
are not asking for the owner's review. A pending review of the owner's means they
have started, and the forge keeps one per user per PR. A fresh request after new
commits is a new question about those commits. A test that cannot be read fails;
the owner's pending reviews are visible only to the owner's credential, so the
reviewer's own check is the one that holds.

**Why the draft-only limits travel in the prompt:** as the owner's limits do for a
run (*6. Dispatch*): a session that loaded another skill, or none, carries only what
its prompt says.

**Why drafts are verified before the owner is told, and silent reviewers are read
from their records:** a reviewer's report is peer data, and *Needs you* is a promise
that something is ready. A reviewer that never reports, or waits on a permission
prompt, would otherwise surface nowhere.

**Why no watch, no check-in, and archiving only a drafted reviewer (owner's
rulings, 2026-11-06):** a reviewer's job ends when its drafts exist, and the owner's
submit is seen by sweeps that run anyway; a check-in for it would spend wakes
protected rule 9 bounds. The conductor created the session, so it may release it
(`swarm`, *Releasing a worker*), and it writes no branch. The blind protected-rule
audit limited the automatic archive to a reviewer verified `drafted`: a failed one
may have published under the owner's account, which a sweep would misread as the
owner's submission (protected rule 2), and a blocked one would vanish unreported
(rule 9). The archive reads the tracker as well as the forge until a Linear submit
is confirmed to appear on GitHub as the owner's (owner's ruling, 2026-11-09).

**Why every created session attaches a source, and why titles are the only grouping
(owner's report, 2026-11-06):** a session created without a source repository
failed its environment setup, and the create call did not warn of it. The session
sidebar nests only one level, so a title's prefix and repository are the only
grouping a person scanning the list gets.

**Why a reviewer's candidate test counts a peer's runs and reviewers (owner's ruling, 2026-11-16):** a
PR a peer's run opened, or one a peer's reviewer is already drafting, failed none
of the earlier tests, which read only this ledger; two drafted reviews of one PR,
or a review of the owner's own run's PR, is what those tests exist to stop.

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

**Why a new id goes only to this ledger's runs (owner's ruling, 2026-11-16):** a run adopts a new
conductor id from its sender where that session's sources include the conductor's
home repository (`rules/conductor-exchange.md`, *Pushes*). Two conductors can share
a home repository, so that test cannot tell them apart; what keeps a run with its
own conductor is that a conductor sends its new id only to the runs its ledger
records. The run-side residual is recorded in `rules/conductor-exchange-notes.md`.

**Why the restart prompt builds a missing work queue (owner's report, 2026-11-18, FE
Testing Guild run):** the prompt only confirmed the queue's watch "where the ledger
records one", so a conductor that had never built a queue restarted with nothing
telling it to, and ran on without one. The dump now records the URL or its absence,
and where it is absent and the tool is held, the prompt says to build it first. The
rule that does the building is *Report*'s (*The work queue*, below); this is its
restatement at the restart's decision point. Scenario:
`a-restart-with-no-work-queue-recorded-builds-one-first`.

## 7. Ledger

**Why the ledger's home is configurable (owner's ruling, 2026-11-02):** the work
deployment keeps plans in its tracker's project documents, with a document store
as fallback, not in GitHub issues. The kinds are named generically so this skill
stays tracker-agnostic; which tracker and store they mean is the session's
connected tools. Rulings never move into the ledger: they stay where the decision
lives, so a run reads them where its own tests look.

**Why each run's row carries its version line (owner's decision, 2026-11-06):**
an owner audit could not tell which skill revision a dispatched session had run.
The row records what the run's reports said — `not reported` where none carried a
line, which is itself the finding — and nothing the conductor inferred. The
conductor's own line opens its first report, under the same rule
(`rules/run-start.md`). Since 2026-11-18 the row also carries the installed version
and the comparison *1. Sweep*, step 6, makes; the reported line is still recorded
as the run gave it, and the verdict sits beside it, never in its place.

**Why the ledger keeps earlier session ids and the peers seen (owner's ruling, 2026-11-16):** the
provenance test in *1. Sweep* needs every id this conductor has had, or a run
created before an id change would read as another session's. Peers are recorded
so the next context, after a clear, does not rediscover and re-report them.

**Why each dispatch prompt is recorded as sent (same incident):** the ledger held a rebuilt approximation of each run's dispatch prompt, written afterwards, and the seed template — the first prompt of the last good run — pointed at it. A rebuilt prompt records what the conductor remembers sending, which is not what the run read; seeding from it repeats whatever the memory dropped. So the prompt is written to the ledger at dispatch, verbatim, or linked where it is held verbatim, and the seed template is taken only from that record. An approximation already in a ledger stays labelled as one and is never a seed.

**Why a size budget, at about 70% (same deployment, day 11):** "maintained, not appended to" did not hold. The changelog kept every line since day one, and posted or superseded drafts stayed in the body, until a Linear document save was refused at 250,000 characters (`rules/linear-mechanics.md`, *Documents*). A refused ledger write loses the sweep's record, so the budget acts well before the cap: at about 70% the history that the body does not need — changelog lines older than the last clear, drafts no longer pending — leaves the body for the document's history or a linked archive document, with a one-line pointer. The state never moves, since the body is what a restart reads. It names the platform's limit rather than a number so another tracker's cap applies the same way.

**Why a `document-store-page` is named beside `github-issue` (review of #248, folded into the drafts change, 2026-11-27):** the budget named Linear's cap and said none is established for a `github-issue` ledger, and left the Notion-page fallback unnamed, which a reader could take as covered by Linear's number or as forgotten. No cap on a Notion page's body has been observed here, so it is stated in the same place as not established, and the budget does not reach it yet. **How the budget and the drafts agree:** a pending draft is state and stays in the body in full; it moves out once posted or superseded, and "posted" is the event `work-queue.md`, *Drafts to post*, defines — read at its site, or for a Notion or Slack draft the owner's tick read back — so the page and the ledger close a draft on one event. Scenario: `a-notion-page-ledger-has-no-size-budget-yet`.

## The work queue

*Report*, its last paragraph; *7. Ledger*, the queue's URL; *Rules*, where a check's
outcome may sit (owner's brief, 2026-11-06).

**Why a page at all:** on a busy day *Needs you* outgrows a chat report. The owner
worked through it from a published page, so the report could stay short, as
operator output wants: what changed, plus a link. **Why republishing is tied to the
report that changes the list:** a hand-made first version went stale overnight. A
page that is refreshed only when someone remembers is worse than none, because it
reads as current.

**Why it is a view, never a record:** *7. Ledger* says the body is the state. A
page holding something recorded nowhere else, or a tick the conductor acted on,
would be a second store of open items, and the two would drift as the hand-made
page did. So it renders the report's own *Needs you*, nothing is recorded only on
it, and a viewer's ticks are a convenience the conductor never acts on. Since
2026-11-16 they are saved on the page and carried across a republish, so the
conductor no longer overwrites them; carrying a mark is not acting on it. The ledger records the page's URL so a restart after a clear
republishes to the same place. **The one addition (review round 1 on #226):** "Your PRs" also lists a run's PRs waiting on their team, which are not *Needs you*. A PR whose next step is the owner's is a *Needs you* item in every output, so the chat and the page agree; one waiting on the team is shown as waiting and counted in the report's *Unchanged* line, which is the same snapshot's count. *The status snapshot* names this as the only thing the page shows beyond *Needs you*, so the one-snapshot rule still holds.

**Why it renders the report, not the ledger (contradiction pass, 2026-11-06):** the
brief said the page renders the ledger and records nothing the ledger lacks. Read
strictly, that drops items: the ledger holds no tool string for a *Confirm in a
session* item, and a forge ledger never carries a check's outcome, so a red default
branch under *Clear a failure* is in the report but not the ledger (protected rule
7). Rendering the report keeps the owner's point — no second store — without
dropping either. *Rules* says a check's outcome may sit on the page because it is
not a forge write. Since 2026-11-16 the report and the page render the same
snapshot (*The status snapshot*), which is what makes "renders the report" hold.

**Why private, and never shared:** its items can carry the owner's internal work —
issue titles, decisions, held replies' sites and text — on whatever repositories the
conductor is scoped to. This repository is public and its skills run at work and
at home alike, so the contract states the privacy itself rather than leaving it to
the platform's default.

**Why the order is not new:** it reuses the owner pass's — what frees the most
downstream work first, owner steps by dependency — inside the report's own groups,
rather than inventing a second ranking. **Why a scheduled firing republishes too:**
its report can change *Needs you*, and a page left at the last attended report is
the stale page this exists to prevent; a firing that cannot publish leaves the page
showing its earlier read time.

**Why the tracker inbox is excluded:** the owner's tracker inbox (Linear's, or any
other) spans every project and team, and the conductor is scoped to its configured
repositories (*Configuration*), so reading it would pull work from outside that
scope into the queue. Its items are only what the sweep already collects; the build reads links and draft counts for those items alone, never the inbox. The
contract states that half at the decision point: the page renders the report's
*Needs you*, which only the sweep collects.

**Why optional:** not every session can publish a page. Where none can, nothing
changes: the ledger link carries the list, as before.

**Why the link and the publish hang on the recorded URL (review round 1, PR #208):**
"every report links it" read as unconditional, and readers linked, even published,
a queue in scenarios that never said one could exist. The ledger's record of the URL
is the one thing a report can check, so a link appears only where it is recorded,
and a page was created only by a report whose *Needs you* changed, from a session
holding a tool that publishes one.

**Why any sweep now builds the first page (owner's report, 2026-11-18, FE Testing
Guild run):** that rule left a gap. A conductor whose list never changed while it
could publish — quiet attended sweeps, then firings — never built a queue, and ran
two days without one. So a sweep of any kind that finds no URL in the ledger while
the session holds the Artifact tool builds the first page that turn as *Which
page* says for a first publish — read-only, upgraded that turn where the watch
lists it (*The work queue page*, below) — and records its URL; the link still appears
only once the URL is recorded. A session with no such tool is unchanged, which is
why `an-unchanged-needs-you-list-is-one-line` now says the session holds none.
Scenario: `a-quiet-sweep-with-no-work-queue-recorded-builds-the-first-page`.

**Why a PR item carries up to four links in that order (owner's ruling, 2026-11-06):** a
review the owner had drafted in the tracker's review view, not yet submitted, was
invisible from a queue item linking only the forge PR, so the item read as nothing
waiting on them. The tracker's review page sits beside the PR, marked with the draft count, because that is where the drafts are; the closing issues follow, or "no linked issue", because an item with no issue is a question in itself. **The order changed on the owner's ruling of 2026-11-11** to worker session, PR, review page, issue, in the chat and on the page alike: the session is where the owner acts on a run, so it leads, and one order everywhere means the owner's eye finds each link in the same place. Drafts held elsewhere were linked to their text or named where held, as
*Approve drafts* is in the chat. **Since the owner's ruling of 2026-11-16, a reply or
ruling the owner is to post in a thread where no run posts** (`resolve-pr-comment`,
*Replies held for the owner*) **is carried on the page in full** — text, the
thread's recorded `html_url` and the fix SHA — because the owner now copies, edits
and posts it themselves, and a page that only names where the text is held makes
them go and fetch it. The page is private and is not the ledger, so the
`github-issue` ledger's rule of naming such drafts only does not reach it. (Widened on 2026-11-27 to every draft the owner posts, from any surface: *Drafts to post*, below.) A draft's location is a claim about current state,
so it is read each sweep (*establish, do not assume*), never carried from memory,
and a change in a PR item's links or draft count republishes the page even where
the list is otherwise unchanged: otherwise a submitted draft would stay counted on
a page every report links (contradiction pass, review round 1 of PR #208). That is
also why the *Rules* line on subagent results exempts these links, which are
re-read rather than persisted. *(#226 briefly made the review link a layer's alone; the blind audit of #226 restored the conductor's own Linear read and the account label, so this entry stands. A layer may still supply its own link — `The work queue page`, "Why the review slot stayed generic".)* **The count is labelled with the tracker account
that holds the drafts**, because the tracker returns the calling account's drafts
only, and *Configuration* never takes the owner's account from a credential. The tracker's tool specifics live in the *Linear mechanics* rule, where
the next tracker's would go beside them.

Scenarios: `a-changed-needs-you-republishes-the-work-queue-in-the-same-turn`,
`with-no-page-to-publish-the-ledger-carries-the-list`,
`the-work-queue-takes-nothing-from-the-tracker-inbox`,
`the-first-changed-report-creates-the-work-queue-and-records-its-url`,
`an-unchanged-list-links-a-kept-queue-without-republishing`,
`a-scheduled-firing-republishes-a-changed-work-queue`,
`a-red-default-branch-is-on-the-page-never-in-a-forge-ledger`,
`a-tracker-review-draft-is-marked-on-the-queue-item`,
`a-pr-with-no-linked-issue-says-so`,
`a-reply-the-owner-posts-is-on-the-queue-in-full` (renamed from `a-reply-draft-held-in-the-ledger-is-linked-and-labelled`, 2026-11-27, below),
`a-quiet-sweep-with-no-work-queue-recorded-builds-the-first-page`.

**Why the work queue and the check-in are per conductor (owner's ruling, 2026-11-16):** each is bound
to one session and recorded in its ledger, so a peer's is simply another; the
wording says so only so that "one check-in, never two" is not read across
conductors.

## The work queue page (`work-queue.md`, owner's request, 2026-11-16)

**Why the template, the scripts and the schema ship with the skill:** the owner ran
the page by hand from a template, a state file and four scripts, and asked for them
in the skill. They are generalised: every link is a recorded URL, the title names
the workstream, and nothing names a repository, a tracker or a person. A layer adds
its own `--pending-blocker` patterns for checks that wait on a person.

**What changed on the way in:** the owner's scripts were written and run in a cloud
session, where the thread read's REST route, `pulls/{n}/ccr/review_threads`, is the
one that works. It is cloud-only: a local session gets a 404 for it (run 2026-11-16,
`gh api repos/baseten/agent-skills/pulls/223/ccr/review_threads` → `Not Found (HTTP
404)`), which the first local port read as an empty list, so every count came out 0.
GraphQL is the reverse, working locally and refused in cloud (next entry), so
`prdata.py` reads by whichever route answers, paginates every list, and stops on
any failed read. `mergeq.py` and `prune.py` read the sweep's
`prdata.py` output instead of GitHub, so the page renders the turn's one snapshot.
`prune.py` keeps an unposted reply on a merged PR: its asker is still unanswered.

**Why threads are read by two routes (observed 2026-11-17, a Claude Code cloud conductor
session):** there, `python3` 3.13 with the standard library and `gh` 2.89 were
present; `gh auth status` reported the token invalid while `gh api` REST calls
succeeded through the session's proxy, and `gh api user` returned the owner's login.
`gh api graphql` returned HTTP 403, "GitHub GraphQL is not available from Claude Code
sessions; use the REST API", pointing review threads at `GET
/repos/{owner}/{repo}/pulls/{n}/ccr/review_threads`. That route answered there, each
entry shaped `{"comment_ids": [...], "path": ..., "line": ..., "resolved": ...,
"outdated": ...}` with the ids in thread order; a comment's author and body come from
`pulls/{n}/comments` (one paginated read) or `pulls/comments/{id}`. Locally the
opposite holds: the `ccr` route is a 404 and GraphQL works. So `prdata.py` tries
GraphQL, falls back on a 403 to the `ccr` route, and stops where neither answers; both
routes feed one counting function, so the answered and "fixed, needs a reply" rule
cannot differ by route. The session also exposes `ccr` routes that resolve and
unresolve a thread; the script never calls them, since nothing here resolves one
(#222). **Run to establish it:** the GraphQL route against eight real PRs of this
repository, output identical to the previous script's in every thread count; the
`ccr` route only against a fixture of entries in the observed shape (an owner reply,
a reviewer-last outdated thread, an owner question, a resolved thread, an id missing
from the bulk read), plus a 403-then-404 case that stops and a non-403 GraphQL
failure that stops without falling back — a cloud session has not yet run the script.
**Why a pending review's comments are read first (owner's report, 2026-11-18, FE
Testing Guild run):** on a cloud session, `pulls/{n}/ccr/review_threads` listed a
thread whose last comment was in the owner's unsubmitted review. That comment is in
neither `pulls/{n}/comments` nor `pulls/comments/{id}`, which returned 404, and the
script stopped, losing the whole merge section. A PENDING review is visible only to
its author, so `prdata.py` now reads every PENDING review the reviews list returns
through `pulls/{n}/reviews/{id}/comments` before any single-comment read, and every
other 404 still stops it. GraphQL's `reviewThreads` includes the viewer's pending
comments too, with `state: PENDING`, so that route reads the state and both feed one
rule: a thread whose last comment is in the owner's pending review is the owner's to
finish, counted neither open nor answered, and the review's id and comment count
become `owner_pending_review` and `owner_pending_drafts`, which `mergeq.py` shows as
a blocker. A pending last comment by another login is counted open, failing closed.
Where `gh api user` is not the owner's login, or cannot be read, the owner's
pending review is invisible to the script, so its fields are null, never 0, and
`mergeq.py` shows the review as unread (review round 1 on this PR).
**Run to establish it:** `scripts/test_work_queue_prdata.py`, which runs both scripts
against a stubbed `gh` over a fixture of that shape, by both routes; against the
previous `prdata.py` it fails with the reported 404 on `pulls/comments/5001`. The
GraphQL field was read live on 2026-11-18: `comments(last:1){nodes{state}}` on
cli/cli#13251 returned `SUBMITTED`; a `PENDING` value has not been observed live
here, only in the schema and the owner's report.

**Why `gh auth status` is not the test:** it reported failure where every read worked,
so `work-queue.md` takes a successful `gh api user` as the test of a working `gh`.

**Which page, and why gated:** tested on 2026-11-16, a republish woke nothing, a
connector call from the page failed with "Couldn't load this connector", and
nothing let a page or a session type `/clear`. Only `comments.sendToClaude` woke the
session, and only for a writer of the page. So the page is interactive only where
the watch listing confirms it, and read-only otherwise, so it never claims an
answer reaches the session when none can.

**Why the listing is read again after a first publish, and every build (owner's
report, 2026-11-18, a close-conductor run):** *Which page* was read before each
build, but a new page's first publish is read-only because no watch can list a
page that does not exist yet, and nothing made a later build look again. One
session published its queue 8 times read-only while `ArtifactComments` `watch`
had listed the page's comment-wake subscription since a minute after the first
publish; the owner saw "Read-only view…" and could not answer. So the listing is
read straight after a first publish, and where it shows the page, the same
snapshot is republished interactive in that turn. *Publishing* allows one publish
per turn to keep the owner's saves from colliding with republishes; the upgrade
is the one exception, stated there, because it changes nothing the owner could
have saved — the read-only page takes no answer — and waiting a turn is what left
the queue read-only. The result goes in the ledger beside the URL so a restart,
and the report's link, know the page's state without guessing; the link says
"read-only, answers here" so the banner is no surprise. **Why the session arms the
watch itself (review round 1 on this PR):** the first version only read the
listing, so a page whose subscription never armed stayed read-only and became an
owner item the owner could do nothing about. The session now calls `watch` with
the page's URL and reads the listing again, on a first publish and on a downgrade;
what still fails is a line beside the queue link, not a *Needs you* item, since the
answer path — this chat — still works. **Mechanism, from the owner's wake tests
against artifact contract 0.2.96:** a publish result's "arming" line is not a watch,
only the listing establishes one; and `composer_only` comments make
`canSendToClaude()` return "off", so the queue always uses the full
`{artifact:{}, comments:{}}`. **Why `build.py` refuses an interactive state with an
unruled option:** an answer records the option's `ruling` text as the complete
comment the owner approved (*Answers*); with none, the pick could only become a
draft, after the owner believed they had answered. A read-only page records no
answer, so it still builds. Review round 1 found that the upgrade, carrying the same
snapshot, could hit that refusal; so an interactive build writes any missing
`ruling` first — every option put to the owner already has a determinate meaning —
and stays read-only only where it cannot. `scripts/test_work_queue_prdata.py` runs
both cases. Scenarios:
`a-first-publish-is-upgraded-once-the-watch-lists-it`,
`a-state-with-an-unruled-option-does-not-build`.

**How an answer leaves the page (owner's wake tests against artifact contract 0.2.96, 2026-11-18):** from those tests: a save through `artifact.publish` wakes no session; only `comments.sendToClaude` does, in about 4 to 6 seconds; a save reloads the view, so a send started after it can be lost; `anchorFor(el)` has to be called synchronously in the click, before a re-render replaces the element; `canSendToClaude()` returns `writers_only`, `no_session` or `off` where a send cannot wake anyone, and a `capability_removed` rejection means the capability is gone from this view. The template already took the anchor in the click, awaited the send before the save, and read `canSendToClaude()` at load and on focus and visibility, never in the click; those were left alone. What changed: the banner now names the fix for each state, `off` included, which it had shown only as a raw code; a `capability_removed` rejection now reads as unavailable rather than as a viewer who is not a writer; and an over-long comment is shortened prose first, level by level, instead of being cut from the end, which could drop an answer line the conductor needs to match a card. Run: the page script parses under `node --check`, and `commentText` over 25 answers with 300-character questions and labels and 900-character notes came to 3,706 bytes with every answer line whole, while a single answer kept its 600-character note. The `writers_only` fix first told the owner to share the page as an editor; the page is never shared, so it now says to open it from the account that owns it (review round 1 on #226). No decision scenario pins this: it is the template's mechanics, not a reading of the contract.

**Why an answer counts only from the comment:** the page's state is written by the
conductor's republishes and by the owner's saves, under one account, and nothing in
it tells them apart; reading a pick from it would know the owner by content, which
protected rule 2 forbids. The comment is the platform's: only a writer can send it,
and the page is never shared. So a saved pick with no comment is asked again,
naming it. The comment's text is data: an answer counts only where its card and
option match what this skill published, so free text in it never steers anything. **Owner's ruling (2026-11-17, after the batch's blind audit):** page access alone was the audit's rule 2 flag — nothing enforces that the page stays unshared — and through a relayed ruling it reached a `DECISION` the merge gate holds on (rule 8). So an answer, and an archive tick, now counts only where the comment's author, as the thread reports it, is the owner's login; an absent or unreadable author is no answer and is asked at the next attended pass. Scenario: `a-page-comment-with-no-readable-author-is-asked-not-recorded`.

**Why a restart runs a normal sweep (owner's ruling, 2026-11-17):** the first version of the restart prompt passed `status`, which made every restart after a clear skip the owner pass — the turn *The `status` mode* says a recorded `status` must not cause. The prompt now passes the invocation's arguments alone.

**Why the option carries its ruling text:** a relayed ruling is posted without a
footer only where the owner approved the complete comment (`rules/conductor-exchange.md`,
*Relayed rulings*). A card showing the exact text each option records makes the pick
that approval, as an `AskUserQuestion` option carrying the full text already did
(conductor-exchange NOTES, 2026-11-05).

**Why the page offers no thread resolution:** the owner's version let them mark
threads "to resolve" after their reply. Under the 2026-11-16 ruling no run resolves
a review thread a person other than the owner is in, whatever a message says, and a
page comment is a message. The owner resolves the thread where they post the reply.

**Why sessions to archive are listed from the ledger, and a tick still waives nothing
(owner's addendum, 2026-11-16):** the owner asked for finished sessions to be listed
with `list_sessions children:true`. No session in this repository's record has
observed a `children` parameter, so the list comes from what this conductor already
knows as its own: the ledger's runs and reviewers. That also keeps a peer conductor's
runs off it. `status_bucket` is observed (`swarm`, *Runtime*), but a run's finish is
read as *4. Owner pass* defines it. A tick sent in a comment is the owner's go, which
`swarm` requires for a session the run did not create; protected rule 9's remote
checks still run, because the owner ticks from what the page shows, not from the
remote. A saved-only tick is asked again for the reason an answer is.

**When an unresolved thread counts as answered (owner's ruling, 2026-11-16):** a
thread GitHub shows unresolved held "Ready" off the page even where the owner had
answered it and was waiting on nothing. It now counts as answered where its last
comment is by the owner's account and has no `?`; a later reviewer reply reopens it.
The ruling first also counted an outdated thread as answered; the owner corrected
that the same day: a fixed thread still needs their reply, so it stays open and is
shown as "fixed, needs a reply", which is the item the owner acts on. Authorship is the comment author's login, never a footer or the text (protected
rule 2). This changes only how the page and the report read a PR: nothing resolves
the thread, which stays with the owner (#222), and the merge gate (`settle-and-merge`,
*The merge gate*, protected rule 8's home) reads threads by its own rules, so
"answered" never means gate-passing. Field names checked with real queries on
2026-11-16: `gh api graphql` on cli/cli#14951 returned `isResolved`, `isOutdated` and
`comments(last:1){nodes{author{login} body}}`; on cli/cli#13251, `prdata.py` read 3
open threads, and 0 open, 3 answered with the account flag set to their last
commenter (`copilot-pull-request-reviewer`: GraphQL gives a bot's login without
`[bot]`).

**Why an archive tick is an attended answer, not a posted go (owner's ruling,
2026-11-16):** it follows #214, where retirement takes the owner's answer in an
attended turn, written to the ledger with their words. A comment the page sends is
that answer arriving by another route; the remote checks still run.

**Why the restart prompt invokes the skill:** a clear drops the loaded contract with
the rest of the context, so a prompt that only resumed ran the next sweep with no
conductor contract at all; the Close layer had patched this in its own text. Naming
the skill the session was first invoked as reaches the layer where there is one.

**Why one "Your PRs" section with steps read from the forge (owner's request, 2026-11-18):** the page split PR work between "PRs to merge" and a hand-ordered "Run order", so a run's open PR that was not yet approved sat in a list the owner had to keep current by hand, and its next step was a guess. One section now holds every open PR of this ledger's runs, merge rows first, each other PR with the four steps the owner takes it through. Each step's state is a forge fact `prsteps.py` reads from the sweep's `prdata.py` output — not a draft, the team requested or a person reviewing, a person's approval, merged — so the page shows what is true rather than what someone ticked; it offers no checkbox for them, and `build.py` refuses an item whose steps were not read, since a hand-written `done` would be a second store. Held replies keep their tick, a viewer's convenience that is still verified in the thread. **Why the team is the caller's:** the generic skill has no convention for which team reviews a PR, so a layer says where it comes from — for instance a ticket's Review line. **Why the review slot stayed generic (blind audit of #226):** the first version moved the Linear review link out of the generic skill into a layer for neutrality, which dropped it for any conductor running without that layer, a regression on the 2026-11-06 ruling that put it on the page. So the conductor still reads it itself where the repository is linked to Linear (`rules/linear-mechanics.md`, *Review pages*), labelled with the tracker account holding the drafts, since `get_diff_threads` returns only the calling account's, and counted only where read; a layer may supply its own instead. Run: `scripts/test_work_queue_prdata.py` covers each step's reading, the link order and count, a merged PR moving to *Done recently*, a merge row not listed twice, and `build.py` refusing unread steps. **Review round 1 on #226 changed four things here.** The team is matched, ignoring case, against a requested team's slug or name, since a layer names a team as people do ("FE Platform") while GitHub's slug is `fe-platform`; `prdata.py` reports both. "Team approves" is not done while any person's latest review requests changes, and then reads "Changes requested", so an approved PR with an open change request is never pointed at Merge. `build.py`'s guard could not tell a read `done` from a written one, so `prsteps.py` stamps each item `stepsReadAt` and the build requires it: the stamp catches steps `prsteps.py` never filled, and a hand edit after it is forbidden by the rule, not detected by the check (named `stepsReadAt` rather than the review's `steps_read_at` to match the state's other camelCase keys). And removing "Run order" had sent urgent items under "When there's time"; non-PR *Needs you* items now carry their report group and render under it, above "When there's time", which holds only what the report puts at low urgency. Each change has a test case in `scripts/test_work_queue_prdata.py`, and the template was rendered from `state.example.json` through a DOM shim to check the sections' order. **Why merging and marking ready are narrowed (protected rule 8, blind audit of #226):** the first steps offered "Merge" to any approved PR and "Mark ready" to any draft. Offering a merge the merge rows had not cleared invited one past a red check, an open thread or the owner's own unsubmitted review, which is rule 8's gate in effect if not in text; so only a merge row reading Ready is a merge item, and any other approved PR's last step names its blocker. Offering to publish a draft that someone returned to draft would undo a hold (`rules/draft-state.md`, whose discriminator, currently a draft and ever ready, `prdata.py` now reads from the timeline); so a held draft reads "Held in draft" with no owner step. **The re-audit narrowed it further:** `rules/draft-state.md` also holds a draft by explicit instruction, a caller's preference or a repository convention, none of which the timeline shows. So the step fails closed: a draft is offered to mark ready only where its run reported it awaiting the owner's publish, which the conductor passes as `awaitingPublish`, and any other draft reads "Draft" with no owner step. **Why team membership is checked where it can be:** an approval from someone outside the team is not the team's; where `prdata.py` can read the team's members only a member's counts, and elsewhere any person's counts but is labelled unverified, which with the merge-row rule can never by itself surface a merge. A team may leave `requested_teams` once a member reviews, so after that its members are read only where the caller passes `--team` with the slug; a layer resolves its own team names to slugs (the re-audit). **Why the skill names reviewer requests among its nevers (protected rule 4, same audit):** "request its team" became a *Needs you* item, so the contract states that the request is the owner's act and that this skill never requests, re-requests or removes a human reviewer on the forge (`rules/review-trigger.md`). The re-audit found the first wording said "a reviewer", which this skill defines as a `review-pr` session it starts on the owner's go, so it read as forbidding that; it now names a GitHub review request and says a reviewer session is not one. Each has a test case in `scripts/test_work_queue_prdata.py`. Scenarios: `pr-steps-are-read-from-the-forge-not-ticked`, `a-linear-linked-pr-carries-its-review-link`, `urgent-items-keep-their-group-above-when-theres-time`, `an-approved-pr-off-the-merge-rows-is-not-a-merge-item`.

**Why every publish reads the live page first, and another publisher drops its watch (owner's report, 2026-11-18):** "merge before republishing" was read as applying to later publishes only, so a turn's first rebuild went out from a copy built in an earlier turn. Once the page is interactive that erases every answer and tick the owner saved since, so the live read and `carry.py` now precede every publish. Publishing a page also starts the publishing session watching it; a second session that published the conductor's page would then be woken by the owner's answers too, and could act on one the conductor never sees, so it turns that watch off at once. Scenario: `a-publish-reads-the-live-page-first`. *(Narrowed 2026-11-24, below: only a separate session unwatches; a subagent of the conductor's own session never does.)*

**Why the pacing:** each run's reply is its own turn, and a busy hour republished the
page a dozen times, each a chance to collide with the owner's own save. A status
sweep and a publish at most once a turn, and none within five minutes for a change
outside *Needs you*, keeps the page current where it matters.
*(A turn that takes in a submission or a deferred outcome is exempt from the five-minute skip since 2026-11-24, below.)*

**Why a read answer's card is done, in progress or the owner's step, and every submission republishes (owner's report, 2026-11-24, a local conductor's work queue):** *Answers* said to mark each card done and republish, but an outcome is often not final in that turn: a helper agent is still drafting, a session cannot start until the owner types go, a draft waits for the owner's approval. The card had no state for these but `answered`, which the page renders as "Waiting for the conductor to act on it", so cards the conductor had already read sat there as if nobody had; and nothing republished when the outcome landed later, because a local conductor's child sessions and helper agents report straight back, with no PR subscription or sweep to drive a build, and the five-minute skip in *Publishing* swallowed the turns that did happen. So step 4 now gives each read card exactly one state — `done` with the record's link, `progress` naming the session or task, `yours` with the owner's exact next action — and `build.py` refuses any of the three without its `outcome`, the token-level half of the rule; `carry.py` ranks both new states above `answered`, so a live page's wait never overwrites a read card, and between them the build, read from the ledger, wins. Step 6 moved after the thread reply and binds every turn that takes in a submission (answers, `Archive:` ticks, an item the owner removes) whatever the outcomes, and a deferred outcome republishes in the turn it arrives even with *Needs you* otherwise unchanged; *Publishing*'s skip names both as exempt. Both publish through the `status` sweep the turn runs at its end, since a build needs this turn's snapshot and `prdata.py` read (*Building it*), and a turn with no sweep has neither; `SKILL.md`, *The `status` mode*, *Report*, the quiet point in *8. Context clear* and *7. Ledger*'s list of card states say the same at their decision points. `done` is only for a card with nothing left to do: a draft the owner must post is `yours` (post it at its link), never an approval, since a run never posts in a person's thread (`rules/review-feedback.md`). **The same gap in *Sessions to archive*:** a ticked row the conductor had read still rendered "Archive requested; the conductor is on it", including a local conductor's cloud run whose archive is the owner's own step. A read row is now dropped, kept with `done: false` and `why` (the existing failure rule), or given an `outcome` naming who is archiving it or the owner's step, which the template shows in place of the wait. "Removals" in the owner's report is read as an item the owner removes; the page sends no removal of its own today. Scenarios: `a-read-answer-shows-done-in-progress-or-your-step-and-republishes`; `a-work-queue-answer-is-recorded-from-the-comment` now pins the republish after the reply. Run: `scripts/test_work_queue_prdata.py` covers the `outcome` refusal for each state and `carry.py`'s ordering.

**Why a subagent never touches the watch (owner's report, 2026-11-24, same local conductor):** *Publishing* told any publisher other than the conductor — "a subagent's, or one the owner asked to" — to turn its watch off. Watches are scoped to the session, not to the agent inside it, so a helper agent that rebuilt the page inside the conductor's session and then called `on: false` stopped the conductor's own watch and its auto-replies; answers sent from the page reached nobody until the owner asked for the watch back. The 2026-11-18 reason for unwatching — a second session woken by the owner's answers — holds only for a separate session, so the rule now names only that, says a subagent of the conductor's session never touches the watch, and has the conductor's prompt to a helper say so, since the helper reads that prompt and not this contract. Because *Which page* has every build read the watch listing and re-arm through `watch`, a delegated build splits: the conductor reads and re-arms, then hands the helper the chosen row. A watch already lost this way is caught by that downgrade path at the next build. **Contradiction pass before review (same day)** found the first wording forbade a helper the listing read its build needs, left a submission turn with no snapshot to build from, let a drafted go read as either `done` or `yours`, and kept "Nothing waiting on you" and the "Sent to the conductor" heading on read cards; each is fixed above or in the template. Scenarios: `a-helper-agent-never-touches-the-conductors-watch`; `a-publish-reads-the-live-page-first`, rewritten.

Scenarios: conductor#101–110; implement-issue#48, backlog-orchestrator#131 and
settle-outstanding-decisions#23 pin the run side (`rules/conductor-exchange-notes.md`,
*Questions under a conductor*).

## Builds from memory (owner's report, 2026-11-20)

`work-queue.md`, *Building it* and *Publishing*; `build.py`; `carry.py`. **The
failures**, five in one afternoon of one interactive session, all a build put
together from what the session remembered rather than from the ledger and the
forge: both held replies vanished (a rebuild wrote `replies: []`; their text was
safe in the ledger and never read back); three answered decisions reverted to
`open` (`carry.py` caught it); five decisions answered in chat never reached the
page; the PR list kept a closed PR and missed three new ones, because a `prs`
array from an earlier turn was reused instead of re-running `prdata.py`; and items
read "waiting on a reviewer" after the review.

**Why a mechanism, not more instruction:** a scheduled firing has no earlier state
to remember, so it rebuilds; the same session's check-in firings swept markedly
better than its interactive turns, with the same tools and contract. An
interactive turn always has a remembered state, and patching it is cheaper, so
"write it from the snapshot" was read as advice. So the lossy path is closed in
the scripts: `prdata.py` stamps each read, `mergeq.py` and `prsteps.py` carry the
stamp, and `build.py` refuses a merge row or PR item whose stamp is missing or
more than 30 minutes old, naming what to re-run. 30 minutes covers a long sweep's
reads before the build and no earlier turn.

**Why `carry.py` now carries the conductor's half, and why `closed`:** it carried
only the owner's marks, while the text said "so the owner's saved answers and ticks
survive", which read as though merging was handled both ways. A rule that depends
on remembering to re-derive is the class that failed five times, so the script
carries a held reply or decision the build lacks. Carrying alone would resurrect a
reply already posted, so the build lists finished ids under `closed`, from the
ledger, and `carry.py` names everything it carried so the session reads it back.
The owner's saved answer wins over the conductor's status: an answer on the
page is the owner's act, a status in the build this session's reading. It never
replaces an answer the build read from the ledger (Codex on #231): a pick saved
without reaching the conductor (`answer.messaged: false`) is put to the owner to
confirm, and where they then chose otherwise, the ledger's answer is the
confirmed one.

**Run to establish it** (`scripts/test_work_queue_prdata.py`): `build.py` refuses
`state.example.json` as it stands, builds it restamped two minutes ago, refuses it
restamped two hours ago; `carry.py` keeps an answered decision answered over a
rebuilt `open`, keeps the owner's answer over a `done` with another, carries two
dropped replies and a dropped decision and names them, and leaves out the ids
`closed` lists.

## The work queue without `gh api` (2026-11-20)

`work-queue.md`, *Which page*, the route order; `prdata.py --from-json`. **The
incident:** on 2026-11-20 a cloud conductor built no work queue. Its environment
limits `gh` to search ("use gh for nothing else"), and the rule then read "where a
working `gh api` is missing, no page is built". `gh api` REST works in such a
session, but the instruction forbids it; GraphQL returns 403 there.

**Why the instruction counts as not permitted:** it binds the session even where
the command would succeed. A contract reading "it worked, so it is allowed" teaches
a session to probe past its instructions.

**Why the MCP reads feed `prdata.py` rather than a second reader:** the reads
differ, the rule must not. `--from-json` runs the same transform (`pr_row`), so the
settled-thread rule and the stops are stated once.

**What the MCP reads cannot cover**, tested on 2026-11-20 against the live tools:

- **`ever_ready`**: no timeline read. It is written null with `ever_ready_read`
  false, and `prsteps.py` offers no "Mark ready" on that draft: an unread history
  may hide a hold, so it fails closed as draft state does.
- **The owner's pending-comment state**: `get_review_comments` gives no comment
  state and no read of a pending review's comments exists. A thread's last comment
  could sit in the owner's unsubmitted review unseen, so wherever `get_reviews`
  shows a PENDING review by the owner, `owner_pending_read` is false and the merge
  row shows it unread, never 0 drafts.
- **`mergeable`**: computed lazily, so a first read often says `unknown`. It stays
  `unknown`, never guessed.
- **Team slugs**: `get_teams` lists only the user's own teams, so a Review-line
  team the user is not in gets no `--team`, and its step reads "team not verified".
- **Requested teams** (post-merge review of #228): `get` returns no
  `requested_teams`, so #228 read every PR as having none and told the owner to
  request a team already requested. It is now unread (`requested_teams_read`
  false), and the Request step stays the owner's, labelled to check.

**Post-merge review of #228 (2026-11-20).** #228 merged without a review; a
`review-skill` pass afterwards found the gap above and four more, fixed together:
the text said the owner's pending review "comes out unread" where only its count
is, and a reader concluded the *Review and submit* item could not be raised;
`--from-json` counted the owner's own last reply as answered while it might sit in
that unsubmitted review (now held); the page told an awaiting-publish draft with
unread history that its run had not asked; and sweep step 6's `gh api` compare had
no route-order pointer. A document naming no PR now stops. Decision scenario 130
pins the search-only route.

Two shapes differ from REST: a review's user carries no type, so a login ending in
`[bot]` is a bot's on both routes; and a thread comment's `author` is a bare login.
The default branch's CI on this route is read from its Actions workflow runs, not
its head commit's check runs.

## Every event, the refresh, and the REST route (2026-11-26)

`SKILL.md`, *On every event*; `work-queue.md`, *Which page*, *Building it* and
*Publishing*; `refresh.py`; `prdata.py`'s REST form; `build.py`'s warning.
**The incident:** a multi-day cloud conductor on 2026-11-25 (conductor @ 289564e)
repeatedly took in a run's merge report, relayed it and wrote a changelog line,
but ran no `status` sweep, so the work queue went stale; when it did refresh the
page, it hand-patched `state.json`, and the PRs rendered as plain items rather
than "Your PRs". The owner noticed both. The contract was right; it failed where
it was read and in what it cost.

**Why a section of its own:** the event trigger lived in one sentence of *The
`status` mode*, which a turn handling a run's report never reads: it reads *2.
Ask*, *3. Reconcile* and *Report*. Those now point at *On every event*, which holds
the order once. The `status` mode keeps only a pointer, so the rule has one home.

**Why `refresh.py`:** the right path was six scripts in order plus two reads, and
the wrong one was one edit. A conductor that judged the patch "close enough" was
choosing the cheap path, so the wrapper makes the right path the cheap one. It
derives the PRs to read from the same files the build renders (prs.json, the merge
notes, the held replies), so the read and the page cannot disagree about which PRs
there are. It reads no watch listing and publishes nothing: those are tool calls
the session makes, and the row they choose is *Which page*'s. `build.py` now warns
on an item that links a PR and asks to merge it, mark it ready or request review —
a warning, not a refusal, since an item may link a PR for another reason.

**Why a REST route, and why inside `--from-json`:** in that session `gh` was barred
by instruction, the MCP server failed to connect and GraphQL was refused, so the
route list read literally built no page; the conductor built one from REST reads
by hand, which the contract never described. REST reads carry more than the MCP
tools — the timeline, the requested teams, a pending review's comments — so the
REST form adds those keys, and the threads come from the same ccr route `gh`
falls back to, through one function (`ccr_rows`). One transform still states the
settled-thread rule and the stops. Run: a REST-form document for two PRs, one
with the owner's pending review, gave the ready history, requested teams and the
pending draft count as read; `refresh.py --first`, then `--live` over its output,
built both pages; a missing document stopped the refresh at `prdata.py`.

**Why back-to-back merges defer, and why only those:** each merge arrived as its own
turn and changed *Needs you*, so five merges in ten minutes meant five ledger
rewrites and five publishes; the 5-minute skip never applied. A merge report alone
asks nothing of the owner, and the forge holds the merge, so deferring it loses
nothing. Only a turn that owes a sweep defers: a merge that changes no *Needs you*
item waits for the next sweep, as before. Anything else — the owner's message, an
answer, a question from a run, an executed conditional go — still sweeps at once.
**Why the fallback check-in is pulled forward rather than a second one armed:** the
contradiction pass before review found a one-shot beside the fallback broke the
shared wake rule (re-arming replaces, never adds; a check-in that cannot be
cancelled blocks arming), had no prompt or liveness guard of its own, and kept its
armed state only in this session. Pulling the one check-in forward avoids all
but the cancel, and where the runtime cannot cancel, the turn sweeps at once
(protected-rule audit, 2026-11-26); `references/wake-budget.md` and `references/operator-output.md`
state it, the latter giving the deferred turn its line. "A PR merged or closed" left
the list of waking events: the conductor holds no PR watch, so a merge reaches it
only as a run's report or in its own sweep.

## Drafts to post (a live conductor, 2026-11-27)

`work-queue.md`, *Drafts to post* and *Publishing*; `SKILL.md`, *Rules*, *7. Ledger*
and *Report*; `drafts.py`, `build.py`, `carry.py`, `prune.py`, `refresh.py`, the
template. **The incident:** a live conductor on 2026-11-27 had nineteen replies the
owner had to post on the comment threads of one Notion ADR page, and two Slack
messages. The page's copy control rendered only for `replies`, which were shaped
for a review thread (repo, PR, thread URL), and `refresh.py` read every reply's PR,
so a reply with no GitHub PR would have stopped the build. So all twenty-one went
on the page as plain items, their text in `why`, where `rich()` turned backticks
into `<code>`: a copy of the rendered text lost the inline-code marks. The owner
asked why they were not copy and navigate, like the review-thread replies.

**Why every draft the owner posts is one kind of entry:** what the owner does is
the same wherever the text goes — copy it, open the site, paste, post, tick — so one
model carries it, and only what the site needs differs by kind (`drafts.py`).
**Why a sibling `drafts` rather than generalising `replies`:** most kinds are not
replies, and a field named for one kind would mislead the next reader. Old pages
keep loading: a published page carries its own script and state, so it renders as
before; `carry.py`, `prune.py`, `refresh.py`, `build.py` and the template all fold a
state's `replies` into review-thread drafts, and a tick under the old `reply:` key is
read as a draft's. **Why the text sits in a `<pre>`, never through `rich()`:** what is
copied must be exactly what was drafted; the page's formatting is for its own
prose. **Why grouped by `label`:** twelve replies to one Notion page are one visit
to that page.

**Why only PR-bound drafts are read from GitHub, and still fail closed:** a Notion,
Linear, Slack or other draft has no PR, so `refresh.py` skips it rather than
stopping. A review-thread reply or a body edit is read with its PR: its PR's state
is what prunes it. **Why an unreadable draft PR no longer stops the build (owner's
ruling on #249, 2026-11-27):** the first version kept that read failing closed, and
the owner's brief had listed a build stopped by a draft's unreadable PR as part of
the problem: one draft cost the owner the whole page. So `refresh.py` reads a PR
that only a draft names on its own, and where that read fails — no `--from-json`
document for its repository, a PR the document lacks, a refused read — it stamps the
draft `prUnread` with the reason, the page shows it on the card, and the rest
builds. Failing closed still holds where it matters: `prune.py` finds no read of
that PR and treats it as unknown, never merged or closed, so the draft is never
pruned; and the PRs "Your PRs" lists, from `prs.json` and the merge notes, still
stop the refresh when unread, since a count there is never written as zero. Run:
`scripts/test_work_queue_prdata.py` builds a page with a review-thread draft in a
repository with no document and a ticked body edit on a PR the document lacks, both
kept with the warning, the merge rows built; a draft whose PR was read carries none.
The warning was rendered through the DOM shim. Scenario:
`an-unreadable-draft-pr-warns-and-the-page-builds`. **Why `prune.py` never prunes
another kind on a PR's state:** it has none to read, so a Notion draft would either
never leave or leave wrongly; it leaves only when the build omits it and `closed`
lists it. `prune.py` now also drops any draft whose id `closed` lists, since the
ledger shows it finished.

**Why a tick is checked only where the site can be read:** the page is a view, and
a tick a convenience the conductor never acts on (*The work queue*). A review
thread, a PR body and a Linear issue's comments can be read, so the post is
confirmed there; Notion and Slack posts are not checked, per the owner's brief.
**Why such a tick is asked, not acted on (contradiction pass before review):** the
first version closed a Notion or Slack draft on its saved tick. A draft tick is
saved with no comment and so no author, and every other carried mark is never acted
on (*The work queue*; a saved archive tick is asked for the same reason), and
closing a draft moves its text out of the ledger under the size budget. So the next
attended owner pass asks about every such tick in one question, and the owner's
answer, in the ledger with their words, counts the post, unverified at its site.
The same pass named where a body edit and a Linear comment are read (*4. Owner
pass*, step 2), which *Drafts to post* had listed with no step to read them, and
that a held reply's draft shows the comments since its fix (`rules/review-feedback.md`,
*Held replies*). **Why a `github-issue` ledger names off-forge drafts:** a `[PLAN]`
issue would otherwise hold a colleague's Notion thread or a Slack message in full,
which is the reason it already names held replies; the brief kept full text for
tracker-document ledgers. **Why not every draft is one:** text a run posts once the
owner approves it stays an *Approve drafts* item, and a reviewer's drafts stay on
their surface for the owner to submit (`reviewers.md`, which now says so at its own
decision point). **Why a PR body line is a draft:** a created PR's body is edited
only while it is a draft, footered, or under a merge opt-in, and otherwise the
drift is reported with its replacement (protected rule 6); the replacement is now
carried in full, old line beside new, for the owner to make.

**Why cards are collapsed by id (same conductor):** its own build script copied
decisions from the live page and also wrote the cards again, and the page showed
each twice. `carry.py`, which sees the live page, keeps the copy that differs from
the live page's — the build's — and keeps a saved owner answer or tick from the
other, under its existing rule that a saved answer wins over the build's status
but never over an answer the ledger holds; `build.py` collapses any left, first copy
first, and both name them; the template shows one per id for a page published
before. **Why `drafts.py` is loaded by path:** the scripts run under `python3 -I`,
which keeps the working directory off the import path; loading the module from the
script's own directory by an explicit path keeps that guarantee.

**Protected rules.** No protected rule's text changed. The change sits beside rule
1 (a held reply is never posted by a run: still the owner's, and nothing on the
page asks this skill to post or resolve), rule 6 (the body edit is reported, never
made) and rule 7, untouched: whether a draft was posted is not a check's outcome. `rules/operator-output.md`'s *Post
yourself* widened from review threads to every draft the owner posts
(`rules/operator-output-notes.md`).

**Run:** `scripts/test_work_queue_prdata.py`, extended: `build.py` builds a whole
draft of each kind, a Slack one without a link, refuses one lacking any field its
kind needs, an `http` link or an unknown kind, builds an old state carrying only
`replies`, and collapses duplicated cards; `carry.py` carries a page's `replies` as
drafts, a Notion draft's tick and a dropped Slack draft, and collapses a decision
and an item written twice, keeping the build's wording and the owner's answer and
tick; `prune.py` drops a ticked reply and body edit on a merged PR, keeps an unposted
one, a ticked Notion draft naming that PR and a ticked Slack draft, and drops what
`closed` lists; `refresh.py` builds `state.example.json`'s six kinds reading one PR,
stops where a review-thread draft's repository has no document, and builds an old
`replies`-only state. The template, built from `state.example.json` and from a
`replies`-only state carrying a decision twice, was rendered through a DOM shim
under node: every kind showed its text verbatim, backticks intact, under its
destination; a Slack draft offered "Copy and tick", every other "Copy, open and
tick"; a ticked draft folded under *Posted*; the old state rendered its reply as a
draft and the decision once. Scenarios: `every-draft-the-owner-posts-is-on-the-queue-with-its-text`,
`a-tick-is-a-mark-read-at-the-site-where-it-can-be`,
`a-reply-the-owner-posts-is-on-the-queue-in-full` (rewritten: it had a reply no run
may post shown as an *Approve drafts* item linking the ledger, the very shape the
incident found).

**Two-arm round (`scripts/run_evals.py`, base origin/main, conductor scenarios 36,
40, 45, 51, 67, 97, 99, 101, 134, 146, 147, 148):** one Haiku reader per batch of
three per arm, each holding only its arm's contract, and one blind Sonnet grader
seeing the two answers per scenario as A and B. New 53/58, old 46/58. Gained: 40
(comments since the fix shown), 45 (grouped by action; held reply's text off the
list line), 97 (each item's full text), 134 (the owner's step names the draft at
its link), 146 (grouped by page; body edit's old and new lines), 147 (Notion and
Slack never checked; no non-PR draft pruned on a PR). Regressed: 45 (narration in
the *Unchanged* line) and 101 (carry before the republish not mentioned), neither
on text this change touches, so read as reader variance. Both arms failed 146's
copy-and-tick and verbatim assertions, because *Drafts to post* no longer named
the control; it now does. 147 was rewritten after the round, when the
contradiction pass changed a Notion or Slack tick from closing the draft to being
asked about. **A second round on 146 and 147 alone**, same method: new 9/11, old
6/11; gained 146's copy-and-tick and 147's question, pruning and no-post assertions;
regressed 146's body edit showing its old line, which only `drafts.py` stated, so
*Drafts to post* now says it. Both arms still missed grouping by page on 146.

## The contradiction pass before the review round (PR #201)

**What a scheduled firing may do is stated the same at every decision point:** it
sweeps, reports and executes a conditional go the owner already recorded, once
verified; it rules nothing and dispatches nothing else. *(Superseded by the owner's
2026-11-12 ruling, below: a scheduled firing never retires a run.)* **Retiring under a standing
ruling is allowed unattended (owner's ruling, 2026-11-02):** the pass first kept it
to attended sweeps; the owner ruled that a scheduled firing may retire once the
ruling's condition is verified on the forge. Protected rule 9 still binds every
archive: the conditions in *6. Dispatch* — wrap-up posted (for a single-issue run, its
`merged` report and merged PR stand in), every PR settled, each
branch head on the remote, no live worker and no outstanding recovery ref — are
checked on that firing exactly as on an attended one. Scenario:
`an-unattended-retirement-under-a-standing-ruling-checks-the-remote-first` (since #214, `an-attended-turn-asks-which-ready-runs-to-retire-and-checks-the-remote-first`).

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

**Why the chat carries only what needs the owner:** a day of sweeps put progress, verified checks and items waiting on others into chat, and the owner had to read all of it to find the one thing that needed them. The ledger holds the rest. **Why results, not the checking:** every claim is still verified; describing how is noise. Both rules, the three-link header and one question at a time moved to `rules/operator-output.md` on 2026-11-03, which also put state changes back in chat once each and reduced a quiet sweep to its title and one minimal line (`rules/operator-output-notes.md`).

**Why decisions are asked one at a time:** batches of up to four, and numbered prose lists, were answered partly or in the wrong order. The planners' blocking questions are the one exception, and it does not reach this skill (`rules/operator-output-notes.md`, *Questions*). One structured question at a time, each self-contained and recommending an option, with its links on the line above it, is answerable on the spot. Held replies awaiting approval are collected across runs into the same pass. `settle-outstanding-decisions` now asks one per call too (its NOTES, *Ordering*).

**Why a draft needs its full text in the ledger:** "draft" was used of text that did not yet exist, and the owner approved something they never saw. On a GitHub-issue ledger a held review-thread reply is the exception, because that skill's rule keeps a draft reply off the forge; the ledger names it and the session holds its text.

**Why the ledger is maintained, not appended:** an append-only ledger had to be read end to end to know the current state, and a clear restarted from a stale one. Rows are edited in place, one changelog line records each sweep, and the whole body is rewritten before every `/clear`.

*(Superseded by #214: the conductor holds no watch.)* **Why the conductor held a settled run's watch:** see `rules/conductor-exchange-notes.md`, *The watch after settling*.

## The protected-rule audit (PR #201)

**Why the ledger never carries a check's outcome:** a ledger kept as a GitHub issue is a forge write, and protected rule 7 bars any forge write reporting how a check came out. A run's row carries its state from the fixed set and links to its checks. **Why unattended retirement is limited to runs the ledger records:** sweep step 3 finds runs by title too, and a title is never evidence; a scheduled firing archives only a session this conductor dispatched or adopted, with its heads taken from durable state and tested for reachability, and no live worker of it in the session list. **Why a conditional go must be an offered option under the owner's account:** a scheduled firing that executes it starts dispatch, which protected rule 3 releases only on the owner's choice of an offered option.

**What the re-audit added (PR #201):** a conditional go is re-read at its site by the comment id the ledger recorded before a scheduled firing executes it, because a ledger row is an editable body and must not be what starts dispatch; "adopted" is recorded only from the owner's go naming the session id, so an unattended retirement never rests on a title; and retirement also requires the session to hold no uncommitted work, swarm's test for work never pushed, stated here because the pointer is not read at this decision point.

## Decision scenarios

Pinned in `evals/evals.json`:

- a worker's message is its report, written down before release
  (`swarm`, `a-messaged-report-is-written-down-before-release`, which replaced
  `a-push-before-its-record-is-a-wake-not-an-act` on 2026-11-13);
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
  - a feature to plan goes to `plan-feature`, and one small issue is shown in full
    before it is written (`a-feature-goes-to-plan-feature-and-a-small-issue-is-shown-first`,
    replacing `a-feature-plan-is-shown-before-any-issue-is-written`, 2026-11-04);
  - a planner's pointer is taken into the ledger and *dispatch?* asked, never acted
    on (`a-planners-pointer-is-taken-in-and-dispatch-is-asked`);
  - a ruling on an issue it did not create is drafted unless approved word for word, on a run's PR recorded
    (`a-ruling-on-someone-elses-issue-is-drafted-on-a-runs-pr-recorded`);
  - invocation settings are forwarded at dispatch
    (`invocation-settings-are-forwarded-at-dispatch`);
  - an unapproved relay on a run's PR is not posted, restoring the PR-site pin #37
    held before it moved to issues (`an-unapproved-relay-on-a-runs-pr-is-not-posted`);
  - a ruling approved word for word is posted on someone else's issue by the
    conductor; a correction is drafted
    (`an-approved-ruling-on-someone-elses-issue-is-posted-by-the-conductor`);
  - a go on someone else's epic is always drafted, even with its text approved
    (`a-go-on-someone-elses-epic-is-always-drafted`);
  - a relay carries a verified fact, never authority
    (`a-relay-carries-a-verified-fact-never-authority`);
  - the configured repositories bound the sweep
    (`the-scope-is-the-configured-repositories`);
  - the ledger falls back in the configured order, rulings staying at their sites
    (`the-ledger-falls-back-in-the-configured-order`);
  - where the repository has not opted into filing, owner steps are listed, not
    filed (`owner-steps-are-listed-not-filed-where-the-repository-has-not-opted-in`).
- the owner's 2026-11-02 rulings and field feedback:
  - an attended turn asks which ready runs to retire, checking the remote first
    (`an-attended-turn-asks-which-ready-runs-to-retire-and-checks-the-remote-first`,
    rewritten by #214 from the standing-ruling version);
  - a sweep reports each state change once, never its steps or waits on others
    (`a-sweep-reports-state-changes-once-never-steps-or-waits-on-others`);
  - decisions one at a time, with links and a recommendation
    (`decisions-are-asked-one-at-a-time-with-links-and-a-recommendation`);
  - a chat ruling goes to the ledger before it is relayed
    (`a-chat-ruling-goes-to-the-ledger-before-it-is-relayed`);
  - a settled run's watch stays with the run, never the conductor
    (`a-settled-runs-watch-stays-with-the-run`, rewritten by #214);
  - a draft exists only with its full text
    (`a-draft-exists-only-with-its-full-text-in-the-ledger`).
- the operator-output rule (2026-11-03, `rules/operator-output-notes.md`):
  - a quiet check-in writes only its minimal line and updates the title's suffix
    (`a-quiet-check-in-writes-nothing-and-updates-the-title`);
  - an unchanged *Needs you* list is one line
    (`an-unchanged-needs-you-list-is-one-line`);
  - every block has a linked heading and every ref is a link
    (`every-block-has-a-linked-heading-and-every-ref-is-a-link`);
  - a meta question is answered in its own block
    (`a-meta-question-is-answered-in-its-own-block`);
  - *Needs you* is grouped by action, and waits on others and narration stay out
    (`needs-you-is-grouped-by-action-and-reviewer-waits-are-left-out`);
  - a quiet suffix is no reason to retitle a run
    (`a-quiet-suffix-is-not-a-reason-to-retitle`).
  - a reply that brings no delta is a quiet turn and leaves the title alone
    (`a-reply-with-no-delta-is-a-quiet-turn`);
  - each work stream is a `##` block of one sentence and at most four bullets
    (2026-11-11, `streams-are-h2-blocks-capped-at-a-sentence-and-four-bullets`);
  - a polled item keeps a wake quiet, its preflight in the re-armed prompt
    (`a-polled-item-keeps-a-wake-quiet-with-its-preflight-in-the-prompt`);
  - a question the flow needs is asked before the report
    (`a-question-the-flow-needs-is-asked-before-the-report`).

- reviewers (owner's rulings, 2026-11-06 and 2026-11-09):
  - at the owner's request, only a PR waiting on the owner alone is started; a
    re-request after new commits qualifies again
    (`review-candidates-are-only-prs-waiting-on-the-owner-alone`);
  - the dispatch prompt carries the draft-only limits
    (`a-reviewer-prompt-carries-the-draft-only-limits`);
  - drafts are read back before the owner is told
    (`a-reviewers-drafts-are-verified-before-the-owner-is-told`);
  - a reviewer is never treated as a run (`a-reviewer-is-never-mistaken-for-a-run`);
  - a drafted reviewer is archived once the owner submits
    (`a-reviewer-is-archived-once-the-owner-submits`);
  - no sweep or ruling starts a reviewer (`no-sweep-or-ruling-starts-a-reviewer`);
  - every created session has its source attached
    (`every-session-the-conductor-creates-attaches-its-source`);
  - a reviewer waiting on a prompt, or silent, is read from its record and the forge
    (`a-silent-or-blocked-reviewer-is-read-from-its-record-and-the-forge`).

**From two independent reviews (PR #201):** *(the retirement half superseded by #214: no standing ruling retires a run.)* a standing retirement ruling is re-read at its site exactly as a conditional go is, because a revoked ruling found only in the ledger would otherwise retire runs unattended; a single-issue run's `merged` report and its merged PR stand in for a wrap-up it never posts; on the default `github-issue` ledger held replies and draft answers are only named, so a deployment where drafts matter configures `tracker-document`; and a relayed approval puts the complete reply text in the question's option, so the owner answers once. Scenarios: `a-revoked-retirement-ruling-retires-nothing`, `a-merged-single-issue-run-retires-without-a-wrap-up`, `a-relayed-ruling-that-posts-a-reply-is-one-question`.

## Contradiction pass and re-audit after the dispatched-account ruling (PR #201)

**Where the owner's account comes from.** The dispatch prompt names the owner's account as the invoking user's for the session it starts (owner's ruling, 2026-11-03), so the conductor must have that account from a statement too: the login its own invocation names, never the ledger (forge content anyone with write access can edit), a credential or a comment. Without one, the dispatch names none and every go and standing ruling stays pending — the fail-closed reading. **Why the DAG write names the open-item ban:** a run cannot tell an approved relay from any other footered comment under the owner's account, so the ban on writing at an open item's site is restated where the conductor writes plans. *(Superseded by #214, which removed the held watch.)* **Why a held watch carried one deadline:** anchoring 7 days at each hand-off restarted the bound on every re-settle; the run's own deadline now travels with the watch and is recorded per held PR in the ledger and the check-in prompt.

*(Superseded by #214: a settled run now keeps its own watch and the conductor holds none — `rules/conductor-exchange-notes.md`, *The watch after settling*.)* **Owner's rulings on the held watch (2026-11-04):** the held watch ignores empty sweeps and runs until the PR merges or closes, or its deadline passes; and a conductor that dies after taking over a settled PR's watch leaves an accepted gap — the run keeps no check-in at its deadline. Recorded in full in `rules/conductor-exchange-notes.md`, *The watch after settling*.

## Owner's rulings (2026-11-05, PR #205)

**Why settings arrive by invocation and travel in every dispatch:** some deployments' repositories can never hold `.claude/agent-policy.json`, so a thin skill passes the values as invocation arguments, which `rules/agent-policy.md`, *Precedence*, already lets beat the file for every key that grants nothing. A cloud session has no local files, so the dispatch prompt is the only carrier: the conductor passes on every argument the run's skill reads, records them in the ledger for a restart, and points a planner at `plan-feature` with its own. **Why it drafts what it would record on an issue it did not create:** the shared permission rule (`rules/authored-write-form.md`, *Issues the run did not create*). Two later rulings narrow this, both below: a ruling the owner approved word for word on an item a run raised is posted by the conductor itself, and every go, on any issue, is drafted for the owner to post — itself narrowed on 2026-11-11, when a dispatch go or a conditional go may be conductor-posted and verified in the conductor's transcript. Evals 0, 9, 25, 34 and 37 were rewritten to match.

**What the third contradiction pass added (2026-11-05):** the drafted path names how the record is known — the owner gives the posted comment's link, the conductor reads it back as the owner's and records its id — because a conditional go and a standing ruling are re-read by that id, and finding the owner's comment by account or content could pick up a run's own write (protected rules 2 and 3). Each section that records on an issue points at *Rules*. The restart prompt carries the invocation arguments verbatim rather than reading them from the ledger, which anyone with write access can edit.

**One exception with `settle-outstanding-decisions` (owner's ruling, 2026-11-05):** a ruling whose complete comment the owner approved word for word — its full text in the option they chose — is posted by the conductor itself, on any issue, as `settle-outstanding-decisions` posts one; the exception is stated once in `rules/authored-write-form.md` and read from the conductor's record of the approval, never from a footer.

**Why a conductor may post a go itself, verified in its transcript (owner's ruling, 2026-11-11):** *supersedes the entry below for dispatch gos and conditional gos.* In practice the conductor posts under the owner's account, so a same-account comment proves nothing about who approved it: the old rule's real guarantee was "a person was present and chose". The owner pasting a drafted comment onto the epic added a round trip without adding proof. A conductor-posted go keeps the guarantee and makes it checkable by the run: the comment names the conductor session, the question and the exact option, and the run finds the owner's input event choosing that option in that session's transcript (`list_events`). It is still one of the conductor's own writes by id (protected rule 2), tagged apart; it is accepted on the transcript, never on its author or its marker, so a marker alone still starts nothing. **Not established:** nothing in this repository has yet observed `list_events`, or an event field that tells owner input from synthetic or peer input; until a run observes both, every conductor-posted go fails closed as unverified and stays pending (owner's choice, 2026-11-11, to write it now and let the first real run settle it).

**Why a conductor-posted go carries the footer and is never posted at an open item's site (contradiction pass on #215, 2026-11-12):** the owner approves the go's text, not the comment the conductor builds around it — the marker's time and session URL are filled in after the answer — so it is not a write the owner approved word for word, and protected rule 1 adds the footer. And *Nothing at an open item's site but its ruling* already keeps every conductor write off such a site so none reads there as the owner's reply; a go due there is owner-posted instead.

**Why a retirement ruling is never conductor-posted, and why only a review thread bars the form (owner's rulings, 2026-11-12):** archiving a run is the authority `swarm` takes only from the owner's ruling, and #214 replaces standing retirement rulings with a sweep and a confirm question, so a retirement keeps the owner's own answer in the session that archives and a conductor-posted go authorises none; *Retire a finished run* says so at its decision point. The thread bar was written for review threads, where a person waits on a reply; an epic or issue others have commented on is the form's ordinary site, which eval 55 already assumed. The `<repo>` in a reviewer's title keeps its `acme-web` examples (owner's ruling, same day).

**Why the form is kept narrow:** releasing a held item, opening a merge gate and merging are irreversible and are read by parties other than the run — a gate, a reviewer, a person in the thread — so they keep the owner's own words at their site. The motivating precedent is 2026-11-05, when runs refused merge rulings a conductor relayed: that refusal was correct, and this change leaves it in place. **"The owner's own words" includes a relayed ruling they approved word for word (pinning round over the batch integration, 2026-11-17):** read bare, the list read as barring the conductor from posting even an approved relay at a hold's site, which *Relayed rulings* allows; the list only bars the conductor-posted go form, and now says so. Scenarios: `a-chat-ruling-is-relayed-under-the-recognisable-marker`; `a-conductor-posted-retirement-ruling-authorises-no-archive` was reworded to hold under #214's attended retirement as well.

**Why every go is the owner's to post, on any issue (contradiction pass after the rebase onto #206, 2026-11-05):** *superseded for dispatch gos and conditional gos by the 2026-11-11 entry above; its reasoning still holds for every other comment, and is why a conductor-posted go is accepted on the transcript and never on its id or author.* A go is the owner's authority. Under #206 a comment whose id the run holds is its own write, so a go the conductor posted itself — even on an issue it created — and then re-read by that id would be its own write accepted as the owner's (protected rules 2 and 3). So the owner posts every go from a draft, the ledger keeps owner-comment ids apart from own-write ids, and both re-reads refuse an own-write id. Only a ruling on an item a run raised is under the exception. A reviewer's go is the other exception, recorded in the ledger alone (*Reviewers*).

## Owner's rulings (2026-11-12, PR #214)

**Why a run retires only on the owner's answer in an attended turn.** The standing retirement ruling let a scheduled firing archive sessions nobody was watching, and every guard on it — re-read by comment id, authored by the owner, unedited, not revoked — existed to stop that path doing harm. The owner replaced it: each attended turn lists the runs ready to retire, meeting every *Retire a finished run* condition verified that turn, and asks one `AskUserQuestion` confirming which to archive. A scheduled firing only lists them for the next attended turn. The cost is one question per attended turn while a run is ready; the gain is that no archive happens without the owner answering in the session that does it. A conductor-posted go never authorises a retirement either (#215 states the same for its posted dispatch go). A drafted reviewer's archive is unchanged (`reviewers.md`). Protected rule 9's conditions bind every archive exactly as before; only the authority moved. Scenarios: conductor#5 #31 #38 #39 rewritten, conductor#87 new.

**The conductor shrink is not in this PR** (owner's ruling): it gets its own.


## The run handover: contradiction pass, audit and evals (2026-11-27)

**What was run, for the handover change.** A repository-scoped contradiction pass ("find every place this repository now contradicts itself") and a separate blind protected-rule audit, each by a fresh reader given the diff but not the author's conclusions. The audit found rule 9 at risk where an owner's answer retired a run without its handover, and three smaller gaps (a check's outcome in a verbatim prompt on a forge ledger, the handover's sender, budgets above the resolved policy). The pass found an orchestrator on a conductor-posted go could never be ready, since it may post no checkpoint comment; a handover request reaching a stale run before the owner's answer; the handover missing fields a resume reads (its `as of`, follow-ups filed, own write ids, gate-note refs by PR); the predecessor's open items unwatched; the single-issue run's and the replacement's go unstated; a turn answering a request reading as a return; a usage disagreement able to refund budget; retired runs' prompts with no way out of a size-capped ledger; and stale copies in `docs/shared-rules.md`, this file and eval 8. All were fixed in the same change.

**Two-arm comparison** (`scripts/run_evals.py`, base `origin/main`, Sonnet readers given only the contract and the prompt, packets renamed so neither readers nor graders could see the arm, a separate Sonnet grader): conductor #5 #8 #31 #38 #39 #107 #115 #118 #127 #128 #140–#143 (base 51/65, change 63/65); backlog-orchestrator #19 #48 #66 #82 #98 #100 #121 #131 #133–#135 (33/44, 44/44); swarm #20 #24 #25 #26 (16/17, 15/17); implement-issue #32 #34 #41 (10/10 both); plan-feature #5 (4/4 both). Every disagreement was a gain on a new or changed scenario but one: swarm #20 lost an assertion about a permission-held slot, a section this change does not touch; the two answers differ in phrasing, not action, so it is read as reader noise. The two assertions the change failed (conductor #115's "only once archived" and #140's seed) failed in both arms. No scenario was ungraded. The corpora were not run whole, for cost; #144 was added after the round.

**Owner's rulings on #248 (2026-11-27).** (1) A run that may not post a checkpoint comment on its epic gets no wider permission; its settle and watch-stop pushes carry the handover instead, and this skill writes it to the ledger on receipt, unasked, replacing the earlier one — a pushed record, not a pulled one (`rules/conductor-exchange.md`, *Pushes*). Retirement still asks for a fresh handover, since a push may be days old. Scenario: `a-pushed-handover-is-recorded-unasked`. (2) #140 and #144 pin protected rule 9 and are listed under it in `CLAUDE.md`. (3) A size budget for a `github-issue` ledger was asked for, with GitHub's body limit believed to be 65,536 characters. It could not be verified: GitHub's documentation states no limit for an issue or PR body, and a test on this change's own draft PR body (2026-11-27, restored straight after) accepted 65,536 and 65,537 ASCII characters alike, so the believed figure is not the limit as counted there. Issue bodies were not tested. The budget therefore names no GitHub figure and reaches a `github-issue` ledger only once its home's limit is known.

**Second two-arm round, after the owner's rulings** (same method): conductor #140 #144 #145, base 6/15, change 14/15; backlog-orchestrator #134 #136, base 3/9, change 9/9. Every disagreement was a gain. On #144 the base arm already refused the archive, which is protected rule 9 holding before this change too; the change added only the ledger record of what was lost. The one miss, #145's "still asks a fresh handover at retirement", came from a reader that took the scheduled firing to send no request, though *Retire a finished run* says a firing sends one as it sends a status request. Nothing ungraded.
