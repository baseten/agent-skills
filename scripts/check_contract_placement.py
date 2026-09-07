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

The deny matrix and the README's claims about it live in `check_permissions.py`;
this file is only about the skill contracts.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def skill(name: str) -> str:
    return (ROOT / "skills" / name / "SKILL.md").read_text()


# A rule statement in these contracts is a bold lead-in; counting those is how
# a duplicate rule is detected without matching its wording.
BOLD = re.compile(r"\*\*(.+?)\*\*", re.S)


FINDINGS = ("licence", "cooldown", "peer")

# A blank line, or the start of a list item. Markdown structure, decided by
# layout alone — no terminator, no capitalisation, no vocabulary. See
# `names_all_three_findings` for why the sentence unit was abandoned for it.
BLOCK_BOUNDARY = re.compile(r"\n\s*\n|\n(?=[ \t]*(?:[-*+]|\d+[.)])[ \t])")


def _routine_bullets() -> list[str]:
    """The routine batch's directive bullets, extracted rather than listed.

    The obligations this route cannot inherit are stated as a bullet list, and
    three rounds running a guard over them was a list of literal phrases — so
    a bullet added without its disposition passed. Extracting them means the
    guard can assert an arity: one disposition entry per bullet, checked
    positionally. Adding a bullet is then a change the check notices.
    """
    text = skill("dependency-upgrade-orchestrator")
    start = text.index("**The routine batch runs no named contract")
    end = text.index("\n\nSupply each agent with the completed triage", start)
    return [b.strip() for b in text[start:end].split("\n- ")[1:]]


ROUTINE_BULLETS = _routine_bullets()

# One entry per bullet, in order: the disposition that bullet must carry —
# what the agent does when its check comes back positive. A bullet may satisfy
# its entry by any one of several phrasings. This is the fixture; the arity
# check above it is the property.
ROUTINE_DISPOSITIONS = [
    # in-flight search: what a hit removes, and what is not a hit at all
    ("removes that candidate",
     "An automated bump PR for a batched package is not that"),
    # adopted PR state: a disposition per outcome it names
    ("verify against the installed version and report it",
     "take the successor on the same terms"),
    # lockfile base record: the value is not the record without them
    ("with both qualifiers that make it safe",),
    # target re-check: operand, whose decision it is, and the blast radius
    ("what moves a target is an adopted PR's head advancing",
     "is not this agent's to re-triage or re-route",
     "the rest of the batch is not void with it"),
]


def eval_names(skill_name: str) -> list[str]:
    f = ROOT / "skills" / skill_name / "evals" / "evals.json"
    if not f.exists():
        return []
    return [c.get("name", "") for c in json.loads(f.read_text(encoding="utf-8")).get("evals", [])]


def eval_assertions(skill_name: str, case: str) -> list[str]:
    """One scenario's assertions as a list, never joined.

    Joining them makes consecutive entries read as one block, and any
    block-scoped rule then fires on an artifact of the join rather than on the
    text. Read as a list, each assertion is its own block, which is what it is.
    """
    f = ROOT / "skills" / skill_name / "evals" / "evals.json"
    if not f.exists():
        return []
    for c in json.loads(f.read_text(encoding="utf-8")).get("evals", []):
        if c.get("name") == case:
            return list(c.get("assertions", []))
    return []


def names_all_three_findings(text: str) -> bool:
    """True where one paragraph or list item names licence, cooldown and peer.

    The convention is that **an oracle states the two rules as two**: licence
    and cooldown are per package, the peer finding is a relation over the whole
    target tuple, and a text presenting them as one rule is the shape every
    contradiction on this PR grew from. What changed three times is the unit
    that "as two" is measured in, and the history is the argument for where it
    landed.

    It was a sentence, and a sentence could not be decided. Round 26: the split
    broke on `;` and `:`, so "Per package, reuse licence and cooldown; under
    that same rule, reuse peer too." read as two compliant halves. Round 27: an
    abbreviation did the same job at `e.g. `, which was fixed by requiring a
    sentence *start* rather than by listing abbreviations — a version number
    has the identical property and no list would have held it. Round 28 ended
    the approach rather than extending it: "...for e.g. **unchanged targets**,
    and reuse peer under the same rule." splits at `g.` because `*` reads as a
    sentence start.

    That last one is a proof, not another instance. Markup must be able to
    start a sentence — `**Peer** is a relation over the tuple.` is ordinary
    oracle prose, and a fixture required it — and markup must not be able to
    fake one. No character class satisfies both, so the unit was wrong.

    A **block** — a paragraph or a list item — is decided by layout alone. No
    terminator, no capitalisation, no vocabulary, nothing an oracle's wording
    can spoof. It is the third time on this contract that an open-ended
    natural-language problem has been answered by ceasing to solve it, after
    `prescribes()` at round 10 and `groups_peer_per_package()` at round 25, and
    it is the first of the three whose replacement has no residual an author
    can trip over unknowingly.

    The price, stated plainly because it is real: this is **stricter** than the
    sentence rule and rejects prose that reads perfectly well. "Licence and
    cooldown are measured per package. Peer resolution is a relation over the
    tuple." was a compliant oracle a round ago and is a violation now. That is
    the difference between a heuristic's false positive and a convention's
    demand — one is unfixable by the author, who cannot see why it fired, and
    the other is mechanical: put the second rule in its own bullet. Conforming
    the corpus cost three oracles, each of which already carried the two rules
    under labels ("Per package:" / "Group-wide:") and now carries them as two
    list items, which is how they should have been written.

    Residual, unchanged from the sentence version and no worse: an oracle
    spread over two blocks that still means per-package peer reuse passes.
    Deciding *that* is the parsing problem two deleted detectors failed at.

    Do not `flat` the text first — that collapses every block into one and the
    guard fires on the whole corpus. The GOOD fixtures fail if it is added.
    """
    return any(all(f in block.lower() for f in FINDINGS)
               for block in BLOCK_BOUNDARY.split(text))


