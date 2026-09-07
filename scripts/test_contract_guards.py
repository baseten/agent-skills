#!/usr/bin/env python3
"""Mutation fixtures for check_contract_placement.py's corpus assertions.

Run from the repository root:

    python3 scripts/test_contract_guards.py

**Why this file exists, stated plainly because it is the whole lesson of the
review series that produced it.** Four consecutive rounds on one pull request
ended with an assertion that was green over the exact defect it was written
for, and each round fixed only the instance it was shown:

* round 29 wrote a guard listing the three obligations it had found, so the
  fourth was pinned *out* by the fix for it;
* round 30 rescoped five whole-file checks and declared the class closed;
* round 31 found three more, rescoped them, and left a sixth four lines away —
  a check whose name asserts three things it never looked at;
* round 32 found that one, plus a clause relabelled "the property" that a new
  bullet passed straight through.

Every one of those was found in seconds by mutating the rule and re-running the
check. `NOTES.md` had said so since round twelve — *"mutate the rule the guard
protects and watch the guard fail; testing the direction you are already
confident in proves nothing"* — as **advice**, in a repository whose own tier
list says advice reaches an agent only if something makes it read the file.

So it is a script. A guard that cannot fail is not a guard, and the only way to
know is to break the rule and watch.

**Adding to this file is the maintenance the check suite needs.** A new corpus
assertion owes a mutation here: the smallest edit to the contract that makes
the rule it protects false. If you cannot write one, the assertion is not
testing what its name says.
"""

from __future__ import annotations

import ast
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
UD = "skills/upgrade-major-dependency/SKILL.md"
BO = "skills/backlog-orchestrator/SKILL.md"
BON = "skills/backlog-orchestrator/NOTES.md"
RC = "skills/resolve-pr-comment/SKILL.md"
ST = "skills/settle-outstanding-decisions/SKILL.md"
CP = "skills/create-pr/SKILL.md"
RP = "skills/repair-pr/SKILL.md"
SM = "skills/summarize-tranche/SKILL.md"
VB = "skills/validate-backlog/SKILL.md"
DU = "skills/dependency-upgrade-orchestrator/SKILL.md"
UD_EVALS = "skills/upgrade-major-dependency/evals/evals.json"
DU_EVALS = "skills/dependency-upgrade-orchestrator/evals/evals.json"

# The replacement `MOVE_TO_END` deletes the text where it stands and appends it
# unchanged to the end of the file. A deletion tests that a rule is PRESENT; a
# relocation tests that it is present WHERE IT IS READ, which is what most of
# these assertions are actually about and what a deletion cannot distinguish.
# Round 33 measured this: with every `near()` reverted to a whole-file grep,
# 21 of 23 deletions still went red, so they were not exercising the scoping
# that three rounds of work had been about.
MOVE_TO_END = "<<MOVE_TO_END>>"

