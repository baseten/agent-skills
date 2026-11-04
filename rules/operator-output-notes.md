# Notes — operator-output

Reasoning for `rules/operator-output.md`. Deliberately *not* bundled into
each skill: the audience is a person editing the rule, who has this checkout.

**Why this is a shared rule (owner's design, 2026-11-03):** the owner runs a
`conductor` over several `backlog-orchestrator` and `implement-issue` sessions, and
each orchestrator over many issues, so the chat is where every run's output lands.
Two transcripts — one at work, one on a personal project — showed the same faults
in every skill that printed to it, and each skill had its own wording for its
output, or none. PR #201 had put the first fixes into the conductor alone (only
what needs the owner, one question at a time, a three-link header, results not
the checking). They moved here, and each consumer keeps only what is its own:
what counts as needing the owner for it, which record its contract requires, and
its own question ordering.

**What it does not govern:** forge writes, which the *authored write form* rule
owns — so a ledger kept as a forge issue still carries bare SHAs (protected rule
7), even though the chat links commits — and peer messages, whose fixed report
form the conductor parses (`rules/conductor-exchange.md`, *Reports*). No protected
rule's text or home changed with this rule.

## What reaches the chat

**Why each exclusion is named (transcript patterns):** both transcripts carried
process narration — "reading the ledger", "the seeds are written, creating the
sessions", "now pulling the text of my drafts", trigger ids, counts of empty
sweeps — none of which the owner could act on, and all of which pushed the one
line that needed them off the screen. They also mixed status the owner could not
act on, chiefly PRs waiting on named reviewers, in among the asks. Naming the
classes is what lets a reader recognise them; "be concise" was already the
instruction and did not stop them.

## A reporting turn ends in a fixed order

**Why a fixed order, and why it ends the turn:** the parts worth keeping in the
transcripts were a "Still waiting on you" list grouped by what the owner does
(merge, request a reviewer, answer) and a table of started runs with their session
and go-ahead links. Fixing their order means the owner reads the same place every
time, and putting the report last means it is what a terminal or a scrolled chat
shows. The groups are the owner's five plus two the conductor already had to
surface — owner steps and a failure only the owner can clear — so that nothing
that needs the owner falls outside a group.

**Why *Changed since* is in the chat at all:** PR #201's conductor rule kept every
change out of chat, and a sweep with nothing for the owner was one line. The
owner's design keeps state changes — a merge, a run started, a run failed — in the
chat, once each, because that is what the owner reads to decide what to do next;
what stays out is the steps, the checking and the unchanged. An attended sweep with no
change and nothing for the owner reduces to its *Unchanged* line and the ledger
link, and a scheduled one to its title and minimal line (*Quiet turns*). The conductor's scenario
`a-sweep-reports-state-changes-once-never-steps-or-waits-on-others` replaces the scenario that pinned the one line.

**Why the unchanged list is one line:** one transcript reprinted the same "Still
waiting on you" list every turn, so a new item was indistinguishable from the old
ones. Reprinting only on change makes a reprint itself the signal. Where the
session has lost the last printed list, it reprints, which is the safe direction.

**Why `---` between groups, stated once:** runs and issues blurred together in both
transcripts where one block's last line ran into the next block's first. The first
draft stated the separator in three places; the review of #204 consolidated them.

