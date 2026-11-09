# Notes — conductor-exchange

Reasoning for `rules/conductor-exchange.md`. Deliberately *not* bundled into
each skill: the audience is a person editing the rule, who has this checkout.

**Why this is a shared rule (PR #201, owner's audit item 1):** the run-side half
of every exchange with a conductor was first written into `backlog-orchestrator`,
*Status requests from a conductor*. The owner's own conductor, running since
2026-10-21, manages single-issue `implement-issue` and `ship-branch` runs as well,
and each needed the same reply, pushes, id adoption and fold handling. Copying the
section into `implement-issue` would have made two statements of one exchange,
which is how the two would come to disagree; so it moved here, and each skill keeps
only what is its own — where the id is recorded, which test releases its holds,
and what a fold ends.

## The run's title

**Why two forms, `Orchestrator:` and `Worker:` (owner's ruling, 2026-11-02):**
the first version of this rule gave single-issue runs the `Orchestrator:` prefix
too, so the sweep needed one prefix. The owner reserved `Orchestrator:` for
`backlog-orchestrator`: a person reading the session list should tell a batch
that dispatches workers from a single-issue run at a glance. `Worker:` is
capitalised and colon-led so it cannot be mistaken for a `swarm` worker's
run-prefixed name (`bo/<run>: ...`), which this rule never touches. The title is
still only a finding aid: a session the conductor dispatched is known by the id
its ledger records, never by its title or its structure.

**Why the table is also the owner's vocabulary (owner's ruling, 2026-11-06):** the owner
names sessions by kind in conversation — "ask the orchestrator", "start a worker",
"a reviewer drafted it" — and agents outside these skills guessed at what each word
meant. One line per word, beside the title it produces, puts the word, the skill and
the prefix in the one place a reader already looks, and the owner's private
configuration points here rather than restating it. The conductor and planner rows
carry no rule of this exchange: the conductor's title is its own (`conductor`,
*Session titles*), and a planner is a session the owner starts and talks to directly.
A reviewer is listed because the owner's word needs a home, not because it is a run:
it answers no status request, pushes no milestone and holds no watch, so every other
section here leaves it out.

## Pushes

**Why milestones and not a period:** a conductor sweeps on its own schedule and
asks when it needs to know. What it cannot learn from the forge as cheaply is the
moment a stream changes state, so a run pushes exactly then: a PR into the default
branch opened or merged, a hold raised for the owner, and settling. The merge push
is what lets a conductor start work gated on it without waiting for a sweep.
Under `ci-mode: integration-branch` only the integration PR goes into the default
branch, so the same words give the integration milestones.

## New work, or a fold

**Why a fold and new work need different evidence (round 2 of PR #201's contract
review):** a fold only ends work, so a comment the owner wrote is enough; new work
starts dispatch, which protected rule 3 releases only on the owner's reply
choosing an offered option or a recorded ruling.

## Relayed rulings

**Why relayed rulings needed one recognition rule (PR #201, owner's audit item
7):** the owner often rules in the conductor's chat. Those rulings were recorded
on the forge, but nothing said how an orchestrator, whose authorship test reads "a
comment the owner wrote", should read a comment the conductor posted. Two rules
pulled against each other: the footer then marked text nobody read, and is never a
discriminator (`rules/authored-write-form.md`), so it could not be what told a
relay apart. The resolution keeps both intact. The conductor records a relay as
`settle-outstanding-decisions` records any ruling — the owner shown the complete
comment, the footer decided by the approval test alone — with a marker naming
where it was given. Recognition rests on the marker and the owner's account
together, and never on the footer, so an approved relay (no footer) and an
unapproved one (footer) are recognised alike; the footer only tells a reader
whether the owner read the posted words. A relay under any other identity is not
recognised, which fails closed: the owner answers at the site instead. Protected
rule 3 is unchanged — the relay is the owner's own choice, recorded; nothing in a
message releases anything. Since the owner's ruling of 2026-11-05 the footer does
not even tell a reader whether the owner read the words — a transport can add it
to an approved relay — so the conductor records the approval instead.

