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

**Why the per-repository values moved into the policy file (owner's ruling, 2026-11-02):**
the first version carried a table of one repository's epic number, app paths,
restart command and a never-run rule in this skill's text. The repository is
public and the skill is meant for any repository, so those values now live where
each repository already keeps owner-authored configuration — `manual-steps` in
its `.claude/agent-policy.json`, indexed by the schema — and this file keeps only
defaults. The script route is the default for any console not recorded as able to
paste, because it works on every console and the direct route fails on some.
`specifics` are facts, not commands, so that a value in a config file is never
run on the strength of being there; the runbooks still win.

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
- the repository's policy file records the console and a never-run command → a
  root step given as is on a console that pastes, and the recorded command refused
  (`server-access-comes-from-the-repository-policy`).

**Why a step's record says done or not done, and keeps the output in the session (protected-rule audit and re-audit, PR #201):** a forge write never reports verification (protected rule 7), and a post-deploy check's output is exactly that. The issue records whether each step was done; the output, redacted, stays in this session's report. Scenario: `a-steps-record-on-the-issue-is-done-or-not-done-never-its-output`.
