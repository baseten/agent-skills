#!/usr/bin/env python3
"""Fail if a bundled shared rule diverges from its source, or a skill cites a
rule it does not carry.

Both checks are file-level and exact. Neither reads the prose: the first is a
byte comparison against the source, the second is whether a path a skill names
exists inside it. A skill that cites a rule it has no copy of is broken on any
machine that installed only that skill, and the failure is silent - the model
simply proceeds without the rule.
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

    for skill_md in sorted(ROOT.glob("skills/*/SKILL.md")):
        skill_dir = skill_md.parent
        cited = set(CITATION.findall(skill_md.read_text(encoding="utf-8")))
        for ref in sorted(cited):
            checked += 1
            bundled = skill_dir / "references" / ref
            rel = bundled.relative_to(ROOT)
            if not bundled.is_file():
                errors.append(f"{rel} is cited by {skill_dir.name} but not present")
                continue
            source = RULES / ref
            if not source.is_file():
                continue  # a skill-local reference with no shared source is fine
            if bundled.read_bytes() != source.read_bytes():
                errors.append(
                    f"{rel} differs from rules/{ref} — "
                    "edit the source and run scripts/refresh_shared_rules.sh"
                )

    # A source nobody bundles is dead weight, and more likely a wiring mistake.
    for source in sorted(RULES.glob("*.md")):
        if source.name.endswith("-notes.md"):
            continue
        if not any(ROOT.glob(f"skills/*/references/{source.name}")):
            errors.append(f"rules/{source.name} is bundled into no skill")

    for e in errors:
        print(f"ERROR {e}", file=sys.stderr)
    print(f"\n{checked} bundled reference(s) checked · {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
