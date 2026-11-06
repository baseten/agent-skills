# Notes — run-start

Reasoning for `rules/run-start.md`. Deliberately *not* bundled into each skill:
its reader is a person editing the rule, who has this checkout.

## Why this rule exists (owner's decisions, 2026-11-05 and 2026-11-06)

An owner audit of a cloud session could not tell which revision of a skill that
session had run. `bootstrap.sh` already wrote the answer to disk — `.source` per
skill, `.agent-skills-install` once — but nothing read it, so the evidence sat in
the container and never reached the transcript, the run's reports or the
conductor's ledger. The version line is the reader.

The same audit raised the second half. A skill can reach a session by two routes
— this repository's bootstrap, or an upload to a claude.ai account — and a
private layer over a generic skill (settings only, passed as invocation
arguments) is only useful if the session runs the layer when the owner meant it.
The owner's ruling: one install route per skill, generic skills from bootstrap
only, layers from uploads only, and a generic skill that finds a layer over itself
hands the run to it.

## A skill that extends this one

**Why the check is the generic skill's first step, not only the session's
choice.** Bootstrap's managed `CLAUDE.md` block tells a session to prefer a layer
when choosing (`global-instructions.md`), but a dispatch prompt, a restart prompt
or a person can still name the generic skill directly. The hand-off catches the
run at the one place every route passes through.

**Why "invoked by it" is the loop guard, and not a flag or an argument.** A layer
invokes the generic skill, which then sees the layer and would hand back. Any
marker passed as an argument would be text a dispatch prompt could also carry,
and would silently disable the hand-off for a run the layer never saw. Whether
the layer's own text invoked this skill is in the session's context and nowhere
else, so that is what the test reads.

**Why two layers stop the run.** Choosing one silently runs settings the owner
may not have meant, which is the failure the hand-off exists to prevent. The
same name under two namespace prefixes is not two layers: a local install and an
account sync of one skill show up as `<name>` and `<namespace>:<name>` (observed
below), and treating them as two would stop every run on a machine that has
both.

**Why the layer must invoke the generic skill in its own session.** The loop
guard is the session's own context. A layer that ran the generic skill through a
subagent or a dispatched session would leave nothing there to read, and the
generic skill would hand the run straight back to it.

**Why a resume is not a start.** A restart after a clear resumes from a ledger or
a checkpoint and invokes no skill, and the guard's context is gone with the clear;
applying the hand-off then would hand a conductor's own run to its layer on every
restart. A restart prompt that does invoke the skill — a layer's restart prompt
naming the layer — is a start, and both parts apply as usual.

**Why it fails open.** Where no layer is visible the generic skill runs as
itself, because that is what every user of this public repository without a layer
needs. The cost — a run without its layer's settings — is visible in the version
lines, which name only the generic skill.

### What a session can see: observed, and assumed

Observed in a local Claude Code session on 2026-11-06 (CLI, `CLAUDE_CONFIG_DIR`
set):

- **the skill listing carries a name and a description, nothing else** — no
  `metadata`;
- **account skills synced from claude.ai appear as `anthropic-skills:<name>`**,
  beside a locally installed skill of the same bare name, both listed;
- **several of those synced skills were listed with no description at all**,
  though their SKILL.md on disk has one — so the listing is not a reliable
  channel for a layer's declaration either;
- **synced account skills are on disk**, at
  `<config dir>/skills/synced/<bucket>/<name>/SKILL.md`, frontmatter intact:
  `license` and `compatibility` survive the round trip. No uploaded skill yet
  carried `metadata`, so its survival is unobserved.

That is why the check reads both sources and the `grep` recurses: the files are
the reliable channel where they exist, the listing the fallback.

**Assumed, and not yet observed in a cloud container:**

- that an uploaded skill reaches a cloud session's disk under the config
  directory as it does locally, `metadata` intact;
- that a skill uploaded to claude.ai can invoke a bootstrap-installed skill in the
  same cloud session, which every layer depends on;
- that the `grep` above, or the listing, finds the layer there.

**The first real cloud run of a layered skill must confirm all three**, and
record the result here: the transcript's version lines (both, layer first) show
the invocation worked; a generic skill invoked directly in that container,
handing off, shows the detection worked.

## The version line

**Why it is read from the stamp and never kept by hand.** A hand-kept version
drifts, which is the very thing an audit needs it to catch; bootstrap's own
comment makes the same argument for the stamp. So the line reports what the
installer wrote and `unknown` where it wrote nothing.

