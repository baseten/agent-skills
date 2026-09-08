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
# Enumerated rather than patched, after four rounds of finding the class wider
# than the fix. A home reference has three independent axes, and every earlier
# version fixed one point on one of them:
#
#   whose home      bare (`~/`), a named user (`~someone/`), or spelled out
#                   (`/Users/x`, `/home/x`)
#   how spelled     literal, `$HOME`, or `${HOME}`
#   how deep        a file directly under it, or a subdirectory below it
#
# Portability is a whitelist, not "anything hidden": only the agent config roots
# travel, and only with their slash, so `~/.claude-work/` is a local profile and
# `~/.writing/` is a personal guide wearing a dotfile's clothes.
#
# URLs are removed before matching rather than excluded by lookbehind, which
# retires that false-positive class instead of enumerating its spellings:
# `https://example.com/home/getting-started` is not a filesystem dependency.
# The portable roots may be named bare as well as with a path under them: a
# skill saying "skills live in ~/.claude" is describing where an agent keeps its
# own config, which is true wherever it runs.
# Exempt when the root is *not* followed by another path character: `~/.claude`
# and `~/.claude/skills` are the agent's own config, `~/.claude-work` is one
# person's profile. `\b` was wrong here because a hyphen satisfies it.
PORTABLE = r"(?!(?:\.claude|\.codex)(?![\w.-]))"
HOME_PREFIX = r"(?:~|\$HOME|\$\{HOME\})"

# Only web URLs are stripped before matching. A `file://` URL is a filesystem
# dependency wearing a scheme, so stripping every scheme hid the very thing this
# looks for.
URL = re.compile(r"\bhttps?://\S+")
# `file://` is stripped down to its path rather than removed: the scheme is not
# the dependency, the path after it is, and the `///` also defeats the
# path-boundary lookbehind below.
FILE_URL = re.compile(r"\bfile://")

PATTERNS = [
    # a bare home, in any spelling, at any depth
    re.compile(HOME_PREFIX + r"/" + PORTABLE + r"[\w.-]+"),
    # another user's home: always machine-specific, never portable
    re.compile(r"~[\w.-]+/"),
    # `(?<![\w/])` because these have to begin a path. Prose uses slashes as an
    # or-separator -- "the supplied manifest/root/explicit issue set" is not a
    # filesystem dependency, and an unanchored /root/ read it as one.
    re.compile(r"(?<![\w/])/Users/[\w.-]+"),
    re.compile(r"(?<![\w/])/home/[\w.-]+"),
    re.compile(r"(?<![\w/])/root/[\w.-]+"),
    # the Windows spellings, which are case-insensitive on their own platform
    re.compile(r"[A-Za-z]:\\+Users\\+[\w.-]+", re.I),
    re.compile(r"%USERPROFILE%", re.I),
]

# Every file a skill ships, not an allowlist of extensions: a reference in a
# .txt, .yml or .csv shipped beside SKILL.md fails exactly the same way. Binary
# files are skipped by failing to decode rather than by being named.


def texts() -> list[Path]:
    return [p for p in sorted(SKILLS.rglob("*")) if p.is_file()]


def main() -> int:
    if not SKILLS.is_dir():
        print(f"no skills/ directory beside this script ({ROOT})", file=sys.stderr)
        return 2

    findings: list[str] = []
    checked = 0
    for path in texts():
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        checked += 1
        for lineno, line in enumerate(content.splitlines(), start=1):
            line = FILE_URL.sub(" ", URL.sub("", line))
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
