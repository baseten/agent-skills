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
version the run never loaded; only a restart that lost the line reads it again.

**The conductor's status request does not list the line.** Its text in
`conductor`, *2. Ask*, summarises the form as the header, the state and the four
parts, and asks for the conductor-exchange form by name, which now carries the
line. It was left unchanged to keep this change's conductor edits to the startup
step and the ledger field, while other work edits that skill; a run that loaded
no conductor-exchange answers without the line, and the ledger records `not
reported` for it, which is true.
