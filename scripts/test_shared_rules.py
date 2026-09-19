#!/usr/bin/env python3
"""Fixtures for check_shared_rules.py's bundling guards.

Run from the repository root:

    python3 scripts/test_shared_rules.py

Why this file exists: the check it defends runs in CI against a tree that is
already correctly wired, so a green result is evidence about the wiring and
none at all about the guards. Delete any one of them and the required check
stays green over a skill that ships citing a rule it does not carry — a rule
the model then never reads, silently, on the one machine that installed that
skill alone.

The guards were added a round at a time, and each was proved by hand against a
mutation that was then thrown away. BROKEN is those mutations, kept: one
fixture repository per wiring failure the check claims to catch, built in a
temporary directory so nothing here touches the real tree. GOOD holds the
shapes that must keep passing — a skill-local reference that has no shared
source, and a `rules/*-notes.md` that nothing bundles.

GUARDS is what makes the fixtures load-bearing, and it is the point of the
file. Each BROKEN case names the single guard it is pinned to, and is run
twice: red against the checker intact, green against the same checker with that
one guard neutered and nothing else. A fixture that stays red either way is
being caught by some other guard and would survive the deletion of the one it
claims to protect — the failure this repository has already shipped twice, and
the reason test_no_machine_paths.py ends in a coverage section of its own.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHECK = "scripts/check_shared_rules.py"
REFRESH = "scripts/refresh_shared_rules.sh"

RULE = "shared-rule.md"
RULE_TEXT = "# Shared rule\n\nHeld once under rules/, copied into every skill that applies it.\n"
CONSUMERS = ("alpha", "beta")

SKILL_MD = """---
name: {name}
description: fixture
---

Read `references/{rule}` before writing anything.
"""

UNCITED_SKILL_MD = """---
name: {name}
description: fixture
---

This skill names no shared rule at all.
"""

# The generator the check reads its two facts out of: which bundles this
# repository generates, and which skills it declares consumers of each. Shaped
# like the real one down to the ROOT assignment, which is itself an uppercase
# assignment the declared-consumer parser has to step over.
REFRESH_SH = """#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/.." && pwd)"

SHARED_RULE="{consumers}"

for skill in $SHARED_RULE; do
  src="$ROOT/rules/{rule}"
  dest="$ROOT/skills/$skill/references/{rule}"
  cp "$src" "$dest"
done
"""

# guard name -> the substitution that removes that guard and nothing else.
GUARDS = {
    "divergence": (
        "            if bundled.read_bytes() != source.read_bytes():",
        "            if False:",
    ),
    "missing-copy": (
        "            if not bundled.is_file():\n"
        '                errors.append(f"{rel} is cited by {skill_dir.name} but not present")\n'
        "                continue",
        "            if not bundled.is_file():\n"
        "                continue",
    ),
    "missing-source": (
        "                if ref in generated:",
        "                if False:",
    ),
    "uncited-rule": (
        "        if not consumers:",
        "        if False:",
    ),
    "declared-consumer": (
        "        for name in sorted(declared.get(source.name, ())):",
        "        for name in sorted(()):",
    ),
    "orphan-bundle": (
        '        if not (bundled.parent.parent / "SKILL.md").is_file():',
        "        if False:",
    ),
    "generator-names-nothing": (
        "    if not generated:",
        "    if False:",
    ),
    "unreadable-consumers": (
        "        if not declared.get(name):",
        "        if False:",
    ),
}


def cite(tree: pathlib.Path, skill: str, rule: str, template: str = SKILL_MD) -> None:
    d = tree / "skills" / skill
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(template.format(name=skill, rule=rule), encoding="utf-8")


def bundle(tree: pathlib.Path, skill: str, rule: str, text: str) -> None:
    d = tree / "skills" / skill / "references"
    d.mkdir(parents=True, exist_ok=True)
    (d / rule).write_text(text, encoding="utf-8")


# --- one mutation per wiring failure the check claims to catch ---------------

def diverged_copy(tree: pathlib.Path) -> None:
    bundle(tree, "alpha", RULE, RULE_TEXT + "\nAnd a sentence edited into the copy.\n")


def citation_without_copy(tree: pathlib.Path) -> None:
    cite(tree, "gamma", RULE)  # cites the rule, carries nothing


def rule_nothing_cites(tree: pathlib.Path) -> None:
    (tree / "rules" / "lonely-rule.md").write_text("# Lonely\n", encoding="utf-8")


def orphan_bundle(tree: pathlib.Path) -> None:
    bundle(tree, "stale", RULE, RULE_TEXT)  # a references/ a rename left behind


def source_deleted(tree: pathlib.Path) -> None:
    (tree / "rules" / RULE).unlink()


def declared_consumer_missing(tree: pathlib.Path) -> None:
    shutil.rmtree(tree / "skills" / "beta")


def declared_consumer_stops_citing(tree: pathlib.Path) -> None:
    cite(tree, "beta", RULE, template=UNCITED_SKILL_MD)


def declared_consumer_drops_rule(tree: pathlib.Path) -> None:
    cite(tree, "beta", RULE, template=UNCITED_SKILL_MD)
    (tree / "skills" / "beta" / "references" / RULE).unlink()


def generator_names_no_source(tree: pathlib.Path) -> None:
    text = (tree / REFRESH).read_text(encoding="utf-8")
    (tree / REFRESH).write_text(
        text.replace(f'src="$ROOT/rules/{RULE}"', 'src="$ROOT/$RULE_PATH"'), encoding="utf-8")


def generator_renames_the_consumer_list(tree: pathlib.Path) -> None:
    """The consumer list is found by spelling the rule out of the variable name,
    so renaming the variable empties it and every per-consumer check iterates
    nothing. Reported by the agent that wrote these fixtures, and green before
    the guard existed: the rule keeps being copied, no consumer is ever checked.
    """
    text = (tree / REFRESH).read_text(encoding="utf-8")
    (tree / REFRESH).write_text(
        text.replace(RULE[:-3].upper().replace("-", "_"), "SOME_OTHER_NAME"),
        encoding="utf-8")


BROKEN = [
    ("a bundled copy diverges from its source", "divergence", diverged_copy),
    ("a skill cites the rule and does not carry it", "missing-copy", citation_without_copy),
    ("a rule in rules/ that no skill cites", "uncited-rule", rule_nothing_cites),
    ("a bundle with no SKILL.md beside it", "orphan-bundle", orphan_bundle),
    ("the source is deleted while its copies remain", "missing-source", source_deleted),
    ("a declared consumer has no skill", "declared-consumer", declared_consumer_missing),
    ("a declared consumer stops citing the rule", "declared-consumer",
     declared_consumer_stops_citing),
    ("a declared consumer drops the citation and the copy", "declared-consumer",
     declared_consumer_drops_rule),
    ("the generator names no source the check can read", "generator-names-nothing",
     generator_names_no_source),
    ("the generator renames the consumer list", "unreadable-consumers",
     generator_renames_the_consumer_list),
]


# --- the shapes that must keep passing --------------------------------------

def skill_local_reference(tree: pathlib.Path) -> None:
    """A reference with no rules/ source is a skill's own, not a stale bundle."""
    cite(tree, "gamma", "local-note.md")
    bundle(tree, "gamma", "local-note.md", "# Local\n")


