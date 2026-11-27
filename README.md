# Agent Skills

Claude Code skills for the whole life of a change: planning a feature into
issues, implementing them in parallel, opening and supervising the pull
requests, repairing what CI and review find, and settling and merging what is
done. Alongside them sit the shared rules every skill applies, and a short set
of general rules for every session.

They are generic on purpose. Nothing here knows which company you work for or
how you write. That comes from layers you put on top.

## A note on how the skills read

The `SKILL.md` files are dense, and that is deliberate.
[Issue #51](https://github.com/baseten/agent-skills/issues/51) benchmarked a
plain-English rewrite of the densest section against the current text, across
all 21 eval scenarios on Sonnet and Haiku. The plain version made the models no
better: identical on Sonnet, worse-to-indistinguishable on Haiku. So the skills
are written for their actual reader. People get their own entry points instead:
each skill's `NOTES.md` explains the reasoning behind its rules, and
`skills/backlog-orchestrator/README.md` has a plain-language overview and a
glossary of the coined terms.

## How the layers fit

At first glance a set of generic skills looks like it should be enough. In
practice every team needs its own facts (which repositories, which tracker, what
the base branch is called, how to trigger the review bot), and every person
needs their own voice. The obvious fix is to fork the generic skills and add
them. I tried that, and every fork drifted: the stale copy is what got
installed, so the stale copy is what ran.

So the skills come in three layers, each shipped as its own plugin:

1. **This repository, the `agent-skills` plugin.** The process, and the rules
   that govern it. It holds nothing company-specific or personal (*Personal
   skills stay out*); `scripts/check_no_machine_paths.py` rejects machine paths.
2. **A company layer.** Thin skills that each extend a generic one and carry
   only the company's facts, plus any company-only tools. A layer skill declares
   `metadata.extends: <generic skill>` in its frontmatter and invokes the
   generic skill with its settings as arguments. Its plugin declares a
   dependency on `agent-skills@baseten`.
3. **A personal layer.** Voice, style guides and identity values such as
   accounts and a branch prefix, printed into the session's context by a plugin's
   SessionStart hook. It is data, not a third wrapper skill: a company layer
   that writes prose uses whichever guide the session's instructions name, so
   anyone can plug in their own.

Two things keep a session on the layer you meant. The general rules tell it to
prefer a skill that extends another over the one it extends, and a generic skill
that starts a run hands the run to an installed layer over it, unless that layer
is what invoked it (`rules/run-start.md`).

The general rules themselves are `global-instructions.md`. The plugin's
SessionStart hook prints them under **General rules (agent-skills plugin)** at
every session start, resume, `/clear` and compaction included. It prints nothing
when the user's `CLAUDE.md` (`$CLAUDE_CONFIG_DIR/CLAUDE.md`, else
`~/.claude/CLAUDE.md`) already holds a block opening `<!-- agent-skills:begin`,
so a machine that writes the rules there reads them once.

## Install as a plugin

