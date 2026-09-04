#!/usr/bin/env python3
"""Assert the workflow rules are stated in CLAUDE.md and nowhere else.

Run from the repository root:

    python3 scripts/check_rule_locality.py

`CLAUDE.md` declares that `AGENTS.md`, `README.md` and `docs/review-fix-workflow.md`
point at it or explain its reasoning, and that none of them states or qualifies a
rule of its own. That claim is load-bearing — it is the whole reason a fixer can
trust one file — and it was violated three review rounds running on the PR that
introduced it. Each round found one more directive that had been left behind, and
each fix was believed complete at the time.

Why a check rather than a fourth careful sweep: prose is the weakest tier in this
repository's own ladder, and a purity constraint over three documents is exactly
what a human sweep keeps failing at. This is the tier-1 guard that recurring shape
earned.

Two properties, both decidable from the text:

1. every canonical rule phrase appears in CLAUDE.md, and in none of the pointer
   files — so a rule cannot be silently restated or re-qualified elsewhere;
2. no pointer file issues a directive of its own, detected as an imperative verb
   opening a numbered step or a bold lead-in.

(2) is a heuristic and deliberately narrow: it fires only on the construction the
violations actually took — `1. **Name the axis.**`, `**Leave a guard.**` — and
never on prose. A rule that needs to be stated belongs in CLAUDE.md, so a hit
here is an instruction to move it, not to reword it.
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

CANONICAL = ROOT / "CLAUDE.md"

# Files that must only point or explain. README is checked whole: its other
# sections predate this rule and describe the repository rather than instruct a
# fixer, so the phrase test carries it and the directive test is scoped to the
# section that could restate a rule.
POINTERS = ["AGENTS.md", "docs/review-fix-workflow.md"]
README_SECTION = ("## Changing the skills", "## Checks")

# A rule is identified by a phrase distinctive enough that a restatement would
# have to reproduce it. Keep these short and verbatim from CLAUDE.md.
RULE_PHRASES = [
    "no document in this repository contradicts",
    "the whole repository",
    "delete it, leave a pointer",
    "assertion in `scripts/check_contract_placement.py`",
    "find every place this repository now contradicts itself",
    "the strongest model available",
    "in an ordinary session",
]

IMPERATIVES = (
    "read|run|add|check|find|grep|delete|keep|leave|record|collapse|prefer|make|use|"
    "name|build|answer|fix|walk|take|classify|state|move|point|spend|match|do not|never|always"
)
# Three constructions, because every narrower version of this shipped green over a
# violation. Requiring `**` missed a plain sentence ("Take every finding of the
# round first.") and a table cell ("| **local** | ... | fix in place |"), and
# requiring the verb first missed a leading conjunction ("**And do not let ...**").
_LEAD = rf"(?:(?:and|also|but|so|then)\s+)?(?:{IMPERATIVES})\b"
_MARKER = r"(?:\s*[-*]\s+|\s*\d+\.\s+|\s*-\s*\[[ x]\]\s+)?"

BOLD_DIRECTIVE = re.compile(rf"^{_MARKER}\*\*{_LEAD}", re.I)
PLAIN_DIRECTIVE = re.compile(rf"^{_MARKER}{_LEAD}", re.I)
CELL_DIRECTIVE = re.compile(rf"^\s*(?:\*\*)?{_LEAD}", re.I)

# Kept for the fixture test, which asserts every known violation is detected.
DIRECTIVE = BOLD_DIRECTIVE


def is_directive(line: str, prev: str = "") -> str | None:
    """Why this line is a directive, or None.

    `prev` is the preceding line, needed only for the plain-sentence test: a
    wrapped continuation ("... can close the gate / but never open it ...") is
    not a sentence-initial imperative, and testing it as one produced the single
    false positive this check has had.
    """
    if line.lstrip().startswith(">"):
        return None  # a quotation is evidence, not an instruction
    if BOLD_DIRECTIVE.match(line):
        return "bold lead-in"
    # A noun lead-in can carry the directive in its body: "**Restatements.**
    # `grep` for the rule across `skills/`". The verb is not first, and the
    # fixture test is what surfaced that the verb-first patterns miss it.
    body = re.sub(r"^\s*(?:[-*]\s+|\d+\.\s+|-\s*\[[ x]\]\s+)?\*\*[^*]+\*\*[.:]?\s*", "", line)
    if body != line and CELL_DIRECTIVE.match(body.lstrip("`")):
        return f"directive in the body of a noun lead-in {body[:32]!r}"
    if line.count("|") >= 2:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if any(set(c) <= set("- :") for c in cells):
            return None  # the header separator row
        for cell in cells:
            if cell and CELL_DIRECTIVE.match(cell):
                return f"table cell {cell[:32]!r}"
        return None
    starts_block = prev.strip() == "" or prev.lstrip().startswith("#")
    if starts_block and PLAIN_DIRECTIVE.match(line):
        return "sentence-initial imperative"
    return None

# Normative content that is a rule's substance rather than its verb. A pointer
# file naming the sweep's scope is restating the rule however it is phrased —
# this is what a noun lead-in ("**Restatements.** `grep` ... across `skills/`")
# hid from the verb test in round one.
FORBIDDEN_SCOPE = ["repository-wide", "across `skills/`", "whole repository"]

# AGENTS.md must not characterise how strongly CLAUDE.md states anything: in
# round three it turned "prefer collapsing" into a requirement, which would have
# licensed deleting legitimate decision-point restatements.
FORBIDDEN_IN_AGENTS = ["requires", "must ", "should ", "prefer"]

errors: list[str] = []
passes: list[str] = []


def flat(text: str) -> str:
    return " ".join(text.split())


def section(text: str, start: str, end: str) -> str:
    i = text.find(start)
    if i < 0:
        return ""
    j = text.find(end, i + len(start))
    return text[i : j if j > 0 else len(text)]


def main() -> int:
    canonical = CANONICAL.read_text()
    canonical_flat = flat(canonical)

    targets = {p: (ROOT / p).read_text() for p in POINTERS}
    readme = (ROOT / "README.md").read_text()
    targets["README.md"] = section(readme, *README_SECTION)
    if not targets["README.md"]:
        errors.append(
            f"README.md: section {README_SECTION[0]!r} not found — "
            "the locality check cannot see what it is meant to guard"
        )

    # 1. Each rule lives in CLAUDE.md, and only there.
    for phrase in RULE_PHRASES:
        if phrase not in canonical_flat:
            errors.append(
                f"CLAUDE.md: canonical rule phrase {phrase!r} is missing — "
                "either the rule moved out of the one file that may state it, "
                "or this check's phrase list is stale"
            )
            continue
        for name, text in targets.items():
            if phrase in flat(text):
                errors.append(
                    f"{name}: restates the rule {phrase!r}, which CLAUDE.md owns. "
                    "Point at CLAUDE.md's section instead of stating the rule here."
                )
        else:
            passes.append(f"rule stated only in CLAUDE.md: {phrase!r}")

    # 2. No pointer file issues a directive of its own.
    for name, text in targets.items():
        lines = text.split("\n")
        for n, line in enumerate(lines, 1):
            why = is_directive(line, lines[n - 2] if n > 1 else "")
            if why:
                errors.append(
                    f"{name}:{n}: directive ({why}) {line.strip()[:60]!r} — "
                    "a rule belongs in CLAUDE.md; keep the reasoning here and "
                    "rephrase this as a 'why', or move the rule."
                )
        for term in FORBIDDEN_SCOPE:
            if term in flat(text):
                errors.append(
                    f"{name}: names the sweep's scope ({term!r}), which CLAUDE.md owns. "
                    "Say why a narrower scope is wrong; do not restate the boundary."
                )
        passes.append(f"no directives or scope restatements in {name}")

    agents = flat((ROOT / "AGENTS.md").read_text()).lower()
    for term in FORBIDDEN_IN_AGENTS:
        if term in agents:
            errors.append(
                f"AGENTS.md: {term.strip()!r} characterises how strongly CLAUDE.md "
                "states a rule. It is a pointer: paraphrase and qualify nothing."
            )
    passes.append("AGENTS.md attributes no rule strength")

    for p in passes:
        print(f"PASS {p}")
    for e in errors:
        print(f"FAIL {e}")
    print(f"\n{len(passes)}/{len(passes) + len(errors)} passing")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