# (label, file, text to replace, replacement, assertion that must go red).
# Each entry is a real defect this repository has had, or the smallest edit
# that reintroduces the rule an assertion protects. The round that produced it
# is in the label, because a fixture without its provenance reads as a
# preference rather than as evidence.
MUTATIONS: list[tuple[str, str, str, str, str]] = [
    # --- absolutes left behind when the footer rule was narrowed (round 4) ---
    # Each narrowing of this rule has left a downstream absolute standing, and
    # each read as a reassurance rather than a claim. Two of the three survivors
    # last round were in NOTES.md, which nothing checked at all.
    ("stale: the resolver promises no path ever footers the answer", RC,
     "**That absolute is about the\ndraft, and it stops there.**",
     "No path puts a footer on this text.",
     "no unconditional no-footer claim survives about a ruling"),
    ("stale: the orchestrator's notes call the ruling footerless again", BON,
     "**is the one write whose footer is decided by a condition rather than by its kind**",
     "recorded ruling now carries **no** footer",
     "no unconditional no-footer claim survives about a ruling"),
    # Owed by f3e0e5e's assertion, which was verified by hand and not durably.
    ("duplicate: the budget is restated in create-pr, as #71 has it", CP,
     "# PR description template",
     "# PR description style\n\n300 words of prose above the fold, maximum.\n\n# PR description template",
     "the PR body budget is stated in one contract only"),
    # --- the footer marks writes nobody read (the owner's ruling) ---
    # The blanket footer was the previous rule here, so the mutation that matters
    # is the one that quietly restores it. Round two of this branch's review found
    # the discriminator's own decision point still asserting the blanket, with a
    # guard green over it because the guard's substring lived only in the stale
    # sentence. These are the mutations that would have caught it in seconds.
    ("footer: the attended row flips to carrying one", BO,
     "confirmed or edited by them | this exact text | **no** |",
     "confirmed or edited by them | this exact text | **yes** |",
     "the attended path forbids the footer"),
    ("footer: the unattended row flips to carrying none", BO,
     "nobody read it | **yes** |", "nobody read it | **no** |",
     "the unattended path requires it"),
    ("footer: the approval test is softened to a blanket", BO,
     "**No \u2192 the write carries the footer. Yes \u2192 it does not.**",
     "**Every authored write carries it.**",
     "the approval test states both answers"),
    ("footer: approval becomes something short of reading the text", BO,
     "Sitting in the session is not approval either.",
     "A person who authorised the run has approved its writes.",
     "approval is of the text, not of the run"),
    ("footer: the unmarked direction becomes the default", BO,
     "the answer is No and the footer goes on",
     "the answer is Yes and the footer is omitted",
     "the unmarked direction is the safe one"),
    ("footer: the discriminator absolute reverts to the blanket claim", BO,
     "The attribution footer is not a substitute either",
     "The attribution footer every authored write now carries is not a substitute either",
     "no blanket footer claim survives anywhere in bo"),
    ("footer: the avatar argument is re-widened past the unattended case", BO,
     "an argument about the unattended case only",
     "an argument about every write the run makes",
     "the avatar argument is scoped to the unattended case"),
    ("footer: settle asks the test of the answer, not the whole comment", ST,
     "asked of **the complete comment, not of the answer inside it**",
     "asked of the answer text the owner approved",
     "settle asks the exact-text test of the complete comment"),
    ("footer: settle claims an exception for itself", ST,
     "There is no exception here for this skill",
     "This skill is the exception",
     "settle's footer is conditional on the complete record being approved"),
    ("footer: the double-attribution argument returns to bo", BO,
     "is never itself a reason to omit the footer",
     "means the footer would double-attribute the write",
     "an existing attribution is not a reason to omit the footer"),
    ("footer: settle stops retracting the double-attribution argument", ST,
     "wrongly argued that a footer beside the marker would double-attribute",
     "correctly argued that a footer beside the marker would double-attribute",
     "settle retracts the double-attribution argument"),
    ("footer: a bodyless write loses its stated reason", BO,
     "there is nowhere to put one", "it is exempt",
     "a write with no body carries no footer for want of anywhere to put one"),
    ("footer: create-pr's body stops splitting by mode", CP,
     "this skill is where the test actually splits",
     "the footer applies to every body this skill creates",
     "create-pr's body footer is mode-dependent"),
    ("footer: the dispatch prompt carries the conclusion, not the test", BO,
     "the footer **with its approval test**", "the footer",
     "the dispatched form rule carries the approval test itself"),

    # --- a question item has to be usable without hunting ---
    ("item: the URL rule becomes a shape rule", RC,
     "as returned by the API, verbatim \u2014 never a hand-built anchor",
     "a valid URL for the thread",
     "the item's URL is API provenance, not a shape rule"),
    ("item: the invisible-failure argument goes", RC,
     "silently resolves to the wrong place", "may be incorrect",
     "the item names why a rebuilt anchor fails invisibly"),
    ("item: the ask may be paraphrased", RC,
     "at most 2 lines**, trimmed with an ellipsis rather than paraphrased",
     "summarised**",
     "the item quotes the ask rather than paraphrasing it"),
    # Codex P1: "paste-ready" collapsed the two draft kinds, and a decision-only
    # draft sent as-is posts a non-answer over an undecided question.
    ("item: the reply is paste-ready for both draft kinds again", RC,
     "paste-ready only for one of the two draft kinds", "paste-ready",
     "the recommended reply splits by draft kind"),
    ("item: the decision-only label goes", RC,
     "**`decision \u2014 not for posting`**", "it",
     "a decision-only draft is labelled not for posting"),
    ("item: the attended path lets a decision-only draft be sent", RC,
     "a **decision-only** draft is not theirs to send at all",
     "either draft they may send",
     "the attended path splits what may be sent by kind"),
    ("item: the decision-only path loses its route to settlement", RC,
     "which is built for exactly this — it asks the\n  underlying options and records the one chosen",
     "which handles it",
     "the decision-only path names settle as its route"),
    ("item: the drafts start carrying a footer", RC,
     "they author whatever they post", "the footer applies",
     "neither draft kind carries a footer"),
    ("item: the URL rule is scoped to question items only", RC,
     "obeys row 1", "is a matter for that entry",
     "the URL rule covers every thread URL the skill emits"),
    ("item: a notification becomes delivery", RC,
     "a subscription dies\nwith the session that armed it",
     "a notification reaches the person who needs it",
     "notification never substitutes for the record"),
    ("item: partial entries become acceptable", RC,
     "four of the five is not this entry", "a summary is enough here",
     "the resolver Output demands all five fields"),
    ("item: repair-pr rebuilds the URL", RP,
     "**Never rebuild the thread URL**", "Reconstruct the thread URL as needed",
     "chain 2/5: repair-pr forbids rebuilding the URL"),
    ("item: bo accepts an almost-complete record", BO,
     "recording all but one of them is recording none",
     "recording most of them is enough",
     "bo records partial items as no record at all"),
    ("item: settle drops back to consuming the reply alone", ST,
     "carry **all of the item's fields** into the question",
     "carry that item's **recommended reply** into the question",
     "chain 5/5: settle consumes all of the item's fields, not just a draft"),

    # --- no mode answers a query in the thread ---
    ("query: the attended path posts the answer again", RC,
     "it is `NEEDS_USER` in every mode, and\nthis skill posts no answer to it",
     "post a reply with an appropriate response when a person invoked you",
     "resolve-pr-comment answers no query in the thread, in any mode"),
    ("query: the mixed rule re-admits attended as an exception", RC,
     "Attended is not an exception here, and this section does not make one",
     "Attended is the exception here",
     "the mixed section makes attended no exception"),
    ("query: the rule reverts to arguing from disclosure", RC,
     "The reason is authority, not disclosure.",
     "The reason is that the reviewer cannot tell.",
     "the no-answer rule rests on authority, not disclosure"),

    # --- #72's skills reach an authored write ---
    ("dep: upgrade-major-dependency keeps its partial local copy", UD,
     "partial copy that names two of its exclusions",
     "restatement is fine here",
     "upgrade-major-dependency defers the form rule instead of copying it"),
    ("issue: summarize-tranche loses the form rule at creation", SM,
     "authorizing creation is not approving a body nobody has read",
     "the invocation authorized it",
     "summarize-tranche carries the form rule to issue creation"),
    ("issue: validate-backlog loses it at an authorized rewrite", VB,
     "authorizes the edit, not the wording", "authorizes the change",
     "validate-backlog carries the form rule to an authorized rewrite"),
    ("dep: the dispatch constraints lose the form rule", DU,
     "- **The authored-write-form rule**", "- (removed)",
     "the dependency dispatch constraints carry the form rule"),

    # --- the PR body budget is a number, not an adjective ---
    ("body: the budget becomes an adjective again", BO,
     "300 words of prose above the fold, maximum", "kept reasonably short",
     "the PR body budget is a number, not an adjective"),
    ("body: intent-not-content is softened", BO,
     "The body states intent, not content",
     "The body describes what changed and why",
     "the body states intent rather than content"),
    ("body: over-budget may be reflowed", BO,
     "never compress by deleting whitespace", "reflow it to fit",
     "over budget means cut, not reflow"),
    ("body: a trivial PR must still be filled out", BO,
     "Do not manufacture prose to fill a template", "Fill every template heading",
     "a trivial PR is allowed a near-empty body"),
    ("body: a documented style guide stops winning", BO,
     "that guide governs and its budget wins", "these rules still govern",
     "a documented style guide overrides the floor"),
    ("body: create-pr reads the guide after drafting", CP,
     "read it before drafting the body, not after", "read it when convenient",
     "create-pr reads the style guide before drafting"),
    ("body: a subtraction may be flattened to a list", BO,
     "may not convert the subtraction into a list", "may enumerate what it requires",
     "the form rule keeps a subtraction a subtraction"),
    # --- the routine batch runs no named contract (rounds 29-32) ---
    ("r32 a fifth obligation with no disposition", DU,
     "\n\nSupply each agent with the completed triage",
     "\n- **Check whether any batched package is subject to a repository dependency policy.** Policies exist.\n\nSupply each agent with the completed triage",
     "the routine batch is given the obligations it cannot inherit"),
    ("r31 the adopted-PR bullet loses its disposition", DU,
     "verify against the installed version and report it", "carry on regardless",
     "the routine batch is given the obligations it cannot inherit"),
    ("r31 the base commit becomes a bare value", DU,
     "with both qualifiers that make it safe", "as a plain value",
     "the routine batch is given the obligations it cannot inherit"),
    ("r30 the target obligation loses its disposition", DU,
     "is not this agent's to re-triage or re-route", "can be handled locally",
     "the routine batch is given the obligations it cannot inherit"),
    ("r30 the in-flight bullet loses its bot-PR exception", DU,
     "**An automated bump PR for a batched package is not that**", "Anything open counts",
     "the routine batch is given the obligations it cannot inherit"),
    ("r33 the target bullet loses its blast-radius clause", DU,
     "the rest of the batch is not void with it", "the batch is void with it",
     "the routine batch is given the obligations it cannot inherit"),
    ("r33 the adopted-PR bullet loses the superseded disposition", DU,
     "take the successor on the same terms", "ignore the successor",
     "the routine batch is given the obligations it cannot inherit"),

    # --- a check carried to an actor that exists (rounds 3-5, 29-31) ---
    ("r30 Supervise loses the carried checks", DU,
     "- **Compare each open PR's recorded lockfile base against the current base**",
     "- (removed)",
     "the routine-target check is carried to actors that exist, not held at the merge"),
    ("r29 the ownerless merge moment returns", DU,
     "**A routine clearance is about one release, so the batch re-checks every candidate's target — and this run re-checks it again, because neither of them occupies the moment that decides it.**",
     "**A routine clearance is about one release, so re-check every batched candidate's target immediately before that task lands.**",
     "the routine-target check is carried to actors that exist, not held at the merge"),
    ("r32 Close out stops handing the lockfile check to the merger", DU,
     ", and **per open PR, whether its lockfile is still resolved against the current base**, plus **whether any batched candidate's target moved since it was cleared** — naming both checks as the merger's to repeat, since this run merges nothing.",
     ", and **whether any batched candidate's target moved since it was cleared**.",
     "close-out reports per-PR lockfile staleness to the merger"),

    # --- every report obligation stated where the report is written (r3, 29-32) ---
    ("r30 the disagreement obligation is dropped from Report", UD,
     "- any **disagreement** between a supplied verdict and what this task re-derived", "- any nothing at all",
     "every report obligation is stated where the report is written"),
    ("r30 the base commit's qualifiers are dropped when restated", UD,
     "that **the re-resolution must be repeated if the base has moved since**, and that it is a **handoff result and never a merge-time one**",
     "the base value",
     "every report obligation is stated where the report is written"),
    ("r31 the docs-divergence obligation is dropped from Report", UD,
     "and any divergence between a rendered docs page and the published artifact (see Research);", "",
     "every report obligation is stated where the report is written"),
    ("r32 the docs-divergence rule is deleted from Research", UD,
     "**Where the two do diverge, the artifact wins and the divergence is reported**", "**Note.**",
     "a docs/artifact divergence is reported, at both places research happens"),
    ("r32 the orchestrator's triage loses the divergence disposition", DU,
     "the divergence is reported rather than silently resolved", "the artifact is used",
     "a docs/artifact divergence is reported, at both places research happens"),
    ("r29 the sentence stating WHY Report restates is deleted", UD,
     "this is the section an agent writes the report from", "this section matters",
     "every report obligation is stated where the report is written"),

    # --- the moved-target stop and its return (rounds 19-21, 29-30) ---
    ("r29 Task's enumeration drops the incompatible tuple", UD,
     "the recomputed set, and, where a peer range is what moved, **the incompatible tuple** that voids the clearance",
     "the recomputed set",
     "the return contract and its consumer agree on the incompatible tuple"),
    ("r29 the caller stops expecting the tuple", DU,
     "the incompatible tuple where a peer range is what moved,", "",
     "the return contract and its consumer agree on the incompatible tuple"),
    ("r29 the adopted PR is no longer left open on a stop", UD,
     "**A task ended by a moved target leaves every adopted PR open**", "**Unrelated sentence**",
     "a moved-target stop leaves every adopted PR open, stated beside the rule it disclaims"),
    ("r33 superseded PRs are closed at branch setup again", UD,
     "**Superseding does not close anything yet.**", "Close each now.",
     "superseding is a closure at the end, not at branch setup"),
    ("r33 the arity paragraph is relocated out of the worktree cases", UD,
     "**Adopt exactly one as the branch — the member with the most of the migration already in it — and supersede the rest**",
     MOVE_TO_END,
     "the adopted-PR arity is stated, with the two rules that read over all of them"),
    ("r33 the carried checks are relocated out of Supervise", DU,
     "- **Compare each open PR's recorded lockfile base against the current base**, and name every PR whose lockfile has gone stale.",
     MOVE_TO_END,
     "the routine-target check is carried to actors that exist, not held at the merge"),
    ("r33 the Report obligations are relocated out of Report", UD,
     "- any **disagreement** between a supplied verdict and what this task re-derived, rather than silently taking either answer (see Task), and any divergence between a rendered docs page and the published artifact (see Research);",
     MOVE_TO_END,
     "every report obligation is stated where the report is written"),
    ("r32 the arity rule's report obligation is dropped", UD,
     "**every adopted PR's URL, not only the one adopted as the branch**", "a mapping",
     "every report obligation is stated where the report is written"),
    ("r34 the batch route closes superseded PRs at setup again", DU,
     "**Superseding does not close anything yet**", "Close each now",
     "the superseding closure is deferred on the batch route too"),
    ("r34 the gate item drops the deferral", UD,
     "at the end, once there is a PR to reference", "immediately",
     "the superseding closure is deferred on the batch route too"),
    ("r34 the fifth removal point loses its sibling qualifier", DU,
     "pull it out — **together with its coupled siblings** (below) —", "pull it out,",
     "the batch route removes coupled groups rather than members of them"),
    ("r33 the batch route forgets coupled siblings", DU,
     "**Every removal on this route therefore removes a coupled group, never a member of one**",
     "Removals are per candidate",
     "the batch route removes coupled groups rather than members of them"),
    ("r29 Research resumes a task the gate ended", UD,
     "**That case does not resume here.**", "Re-read the range and continue.",
     "the research phase does not resume a task the gate ended"),

    # --- placement, where the whole content of the rule is where it sits ---
    ("r31 the description's routine-bump path moves into the body", DU,
     "plus one batched task for the routine bumps triage cleared, which need no migration workflow.",
     "and other work.",
     "the orchestrator's description names the routine-bump path"),
    ("r31 the baseline rule is deleted from the phase that performs it", UD,
     "**An adopted bump PR's head is never the baseline.** It already carries the bump, so tests written and proven green there are post-migration tests wearing this phase's name",
     "**Note.** The head carries the bump",
     "the characterization baseline excludes an adopted PR's head"),
    ("r29 Close out stops reporting the clearances Dispatch requires", DU,
     "**which routine candidates were cleared and on what evidence** (see Dispatch", "nothing at all (see Dispatch",
     "close-out carries the clearance report dispatch requires of it"),

    # --- the moved-target rule and its consumers (rounds 15-21), never
    # --- mutated until round 33 measured the battery's own coverage ---
    ("r21 the stop becomes conditional on a changed set again", DU,
     "**reports and stops rather than reshaping its own task** — on the move itself, whether or not the set came out different (below)",
     "and, finding it different, **reports and stops rather than reshaping its own task**",
     "the producer expects that report and owns membership"),
    ("r21 the caller stops expecting an unconditional stop", DU,
     "**Expect that stop on any moved target, not only a changed set", "**Expect that stop when the set changes",
     "the producer expects the stop on any moved target, not just a changed set"),
    ("r19 the peer clearance survives another member's move", UD,
     "dies as soon as **any** member's target moves", "dies when its own package's target moves",
     "the peer-cap gate item says a supplied clearance dies group-wide"),
    ("r18 the target rule stops reaching research and the audit", UD,
     "licence, install cooldown, breaking-change research and usage audit", "licence and install cooldown",
     "the target rule reaches the research and the audit, not just the gate"),
    ("r21 the re-reading becomes a continuation again", UD,
     "The re-reading serves the report, not the continuation.", "Then continue.",
     "the re-reading serves the report, not the continuation"),
    ("r15 the return mapping collapses to one figure", UD,
     "package → current target mapping for every package that moved**, the refreshed failure-mode reading",
     "current target**, the refreshed failure-mode reading",
     "Report hands back a per-package mapping, symmetric with dispatch"),
    ("r16 dispatch stops forwarding the per-package target", DU,
     "**the viability verdict, the exact target version it measured for every package in the task, and the coupled set**",
     "**the viability verdict and the coupled set**",
     "dependency dispatch forwards the verdict, a per-package target, and the coupled set"),
    ("r1 the gate stops exempting an automated bump PR", UD,
     "**An automated bump PR for these same packages is not that**", "Any open PR counts",
     "its in-flight item exempts an automated bump PR at the item itself"),
    ("r1 triage stops exempting an automated bump PR", DU,
     "**An automated bump PR for a candidate is never work already in flight — it is the work.**",
     "An open PR removes a candidate.",
     "an automated bump PR is the work, not work already in flight"),
    ("r19 peer caps resolve against installed versions again", UD,
     "resolving every cap against the group's **target** versions and not their installed ones",
     "resolving every cap against the installed versions",
     "its peer-cap item resolves caps against the group's targets"),
    ("r20 the adopted PR's state is taken from the verdict again", UD,
     "read the PR itself before branching from it", "trust the verdict's description of it",
     "the adopted PR's state is refreshed, not taken from the verdict"),
    ("r3 the lockfile is settled by hand", UD,
     "never by hand", "carefully by hand",
     "the worker re-resolves the lockfile and never by hand"),
    ("r22 the PR-body record leaves the section that writes the report", UD,
     "the base commit the lockfile was resolved against (see Migration and verification",
     "the base (see Migration and verification",
     "the PR-body record is stated where the report is written, not only where it is produced"),
    ("r23 the target mapping stops covering every coupled member", DU,
     "Forward a **package → triaged target** mapping covering every member", "Forward the task's target",
     "the target mapping covers every coupled member"),
    ("r24 the worker is scoped by version distance again", UD,
     "The version distance does not decide whether this skill applies; **unruled-out risk of a breaking change does**",
     "This skill applies to majors",
     "the worker states the same scope test itself"),
    ("r24 dispatch scopes the worker by version distance again", DU,
     "whose triage did **not** clear it of breaking changes", "that is a major",
     "dispatch scopes the worker by unruled-out risk, not version distance"),
    ("r24 cleared routine bumps get one agent each", DU,
     "**Routine bumps do not each get one.**", "Routine bumps get one each.",
     "cleared routine bumps are batched rather than dispatched each"),
    ("r21 the coupled set is claimed to survive a move", UD,
     "relations over the targets rather than properties of one", "properties of one package",
     "peer resolution and the coupled set are voided task-wide"),
    ("r29 the non-adopted branch stops being the baseline", UD,
     "the upgrade branch is already the baseline — one worktree", "cut a second worktree for the baseline",
     "the non-adopted branch is still eligible as the baseline"),

    # --- round 33b: the rest of this PR's subject, previously unmutated ---
    ("r21 the moved-target rule reshapes instead of ending", UD,
     "**A moved target ends this task; it does not reshape it.**", "**A moved target reshapes this task.**",
     "a moved target ends the task rather than reshaping it"),
    ("r18 the gate stops re-running per-package on a move", UD,
     "Compare each package's current target against the one triage measured for it", "Check the targets",
     "a moved target re-runs the per-package gate items for that package"),
    ("r24 a moved target stops voiding the routine clearance", DU,
     "A routine clearance is about one release", "A routine clearance is durable",
     "a moved target voids a routine clearance and its routing"),
    ("r16 dispatch stops saying why those two are load-bearing", DU,
     "**The first three are supplied because the agent's own gate reaches a different answer without them, not to save it work.**",
     "**They are supplied.**",
     "dependency dispatch says why those two specifically"),
    ("r20 dispatch justifies the adopted PR by the old wrong stop", DU,
     "so it is supplied as identity rather than to prevent a wrong stop",
     "so it is supplied to prevent a wrong stop",
     "dispatch no longer justifies the adopted PR by a wrong stop"),
    ("r2 the manifest audit counts copies again", UD,
     "**not by counting copies in the tree**", "by counting copies in the tree",
     "its manifest audit checks resolution, not copy count"),
    ("r29 the batch claims to hold the lockfile check at merge time", DU,
     "merges nothing, so it cannot hold that check at merge time", "holds that check at merge time",
     "the batch carries the check to merge time rather than claiming to hold it"),
    ("r6 the shared-lockfile amplifier leaves the concurrency site", DU,
     "staleness compounds across it", "staleness is possible",
     "the batch states the shared-lockfile amplifier at the concurrency site"),
    ("r19 the orchestrator presents the verdict as covering the gap", DU,
     "**The verdict does not cover what can change in the dispatch gap, and must not be presented as though it does.**",
     "**The verdict covers the dispatch gap.**",
     "the orchestrator does not present the verdict as covering either"),
    ("r19 triage resolves peer caps outside the coupled group", DU,
     "**resolved against the candidate's coupled group, which is therefore established before this item is answered**",
     "resolved against the installed versions",
     "the orchestrator's peer-cap item is scoped to the coupled group"),
    ("r1 triage's viability item stops exempting a bot bump PR", DU,
     "**other than an automated bump PR for this candidate**", "of any kind",
     "the orchestrator's viability item exempts any automated bump PR"),
    ("r16 dispatch stops saying why the target must travel", DU,
     "**It cannot run that comparison against a version this dispatch never named**", "It compares them",
     "the producer names why the target must travel with the verdict"),
    ("r25 dispatch stops stating the peer exception", DU,
     "**The peer finding is the exception to per-package", "**The peer finding",
     "the producer states the peer exception to per-package"),
    ("r20 the target-move rule gains a second bold statement", UD,
     "Where a target moved, **what survives is identity only**",
     "**A moved target ends this task; it does not reshape it.** Where a target moved, **what survives is identity only**",
     "the target-move rule has exactly one bold statement"),
    ("r5 the orchestrator's green gate becomes singular again", DU,
     "Gate \"green\" on **every** check the repository actually requires having concluded successfully **on the current head**",
     "Gate \"green\" on the required check",
     "the orchestrator's green gate is over every required check"),
]

