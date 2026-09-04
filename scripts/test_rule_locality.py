#!/usr/bin/env python3
"""Fixtures for check_rule_locality.py's directive detector.

Run from the repository root:

    python3 scripts/test_rule_locality.py

Why this file exists, stated plainly because it is the more useful lesson: the
detector shipped green over a live violation. It required a `**` lead-in, so a
plain sentence ("Take every finding of the round first.") and a table cell
("| **local** | ... | fix in place |") both bypassed CI while the claim the
check exists to defend was false. A check that passes on the current tree is
not evidence that it would catch the defect — and a green check over a false
claim is worse than no check, because it stops anyone looking.

So coverage is asserted here rather than asserted by whoever wrote the regex.
BAD holds every construction a real violation of the locality rule has taken in
this repository, each with the round that produced it; GOOD holds the reasoning
prose that must keep passing, because a detector that fires on explanation makes
the pointer files unwritable and will be switched off.

Adding to BAD when a new bypass is found is the maintenance this check needs;
finding one means the detector was wrong, not that the fixture is.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from check_rule_locality import is_directive  # noqa: E402

# (label, previous line, line) — every known violation, by the round that found it.
BAD: list[tuple[str, str, str]] = [
    ("r1 sweep-step noun lead-in", "", "- [ ] **Restatements.** `grep` for the rule across `skills/`"),
    ("r3 collapse rule", "", "**Collapse over reconcile.** Given the choice between two copies"),
    ("r3 guard obligation", "", "**Leave a guard.** Every shape that recurred should end its round"),
    ("r3 record-the-why", "", "**Record the why, naming the round.** The existing entries cite"),
    ("r3 leading conjunction", "", "**And do not let a run edit the contract it is executing.** Using"),
    ("r4 axis-walk step", "", "1. **Name the axis.** Usually a rule crossed with its consumers"),
    ("r4 pre-flight imperative", "", "**Run a pass framed as finding contradictions** before pushing"),
    ("r5 plain sentence", "", "Take every finding of the round first. Fixing them one at a time"),
    ("r5 table cell", "| --- | --- |", "| **local** | wording, a typo | fix in place, sweep, done |"),
    ("r5 table cell, later column", "| --- | --- |", "| **shape** | one assumption failing | walk the axis once |"),
    ("hypothetical: bare imperative", "", "Read a section's note before changing its rules."),
    ("hypothetical: never-form", "", "Never restate a rule in this file."),
]

# Reasoning prose that must not trip the detector.
GOOD: list[tuple[str, str, str]] = [
    ("why-framed lead-in", "", "**Why collapsing beats reconciling.** Restatement is mechanism 2's fuel"),
    ("mechanism heading", "", "**1. Presence in a file is not presence at the decision point.**"),
    ("wrapped continuation", "an invocation can close the gate", "but never open it, because the opt-in is the sole route"),
    ("quoted evidence", "", "> Take every finding of the round first."),
    ("descriptive table row", "| --- | --- |", "| **local** | wording, a typo; no rule changes | one round |"),
    ("separator row", "| kind | why |", "| --- | --- |"),
    ("plain explanation", "", "A diff-scoped reviewer cannot report a shape; it sees N local defects."),
    ("mid-paragraph mention", "The rule is stated once.", "Keeping two copies is what round one got wrong."),
]

failures: list[str] = []

for label, prev, line in BAD:
    if not is_directive(line, prev):
        failures.append(f"MISSED a known violation ({label}): {line[:60]!r}")
    else:
        print(f"PASS caught {label}")

for label, prev, line in GOOD:
    why = is_directive(line, prev)
    if why:
        failures.append(f"FALSE POSITIVE on reasoning prose ({label}, {why}): {line[:60]!r}")
    else:
        print(f"PASS allowed {label}")

print()
total = len(BAD) + len(GOOD)
for f in failures:
    print(f"FAIL {f}")
print(f"{total - len(failures)}/{total} passing")
sys.exit(1 if failures else 0)
