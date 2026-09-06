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


NEGATORS = (
    "not ", "never ", "n't ", "rather than", "instead of", "no longer",
    "avoid", "cannot", "refus", "reject",
)


# A clause boundary: a sentence ender, or a conjunction that introduces a fresh
# positive clause. `or` and `nor` are deliberately absent — under negation,
# disjunction DISTRIBUTES ("do not merge or re-resolve" forbids both), so an
# `or` carries the governing negator across it while an `and` after a negated
# clause introduces a new imperative ("do not trust CI and re-resolve" requires
# the second). That asymmetry is the only surface signal separating the two
# constructions, which are otherwise identical in shape; the fixtures pin both.
#
# The residual ambiguity is real and worth knowing rather than trusting: a
# comma-separated disjunction ("do not merge, or re-resolve …") is not
# disambiguated by this, and English does not disambiguate it either. A
# borderline sentence in an expected answer should be rewritten to say what the
# answer requires rather than restate what it rejects, which is how all of this
# repository's scenarios are already written.
CLAUSE_BREAK = re.compile(r"[.!?;:]\s|,?\s+(?:and|but|then|so|yet)\s+")


def prescribes(texts: list[str], phrase: str) -> bool:
    """True where `phrase` appears as an instruction rather than as one being
    rejected.

    Negation is looked for in the phrase's **own clause**. Two coarser scopes
    were tried first and each was green over a live prescription:

    * a fixed character window — a negation in the neighbouring *sentence*
      suppressed the occurrence ("Do not claim it as a merge-time result.
      Re-resolve immediately before merging.");
    * the sentence — a negation in the neighbouring *clause* did the same
      ("Do not trust green CI, and re-resolve immediately before merging."),
      with or without the comma.

    Both are the exact regression this check exists to catch, and both passed.
    A third round then supplied the opposite failure — a false positive on
    "Do not merge or re-resolve immediately before merging.", where the
    negation governs both coordinated verbs — so the scope is a clause and
    `or` does not open one. See CLAUSE_BREAK for why that asymmetry is the
    only available signal. Every mutation that has defeated this function is
    pinned as a fixture below; it has been wrong in both directions, so both
    directions are tested.
    """
    needle = phrase.lower()
    for text in texts:
        low = flat(text).lower()
        i = low.find(needle)
        while i != -1:
            starts = [m.end() for m in CLAUSE_BREAK.finditer(low, 0, i)]
            if not any(n in low[(starts[-1] if starts else 0):i] for n in NEGATORS):
                return True
            i = low.find(needle, i + 1)
    return False


# Fixtures for `prescribes`. A scope error in it is silent — the check simply
# passes — so the two mutations that already defeated it are pinned here
# rather than left to a future negative test somebody remembers to run.
PRESCRIBES_FIXTURES = [
    ("Re-resolve immediately before merging.", True),
    ("Do not claim it as a merge-time result. Re-resolve immediately before merging.", True),
    ("Do not trust green CI, and re-resolve immediately before merging.", True),
    ("Do not trust green CI and re-resolve immediately before merging.", True),
    ("You do not re-resolve immediately before merging; this task ends at handoff.", False),
    ("Never re-resolve immediately before merging.", False),
    ("Record the base rather than re-resolve immediately before merging.", False),
    ("Do not merge or re-resolve immediately before merging.", False),
    ("Do not merge nor re-resolve immediately before merging.", False),
    ("This task ends at handoff.", False),
]


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
        ("dependency dispatch forwards the viability verdict and the coupled set",
         "the viability verdict and the coupled set"
         in flat(clause(du, "Supply each agent with the completed triage", 2000))),
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
        ("upgrade-major-dependency reads a supplied verdict instead of re-deriving",
         "instead of re-deriving that item" in flat(ud)),
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
        ("prescribes() reads negation at clause scope",
         all(prescribes([s], "immediately before merg") is want
             for s, want in PRESCRIBES_FIXTURES)),
        ("no eval prescribes the ownerless merge-time re-resolution",
         not prescribes(eval_expected("upgrade-major-dependency"),
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
         "the merger's to repeat" in flat(du)),
        # Discovery text is a decision point too: it is what a caller reads
        # before dispatching, and it advertised a workflow the contract rejects.
        ("the orchestrator's description names the routine-bump path",
         "plus one batched task for the routine bumps" in flat(du)),
        ("the characterization baseline excludes an adopted PR's head",
         "never the baseline" in flat(ud)
         and "merge base" in near(ud, "## Characterization tests", 1800)),
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
