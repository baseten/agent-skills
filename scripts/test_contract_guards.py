#!/usr/bin/env python3
"""Mutation fixtures for check_contract_placement.py's corpus assertions.

Run from the repository root:

    python3 scripts/test_contract_guards.py

**Why this file exists, stated plainly because it is the whole lesson of the
review series that produced it.** Four consecutive rounds on one pull request
ended with an assertion that was green over the exact defect it was written
for, and each round fixed only the instance it was shown:

* round 29 wrote a guard listing the three obligations it had found, so the
  fourth was pinned *out* by the fix for it;
* round 30 rescoped five whole-file checks and declared the class closed;
* round 31 found three more, rescoped them, and left a sixth four lines away —
  a check whose name asserts three things it never looked at;
* round 32 found that one, plus a clause relabelled "the property" that a new
  bullet passed straight through.

Every one of those was found in seconds by mutating the rule and re-running the
check. `NOTES.md` had said so since round twelve — *"mutate the rule the guard
protects and watch the guard fail; testing the direction you are already
confident in proves nothing"* — as **advice**, in a repository whose own tier
list says advice reaches an agent only if something makes it read the file.

So it is a script. A guard that cannot fail is not a guard, and the only way to
know is to break the rule and watch.

**Adding to this file is the maintenance the check suite needs.** A new corpus
assertion owes a mutation here: the smallest edit to the contract that makes
the rule it protects false. If you cannot write one, the assertion is not
testing what its name says.
"""

from __future__ import annotations

import ast
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
UD = "skills/upgrade-major-dependency/SKILL.md"
DU = "skills/dependency-upgrade-orchestrator/SKILL.md"
UD_EVALS = "skills/upgrade-major-dependency/evals/evals.json"
DU_EVALS = "skills/dependency-upgrade-orchestrator/evals/evals.json"

# The replacement `MOVE_TO_END` deletes the text where it stands and appends it
# unchanged to the end of the file. A deletion tests that a rule is PRESENT; a
# relocation tests that it is present WHERE IT IS READ, which is what most of
# these assertions are actually about and what a deletion cannot distinguish.
# Round 33 measured this: with every `near()` reverted to a whole-file grep,
# 21 of 23 deletions still went red, so they were not exercising the scoping
# that three rounds of work had been about.
MOVE_TO_END = "<<MOVE_TO_END>>"