def notes(name: str) -> str:
    """A skill's NOTES.md. It restates the rules it explains, so it drifts like
    any other restatement — one review round on this repo was spent on a rule
    the contract had already fixed, still standing in the note beside it.
    Prefer a PRESENCE check on the corrected rule over an absence check on the
    old one: NOTES legitimately quotes superseded wording when recording why it
    was superseded, so absence cannot tell drift from history.
    """
    f = ROOT / "skills" / name / "NOTES.md"
    return f.read_text(encoding="utf-8") if f.exists() else ""


def eval_expected(name: str) -> list[str]:
    """Every scenario's expected answer — the only eval field that PRESCRIBES.

    Evals restate the rules they pin, so they go stale exactly as a second
    copy in prose does — and a stale one is worse than a stale paragraph,
    because it actively rewards a rewrite that reintroduces the defect. One
    review round on this repo was spent on a scenario still carrying the
    ownerless instruction the round before it had removed from the contract.
    They are part of the consequence sweep, not a separate artifact.

    Scope matters in both directions and they are not symmetric:

    * PRESENCE must scope to the field that has to carry the requirement —
      see `eval_field`. A whole-file check accepts the phrase anywhere,
      including inside the assertion meant to be testing for it.
    * ABSENCE must scope to the fields that could *instruct* the behaviour.
      A whole-file check conflates use with mention: a scenario whose prompt
      quotes a forbidden instruction so the model can reject it, or whose
      assertion requires that rejection, is the guard working, not failing.
      Only the expected answer tells the model what to do.
    """
    f = ROOT / "skills" / name / "evals" / "evals.json"
    if not f.exists():
        return []
    return [
        c.get("expected_output", "")
        for c in json.loads(f.read_text(encoding="utf-8")).get("evals", [])
    ]


def states_rather_than_restates(name: str, phrase: str) -> bool:
    """True when no scenario's expected answer contains `phrase` at all.

    This replaces three rounds of natural-language negation detection, and the
    replacement is the point rather than a retreat. The heuristic had to decide
    whether an occurrence was an instruction or a rejection of one, and four
    review rounds produced four constructions it got wrong — a negation from
    the neighbouring sentence, then from the neighbouring clause, then a
    coordinated disjunction it wrongly split, then comma-separated imperatives
    it wrongly joined. Fixing that last one requires treating a bare comma as
    a clause break, which immediately misreads "do not merge, or re-resolve
    ...", a sentence English does not disambiguate either. The surface signals
    were exhausted, and each round's fix bought one construction and cost
    another.

    So the check is on a property that is decidable: an expected answer states
    what it requires and never restates what it rejects. That is a real
    authoring convention rather than a device to satisfy a checker — every
    scenario in these two skills already read that way when it was introduced,
    with no text changed to satisfy it, because the
    wrong instruction belongs in the prompt, where a colleague suggests it,
    and the assertions are free to name it. Only the expected answer is
    constrained, and that is the field that teaches.

    What this gives up, said plainly: a paraphrase ("defer the re-resolution
    to merge time") is not caught. Neither was it by the heuristic, which also
    carried an undecidable class. The scenario that actually pins this rule is
    held by the two field-scoped presence checks below, which require the
    handoff record and its expiry positively.
    """
    return not any(phrase.lower() in e.lower() for e in eval_expected(name))


