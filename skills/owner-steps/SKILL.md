---
name: owner-steps
description: Walk the owner through one `[Manual]` owner-steps issue, one step at a time, while they run each command on the live server or console and paste the output back — confirm its blockers are cleared on GitHub, give each exact command with where and as whom to run it and what to expect, judge each pasted result against that expectation and diagnose a failure rather than advancing, record each result redacted on the issue and tick it, and close the issue only when its "Done when" holds. It follows the repository's runbooks and server-access rules (SSH as the deploy user without sudo; root only in the provider's web console, through a short script on Hetzner), never suggests an unrequested destructive command, and never asks for or repeats a secret. Use when the owner wants to work through a manual step, a `[Manual]` issue, a post-deploy check, a backfill or a key placement.
---

# Owner steps

The owner is at a terminal on the live server, or in a provider's web console;
this session is not. It gives **one step at a time**, the owner runs it and
pastes the output back, and this session judges the result, records it on the
issue, and gives the next step. **It runs nothing on the server itself, and it
never sees a secret.**

The issue is a `[Manual]` issue in the form `references/manual-step-issues.md`
states; that rule says what each part means. This file is the contract; the
reasoning lives in `NOTES.md`, keyed by section.

**Attended only.** Every step waits on the owner's paste. Invoked with nobody to
answer, say so in one line and stop.

## Hard rules

- **No unrequested destructive command.** Never suggest or give a drop, a delete,
  an `rm -rf`, a force flag, a key rotation, or anything else that destroys data
  or state, unless the issue states that step — and even then, say what it
  destroys and get the owner's confirmation before giving it.
- **One command block per step.** One copyable block, run in one place, as one
  user. A step needing two places is two steps.
- **Never ask for a secret, and never repeat one.** Where a step places a key,
  name the file and the variable (or the app dialog) and let the owner type the
  value there. Where a paste contains anything secret-looking — a key, a token, a
  password, a connection string carrying one — do not repeat it, redact it in
  every record, and tell the owner it has been exposed in this session and should
  be rotated.
- **Never guess.** A result that cannot be judged from the output is not a pass:
  ask for the output that would decide it.
- **The runbook wins.** Where a step's command differs from the repository's
  runbook docs, follow the docs, tell the owner why, and flag the issue text for
  correction in its record.

## Server access

These are the defaults. **A repository's runbooks override them**, and so does an
entry under *Per-repository overrides*, below.

- **SSH reaches the live server as the deploy user only, with no sudo.** Never
  suggest `sudo`.
- **Root commands run in the hosting provider's web console** — DigitalOcean or
  Hetzner — never over SSH.
- **DigitalOcean's console pastes anything**, so a root command is given as is.
- **Hetzner's console cannot paste shift characters** — none of
  `| > & " _ : ~ ( ) { }` and the like. So a root step on Hetzner is three steps:
  1. as the deploy user, over SSH, write the commands into a temporary script —
     for example `/home/deploy/<name>.sh` — and make it readable; give the
     script's contents and the command that writes it;
  2. as root, in the console, the owner types only `bash /home/deploy/<name>.sh`;
  3. as the deploy user, delete the script once its output is judged.
- **Keys** go only into the server's env files or the app's own dialogs.
- **Long jobs** run under `nice` inside `tmux` or `screen`, so a dropped
  connection does not kill them; give the command to reattach.

### Per-repository overrides

Read the repository's runbooks first; these entries record what they say, for a
session that has to start somewhere.

| repository | recorded specifics |
|---|---|
| crypto-scanner | manual-steps epic #1584; app at `/opt/crypto-scanner-api/{current,shared}`; restart with `pm2 restart crypto-scanner-api`; never `--update-env` on `crypto-scanner-mcp` |

A runbook that disagrees with this table wins, and the difference is reported so
the table can be corrected.

# 1. Read

Read the issue, everything it links, and the repository's runbook docs. **Confirm
each `Blocked by` is cleared on GitHub** — the PR merged, the deploy recorded, the
issue closed as completed (`references/establish-do-not-assume.md`, *You are about
to assert it*). Where one is not, **name it and stop**: a step run against an
unmet blocker produces output that means nothing.

Where the issue is missing a part of the form, or a command contradicts the
runbook, say so before the first step.

# 2. One step at a time

For each step, give:

- **where and as whom** — host or console, and user;
- **the exact command**, in one copyable block;
- **what output to expect** when it works.

Then **wait for the owner's paste.** Give nothing further until it arrives.

# 3. Judge the paste

Read the output against the expectation:

- **pass** — record it (*4. Record*) and go to the next step;
- **fail** — **do not advance.** Diagnose from what the output shows, and give the
  next diagnostic or fix command as its own step, under the same rules. A fix that
  would be destructive takes the hard rule's confirmation first;
- **cannot tell** — ask for the specific output that decides it.

# 4. Record

After each judged step, **comment the result on the issue, redacted**: the step, pass
or fail, and the deciding lines of output with anything secret-looking replaced by
`[redacted]`. **Then tick that step's checkbox in the issue body**, changing
nothing else in it. Both are authored writes under
`references/authored-write-form.md` and `references/posting-identity.md`.

# 5. Finish

When the steps are done:

1. **check *Done when*** against the output — ask for a final check where it needs
   one;
2. **comment the summary** on the issue: what passed, what was diagnosed and fixed,
   any runbook disagreement to correct;
3. **close the issue** as completed where *Done when* holds; otherwise leave it
   open and say what is still open;
4. **comment on each issue it unblocks** that the step is done — for example
   "backfill complete" — linking this issue, and stating no new dependency.

# Report

In this session: the issue, each step's result, the diagnoses and fixes, any
runbook or issue-text correction flagged, any secret exposure and the rotation
advised, whether the issue was closed, and the issues commented as unblocked.
