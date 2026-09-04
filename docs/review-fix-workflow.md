# Resolving review rounds on a prose contract

How to settle automated review (Codex, or any diff-scoped reviewer) on this repository in
fewer rounds. `CLAUDE.md` carries the binding rules; this document is the reasoning and the
checklist behind them.

## The problem this addresses

Review rounds on `skills/*/SKILL.md` routinely reach ten or more. The cause is not reviewer
quality and not fix quality — it is that a finding on a prose contract is **not localized**,
while the reviewer reports it as though it were and the fixer patches it as though it were.

Three distinct mechanisms, each already documented in this repository from the round that
discovered it:

**1. Presence in a file is not presence at the decision point.**
`scripts/check_contract_placement.py` exists because "two review rounds on this repo were
spent on exactly that — an exception written into a step body that a predicate had already
excluded the thread before reaching, and a `no-action` classification produced by one skill
that the skill between it and its recorder never forwarded." A rule in the wrong clause
reads as correct to a reviewer and to a grep, and is inert when executed.

**2. Restated rules drift, and the fix for one round introduces the next.**
`skills/backlog-orchestrator/NOTES.md`, *Releasing a worker*: "restating it in situ is how
successive versions of it came to disagree about the same worker — every review round the
section has had found one such disagreement, each introduced by the fix for the last." That
sentence is the ten-round phenomenon, diagnosed, in the repository's own words.

**3. A limitation stated only where it was observed leaves every rule written on its
negation standing.** Same file, *Blocked workers*: "those rules do not announce themselves —
this one was two sections away and phrased as a reassurance." A reviewer scoped to the diff
structurally cannot see it.

Mechanisms 1 and 3 are invisible to a diff-scoped reviewer, so they surface one instance at
a time, over successive rounds. Mechanism 2 is actively *created* by local fixing. Together
they guarantee that a fixer optimizing for "the flagged line now reads correctly" generates
the next round.

## Classify the round before touching it

Take every finding of the round first. Fixing findings one at a time is what turns one
shape into several rounds.

| kind | signature | method |
| --- | --- | --- |
| **local** | wording, typo, an ambiguous clause; no rule changes | fix in place, sweep, done |
| **rule** | a rule is wrong, missing, or sited where nothing reads it | fix the rule, sweep its dependents |
| **shape** | several findings that are instances of one assumption failing in several places | walk the axis once (below) |

The **shape** class is the one that matters. A diff-scoped reviewer cannot report a shape;
it reports N locals. Fixing the N locals leaves the assumption intact, and round N+1 finds
instance N+1.

## The axis walk, for a shape finding

The method, and the evidence it works, are in `docs/invariant-12-gate-audit.md`: "Seven
Codex review rounds on PR #27 produced thirteen findings, ten of them on the merge path,
and all ten the same shape: an assumption the gate's author could make for
`backlog-orchestrator` that silently does not hold standalone. ... Each round discovered one
more missing supplier reactively. This audit walks the whole gate once instead."

1. **Name the axis.** Usually a rule or gate crossed with its consumers — every condition ×
   every skill that can reach it.
2. **Build the table.** One row per condition, one column per consumer.
3. **Answer one question per cell:** *what supplies this here?* Three answers only —
   supplied identically, supplied by a different mechanism, or **not supplied at all**.
4. **Fix every not-supplied cell in one pass.** That audit found three and closed all three
   together; reactively they were three more rounds.
5. **Keep the table.** It is the artifact that tells the next change what it owes: "a new
   consumer of `auto-merge` owes this table a column before it ships."

## The consequence sweep

`CLAUDE.md`, *The consequence sweep*, defines the five steps and their scope. This section
expands each with its reasoning and adds no step of its own — the steps are not restated
here, because two copies of a checklist is how the scopes come apart, which is what this
document is about.

1. **Restatements** — `skills/` is the tempting scope, and what makes it the wrong one is
   that the root-level and `docs/` files carry shared rules too, so a stale copy there is
   as contradictory as one inside a `SKILL.md`. The step's scope is defined at the pointer
   above and not restated here; this document narrowed it on its own first draft, and round
   one caught that.
2. **Inbound cross-references** — `check_skills.py` proves a pointer *resolves*; nothing
   proves it is still *accurate*. A reference surviving a rule change while describing the
   old rule is a passing check over a false statement.
3. **Negations** — the expensive class. They sit sections away from the change, read as
   reassurances rather than rules, and nothing links them to the limitation they assume
   away. Mechanism 3 above is exactly this.
4. **Decision point** — a rule in the right file and the wrong clause reads as correct to a
   reviewer and to a grep, and is inert when executed.
5. **Chain forwarding** — where the rule produces something another skill must record,
   every skill between producer and recorder has to forward it. Half of
   `check_contract_placement.py` exists for this: a `no-action` classification produced by
   one skill that the skill between it and its recorder never forwarded.

**Why collapsing beats reconciling.** Restatement is mechanism 2's fuel, and a rule stated
once cannot disagree with itself — reconciling two copies leaves both, so it buys agreement
today and the next round's finding tomorrow. The repository already settled this for one of
its own rules: `NOTES.md`, *Releasing a worker*, "Why the releasable test is stated once."

**Why a recurring shape earns a guard.** A mechanical assertion or an eval scenario is the
only tier that binds without being read, so it is the one thing a later round cannot skip
past. `scripts/eval_reminder.sh` exists at the weaker end of the same idea and stays
advisory on purpose: "it cannot know whether a change needs a scenario, only that nobody
added one."

