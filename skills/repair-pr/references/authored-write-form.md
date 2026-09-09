# Authored write form

This is the rule other skills mean when they cite *authored write form*.

**It is not a skill and nobody invokes it.** It is a shared rule, held once at
`rules/authored-write-form.md` and copied into each skill that applies it by
`scripts/refresh_shared_rules.sh`. A skill reads its own
`references/authored-write-form.md`, which works after `bootstrap.sh` has
installed only that skill's directory, and travels with the skill if it is
moved into a plugin. Edit the source, never a copy; CI fails if they diverge.

`backlog-orchestrator`, *Posting identity*, decides which **author** a write
carries. This decides **what the write looks like** once it is authored, and the
two are independent: identity is a fact about the credential, form is a fact
about the text.

Posting identity decides which **author** a write carries; this decides **what the write looks like** once it is authored. It covers every authored forge/tracker write made on the run's behalf — PR bodies, timeline comments, review replies, worker reports, recorded rulings — whichever skill or worker performs it. **This section is the rule's only statement; the skills that write defer here rather than restating it.** Two rules: keep it short, and mark the writes nobody read.

**Keep it short, and say why rather than what.** The reader is a person with a queue of these; length is a cost they pay and the run does not, which is the asymmetry that makes it worth a rule. A review reply is one line: `Fixed in <sha> — <what changed>.` and nothing else above the footer.

A **PR body** is the case with a budget, because it is the one a reviewer has to read before they can start:

- **300 words of prose above the fold, maximum** — linkage, background, description and the testing summary together. It is a ceiling for a genuinely large change, not a target; most come in far under. A manual test checklist does not count against it and is capped at 8 grouped items, because a fifteen-item list gets skipped entirely and six get done.
- **Background: 2-4 sentences** — the problem, not its history. **Description: one paragraph, or at most 5 bullets** — the solution and why this one.
- **The body states intent, not content: background, why this solution where a reviewer might expect another, what is deliberately in and out of scope, and what could break.** So: no file-by-file inventory and no "surface area changed" list, no restating what a function now does, no investigation log ("grepped for", "reproduced with", "verdict:"), and no account of the order things went wrong in. **The diff is the content**, and a description that competes with it buries the part only a person could have written.
- **Depth goes in a collapsed `<details>` block or a commit message**, not above the fold. Over budget means **cut**, never compress by deleting whitespace while keeping every fact.
- **A genuinely trivial PR gets a near-empty body.** Do not manufacture prose to fill a template, and delete a template heading with nothing real under it rather than padding it. **Where the template's gap is something the author can supply and this run cannot** — a capture of a visual change, a note only they hold — leave the heading with one line naming what is needed instead of deleting it. Deleting is right where the section will never apply to this change; it is wrong where it hides a gap, because the reader then sees an absent section rather than a missing screenshot, and cannot tell which.
- **Where a change is user-visible and the repository provides a way to capture it** — a screenshot skill, a Storybook or VRT harness, a browser-driving test — **capture one**: it is the only part of a body the diff cannot supply. Where it does not, describe **what changed visually** and say that no capture was available — never describe the capture itself, which is the same fabrication one step back. **Never imply a visual check that was not performed.** The unconditional form of this rule belongs to a human author's style guide, where the actor can always take a screenshot; this contract's actor frequently cannot, and an obligation it cannot meet is discharged with a fabricated "N/A" (NOTES).

**Where the repository or the user's own configuration documents a PR-description style guide, that guide governs and its budget wins** — `create-pr` already reads `CLAUDE.md`/`AGENTS.md` before writing a body, and a personal guide is where voice rules live, which are not this section's to state. The rules above are the floor for a repository with no guide of its own. Where the write's own site mandates contents — `create-pr`'s linkage and `Depends on:` lines, `settle-outstanding-decisions`'s ruling record, the worker report's marker first line **and the judgment its subtraction requires** (Before dispatch, step 11) — **those contents win**: brevity governs how each required element is written, never whether it is written, and one dropped to shorten a write is a defect, not a short write. Where a site defines its contents as a **subtraction** rather than a list, brevity may not convert the subtraction into a list: everything the subtraction leaves in is required, including whatever nobody has thought to enumerate.

### The attribution footer marks the writes nobody read

**The footer is not a stamp on everything the run types. It marks a write no person read before it was posted.** At every write site the test is one question, asked of the write in front of you:

> Did this run obtain the invoking person's approval of **this exact text** before posting it?

**No → the write carries the footer. Yes → it does not.** Nothing else decides it: not which skill performs the write, not what typed the words, not whether the run feels confident about them.

```text

---
_Generated by [Claude Code](https://claude.ai/code)_
```

**Why a marker on everything would carry no information (NOTES).** The reader who matters is deciding how much scrutiny a write has already had. A banner on every write cannot separate the unedited automated reply — where they should read closely, because nobody has — from a body its author drafted with an agent, edited, and posted under their own name. Attended work is already attributed durably where attribution belongs: commits carry `Co-Authored-By: Claude`. A footer added on top of that says nothing new and invites a reviewer to skip a description its author owns, which is the failure the whole brevity rule above exists to prevent, arriving from the other direction.

**Approval means this exact text.** A person who authorised the run, approved the plan, or asked for the PR has not approved a body they have not read. Sitting in the session is not approval either. Where the run cannot say the person read the text it is about to post, the answer is No and the footer goes on — that is the safe direction, and it is the common one.

Applied to the writes these skills actually make:

| write | approval | footer |
|---|---|---|
| Worker report, automated review reply, mechanical supervision comment, a PR body opened by a dispatched worker | nobody read it | **yes** |
| A `create-pr` body drafted interactively, shown to the user, and confirmed or edited by them | this exact text | **no** |
| A `settle-outstanding-decisions` recorded ruling | **the complete comment**, shown to the owner and approved or edited — approving the answer inside it is not approving the record built around it | **no** where that happened, **yes** where it did not |
| A `NEEDS_USER` draft reply | not a write at all — material for a person, who authors it when they post it | **no** |
| The review-trigger comment | — | **no**, see below |

Forge avatar rendering is **transport-dependent and not a signal a reader can rely on** — the same run's writes appear differently depending on which surface authored them, and on the degraded path of Posting identity, which is the common one, they carry the invoking user's login with nothing marking them as agent-written at all (NOTES: what the avatar actually tracks). **That argument is why the footer exists, and it is an argument about the unattended case only**: it says a reader cannot tell that nobody reviewed this text, which is exactly what the footer now tells them. It does not extend to a write a person authored under their own name.

- **Where a body reports verification, it reports the checks a reader has to run and the tests that now cover the work — not the ones the forge already ran.** Formatting, linting, type checking and the test suite are reported by the checks on the PR, so listing them says nothing a reviewer did not have, while reading as though the length were diligence. What only the author knows is which manual exercise the change actually needs, and whether a test was added or an existing one already covers it: a line or two on that, and the manual steps grouped rather than enumerated one per assertion.
- **The footer says the posted text went unread; it does not say who wrote the content.** The two are different claims and can both be true of one comment, so **an attribution already present is never itself a reason to omit the footer** — only the approval test is. A `settle-outstanding-decisions` ruling carries an owner-ruling marker attributing the content to the owner, and still carries the footer unless the owner was shown and approved the complete comment (that skill, *Recording the ruling*). Reading the marker as licence to drop the footer is the mistake this bullet exists to block, and an earlier version of this section made it.
- **A write with no body carries no footer, because there is nowhere to put one.** A merge, a base retarget, a native dependency edge: the form rule reaches the writes that have text, and brevity and the footer both have nothing to govern on a write that has none (`merge-stack` applies this to its own three write kinds). This is not an exemption and needs none — it is what the rule says when the write has no prose.
- **The footer is not identity evidence, and it is not a discriminator either.** It is text this run wrote, so it establishes nothing about authorship: the posting-identity map is still built only from observed write authorship, and a footer is never read back as an observation. Nor may anything test for it to decide whether a comment is this run's own — that is the author-side carve-out *Merge policy and review feedback* forbids maintaining separately, and it would break on every attended write, which legitimately carries none, and on any comment a person pasted one into. The thread-root test and the no-new-threads rule keep that job. **Both of these hold unchanged under the approval test**, which narrows which writes are marked and changes nothing about what the mark may be used for.
- **The review trigger comment carries no footer and nothing else** — it must read exactly as the repository's convention requires, and the convention fails silently when it does not (`create-pr` owns the trigger; Posting identity's *The review trigger* owns its authorship). **That functional reason is the one to state**: the trigger also happens to be unattended, so the approval test alone would ask for a footer, and the exemption is what overrides it.
