#!/usr/bin/env python3
"""Fixtures for check_contract_placement.py's oracle guard.

Run from the repository root:

    python3 scripts/test_contract_placement.py

`names_all_three_findings` enforces the one convention that keeps the two
dependency skills' eval oracles from restating the contradiction this PR spent
five rounds on: **an oracle states the two rules as two, and never names
licence, cooldown and peer in one block.** Licence and cooldown are per
package; the peer finding is a relation over the whole target tuple. A block is
a paragraph or a list item — decided by layout, not by wording.

Why this file exists is the lesson `test_rule_locality.py` records, and it
recurred here three rounds running while the unit was a *sentence*:

* round 26 — the split treated `;` and `:` as boundaries, so a run-on
  conflating the two rules read as two compliant halves;
* round 27 — narrowed to `.!?`, an abbreviation did the same job at `e.g. `;
* round 28 — narrowed again to require a sentence *start*, markup after an
  abbreviation did it a third time (`e.g. **unchanged targets**`).

Each time the corpus guard was green over the construction it exists to reject.
The third is why the unit changed rather than the regex: markup must be able to
start a sentence and must not be able to fake one, and no character class does
both. BAD keeps all three escapes even though the block rule makes them
uninteresting — they are the evidence for the unit, and a future author tempted
back to sentence parsing should have to delete them deliberately.

The GOOD list is the half that needs defending. A detector that rejects a
correct oracle gets switched off, and that is exactly how the two detectors
this one replaced were lost.

Finding a construction BAD misses means the guard was wrong, not the fixture.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from check_contract_placement import names_all_three_findings  # noqa: E402

# Must fire: all three findings inside one paragraph or list item.
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
        # after it. An abbreviation list would have missed this one.
        "r27 version number mid-sentence",
        "Reuse the licence and cooldown measured at v2.9.0 and the peer "
        "clearance with them.",
    ),
    (
        # The one that ended sentence parsing: `*` had to count as a sentence
        # start for ordinary oracle prose, which let it fake one here.
        "r28 markup after an abbreviation",
        "Reuse licence and cooldown for e.g. **unchanged targets**, and reuse "
        "peer under the same rule.",
    ),
    (
        # NEW under the block rule, and the point of it: correct-reading prose
        # that still presents the two rules as one paragraph. This exact text
        # was a GOOD fixture one round ago. The rule is stricter on purpose,
        # and complying with it is mechanical — one of these goes in a bullet.
        "r28 two rules in one paragraph",
        "Licence and cooldown are measured per package. Peer resolution is a "
        "relation over the tuple, so any member moving voids it task-wide.",
    ),
    (
        "r28 a single list item carrying both rules",
        "- Reuse licence and cooldown per package, and re-run peer over the tuple.",
    ),
]

# Oracle prose that must not trip the guard.
GOOD: list[tuple[str, str]] = [
    (
        # The restructured eval 14. Also pins that the text is not flattened
        # first: collapse these into one block and the guard fires.
        "eval 14, the two rules stated as two list items",
        "Everything else is void:\n\n"
        "- The companion's licence and cooldown go, because its target moved.\n"
        "- So does the peer clearance for the **whole** group, framework "
        "included, because a peer range is a relation between packages.\n\n"
        "Then stop: a moved target puts membership back in the caller's hands.",
    ),
    (
        "the two rules as two paragraphs",
        "Licence and cooldown are measured per package.\n\nPeer resolution is "
        "a relation over the tuple, so any member moving voids it task-wide.",
    ),
    (
        "a paragraph and a bullet",
        "The targets serve two different rules.\n\n"
        "Licence and cooldown are compared per package.\n"
        "- The peer finding is re-run over the whole tuple.",
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
        # Markup starting a block is ordinary oracle prose. Requiring the guard
        # to tell this from "r28 markup after an abbreviation" is what the
        # sentence unit could not do.
        "a block starting with markup",
        "Licence and cooldown are per package.\n\n**Peer** is a relation over "
        "the tuple, and `peer_ranges` is where that shows up.",
    ),
    (
        "one finding named twice in a block",
        "A licence finding stays a licence finding; nothing about it depends on "
        "another package's target.",
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
