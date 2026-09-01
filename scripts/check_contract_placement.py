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


def flat(text: str) -> str:
    """Whitespace-collapsed, for a phrase that may wrap across lines."""
    return " ".join(text.split())


def near(text: str, anchor: str, span: int = 300) -> str:
    """The window just after `anchor` — for a rule that must sit under a heading."""
    i = text.find(anchor)
    return "" if i < 0 else text[i : i + span]


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
        # A settlement record posted into a reserved thread is this workflow
        # answering it, not a reviewer follow-up. Without this, answering a
        # thread re-opens it and the answer is re-escalated forever.
        ("bo predicate: settlement records are not new content",
         "a write this workflow did not author" in bo_pred),
        ("ii predicate: settlement records are not new content",
         "a write this workflow did not author" in ii_pred),
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
        # A comment can want a diff and an answer at once. Repairable-only
        # resolves the thread with the question unanswered, and the gate then
        # reads the review as clean over it.
        ("resolve-pr-comment handles a comment wanting both", "### A comment can want both" in rc),
        ("the three-way split does not claim exclusivity",
         "not three boxes it must choose between" in flat(rc)),
        ("a mixed thread is repaired and still not resolved",
         "a reserved thread is never resolved at all" in flat(rc)),
        ("repair-pr's no-repair early return turns on absence of repair work",
         "no repair for this invocation to make" in flat(rp)),
        ("repair-pr's early return covers an acknowledgements-only round",
         "a round of nothing but acknowledgements qualifies" in flat(rp)),
        ("bo states NO_CODE_CHANGE as no repair to make, not all-questions",
         "left it no repair to make" in flat(bo)),
        ("ii states NO_CODE_CHANGE as no repair to make, not all-questions",
         "left it no repair to make" in flat(ii)),
        ("repair-pr leaves a mixed round's outcome to the budget",
         "the budget's answer, not the kind test's" in flat(rp)),
        ("repair-pr Output keeps a mixed thread's NEEDS_USER entry",
         "a mixed thread this pass also pushed a fix for" in rp),
        # Classify-only x mixed is a cross product: one thread, two items. An
        # Output keyed per thread has to drop one of them.
        ("repair-pr Output is keyed by item, not by thread",
         "items, not threads" in flat(rp)),
        ("bo records a two-item thread as handled only when both are in",
         "handled only when both are in" in flat(bo)),
        ("ii records a two-item thread as handled only when both are in",
         "handled only when both are in" in flat(ii)),
        # The mixed rule adds a classification case, not an exception to the
        # attended/unattended split: attended still answers in the thread.
        ("mixed comments follow the mode split for the prose half",
         "no exception to any mode rule" in flat(rc)),
        ("attended posts the substantive answer on a mixed comment",
         "Post the substantive answer in the thread" in rc),
        ("no mode resolves a mixed thread",
         "No mode resolves the thread" in flat(rc)),
        ("the mixed rule's repair half is scoped away from classify-only",
         "not* repaired under a classify-only invocation" in flat(rc)),
        ("repair-pr's mixed-round outcome is split by budget",
         "budget remaining" in rp and "budget zero" in rp),
        ("bo scopes never-auto-fixed to the part wanting an answer",
         "for the part that wants an answer" in bo),
        ("ii scopes never-repaired to the part wanting an answer",
         "in the part that wants an answer" in ii),
        # The prose branch must not list acknowledgements: the unattended
        # override turns that branch into NEEDS_USER, which settle cannot
        # qualify, so the thread holds the gate with nothing able to clear it.
        ("the prose branch excludes acknowledgements",
         "An acknowledgement is not this branch" in rc
         and "acknowledging something" not in clause(rc, "If a comment's correct response")),
        # resolve-pr-comment's own Output is the producer contract: the same
        # per-item, per-kind split the downstream contracts already have.
        ("resolve-pr-comment Output is keyed by item, not by thread",
         "items, not threads" in flat(clause(rc, "- **Every `NEEDS_USER` item", 2000))),
        ("resolve-pr-comment Output splits NEEDS_USER by item kind",
         "no draft" in near(rc, "- **Every `NEEDS_USER` item", 1600)),
        ("resolve-pr-comment Output names the two-entry mixed case",
         "mixed thread returns two entries" in flat(rc)),
        # A budget-deferred repair is not a question, so it carries no draft:
        # a draft is defined only for the two question shapes.
        ("repair-pr: budget-deferred item is a distinct kind with no draft",
         "deferred-repair item" in rp and "no draft" in rp),
        # repair-pr's own Output is a consumer site too: the caller only ever
        # sees what this bullet says to return.
        ("repair-pr Output splits NEEDS_USER entries by item kind",
         "no draft" in clause(rp, "- **every `NEEDS_USER` item", 3000)),
        ("bo records deferred-repair items without a draft", "deferred-repair item" in bo),
        ("ii records deferred-repair items without a draft", "deferred-repair item" in ii),
        # The callee's own workflow pushes, so a caller skipping its own
        # mutation steps does not constrain it. Only an explicit mode does.
        ("resolve-pr-comment has a classify-only mode", "### Classify-only invocations" in rc),
        ("classify-only gates the resolver's apply step at the step itself",
         "classify-only invocation" in near(rc, "### 3. Apply the fix(es)")),
        ("repair-pr passes classify-only into the resolver, not just to itself",
         "classify-only** mode where the remaining budget is zero"
         in clause(rp, "2. invoke `resolve-pr-comment`")),
        # A deferred repair carries no draft, so every site that reports a
        # reserved thread must split by kind or the case is unsatisfiable.
        ("bo reserved-thread report splits by item kind",
         "no draft" in clause(bo, "A thread classified `NEEDS_USER` is **reserved", 3000)),
        ("ii reserved-thread definition splits by item kind",
         "no draft" in clause(ii, "- A `NEEDS_USER` thread is **reserved", 3000)),
        ("ii structured result splits by item kind",
         "no draft" in clause(ii, "- review threads reserved for the owner", 2000)),
        ("ii checkpoint template splits by item kind",
         "no draft" in clause(ii, "Threads reserved for the owner: <count>")),
        # A draft lives only in a run report, which is a cache. Absent after a
        # restart it must not read as work nobody did, or the walkthrough the
        # owner ran to clear the thread declines the one item it could clear.
        ("settle: a missing draft is not the homework test",
         "A missing draft is not that test" in st),
        ("settle regenerates a lost draft rather than declining it",
         "then regenerate before applying this bullet" in flat(st)),
        ("bo names the draft as the enrichment a later walkthrough regenerates",
         "the draft reply attached to a reserved thread is exactly that"
         in bo.lower()),
        # Settle's two writes, and what retires a question.
        # A rejected-draft record that nothing reads prevents nothing: draft
        # regeneration is the one path that could recreate the discarded text.
        ("settle reads the rejected-draft record before regenerating",
         "read the thread's site for a rejected-draft record first" in flat(st)),
        ("settle never re-offers a rejected draft",
         "the same answer is not offered again" in flat(st)),
        ("settle names regeneration as the consumer of the rejection record",
         "Draft regeneration is what consumes this record" in flat(st)),
        ("bo's regeneration pointer names the record too",
         "reading any rejected-draft record there first" in flat(bo)),
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
        # Bundles must be caught in any option position, not only the first.
        "git push -q -uf origin main", "git push -v -unvf origin main",
        "git push --tags -uf origin main", "git push origin master --force",
        "git push origin master -f",
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
    checks.append(("README documents all three deny residuals",
                   "Three residuals are left in on purpose" in readme
                   and "git push -unvvvvvvvvvf" in readme
                   and "git push +prod HEAD:main" in readme))

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
