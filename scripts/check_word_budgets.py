#!/usr/bin/env python3
"""Hold every contract to a committed word budget, and let the budgets only fall.

Run from the repository root:

    python3 scripts/check_word_budgets.py            # enforce
    python3 scripts/check_word_budgets.py --report   # also print each skill's runtime load
    python3 scripts/check_word_budgets.py --tighten  # lower budgets to current counts

The contracts grow by accretion — every review finding and field report adds
text and nothing pushes back — and a model holds a long contract worst exactly
where it matters, through a compaction that keeps a sentence's headline and
drops its conditions (issue #157). This is the push back.

A word count is a token count, not a reading of the prose: it cannot be
paraphrased around and it says nothing about meaning, so it sits inside
CLAUDE.md's rule against checks that grep the contracts.

Counting: runs of the file's raw bytes separated by ASCII whitespace, Python's
`bytes.split()`. That is what `wc -w` reports on macOS; GNU `wc` does not count
a run made only of non-ASCII bytes, such as a lone em dash, so it reads lower
on this corpus. The number here is the same on every platform, which is what a
budget needs.

The budgets live in scripts/word_budgets.json, one entry per `skills/*/SKILL.md`,
per other contract file beside one (a top-level `skills/*/*.md` that is not
NOTES.md or README.md, such as swarm's runtime-remote.md, which a tier-specific
run loads with the SKILL.md), per file in a skill's `schemas/` directory (such
as backlog-orchestrator's checkpoint-output.md, the field lists its SKILL.md
moved there), and per `rules/*.md` that is not a `-notes.md`. Without the
second and third kinds, a cut could move text into a file beside SKILL.md and
count as a cut. The check fails when:

  - a file has more words than its budget;
  - a file has no entry (a new skill or rule declares one), or an entry names
    no file;
  - a budget exceeds the file's count by more than the slack, so a budget
    cannot be padded ahead of growth, and a cut that is not recorded with
    --tighten turns the check red until it is.

Each entry also carries a target, which is reported and not enforced.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUDGETS = ROOT / "scripts" / "word_budgets.json"

# Top-level files in a skill directory that are not contract: SKILL.md has its
# own line in governed(), NOTES.md explains and never binds, README.md is for
# people.
NOT_CONTRACT = {"SKILL.md", "NOTES.md", "README.md"}


def count_words(path: Path) -> int:
    return len(path.read_bytes().split())


def governed() -> list[str]:
    """Every file that must carry a budget, as a repository-relative path."""
    files = sorted(ROOT.glob("skills/*/SKILL.md"))
    files += sorted(p for p in ROOT.glob("skills/*/*.md") if p.name not in NOT_CONTRACT)
    files += sorted(p for p in ROOT.glob("skills/*/schemas/*") if p.is_file())
    files += sorted(p for p in ROOT.glob("rules/*.md") if not p.name.endswith("-notes.md"))
    return [p.relative_to(ROOT).as_posix() for p in files]


def load() -> dict:
    return json.loads(BUDGETS.read_text(encoding="utf-8"))


def slack_limit(words: int, slack_percent: float) -> int:
    return math.ceil(words * (1 + slack_percent / 100))


def check(data: dict) -> tuple[list[str], list[tuple[str, int, int, int]]]:
    errors: list[str] = []
    rows: list[tuple[str, int, int, int]] = []
    slack = data.get("slack_percent")
    if not isinstance(slack, (int, float)) or isinstance(slack, bool) or slack < 0:
        return [f"{BUDGETS.name}: slack_percent must be a non-negative number"], rows
    entries = data.get("files")
    if not isinstance(entries, dict):
        return [f"{BUDGETS.name}: files must be an object"], rows

    wanted = governed()
    for rel in wanted:
        words = count_words(ROOT / rel)
        entry = entries.get(rel)
        if entry is None:
            errors.append(f"{rel}: no budget entry ({words} words); add one to {BUDGETS.name}")
            continue
        budget, target = entry.get("budget"), entry.get("target")
        bad = [k for k, v in (("budget", budget), ("target", target))
               if not isinstance(v, int) or isinstance(v, bool) or v <= 0]
        if bad:
            errors.append(f"{rel}: {' and '.join(bad)} must be a positive integer")
            continue
        rows.append((rel, words, budget, target))
        if words > budget:
            errors.append(f"{rel}: {words} words, over its budget of {budget} by {words - budget}")
        elif budget > slack_limit(words, slack):
            errors.append(
                f"{rel}: budget {budget} is more than {slack}% above its {words} words; "
                f"run --tighten and commit the result")

    for rel in sorted(set(entries) - set(wanted)):
        errors.append(f"{rel}: budget entry names no governed file; remove it")
    return errors, rows


def print_table(rows: list[tuple[str, int, int, int]]) -> None:
    width = max((len(r[0]) for r in rows), default=4)
    print(f"{'file':<{width}}  {'words':>6}  {'budget':>6}  {'target':>6}  {'over target':>11}")
    for rel, words, budget, target in rows:
        over = words - target
        print(f"{rel:<{width}}  {words:>6}  {budget:>6}  {target:>6}  "
              f"{(f'+{over}' if over > 0 else '-'):>11}")


def print_runtime_load() -> None:
    """SKILL.md, any contract file beside it, and its bundled references/.

    That is what a skill loads before work, on the tier that loads the most.

    Information only. references/ is generated by refresh_shared_rules.sh and
    never committed, so run that first or every skill reads as bare.
    """
    print("\nRuntime load per skill (SKILL.md and files beside it + references/; information only)")
    rows = []
    for skill_md in sorted(ROOT.glob("skills/*/SKILL.md")):
        refs = sorted((skill_md.parent / "references").glob("*.md"))
        own = count_words(skill_md) + sum(
            count_words(p) for p in sorted(skill_md.parent.glob("*.md")) if p.name not in NOT_CONTRACT)
        own += sum(count_words(p) for p in sorted(skill_md.parent.glob("schemas/*")) if p.is_file())
        ref_words = sum(count_words(p) for p in refs)
        rows.append((skill_md.parent.name, own, len(refs), ref_words, own + ref_words))
    width = max((len(r[0]) for r in rows), default=5)
    print(f"{'skill':<{width}}  {'SKILL.md':>8}  {'refs':>4}  {'ref words':>9}  {'total':>6}")
    for name, own, n, ref_words, total in rows:
        print(f"{name:<{width}}  {own:>8}  {n:>4}  {ref_words:>9}  {total:>6}")
    if not any(r[2] for r in rows):
        print("(no references/ found: run scripts/refresh_shared_rules.sh first)")


def tighten(data: dict) -> int:
    """Lower each budget to its file's current count where that is lower. Never raise."""
    lowered = 0
    for rel, entry in data.get("files", {}).items():
        path = ROOT / rel
        budget = entry.get("budget")
        if not path.is_file() or not isinstance(budget, int):
            continue
        words = count_words(path)
        if words < budget:
            print(f"tightened {rel}: {budget} -> {words}")
            entry["budget"] = words
            lowered += 1
    BUDGETS.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"{lowered} budget(s) lowered")
    return lowered


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--report", action="store_true",
                    help="also print each skill's runtime load (information only)")
    ap.add_argument("--tighten", action="store_true",
                    help="lower budgets to current counts where lower, then check")
    args = ap.parse_args()

    if not BUDGETS.is_file():
        print(f"no {BUDGETS.relative_to(ROOT)}", file=sys.stderr)
        return 2
    data = load()
    if args.tighten:
        tighten(data)
        data = load()

    errors, rows = check(data)
    print_table(rows)
    if args.report:
        print_runtime_load()
    for e in errors:
        print(f"error: {e}")
    print(f"\n{len(rows)} file(s) budgeted · {len(errors)} error(s)")
    if errors:
        print(
            "\nA budget may fall and may not rise without a reason. Cutting? Run\n"
            "--tighten and commit it. Growing? Raise the budget in word_budgets.json\n"
            "and say why in the PR body (CLAUDE.md, *Checks*).")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
