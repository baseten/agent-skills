---
name: review-docs
description: Review the documentation in a pull request by checking what it claims about the codebase against the codebase, in a review that terminates by contract — one pass plus one re-check, never a third. Replaces automated code review on a documentation-only PR and runs alongside it over the prose of a mixed one. Use whenever a PR changes specs, ADRs, READMEs, design docs or runbooks; when asked to review a spec or design doc, to check a document against the code, or to review only the docs part of a PR; and when an automated code reviewer is grinding rounds on a document without converging.
---

# Review Docs

Review the documentation in one pull request. **Two things make this different from the code review it replaces, and both are the reason it exists:** it stops at a point fixed in advance rather than when someone decides to stop, and it reads the document against the **codebase** rather than against itself.

This file is the contract; the reasoning behind its rules lives in `NOTES.md` beside it, keyed by section. NOTES explains; it never overrides.

Read-only over the PR and the repository: it verifies, it reports once, and it changes no file, pushes nothing, resolves nothing, and merges nothing.

## Inputs

- **the PR** — URL, or `owner/repo` and number;
- **the run's posting-identity map**, where the caller has one (`backlog-orchestrator`, *Posting identity*): the comment below is an authored write and needs its author selected from that map like any other.

**Nothing else is supplied, and in particular the round number never is.** The documentation paths, the commit to check against, and the round are all derived from the PR itself — a caller that could assert the round could assert its way past the budget.

## Why an automated code reviewer is the wrong instrument here

Both halves were measured on one backlog, on a run that took four spec PRs to merge (NOTES carries the numbers).

**Code review terminates because something eventually says *correct*** — a test passes, a compiler accepts, a type checks. Prose has no such oracle. Every fresh reading of a document finds another sentence the reader would have phrased differently, and the supply of those is unbounded, so a reviewer that stops "when there is nothing left to say" never stops. One spec PR ran **nine rounds and 28 threads**, and the document was not materially better after round four. Nobody was deciding to stop, because nothing in the process was supposed to.

**And it reads the document against itself.** All 28 of those threads checked internal consistency — does section 5 contradict section 9, is this term defined before it is used, does that table order match the prose above it. That is real, and it is shallow, and it is blind to the one failure mode that actually costs implementation time: **a document making a false claim about the codebase.** An implementer believes it, builds against it, and finds out late.

So this skill fixes the stopping point in advance, and spends its pass on the claims instead.

# 1. What this skill reviews, and what it replaces

Its scope is always **the documentation paths of the PR it is given** — never the code, in any PR. What changes with the diff is what it *replaces*.

**Documentation** means a path whose content is prose written for people to read, which no build, test, or runtime consumes — specs, ADRs, READMEs, design docs, runbooks, `docs/` trees. Not: code, configuration, schemas, fixtures, generated output, or a docstring inside a source file. **Cannot tell → not documentation**, and it falls to the code review, whose cost is one ordinary reading; accepting wrongly costs a file nobody reviewed (NOTES).

| the PR's diff | what runs | what this skill reviews |
|---|---|---|
| every path is documentation | **this, in place of** the repository's automated code review | all of it |
| documentation **and** code | **this alongside** the code review, which still runs in full over everything | the documentation paths only |
| no documentation at all | the code review alone; this declines in one line | nothing |

**On a mixed PR it never replaces the code review and never narrows it.** The code review still reads every file in the diff, documentation included; this adds the claims check that a diff-scoped code reviewer does not perform, over the prose it performs worst on. A gate reading both is satisfied by both — the code review's actionable findings and this skill's, neither standing in for the other.

**The mixed case is where the single most valuable finding lives**, which is why it is worth running at all: a document and the code in its own PR disagreeing. A code reviewer reads the diff's code and rarely tests the document's sentences against it, so *"the endpoint returns 202"* beside a handler returning 200 survives a review that looked directly at both. That finding is about the **document** — it is reported here as an ordinary `FALSE_CLAIM`, and never as a request to change the code, which is the code review's to ask for.

## Which codebase the claims are checked against

Not the same commit in the two cases, and choosing wrongly inverts every verdict:

- **Documentation-only PR → the base branch's head.** The prose is the only thing the PR changes, so the code an implementer will find is the code already there.
- **Mixed PR → the PR's own head.** The document may be describing the code landing beside it, and checking that against the base marks every correctly-documented change `FALSE` — a report that is wrong in exactly the cases the feature exists for.

Either way, **read the code; do not settle for a `grep` hit.** A matching token proves a name exists somewhere, not that the sentence is true about it — a claim confirmed by string match alone is this skill's own failure mode arriving inside its verification step (NOTES).

# 2. Extract the claims and check them

Enumerate every claim the document makes about the codebase, and give each one a verdict with evidence at `path:line`. A claim is anything an implementer could act on and be wrong about: a file path, a module, function, endpoint or table name, a config key, an environment variable, a CLI flag, a schema field, a default value, a sequence ("X calls Y"), a count, a stated current behaviour.