The plugin is `agent-skills`, from the `baseten` marketplace that
`.claude-plugin/marketplace.json` declares. (`agent-skills` is a marketplace
name Claude Code reserves for Anthropic's own.)

### On claude.ai

This is the route to use. A plugin enabled on a claude.ai account reaches every
session signed in to that account: Claude Code on the web, a self-hosted runner
and the local CLI alike. The one exception today is a cloud session that another
session creates, which is how `conductor`, `backlog-orchestrator` and `swarm`
start their runs and workers; see
[Sessions another session creates](#sessions-another-session-creates).

1. On claude.ai, open **Customize > Plugins**, choose **Add > Add marketplace**
   and enter `baseten/agent-skills`.
2. Enable `agent-skills`, and any layer plugins you use, from the same page.
3. Update Claude Code to v2.1.275 or later, the release that syncs account
   plugins into terminal sessions.
4. Start a new session. Plugins sync when a session starts; an open session says
   so and picks them up with `/reload-plugins`.

To keep a machine out of the sync, set `syncClaudeAiPlugins` (and, for skills
uploaded to the account, `syncClaudeAiSkills`) to `false` in its user settings.

### From the CLI

Where claude.ai is not an option, such as a machine signed in with an API key:

```bash
claude plugin marketplace add baseten/agent-skills
claude plugin install agent-skills@baseten --scope user
```

To update later, `claude plugin marketplace update baseten`, then
`claude plugin update agent-skills`.

### Sessions another session creates

A cloud session created by another session's `create_session` tool gets the
account's skills but none of its plugins. It starts without the variable that
turns plugin sync on, so its synced-plugins folder stays empty
([anthropics/claude-code#111802](https://github.com/anthropics/claude-code/issues/111802),
open as of 2026-11-27). That is every cloud session `conductor` dispatches,
`swarm` starts as a worker, and `backlog-orchestrator` starts through `swarm`.
A conductor's run stops at its preamble with `failed: missing skills`, having
written nothing, and a worker starts without the skills its brief names.

Until that's fixed, install the plugin from the CLI in the environment's setup
script, and turn claude.ai plugin sync off there so no session gets two copies:

```bash
{
  claude plugin marketplace add baseten/agent-skills
  claude plugin install agent-skills@baseten
  python3 - <<'EOF'
import json, os
p = os.path.expanduser("~/.claude/settings.json")
s = json.load(open(p)) if os.path.exists(p) else {}
s["syncClaudeAiPlugins"] = False
json.dump(s, open(p, "w"), indent=2)
EOF
} >>~/agent-skills-setup.log 2>&1 || true
```

The session and the sessions it creates then load the same `agent-skills:*`
skills from the same snapshot, so their version lines match. A few things come with it:

- **Sync is off for every claude.ai plugin in that environment**, not only this
  one. Account skills still sync.
- **A private layer needs a token.** The setup script has no GitHub
  credentials for a private marketplace ([Why this repository is
  public](docs/other-install-routes.md#why-this-repository-is-public)), so a
  layer like `close` needs a read-only token in the environment; the layer's
  own README says how.
- **The version is the snapshot's.** The setup script runs once and its result
  is reused for about seven days, so the plugin stays at the `release` it
  installed. Any edit to the script rebuilds it sooner.
- **Fixing it in the created session doesn't hold up.** It can clone
  and install the skills mid-session, and they do load, but it stops to ask
  permission to download and run the script, and nothing in its prompt avoids
  that.

When the bug is fixed, delete the block. The snapshot rebuilds and the synced
plugin comes back.

### Gotchas

- **One route per machine.** Don't CLI-install a plugin you've also enabled on
  claude.ai, or a session gets two of it. The same goes for a copied skill
  beside the plugin, which loads too and wins the bare name, so a stale copy
  runs in place of the plugin. Move a machine off copies by deleting them, and
  `~/.claude/.agent-skills-install` with them, since the version line falls back
  to that stamp. `AGENT_SKILLS_SKILLS=0 bash bootstrap.sh` names any it finds.
- **Old uploads shadow the plugin.** A skill zip-uploaded to claude.ai under the
  same name as a plugin's skill wins over it. Delete the upload.
- **A CLI-installed plugin's dependency isn't met by a synced one.** A
  CLI-installed layer beside a claude.ai-synced `agent-skills` does not load.
  Install both the same way.

The skills name each other bare, which resolves to the plugin's skill where
nothing else holds the name. The general rules say that a bare name and
`agent-skills:<name>` are the same skill.

### What the plugin installs

**The marketplace installs the `release` branch, never `main`.** A plugin
installs the repository as committed, and `main` commits neither each skill's
`references/` nor its `.source` stamp. `.github/workflows/release.yml` rebuilds
`release` from every push to `main` that passes its checks, with
`scripts/build_plugin_release.sh`, which generates both. It stamps the `main`
commit the build came from, so the version line names a revision of this
repository, then force-pushes. Nobody edits `release`. Its plugin version is the
release commit, so every build is an update.

To see which revision a session loaded, read its version line: every skill that
starts a run opens with `running <skill> @ <commit> (<date>)`, read from that
`.source` (`rules/run-start.md`). On disk, a synced plugin lives under
`<config dir>/plugins/synced/` and a CLI install under
`<config dir>/plugins/cache/baseten/agent-skills/`.

### Other routes

`bootstrap.sh` predates the plugin, and it is no longer the way to install the
skills. It stays for three things: a cloud environment's setup script where the
plugin is not available, the managed rules block it writes into
`~/.claude/CLAUDE.md` (`AGENT_SKILLS_SKILLS=0` writes only that), and the one
thing the plugin cannot do, which is provision a second GitHub MCP server that
reads cross-repository issue dependencies and Projects v2 in a cloud session
(`AGENT_SKILLS_GH_MCP=1`). `docs/other-install-routes.md` covers all three, and
Codex.

## Permissions

This repository ships no permission rules. It used to merge a `permissions.json`
allowlist into `~/.claude/settings.json`, and stopped on 2026-11-25: auto mode is
where these skills run, claude.ai connector tools are named
`mcp__claude_ai_<Name>__<tool>` in the CLI so the file's connector entries never
matched there, and in cloud sessions those tools follow the connector's own
settings on claude.ai. `bootstrap.sh` removes, once, the entries an earlier run
recorded in `~/.claude/.agent-skills-permissions.json`, keeping anything added
by hand. The evidence, and the way back if a worker stalls on a prompt, are in
`skills/swarm/NOTES.md`, *Blocked workers*.

## The skills

Each skill's `SKILL.md` description says when to use it; this is the map.

**Implementing and shipping**

- `implement-issue` — one tracked issue, or a branch with no PR, from
  implementation through supervision to settle and merge.
- `implement-issue-core` — internal: implements exactly one issue to a durable
  remote PR; invoked only by `implement-issue`, `backlog-orchestrator` or a
  `swarm` worker.
- `ship-branch` — the findable name for taking already-committed work through
  `implement-issue`'s supervised path.
- `create-pr` — opens a correctly linked PR, keeps stack bases and
  `Depends on:`, and triggers the repository's review automation.
- `supervise-prs` — watches a set of open PRs until each is finished, routing
  feedback and dispatching bounded repairs; never merges.
- `repair-pr` — one bounded repair pass on a PR, for a CI failure, a review
  round or a settle-time finding.
- `resolve-pr-comment` — addresses one review thread under the repository's
  review workflow.
- `swarm` — fans independent tasks out to parallel isolated workers and
  supervises them, including everything a remote worker session needs.

**Reviewing**

- `review-pr` — drafts a review of someone else's PR as one unsubmitted pending
  review for the owner to edit and submit.
- `review-docs` — checks a PR's documentation against the codebase, in a review
  that ends by contract after one pass and one re-check.
- `review-skill` — reviews a change to a prose contract by what it makes a
  reader decide, against the scenarios that pin it.

**Planning and coordinating**

- `conductor` — the owner's daily view across repositories: which epics run,
  in what order, dispatching and checking on every run.
- `write-spec` — turns a brief into one spec document and returns its link.
- `plan-feature` — plans a parent issue, epic or brief into PR-sized child
  issues, each a full spec.
- `validate-backlog` — validates a bounded issue DAG before anything runs on
  it.
- `normalize-github-dependencies` — converts dependencies described in issue
  text into GitHub's native blocked-by links.
- `backlog-orchestrator` — runs a validated issue set as parallel waves of
  workers, supervising every PR it opens.
- `owner-steps` — walks the owner through a `[Manual]` issue one command at a
  time, judging each pasted output.

**Settling and merging**

- `settle-and-merge` — the closing sequence over a set of PRs: summary,
  decisions, ranking, then the merge gate.
- `summarize-wave` — a plain-language account of what a settled wave did, and
  what a person still has to handle.
- `settle-outstanding-decisions` — walks the owner through the decisions only
  they can make, one at a time, and records each.
- `plan-merge-order` — ranks a settled wave's open PRs by how much each
  unblocks; read-only.
- `merge-stack` — merges one PR or a stack and restacks the descendants.

**Dependency upgrades**

- `upgrade-npm-dependency` — upgrades one package or coupled group, proven by
  characterization tests written before the bump.
- `npm-dependency-upgrade-orchestrator` — triages a batch of upgrades and
  dispatches them through `swarm`, merging only where the repository opted in.

`docs/orchestration-overview.md` explains how the orchestration skills behave
once started: runtimes, autonomy, per-repository policy, recovery, PR
supervision and settled waves.

## Shared rules

`rules/` holds each rule more than one skill applies. A rule is not a skill:
nobody invokes it, and it has no `SKILL.md`.

- `absence-is-not-a-verdict.md` — a query that returned nothing is evidence
  about the query, not a clean result.
- `establish-do-not-assume.md` — a claim or an assumption is checkable, not
  evidence, and holds only as of when it was read.
- `prose-review-round-budget.md` — a prose review ends on a fixed budget: one
  pass, one re-check.
- `a-passing-test-is-not-a-verified-fix.md` — what defeats "make the test fail
  first".
- `authored-write-form.md` — the shape of any write an agent authors on a
  forge, its footer, and when a PR body may change.
- `posting-identity.md` — which author a forge or tracker write carries,
  established by reading one back.
- `agent-policy.md` — the contract of `.claude/agent-policy.json`, including
  what `auto-merge` grants.
- `review-feedback.md` — what a run may auto-fix, and which threads it must
  leave to a person.
- `draft-state.md` — when a run may promote a draft PR, and what an explicitly
  held draft is.
- `repair-rounds.md` — repair escalation and budgets, from the dispatching
  side.
- `mechanical-pushes.md` — which pushes are mechanical and never re-trigger
  review.
- `review-trigger.md` — what an automated review trigger is, and the only
  review action a run takes.
- `ci-and-review-verdicts.md` — what makes CI green and a review clean, on one
  commit.
- `ci-attribution.md` — whether a red check is the PR's own failure.
- `watch-and-read.md` — when a supervising run arms its watch and reads.
- `platform-pr-posture.md` — how a supervising skill overrides the platform's
  drive-to-green posture.
- `wake-budget.md` — the bounded check-ins a run with nothing in flight arms.
- `manual-step-issues.md` — how owner steps are filed as `[Manual]` issues.
- `conductor-exchange.md` — a run's side of a conductor's coordination, and the
  session vocabulary.
- `operator-output.md` — what an orchestration run writes to the owner, and in
  what order.
- `run-start.md` — the layer hand-off and the version line every run opens
  with.
- `linear-mechanics.md` — how reads and writes to Linear actually behave.
- `node-and-pnpm-upgrades.md` — moving a project to a new Node or pnpm version.
- `field-feedback.md` — how a long-running run reports, once at wrap-up, what
  in its own contract did not work.

A shared rule cannot just sit at the repository root, because an installed
skill cannot read `../../rules/`. Nor can it live inside one skill, which would
make that skill a dependency of every other. So `scripts/refresh_shared_rules.sh`
copies each rule into `skills/<name>/references/` for every skill that applies
it, at install or release time. The copies are gitignored and never committed to
`main`, and `scripts/check_shared_rules.py` fails the build when one diverges
from its source or a skill cites a rule it does not carry.

Reasoning for a rule lives beside it as `rules/<name>-notes.md`, and is
deliberately not bundled: its reader is someone editing the rule, and they have
this checkout. `docs/shared-rules.md` keeps the longer description of each rule
and how the rules came to be extracted.

## Repository layout

```
skills/                 every directory with a SKILL.md ships
skills/*/references/    generated from rules/ (gitignored)
rules/                  shared rules, each with its -notes.md
global-instructions.md  the general rules the SessionStart hook prints
hooks/                  the plugin's SessionStart hook
.claude-plugin/         the plugin manifest and the `baseten` marketplace
schemas/                the agent-policy.json schema
CLAUDE.md               how to change a skill, and what a complete fix means here
AGENTS.md               pointer to CLAUDE.md, for agents that look for it
docs/                   audits, workflows and reference that outlive one PR
scripts/                repository checks (run in CI, runnable locally)
bootstrap.sh            the setup-script installer (docs/other-install-routes.md)
.github/workflows/      checks, and the release build
.claude/                this repository's own policy and skills
```

Adding a skill needs no change to the plugin manifest or `bootstrap.sh`: create a
directory under `skills/` with a `SKILL.md` in it, and the next release build
ships it.

### Personal skills stay out

This repository is public, so it holds general engineering workflow skills and
nothing personal. Skills that depend on someone's writing samples, voice guide
or internal material live in a private repository, and reach sessions as a
plugin of their own enabled on a claude.ai account.

`check_no_machine_paths.py` enforces this. A skill referencing a path like
`~/Documents/...` or `/Users/someone/...` fails the build, because that skill
cannot work in a cloud session and the failure is silent when it doesn't:
`` !`cat <missing path>` `` injects an empty string, so the skill loads with its
guidance gone and says nothing. Paths under `~/.claude` or `$HOME/.codex` are
fine — those exist wherever the agent runs. `test_no_machine_paths.py` holds the
forms it must reject and the ones it must not, and asserts the rejections come
from the detector rather than the harness.

## Changing the skills

The `SKILL.md` files are prose contracts executed by models, and they
cross-reference each other, so a finding on one is rarely local to where it was
reported. **`CLAUDE.md` carries the binding rules** for changing them: how to
classify a review round's findings, the consequence sweep, and when a change
owes a guard. Read them there rather than in a summary here, which is exactly
where a condition gets dropped. `AGENTS.md` points at the same file.

`docs/review-fix-workflow.md` is the long form, with the evidence from this
repository's history, and `docs/invariant-12-gate-audit.md` is the worked
example of walking a whole axis at once. Running these skills against this
repository has three known mismatches: `CLAUDE.md`, *Using this repository's own
automation on this repository*, names them.

## Checks

`.github/workflows/checks.yml` runs on every pull request. Everything in it is
deterministic — no model calls, no API key, no cost — and every check is
runnable locally:

```bash
bash scripts/refresh_shared_rules.sh                  # generate references/ first; they are not committed
python3 scripts/check_skills.py
python3 scripts/check_shared_rules.py                # bundled rules match rules/, and no skill cites one it lacks
python3 scripts/test_shared_rules.py                  # and each of those guards can actually fail
python3 scripts/check_no_machine_paths.py             # no skill depends on one machine's filesystem
python3 scripts/test_no_machine_paths.py              # and that detector can actually fail
python3 scripts/check_word_budgets.py --report       # no contract outgrows its budget; --report adds runtime load
python3 scripts/test_check_word_budgets.py            # and each of its guards can actually fail
python3 scripts/test_run_evals.py                    # the eval runner's own tests
bash skills/swarm/scripts/test-checkpoint-capture.sh
python3 -I scripts/test_work_queue_prdata.py          # conductor's work-queue scripts, against a stubbed gh
bash scripts/test_bootstrap_stamp.sh                  # bootstrap.sh's install stamp, against a scratch HOME
bash scripts/test_bootstrap_instructions.sh          # bootstrap.sh's managed block in ~/.claude/CLAUDE.md
bash scripts/test_session_instructions.sh            # the plugin's SessionStart hook
shellcheck --severity=warning bootstrap.sh skills/*/scripts/*.sh scripts/test_bootstrap_stamp.sh scripts/test_bootstrap_instructions.sh scripts/build_plugin_release.sh hooks/*.sh scripts/test_session_instructions.sh
bash scripts/eval_reminder.sh origin/main             # advisory, never fails
```

`check_skills.py` catches what is decidable from the text: frontmatter that
disagrees with its directory, an `evals.json` that no longer parses or has
duplicate ids, and — the one worth having in a document this cross-referenced —
a `(see Some Section)` or `` `other-skill`, *Some Section* `` pointer that
resolves to no heading. A section can be cited by the first clause of a longer
heading; anything else is an error, including a cross-reference naming a skill
that does not exist.

`check_word_budgets.py` holds every `SKILL.md`, every contract file beside one
(`swarm`'s `runtime-remote.md`; not `NOTES.md` or `README.md`), every file in a
skill's `schemas/` directory (`backlog-orchestrator`'s `checkpoint-output.md`), and every rule in
`rules/` to a word budget in `scripts/word_budgets.json`, because the contracts grow by
accretion and a long one is what a compaction summarises worst (#157). The
budgets started at each file's size and work as a ratchet: a file over its
budget fails, a file with no entry fails, and a budget more than 2% above its
file's count fails too, so a budget cannot be padded ahead of growth and a cut
turns the check red until `--tighten` records it. Each entry also carries a
target — 3,000 words for a leaf skill, 8,000 for an orchestrator, 1,500 for a
rule or a file beside a `SKILL.md` — which is reported and not enforced; so is
`--report`'s runtime load, a skill's `SKILL.md` and the files beside it plus the
references it bundles. A word count is a token
count, not a reading, which is why this check is allowed where the ones below
were not. Raising a budget is governed by `CLAUDE.md`, *Checks*.

Contract and NOTES heading sets are kept separate, which matters more than it
sounds: `NOTES.md` is keyed by the section names of `SKILL.md` by design —
`backlog-orchestrator` shares 20 of its 21 — so a merged set would give almost
every contract section a shadow heading, and renaming one in `SKILL.md` alone
would leave its references resolving happily against `NOTES.md`. References
inside `NOTES.md` resolve against both, since a note legitimately cites a
contract section or one of its own.

Four checks that read the contracts' prose were removed, and what they turned out to verify
is worth recording so nobody rebuilds them.

`check_contract_placement.py` held 247 assertions, 205 of them a single `"phrase" in file`.
Such an assertion pins the sentence rather than the rule: it fails on a rewording that
improves the contract and passes on one that breaks it. Its two duplicate-rule assertions
looked like the exception — a rule stated twice merges clean with no conflict marker, which
happened here — but appending a *paraphrase* of the same rule to a second contract passed
the check, so it caught only the copy-paste case a reader would notice anyway.

`check_rule_locality.py` asserted what `CLAUDE.md` claims about itself, that its pointer
files never restate a rule. It matched verbatim phrases, so paraphrasing a rule into
`README.md` passed while the duplication remained — again catching the visible case and
missing the drifting one.

`check_skills.py`'s cross-reference half confirmed that a `` `skill`, *Section* `` pointer
named a heading that exists. Gutting a section while leaving its heading in place left
nineteen pointers resolving to nothing and the check green; a reference written in a
near-miss form was never examined. It verified names, not links, and only the names shaped
the way its regex expected.

The pattern is one thing pointed four ways: a string matcher aimed at meaning. It is
evadable by rewording, trips on innocent overlap, and covers only the phrasings its author
anticipated. What remains in CI reads **tokens** — a frontmatter name against its directory,
an `evals.json` that parses — because a token
cannot be paraphrased and still be itself. Whether the prose *means* the right thing is
answered by reading it, and by the eval corpus (`CLAUDE.md`, on comparing two readings of a
change that should not alter meaning).

## Running the evals

`CLAUDE.md` states the method — two arms, the same assertions, and the information in the
disagreement. `scripts/run_evals.py` does the deterministic half of it, so the method stops
depending on whoever remembers it:

```bash
python3 scripts/run_evals.py prepare --skill <name> --base origin/main
# dispatch one reader per packet.json; save its reply to answer.md beside it
# grade answer.md against key.json into grading.json
python3 scripts/run_evals.py score --round <dir>
```

`prepare` materialises both arms from git into a scratch directory outside the tree, and
splits each scenario in two: `packet.json` for a reader, carrying the prompt and the
contract path, and `key.json` for a grader, carrying `expected_output` and the assertions.
The split is the point — a reader that has seen either is grading its own answer — and
`name` is withheld too, because a scenario name telegraphs its verdict in three words.

**A skill that cites another's rules as its own names it in `"companions"`** at the top
of its `evals.json` — `backlog-orchestrator` and `npm-dependency-upgrade-orchestrator`
name `swarm`, which holds the worker mechanics both apply. `prepare` then puts each
companion's `SKILL.md` and `NOTES.md` into both arms' contract directories, as
`<companion>-SKILL.md` and `<companion>-NOTES.md`, each arm's taken from its own revision,
and the reader's packet says they are part of the contract. Any other top-level `.md`
beside a `SKILL.md` — `swarm`'s `runtime-remote.md`, which its contract has a tier-2 run
read — joins the contract the same way, for the skill itself and for each companion,
because an install carries the whole skill directory; so does every file in a
`schemas/` directory beside it, kept at `schemas/<name>` so the contract's citation of it
resolves. That is what lets a rule
move between skills and be compared: without it, the new arm reads a pointer to a rule it
was never given, and a behaviour-preserving move scores as a deletion.

That also means a pointer to a side file can never fail a default round: the reader
is told the side file is contract, so it holds the moved rule whether or not the
pointer fired. `prepare --lazy-side-files` tests the pointer instead. The side files
stay in the contract directory, but the reader is told to read `SKILL.md` first, to
open a side file only where the text sends it, and to name each one it opened with
the line that sent it; `key.json` lists the arm's side files for the grader. Use it
for any change that moves text into a side file or edits a pointer to one.

`prepare --batch N` puts up to N scenarios into one reader packet per arm
(`<arm>/batch-XX/packet.json`), so a reader reads the contract once rather than once
per scenario. It answers each under `## eval <id>`; the grader grades that section
into the scenario's own `grading.json`, and `score` reads them as before. Both arms
are batched alike, so whatever one prompt does to the reading of the next, it does
to both.

`score` reads the `grading.json` files and reports the pass rate per arm, then the
disagreements, which is the only part that carries information. It marks an ungraded
scenario as ungraded rather than counting it either way.

**The model calls are not in here.** This repository has no API key and *Checks* above gives
the reason model-graded work stays out of CI; dispatching readers is the caller's, whether
that is a person or an agent. **A skill new in this branch has no old arm**, and `prepare`
says so: its scores are a baseline for the next round, not a result, because there is
nothing to disagree with. **A skill renamed in this branch is not new**: `prepare` finds
the rename in git and reads the old arm from the old directory at the base, so a rename can
be compared rather than scored as a new skill.
