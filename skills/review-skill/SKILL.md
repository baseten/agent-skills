---
name: review-skill
description: Review a change to a prose contract — a SKILL.md, a rules/ entry, or the NOTES.md beside one — by checking what it now makes a reader decide, against the decision scenarios that pin it, in a review that terminates by contract. Use when asked to review a skill or rule change, to check whether an edit altered behaviour, or when an automated code reviewer is grinding rounds on a contract without converging. Do not select it merely because a PR touches skills/ — it replaces code review on a contract-only PR, and that substitution is the repository's to route.
---

# Review Skill

A `SKILL.md` is read and executed by a model. Reviewing one is not reviewing
code and not reviewing documentation: the question is neither *does it compile*
nor *is it true about the codebase*, but **does a reader reach a different
decision than before**.

That question has an oracle, which is what makes this reviewable at all. The
repository's `evals/evals.json` scenarios are decisions with assertions, and
`scripts/run_evals.py` runs the two-arm comparison `CLAUDE.md` specifies. A
finding that cannot be expressed as a scenario a reader fails is a finding this
skill does not make.

## Inputs

- the pull request, and the contract paths it changes;
- the base the arms are taken from — `origin/main` unless the caller names another;
- whether `skill-creator` is available (see *When to reach for a real task run*).

# 1. What this reviews, and what it replaces

**Scope is the contract paths**: `skills/*/SKILL.md`, `rules/*.md`, and the
`NOTES.md` beside them. Never the scripts, never the evals as code.

On a contract-only PR it **replaces** automated code review, which has no oracle
here and grinds. On a mixed PR it runs **alongside** one, over the contract paths
only — a contract that contradicts the script landing beside it is the finding a
diff-scoped reviewer misses.

# 2. Establish what changed for a reader

**Take the arms from git, never a copy in the tree.** `scripts/run_evals.py
prepare` materialises the base contract into a scratch directory and emits reader
packets carrying only the contract and the prompt. A reader that has seen
`expected_output` or the assertions is grading its own answer.

Run both arms over the scenarios that touch the changed sections. **The
information is entirely in the disagreement** — a single-arm run returns a clean
sweep and teaches nothing, which is the flattering direction this fails in.

`score` reports the rate per arm, then the disagreements, and marks an ungraded
scenario as **ungraded** rather than counting it either way
(`references/absence-is-not-a-verdict.md`).

# 3. What is a finding

Classify before reporting, using `CLAUDE.md`'s own definitions rather than
inventing a second set:

| kind | what it is |
|---|---|
| `LOCAL` | a clause that reads wrong, with a scenario that shows a reader taking it wrong |
| `RULE` | a rule wrong, missing, or **stated away from the decision point that reads it** |
| `SHAPE` | one assumption failing in several places, arriving as several findings |

**A `SHAPE` finding is never repaired instance by instance.** Enumerate the axis
— every condition × every consumer — answer *what supplies this here* per cell,
and report it as one finding with its loci. Reporting the instances separately is
how a reviewer manufactures four rounds out of one defect.

**Two more, and they are the ones with teeth:**

- `REGRESSION` — a scenario whose arms disagree in the wrong direction. The base
  contract got it right and the change gets it wrong. Always a finding, always
  with the scenario name and both answers.
- `UNPINNED` — changed behaviour with no scenario covering it. Not a defect in
  the change; a defect in the evidence. Report the scenario that should exist,
  because `bug → failing eval → repair` needs the eval to exist first.

**Not findings, at any round:** phrasing, ordering, terminology, and a section
that got better in a way nobody asked about.

# 4. The rounds

**The budget is `references/prose-review-round-budget.md`.** Apply it from there.

What that rule leaves to this skill is the name of its failure class: **the new
instance a fix may introduce is a `REGRESSION`** — a repair that moves a
scenario's answer the wrong way is the thing this reviewer exists to catch, and
it is reported inside the finding whose fix created it.

This skill's report carries no revision marker, so the rule's certification
clause does not bind it. A consumer establishes freshness from the review it
routed, not from this comment.

# 5. The report is one comment

```text
## Contract review — round <1|2> of 2

<N> scenarios run, both arms · <M> findings · <U> ungraded
Reviewed: <the contract paths>, base <commit>

### Disagreements
| scenario | base arm | changed arm | verdict |
|---|---|---|---|

### Findings
1. [REGRESSION] <scenario> — base answered <X>, change answers <Y> — <what to do>

### Notes
<non-actionable observations, or "None.">

Round 2 is the last round; unresolved findings after it go to the author.
```

**Ungraded scenarios are reported as a count, never folded into either arm.** A
review that ran twelve scenarios and graded nine has three unknowns, not nine
passes.

**The comment follows the authored-write-form rule**
(`references/authored-write-form.md`) and carries the attribution footer: that
rule's approval test answers No for every comment this skill writes. The
disagreement table and each finding's scenario name are the write's **required
contents** — a table cut to fit a word count is the review deleting its evidence.

# 6. When to reach for a real task run

`scripts/run_evals.py` grades answers to decision scenarios. It cannot tell you
whether a rewritten contract makes a model *behave* better, and for a large
meaning-preserving change that is the question.

**Where `skill-creator` is available, use it for that** — real task prompts, its
blind comparator judging two outputs without knowing which produced which, and
its analyzer explaining why the winner won. Its baseline for an existing skill is
the previous version, which is this comparison exactly.

**Capability-based, never silently skipped**: where it is unavailable, say so in
the report, fall back to the scenario corpus, and name what could not be run. An
absent tool that goes unmentioned is a review reporting more confidence than it
has.

# Enabling it in a repository

Inert until a repository routes contract review here, the same way `review-docs`
is. Routing is that repository's change to make, and until it does, this skill
runs only when a person asks for it by name.

# Boundaries

Read-only. It reports findings; it does not edit a contract, push, resolve a
thread, or merge. A finding needing intent or a product decision is reported for
a person, never guessed — a reviewer suggestion is not evidence that a change
improves the skill.

**Its findings travel the finding route, not the review one.** They are returned to the caller and carried into `summarize-tranche`, which classifies them as `IN_FLIGHT_FIX` / `MERGE_RISK` / `DECISION`; a repair reaches `repair-pr` as `repair type = finding`. They are never threads — the report is one comment per round — so `repair type = review`, which resolves a thread per finding, finds nothing to resolve.
