#!/usr/bin/env python3
"""Structural checks for this repo's skills. No model calls, no network.

Run from the repository root:

    python3 scripts/check_skills.py            # errors fail, warnings print
    python3 scripts/check_skills.py --strict   # warnings fail too

Every check here is mechanical. Anything needing judgement about whether a
rule is *right* belongs in a skill's evals, not here — this only catches the
defects that are decidable from the text: a skill whose frontmatter disagrees
with its directory, and an evals file that no longer parses.

It used to check cross-references too — that a `` `skill`, *Section* `` pointer
resolved to a heading that exists. That was removed after a test showed what it
actually verified: gutting a section while keeping its heading left nineteen
pointers resolving to an empty heading and the check green, and a reference
written in a near-miss form was never examined at all. It confirmed names, not
links, and only the names written in the shape its regex expected.
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"

errors: list[str] = []
warnings: list[str] = []


def error(where: str, msg: str) -> None:
    errors.append(f"{where}: {msg}")


def warn(where: str, msg: str) -> None:
    warnings.append(f"{where}: {msg}")


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


# --- frontmatter -------------------------------------------------------------

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def parse_frontmatter(text: str) -> dict[str, str] | None:
    """Read the leading YAML block as flat key: value pairs.

    Deliberately not a YAML parser: the frontmatter this repo ships is flat
    scalars, and a dependency for two keys is not worth a CI install step.
    """
    m = FRONTMATTER.match(text)
    if not m:
        return None
    fields: dict[str, str] = {}
    key = None
    for line in m.group(1).split("\n"):
        if re.match(r"^[a-zA-Z_-]+:", line):
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
        elif key and line.startswith(" "):
            fields[key] += " " + line.strip()
    return fields


# --- headings and references ------------------------------------------------

def check_skill(d: Path) -> None:
    name = d.name
    skill_md = d / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")

    fm = parse_frontmatter(text)
    if fm is None:
        error(rel(skill_md), "no YAML frontmatter block")
    else:
        if fm.get("name") != name:
            error(rel(skill_md), f'frontmatter name "{fm.get("name")}" != directory "{name}"')
        if not fm.get("description"):
            error(rel(skill_md), "frontmatter has no description")

    evals = d / "evals" / "evals.json"
    if evals.exists():
        try:
            data = json.loads(evals.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            error(rel(evals), f"does not parse: {exc}")
        else:
            if data.get("skill_name") != name:
                error(rel(evals), f'skill_name "{data.get("skill_name")}" != directory "{name}"')
            cases = data.get("evals")
            if not isinstance(cases, list) or not cases:
                error(rel(evals), "no evals array, or it is empty")
            else:
                ids = [c.get("id") for c in cases]
                if len(set(ids)) != len(ids):
                    error(rel(evals), f"duplicate eval ids: {sorted(ids)}")
                for c in cases:
                    label = c.get("name") or c.get("id")
                    for field in ("prompt", "expected_output", "assertions"):
                        if not c.get(field):
                            error(rel(evals), f'eval "{label}" has no {field}')



def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="treat warnings as failures")
    args = ap.parse_args()

    if not SKILLS.is_dir():
        print(f"no skills/ directory beside this script ({ROOT})", file=sys.stderr)
        return 2
    dirs = sorted(d for d in SKILLS.iterdir() if (d / "SKILL.md").exists())
    if not dirs:
        print("skills/ holds no directory with a SKILL.md", file=sys.stderr)
        return 2

    for d in dirs:
        check_skill(d)

    perms = ROOT / "permissions.json"
    if perms.exists():
        try:
            json.loads(perms.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            error("permissions.json", f"does not parse: {exc}")

    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"error: {e}")

    print(
        f"\n{len(dirs)} skills checked · {len(errors)} error(s) · {len(warnings)} warning(s)"
    )
    if errors or (args.strict and warnings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
