#!/usr/bin/env python3
"""Fail if a bundled shared rule diverges from its source, or a skill reaches a
rule it does not carry.

Both checks are file-level and exact. Neither reads the prose: the first is a
byte comparison against the source, the second is whether a path a skill names
exists inside it. A skill that cites a rule it has no copy of is broken on any
machine that installed only that skill, and the failure is silent - the model
simply proceeds without the rule.

A rule can cite another rule the same way a skill does, as a literal
`references/<name>.md` token, and a skill carrying the first then needs the
second beside it. The generator's consumer lists name only the skills that
*apply* a rule, and each of those must cite it in its own SKILL.md, exactly as
before rules cited rules. refresh_shared_rules.sh derives the rest: for each
skill, every generated rule its declared rules cite, transitively, is copied
too. This check computes the same closure and exempts only that *derived*
carriage from the must-cite requirement - a declared consumer that stops citing
its rule still fails, however many rules would reach it. The transitive-
consumer guard is that what a skill carries of the generated rules is exactly
its declared rules plus their derived closure: a derived copy missing, or a
generated copy the generator neither declares nor derives. A rule's citation of
itself (its intro names its own bundled path) is not an edge.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RULES = ROOT / "rules"
CITATION = re.compile(r"`references/([a-z0-9-]+\.md)`")


def main() -> int:
    errors: list[str] = []
    checked = 0

    # What this repo generates comes from the generator, not from what happens to
    # exist. Reading it off rules/ cannot see a deleted source - the very case
    # the missing-source check below exists for.
    refresh = (ROOT / "scripts" / "refresh_shared_rules.sh").read_text(encoding="utf-8")
    # The generator names its rules in one RULES list and holds each rule's
    # consumers in a variable spelled from the rule name. Read the list, not the
    # copy line: the copy line is now a loop over $rule and names nothing.
    rules_list = re.search(r'^RULES="([^"]*)"', refresh, re.M)
    generated = {f"{r}.md" for r in (rules_list.group(1).split() if rules_list else ())}

    # And which skills the generator declares apply each rule, so a consumer
    # that quietly stops carrying one is visible.
    declared: dict[str, set[str]] = {}
    for var, names in re.findall(r'^([A-Z_]+)="([^"]*)"', refresh, re.M):
        rule = f"{var.lower().replace('_', '-')}.md"
        if rule in generated:
            declared[rule] = set(names.split())

    # The consumer list is found by spelling the rule out of the variable name,
    # so AUTHORED_WRITE_FORM works only because it happens to spell
    # authored-write-form.md. Rename the variable and this mapping finds nothing,
    # every per-consumer check below iterates an empty set, and the guard becomes
    # a no-op that reports success. A rule the generator copies must have a
    # consumer list the check can actually read - the same self-awareness the
    # empty-`generated` error above provides for sources.
    for name in sorted(generated):
        if not declared.get(name):
            errors.append(
                f"scripts/refresh_shared_rules.sh copies rules/{name} but names no "
                "consumers the check can read — the variable holding them must be "
                f"spelled {name[:-3].upper().replace('-', '_')}"
            )
    if not generated:
        errors.append(
            'scripts/refresh_shared_rules.sh declares no RULES="..." list — '
            "this check cannot tell a generated bundle from a skill-local one"
        )

    # Rule-to-rule citations, read off the sources as literal tokens.
    rule_cites: dict[str, set[str]] = {}
    for source in RULES.glob("*.md"):
        if source.name.endswith("-notes.md"):
            continue
        rule_cites[source.name] = (
            set(CITATION.findall(source.read_text(encoding="utf-8"))) - {source.name})

    def closure(start: set[str]) -> set[str]:
        seen, todo = set(), list(start)
        while todo:
            ref = todo.pop()
            if ref in seen:
                continue
            seen.add(ref)
            todo.extend(rule_cites.get(ref, ()))
        return seen

    # What the generator carries into each skill: the rules declared for it,
    # and - derived, not declared - every generated rule those cite.
    declared_for: dict[str, set[str]] = {}
    for rule, names in declared.items():
        for name in names:
            declared_for.setdefault(name, set()).add(rule)
    derived: dict[str, set[str]] = {
        name: (closure(rules) & generated) - rules for name, rules in declared_for.items()}

    # Derived carriage is the generator's to get right, and the tree is where it
    # shows: a derived copy missing means the skill holds a pointer to a file it
    # was never given; a generated copy nobody declared or derived is stale, and
    # a stale copy is what hides the first failure locally.
    expected_carriage = {
        skill_md.parent.name: declared_for.get(skill_md.parent.name, set())
        | derived.get(skill_md.parent.name, set())
        for skill_md in ROOT.glob("skills/*/SKILL.md")}
    for skill_name, expected in sorted(expected_carriage.items()):
        refs = ROOT / "skills" / skill_name / "references"
        carried = {p.name for p in refs.glob("*.md")} & generated if refs.is_dir() else set()
        for name in sorted(derived.get(skill_name, set()) - carried):
            errors.append(
                f"skills/{skill_name} carries a rule that cites {name}, but not {name} "
                "itself — run scripts/refresh_shared_rules.sh")
        # A rule with no readable consumer list is the unreadable-consumers
        # guard's to report; every copy of it would otherwise land here too.
        for name in sorted((carried - expected) & {r for r, s in declared.items() if s}):
            errors.append(
                f"skills/{skill_name}/references/{name} is a generated rule the generator "
                "neither declares nor derives for this skill — stale; run "
                "scripts/refresh_shared_rules.sh")

    for skill_md in sorted(ROOT.glob("skills/*/SKILL.md")):
        skill_dir = skill_md.parent
        cited = set(CITATION.findall(skill_md.read_text(encoding="utf-8")))
        for ref in sorted(cited | derived.get(skill_dir.name, set())):
            checked += 1
            bundled = skill_dir / "references" / ref
            rel = bundled.relative_to(ROOT)
            if ref not in cited and not bundled.is_file():
                continue  # a missing derived copy is reported above
            if not bundled.is_file():
                errors.append(f"{rel} is cited by {skill_dir.name} but not present")
                continue
            source = RULES / ref
            if not source.is_file():
                # A skill-local reference with no shared source is fine - but a
                # bundle this repo generates is not. If rules/<name>.md is
                # deleted while its copies remain, every citation takes this
                # path, the source loop below has nothing to inspect, and the
                # twelve copies quietly become independent files with no single
                # source of truth - green the whole way.
                if ref in generated:
                    errors.append(
                        f"rules/{ref} is missing but {rel} was generated from it — "
                        "restore the source or drop the bundles"
                    )
                continue
            if bundled.read_bytes() != source.read_bytes():
                errors.append(
                    f"{rel} differs from rules/{ref} — "
                    "edit the source and run scripts/refresh_shared_rules.sh"
                )

    # A source nobody bundles is dead weight, and more likely a wiring mistake.
    # Only a directory holding a SKILL.md counts as a consumer: a rename or a
    # rebase can leave skills/<old-name>/references/ behind with no skill beside
    # it, and counting that orphan keeps this guard green while no installable
    # skill carries the rule at all. That happened while assembling this change.
    for source in sorted(RULES.glob("*.md")):
        if source.name.endswith("-notes.md"):
            continue
        consumers = [
            b for b in ROOT.glob(f"skills/*/references/{source.name}")
            if (skill := b.parent.parent / "SKILL.md").is_file()
            and source.name in CITATION.findall(skill.read_text(encoding="utf-8"))
        ]
        if not consumers:
            errors.append(
                f"rules/{source.name} is cited by no skill — "
                "a bundle nothing cites is never read"
            )

        # "Some skill cites it" is not the property that matters. The generator
        # names the skills that apply this rule, and each of them installs
        # alone: one that loses its citation and its copy ships without the rule
        # while every other consumer keeps CI green. Check each declared one.
        for name in sorted(declared.get(source.name, ())):
            skill_md = ROOT / "skills" / name / "SKILL.md"
            if not skill_md.is_file():
                errors.append(
                    f"refresh_shared_rules.sh declares {name} a consumer of "
                    f"{source.name} but skills/{name}/SKILL.md does not exist"
                )
                continue
            if source.name not in CITATION.findall(skill_md.read_text(encoding="utf-8")):
                errors.append(
                    f"skills/{name} is declared a consumer of {source.name} "
                    "but does not cite it"
                )
            if not (ROOT / "skills" / name / "references" / source.name).is_file():
                errors.append(
                    f"skills/{name} is declared a consumer of {source.name} "
                    "but does not carry it — run scripts/refresh_shared_rules.sh"
                )

    # And an orphan bundle is itself the wiring mistake, so name it rather than
    # leaving a stale copy that nothing installs and nothing refreshes.
    for bundled in sorted(ROOT.glob("skills/*/references/*.md")):
        if not (bundled.parent.parent / "SKILL.md").is_file():
            errors.append(
                f"{bundled.relative_to(ROOT)} has no SKILL.md beside it — orphan bundle"
            )

    for e in errors:
        print(f"ERROR {e}", file=sys.stderr)
    print(f"\n{checked} bundled reference(s) checked · {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