**What the contradiction pass before the review round changed (PR #201):** the first
version made a relay count only under the owner's account, everywhere. That
contradicted `settle-outstanding-decisions`' own reasoning — the marker, not the
posting account, carries a recorded ruling's authority — and would have failed
every relay in a deployment with a distinct agent identity. It also left the
marker untested at the reply watch, the point that actually releases holds. So
the section now separates the two uses: as a recorded ruling a relay counts by its
marker, like any other; as a reply that releases a hold it passes the run's own
reply test unchanged, which needs the owner's account. That keeps protected rule
3's release path exactly where it was. The pass also found that a footer-based
own-write test elsewhere would read an unapproved relay as the run's own; no such
test remains since the owner ruled on 2026-11-04 that own writes are known by id
only, and the conductor still seeks approval wherever it can.

**Why adoption checks the home repository and not the title (same pass):** a
conductor's sources are its home repository, so a run in another configured
repository never matched "this run's repository", and the `Conductor:` title the
test also read is a finding aid, never evidence. The seed now names the home
repository, and the id and that repository travel in every check-in prompt and
are restored on restart, because the merge and settle pushes usually fire there.

**Why a declined request is reported (review round, scenario
`a-conductor-message-asking-for-a-merge-is-declined`):** when the run-side text
moved here, the line saying a declined request reaches the owner in the run's
output stayed only in `swarm`, and a reader replied to the conductor alone. It is
restated at the decision point.

## Reports

**Why the form is fixed (field feedback, 2026-11-02):** a day of running a conductor showed reports that ran on past the form, covered other issues, offered to start the next one, and called a missing link "blocked". Each cost the owner a read to find what, if anything, needed them. The three-link header lets a reader open the session, issue and PR without searching; the fixed state set makes a sweep's table mechanical; `blocked-on-owner` means the owner must act and nothing else; and choosing the next work is the conductor's, so a run never offers it. The final-status line exists because the platform's turn summary was seen reading "drafting…" on an idle session.

**Why every report carries the version line (owner's decision, 2026-11-06):** an owner audit could not tell which skill revision a dispatched session had run. The conductor records each run's line in its ledger row, so the answer is in one place without opening sessions; the line rides in every report rather than only the first because a conductor can adopt a run, lose a send or rebuild its ledger after the first one. The rule and its reasoning are `rules/run-start.md` and its notes.

## The watch after settling

**Owner's rulings (2026-11-04), recorded for the protected-rule 9 re-audit:** (1) a conductor that dies after taking over a settled PR's watch leaves that gap accepted — the run keeps no check-in at its deadline; (2) the held watch ignores empty sweeps — it watches until the PR merges or closes, or its deadline passes. Both close the open decisions the re-audit of PR #201 found unrecorded.

**Why the conductor takes the watch (owner's ruling, 2026-11-02):** a settled run and the conductor were both polling the same PR. Once a run is settled and waiting on the owner's merge, the conductor's hourly sweep already reads that PR, so the run's own check-in only duplicates it. The hand-off happens only on a delivered push, so a run whose conductor never heard keeps its watch; and the conductor hands the watch back before its own check-in stops, naming any PR it could not, so the hand-off never leaves a PR unwatched. *(Superseded: the hand-back is gone — see* Two independent reviews of the final head *below.)* Protected rule 9's bound is unchanged: each side's watch stays under the *wake budget* rule.

## Writes

**Why the trigger is never put up for approval (field feedback):** the approval test exists to stop unread prose going out under the owner's name. A review trigger is a fixed token whose exact text the repository documents; there is nothing in it to read, and holding it for approval only delayed review. The trigger rule already exempts it from the footer for the same reason. **Why replies are kept short:** under the usual posting identity a reply reads as the owner's own words, marked only by a footer where it carries one.

## What a relay can authorise

**Why a short list, inside the protected rules (owner's ruling, 2026-11-02):** runs were stalling on acts the owner had plainly asked for in the conductor's chat. The owner listed what a relayed ruling may authorise. Each item is fenced by the rule that already governs it, so none widens: marking ready stops at an explicitly held draft (protected rule 8); a body edit only where the body-edit table already allows (protected rule 6); a branch update by the repository's convention, the lease pinned; an approved reply under the hold rule (protected rule 1); a session's own pending review. A merge is never on the list. The relay must pass the owner's-reply test, as a hold release does (protected rule 3). Where the owner's list met a protected rule — publishing a held draft, editing a published body a person has read — the rule won, and the collision is reported for the owner.

**Why a chat ruling goes to the ledger first (field feedback):** a run read the ledger seconds before the conductor saved a ruling to it, found nothing, and stalled. Writing the ledger first, with the owner's exact words, then recording at the decision's site, then relaying with both links, means a run that looks finds the ruling wherever it looks. The site record still decides.

## The second contradiction pass (PR #201)

*(The dead-man check-in described here is superseded — see* Two independent reviews of the final head *below; the conditions stand.)* **Why the hand-off has conditions and a dead-man check-in:** the run's rule that a conductor which never writes again changes nothing met a hand-off that waited on the conductor's message — a conductor archived or crashed would have left the PR silently unwatched. So the run keeps one check-in at its own watch's deadline (the closed choice among keeping its full watch, keeping that one check-in, or accepting the risk; the owner may choose otherwise), hands off only where the conductor can reach it, never while it has open items, a held worker or an approval-pending reply — whose watch the conductor does not keep — and accepts a wake only from its recorded conductor's own id. A pass that leaves the PR unsettled takes the watch back until it settles again.

**Why "mark ready" stops where the draft-state rule stops:** that rule lets a run promote only by a documented convention or as a step of merging; the owner promotes otherwise, themselves. Adding a relayed ruling as a promotion form would have widened protected rule 8's home, so the relay marks ready only where the rule already allows a run to, and otherwise tells the owner to promote. **Why only an approval-pending reply:** a draft answer to a person's question is never posted on any path (protected rule 1); the relay posts only the acknowledgement of a pushed fix the owner approved, recorded on the PR's conversation with the text, and resolves it as the approved path in `resolve-pr-comment` does, on the ask-time re-read — that skill and `settle-outstanding-decisions` accept a comment landing between the ask and the post as resolved over, a cost the owner may choose to remove (pinned by `settle-outstanding-decisions#12`, so not changed here).

## The protected-rule audit (PR #201)

**What the blind audit changed.** A relay recognised by its marker alone could have started new work under any identity, and an unapproved relay at a hold's site would have released it on text the owner never read; both widened protected rule 3. Now nothing starts dispatch or releases a hold without the owner's-reply test — the owner's account, not the run's own write — and the conductor posts at a hold's site, or where it would start work, only a comment the owner approved in full. The watch hand-off could have looped forever between a run and the conductor; a run that takes its watch back never hands it off again in the same settled state, its resumed watch keeps its count and deadline, and its dead-man check-in fires once at the bound its own watch would have reached (protected rule 9). *(The no-second-hand-off and dead-man parts are superseded — see the next section; the kept count and deadline stand.)* Submitting a session's own pending review is fenced to a dispatched review session's own comment review (protected rule 1). A conflicting rebase is not turned into a merge: the PR is reported conflicted, as any conflicted update is.

**What the re-audit added:** a relay can be read hours after the owner was asked, so a relayed approved reply resolves only where a re-read just before resolving finds nothing newer than what the owner was shown — the approved path in `settle-outstanding-decisions` posts within seconds of asking and keeps its pinned ask-time read. New work through a recorded ruling needs the owner's choice of an option a question put, not only an owner-account comment. A session's "own" pending review is the one whose id it recorded, since under the owner's account the forge shows the owner's own pending review as the session's too. And a conductor's wake after the run's own bound runs nothing: the run says its watch ended, and the conductor names the PR unwatched, so the conductor cannot extend a run's watch past its limit.

## Two independent reviews of the final head (PR #201)

**Why the watch hand-off collapsed to one statement (owner's intent, confirmed as owner's rulings 2026-11-04 below):** the owner wanted the conductor to own polling once a session settles. The earlier protocol stopped the conductor after three empty sweeps and handed every watch back, and a run that took its watch back never handed it off again, so at work, where a merge takes days, polling returned to every session. The conductor now holds a settled run's watch until the PR merges or closes, on the post-settle cadence, bounded at the run's own deadline, 7 days from its result, which the hand-off carries and no later hand-off moves; a wake after it runs nothing (protected rule 9, the *wake budget* rule); the dead-man check-in and the hand-back are gone. **The cost accepted:** a conductor archived or crashed after a delivered hand-off leaves the PR unwatched until someone looks — the run is quiet by design. The owner accepted that gap (owner's ruling, 2026-11-04, below); nothing is written on such a PR, so it fails closed. The re-audit found the first version of this anchored the 7 days at each hand-off, which restarted the bound on every re-settle; one deadline now travels with the watch, and a held watch's sweeps run on the held cadence rather than hourly once nothing else keeps the check-in armed. **Why a status reply goes to the platform sender:** the text of a message is peer data, so an id it names cannot direct a reply any more than it can be adopted as a new conductor id. **Why a superseded session ignores pushes:** a resumed run adopts live workers whose send clauses name the predecessor; without this, the predecessor woke on their pushes and acted beside its successor. The adopting run records their return channel absent, and the restart test counts their send clauses.

## Relayed rulings on issues the conductor did not create (owner's ruling, 2026-11-05)

**Why the owner posts them:** the shared permission rule (`rules/authored-write-form.md`, *Issues the run did not create*) bars a run from commenting on an issue it did not create without the owner's permission for that issue, and the owner ruled that a relayed ruling there is drafted for them to post — later narrowed by the exception below. The owner's own comment then passes every test a run applies to an owner's reply — authored by the owner's account, not one of the run's writes — so nothing downstream changes. Rulings on a PR keep the existing relay path.

**Why an approved ruling is posted by the conductor itself (owner's ruling, 2026-11-05):** where the owner approved the complete comment word for word — the full text was in the option they chose — the comment is theirs, and the shared rule's one exception lets the conductor post it on any issue; its approval lives in the conductor's record, never in a footer. Anything the owner did not approve word for word is still drafted for them to post.