def notes_beside_the_rule(tree: pathlib.Path) -> None:
    """rules/<name>-notes.md explains the rule and is never bundled, per CLAUDE.md."""
    (tree / "rules" / f"{RULE[:-3]}-notes.md").write_text("# Why\n", encoding="utf-8")


GOOD = [
    ("a skill-local reference with no shared source", skill_local_reference),
    ("a rules/*-notes.md that nothing bundles", notes_beside_the_rule),
]


def neutered(src: str, guard: str) -> str:
    old, new = GUARDS[guard]
    out = src.replace(old, new, 1)
    if out == src:
        raise AssertionError(
            f"neutering {guard!r} did not apply — check_shared_rules.py has been reworded "
            "and this fixture is no longer testing the guard it names")
    return out


def tree_with(tmp: pathlib.Path, name: str, guard: str | None = None) -> pathlib.Path:
    """A minimal repository: one generated rule, two declared consumers."""
    tree = tmp / name
    if tree.exists():
        shutil.rmtree(tree)
    (tree / "scripts").mkdir(parents=True)
    (tree / "rules").mkdir()
    src = (ROOT / CHECK).read_text(encoding="utf-8")
    if guard is not None:
        src = neutered(src, guard)
    (tree / CHECK).write_text(src, encoding="utf-8")
    (tree / REFRESH).write_text(
        REFRESH_SH.format(consumers=" ".join(CONSUMERS), rule=RULE), encoding="utf-8")
    (tree / "rules" / RULE).write_text(RULE_TEXT, encoding="utf-8")
    for skill in CONSUMERS:
        cite(tree, skill, RULE)
        bundle(tree, skill, RULE, RULE_TEXT)
    return tree


def run(tree: pathlib.Path) -> tuple[int, str]:
    r = subprocess.run([sys.executable, CHECK], cwd=tree, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def main() -> int:
    checks: list[tuple[str, bool]] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmpp = pathlib.Path(tmp)

        code, out = run(tree_with(tmpp, "clean"))
        checks.append(("a correctly wired tree is green", code == 0))

        for i, (label, _guard, break_it) in enumerate(BROKEN):
            tree = tree_with(tmpp, f"broken-{i}")
            break_it(tree)
            code, out = run(tree)
            checks.append((f"rejected: {label}", code == 1))

        for i, (label, allow) in enumerate(GOOD):
            tree = tree_with(tmpp, f"good-{i}")
            allow(tree)
            code, out = run(tree)
            checks.append((f"accepted: {label}", code == 0))

        # The property the fixtures above cannot supply on their own: that each
        # is caught by the guard it names, rather than by a neighbour that
        # would outlive that guard's deletion. Remove the named guard alone and
        # the case must sail through.
        for i, (label, guard, break_it) in enumerate(BROKEN):
            try:
                tree = tree_with(tmpp, f"pinned-{i}", guard=guard)
            except AssertionError as e:
                # The guard this case names is gone or reworded. That is a
                # result, not a crash: report it and let the rest of the
                # battery run, because the rejection above has gone red too and
                # the pair together says which guard went missing.
                checks.append((f"{guard} is still there to neuter: {e}", False))
                continue
            break_it(tree)
            code, out = run(tree)
            checks.append((f"{guard} alone rejects it: {label}", code == 0))

    for name, ok in checks:
        print(("PASS " if ok else "FAIL ") + name)
    failed = [n for n, ok in checks if not ok]
    print(f"\n{len(checks) - len(failed)}/{len(checks)} passing")
    if failed:
        print("\nFAILED:")
        for n in failed:
            print("  " + n)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