# (label, file, text to replace, replacement, assertion that must go red).
# Each entry is a real defect this repository has had, or the smallest edit
# that reintroduces the rule an assertion protects. The round that produced it
# is in the label, because a fixture without its provenance reads as a
# preference rather than as evidence.
MUTATIONS: list[tuple[str, str, str, str, str]] = [
    # --- the routine batch runs no named contract (rounds 29-32) ---
    ("r32 a fifth obligation with no disposition", DU,
     "\n\nSupply each agent with the completed triage",
     "\n- **Check whether any batched package is subject to a repository dependency policy.** Policies exist.\n\nSupply each agent with the completed triage",
     "the routine batch is given the obligations it cannot inherit"),
    ("r31 the adopted-PR bullet loses its disposition", DU,
     "verify against the installed version and report it", "carry on regardless",
     "the routine batch is given the obligations it cannot inherit"),
    ("r31 the base commit becomes a bare value", DU,
     "with both qualifiers that make it safe", "as a plain value",
     "the routine batch is given the obligations it cannot inherit"),
    ("r30 the target obligation loses its disposition", DU,
     "is not this agent's to re-triage or re-route", "can be handled locally",
     "the routine batch is given the obligations it cannot inherit"),
    ("r30 the in-flight bullet loses its bot-PR exception", DU,
     "**An automated bump PR for a batched package is not that**", "Anything open counts",
     "the routine batch is given the obligations it cannot inherit"),
    ("r33 the target bullet loses its blast-radius clause", DU,
     "the rest of the batch is not void with it", "the batch is void with it",
     "the routine batch is given the obligations it cannot inherit"),
    ("r33 the adopted-PR bullet loses the superseded disposition", DU,
     "take the successor on the same terms", "ignore the successor",
     "the routine batch is given the obligations it cannot inherit"),

    # --- a check carried to an actor that exists (rounds 3-5, 29-31) ---
    ("r30 Supervise loses the carried checks", DU,
     "- **Compare each open PR's recorded lockfile base against the current base**",
     "- (removed)",
     "the routine-target check is carried to actors that exist, not held at the merge"),
    ("r29 the ownerless merge moment returns", DU,
     "**A routine clearance is about one release, so the batch re-checks every candidate's target — and this run re-checks it again, because neither of them occupies the moment that decides it.**",
     "**A routine clearance is about one release, so re-check every batched candidate's target immediately before that task lands.**",
     "the routine-target check is carried to actors that exist, not held at the merge"),
    ("r32 Close out stops handing the lockfile check to the merger", DU,
     ", and **per open PR, whether its lockfile is still resolved against the current base**, plus **whether any batched candidate's target moved since it was cleared** — naming both checks as the merger's to repeat, since this run merges nothing.",
     ", and **whether any batched candidate's target moved since it was cleared**.",
     "close-out reports per-PR lockfile staleness to the merger"),

    # --- every report obligation stated where the report is written (r3, 29-32) ---
    ("r30 the disagreement obligation is dropped from Report", UD,
     "- any **disagreement** between a supplied verdict and what this task re-derived", "- any nothing at all",
     "every report obligation is stated where the report is written"),
    ("r30 the base commit's qualifiers are dropped when restated", UD,
     "that **the re-resolution must be repeated if the base has moved since**, and that it is a **handoff result and never a merge-time one**",
     "the base value",
     "every report obligation is stated where the report is written"),
    ("r31 the docs-divergence obligation is dropped from Report", UD,
     "and any divergence between a rendered docs page and the published artifact (see Research);", "",
     "every report obligation is stated where the report is written"),
    ("r32 the docs-divergence rule is deleted from Research", UD,
     "**Where the two do diverge, the artifact wins and the divergence is reported**", "**Note.**",
     "a docs/artifact divergence is reported, at both places research happens"),
    ("r32 the orchestrator's triage loses the divergence disposition", DU,
     "the divergence is reported rather than silently resolved", "the artifact is used",
     "a docs/artifact divergence is reported, at both places research happens"),
    ("r29 the sentence stating WHY Report restates is deleted", UD,
     "this is the section an agent writes the report from", "this section matters",
     "every report obligation is stated where the report is written"),

    # --- the moved-target stop and its return (rounds 19-21, 29-30) ---
    ("r29 Task's enumeration drops the incompatible tuple", UD,
     "the recomputed set, and, where a peer range is what moved, **the incompatible tuple** that voids the clearance",
     "the recomputed set",
     "the return contract and its consumer agree on the incompatible tuple"),
    ("r29 the caller stops expecting the tuple", DU,
     "the incompatible tuple where a peer range is what moved,", "",
     "the return contract and its consumer agree on the incompatible tuple"),
    ("r29 the adopted PR is no longer left open on a stop", UD,
     "**A task ended by a moved target leaves every adopted PR open**", "**Unrelated sentence**",
     "a moved-target stop leaves every adopted PR open, stated beside the rule it disclaims"),
    ("r33 superseded PRs are closed at branch setup again", UD,
     "**Superseding does not close anything yet.**", "Close each now.",
     "superseding is a closure at the end, not at branch setup"),
    ("r33 the arity paragraph is relocated out of the worktree cases", UD,
     "**Adopt exactly one as the branch — the member with the most of the migration already in it — and supersede the rest**",
     MOVE_TO_END,
     "the adopted-PR arity is stated, with the two rules that read over all of them"),
    ("r33 the carried checks are relocated out of Supervise", DU,
     "- **Compare each open PR's recorded lockfile base against the current base**, and name every PR whose lockfile has gone stale.",
     MOVE_TO_END,
     "the routine-target check is carried to actors that exist, not held at the merge"),
    ("r33 the Report obligations are relocated out of Report", UD,
     "- any **disagreement** between a supplied verdict and what this task re-derived, rather than silently taking either answer (see Task), and any divergence between a rendered docs page and the published artifact (see Research);",
     MOVE_TO_END,
     "every report obligation is stated where the report is written"),
    ("r32 the arity rule's report obligation is dropped", UD,
     "**every adopted PR's URL, not only the one adopted as the branch**", "a mapping",
     "every report obligation is stated where the report is written"),
    ("r33 the batch route forgets coupled siblings", DU,
     "**Every removal below therefore removes a coupled group, never a member of one**",
     "Removals are per candidate",
     "the batch route removes coupled groups rather than members of them"),
    ("r29 Research resumes a task the gate ended", UD,
     "**That case does not resume here.**", "Re-read the range and continue.",
     "the research phase does not resume a task the gate ended"),

    # --- placement, where the whole content of the rule is where it sits ---
    ("r31 the description's routine-bump path moves into the body", DU,
     "plus one batched task for the routine bumps triage cleared, which need no migration workflow.",
     "and other work.",
     "the orchestrator's description names the routine-bump path"),
    ("r31 the baseline rule is deleted from the phase that performs it", UD,
     "**An adopted bump PR's head is never the baseline.** It already carries the bump, so tests written and proven green there are post-migration tests wearing this phase's name",
     "**Note.** The head carries the bump",
     "the characterization baseline excludes an adopted PR's head"),
    ("r29 Close out stops reporting the clearances Dispatch requires", DU,
     "**which routine candidates were cleared and on what evidence** (see Dispatch", "nothing at all (see Dispatch",
     "close-out carries the clearance report dispatch requires of it"),

    # --- the moved-target rule and its consumers (rounds 15-21), never
    # --- mutated until round 33 measured the battery's own coverage ---
    ("r21 the stop becomes conditional on a changed set again", DU,
     "**reports and stops rather than reshaping its own task** — on the move itself, whether or not the set came out different (below)",
     "and, finding it different, **reports and stops rather than reshaping its own task**",
     "the producer expects that report and owns membership"),
    ("r21 the caller stops expecting an unconditional stop", DU,
     "**Expect that stop on any moved target, not only a changed set", "**Expect that stop when the set changes",
     "the producer expects the stop on any moved target, not just a changed set"),
    ("r19 the peer clearance survives another member's move", UD,
     "dies as soon as **any** member's target moves", "dies when its own package's target moves",
     "the peer-cap gate item says a supplied clearance dies group-wide"),
    ("r18 the target rule stops reaching research and the audit", UD,
     "licence, install cooldown, breaking-change research and usage audit", "licence and install cooldown",
     "the target rule reaches the research and the audit, not just the gate"),
    ("r21 the re-reading becomes a continuation again", UD,
     "The re-reading serves the report, not the continuation.", "Then continue.",
     "the re-reading serves the report, not the continuation"),
    ("r15 the return mapping collapses to one figure", UD,
     "package → current target mapping for every package that moved**, the refreshed failure-mode reading",
     "current target**, the refreshed failure-mode reading",
     "Report hands back a per-package mapping, symmetric with dispatch"),
    ("r16 dispatch stops forwarding the per-package target", DU,
     "**the viability verdict, the exact target version it measured for every package in the task, and the coupled set**",
     "**the viability verdict and the coupled set**",
     "dependency dispatch forwards the verdict, a per-package target, and the coupled set"),
    ("r1 the gate stops exempting an automated bump PR", UD,
     "**An automated bump PR for these same packages is not that**", "Any open PR counts",
     "its in-flight item exempts an automated bump PR at the item itself"),
    ("r1 triage stops exempting an automated bump PR", DU,
     "**An automated bump PR for a candidate is never work already in flight — it is the work.**",
     "An open PR removes a candidate.",
     "an automated bump PR is the work, not work already in flight"),
    ("r19 peer caps resolve against installed versions again", UD,
     "resolving every cap against the group's **target** versions and not their installed ones",
     "resolving every cap against the installed versions",
     "its peer-cap item resolves caps against the group's targets"),
    ("r20 the adopted PR's state is taken from the verdict again", UD,
     "read the PR itself before branching from it", "trust the verdict's description of it",
     "the adopted PR's state is refreshed, not taken from the verdict"),
    ("r3 the lockfile is settled by hand", UD,
     "never by hand", "carefully by hand",
     "the worker re-resolves the lockfile and never by hand"),
    ("r22 the PR-body record leaves the section that writes the report", UD,
     "the base commit the lockfile was resolved against (see Migration and verification",
     "the base (see Migration and verification",
     "the PR-body record is stated where the report is written, not only where it is produced"),
    ("r23 the target mapping stops covering every coupled member", DU,
     "Forward a **package → triaged target** mapping covering every member", "Forward the task's target",
     "the target mapping covers every coupled member"),
    ("r24 the worker is scoped by version distance again", UD,
     "The version distance does not decide whether this skill applies; **unruled-out risk of a breaking change does**",
     "This skill applies to majors",
     "the worker states the same scope test itself"),
    ("r24 dispatch scopes the worker by version distance again", DU,
     "whose triage did **not** clear it of breaking changes", "that is a major",
     "dispatch scopes the worker by unruled-out risk, not version distance"),
    ("r24 cleared routine bumps get one agent each", DU,
     "**Routine bumps do not each get one.**", "Routine bumps get one each.",
     "cleared routine bumps are batched rather than dispatched each"),
    ("r21 the coupled set is claimed to survive a move", UD,
     "relations over the targets rather than properties of one", "properties of one package",
     "peer resolution and the coupled set are voided task-wide"),
    ("r29 the non-adopted branch stops being the baseline", UD,
     "the upgrade branch is already the baseline — one worktree", "cut a second worktree for the baseline",
     "the non-adopted branch is still eligible as the baseline"),
]

