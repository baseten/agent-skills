# CLAUDE.md — agent-skills

The `skills/*/SKILL.md` files in this repository are **prose contracts**, not code. They
are read and executed by models, they cross-reference each other, and several state the
same rule in more than one place on purpose. That changes what a correct fix looks like
here, and this file is the rule for it.

Reasoning lives in a skill's `NOTES.md`, keyed by its `SKILL.md` section names. Read a
section's note before changing its rules. `NOTES.md` explains; it never overrides. Most
skills have one; `resolve-pr-comment`, `draft-blog-post` and `draft-slack-message` do not,
so for those the commit message carries the reasoning instead.

**These rules are stated in this file and nowhere else.** `AGENTS.md`, `README.md` and
`docs/review-fix-workflow.md` point here or explain the reasoning behind what is here; none
of them states a rule of its own, and none should be read as qualifying one. That is this
file's own collapse rule applied to itself — three review rounds went by before it was.

## A rule change is not complete until its dependents agree

**The completion criterion for any change to a rule: no document in this repository
contradicts the changed rule.** Not "the flagged line now reads correctly" — that is the
code-shaped criterion, and it is what produces ten rounds of review here.

The reason is written into the repository's own history, in three places worth reading
before your first fix:

- `scripts/check_contract_placement.py` — on a rule that reads as correct where it sits and
  is inert where it is read;
- `skills/backlog-orchestrator/NOTES.md`, *Releasing a worker* — on how successive versions
  of one rule came to disagree, each by the fix for the last;
- `skills/backlog-orchestrator/NOTES.md`, *Blocked workers* — on the third of them, which
  the workflow document numbers and states.

`docs/review-fix-workflow.md` states all three in full, with the evidence.

`docs/review-fix-workflow.md` is the long form: the finding classification, the audit-table
method, and the sweep checklist. Follow it when resolving review rounds.

## Classify a finding before fixing it

Take **every** finding of a review round before editing anything, then classify each:

| kind | what it is | what to do |
| --- | --- | --- |
| **local** | wording, a typo, an unclear clause | fix in place, then sweep |
| **rule** | a rule is wrong, missing, or at the wrong decision point | fix the rule, then sweep |
| **shape** | one assumption that fails in several places; reported as several separate local findings | stop patching — walk the whole axis once |

On a **shape** finding, do not fix the instances. Enumerate the axis (every condition ×
every consumer) and answer one question per cell — *what supplies this here?* —
then fix the whole column in one pass. `docs/invariant-12-gate-audit.md` is the worked
example: seven review rounds produced thirteen findings, ten of them the same shape, and
one audit closed all three real defects at once.

## The consequence sweep

Before committing a rule change, find what it now contradicts:

1. `grep` **the whole repository** for every restatement of the rule, including
   paraphrases — `skills/` is not the boundary: `CLAUDE.md`, `AGENTS.md`, `README.md` and
   `docs/` state shared rules too, and a stale copy there contradicts the criterion above
   exactly as one in a `SKILL.md` does;
2. `grep` for every **cross-reference** into the section you changed, and check each still
   says something true;
3. find every rule written on the **negation** of a limitation you just introduced — these
   are the expensive ones, they sit sections away and read as reassurances;
4. check the rule is stated at the **decision point** that reads it, not merely present in
   the file;
5. where the rule produces something another skill must record, confirm every skill
   **between producer and recorder forwards it** — a chain that drops it silently is the
   defect class `check_contract_placement.py` was written for.

These five steps are the sweep. `docs/review-fix-workflow.md` expands each with its
reasoning and adds no step of its own.

**Prefer collapsing over reconciling — and know which restatements are legitimate.** Two
cases look alike and are not. A rule needed at two **decision points** belongs at both: that
is sweep step 4, and the repository's practice is to carry a pointer to the exception
alongside the absolute rather than let the two copies drift silently
(`backlog-orchestrator/NOTES.md`, *Remote worker session arguments*, on why `SKILL.md` line
198 carries one). A **summary** of a rule in a second document is the other case: it serves
no decision point of its own, it is where a condition gets quietly dropped, and it is what
collapsing is for — delete it, leave a pointer. So when a fix would make two summaries
agree, delete one instead; when it would make two decision points agree, keep both and
change them together. A local fix cannot contradict a distant copy that no longer exists,
which is what makes this the highest-leverage habit here.

