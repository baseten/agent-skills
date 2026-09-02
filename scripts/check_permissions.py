#!/usr/bin/env python3
"""Assert what `permissions.json` actually does, and that the README says so.

A permission glob argued about in prose ships bugs. `Bash(git push -*f)` looks
like it matches a bundled force flag and also matches `git push -u origin ref`,
because `*` spans spaces in fnmatch. So the deny list is asserted as a matrix of
commands rather than reasoned about, and every must-allow case below is a command
some earlier version of this file broke.

The README assertions exist for a sharper reason: a check that quotes a claim's
wording instead of testing its substance turns a mistake into a protected
invariant. This file shipped a README sentence calling post-refspec options an
uncovered residual while the shipped globs covered them, and an assertion held
that sentence in place. Where a claim is mechanically checkable, check it by
running the globs; where it is not, key on the discriminator and not the phrasing.
"""

from __future__ import annotations

import fnmatch
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main() -> int:
    checks: list[tuple[str, bool]] = []

    # Deny-pattern behaviour, asserted rather than argued.
    deny = [e[5:-1] for e in json.loads((ROOT / "permissions.json").read_text())["deny"]
            if e.startswith("Bash(")]

    def denied(command: str) -> bool:
        return any(fnmatch.fnmatch(command, p) for p in deny)

    must_deny = [
        "git push -f origin main", "git push --force origin main", "git push -uf origin main",
        "git push -unvf origin main", "git push -unvvf origin HEAD:main",
        "git push -unvvvvvf origin main", "git push origin +HEAD:master",
        "git push -u origin +feat:main", "git reset --hard HEAD~1", "git clean -fdx",
        # Bundles must be caught in any option position, not only the first.
        "git push -q -uf origin main", "git push -v -unvf origin main",
        "git push --tags -uf origin main", "git push origin master --force",
        "git push origin master -f",
        # Options past the refspec. Once wrongly documented as uncovered; the
        # space-spanning `*` catches them, and the README says so now.
        "git push origin -uf", "git push origin main -uf", "git push origin main -uqf",
    ]
    # Every entry here is a command that a previous version of this file broke.
    must_allow = [
        "git push --force-with-lease origin feat", "git push --force-with-lease",
        "git push -u origin main", "git push -u origin ref", "git push -u origin wip-perf",
        "git push -u origin my-branch-f", "git push -u origin claude/fix-auth-conf",
        "git push -u origin feature+metrics", "git push origin release+rc1",
        "git push origin hotfix", "git push -u origin perf main", "git push -n origin main",
        "git push origin feature--force", "git push -u origin my-f",
        "git push origin feat --force-with-lease",
    ]
    # The enumerated depth. fnmatch has no bounded repetition, so the ceiling
    # cannot be removed — only stated. Assert where it actually falls, and that
    # the README documents it, so it stops being an unnoticed hole.
    must_deny.append("git push -vvvvvvvvf origin main")  # 8 letters: the last covered
    for c in must_deny:
        checks.append((f"deny: {c}", denied(c)))
    for c in must_allow:
        checks.append((f"allow: {c}", not denied(c)))

    # The README's "tool-name rules only" claim is about `allow`. Assert that it
    # stays true of `allow` and that `deny` is not silently emptied to match it.
    perms = json.loads((ROOT / "permissions.json").read_text())
    readme = (ROOT / "README.md").read_text()
    checks.append(("allow list has no Bash entries",
                   not any(e.startswith("Bash(") for e in perms["allow"])))
    checks.append(("deny list still has Bash entries",
                   any(e.startswith("Bash(") for e in perms["deny"])))
    checks.append(("README scopes the tool-name claim to the allow list",
                   "**The `allow` list holds tool-name rules only" in readme))
    checks.append(("deny depth ceiling is where the README says it is",
                   not denied("git push -vvvvvvvvvf origin main")))
    checks.append(("README states what dropping the shell rules costs outside auto mode",
                   "### What dropping the shell rules costs outside auto mode" in readme
                   and "loses them on its next" in readme))
    checks.append(("README documents both deny residuals",
                   "Two residuals are left in on purpose" in readme
                   and "git push -unvvvvvvvvvf" in readme
                   and "git push +prod HEAD:main" in readme))
    checks.append(("README does not claim post-refspec options are uncovered",
                   "Options written *after* the refspec are covered" in readme))

    failures = [name for name, ok in checks if not ok]

    failures = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS " if ok else "FAIL ") + name)
    print(f"\n{len(checks) - len(failures)}/{len(checks)} passing")
    if failures:
        print("\nFAILED:")
        for f in failures:
            print("  " + f)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
