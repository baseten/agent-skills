# write-spec — design notes

Reasoning behind `SKILL.md`, keyed by its section names. NOTES explains; it never
overrides.

## Write spec

**Why this skill exists (owner's ruling, 2026-11-04):** the pipeline is `write-spec`
→ `plan-feature` → `conductor` → the runs. A spec is the one document a plan is cut
from, so it is its own step with its own conversation, and the conductor's planning
section was removed rather than grown. The owner asked for it to be simple: one
brief in, one document out, a link back.

**Why it never writes issues:** splitting the work is a different decision with a
different reader. Every baseline below already refused to write tickets, so the
rule costs nothing and stops a spec run from pre-empting the plan.

**Prior art.** The template's shape — problem, goal, non-goals, success criteria,
an approach with its rejected alternatives, constraints marked where they were
decided — and the habits of researching code through a subagent with a fixed
brief, of amending a rejected draft in place, and of re-showing only what changed
come from [essmahr/planet](https://github.com/essmahr/planet), a coworker's planning plugin. It carries no licence, so
nothing here is copied from it: the ideas are paraphrased, and the parts that
depend on its CLI, hooks, private store or plan mode are left out.

## Baselines (2026-11-04, before the contract was written)

Three realistic prompts, each given to a fresh subagent with no skill and no file
access, answering as a dry run:

1. **A Slack thread, two repositories, no design.** It grepped the code in its own
   thread, asked nothing before drafting, chose a two-phase split itself, published
   a private page the owner first saw as a finished link, and filled every section
   (rollout, metrics, risks) at 1,200–1,600 words. Questions came after the fact,
   batched.
2. **A product issue with a design link, "put it where we keep specs".** It
   delegated code reading to a subagent, asked four questions together (one about
   storage), and committed a markdown file on a branch with a draft PR — closest to
   this contract — but its outline carried a test plan and open-questions section
   regardless of content.
3. **A pitch page, two decisions already made, a known specs database.** It recorded
   both decisions as settled constraints without reopening them and left empty
   sections out, but wrote straight into the database without showing the draft.

**What the contract targets from them:** a write before the owner has seen the
text (1, 3); a storage location chosen differently on every run (1–3); code read in
the main thread (1); decisions the run made for the owner (1); no section listing
the options rejected (1–3). What they already did well — no tickets, decisions kept
as constraints — is kept as one line each.

## Configuration

**Why `repo-file` is the default:** a file in the repository is reviewable as a PR,
versioned with the code it describes, and needs no connector, so the skill works in
any session. A team that keeps specs elsewhere sets `spec.storage` once, in the
policy file, or a thin skill passes it. **Why falling back silently is forbidden:**
a spec written to the wrong home is one nobody finds; asking costs one question.

**The hooks a thin skill uses** are the four `spec` fields, passed as invocation
arguments: a work wrapper sets `storage: document-store`, its database as
`location`, its template's URL as `template`, and its naming convention as
`naming`. Nothing else in the contract is deployment-specific.

## Rules

**Why nothing is written before the go:** baselines 1 and 3 both wrote first and
showed after, which puts the owner's first read on a published artifact. The spec
is shown in chat and written once it is approved. **Why nothing here reads a
footer (owner's ruling, 2026-11-05):** a transport can append one to every write, so
its presence means nothing.

**Why prompts are never recorded verbatim:** the owner's working conversation is not
the spec's content, and the prior art found a captured-prompt store grew noisier
than useful.

## 1. Gather

**Why the research brief is fixed and its reply capped:** a free-form research
dispatch grows extra instructions and runs long, and the planner should spend its
context on the five lines that matter. Question (4) — what the work assumes that
the code contradicts — is the one a brief writer cannot answer and the one that
most often changes a spec. **Why a cheaper model:** the questions are factual and
answered with paths.

## 2. Ask

**Why blocking questions are batched and design discussion is not:** see
`rules/operator-output-notes.md`, *Questions*.

## 3. Draft

**Why no caps and no mandatory sections:** the prior art measured both being filled
mechanically — a section kept because the template had it, a length target met by
padding — and baselines 1 and 2 did the same unprompted. A section with nothing
real is left out instead. **Why *Considered*:** a reviewer's first question about an
approach is what else was looked at; none of the baselines recorded it. **Why
constraints say where they were decided:** a constraint with no origin gets
re-litigated; one marked `(owner, <date>)` does not.

**Why amend in place and re-show only the change:** regenerating a rejected draft
silently changes parts the owner had accepted, and re-reading a whole document for
a one-section change is the cost the prior art measured on its re-cuts.

## Decision scenarios

Pinned in `evals/evals.json`:

- no storage configured → a markdown file under `docs/specs/` on a branch with a
  draft PR, after the go (`the-default-storage-is-a-repo-file-with-a-draft-pr`);
- blocking questions together with defer, design one at a time
  (`blocking-questions-are-asked-together-with-defer`);
- a rejection amends in place and re-shows the change
  (`a-rejection-amends-in-place-and-reshows-the-change`);
- a decision already made is a constraint, not a question
  (`a-decision-already-made-is-a-constraint-not-a-question`);
- no issues are written, even when asked in passing
  (`the-spec-run-writes-no-issues`);
- configured storage this session cannot write is asked about, not substituted
  (`unwritable-storage-is-asked-not-substituted`).
