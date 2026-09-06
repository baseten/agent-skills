#!/usr/bin/env python3
"""Fixtures for check_contract_placement.py's sentence-scoped detector.

Run from the repository root:

    python3 scripts/test_contract_placement.py

`names_all_three_findings` enforces the one convention that keeps the two
dependency skills' eval oracles from re-stating the contradiction this PR spent
four rounds on: **an oracle states the two rules as two, and never names
licence, cooldown and peer in one sentence.** Licence and cooldown are per
package; the peer finding is a relation over the whole target tuple.

Why the fixtures exist is the same lesson `test_rule_locality.py` records, and
it recurred here twice. Round 26: the split treated `;` and `:` as sentence
boundaries, so a run-on stating per-package peer reuse in one breath read as
two compliant sentences. Round 27, on the narrowed split: an abbreviation did
the same job, because `e.g. ` is a terminator with no sentence after it. Both
times the corpus guard was green over the construction it exists to reject,
which is the whole argument for this file — a check that passes on the current
tree is no evidence it would catch the defect.

The fix for the second was to require a sentence *start* rather than to
enumerate abbreviations, so BAD carries a version number alongside `e.g.` and
`i.e.`: the class is "a terminator with nothing starting after it", and an
abbreviation list would have missed the version. GOOD carries the mirror cases
— a version number that really is followed by a sentence, and a sentence
starting with markup — because the boundary test has to admit those.

So the split is asserted here rather than asserted by whoever wrote the regex.
BAD holds every construction that must fire, each labelled with the round that
produced it; GOOD holds the oracle prose that must keep passing, because a
detector that rejects a correct oracle gets switched off — that is how the two
detectors this one replaced were lost.

Finding a construction BAD misses means the detector was wrong, not the fixture.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from check_contract_placement import names_all_three_findings  # noqa: E402

# Must fire. Clause punctuation joins a sentence; it does not end one.
BAD: list[tuple[str, str]] = [
    (
        "r26 semicolon join",
        "Per package, reuse licence and cooldown; under that same rule, reuse peer too.",
    ),
    (
        "r26 colon join",
        "Reuse is per package: licence, cooldown and peer all survive where "
        "that package's own target is unchanged.",
    ),
    (
        "r26 dash join",
        "Licence and cooldown are reusable per package — and so is the peer clearance.",
    ),
    (
        "r25 plain listing",
        "Compare each package's current target and reuse its licence, cooldown "
        "and peer findings where the target is the one triage measured.",
    ),
    (
        # Correct in content, rejected as a shape — this is the run-on round 26
        # split into three sentences in eval 14. The convention is deliberately
        # blind to whether the sentence gets the rules right, because deciding
        # that is the parsing problem two deleted detectors failed at.
        "r26 the run-on this round split",
        "Everything else is void: the companion's licence and cooldown, because "
        "its target moved; and the peer clearance for the whole group.",
    ),
    (
        "r26 wrapped across lines",
        "Reuse licence and cooldown per package,\nand reuse peer on the same terms.",
    ),
    (
        "r27 abbreviation before the peer clause",
        "Reuse licence and cooldown for e.g. unchanged targets, and reuse peer "
        "under the same rule.",
    ),
    (
        "r27 the other abbreviation",
        "Reuse licence and cooldown per package, i.e. where the target is "
        "unchanged, and reuse peer too.",
    ),
    (
        # Not an abbreviation but the same class: a terminator with no sentence
        # after it. Enumerating abbreviations would have missed this one.
        "r27 version number mid-sentence",
        "Reuse the licence and cooldown measured at v2.9.0 and the peer "
        "clearance with them.",
    ),
]

# Oracle prose that must not trip the detector.
GOOD: list[tuple[str, str]] = [
    (
        "eval 14, the two rules stated as two",
        "The companion's licence and cooldown go, because its target moved. So "
        "does the peer clearance for the **whole** group, framework included, "
        "because a peer range is a relation between packages.",
    ),
    (
        "the per-package pair alone",
        "Framework's licence and cooldown stay valid — its own target did not "
        "move — and they are not enough to continue on.",
    ),
    (
        "the peer finding alone",
        "The peer clearance for the whole group is void, because a peer range "
        "is a relation between packages rather than a property of one.",
    ),
    (
        "the contrast across a sentence boundary",
        "Licence and cooldown are measured per package. Peer resolution is a "
        "relation over the tuple, so any member moving voids it task-wide.",
    ),
    (
        # The pair with "r26 wrapped across lines": a wrap is not a boundary,
        # the terminator is, and a wrap after one does not undo it.
        "a wrap after a terminator is still a boundary",
        "Licence and cooldown are per package.\n\nThe peer finding is not.",
    ),
    (
        "one finding named twice in a sentence",
        "A licence finding stays a licence finding; nothing about it depends on "
        "another package's target.",
    ),
    (
        # Round 27's boundary test needs a sentence START, so a terminator
        # inside a version string must still end a sentence when a real one
        # follows it. The pair to "r27 version number mid-sentence".
        "a version number does not swallow the next sentence",
        "Licence and cooldown were measured at v2.9.0. Peer resolution is a "
        "relation over the tuple, so it is not measured per package at all.",
    ),
    (
        # Markdown and code spans start sentences too. Requiring an uppercase
        # letter rather than "not a continuation" would false-fire on both.
        "a sentence starting with markup",
        "Licence and cooldown are per package. **Peer** is a relation over the "
        "tuple, and `peer_ranges` is where that shows up.",
    ),
]

failures: list[str] = []

for label, text in BAD:
    if not names_all_three_findings(text):
        failures.append(f"MISSED a construction that must fire ({label}): {text[:60]!r}")
    else:
        print(f"PASS caught {label}")

for label, text in GOOD:
    if names_all_three_findings(text):
        failures.append(f"FALSE POSITIVE on compliant oracle prose ({label}): {text[:60]!r}")
    else:
        print(f"PASS allowed {label}")

print()
total = len(BAD) + len(GOOD)
for f in failures:
    print(f"FAIL {f}")
print(f"{total - len(failures)}/{total} passing")
sys.exit(1 if failures else 0)