# Mutations against the eval corpus, which is a restatement of the contract and
# goes stale with it. Three contract sweeps on one PR left it behind.
EVAL_MUTATIONS: list[tuple[str, str, str, str, str]] = [
    ("r30 an expected answer teaches the deleted peer re-run", DU_EVALS,
     "and the agent does not re-run it and carry on", "and it is re-run over the tuple, so",
     "no expected answer or assertion teaches a formulation the contract removed"),
    ("r31 an assertion grades a count of obligations", DU_EVALS,
     "The answer states each obligation in the brief rather than cross-referencing it",
     "The answer states all four obligations in the brief rather than cross-referencing them",
     "the routine-brief eval grades obligations rather than a count of them"),
]


def run_check(tree: pathlib.Path) -> set[str]:
    """Assertion names that FAILED, running the checker against `tree`.

    A crash is not a failure: the checker dying (a moved anchor inside one of
    its own helpers, say) produces no FAIL lines, and reading stdout alone
    would report every mutation as green over its own defect while printing a
    baseline PASS. Round 33 reproduced that. So the exit code is checked.
    """
    proc = subprocess.run(
        [sys.executable, str(tree / "scripts" / "check_contract_placement.py")],
        capture_output=True, text=True)
    if proc.returncode not in (0, 1):
        raise SystemExit(
            "the checker crashed rather than reporting failures "
            f"(exit {proc.returncode}):\n{proc.stderr.strip()[:2000]}")
    return {m.group(1) for m in re.finditer(r"^FAIL (.+)$", proc.stdout, re.M)}