# Mutations against the eval corpus, which is a restatement of the contract and
# goes stale with it. Three contract sweeps on one PR left it behind.
EVAL_MUTATIONS: list[tuple[str, str, str, str, str]] = [
    ("r30 an expected answer teaches the deleted peer re-run", DU_EVALS,
     "and the agent does not re-run it and carry on", "and it is re-run over the tuple, so",
     "no expected answer or assertion teaches a formulation the contract removed"),
    ("r31 an assertion grades a count of obligations", DU_EVALS,
     "The answer states each obligation in the brief rather than cross-referencing it",
     "The answer states all four obligations in the brief rather than cross-referencing them",
     "the routine-brief eval grades obligations rather than a count of them"),

    # The corpus and NOTES are restatements of the contract and go stale with
    # it; these break the ones with an assertion behind them.
    ("r25 an oracle names all three findings in one block", UD_EVALS,
     "Everything else is void:",
     "Everything else is void, so reuse licence, cooldown and peer per package:",
     "no eval oracle names all three findings in one block"),
    ("r21 an oracle makes the moved-target stop conditional", UD_EVALS,
     "(b) the set is unchanged and the answer is the same stop, because the model question is untouched by that.",
     "(b) the set is unchanged, so the task continues.",
     "an oracle makes the moved-target stop unconditional"),
    ("r20 the notes state a superseded rule as live", "skills/upgrade-major-dependency/NOTES.md",
     "The versions are worth recording as **superseded**", "The versions are worth recording",
     "the worker's notes state the superseded rules as superseded"),
]