**Why the provenance matters.** The existing `NOTES.md` entries cite their origin ("Codex
round one on the PR that introduced this section"), and that is what stops a later fixer
re-deriving the alternative an earlier round already rejected. A note without its round
reads as preference rather than as a settled argument.

## Where the rules bind, weakest tier last

1. **`scripts/check_*.py` assertions.** Mechanical, run in CI, bind whether or not anything
   read them. Highest tier available.
2. **`evals/evals.json` scenarios.** Pin a rule against the model actually applying it.
   Deliberately out of CI — model-graded, non-deterministic, and a required check built on
   them "goes red on sampling noise and teaches everyone to override it." Run on demand,
   comparing against the previous text.
3. **`CLAUDE.md`, reached through two filenames.** The skills are contractually told to
   read it by name (`implement-issue-core`, `resolve-pr-comment`, `create-pr`,
   `merge-stack`, and `backlog-orchestrator` for its resource inventory), and `AGENTS.md`
   points at it for agents whose convention looks for that name instead — Codex among
   them, which matters because Codex is the reviewer deciding whether a round ends.
   **Neither filename is loaded by every entry point**, so this tier reaches an agent only
   where its harness or its contract reads one of the two; it is also unchecked prose that
   no cross-reference check covers, so it is the tier that drifts. Method belongs here;
   anything mechanizable belongs in tier 1. (Codex raised the discoverability half of this
   on round one of the PR that added this document, against the commit before `AGENTS.md`
   landed.)

**Policy is not in this ladder.** `backlog-orchestrator/SKILL.md`, *Per-repository policy
configuration*: policy that can authorize merges "is a config file and not prose — never a
`CLAUDE.md` paragraph", because "a `CLAUDE.md` paragraph gets interpreted, and interpretation
must not decide whether a run may merge." Budgets live in
`.claude/backlog-orchestrator.json` and their values are stated there only. `CLAUDE.md`
naming a budget number would be mechanism 2 applied to this very workflow.

## Pre-flight: spend a free round first

A diff-scoped reviewer cannot see mechanisms 1 and 3, so round one is routinely spent on
findings a repository-scoped pass gets for nothing. Before pushing, run a pass framed as
*"find every place this repository now contradicts itself"* rather than *"review this
diff"* — `/code-review` at high effort, or an equivalent — and complete the sweep above.
Every finding caught here is a round not spent.

## Model choice

The binding constraint on a shape finding is holding the whole corpus — every `SKILL.md`
and `NOTES.md` at once — in view while reasoning about consequences, not the edit itself.

- **local** findings: any capable model; the work is the sweep, not the reasoning.
- **rule** and **shape** findings: the strongest model available, at high effort. This is
  also what `backlog-orchestrator`, *Repair escalates on evidence, not on exhaustion*,
  already triggers on — "a finding on a locus an earlier repair on this PR already wrote ...
  the signal that the previous repair was shallow and the root was never understood." In a
  prose contract that signal fires often, which is why this repository's
  `repair-model-escalations` is set above the default.

Two caveats. A stronger model cannot find a contradiction in a document it was not given —
process precedes model. And the strongest current models are prompt-sensitive in the
opposite direction from older ones: prompts written for earlier models are often *too*
prescriptive and reduce quality. Give the whole task spec up front — the full file set, the
finding, and the completion criterion — rather than a micro-managed step list.

## Automating rounds on this repository

The skills here can drive their own repository's PRs, with three known mismatches.

**1. The review budget.** `review-repair-cycles` bounds unattended review rounds per PR.
Its built-in default — stated in `backlog-orchestrator`'s own defaults list, and not
repeated here — is far below the observed round count for documentation changes. Exhaustion degrades safely rather than failing — rounds past the cap return as
deferred-repair `NEEDS_USER` **items** under a `NO_CODE_CHANGE` round, holding that PR's
merge gate and reaching the owner at settle, never as a `NEEDS_USER` outcome for the PR. So
the symptom is a stall that hands you the work, not a crash. This repository raises the key
in `.claude/backlog-orchestrator.json`.

**2. `resolve-pr-comment` is line-local by contract.** Its gather step reads "the referenced
files at the relevant lines to understand what each comment is asking for." That is
precisely the fix shape that spawns the next round here, and no budget increase changes it.
`CLAUDE.md`'s completion criterion is the counterweight, and the skill is told to read
`CLAUDE.md` — but state the criterion in the invocation too where you can.

**3. `auto-merge` is enabled here, so the gate is reachable.** For a documentation PR the
exposure is not a stalled run: it is a locally-correct fix passing a green gate while
contradicting a document the reviewer did not happen to re-check that round. The
deterministic checks cannot catch a semantic contradiction, and the evals that could are out
of CI. `CLAUDE.md` states when to narrow the key for a run; what makes narrowing the only
available lever is the asymmetry the grant is built on — an invocation can close the gate
but never open it, because the repository's opt-in is the sole route to a merge.

**Why a run must not edit the contract it is executing.** Using `backlog-orchestrator` or
`implement-issue` to modify `backlog-orchestrator/SKILL.md` has the run rewriting its own
instructions mid-flight, and no contract here guards against it — the config file is read
once at preflight and never re-read precisely so a worker's write cannot change the running
policy, but nothing extends that protection to the contract text itself. `CLAUDE.md` carries
the rule this reasoning supports.
