# Run start

This is the rule other skills mean when they cite *run start*: the two things a skill that starts a run does before anything else — hand the run to an installed skill that extends it, and name the version it is running.

**It is not a skill and nobody invokes it.** It is a shared rule, held once at
`rules/run-start.md` and copied into each skill that applies it by
`scripts/refresh_shared_rules.sh`. A skill reads its own
`references/run-start.md`, which works after `bootstrap.sh` has
installed only that skill's directory, and travels with the skill if it is
moved into a plugin. Edit the source, never a copy; check_shared_rules.py fails if a generated copy diverges.

**The skills that apply it are those a person or a dispatch prompt can invoke to start a run**, and each cites this rule at its start. Each applies both parts whenever it is invoked — by a person, a prompt, a layer or another such skill — so a run that passes through two of them prints two lines. A skill only ever composed inside a run applies neither. A prompt that resumes a run without invoking its skill again, such as a restart after a clear, is not a start: neither part applies.

The *config directory* below is `$CLAUDE_CONFIG_DIR` where it is set, otherwise `~/.claude`.

## A skill that extends this one

**A layered skill extends a generic one.** It declares so in its frontmatter,

```yaml
metadata:
  extends: <generic skill>
```

says so by name in its description, holds only settings, and invokes the generic skill **in the same session** with them as invocation arguments, deciding itself how its settings combine with the arguments it was given. The process stays the generic skill's. A layer that ran the generic skill in another session or a subagent would be handed the run straight back, since the test below reads only this session.

**First, before the version line or any other read or write, find every available skill that extends this one**, from both sources:

- **the frontmatter of every SKILL.md this session can read** under the config directory's `skills/`, account skills synced there included, and the working repository's `.claude/skills/` — `grep -rlsE '^[[:space:]]+extends:[[:space:]]*<this skill>[[:space:]]*$' --include=SKILL.md "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills" .claude/skills`;
- **the session's skill listing**, where a description says the skill extends this one.

One name under two namespace prefixes (`<namespace>:<name>`) is one skill. Then:

| found | act |
|---|---|
| none | carry on |
| one, and this invocation came from it — its text invoked this skill in this session | carry on: it is the layer, and this is its process |
| one, and anything else invoked this skill | **stop and hand off**: write nothing, invoke it with this invocation's arguments verbatim, and follow it; it invokes this skill back with its settings added |
| more than one, none of them the invoker | stop, write nothing, and ask the invoking user which to run, naming each; with nobody to answer, name them and end with `final status: failed · no PR`, sent as the run's report where its invocation names a conductor. Two layers over one skill is an install to fix, never one to pick silently |

**What a session can see of another skill's frontmatter is not established on every install route** (`rules/run-start-notes.md`): where neither source shows a layer, this skill runs as itself.

## The version line

**After the hand-off check, the first line the run prints — before its first state block, report or reply — is:**

```text
running <skill> @ <commit> (<date>)
```

`<skill>` is this skill's own frontmatter `name`. **The version is read, never written from memory**, from the first of these that reads:

1. `.source` in this skill's own directory — the one its SKILL.md was loaded from, else the config directory's `skills/<skill>/` — its `commit` and `committed` values, written by the installer;
2. this skill's own frontmatter `metadata.version`, `<commit> <committed>`, which the packaging of an uploaded skill writes;
3. the config directory's `.agent-skills-install`, **only where this skill's own directory cannot be found at all** — a directory found without a `.source` was left by an earlier install or came from elsewhere, and the install-wide stamp does not describe it.

`<date>` is the date part of `committed`. **Each value nothing reads is written `unknown`**, as is one the stamp itself records as `unknown`: `running conductor @ unknown (unknown)`. **No skill keeps its own version by hand**: a version stated from memory, or taken from another skill's stamp, is the defect this line exists to expose.

A layered skill prints its own line before it invokes the skill it extends, which then prints its own, so a layered run names both versions. **Where the line lands in a forge write** — a ledger row on a forge, a checkpoint comment — its commit is written as the *authored write form* shared rule writes any SHA there: bare, never in a code span, and as `owner/repo@sha` taken from `.source`'s `repo` where that names another repository.

**A coordinated run's reports carry the line as well** — the *conductor exchange* shared rule, *Reports*, says where.
