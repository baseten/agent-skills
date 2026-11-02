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

**Why one form for both kinds of run:** the conductor's sweep reads titles first,
and a person reads the session list. A second form for single-issue runs would
have needed a second prefix in the sweep and a second thing to learn. The title is
still only a finding aid: a session the conductor dispatched is known by the id
its ledger records, never by its title or its structure.

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
pulled against each other: the footer marks text nobody read, and is never a
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
message releases anything.
