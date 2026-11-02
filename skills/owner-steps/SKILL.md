---
name: owner-steps
description: Walk the owner through one `[Manual]` owner-steps issue, one step at a time, while they run each command on the live server or console and paste the output back — confirm its blockers are cleared on GitHub, give each exact command with where and as whom to run it and what to expect, judge each pasted result against that expectation and diagnose a failure rather than advancing, record each step done or not done on the issue, with its output kept redacted in the session, and tick it, and close the issue only when its "Done when" holds. It follows the repository's runbooks and its recorded server access (by default SSH as the deploy user without sudo; root only in the provider's web console, through a short script where the console cannot paste), never suggests an unrequested destructive command, and never asks for or repeats a secret. Use when the owner wants to work through a manual step, a `[Manual]` issue, a post-deploy check, a backfill or a key placement.
---

# Owner steps

The owner is at a terminal on the live server, or in a provider's web console;
this session is not. It gives **one step at a time**, the owner runs it and
pastes the output back, and this session judges the result, records it on the
issue, and gives the next step. **It runs nothing on the server itself, and it
never sees a secret.**

The issue is a `[Manual]` issue in the form `references/manual-step-issues.md`
states; that rule says what each part means. **Where the repository files no
such issues** (`manual-steps.issues` is not `true`, the default), walk the steps the owner gives,
in the same form, exactly as below — but the record is this session's report:
there is no issue to comment on, tick or close. This file is the contract; the
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

**The repository's values come first**: read `manual-steps` from its
`.claude/agent-policy.json` once, at the start, as `references/agent-policy.md`
says. Its `runbooks` win over everything, then its `server-access` and
`specifics`, then these defaults:

- **SSH reaches the live server as one deploy user** — `server-access.ssh-user`,
  else the one the runbooks name — **with no sudo** unless `server-access.sudo`
  is `true`. Without it, never suggest `sudo`.
- **Root commands run in the hosting provider's web console**
  (`server-access.root-console`), never over SSH.
- **A console that pastes anything** — `digitalocean` — takes a root command as is.
- **Any other console — `hetzner`, `other`, or none recorded — takes the script
  route**, because Hetzner's cannot paste shift characters (none of
  `| > & " _ : ~ ( ) { }` and the like) and an unknown one may not. A root step
  is then three steps:
  1. as the deploy user, over SSH, write the commands into a temporary script in
     that user's home — for example `~/<name>.sh` — and make it readable; give
     the script's contents and the command that writes it;
  2. as root, in the console, the owner types only `bash /home/<user>/<name>.sh`;
  3. as the deploy user, delete the script once its output is judged.
- **Keys** go only into the server's env files or the app's own dialogs.
- **Long jobs** run under `nice` inside `tmux` or `screen`, so a dropped
  connection does not kill them; give the command to reattach.

**`specifics` are recorded facts, not commands to run**: an app path, a restart
command, a command never to run on this server. A runbook that disagrees with
one wins, and the difference is reported so the owner can correct the file.

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

After each judged step, **comment the result on the issue**: the step, done or not done — never
the output itself, which stays in this session's report, redacted, since no forge
write reports how a check came out (`references/authored-write-form.md`). **Then tick that step's checkbox in the issue body**, changing
nothing else in it. Both are authored writes under
`references/authored-write-form.md` and `references/posting-identity.md`.

# 5. Finish

When the steps are done:

1. **check *Done when*** against the output — ask for a final check where it needs
   one;
2. **comment the summary** on the issue: what was done, what was diagnosed and fixed,
   any runbook disagreement to correct;
3. **close the issue** as completed where *Done when* holds; otherwise leave it
   open and say what is still open;
4. **comment on each issue it unblocks** that the step is done — for example
   "backfill complete" — linking this issue, stating no new dependency, and
   answering no open question or hold item there; that is the owner's to answer.

# Report

In this session: the issue, each step's result, the diagnoses and fixes, any
runbook or issue-text correction flagged, any secret exposure and the rotation
advised, whether the issue was closed, and the issues commented as unblocked.
