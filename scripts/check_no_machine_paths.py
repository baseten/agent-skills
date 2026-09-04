#!/usr/bin/env python3
"""Reject skills that depend on one machine's filesystem.

A skill here has to work in a cloud session and in a fresh container, so it
cannot read a path that exists only in one person's home directory. The failure
mode this catches is silent, which is why it is a gate: `` !`cat /some/path` ``
injects the empty string when the path is missing, so the skill loads with its
guidance gone and reports nothing.

Absolute home paths are also the signature of a skill that needs someone's
private material to function. Those belong in a private checkout and reach
cloud sessions through a claude.ai account, never through this public
repository — see the README, *Personal skills stay out*.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"

# `~/Documents/...`, `/Users/someone/...`, `/home/someone/...`, `$HOME/Documents/...`.
# A bare `~/.claude/...` or `$HOME/.codex/...` is fine: those exist wherever the
# agent runs, and naming them is how a skill talks about its own install location.
PATTERNS = [
    re.compile(r"~/(?!\.)[\w.-]+/"),
    re.compile(r"/Users/[\w.-]+/"),
    re.compile(r"/home/[\w.-]+/"),
    re.compile(r"\$HOME/(?!\.)[\w.-]+/"),
]

SEARCHED = ("*.md", "*.sh", "*.py", "*.json")


def main() -> int:
    if not SKILLS.is_dir():
        print(f"no skills/ directory beside this script ({ROOT})", file=sys.stderr)
        return 2

    findings: list[str] = []
    checked = 0
    for pattern in SEARCHED:
        for path in sorted(SKILLS.rglob(pattern)):
            checked += 1
            for lineno, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                for rx in PATTERNS:
                    m = rx.search(line)
                    if m:
                        findings.append(
                            f"{path.relative_to(ROOT)}:{lineno}: "
                            f"machine-specific path {m.group(0)!r}"
                        )
                        break

    for f in findings:
        print(f"error: {f}")

    print(f"\n{checked} file(s) checked · {len(findings)} error(s)")
    if findings:
        print(
            "\nA skill that needs a path from one machine cannot work in a cloud\n"
            "session. If it needs private material, keep it in a private checkout\n"
            "and enable it for a claude.ai account instead."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