| verdict | meaning |
|---|---|
| `TRUE` | verified in the code at a named `path:line` |
| `FALSE` | the code says otherwise — always a finding |
| `PRESCRIPTIVE` | the document says what *will* exist; nothing to check today, and its premises check out |
| `FALSE_PREMISE` | a prescriptive claim resting on something that does not exist — *"add `status` to the `scans` table"* where there is no `scans` table — always a finding |
| `UNVERIFIABLE` | the repository carries no evidence either way — a verdict of its own, never folded into `TRUE` (`references/absence-is-not-a-verdict.md`) |

**The descriptive/prescriptive split is this skill's central judgment, and getting it wrong in either direction ruins the review.** A spec describes a codebase that does not exist yet. Marking its forward-looking sentences `FALSE` turns the whole report into noise, and a report that is mostly noise gets switched off — which is how the cheap mistake becomes the expensive one. But a prescriptive sentence still rests on **present-tense premises**, and those are checkable now. That is `FALSE_PREMISE`, and it is the highest-value finding here: it is the claim that looks like a plan, reads as unfalsifiable, and sends someone to write a migration against a table that was renamed two months ago.

Where a claim's tense is genuinely ambiguous, check the premises and say which reading you took. Do not resolve it silently in either direction.

# 3. What is a finding

| class | actionable — becomes an item |
|---|---|
| `FALSE_CLAIM` | **yes** — a `FALSE` verdict |
| `FALSE_PREMISE` | **yes** |
| `CONTRADICTION` | **yes**, and capped — see below |
| `NEEDS_AUTHOR` | **yes** |
| `NOTE` | **never** |

**These findings are not review-thread feedback, and the route they take to a merge decision is not the review path.** This skill's report is a timeline comment authored by the run, which `backlog-orchestrator`, *Merge policy and review feedback*, classifies as conversation by kind — that skill's discriminator, not an oversight here. So nothing groups these into a review round, and no `repair-pr` pass with `repair type = review` will ever see one.

They travel the **finding** route instead, which exists for exactly this: work evidenced by something other than a thread. An actionable finding is **returned to the caller**, which carries it into the run's findings and so into `summarize-tranche` — a document change this PR still needs is an `IN_FLIGHT_FIX`, one that must not ship as it stands is also a `MERGE_RISK`, and a `NEEDS_AUTHOR` is a `DECISION`. Invariant 12's gate already refuses to open over any of the three, and `repair-pr` already accepts a finding as a repair type. **Nothing new is needed at the gate, and nothing here restates it** — a `NOTE` simply never becomes an item, whatever it says and however many there are.

On a **mixed** PR the two reviews are independent and both are owed. A clean pass here speaks only for the documentation paths and never for the code review, whose own findings reach the gate by their own route.

- **`NEEDS_AUTHOR`** — a question only the author can answer, admitted **only where you can name what would be built wrong without the answer.** That test is the whole class: without it, every sentence anyone found unclear qualifies, and the class becomes the 28 threads again under a new name.
- **`CONTRADICTION`** — two parts of the document disagreeing **about what to build**, so an implementer has to pick and cannot. Differing emphasis, ordering, or level of detail is not a contradiction. **Capped at three.** Past three, emit a single finding saying the document contradicts itself structurally and needs its author, and stop enumerating: the fourth instance tells the author nothing the first three did not, and a list of them is how a review stops being read.

**Not findings, at any count:** phrasing, register, word choice, heading order, table ordering, terminology preference, a term defined after its first use where no reader would actually be misled, internal inconsistency with no consequence for what gets built, and everything of the shape *"I would have written this differently."* These are not withheld because they are wrong. They are withheld because they are unbounded, and admitting them is precisely how nine rounds happen.

# 4. The rounds, and why there are two

**Round 1** — the full pass above: extract, verify, classify, report.

**Round 2** — reads **only round 1's findings** and the diff since, and says of each: fixed, not fixed, or fixed wrongly. It raises **no new findings.** Re-reading a rewritten section is a fresh unbounded reading, and that is the loop this skill exists to break; a section that got better in a way nobody asked about is not an occasion to say so.

- **The one exception**: a fix that introduces a new `FALSE_CLAIM` or `FALSE_PREMISE`. That is the failure class the whole skill is for, and the fix created it, so it is reported — inside the finding whose fix created it, never as a new finding of its own, and it **earns no additional round.**

**There is no round 3.** Whatever is unresolved after round 2 is named and handed to the author: the findings still open, with their evidence, and the statement that the review is over. A caller invoking a third time gets a **declined pass naming the residue** — the decline is the deliverable, not an error, and it posts nothing. **A decline is a completed outcome, not a pass that failed to happen**, and a caller confirming that a routed review took effect reads it as one (`backlog-orchestrator`, *Implementation worker contract*, says so at the confirmation step): the residue it returns is the review's result, already reported in round 2's comment.

**The round is read off the PR, not off run state**: no prior `review-docs` comment → round 1; exactly one → round 2; two → declined. A restarted session, a different worker, and a person invoking by hand all count the same rounds, because the count lives where the comments do (NOTES).

