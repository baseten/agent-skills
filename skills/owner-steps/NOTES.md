# owner-steps — design notes

Reasoning behind `SKILL.md`, keyed by its section names. NOTES explains; it never
overrides.

## Owner steps

**Why this skill exists (2026-10-31):** orchestrators and the conductor identify
work only the owner can do — post-deploy checks, key placements, backfills,
console actions — and the owner asked for each to be filed as a `[Manual]` issue
(`rules/manual-step-issues.md`) and walked through by a helper. The owner copies
each command to the live server and pastes the output back, so the session's job
is to give one unambiguous step, judge what came back, and keep the issue's record
true.

**Why one step at a time:** a block of ten commands run in one paste hides which
one failed, and the later ones run on top of the failure.

## Hard rules

**Why the secret rule covers what the owner pastes, not only what this session
asks for:** the most likely exposure is a paste — `env` output, a config file, a
connection string in an error. Repeating it, or recording it on GitHub, multiplies
the exposure; the only remedy for one already pasted is rotation, so the skill
says so.

**Why the runbook wins over the issue:** the issue was written by a run from what
it knew; the runbook is the repository's maintained account of how its server
works. A mismatch is more often a stale issue than a stale runbook, and following
the issue silently would also leave the next reader with the wrong command.

## Server access

**Where these defaults come from:** the owner's servers are reached by SSH as a
deploy user without sudo, and root work is done in the provider's web console.
Hetzner's console drops shift characters on paste, so a root command containing
`|` or `>` arrives mangled; the workaround — the deploy user writes a script where
pasting works, root types one unshifted line to run it — is the owner's own. It is
three steps, not one, because each runs in a different place as a different user,
and the hard rule allows one block per step.

## Decision scenarios

Pinned in `evals/evals.json`:

- pasted output shows a failure → diagnose, do not advance
  (`a-failing-paste-is-diagnosed-not-advanced`);
- a root step on Hetzner → a script plus a `bash` line
  (`a-hetzner-root-step-goes-through-a-script`);
- the owner pastes a secret → do not repeat it, redact it, advise rotation
  (`a-pasted-secret-is-redacted-and-rotation-advised`);
- a blocker is not cleared on GitHub → stop and name it
  (`an-uncleared-blocker-stops-the-walk`);
- a step's command differs from the runbook → follow the docs and flag the issue
  (`the-runbook-wins-over-the-issue-text`).
