#!/usr/bin/env python3
"""Fixtures for check_word_budgets.py.

Run from the repository root:

    python3 scripts/test_check_word_budgets.py

The check runs in CI against a tree whose budgets were just written to match
it, so a green result there says nothing about whether any of its guards can
fail. Each fixture here builds a scratch repository, breaks it one way, and
requires the check to reject it — and --tighten is exercised in both
directions, because a tighten that could raise a budget would turn the ratchet
into a way of padding one.
"""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHECK = "scripts/check_word_budgets.py"


def words(n: int) -> str:
    return " ".join(["word"] * n) + "\n"


def build(tmp: pathlib.Path, files: dict[str, str], budgets: dict[str, dict],
          slack: float = 2) -> pathlib.Path:
    tree = tmp / "repo"
    if tree.exists():
        shutil.rmtree(tree)
    (tree / "scripts").mkdir(parents=True)
    shutil.copy(ROOT / CHECK, tree / CHECK)
    for rel, body in files.items():
        (tree / rel).parent.mkdir(parents=True, exist_ok=True)
        (tree / rel).write_text(body, encoding="utf-8")
    (tree / "scripts" / "word_budgets.json").write_text(
        json.dumps({"slack_percent": slack, "files": budgets}, indent=2) + "\n",
        encoding="utf-8")
    return tree


def run(tree: pathlib.Path, *args: str) -> tuple[int, str]:
    r = subprocess.run([sys.executable, CHECK, *args], cwd=tree,
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def budgets_of(tree: pathlib.Path) -> dict[str, int]:
    data = json.loads((tree / "scripts" / "word_budgets.json").read_text())
    return {k: v["budget"] for k, v in data["files"].items()}


SKILL = "skills/probe/SKILL.md"
RULE = "rules/probe.md"
NOTES = "rules/probe-notes.md"


def base_files(skill_words: int = 100, rule_words: int = 50) -> dict[str, str]:
    return {SKILL: words(skill_words), RULE: words(rule_words), NOTES: words(999)}


def entry(budget: int, target: int = 3000) -> dict:
    return {"budget": budget, "target": target}


def main() -> int:
    checks: list[tuple[str, bool]] = []
    with tempfile.TemporaryDirectory() as tmp:
        t = pathlib.Path(tmp)
        ok = {SKILL: entry(100), RULE: entry(50, 1500)}

        code, _ = run(build(t, base_files(), ok))
        checks.append(("an exact budget is green, and a -notes.md needs no entry", code == 0))

        code, out = run(build(t, base_files(skill_words=101), ok))
        checks.append(("one word over budget fails", code == 1 and "over its budget" in out))

        code, out = run(build(t, base_files(), {SKILL: entry(100)}))
        checks.append(("a rule with no entry fails", code == 1 and "no budget entry" in out))

        files = base_files()
        files["skills/new/SKILL.md"] = words(10)
        code, out = run(build(t, files, ok))
        checks.append(("a new skill with no entry fails", code == 1 and "no budget entry" in out))

        code, out = run(build(t, base_files(), {**ok, "skills/gone/SKILL.md": entry(10)}))
        checks.append(("an entry naming no file fails", code == 1 and "names no governed file" in out))

        code, out = run(build(t, base_files(), {SKILL: entry(103), RULE: entry(50, 1500)}))
        checks.append(("a padded budget (3% over, slack 2%) fails",
                       code == 1 and "run --tighten" in out))

        code, _ = run(build(t, base_files(), {SKILL: entry(102), RULE: entry(50, 1500)}))
        checks.append(("a budget within the slack passes", code == 0))

        code, out = run(build(t, base_files(), {SKILL: {"budget": 100}, RULE: entry(50, 1500)}))
        checks.append(("an entry with no target fails", code == 1 and "target" in out))

        code, _ = run(build(t, base_files(), {SKILL: entry(100, 50), RULE: entry(50, 1500)}))
        checks.append(("being over target is reported, not enforced", code == 0))

        # --tighten lowers where the file shrank, and never raises where it grew.
        tree = build(t, base_files(skill_words=80, rule_words=60),
                     {SKILL: entry(100), RULE: entry(50, 1500)})
        code, out = run(tree, "--tighten")
        after = budgets_of(tree)
        checks.append(("--tighten lowers a budget to the current count", after[SKILL] == 80))
        checks.append(("--tighten never raises a budget", after[RULE] == 50))
        checks.append(("--tighten still fails the file that grew",
                       code == 1 and "over its budget" in out))

        tree = build(t, base_files(skill_words=80), {SKILL: entry(100), RULE: entry(50, 1500)})
        code, _ = run(tree, "--tighten")
        checks.append(("after --tighten a cut tree is green", code == 0))
        code, _ = run(tree)
        checks.append(("and stays green on a plain run", code == 0))

        # The count must be the one the budgets file documents: LC_ALL=C wc -w.
        body = "tab\tsep  double\nnon breaking café — dash\n"
        probe = t / "probe.md"
        probe.write_text(body, encoding="utf-8")
        wc = shutil.which("wc")
        if wc:
            r = subprocess.run([wc, "-w", str(probe)], capture_output=True, text=True,
                               env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"})
            expected = int(r.stdout.split()[0])
            tree = build(t, {SKILL: body, RULE: words(1)},
                         {SKILL: entry(expected), RULE: entry(1, 1500)})
            code, out = run(tree)
            checks.append(("the count matches LC_ALL=C wc -w", code == 0))

    for name, passed in checks:
        print(("PASS " if passed else "FAIL ") + name)
    failed = [n for n, passed in checks if not passed]
    print(f"\n{len(checks) - len(failed)}/{len(checks)} passing")
    if failed:
        print("\nFAILED:")
        for n in failed:
            print("  " + n)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