**Leave a guard behind.** A finding shape that recurred should end the round with an
assertion in `scripts/check_contract_placement.py` or a scenario in the skill's
`evals/evals.json` — that is what stops a later round reintroducing it. `scripts/eval_reminder.sh`
flags a contract change whose evals did not move; it is advisory and needs someone to act
on it.

**Record the why.** Add the reasoning to the skill's `NOTES.md`, keyed by section, naming
the review round it came from. The existing entries do this; it is what stops the next
fixer re-breaking the fix. Where the skill has no `NOTES.md` (the three named at the top of
this file), put it in the commit message — do not create one as a side effect of an
unrelated fix.

## The sweep is scope clarification, not scope widening

`skills/repair-pr/SKILL.md` constrains a repair pass — *"make only the requested/in-scope
corrections"* (*Review repair*) and *"Never widen into other action points or findings the
caller did not supply"* (*Finding repair*). Those rules stand.

**They forbid taking on other findings. They do not license leaving the repository
self-contradictory.** Making the documents agree with the rule you just changed is part of
that one change — it is what "complete" means for a prose contract, per the criterion
above. Widening is picking up a second finding; sweeping is finishing the first.

Where a sweep genuinely cannot be completed inside the pass's scope, report the
contradiction with its location rather than committing a fix that creates it.

## Spend a free round before pushing

A diff-scoped reviewer cannot see a rule stated at the wrong decision point, or one written
on the negation of a limitation elsewhere, so its first round is routinely spent on findings
a repository-scoped pass gets for nothing. Before pushing a rule change, run a pass framed
as *"find every place this repository now contradicts itself"* rather than *"review this
diff"* — `/code-review` at high effort, or an equivalent — and complete the sweep.

## Match the model to the finding class

A **local** finding takes any capable model; the work is the sweep, not the reasoning. A
**rule** or **shape** finding takes the strongest model available, at high effort, because
the binding constraint is holding the whole corpus in view while reasoning about
consequences. Give it the whole task spec up front — the full file set, the finding, and the
completion criterion — rather than a micro-managed step list. Where a fixer runs under
`backlog-orchestrator`, the same escalation is already automatic on the strongest signal
that a previous repair was shallow; this repository raises `repair-model-escalations` for it.

## Checks

Every check is deterministic and runnable locally. Run them before committing:

```bash
python3 scripts/check_skills.py
python3 scripts/check_permissions.py
python3 scripts/check_contract_placement.py
python3 scripts/test_rule_locality.py
python3 scripts/check_rule_locality.py
bash skills/backlog-orchestrator/scripts/test-checkpoint-capture.sh
shellcheck --severity=warning bootstrap.sh skills/*/scripts/*.sh
bash scripts/eval_reminder.sh origin/main
```

The eval scenarios are not among them, and `README.md`, *Checks*, gives the reasons. The
consequence for a fixer is what matters here: on a documentation change these deterministic
checks are nearly the whole safety net, so the sweep is not optional diligence — it is the
missing test.

## Using this repository's own automation on this repository

The skills in `skills/` can be run against this repository, but three mismatches are known
and none of them announces itself. See `docs/review-fix-workflow.md`, *Automating rounds on
this repository*, for the full reasoning.

- **`resolve-pr-comment` is line-local by contract** — it reads "the referenced files at the
  relevant lines". That is the fix shape that spawns the next round here. Give it the
  completion criterion and the sweep above explicitly, or expect local fixes.
- **`auto-merge` is enabled for this repository**, so the merge gate is reachable. The risk
  on a documentation PR is not a stalled run but a locally-correct fix merging while
  contradicting a document the reviewer did not re-check that round. Narrow it per run
  (an invocation can switch `auto-merge` off, never on) when a change touches shared rules.
- **A run editing the contract it is executing.** Using `backlog-orchestrator` or
  `implement-issue` to change `backlog-orchestrator/SKILL.md` means the run is rewriting
  its own instructions mid-flight. Nothing in the contracts guards this. Make such changes
  in an ordinary session.

**Repair budgets are policy and live in `.claude/backlog-orchestrator.json`, never here.**
`skills/backlog-orchestrator/SKILL.md`, *Per-repository policy configuration*, is explicit
that policy which can authorize merges must be a config file and not prose, because prose
gets interpreted. This file therefore names no budget values — read them from the config.
