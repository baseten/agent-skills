# Notes — review-feedback

Reasoning for `rules/review-feedback.md`. Deliberately *not* bundled into
each skill: a copy of this per consumer would be design history with no reader,
and the audience for it is a person editing the rule, who has this checkout.

Moved here with the rule itself, from `backlog-orchestrator/NOTES.md`, where it
was reasoning about a section that no longer lives there.

**Why the kind test stays author-blind, including for the escalation (confirmed by the owner, Sept 2026):** the rule reads the same for a bot's question as for a human's — a thread needing intent, design, rationale or a decision is `NEEDS_USER`, reserved, and answered by nobody but the owner. This is worth writing down because it looks like an oversight and invites a "fix" back to an author-keyed rule, and that fix has already been made and reverted once here. Three reasons it is deliberate:

- **The two directions of error are symmetric and both were observed.** Automated reviewers raise architecture questions no run should answer; human reviewers file one-line nits any run can fix. An author key errs on both at once, which is why `auto-fix-reviewers` was deleted rather than re-defaulted (`rules/agent-policy-notes.md`, on why there is no reviewer-identity option).
- **Whose voice the reply would be in does not depend on who asked.** The escalation exists because an answer composed by a pass arrives as the owner's position (`resolve-pr-comment`, *Handling queries*). That is true in a bot's thread as much as a person's: the bot's thread is read by the humans reviewing the PR, and a confident wrong answer to a review bot is a confident wrong answer on the record.
- **Author is not reliably knowable anyway.** A bot posting through an integration, a human using a bot account, an account that changes hands — the test would key on the least stable field available, and `rules/posting-identity.md` already documents that authorship reads differently per transport.

The owner asked for the rule scoped to human comments and, when the asymmetry was put to them, confirmed author-blind. Do not narrow it without a new ruling.