**Why times are local where known (review of #204):** the owner reads the report;
UTC is the fallback only where the session does not know their timezone, and is
labelled so it is never mistaken for local time.

**Why an unchanged list's questions are not asked again (review of #204):** asking
the same structured question every report is the reprinted list in another form.
A question returns only when its item is new or changed.

## Records

**Why a contract's record is printed before the report, not removed:**
`backlog-orchestrator`'s state block is printed because a count that re-enters the
transcript survives a compaction (its *Progress / checkpoint output*);
`implement-issue`'s structured result and the settle outputs are what callers and
the owner keep once a run ends. Removing them would change those contracts'
recovery paths. So the record stays, put first, and the report — short, and the
same shape every time — is what the turn ends with.

**Why a recurring record prints only when it changed (owner's ruling,
2026-11-03):** a state block reprinted every cycle with the same numbers was the
largest single source of noise in an orchestrator's chat. The owner ruled that it
prints only when it changed, plus once whenever the last printed one has left the
session's context — after a compaction, a restart or a clear — so the record is
never lost from what the session can see. A new as-of time, wake count, next firing
or waking event alone is not a change: those ride the wake's prompt. Everything
that reads "the last state block" still finds one: a compaction or restart prints
it on the next cycle (`restart-resume.md`, step 6, reads it only where the resume
has it, and otherwise rebuilds from durable state); the conductor's retirement test
reads the run's last block, which is current because any change — a session
archived, a recovery ref outstanding — prints a new one. The rule states this for
every recurring record, so `supervise-prs`' `state emission` follows it in chat
too. `backlog-orchestrator`'s `state-block-every-cycle` scenario now pins it.

**Why records are exempt from the report's exclusions:** a state block carries
check-in ids and trigger lists, a settle carries a ranking table, and a summary
says what was verified. Those fields serve a restart, a gate or a caller, not the
owner's reading. The record keeps its contract's form; the report is what is kept
terse.

## Headings and links

**Why one heading scheme for a conductor and a run (review of #204):** the first
draft gave a run's own issues the `###` a conductor gives a run, so the same
heading level meant two things. A run's report now carries its one run heading
under each section, and the levels mean the same everywhere. The two worked
examples exist because a model applying the rule every turn copies an example more
reliably than it assembles one from clauses.

**Why every block names its subject:** in both transcripts a reader could not tell
where one run's news stopped and another's began; context switches between runs
and between issues were unmarked. A heading with the session, repository and epic
makes every block self-locating.

**Why every reference is a link, and the repository once:** references were
written three ways in one message — a full `org/repo#N`, a bare `#N`, and plain
unlinked text — and sessions appeared as raw ids, even in tables, or as plain
titles that wrapped. A link with the title as its text is clickable and readable;
naming the repository once per block — in a run's heading, or on a *Needs you*
group's line where its items share one — lets every ref below it be short without
being ambiguous. The three-link header PR #201 required is this rule's heading for
a run and for an issue.

## Questions

**Why one per call (field feedback carried from PR #201):** batches of up to four,
and numbered prose lists, were answered partly or out of order.
`settle-outstanding-decisions` used to chunk up to four per call; one per call
satisfies its fork rule by construction, so its chunk mechanics were cut (its
NOTES, *Ordering*).

**Why a question is asked where the flow needs it (review of #204):** the first
draft put every question after the report, which breaks flows that need an answer
mid-turn: `settle-and-merge` runs the walkthrough before the merge gate, and the
conductor acts on some owner-pass rulings in the same turn. Questions whose answer
the turn acts on are asked before the report; the rest follow it. A question
already asked is not asked again while its item is unchanged — the conductor's
owner pass included — unless the owner asks; a walkthrough a contract runs keeps
its own qualifying bar.

**Why the heading is repeated before a question, and the repository named inside
it:** links may not render inside a structured question, so the chat line above it
carries the clickable links, and the question carries the names in plain words so
that it still stands alone — `settle-outstanding-decisions`, *The question*, holds
that text between tool calls may never reach the owner, so nothing the answer
needs is left to that line. The `header` chip is the issue id because it is the
one thing that identifies the item at a glance and fits the platform's 12
characters.

**Why options are never also listed in prose:** one transcript listed the options
in prose and then asked the structured question with the same options, so the
owner read every option twice and could not tell which list was the question.

**Why a run with no lean says so rather than marking one:** the owner asked for one
option recommended; `settle-outstanding-decisions` already forbade a fake lean,
because a recommendation the run cannot back steers the owner toward an arbitrary
choice. Both hold: the recommendation is the evidence-backed lean, and where there
is none the question says so.

## Meta answers

**Why a separate block:** the owner's questions about how a skill works were
answered inline with run status, so the answer and the status each had to be
picked out of the other.

## Quiet turns

**Why nothing, and why the title:** quiet check-ins posted "nothing new since the
last check-in; next check-in at …" every hour. The chat is append-only, so those
lines accumulate and cannot be replaced. The session title is the one surface a
run can change in place, so the quiet state — since when, and when next — goes
there, with the count of items waiting on the owner. That count is what keeps
`backlog-orchestrator`'s rule that a quiet wake is never silent about what is
waiting on the owner: the total moves from the state block to the title, on the
same cadence, and the split by kind stays in the wake's prompt. The record is not
printed either: a quiet wake changed nothing in it but the count and the next
firing, which the wake's own prompt already carries (the *wake budget* rule) and
which re-enters the transcript each firing, so the last printed block still
stands (*Records*).

**Why quiet is narrower than unproductive (contradiction pass, 2026-11-03):** the
*wake budget* rule counts a wake that could not read as unproductive, and the
*watch and read* rule says such a wake, or one that found an unwatched item, is
unread, never quiet. A wake that deferred a read, found a blind spot, acted on
anything — archived a session, released a hold — or stopped the watch therefore
prints as usual. The first draft defined quiet as any unproductive wake and
would have titled a blind wake quiet. Consumers point at the definition rather than
paraphrase it: the review of #204 found two pointers that read "no delta" for
quiet and dropped the narrowing.

**Why the no-change preflight rides the prompt (review of #204):** the *watch and
read* rule requires the tracked set, each item's watch state and a polled item's
last-observed time before any no-change result is reported or recorded. Printing
them would put the hourly line back; treating every wake with a polled item as
not quiet would make polling runs chatty for good. Carrying the preflight result in
the re-armed wake's prompt records it where the next firing compares against it,
which satisfies that rule and keeps the chat at one line.

**Why a quiet turn excludes the post-compaction reprint, a proposal and attended
turns (second contradiction pass):** the first cycle after a compaction must print
the record, a context-clear proposal needs the operator, and an attended turn owes
its report, so none of them can also be quiet. A reply turn owes no preflight
because it reports and records no no-change result; *watch and read* binds only
those.

**Why sending status requests does not stop a turn being quiet, and why a reply
with no delta is quiet (review of #204):** a conductor's fallback sweep always asks
each run for status, and each reply arrives as its own turn. Counting the requests
as acting, or reporting every reply, gives N runs N lines an hour. A reply turn
that brought no delta writes its minimal line and leaves the title alone, so the
title does not churn either.

**Why only the suffix changes:** PR #201 finds runs first by title prefix
(`Orchestrator:`, `Worker:`), retitles a run whose title is not its kind's form,
and sets the conductor's own title at startup. A suffix appended from
` · quiet` leaves the prefix and the form before it intact, so the sweep's
prefix match is unaffected, and the conductor reads the form before the suffix, so
it does not retitle a run for being quiet. The review of #204 asked for a less
rigid suffix: only its ` · quiet` start is a token, which the sweep needs; what it
says after that is prose. The title remains a finding aid, never
evidence (`swarm`, *Runtime*).

**Not established: whether a turn can end with no text.** Nothing in this
repository or its NOTES records a session ending a turn with no text, or what its
`post_turn_summary` and the chat show when it does. So the rule takes the minimal
line: for a coordinated run, the `final status:` line its contract already requires
(which the conductor's sweep reads); otherwise `quiet`. To establish it: let one
quiet firing end with no text and read the session's record and chat afterwards;
if both are sound, the minimal line can go.

**Why a held watch reaching its deadline is not quiet (rebase onto #201's final head):** #201 lets a conductor hold a settled run's watch, polled on the post-settle cadence and ended at the deadline the hand-off carried, reported as unwatched. That end is a stop the owner must hear about, so the quiet test names it beside the check-in's own stop. The held watch's polling fits the preflight rule as it stands: a polled item whose poll ran is quiet with its last-observed time, carried in the re-armed prompt with the held watch's PR and deadline, and the title's next time is whatever cadence keeps the check-in armed.

**Why the stop message stays:** the *wake budget* rule requires a stopped watch to
be reported, never silent, because an expired watch is a cost decision the owner
must know about. It is one message, not a recurring one.

## Collapsing

**Why leaving out beats collapsing:** `<details>` renders as a collapsed block on
GitHub, and as raw tags in a terminal. Moving content to the ledger or the record,
linked, works on every surface.

## Consumers

**Who applies it:** every orchestration skill that prints to the owner —
`conductor`, `backlog-orchestrator`, `implement-issue`, `supervise-prs` when
invoked directly — and the settle steps whose output lands in their chat:
`settle-and-merge`, `settle-outstanding-decisions` and `summarize-wave`.
`ship-branch` holds no rule of its own and inherits it through `implement-issue`.
`npm-dependency-upgrade-orchestrator` prints to the owner too, but was outside the
owner's list; adopting it is a follow-up, tracked on #202.
