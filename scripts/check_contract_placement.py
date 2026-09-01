#!/usr/bin/env python3
"""Assert that cross-skill contract rules sit at the site that reads them.

`check_skills.py` validates that a cross-reference resolves to some heading.
This checks something it cannot: that a rule which must appear at a specific
decision point actually does, and that a chain of skills forwards what the next
one records.

Why this exists rather than a grep: a rule present in a file but stated in the
wrong clause reads as correct to a grep and is inert in practice. Two review
rounds on this repo were spent on exactly that — an exception written into a
step body that a predicate had already excluded the thread before reaching, and
a `no-action` classification produced by one skill that the skill between it and
its recorder never forwarded. Presence in a file is not presence at the
decision point.

The deny-pattern assertions are here for a related reason: a permission glob
argued about in prose ships bugs. `Bash(git push -*f)` looks like it matches a
bundled force flag and also matches `git push -u origin ref`, because `*` spans
spaces in fnmatch. Assert the matrix instead.
"""

from __future__ import annotations

import fnmatch
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def skill(name: str) -> str:
    return (ROOT / "skills" / name / "SKILL.md").read_text()


def clause(text: str, anchor: str, span: int = 700) -> str:
    """The single line beginning at `anchor` — the clause, not the file."""
    i = text.find(anchor)
    return "" if i < 0 else text[i : i + span].split("\n")[0]


def main() -> int:
    bo = skill("backlog-orchestrator")
    ii = skill("implement-issue")
    st = skill("settle-outstanding-decisions")
    rp = skill("repair-pr")
    rc = skill("resolve-pr-comment")

    bo_pred = clause(bo, "On unhandled review feedback")
    ii_pred = clause(ii, "On unhandled feedback")

    checks: list[tuple[str, bool]] = [
        # The unhandled predicates. Both conditions must be in the predicate
        # itself: a predicate that excludes a thread never reaches the step
        # body that would have re-admitted it.
        ("bo predicate: handled is reserved or no-action", "reserved or no-action" in bo_pred),
        ("ii predicate: handled is reserved or no-action", "reserved or no-action" in ii_pred),
        ("bo predicate: new-content exception", "new content has arrived on it since" in bo_pred),
        ("ii predicate: new-content exception", "new content has arrived on it since" in ii_pred),
        # Classification is dispatchable with the repair budget spent.
        ("bo dispatch ungates classification",
         "gates repairing, not classifying" in clause(bo, "2. allocate an isolated checkout")),
        ("ii dispatch ungates classification",
         "gates repairing, not classifying" in clause(ii, "2. invoke `repair-pr` once")),
        ("repair-pr enforces a zero budget", "classify-only invocation" in rp),
        # A no-op pass must not ask for another review of identical code.
        ("bo retrigger is push-conditional", clause(bo, "6. **only where the pass pushed a repair**") != ""),
        ("ii retrigger is push-conditional", clause(ii, "4. **only where the pass pushed a repair**") != ""),
        # The no-action chain. Every link, because a missing middle link is
        # silent: the pass looks clean and the thread never stops returning.
        ("chain 1/4: resolve-pr-comment classifies no-action", "A comment that wants nothing" in rc),
        ("chain 2/4: resolve-pr-comment returns no-action entries", "Any thread classified no-action" in rc),
        ("chain 3/4: repair-pr forwards no-action entries", "every thread classified no-action" in rp),
        ("chain 4/4: both orchestrators record no-action threads",
         "no-action thread it returned" in bo and "no-action thread it returned" in ii),
        # Settle's two writes, and what retires a question.
        ("settle requires the approved answer text", "the approved or edited answer text itself" in st),
        ("settle zero-output keys on authored writes", "no authored write of any kind" in st),
    ]

    # Every write-absolute must name the second write kind, or it silently
    # forbids a record another section requires.
    absolute = re.compile(
        r"[^.\n]*\b(the one write|its one write|only write|the only writes?|writes only"
        r"|never writes|sole write)\b[^.\n]*\.",
        re.I,
    )
    stale = [
        m.group(0).strip()
        for m in absolute.finditer(st)
        if "rejected-draft" not in m.group(0)
    ]
    checks.append(("settle write-absolutes name the rejected-draft record", not stale))

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
    ]
    # Every entry here is a command that a previous version of this file broke.
    must_allow = [
        "git push --force-with-lease origin feat", "git push --force-with-lease",
        "git push -u origin main", "git push -u origin ref", "git push -u origin wip-perf",
        "git push -u origin my-branch-f", "git push -u origin claude/fix-auth-conf",
        "git push -u origin feature+metrics", "git push origin release+rc1",
        "git push origin hotfix", "git push -u origin perf main", "git push -n origin main",
    ]
    for c in must_deny:
        checks.append((f"deny: {c}", denied(c)))
    for c in must_allow:
        checks.append((f"allow: {c}", not denied(c)))

    failures = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS " if ok else "FAIL ") + name)
    if stale:
        print("\nwrite-absolutes not naming the rejected-draft record:")
        for s in stale:
            print("  " + s[:160])
    print(f"\n{len(checks) - len(failures)}/{len(checks)} passing")
    if failures:
        print("\nFAILED:")
        for f in failures:
            print("  " + f)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