def eval_field(skill_name: str, case: str, field: str) -> str:
    """One field of one named scenario — the scope every PRESENCE check needs.

    Asserting a required phrase against the whole file passes when the phrase
    sits in any field, so a requirement dropped from `expected_output` stays
    green as long as an assertion still happens to mention it. The round that
    added the corpus check shipped exactly that: its "the scenario requires
    the handoff record" assertion matched only the assertion text, and the
    expected answer it was written to pin never contained the phrase at all.
    A presence check must name the field that has to carry the requirement.

    Returns "" for a missing skill, scenario or field, so a renamed or deleted
    scenario fails the check rather than silently satisfying it.
    """
    f = ROOT / "skills" / skill_name / "evals" / "evals.json"
    if not f.exists():
        return ""
    for c in json.loads(f.read_text(encoding="utf-8")).get("evals", []):
        if c.get("name") == case:
            v = c.get(field, "")
            return flat(v if isinstance(v, str) else " ".join(v))
    return ""


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
    sm = skill("summarize-tranche")
    rp = skill("repair-pr")
    rc = skill("resolve-pr-comment")
    ud = skill("upgrade-major-dependency")
    du = skill("dependency-upgrade-orchestrator")

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
        # The recorded states name only the two outcomes that leave a thread
        # open, so a predicate listing them alone re-groups every fixed thread.
        ("bo predicate: a resolved thread is handled", "still unresolved" in bo_pred),
        ("ii predicate: a resolved thread is handled", "still unresolved" in ii_pred),
        # NEEDS_USER is an outcome for ci/finding evidence and an item kind for a
        # review thread. The caller branches on the outcome, so conflating them
        # marks the whole PR NEEDS_USER and the run never settles.
        ("repair-pr scopes the NEEDS_USER outcome away from review threads",
         "it is a `NEEDS_USER` **item** carried" in flat(rp)),
        # Settle's bar takes choices, not work, so it cannot clear a deferred repair.
        ("bo does not claim settle consumes deferred repairs",
         "does not consume a deferred repair" in flat(bo)),
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
        # A deferred repair is an item under NO_CODE_CHANGE, never a PR-level
        # NEEDS_USER outcome. Both readings were live in one file: the summary
        # path then had no rule for it and either dead-ended or looped.
        ("bo interruption clause distinguishes outcome from item",
         "item on a review thread is never an interruption" in flat(bo)),
        ("bo budget-exhaustion rule names the review budget's item form",
         "as **items** where a review budget is" in flat(bo)),
        ("bo dispatch step calls a deferred repair an item, not an outcome",
         "never a `NEEDS_USER` outcome for the PR" in flat(bo)),
        ("ii budget-exhaustion step names items, not an outcome",
         "never a `NEEDS_USER`\n   outcome for the PR" in ii or
         "never a `NEEDS_USER` outcome for the PR" in flat(ii)),
        ("summarize-tranche excludes only reserved threads with no dispatch",
         "with nothing able to dispatch it is never `IN_FLIGHT_FIX`" in flat(sm)
         and "as `MERGE_RISK`" in flat(sm)),
        ("summarize-tranche says the ruling survives a restart, not the reservation",
         "What survives is the ruling, not the reservation" in flat(sm)),
        ("summarize-tranche emits a code-changing ruling as IN_FLIGHT_FIX",
         "The test is the absence of a dispatch, not the reservation" in flat(sm)
         and "whose change has not been pushed** is `IN_FLIGHT_FIX`" in flat(sm)),
        ("bo finding shape excludes only threads with no dispatch",
         "not a source of an `IN_FLIGHT_FIX` where nothing can dispatch it" in flat(bo)
         and "recorded code-changing ruling is the exception" in flat(bo)),
        ("ii un-settling excludes only threads with no dispatch",
         "with nothing able to dispatch it" in flat(ii)
         and "recorded code-changing ruling un-settles as it always did" in flat(ii)),
        # A gate condition with no termination rule holds after the owner answers.
        ("bo states what ends a reservation, and that it is run state",
         "A reservation is run state" in flat(bo)
         and "does not survive one" in flat(bo)),
        ("bo makes lifting the budget actionable",
         "repairs it where it now has budget" in flat(bo)),
        ("bo counts the owner's own reply as ending a reservation",
         "or the owner's own reply in the thread" in flat(bo)),
        # Settle's two writes, and what retires a question.
        # A rejected-draft record that nothing reads prevents nothing: draft
        # regeneration is the one path that could recreate the discarded text.
        ("settle reads the record on the regenerate path too",
         "do that read first, then regenerate" in flat(st)),
        ("settle never re-offers a rejected draft",
         "the same answer is not offered again" in flat(st)),
        # A model reading this reliably inverted it: regeneration surfaced that
        # the codebase answers the question, so it declined it as homework.
        ("settle preserves the kind a regenerated draft was given",
         "A regenerated draft keeps whichever kind regenerating it produced" in flat(st)),
        ("settle's carve-out covers only the answerable-from-work kind",
         "the carve-out above covers only the first" in flat(st)),
        ("settle forbids regeneration making an item homework",
         "Regeneration cannot turn an item into homework" in flat(st)),
        ("settle names offering, not regenerating, as the record's consumer",
         "Offering a draft is what consumes this record" in flat(st)),
        ("bo's regeneration pointer names the record too",
         "reading any rejected-draft record there first" in flat(bo)),
        ("settle requires the approved answer text", "the approved or edited answer text itself" in st),
        ("settle zero-output keys on authored writes", "no authored write of any kind" in st),
        # The dependency-upgrade chain. The orchestrator's triage clears a
        # candidate; the agent's own viability gate then re-derives the same
        # conclusions from a narrower scope and reaches a *stop*. Every triage
        # output the gate can contradict has to be forwarded AND read at the
        # gate — presence in the dispatch prose is not presence at the gate.
        ("dependency dispatch forwards the verdict, a per-package target, and the coupled set",
         "the exact target version it measured for every package in the task"
         in flat(clause(du, "Supply each agent with the completed triage", 2000))),
        # A coupled task's members can sit on different version lines, so one
        # figure cannot say which version each finding measured.
        ("the target mapping covers every coupled member",
         "One target for the task is not enough" in flat(du)
         and "package → triaged target" in flat(du)),
        # The consumer is required to compare current target against triaged
        # target. A rule whose operand is never forwarded cannot fire, and the
        # failure is silent: reusing a stale clearance looks like compliance.
        ("the producer names why the target must travel with the verdict",
         "It cannot run that comparison against a version this dispatch never named"
         in flat(du)),
        ("dependency dispatch says why those two specifically",
         "reaches a different answer without them" in flat(du)),
        ("an automated bump PR is the work, not work already in flight",
         "never work already in flight — it is the work" in flat(du)),
        ("the orchestrator's viability item exempts any automated bump PR",
         "other than an automated bump PR for this candidate"
         in flat(clause(du, "**Viability** —", 2000))),
        # Source-conditional here and source-agnostic in the worker is the same
        # producer/consumer disagreement, one clause deeper.
        ("the adoption note defines a duplicate by what the work is",
         "somebody else's attempt at the same upgrade"
         in flat(clause(notes("dependency-upgrade-orchestrator"),
                        "The adoption rule itself is not merely an exemption", 1200))),
        ("the exemption does not turn on the discovery source",
         "Where the candidate came from does not enter into this" in flat(du)
         and "whatever discovery source produced the candidate" in flat(du)),
        ("the orchestrator's peer-cap item is scoped to the coupled group",
         "established before this item is answered" in flat(clause(du, "**Viability** —", 2000))),
        # A supplied verdict is a snapshot. Most of it cannot go stale; the
        # work-in-flight item can, and bounded concurrency is what makes the
        # gap long enough to matter.
        ("a moved target ends the task rather than reshaping it",
         "A moved target ends this task; it does not reshape it" in flat(ud)
         and "what survives is identity only" in flat(ud)
         and "even when a caller supplied a viability verdict clearing it"
         in flat(clause(ud, "- **Work already in flight.**", 2000))),
        # A worker cannot revise its own model assignment, so re-deriving the
        # research and continuing is the one outcome the selection rule exists
        # to prevent — a mid-tier agent implementing a silent-failure release.
        ("the stop is justified by the two caller decisions, model included",
         "the model this task is running under" in flat(ud)
         and "an agent cannot revise its own assignment" in flat(ud)),
        ("the re-reading serves the report, not the continuation",
         "The re-reading serves the report, not the continuation" in flat(ud)),
        ("Report hands back a per-package mapping, symmetric with dispatch",
         "package → current target mapping for every package that moved"
         in flat(clause(ud, "A task ended by a moved target", 900))),
        # The stop is on the move, not on the set changing — an oracle that
        # conditions it lets an answer continue under a stale model.
        # An oracle that opens by discarding every cached finding and then
        # exempts one contradicts itself, and the assertions decided neither
        # way — so a rewrite could be rewarded for either behaviour.
        ("the moved-companion oracle gives one answer on unchanged findings",
         "stay valid" in eval_field("upgrade-major-dependency",
                                    "a-moved-companion-voids-the-whole-groups-peer-clearance",
                                    "expected_output")
         and "rather than discarding every cached finding"
         in eval_field("upgrade-major-dependency",
                       "a-moved-companion-voids-the-whole-groups-peer-clearance",
                       "assertions")),
        ("an oracle makes the moved-target stop unconditional",
         # Both fields, because they can disagree: this checked only the
         # assertions, so the expected answer — the one field that PRESCRIBES,
         # per `eval_expected` — could teach "(b) the set is unchanged, so the
         # task continues" while the assertion beside it still graded the stop.
         # The grading field disagreeing with the teaching field is worse than
         # either being stale alone.
         "The stop is on the target having moved, not on the membership having changed"
         in flat(eval_field("upgrade-major-dependency",
                            "an-advanced-target-can-change-the-coupled-set",
                            "expected_output"))
         and "the set is unchanged and the answer is the same stop"
         in flat(eval_field("upgrade-major-dependency",
                            "an-advanced-target-can-change-the-coupled-set",
                            "expected_output"))
         and "including the one where the recomputed coupled set is unchanged"
         in eval_field("upgrade-major-dependency",
                       "an-advanced-target-can-change-the-coupled-set", "assertions")
         and "unconditionally, whatever the recomputed coupled set turns out to be"
         in eval_field("upgrade-major-dependency",
                       "a-supplied-verdict-does-not-cover-work-in-flight",
                       "expected_output")),
        ("the producer's return contract names the same mapping",
         "package → current target mapping for every package that moved"
         in flat(clause(du, "**Expect that stop on any moved target", 2000))),
        # An advanced bot PR can move the target, which invalidates exactly the
        # three findings a verdict is most trusted for.
        ("a moved target re-runs the per-package gate items for that package",
         "Compare each package's current target against the one triage measured for it"
         in flat(ud)
         and "only while that package's target is the one it measured for it"
         in flat(near(ud, "## Viability gate", 500))),
        # Peer viability is a relation over the whole target tuple, not a
        # property of one package: a member advancing can void another
        # member's clearance while that member's own target sits unchanged,
        # so every individual clearance reads valid and the combination was
        # never checked.
        # An oracle that groups peer with licence and cooldown under a
        # per-package comparison rewards exactly the behaviour eval 14 and the
        # contract reject. Every contradiction on this PR about these three
        # findings grew from a text listing them together, so the rule is that
        # an oracle states the two rules as two — a property that needs no
        # parsing. Which UNIT of text took three rounds to settle: 26 found
        # this assertion green over a semicolon, 27 over an abbreviation, 28
        # over markup faking a sentence start. It is a paragraph or list item
        # now, documented and fixtured at `names_all_three_findings`.
        ("no eval oracle names all three findings in one block",
         not any(names_all_three_findings(e)
                 for sk in ("upgrade-major-dependency", "dependency-upgrade-orchestrator")
                 for e in eval_expected(sk))
         and not any(names_all_three_findings(a)
                     for sk in ("upgrade-major-dependency", "dependency-upgrade-orchestrator")
                     for n in eval_names(sk)
                     for a in eval_assertions(sk, n))),
        ("peer resolution and the coupled set are voided task-wide",
         "relations over the targets rather than properties of one" in flat(ud)
         and "only while no member's target has moved at all"
         in flat(near(ud, "## Viability gate", 600))),
        # Coupling is DERIVED from peer requirements at the targets, so a move
        # can change task membership — which the worker must not decide.
        # NOTES records superseded rules on purpose, so the guard is not
        # absence of the old wording but that every statement of it is MARKED
        # superseded. Four rounds were spent on intermediate versions of one
        # rule reading as live prose in a changelog-shaped note.
        ("the worker's notes state the superseded rules as superseded",
         "worth recording as **superseded**" in flat(notes("upgrade-major-dependency"))
         and "nothing survives but identity" in flat(notes("upgrade-major-dependency"))),
        ("no unmarked survival claim for the coupled set remains in the notes",
         "the coupled set is about which packages move together and survives"
         not in flat(notes("upgrade-major-dependency"))
         and "cannot go stale — a licence, a publication date, a peer's published ranges, the coupled set"
         not in flat(notes("upgrade-major-dependency"))),
        ("membership is named as a caller decision, not the worker's",
         "the decisions built on that triage are the caller's, not this task's" in flat(ud)
         and "report and stop" in flat(ud)),
        ("the producer expects the stop on any moved target, not just a changed set",
         "Expect that stop on any moved target, not only a changed set" in flat(du)
         and "cannot revise its own model assignment" in flat(du)),
        ("the producer expects that report and owns membership",
         "Coupling is target-derived too" in flat(du)
         and "reports and stops rather than reshaping its own task" in flat(du)
         # The phrase alone is not the rule: round 19's conditional wrapped it
         # ("and, finding it different, reports and stops…") and round 29
         # removed the wrapper while leaving a guard blind to its return.
         and "on the move itself, whether or not the set came out different"
         in flat(du)),
        ("the peer-cap gate item says a supplied clearance dies group-wide",
         "dies as soon as **any** member's target moves"
         in flat(clause(ud, "- **Peer caps.**", 3000))),
        ("a moved target voids a routine clearance and its routing",
         "A routine clearance is about one release" in flat(du)
         and "the route it chose has no viability gate in it" in flat(du)),
        ("the target rule reaches the research and the audit, not just the gate",
         "licence, install cooldown, breaking-change research and usage audit"
         in flat(ud)
         and "Supplied research is reusable on the same condition" in flat(ud)),
        ("the producer states the peer exception to per-package",
         "The peer finding is the exception to per-package" in flat(du)),
        # The cherry-pick is the two-branch mechanism, not the rule; with one
        # branch the test commit is already an ancestor.
        ("the phase states the ordering as the invariant, not the cherry-pick",
         "What is invariant is the ordering, not the mechanism" in flat(ud)
         and "the bump goes on top instead, and no second worktree is cut"
         in flat(ud)),
        # A PR's URL is stable and everything else about it is not. The
        # in-flight search cannot cover this: it sees open work, and the
        # dangerous case is the adopted PR having merged.
        ("the adopted PR's state is refreshed, not taken from the verdict",
         "identity and does not change; nothing else about it is given"
         in flat(ud)
         and "read the PR itself before branching from it" in flat(ud)),
        # A group is adopted per candidate and can arrive with several PRs,
        # while every consumer below it was written for one. The rule names
        # which is the branch and which two things read over all of them.
        ("the adopted-PR arity is stated, with the two rules that read over all of them",
         # Scoped to the worktree cases. Whole-file, this passed with the whole
         # paragraph relocated to an appendix — and NOTES says the placement is
         # the point.
         "**Adopt exactly one as the branch"
         in flat(near(ud, "Work in a dedicated worktree", 2600))
         and "any** adopted PR's head advancing can move its own package's target"
         in flat(ud)
         and "every** adopted PR's URL is identity that survives a moved target"
         in flat(ud)
         and "What moves a target is an adopted PR's head" in flat(ud)),
        ("the orchestrator does not present the verdict as covering either",
         "must not be presented as though it does" in flat(du)
         and "as identity rather than as a state" in flat(du)),
        # The rationale for forwarding the adopted PR was removed in round
        # seven; the sites asserting it outlived it by three rounds.
        ("dispatch no longer justifies the adopted PR by a wrong stop",
         "supplied as identity rather than to prevent a wrong stop" in flat(du)),
        # Keyed on what the rule turns on — reuse scoped to facts, not items —
        # because the item-level phrasing this replaced was itself required by
        # an assertion, which is how a contradiction survived a round.
        # One statement of the reuse rule, not a summary above the real one:
        # the summary drifted from the rule below it within a single round.
        # The failure shape here is duplication, so the guard counts rather than
        # matching a phrase — and it counts the SHAPE a rule statement takes in
        # these files (a bold lead-in) rather than one sentence, so a
        # reintroduced summary fails even when reworded. What it cannot catch
        # is a summary written unbolded as running prose; that is the residual,
        # and it is smaller than the literal-match version this replaced, which
        # any rewording defeated.
        ("the target-move rule has exactly one bold statement",
         sum("ends this task" in b.lower() for b in BOLD.findall(ud)) == 1
         and sum("voids the triage" in b.lower() for b in BOLD.findall(ud)) == 0),
        ("the non-adopted branch is still eligible as the baseline",
         "it is the baseline, and stays one until the bump is applied to it"
         in flat(ud)
         # Stated at two decision points — *Task* chooses the worktree, the
         # phase performs the ordering — and the guard held only the first, so
         # the phase could lose its path entirely and stay green.
         and "the upgrade branch is already the baseline"
         in flat(near(ud, "## Characterization tests", 1500))),
        ("a supplied adoption settles identity, not state",
         "**identity** is settled and its state is not"
         in flat(clause(ud, "- **Work already in flight.**", 3000))),
        ("its in-flight item exempts an automated bump PR at the item itself",
         "is not that" in flat(clause(ud, "- **Work already in flight.**", 2000))),
        ("its peer-cap item resolves caps against the group's targets",
         "not their installed ones" in flat(clause(ud, "- **Peer caps.**", 2000))),
        ("its manifest audit checks resolution, not copy count",
         "not by counting copies in the tree" in flat(ud)),
        ("the single-copy requirement is scoped to singletons",
         "only where the package must be a singleton" in flat(ud)),
        # Adoption makes the bump PR's head the upgrade branch, so the obvious
        # place to write characterization tests is already post-migration. The
        # phase performs every visible step and its claim is gone.
        # Round two. The green gate must be plural at BOTH decision points:
        # a singular reading is green the moment any one required check
        # concludes, with the rest still pending.
        ("the orchestrator's green gate is over every required check",
         "every** check the repository actually requires" in flat(du)
         and "on the current head" in flat(clause(du, 'Gate "green"', 2000))),
        ("the worker's rollup rule carries the same plural gate",
         "every** check the repository requires" in flat(ud)),
        # The two assertion rules bind only to a constraint over an input. The
        # substitute for the other domains is an obligation, not an exemption:
        # phrased as "where applicable" it is taken by the same author who
        # would have written happy-path-only assertions.
        ("the non-constraint domains get a mandatory substitute, not an exemption",
         "mandatory, not an exemption" in flat(ud)),
        ("the substitute names a captured measurement compared after",
         "capture that domain's own measurement on the current version" in flat(ud)),
        # Dispatch scope must match the worker's own scope statement, and both
        # must key on unruled-out risk rather than on the version distance.
        ("dispatch scopes the worker by unruled-out risk, not version distance",
         "whose triage did **not** clear it of breaking changes" in flat(du)),
        ("the worker states the same scope test itself",
         "unruled-out risk of a breaking change does" in flat(ud)),
        ("cleared routine bumps are batched rather than dispatched each",
         "Routine bumps do not each get one" in flat(du)),
        # A stale base is invisible to every green signal: two upgrades editing
        # different lockfile entries do not conflict, so the merge is clean and
        # the merged lockfile carries a resolution the base had removed.
        ("the worker re-resolves the lockfile and never by hand",
         "before pushing, and record which base" in flat(ud)
         and "never by hand" in flat(ud)),
        # Neither skill merges, so a rule saying "immediately before merging"
        # names an actor that does not exist and the base goes stale again
        # between handoff and the human's merge. The check is carried, not held.
        ("the worker states that its result expires at handoff",
         "That result expires, and this task ends at handoff" in flat(ud)
         and "state in the PR body the base commit" in flat(ud)),
        ("the batch states the shared-lockfile amplifier at the concurrency site",
         "staleness compounds across it" in flat(du)),
        ("the batch carries the check to merge time rather than claiming to hold it",
         "merges nothing, so it cannot hold that check at merge time" in flat(du)
         and "name every open PR whose lockfile has gone stale" in flat(du)),
        # The eval corpus is a restatement of the contract and is swept with it.
        # Presence is checked per field, or a requirement dropped from the
        # expected answer stays green on the strength of an assertion that
        # happens to mention it. Absence is checked over expected answers
        # only, and skips negated occurrences: a prompt quoting a forbidden
        # instruction so the model can reject it is the guard working.
        ("no expected answer restates the ownerless merge-time instruction",
         states_rather_than_restates("upgrade-major-dependency",
                                     "immediately before merg")),
        ("the stale-base eval's expected answer requires the handoff record",
         "record in the PR body the base commit"
         in eval_field("upgrade-major-dependency",
                       "a-stale-base-reintroduces-a-removed-resolution",
                       "expected_output")),
        ("the stale-base eval's expected answer states the check expires",
         "repeated by whoever merges"
         in eval_field("upgrade-major-dependency",
                       "a-stale-base-reintroduces-a-removed-resolution",
                       "expected_output")),
        ("the stale-base eval grades on the handoff record",
         "resolved-against base commit in the PR body"
         in eval_field("upgrade-major-dependency",
                       "a-stale-base-reintroduces-a-removed-resolution",
                       "assertions")),
        # Round seven made the exemption source-independent; round eight found
        # this scenario still teaching the source-based rule. Evals restate,
        # and a restatement left behind grades against the old contract.
        ("no eval reserves duplicate status by discovery source",
         "did not derive its candidate from"
         not in " ".join(eval_expected("dependency-upgrade-orchestrator"))),
        ("the bump-queue eval grades the source-independence",
         "does not make the exemption depend on the bump queue having been the discovery source"
         in eval_field("dependency-upgrade-orchestrator",
                       "the-bump-queue-is-not-work-already-in-flight",
                       "assertions")),
        ("the routine-bump eval's expected answer counts the batched task",
         "Four tasks"
         in eval_field("dependency-upgrade-orchestrator",
                       "a-cleared-patch-is-not-one-dispatch-each",
                       "expected_output")),
        ("the routine-bump eval grades on that count",
         "counts four tasks"
         in eval_field("dependency-upgrade-orchestrator",
                       "a-cleared-patch-is-not-one-dispatch-each",
                       "assertions")),
        ("the PR-body record is stated where the report is written, not only where it is produced",
         "the base commit the lockfile was resolved against" in flat(clause(ud, "State what changed", 2000))),
        ("close-out reports per-PR lockfile staleness to the merger",
         all(phrase in flat(near(du, "## Close out", 1200))
             for phrase in ("per open PR, whether its lockfile is still resolved "
                            "against the current base",
                            "the merger's to repeat"))),

        # SHAPE, found by a repository-scoped pass rather than a diff review.
        # Round 3 removed an ownerless "immediately before merging" from the
        # lockfile rule; the routine-bump rule then said "immediately before
        # that task lands", which is the same defect with a different verb in
        # the other file. The round-3 guard could not see it: it was scoped to
        # the WORKER's evals and spelled to that instance's verb.
        # An ABSENCE check on the phrasing is not the answer — `du` uses it
        # correctly inside the authorized-merge clause and `ud` quotes it in
        # order to reject it, so such a check would have to tell use from
        # mention, which is the problem two deleted detectors failed at. So:
        # presence of the CARRIED structure. Each part names an actor that
        # exists — the agent before it writes, this run on every pass, the
        # merger afterwards.
        ("the routine-target check is carried to actors that exist, not held at the merge",
         "That check is carried rather than held" in flat(du)
         and "The batch agent re-checks immediately before it writes anything" in flat(du)
         # This one is legitimately whole-file: the sentence belongs to
         # *Dispatch*, which is where the check is assigned.
         and "this run re-checks on every supervision pass and again at close-out"
         in flat(du)
         # These are scoped, and that is the point. The first version of the
         # clause below passed while *Supervise* said nothing about either
         # check, because the sentence satisfying it sat in *Dispatch*
         # describing what *Supervise* would do. A guard for a rule about
         # WHERE something is stated has to check where it is stated.
         and all(phrase in flat(near(du, "## Supervise", 1400))
                 for phrase in ("Compare each open PR's recorded lockfile base",
                                "Re-check every batched routine candidate's target"))
         and "whether any batched candidate's target moved since it was cleared"
         in flat(near(du, "## Close out", 900))
         # The presence check above is the load-bearing half, and on its own it
         # is satisfiable while the defect sits beside it — negative-testing
         # showed the old heading restored with the carried paragraph left in
         # place going green, which is the two-disagreeing-statements shape
         # this pass found five times. So the exact constructions that have
         # occurred are named. This is a fixture list, not a detector: it holds
         # what a real defect said here, it cannot decide a novel verb, and a
         # broad ban on the phrasing is unavailable because `du` uses it
         # correctly under the authorized-merge exception and `ud` quotes it
         # to reject it.
         and not any(phrase in flat(text) for text in (ud, du) for phrase in (
             "target immediately before that task lands",
             "candidate's target immediately before",
             "re-check every batched candidate's target immediately",
         ))),
        # The routine batch is the one task that runs no named contract, so
        # every obligation delegated by pointing at `upgrade-major-dependency`
        # reaches it through nothing.
        # Three rounds got this assertion wrong in the same way, which is why
        # it is written as it is now. Round 29 listed the three obligations it
        # had found, so the fourth was pinned OUT by the fix for it. Round 30
        # added the fourth, stated the standard — every bullet needs its
        # operand, its disposition and its exception — and applied it to one
        # bullet. Round 31 claimed to assert "the property" and shipped a
        # longer list of literals, which a fifth bullet with no disposition
        # passed straight through.
        # The property that actually generates the list is ARITY: every bullet
        # in this block is an obligation, and every obligation owes a
        # disposition entry here. So the bullets are counted. Add one without
        # extending the list below and this goes red — which is the only thing
        # a list of literals could never do.
        # A group whose every member triage cleared is routine AND coupled, so
        # it batches — and every removal on this route pulled one member and
        # shipped its siblings, which is the split *Triage each candidate*
        # names by name. The worker has the rule; this route inherits nothing.
        # Round 33 fixed four removal points and pinned exactly those four
        # anchors, so the fifth — the earliest and most emphatic, sitting ABOVE
        # the scope paragraph, whose "below" textually excluded it — passed.
        # A list of anchors cannot tell you a site is missing, which is why the
        # scope sentence itself is now asserted to cover the route rather than
        # what follows it.
        ("the batch route removes coupled groups rather than members of them",
         "Every removal on this route therefore removes a coupled group, never a member of one"
         in flat(du)
         and all("coupled sibling" in flat(near(du, anchor, 900))
                 for anchor in ("A routine clearance is about one release",
                                "A colleague's branch pushed since triage",
                                "**Merged or closed**:",
                                "the rest of the batch is not void with it",
                                "Where one moved, its clearance"))),
        # The superseding closure is deferred to the end on both routes, for
        # the two reasons round 33 established in the worker: the PR the
        # reference points at does not exist yet, and a closed PR stops being
        # updated by its bot, which the target rules read.
        ("the superseding closure is deferred on the batch route too",
         "**Superseding does not close anything yet**"
         in flat(near(du, "- **Read each adopted bump PR's current state", 900))
         and "closed with that reference at the end, only if the batch produced a PR"
         in flat(du)
         and "at the end, once there is a PR to reference"
         in flat(near(ud, "- **Work already in flight.**", 1600))),
        ("the routine batch is given the obligations it cannot inherit",
         "The routine batch runs no named contract" in flat(du)
         and len(ROUTINE_BULLETS) == len(ROUTINE_DISPOSITIONS)
         and all(d in flat(bullet)
                 for bullet, dispositions in zip(ROUTINE_BULLETS,
                                                 ROUTINE_DISPOSITIONS)
                 for d in dispositions)),
        # SHAPE: an obligation on the report, stated only at the phase that
        # produces it, is dropped by an agent writing from *Report* — which
        # reads as an exhaustive list. Round 3 walked one cell (the base
        # commit) and left an assertion for it. Rounds 29 and 30 each walked
        # more and each left the list reading closed; see NOTES. The
        # list is a fixture — it holds every obligation found so far and
        # cannot see the next one — so the rule that matters is the sentence
        # asserted below it, which states WHY the restatement is here.
        ("every report obligation is stated where the report is written",
         "this is the section an agent writes the report from" in flat(ud)
         and all(phrase in flat(near(ud, "State what changed", 3200))
                 for phrase in ("the base commit the lockfile was resolved against",
                                "the measurement standing in for",
                                "what the real evidence is and that the passing build is not it",
                                "the in-flight search rather than the caller found the adopted bump PR",
                                "any **disagreement** between a supplied verdict",
                                "merged or closed, what the installed version actually shows",
                                "any blocker that ended the task",
                                # Added by round 31, which added the obligation
                                # and not this entry — inside the same commit
                                # as the note telling the next fixer to.
                                "any divergence between a rendered docs page",
                                # Round 32's own, missed by round 32.
                                "every adopted PR's URL, not only the one adopted as the branch",
                                # The two qualifiers a bare restatement drops.
                                "the re-resolution must be repeated if the base has moved since",
                                "handoff result and never a merge-time one"))),
        # Three contract sweeps on this PR left the eval corpus behind, and an
        # expected answer that teaches a deleted rule actively rewards
        # reintroducing it. These are the formulations the contract removed.
        # Scoped to expected_output AND assertions, because the first version
        # of this guard scanned only the first — and the defect it was written
        # for lived in an assertion ("The answer states all three obligations"),
        # so the guard was green over the exact thing it existed to catch.
        # Mutation-proved before this line was changed. Prompts are excluded on
        # purpose: quoting a wrong instruction so the model rejects it is the
        # corpus convention, and banning it there would conflate use with
        # mention.
        ("no expected answer or assertion teaches a formulation the contract removed",
         not any(phrase in text
                 for sk in ("upgrade-major-dependency", "dependency-upgrade-orchestrator")
                 for name in eval_names(sk)
                 for text in ([eval_field(sk, name, "expected_output")]
                              + eval_assertions(sk, name))
                 for phrase in ("and it is re-run over the tuple",
                                "reports the difference and stops",
                                "all three obligations"))),
        # A count in an eval goes stale the round after an obligation is added,
        # and grading a count rewards a brief that stops at that many. The
        # brief scenario grades the obligations instead.
        ("the routine-brief eval grades obligations rather than a count of them",
         not any(re.search(r"all (three|four|five|six) obligations", a)
                 for a in eval_assertions("dependency-upgrade-orchestrator",
                                          "the-routine-batch-inherits-nothing-by-cross-reference"))),
        ("close-out carries the clearance report dispatch requires of it",
         "which routine candidates were cleared and on what evidence"
         in flat(near(du, "## Close out", 1200))),
        # The worker's return grew a fourth item that eval 14 already graded.
        ("the return contract and its consumer agree on the incompatible tuple",
         # Three prose sites enumerate this return and all three are checked:
         # *Task* produces it, *Report* writes it, the caller expects it.
         "**the incompatible tuple**" in flat(near(ud, "So re-read enough to make the report useful", 700))
         and "the incompatible tuple" in flat(near(ud, "A task ended by a moved target reports", 1200))
         and "the incompatible tuple where a peer range is what moved"
         in flat(near(du, "**Expect that stop on any moved target", 1400))),
        # A moved-target stop is not "proved unsafe", and the rule beside it
        # tells the worker to close the adopted PR — destroying the one thing
        # the move leaves standing.
        ("a moved-target stop leaves every adopted PR open, stated beside the rule it disclaims",
         "leaves every adopted PR open"
         in flat(near(ud, "**A task ended by a moved target leaves", 800))
         and "If the upgrade proved unsafe"
         in flat(near(ud, "**A task ended by a moved target leaves", 800))),
        # Round 32 ordered superseded PRs closed at branch setup and then built
        # two rules on their staying open. A closed PR's bot stops updating it,
        # so the mechanism was dead before the stop meant to preserve it.
        ("superseding is a closure at the end, not at branch setup",
         "**Superseding does not close anything yet.**" in flat(ud)
         and "a closed PR stops being updated by its bot" in flat(ud)
         and "at the end, and only if the task produced a PR" in flat(ud)),
        # Research was written when a moved target meant re-derive and continue.
        # An eval graded this for rounds before any contract sentence said it,
        # which is how it was found. Both decision points now carry it: the
        # worker researches per package, and the orchestrator researches every
        # candidate at triage before any worker exists.
        ("a docs/artifact divergence is reported, at both places research happens",
         "the artifact wins and the divergence is reported"
         in flat(near(ud, "## Research", 1200))
         and "the divergence is reported rather than silently resolved"
         in flat(near(du, "**Breaking changes**", 700))),
        ("the research phase does not resume a task the gate ended",
         "That case does not resume here" in flat(near(ud, "## Research", 900))),
        # Discovery text is a decision point too: it is what a caller reads
        # before dispatching, and it advertised a workflow the contract rejects.
        ("the orchestrator's description names the routine-bump path",
         # Scoped to the frontmatter it names. Whole-file, this passed with the
         # clause moved into the body — where a caller choosing a skill never
         # reads it, which is the entire point of the assertion.
         "plus one batched task for the routine bumps"
         in flat(du.split("---")[1] if du.count("---") > 1 else "")),
        ("the characterization baseline excludes an adopted PR's head",
         # Both clauses scoped to the phase. "never the baseline" also appears
         # in *Task*, so the whole-file version stayed green with the rule
         # deleted from the section that performs it.
         "never the baseline" in flat(near(ud, "## Characterization tests", 2200))
         and "merge base" in near(ud, "## Characterization tests", 2200)),
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
