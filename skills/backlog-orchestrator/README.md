# backlog-orchestrator, for humans

This file is for people. The model that runs the skill never reads it — it reads `SKILL.md`, which is written as a dense rule contract and is hard going for a human. This page explains what the orchestrator does in normal words, names the moving parts, and defines the vocabulary `SKILL.md` uses. If you change or add a coined term in `SKILL.md`, update the glossary here in the same PR.

## What it does, end to end

You point it at a set of tracked issues that depend on each other — for example a GitHub parent issue with sub-issues, some blocked by others. It then:

1. **Checks the plan before doing anything** (`validate-backlog`): reads the dependency graph, makes sure the issue set is complete and the ordering makes sense, and — crucially — proves that the credentials it's reading with can actually *see* all the dependency links, because a restricted token silently returns a partial graph that looks complete. Where the platform offers no dependency read at all from here (GitHub without an authenticated `gh` is the common case), no such proof is possible: the run then proceeds from what the issue text says, with that limitation recorded up front and carried into every dispatch rather than papered over.
2. **Starts a worker per ready issue** (by default up to 4 at a time and 12 new issues per run — an invocation or the repository's config can change both caps): each worker implements one issue in an isolated checkout and opens a pull request (`implement-issue-core` → `create-pr`). On the usual remote runtime a worker is its own Claude session; where that isn't available, workers can also run as workflow agents, as in-process subagents, or one at a time inside the orchestrator itself.
3. **Supervises**: watches workers and their PRs in a loop — collects what each worker learned about the dependency graph, rescues unsaved work from stuck workers, dispatches bounded repair jobs when CI or review fails (`repair-pr`), starts newly-unblocked issues as PRs merge, and shuts workers down when they finish.
4. **Stops cleanly** ("settled"): when nothing more can start and every open PR is individually finished for now — its automated review completed and every actionable finding dealt with, CI done, the PR not stuck waiting on the user, no worker still running, and no worker session the run created still alive — it writes a plain-language summary (`summarize-tranche`), walks you through the decisions only you can make (`settle-outstanding-decisions`), ranks the PRs by what merging them unblocks (`plan-merge-order`), merges only where a repository's own config file explicitly allows it, and reports everything it did and everything still open.

Most of `SKILL.md`'s size is rules for the ways steps 1–4 have gone wrong in practice. Nearly every rule traces to a real incident, recorded in `NOTES.md`.

## The moving parts

- **Workers** are disposable single-issue sessions. They report what happened as a comment on their own PR — never on the issue, because three skills scan issue comments for "blocked by X" statements and would mistake a status note for a real dependency, permanently.
- **The pre-flight validator** (`validate-backlog`) gates every dispatch. Its hardest job is *transport visibility*: proving a credential can see the whole dependency graph, which can only be done against a link whose existence is already known some other way.
- **Checkpoint rescue**: when a worker gets stuck with uncommitted files, the orchestrator saves them by committing to a hidden git ref (`refs/checkpoints/...`) via a tested script (`scripts/checkpoint-capture.sh`) — never by touching the worker's own branch or index.
- **Session hygiene**: every cycle the orchestrator compares the sessions the runtime says are alive against what it thinks it launched, because a leaked worker session keeps a container and can keep waking itself hourly at real cost. A run cannot call itself finished while a session it created is still alive.
- **Posting identity**: when the orchestrator writes comments, it posts through whatever connection it would use anyway and reports *who* the comment appeared to come from (you, or a bot identity). The one exception is the comment that triggers automated review, which only works when it comes from you.
- **The merge gate**: it never merges on its own judgment. A repository must opt in via `.claude/backlog-orchestrator.json` (`auto-merge: true`), and even then a merge waits until nothing in the batch has an unanswered decision.
- **Budgets everywhere**: new issues per run, concurrent workers, repair rounds per PR, one model escalation, and a no-op budget with backoff on every recurring check-in, so nothing loops forever at your expense.

## Glossary

Terms `SKILL.md` coins, in plain words. Section names in parentheses point to where each is defined.

| Term | Meaning |
|---|---|
| **tranche** | One run's batch of work: the issues it adopted and the PRs it produced. |
| **manifest** | The parent issue (or explicit issue list) that defines the run's scope. |
| **bounded scope** | The fixed set of issues the run may work on. Nothing outside it is ever started, even if a merge unblocks it. |
| **READY / frontier** | An issue whose prerequisites are all met is READY; the frontier is the current set of READY issues. A merge "advances the frontier" by making more issues READY. |
| **validated DAG** | The dependency graph after the pre-flight checks; the only graph scheduling trusts. |
| **worker** | A disposable sub-session implementing exactly one issue (or one repair). |
| **dispatch** | Launching a worker, with a prompt that carries everything it needs. |
| **releasing a worker** (*Releasing a worker*) | Shutting a finished worker down. On remote sessions this means archiving the session — a live one holds a container and can keep waking itself. |
| **the releasable test** | The two conditions for shutdown: the worker is genuinely done, and nothing unsaved is left in its checkout. |
| **recovery ref / checkpoint capture** (*Checkpoint compliance*) | The hidden git ref where a stuck worker's unsaved files are rescued, via the tested script. |
| **durable remote state** | Work that survives the run dying: a pushed branch with a PR. |
| **invariant 1** | The run's own memory and notes are a cache; only the tracker, git remote, and runtime are the truth. |
| **invariant 12** | The merge gate. A merge needs all of: the repo's config opted in, nothing decision-shaped outstanding anywhere in the batch, green CI on the PR's current head, no merge conflict, a clean review, no unreconciled rescue ref, not a deliberately held draft, and a dependency view that was proven or explicitly answered for. |
| **invariant 13** | A merge is a scheduling event (it can start new work), never an end state. |
| **settled** (*Settled tranche*) | Nothing more can start and every PR is individually finished-for-now. Settled ≠ finished: the next move is a human's. |
| **transport** (*Transport precedence*) | Any way of reading/writing the tracker or forge: an MCP tool, a CLI, raw HTTP. Ordered by preference. |
| **transport visibility / visibility proof** (*Proving a transport can see the graph*; canonical in `validate-backlog`) | Evidence that a credential can see all the dependency links in scope, established against a link already known to exist ("known-true case"). A restricted credential returns a partial graph with no error, so absence through an unproven transport proves nothing. |
| **`dependency transport unavailable`** | The tracker offers no dependency read at all here (e.g. GitHub without `gh`). A known, uniform limitation accepted up front — different in kind from an unproven view. |
| **unproven dependency view** | A worker couldn't establish that its blocker list was complete. The most serious `NEEDS_USER`: it holds every sibling scheduled through the same read. |
| **unverifiable prerequisite** | A dependency whose completion can't be observed from the repo/tracker (e.g. "the release happened") — a question for a person. |
| **outcomes** (`PR_OPEN`, `BLOCKED`, `BLOCKED_EXTERNAL`, `FAILED`, `NEEDS_USER`, `NO_CODE_CHANGE`, `REPAIRED`) | The terminal states a worker returns. `BLOCKED` = an in-scope prerequisite was unmet (the graph was wrong); `BLOCKED_EXTERNAL` = only out-of-scope work is missing (a known wait). |
| **worker report vs blocker record** (*How a worker's report actually reaches you*) | A report is what the worker observed (goes on its PR); a record is what the orchestrator verified and wrote down (goes on the issue). Only records count as dependencies. |
| **the worker-report marker** | The exact first line (`**Worker report — unclassified evidence, not a dependency record.**`) that makes dependency-scanning skills skip a report that ended up on an issue anyway. |
| **one-line summary / `needs_action`** | The single line of free text a remote worker's runtime keeps about its last turn — a pointer to go look, never a complete list. |
| **posting identity** (*Posting identity*) | The map of who comments actually appear to come from, per connection and credential and kind of write, learned only by reading a posted comment back. |
| **review trigger / bootstrap** | The "@codex review"-style comment that starts automated review. It only works posted as you, and the first one in a run is sent on prediction and verified by read-back. |
| **coverage finding** (*Outcomes*) | A dependency satisfied on paper (issue closed, PR merged) whose actual capability is missing from the code. Such a PR must not auto-close its issue. |
| **deep vs shallow validation / escalation** | Shallow checks declared links; deep reads the code behind them. Certain shapes (cross-repo edges into earlier merges) force deep mode. |
| **explicitly held draft** | A draft PR a human deliberately keeps in draft (it was ready once and was returned) — excluded from merging entirely. |
| **per-PR block** | The record the run keeps per PR: heads, budgets, subscription state, worker session id, draft state. |
| **event subscription / no-change preflight** (*Event handling*) | The per-PR watch that delivers CI/review events, and the rule that a "nothing changed" claim must first prove something was listening. |
| **arming the wait / no-op budget** (*Arming the wait when nothing is in flight*) | The subscription + scheduled check-in a settled run sets up, and the cost cap on it: 8 fruitless wakes with growing gaps (~21 hours), then it stops and says so. |
| **countermand / ambient posture** (*Countermanding the worker's ambient supervision posture*) | Remote worker sessions inherit a default habit of watching their own PRs and scheduling their own check-ins; the orchestrator overrides it because it is the single supervisor. |
| **release reconciliation / provenance key** (*Parent supervision loop*, step 11) | The every-cycle comparison of the runtime's live sessions (filtered by `parent_session_id`) against the run's records — mine-and-alive gets handled now; another run's are reported, never touched. |
| **state block** (*Progress / checkpoint output*) | The short status snapshot (budgets, workers, sessions created/archived/alive, PRs, check-in state) emitted every supervision cycle. |
| **stacked PRs / restack / `Depends on:`** | PRs based on each other's branches; after a parent merges, children are rebased so its commits don't leak into their diffs. The `Depends on:` body line records the parent. |
| **repair cycles / model escalation / locus evidence** (*Model and skill policy*) | Bounded repair rounds per PR; one round may run on the strongest model, triggered only when a new finding lands in text an earlier repair wrote. |
| **rulings / `DECISION` / `MERGE_RISK` / `NEW_ISSUE` / `IN_FLIGHT_FIX`** (*Settled tranche*) | Action-point kinds the summary raises; a ruling is your recorded answer. A ruling that requires code changes re-opens the run. |
| **resume frontier** | The READY-but-not-started issues named in the closing report so the next run adopts them instead of rediscovering them. |
| **lost worker recovery** | What happens when a worker becomes unreachable: rescue its work from durable state, then redispatch within budget. |