The budget is **per PR, not per document.** A document that comes back as a new PR gets its own two rounds — a new PR is a new decision to review, and the loop this bounds is the one inside a single PR.

**This budget is a contract rule, not a policy key, and it is deliberately not configurable** (NOTES: a budget is a ceiling, and the run that spent nine rounds would have spent any ceiling it was given).

# 5. The report is one comment

One PR comment per round. **Never a thread per finding.** Two independent reasons, and the second is not this skill's to relax: 28 threads was not the review being thorough, it was the review being unreadable — a reader triaging a wall of threads cannot see that only two of them were about the code at all. And **the run never roots a review thread on a PR it is driving** (`backlog-orchestrator`, *Merge policy and review feedback*, states that prohibition and the discriminator that depends on it); a run-authored root would make this report indistinguishable from a reviewer's instruction.

```text
## Documentation review — round <1|2> of 2

<N> claims checked · <M> findings (<K> actionable)
Reviewed: <the documentation paths>, against <commit>

### Claims about the codebase
| claim | verdict | evidence |
|---|---|---|

### Findings
1. [FALSE_CLAIM] <what the document says> — <what the code says, at path:line> — <what to do>

### Notes
<non-actionable observations, or "None.">

Round 2 is the last round; unresolved findings after it go to the author.
```

- **Name the paths reviewed and the commit checked against.** On a mixed PR a reader who cannot see the scope will read a clean report as the code having been reviewed too, and this comment sitting beside a code review makes that misreading easy rather than perverse.
- **Say which round this is and that there is no third**, in the comment. A reader has to be able to see that the review terminated by design rather than by neglect — that visibility is half of the fix, because the failure being corrected was nobody knowing whose job it was to stop.
- **Every finding carries its evidence at `path:line`.** A claim reported false without the code that makes it false is an opinion in a table.
- Round 2's comment reports each round 1 finding's outcome and **repeats nothing else** — no re-verification table, no re-listing of notes.

**The comment follows the authored-write-form rule** (`references/authored-write-form.md`) and **carries the attribution footer**, because nobody read it before it was posted — that rule's approval test answers No for every comment this skill writes. Its brevity rule governs how each element is written and never whether it is written: the claims table and each finding's evidence are the write's **required contents**, and a table cut to fit a word count is the review deleting its own evidence. Its author follows the posting-identity rule (`backlog-orchestrator`, *Posting identity*, states it once); this comment is **not** the review-trigger comment and carries none of that comment's exemptions.

# Enabling it in a repository

A repository routes documentation-only PRs here by documenting it in its own `CLAUDE.md`/`AGENTS.md`, which `create-pr` already reads for review-trigger conventions (`create-pr`, *Automated review trigger*, owns the routing):

```text
Documentation-only PRs (every changed path is prose) are reviewed by the
`review-docs` skill instead of the repository's automated code review.
```

A repository wanting the mixed case routed automatically as well says so too, naming it as an addition:

```text
On a PR changing both code and documentation, `review-docs` also reviews the
documentation paths, alongside the code review, which still runs in full.
```

**Mixed routing is opt-in and off by default, while a hand invocation on a mixed PR always works.** A one-line README touch-up on a feature PR does not need a claims audit, and a second review comment on every PR that grazes a `docs/` path is how a useful report becomes something people scroll past — the cost this skill is otherwise spent avoiding (NOTES).

**Installed is not enabled.** Until a repository states the documentation-only line above, `create-pr` has no convention to read there and keeps triggering ordinary code review, silently — the skill is present and inert. Enabling it is a change in that repository, never here, which is also why this contract names no repository: nothing here has to change when the next one adopts it, or stops.

# Boundaries

- Reviews; never edits the document, pushes a commit, resolves a thread, or merges.
- **Never reviews code, on any PR.** On a mixed PR the code is the code review's, and a finding about the document is phrased as a claim the document gets wrong — never as a change the code should make, even when changing the code is obviously the better fix. Say which it is and leave the choice with the author.
- Never re-reviews a mechanical push (`create-pr`, *Substantive vs mechanical pushes*, owns the test); it consumes no round either.
- Never opens issues or files follow-ups. A finding needing work beyond this PR is reported as a finding; `summarize-tranche` is what turns run findings into action points.

# Output

Return: PR URL and the repository; which case the diff fell in (documentation-only, mixed, or no documentation) and the documentation paths reviewed, with the commit their claims were checked against; where nothing was reviewed, which review should run instead; round number and whether a further round exists; claims checked by verdict; findings by class, with the actionable count stated separately; the posted comment's URL; **the posting-identity observations made, one entry per `(transport, credential)` pair written through, with the write kind** — on a documentation-only routed PR no review-trigger comment is posted at all, so this comment is the run's only comment-kind evidence and a caller that drops it loses what its next trigger selection reads (`create-pr`, *Automated review trigger*); and anything that could not be verified, with why.