**Why the install-wide stamp is the last source, and only where the skill's own
directory cannot be found.** `README.md`, *Install from a setup script*: a skill
with no `.source` came from an install older than the stamp, or from somewhere
else. In both cases `.agent-skills-install` describes a different install, and
reporting it would put a confident, wrong commit in the transcript. It remains
useful only where the session cannot locate the skill's directory at all, and
then it is an honest best reading of the one install the container had.

**Why `metadata.version` comes before it.** An uploaded skill has no `.source`
— the upload carries the zip's files and nothing an installer writes — and
claude.ai accepts only `name`, `description`, `license`, `compatibility`,
`metadata` and `allowed-tools` in frontmatter, so `metadata` is the one place a
packager can write a version. The packager writes it into the packaged copy, never
into the tracked file, for the same reason the stamp is not committed.

**Why a consumer applies the rule however it was invoked.** A first draft said a
skill composed inside a run applies neither part; the contradiction pass before
the first push found that `ship-branch` invokes `implement-issue`, and
`implement-issue-core`, invoked directly, hands off to it, so `implement-issue`
would print nothing in exactly the runs that needed its line. The line costs one
line per consumer passed through, and a layer over the inner skill is still
handed the run, so the rule applies at every consumer's start.

**Why a forge write takes the SHA rule.** The conductor's default ledger is a
GitHub issue, and the authored write form rule (protected rule 7) says a SHA in
any forge write is bare, and another repository's is `owner/repo@sha`. The line
names another repository's commit, so on a forge it follows that rule; the chat
copy keeps the plain form. The line is not a verification report — it names the
revision loaded, not a check or its outcome — so rule 7's ban on reporting
verification does not reach it, and no protected rule's text changed.

**Which skills start a run.** Checked one by one on 2026-11-06 against the
consumer list in `scripts/refresh_shared_rules.sh`:

- applies it — `conductor`, `backlog-orchestrator`, `implement-issue`,
  `ship-branch`, `plan-feature`, `write-spec`,
  `npm-dependency-upgrade-orchestrator`: each is invoked by a person or a
  dispatch prompt as its session's outermost skill. `owner-steps` too: the owner
  invokes it directly to walk an issue.
- does not — `implement-issue-core`, since #207 an entry point only in that it
  hands off to `implement-issue`, which prints the line; `swarm`,
  `supervise-prs`, `settle-and-merge` and the settle steps, `create-pr`,
  `repair-pr`, `resolve-pr-comment`, `merge-stack`, `upgrade-npm-dependency`, the
  reviewers and the validators, which run composed inside a run whose line
  already names it, or as a single bounded task in the invoking user's own
  session. Adding one later is a consumer-list entry and a citation at its start.

**Why every coordinated report carries it, not only the first.** A conductor may
adopt a run after its first report, miss it to a failed send, or rebuild its
ledger after a clear; a line in every report costs one line and makes each
report self-describing. The run carries the line it printed at its start rather
than re-reading the stamp, because a reinstall mid-run would otherwise report a
version the run never loaded; only compaction or a restart that lost the line
reads it again. That re-read is a residual: no state-block field carries the line
(`backlog-orchestrator`'s `schemas/checkpoint-output.md`), so a reinstall mid-run
followed by a compaction reports the new stamp. A field was not added because
that schema is under other open work, and a container is seldom reinstalled
mid-run; it is the field to add if one ever is.

**The config directory.** The rule reads `$CLAUDE_CONFIG_DIR` where it is set,
because that is where Claude Code reads skills from. `bootstrap.sh` always writes
under `$HOME/.claude`; in a container that sets the variable elsewhere, its
skills would not load at all, so the two never disagree about a skill that ran.
The skill's own directory, which the session loaded it from, is read first in any
case.

**The conductor's status request does not list the line.** Its text in
`conductor`, *2. Ask*, summarises the form as the header, the state and the four
parts, and asks for the conductor-exchange form by name, which now carries the
line. It was left unchanged to keep this change's conductor edits to the startup
step and the ledger field, while other work edits that skill; a run that loaded
no conductor-exchange answers without the line, and the ledger records `not
reported` for it, which is true.

## Evals (2026-11-06, PR #209)

Five scenarios pin the rule: `implement-issue` #45 and #46 (the line from the
skill's own stamp; `unknown` where its directory has none, never the
install-wide stamp), and `conductor` #68–#70 (the ledger row records what reports
carried, `not reported` otherwise; a direct invocation hands off to the one
layer; the layer as invoker gets no hand-off, and a namespaced copy is not a
second layer). A blind two-arm round against `origin/main`, one reader per
packet and an arm-blind grader, passed every assertion on the new arm (19 of 19)
and 7 of 19 on the old; every disagreement was a gain, none a loss. The rule is
pinned there rather than in each consumer's evals because every consumer reads
the same bundled rule through a one-line pointer.