def run_check(tree: pathlib.Path) -> set[str]:
    """Assertion names that FAILED, running the checker against `tree`.

    A crash is not a failure: the checker dying (a moved anchor inside one of
    its own helpers, say) produces no FAIL lines, and reading stdout alone
    would report every mutation as green over its own defect while printing a
    baseline PASS. Round 33 reproduced that. So the exit code is checked.
    """
    proc = subprocess.run(
        [sys.executable, str(tree / "scripts" / "check_contract_placement.py")],
        capture_output=True, text=True)
    if proc.returncode not in (0, 1):
        raise SystemExit(
            "the checker crashed rather than reporting failures "
            f"(exit {proc.returncode}):\n{proc.stderr.strip()[:2000]}")
    return {m.group(1) for m in re.finditer(r"^FAIL (.+)$", proc.stdout, re.M)}


# Assertions deliberately without a mutation, each with the reason. An entry
# here is a claim that breaking the rule is not expressible as a text edit to
# the two contracts — not that nobody got round to it. Keep it short; a long
# exemption list is this file failing quietly.
UNMUTATED_BY_DESIGN: dict[str, str] = {}


def _assertion_names(src: str) -> set[str]:
    """Every assertion label in the checker, by parsing rather than grepping.

    A regex over `("...",` also matches the phrase tuples the checker uses as
    fixtures, which inflates the gap and makes the coverage line a number
    nobody can act on — the exact species of false reassurance this file
    exists to remove, committed inside the thing that measures it. So the
    module is parsed and only the first element of each 2-tuple appended to a
    list named `checks` is taken.
    """
    names: set[str] = set()
    for node in ast.walk(ast.parse(src)):
        # Both forms: `checks = [...]` and `checks: list[...] = [...]`. The
        # first version of this handled only ast.Assign and found nothing,
        # which surfaced as every mutation naming a missing assertion — loudly,
        # which is the behaviour to keep.
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign):
            targets, value = [node.target], node.value
        else:
            continue
        if not isinstance(value, ast.List):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "checks" for t in targets):
            continue
        for elt in value.elts:
            if (isinstance(elt, ast.Tuple) and len(elt.elts) == 2
                    and isinstance(elt.elts[0], ast.Constant)
                    and isinstance(elt.elts[0].value, str)):
                names.add(elt.elts[0].value)
    # `checks.append((...))` for an assertion built conditionally. The docstring
    # above said "appended" from the first version and only the list literal was
    # read, so the denominator was short by one and that assertion could never
    # appear in the gap list — a number that does not mean what it says, which
    # is the defect this file exists to catch, in the file itself.
    for node in ast.walk(ast.parse(src)):
        if not (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "append"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "checks"
                and node.args):
            continue
        arg = node.args[0]
        if (isinstance(arg, ast.Tuple) and len(arg.elts) == 2
                and isinstance(arg.elts[0], ast.Constant)
                and isinstance(arg.elts[0].value, str)):
            names.add(arg.elts[0].value)
    return names


