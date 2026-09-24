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
            if isinstance(data, list):
                cases = data
            else:
                if data.get("skill_name") != name:
                    error(rel(evals), f'skill_name "{data.get("skill_name")}" != directory "{name}"')
                cases = data.get("evals")
                # A companion is a skill name, so it is a token: it names a
                # directory that exists, or the eval runner silently gives the
                # reader a contract without the rules it defers to.
                companions = data.get("companions")
                if companions is not None:
                    if not isinstance(companions, list) or not all(isinstance(c, str) for c in companions):
                        error(rel(evals), "companions must be a list of skill names")
                    else:
                        for c in companions:
                            if c == name:
                                error(rel(evals), f'companion "{c}" is the skill itself')
                            elif not (SKILLS / c / "SKILL.md").exists():
                                error(rel(evals), f'companion "{c}" is not a skill in skills/')
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



def check_policy_schema() -> None:
    """schemas/agent-policy.schema.json against the skills that read each key.

    The schema restates defaults a skill documents, so it can drift from them;
    this compares files and tests literal tokens, never prose. It checks that
    every key names readers that exist and that each reader mentions the key,
    and that backlog-orchestrator's documented defaults block and the schema
    agree key for key and value for value.
    """
    path = ROOT / "schemas" / "agent-policy.schema.json"
    where = rel(path)
    if not path.exists():
        error(where, "missing")
        return
    try:
        props = json.loads(path.read_text(encoding="utf-8"))["properties"]
    except (json.JSONDecodeError, KeyError) as exc:
        error(where, f"does not parse as a schema with properties: {exc}")
        return
    for key, spec in props.items():
        if key == "$schema":
            continue
        readers = spec.get("x-read-by") or []
        if not readers:
            error(where, f"{key} names no reader in x-read-by")
        if "default" not in spec:
            error(where, f"{key} has no default")
        # A merge permission defaulting to on would publish "merging is on unless
        # you say otherwise" in the one place people look it up.
        if key.startswith("auto-merge") and spec.get("default") is not False:
            error(where, f"{key} is a merge permission and must default to false")
        expected = f"Read by: {', '.join(readers)}."
        if not str(spec.get("description", "")).endswith(expected):
            error(where, f"{key}: description must end with {expected!r}, matching x-read-by")
        for skill in readers:
            skill_md = ROOT / "skills" / skill / "SKILL.md"
            if not skill_md.exists():
                error(where, f"{key} is read by {skill}, which does not exist")
            elif f"`{key}`" not in skill_md.read_text(encoding="utf-8"):
                error(where, f"{key} is read by {skill}, whose SKILL.md never names `{key}`")

    # implement-issue lists what it reads on one line; a key it names only to
    # ignore must not pass for one it reads.
    ii = (ROOT / "skills" / "implement-issue" / "SKILL.md").read_text(encoding="utf-8")
    consumed_line = next((l for l in ii.splitlines() if "Keys consumed:" in l), "")
    consumed = set(re.findall(r"`([a-z-]+)`", consumed_line.split("Ignore")[0]))
    for key, spec in props.items():
        if "implement-issue" in spec.get("x-read-by", []) and key not in consumed:
            error(where, f"{key} lists implement-issue as a reader, but its 'Keys consumed' line does not")
    for key in consumed:
        if key in props and "implement-issue" not in props[key].get("x-read-by", []):
            error(where, f"implement-issue consumes {key}, but the schema does not list it as a reader")

    bo = (ROOT / "skills" / "backlog-orchestrator" / "SKILL.md").read_text(encoding="utf-8")
    anchor = bo.find("## Per-repository policy configuration")
    start = bo.find("```json", anchor)
    end = bo.find("```", start + 7)
    if anchor < 0 or start < 0 or end < 0:
        error(where, "cannot find backlog-orchestrator's policy defaults block")
        return
    try:
        documented = json.loads(bo[start + 7:end])
    except json.JSONDecodeError as exc:
        error(where, f"backlog-orchestrator's policy defaults block does not parse: {exc}")
        return
    for key, value in documented.items():
        if key not in props:
            error(where, f"backlog-orchestrator documents {key}, which the schema lacks")
        elif props[key].get("default") != value:
            error(where, f"{key}: schema default {props[key].get('default')!r}, backlog-orchestrator documents {value!r}")
        elif "backlog-orchestrator" not in props[key].get("x-read-by", []):
            error(where, f"{key}: backlog-orchestrator documents it but is not in its x-read-by")
    for key, spec in props.items():
        if "backlog-orchestrator" in spec.get("x-read-by", []) and key not in documented:
            error(where, f"{key} lists backlog-orchestrator as a reader, but its defaults block omits it")


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

    check_policy_schema()

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