# Assertions deliberately without a mutation, each with the reason. An entry
# here is a claim that breaking the rule is not expressible as a text edit to
# the two contracts — not that nobody got round to it. Keep it short; a long
# exemption list is this file failing quietly.
UNMUTATED_BY_DESIGN: dict[str, str] = {}


def _assertion_names(src: str) -> set[str]:
    """Every assertion label in the checker, by parsing rather than grepping.

    A regex over `("...",` also matches the phrase tuples the checker uses as
    fixtures, which inflates the gap and makes the coverage line a number
    nobody can act on — the exact species of false reassurance this file
    exists to remove, committed inside the thing that measures it. So the
    module is parsed and only the first element of each 2-tuple appended to a
    list named `checks` is taken.
    """
    names: set[str] = set()
    for node in ast.walk(ast.parse(src)):
        # Both forms: `checks = [...]` and `checks: list[...] = [...]`. The
        # first version of this handled only ast.Assign and found nothing,
        # which surfaced as every mutation naming a missing assertion — loudly,
        # which is the behaviour to keep.
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign):
            targets, value = [node.target], node.value
        else:
            continue
        if not isinstance(value, ast.List):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "checks" for t in targets):
            continue
        for elt in value.elts:
            if (isinstance(elt, ast.Tuple) and len(elt.elts) == 2
                    and isinstance(elt.elts[0], ast.Constant)
                    and isinstance(elt.elts[0].value, str)):
                names.add(elt.elts[0].value)
    return names


