# Manual-step issues

This is the rule other skills mean when they cite *manual-step issues*: where an
owner step a run identifies is written down, the form of that record, and what
never goes in it.

**It is not a skill and nobody invokes it.** It is a shared rule, held once at
`rules/manual-step-issues.md` and copied into each skill that applies it by
`scripts/refresh_shared_rules.sh`. A skill reads its own
`references/manual-step-issues.md`, which works after `bootstrap.sh` has
installed only that skill's directory, and travels with the skill if it is
moved into a plugin. Edit the source, never a copy; check_shared_rules.py fails if a generated copy diverges.

## Every owner step is an issue

**An owner step** is work only the owner can do outside the repository: a
post-deploy check, placing a key, a backfill, a console action, data entry, an
owner test. **Where the repository opts in, every one a run identifies is filed as
a `[Manual] <what>` issue under the repository's manual-steps epic** — never left
only in a PR body, a comment, a report or chat, which is where a step is lost.

**Filing is opt-in.** The repository's `.claude/agent-policy.json` (the *agent
policy* shared rule) carries these values under `manual-steps`, and only
`issues: true` there turns filing on. Absent that — the default — nothing is filed
and no epic is found or created: each owner step is reported, in this form,
wherever the run reports — its closing report, a status reply, a conductor's owner
pass — and the rest of this rule still holds, secrets included.

- **The epic** is the one `manual-steps.epic` names. Where none is named, find an
  open epic titled for manual steps; where there is none, create
  `[EPIC] Manual steps` and report that it was created.
- **One issue per coherent session of work** — what the owner does at one sitting,
  on one server or console. Steps that need different sittings, or that another
  step must unblock, are separate issues.
- **Search before filing**: an open `[Manual]` issue for the same step is updated,
  not duplicated.

## The form

Every `[Manual]` issue body has these parts, in this order. They are the issue's
required contents, which brevity never cuts (`references/authored-write-form.md`,
*What overrides brevity*):

```text
Owner steps. Not for an orchestrator · Blocked by: <full URLs | none> · Unblocks: <full URLs | none>

## Server access
<host and how it is reached for each step: SSH as which user, or which
provider's web console as root — per owner-steps' server access rules>

## Steps
- [ ] 1. <what> — run as <user>, where <host/console>:
      <exact command>
      Expect: <what the output shows when it worked>
- [ ] 2. ...

## Paste back
<for each step, which output to paste — never a secret value>

## Done when
<the observable end state, and how to check it>
```

- **`Not for an orchestrator`** means exactly that: no run and no conductor
  dispatches a `[Manual]` issue, and none adds one to its scope. It is an external
  prerequisite for whatever it unblocks.
- **`Blocked by` and `Unblocks` are dependency statements**, read by every skill
  that reads dependencies from issue text, and promotable into native edges — so
  name only real edges, by full URL.
- **Exact commands** come from the repository's runbooks — `manual-steps.runbooks`,
  then any the repository's docs name — and its recorded `manual-steps.specifics`;
  a command that departs from them says why.

## Never a secret

**A secret never goes in an issue, a PR, a comment or chat** — not a key, a token,
a password, a connection string carrying one, or command output that prints one.
A step that places a secret names **the env var and the file**, or the app dialog,
and says the owner types the value there. *Paste back* names output that proves
the step worked without showing the value — a variable's presence, a length, a
fingerprint, a service's health.
