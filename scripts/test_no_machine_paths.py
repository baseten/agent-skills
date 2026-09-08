#!/usr/bin/env python3
"""Fixtures for check_no_machine_paths.py's path detector.

Run from the repository root:

    python3 scripts/test_no_machine_paths.py

Why this file exists: the check it defends runs in CI against a tree that is
already clean, so a green result is evidence about the tree and none at all
about the detector. Weaken the patterns to match nothing and the required check
stays green over a skill that cannot work anywhere but one laptop — which is
precisely the silent failure the gate was added for.

It shipped with exactly that gap. The first version required another path
component after the first, so `~/style-guide.md` passed while
`~/Documents/style-guide.md` failed, and nothing said so.

BAD holds every form a machine-specific path has taken or plausibly could take,
including the one that got through. GOOD holds the paths that must keep
passing: `~/.claude` and `$HOME/.codex` exist wherever an agent runs, and a
detector that fires on those makes the install instructions unwritable and will
be switched off. COVERAGE asserts the fixtures exercise the patterns rather
than the tree, by blanking the detector and requiring every BAD case to pass.
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHECK = "scripts/check_no_machine_paths.py"

BAD = [
    ("a home-relative directory", "!`cat ~/Documents/ai-alex/writing-style/style-guide.md`"),
    ("a home-relative file, no subdirectory", "!`cat ~/style-guide.md`"),
    ("an absolute macOS home", "Read /Users/someone/notes/style.md before drafting."),
    ("an absolute Linux home", "Read /home/someone/notes/style.md before drafting."),
    ("$HOME with a subdirectory", "Read `$HOME/Documents/guide.md` first."),
    ("$HOME with a bare file", "Read `$HOME/guide.md` first."),
    ("the braced spelling", "Read `${HOME}/style-guide.md` first."),
    ("the braced spelling, with a subdirectory", "Read `${HOME}/Documents/guide.md`."),
    ("a hidden personal directory", "Read `~/.writing/style-guide.md` before drafting."),
    ("a hidden personal directory via $HOME", "Read `$HOME/.private/guide.md`."),
    ("a hidden personal directory, braced", "Read `${HOME}/.secret/guide.md`."),
    ("a local profile that only looks portable", "Read `~/.claude-work/skills/x/SKILL.md`."),
    ("another user's home", "Read `~someone/style-guide.md` before drafting."),
    ("another user's home, with a subdirectory", "Read `~someone/Documents/guide.md`."),
    ("a Windows home", "Read `C:\\Users\\someone\\guide.md` first."),
    ("the Windows home variable", "Read `%USERPROFILE%\\guide.md` first."),
    ("the root user's home", "Read /root/notes/style.md before drafting."),
    ("a file:// URL is a path with a scheme", "Open file:///Users/someone/guide.md."),
    ("Windows, lower case", "Read `c:\\users\\someone\\guide.md`."),
    ("the Windows variable, lower case", "Read `%userprofile%\\guide.md`."),
]

GOOD = [
    ("the agent's own config directory", "Skills live in `~/.claude/skills/`."),
    ("a Codex symlink target", 'ln -sfn "$REPO/skills/$s" "$HOME/.codex/skills/$s"'),
    ("the braced spelling of the agent's own directory", 'Under `${HOME}/.claude/skills/`.'),
    ("the Codex root, unbraced", "Symlink into `~/.codex/skills/`."),
    ("a repo-relative path", "Read `references/style-guide.md` from this skill's directory."),
    ("a bare tilde in prose", "Roughly ~200 words, no more."),
    ("slashes used as an or-separator in prose",
     "from the supplied manifest/root/explicit issue set"),
    ("a mid-path segment that is not a home", "See docs/home/getting-started.md."),
    ("a portable root named bare", "Skills live in `~/.claude`, one per directory."),
    ("the Codex root named bare", "Codex reads `~/.codex` for its own config."),
    ("a URL that merely contains /home/", "See https://example.com/home/getting-started."),
    ("a URL that merely contains /Users/", "See https://example.com/Users/alex/profile."),
]


def run(tree: pathlib.Path) -> tuple[int, str]:
    r = subprocess.run([sys.executable, CHECK], cwd=tree, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def tree_with(tmp: pathlib.Path, body: str, detector: str | None = None) -> pathlib.Path:
    """A minimal repository: one skill, plus the checker under test."""
    tree = tmp / "repo"
    (tree / "scripts").mkdir(parents=True, exist_ok=True)
    (tree / "skills" / "probe").mkdir(parents=True, exist_ok=True)
    src = (ROOT / CHECK).read_text(encoding="utf-8")
    if detector is not None:
        # Anchored on the closing bracket at column 0: the patterns themselves
        # contain `]` inside character classes, so a non-greedy match to the
        # first one truncates the file and every fixture then fails on a syntax
        # error rather than on the detector -- which is what this substitution
        # exists to rule out.
        src = re.sub(r"PATTERNS = \[[\s\S]*?\n\]", detector, src, count=1)
        if "PATTERNS = []" not in src:
            raise AssertionError("blanking the detector did not apply; fixture is not testing it")
    (tree / CHECK).write_text(src, encoding="utf-8")
    (tree / "skills" / "probe" / "SKILL.md").write_text(
        f"---\nname: probe\ndescription: fixture\n---\n\n{body}\n", encoding="utf-8")
    return tree


def main() -> int:
    checks: list[tuple[str, bool]] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmpp = pathlib.Path(tmp)

        code, out = run(tree_with(tmpp, "Read `references/style-guide.md`."))
        checks.append(("a clean tree is green", code == 0))

        for label, body in BAD:
            code, out = run(tree_with(tmpp, body))
            checks.append((f"rejected: {label}", code == 1))

        for label, body in GOOD:
            code, out = run(tree_with(tmpp, body))
            checks.append((f"accepted: {label}", code == 0))

        # The property the fixtures above cannot supply on their own: that they
        # fail because of the patterns, not because of something else in the
        # checker. Blank the detector and every BAD case must sail through.
        blanked = "PATTERNS = []"
        missed = []
        for label, body in BAD:
            code, out = run(tree_with(tmpp, body, detector=blanked))
            if code != 0:
                missed.append(label)
        checks.append(
            ("every rejection is the detector's doing, not the harness's", not missed))

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