def coverage_gap(tree: pathlib.Path) -> list[str]:
    """Assertion names in the checker with neither a mutation nor an exemption.

    This is the property the fixture list cannot supply. Round 32 built the
    battery and round 33 measured it: 138 of 151 assertions had no mutation,
    including round 32's own headline one, which turned out to be four
    whole-file greps that a relocation walked straight through. A battery that
    cannot tell you it is short reads as complete for exactly as long as nobody
    checks — which is the defect this whole file exists to end, one level up.

    Reported, not enforced, and the distinction is deliberate: failing the
    build on an uncovered assertion would push the next person to write a
    mutation that passes rather than one that breaks the rule. It prints, it
    ranks, and `NAMED_BELOW` is what closes the gap.
    """
    src = (tree / "scripts" / "check_contract_placement.py").read_text(encoding="utf-8")
    names = _assertion_names(src)
    covered = {expected for *_, expected in MUTATIONS + EVAL_MUTATIONS}
    unknown = covered - names
    if unknown:
        return [f"mutation names an assertion that no longer exists: {sorted(unknown)}"]
    return sorted(names - covered - set(UNMUTATED_BY_DESIGN))


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tree = pathlib.Path(tmp) / "repo"
        tree.mkdir()
        for d in ("scripts", "skills"):
            shutil.copytree(ROOT / d, tree / d,
                            ignore=shutil.ignore_patterns("__pycache__"))

        baseline = run_check(tree)
        if baseline:
            print(f"FAIL the unmutated tree is already red: {sorted(baseline)}")
            return 1
        print("PASS baseline: the unmutated tree is green")

        for label, rel, old, new, expected in MUTATIONS + EVAL_MUTATIONS:
            f = tree / rel
            pristine = f.read_text(encoding="utf-8")
            n = pristine.count(old)
            if n != 1:
                failures.append(
                    f"fixture ({label}) no longer applies: its anchor matches {n} times in {rel}. "
                    "The contract moved; re-anchor the mutation rather than deleting it.")
                continue
            if new == MOVE_TO_END:
                mutated = pristine.replace(old, "") + "\n\n" + old + "\n"
            else:
                mutated = pristine.replace(old, new)
            f.write_text(mutated, encoding="utf-8")
            red = run_check(tree)
            f.write_text(pristine, encoding="utf-8")
            if expected in red:
                print(f"PASS {label}")
            elif red:
                failures.append(
                    f"WRONG GUARD ({label}): expected {expected!r} to go red, got {sorted(red)}")
            else:
                failures.append(
                    f"GREEN OVER ITS OWN DEFECT ({label}): {expected!r} passes with the rule broken")

        gap = coverage_gap(tree)
        if gap and gap[0].startswith("mutation names"):
            failures.append(gap[0])
            gap = []

    print()
    if gap:
        # Assertions and mutations are different units — several mutations can
        # exercise one assertion — so the first version of this line added them
        # together and printed a denominator that was not a count of anything.
        # A reassuring number that does not mean what it says is the failure
        # this file exists to catch, so it is spelled out.
        covered = len({expected for *_, expected in MUTATIONS + EVAL_MUTATIONS})
        print(f"COVERAGE {covered} of {covered + len(gap)} assertions have a mutation "
              f"({len(MUTATIONS) + len(EVAL_MUTATIONS)} mutations in total); "
              f"{len(gap)} have neither a mutation nor a stated exemption.")
        print("  A guard nobody has broken is a guard nobody has tested. The next few:")
        for name in gap[:8]:
            print(f"  - {name}")
        print()

    total = len(MUTATIONS) + len(EVAL_MUTATIONS) + 1
    for f in failures:
        print(f"FAIL {f}")
    print(f"{total - len(failures)}/{total} passing")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
