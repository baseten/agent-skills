#!/usr/bin/env python3
"""Structural checks for this repo's skills. No model calls, no network.

Run from the repository root:

    python3 scripts/check_skills.py            # errors fail, warnings print
    python3 scripts/check_skills.py --strict   # warnings fail too

Every check here is mechanical. Anything needing judgement about whether a
rule is *right* belongs in a skill's evals, not here — this only catches the
defects that are decidable from the text: a skill whose frontmatter disagrees
with its directory, an evals file that no longer parses, and a cross-reference
pointing at a section that does not exist.
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

HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.M)

# "(see Section)", "(see Section, below)", "(see Section — aside)". The
# trailing qualifiers are prose, not part of the name.
SEE_REF = re.compile(r"\(see ([A-Z][^)]*?)\)")
CUT = re.compile(r"\s*(?:,|;|:|—|–| - |\.\s|\?)")
TRAILING = re.compile(r"\s+(?:above|below)$")

# "`other-skill`, *Section Name*" — a reference into another skill's contract.
CROSS_REF = re.compile(r"`([a-z][a-z0-9-]+)`,\s+\*([^*]+)\*")

# "(NOTES: ...)" — asserts the skill has a NOTES.md at all.
NOTES_REF = re.compile(r"\(NOTES[:)]")


def headings(text: str) -> set[str]:
    return {m.group(1).strip() for m in HEADING.finditer(text)}


def resolves(target: str, known: set[str]) -> bool:
    """Does `target` name one of `known`?

    Exact match, or the short form of a heading shaped "Short name, the rest
    of the sentence" — citing such a section by its first clause is the
    repo's own style and should not be a failure. The boundary matters: a
    bare prefix rule would let "Merge" resolve to "Merge behavior".
    """
    if target in known:
        return True
    return any(
        h.startswith(target + sep) for h in known for sep in (",", " —", " –", ":")
    )


def normalize(name: str) -> str:
    name = CUT.split(name.strip(), 1)[0]
    name = TRAILING.sub("", name.strip())
    return name.strip().rstrip(".").strip()


def check_references(skill: str, path: Path, text: str, all_headings: dict[str, set[str]]) -> None:
    own = all_headings[skill]
    for m in SEE_REF.finditer(text):
        target = normalize(m.group(1))
        if not target or (" " not in target and target.islower()):
            continue
        if not resolves(target, own):
            line = text[: m.start()].count("\n") + 1
            error(f"{rel(path)}:{line}", f'"(see {target})" matches no heading in this skill')

    for m in CROSS_REF.finditer(text):
        other, section = m.group(1), normalize(m.group(2))
        line = text[: m.start()].count("\n") + 1
        if other == skill or other not in all_headings:
            continue  # not a skill in this repo: a package name, a tool, a file
        if not resolves(section, all_headings[other]):
            error(
                f"{rel(path)}:{line}",
                f'cross-reference `{other}`, *{section}* matches no heading in that skill',
            )

    if NOTES_REF.search(text) and not (path.parent / "NOTES.md").exists():
        error(rel(path), "cites (NOTES: …) but the skill has no NOTES.md")


# --- per-skill checks -------------------------------------------------------


def check_skill(d: Path, all_headings: dict[str, set[str]]) -> None:
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

    check_references(name, skill_md, text, all_headings)
    notes = d / "NOTES.md"
    if notes.exists():
        check_references(name, notes, notes.read_text(encoding="utf-8"), all_headings)


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

    # Headings from every skill first: cross-references need the whole set.
    all_headings: dict[str, set[str]] = {}
    for d in dirs:
        text = (d / "SKILL.md").read_text(encoding="utf-8")
        hs = headings(text)
        notes = d / "NOTES.md"
        if notes.exists():
            hs |= headings(notes.read_text(encoding="utf-8"))
        all_headings[d.name] = hs

    for d in dirs:
        check_skill(d, all_headings)

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
