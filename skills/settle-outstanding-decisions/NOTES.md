# settle-outstanding-decisions — design notes

Companion to `SKILL.md`. That file is the contract; this one holds the reasoning, keyed by section. Read a section's note before changing its rules or when applying them to a case the contract doesn't obviously cover. Nothing here overrides the contract.

## Collects and records; does not act

`summarize-tranche` and `plan-merge-order` hand the next move back to the caller, and this skill does the same, for the same reason: every action a ruling calls for already has an owner — `repair-pr` for a fix, `merge-stack` for a merge, the orchestrator's frontier logic for a held path — and a walkthrough that mutates PRs between questions makes the owner wait mid-conversation on work they have not reviewed.

## Attendance is the precondition

**Why this skill and the orchestrator's `AskUserQuestion` prohibition are one rule, not a conflict:** nobody watches an unattended worker's permission prompts — the call does not pause the worker, it deadlocks it, and a deadlocked worker's run is wasted. This skill exists to occupy a human's attention with the same tool. Both positions follow from *ask only where someone is watching to answer*; the distinguishing property is attendance, never the tool.

**Why the frontmatter no longer forbids model invocation:** the orchestrator's settled-step request is a model invocation, so a flag forbidding those would forbid an intended caller. The description now carries the scoping the flag used to. What bounds the cost of a stray selection is the rest of the skill — unattended it asks nothing, and attended the qualifying bar keeps the questions scarce and the zero case one line.

**Why the decline points at the sites, not the summary:** the summary is an aggregation that reaches the run as closing output, which invariant 1 (`backlog-orchestrator`) classifies as cached run state — it does not survive session loss. The worker records on PRs, the review threads, and the tracker comments are durable; the aggregate may be gone by the time anyone reads it, the decisions will not be.

**Why the unattended path writes nothing:** a durable record of unanswered questions is a different feature with different requirements. This skill once had one and it was deleted — unimplementable (no comment-edit capability exists to maintain it) and unnecessary (the decisions persist at their own sites, so a durable *aggregate* is a convenience, not the thing keeping them alive). Every ambiguity in the unattended rules is an invitation to rebuild it; resist.

## What qualifies / Owner action items

**Why the bar is trust-shaped:** an owner asked to ratify things the run could have decided itself stops reading the questions, and then the one that mattered gets a skimmed answer. The same failure drives the action-item segregation: a non-choice put through a question prompt ("create the token / don't") teaches the owner the prompt is padding.

## Discovery

**Why the summary seeds rather than being one source among five:** two skills independently scanning the same PRs against different bars will disagree about what is outstanding; seeding removes that disagreement and turns the remaining sources into enrichment — what a question needs and a summary action point does not carry, chiefly the 2–4 mutually exclusive options and their consequences. Declined seeded items are reported (never silently dropped) because an owner who saw an item in the summary will otherwise go looking for its question.

**Why a site-less `NEEDS_USER` item is marked:** the unattended decline's promise — the decisions outlive the session at their sites — does not cover an item the parent derived and never wrote anywhere. A decline naming it as the one item that will not survive is honest; one that quietly includes it in "they live at their sites" repeats the false durability claim, one source further down.

**Why deduplication precedes filtering:** the already-ruled bar is per-site. Filter first and an alias whose site holds the ruling retires while its twin, whose site does not, survives and gets asked again — the idempotency the settled step relies on, defeated by the same decision wearing two names. Merging aliases first, then checking every URL the merged item carries, closes that hole.

## Ordering

**Why a fork and its dependents never share a call:** `AskUserQuestion` returns a chunk's answers together, so a fork and a question it can moot, asked in the same call, are answered simultaneously — there is no moment in between at which the dependent one can be retired or reformulated. The owner rules on a choice the first ruling has already eliminated, and the walkthrough records it as though it stood. Hence closing the chunk after the last moot-capable decision and re-running the bar before composing the next.

## Recording the ruling

**Why immediate per-chunk recording:** an interrupted walkthrough must not lose the answers already given; batching to the end puts every earlier ruling at risk of the session dying on a later question.

**Why the marker, not the posting account, carries the owner's authority:** posted under a distinct agent identity, the record reads as what it is — a transcription of the owner's interactive answer. Posted as the invoking user (the posting-identity rule's degraded path), the marker is all that separates the owner's ruling from the owner appearing to comment on their own question. Either way the explicit "owner ruling, given interactively, dated" marker is what distinguishes a ruling (which is the review) from a default (which review can overturn) — which is why it is mandatory.

## Output

**Why the identity return is per pair AND per write kind:** a single walkthrough can record rulings at sites needing different transports (a GitHub PR thread through MCP, a Linear issue through its CLI), and one pair alone can carry rulings of distinct write kinds — a PR timeline comment and a review-thread reply — which the platform may author differently; an observation answers only for its own kind. Returning only a pair's first ruling drops whatever the later ones established — a later transport's entry, or a later kind through the same pair — and either loss is exactly the invoking-user path a later trigger may need, or the evidence a later review reply degrades without.

**Why "mooted by <ruling>" stays distinct in Declined to ask:** the other three reasons say the decision was never worth the owner's attention; this one says it was, right up until their own answer retired it. Collapsing them loses the fact that a ruling had a consequence beyond its own question — the thing a later reader most needs to reconstruct why a decision they remember raising never got asked.
