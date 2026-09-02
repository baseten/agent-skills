#!/usr/bin/env python3
"""Assert the shape of `permissions.json`, and that the README describes it.

The file holds tool-name allow rules and nothing else. Both halves of that are
load-bearing and both were arrived at the hard way, so both are asserted here.

`allow` carries no `Bash(...)` entries: auto mode already permits the ordinary
work these skills do, and a shell rule ending in `*` admits arbitrary trailing
arguments.

`deny` is empty. It once held nineteen entries, every glob asserted against real
commands because prose about globs ships bugs — and it still produced five false
positives against no incident it is known to have prevented. A deny rule is the
only part of this file that can stop a command in *every* mode, so its bugs
break real work while its benefit is confined to `bypassPermissions`. The
emptiness is asserted so that re-adding one is a deliberate edit to this check
as well, which is where the command matrix would have to come back.

The README assertions exist for a sharper reason: a check that quotes a claim's
wording instead of testing its substance turns a mistake into a protected
invariant. This file once carried a README sentence calling post-refspec options
an uncovered deny residual while the shipped globs covered them, and an
assertion held that sentence in place. Key on the discriminator, not the phrasing.
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main() -> int:
    perms = json.loads((ROOT / "permissions.json").read_text())
    readme = (ROOT / "README.md").read_text()
    flat = " ".join(readme.split())

    checks: list[tuple[str, bool]] = [
        ("allow list has no Bash entries",
         not any(e.startswith("Bash(") for e in perms["allow"])),
        ("allow list is not empty",
         len(perms["allow"]) > 0),
        ("every allow entry is a bare tool name — no arguments to ride in on",
         all("(" not in e for e in perms["allow"])),
        # Re-adding a deny rule means re-adding the command matrix that used to
        # guard it; failing here is the reminder, not an obstacle.
        ("deny list is empty",
         perms.get("deny") == []),
        ("README says the file is allow-only",
         "This file holds tool-name allow rules and nothing else" in flat),
        ("README explains why there is no deny list",
         "### There is no deny list" in readme),
        ("README names bypassPermissions as the gap that is knowingly accepted",
         "where a deny rule genuinely is the only thing still evaluated" in flat),
        ("README states what dropping the shell rules costs outside auto mode",
         "### What dropping the shell rules costs outside auto mode" in readme
         and "loses them on its next" in flat),
        ("README documents the container verification probe",
         "CronCreate" in readme and "refuses to approve itself under auto" in flat),
    ]

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