def coverage_gap(tree: pathlib.Path) -> list[str]:
    """Assertion names in the checker with neither a mutation nor an exemption.

    This is the property the fixture list cannot supply. Round 32 built the
    battery and round 33 measured it: 138 of 151 assertions had no mutation,
    including round 32's own headline one, which turned out to be four
    whole-file greps that a relocation walked straight through. A battery that
    cannot tell you it is short reads as complete for exactly as long as nobody
    checks — which is the defect this whole file exists to end, one level up.

    Reported, not enforced, and the distinction is deliberate: failing the
    build on an uncovered assertion would push the next person to write a
    mutation that passes rather than one that breaks the rule. It prints, it
    ranks, and `NAMED_BELOW` is what closes the gap.
    """
    src = (tree / "scripts" / "check_contract_placement.py").read_text(encoding="utf-8")
    names = _assertion_names(src)
    covered = {expected for *_, expected in MUTATIONS + EVAL_MUTATIONS}
    unknown = covered - names
    if unknown:
        return [f"mutation names an assertion that no longer exists: {sorted(unknown)}"]
    return sorted(names - covered - set(UNMUTATED_BY_DESIGN))


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tree = pathlib.Path(tmp) / "repo"
        tree.mkdir()
        for d in ("scripts", "skills"):
            shutil.copytree(ROOT / d, tree / d,
                            ignore=shutil.ignore_patterns("__pycache__"))

        baseline = run_check(tree)
        if baseline:
            print(f"FAIL the unmutated tree is already red: {sorted(baseline)}")
            return 1
        print("PASS baseline: the unmutated tree is green")

        for label, rel, old, new, expected in MUTATIONS + EVAL_MUTATIONS:
            f = tree / rel
            pristine = f.read_text(encoding="utf-8")
            n = pristine.count(old)
            if n != 1:
                failures.append(
                    f"fixture ({label}) no longer applies: its anchor matches {n} times in {rel}. "
                    "The contract moved; re-anchor the mutation rather than deleting it.")
                continue
            if new == MOVE_TO_END:
                mutated = pristine.replace(old, "") + "\n\n" + old + "\n"
            else:
                mutated = pristine.replace(old, new)
            f.write_text(mutated, encoding="utf-8")
            red = run_check(tree)
            f.write_text(pristine, encoding="utf-8")
            if expected in red:
                print(f"PASS {label}")
            elif red:
                failures.append(
                    f"WRONG GUARD ({label}): expected {expected!r} to go red, got {sorted(red)}")
            else:
                failures.append(
                    f"GREEN OVER ITS OWN DEFECT ({label}): {expected!r} passes with the rule broken")

        gap = coverage_gap(tree)
        if gap and gap[0].startswith("mutation names"):
            failures.append(gap[0])
            gap = []

    print()
    if gap:
        # Assertions and mutations are different units — several mutations can
        # exercise one assertion — so the first version of this line added them
        # together and printed a denominator that was not a count of anything.
        # A reassuring number that does not mean what it says is the failure
        # this file exists to catch, so it is spelled out.
        covered = len({expected for *_, expected in MUTATIONS + EVAL_MUTATIONS})
        print(f"COVERAGE {covered} of {covered + len(gap)} assertions have a mutation "
              f"({len(MUTATIONS) + len(EVAL_MUTATIONS)} mutations in total); "
              f"{len(gap)} have neither a mutation nor a stated exemption.")
        print("  A guard nobody has broken is a guard nobody has tested. The next few:")
        for name in gap[:8]:
            print(f"  - {name}")
        print()

    total = len(MUTATIONS) + len(EVAL_MUTATIONS) + 1
    for f in failures:
        print(f"FAIL {f}")
    print(f"{total - len(failures)}/{total} passing")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
