# Authored write form

This is the rule other skills mean when they cite *authored write form*. It is a shared rule, not a skill: held once at `rules/authored-write-form.md` and copied into each applying skill's `references/authored-write-form.md` by `scripts/refresh_shared_rules.sh`. Edit the source, never a copy; check_shared_rules.py fails if a generated copy diverges.

The *posting identity* shared rule decides which **author** a write carries; this decides **what the write looks like** once it is authored — identity is a fact about the credential, form a fact about the text. It covers every authored forge/tracker write made on the run's behalf — PR bodies, timeline comments, review replies, worker reports, recorded rulings — whichever skill or worker performs it. **This file is the rule's only statement; the skills that write defer here rather than restating it.** Two rules: keep it short, and mark the writes nobody read.

## Keep it short

**Say why rather than what.** The reader pays for every word; the run pays nothing.

- **A review reply is one line**: `Fixed in <sha> — <what changed>.` and nothing else above the footer.
- **A push is never announced.** A pushed repair is answered by that reply in the thread it fixes, or not at all — never by a timeline comment, a new thread or any other write saying what was pushed or that CI now passes. The worker report a dispatch requires (`swarm`, *How a worker's report actually reaches you*) is not an announcement: it names the head, and nothing else this file forbids.
- **A commit SHA in any forge write is bare** — never inside a code span or code block, where the forge does not link it. The 7-character short form or longer, or the full SHA; another repository's commit is *owner/repo@sha*, also bare.
- **Never hard-wrap a write that lands in a forge field** — a PR body, an issue body, a review comment. A browser renders a newline inside a paragraph as a line break, so write each paragraph as one long line; code blocks, tables and lists are unaffected. **Expect to get this wrong, and expect nothing to catch it**: the write never reaches the repository's formatter, which trains the opposite habit.

**No write reports verification** — no list, table or sentence saying which checks ran or how they came out (lint, formatting, type checking, test suites, CI) — in a PR body, a comment, a review body or a commit message, **a collapsed `<details>` block included**: run locally or not, passed, failed or `not locally runnable`, whatever the gate's provenance, and whatever a style guide or template asks. The forge's own checks report them; a gate report goes in the structured result returned to the caller. What a template's checks section gets instead is the **testing summary**: only the manual steps a reader has to run, grouped rather than one per assertion, and a line naming which behaviour a new or existing test now pins — never that a suite passes, never a list of test files. A repair's diagnosis of the failure it fixed or declined, and a reply answering a reviewer's question about a test or check, are not verification; they go where their contract puts them.

## A PR body

The one write with a budget, since a reviewer reads it before starting:

| part | limit |
|---|---|
| prose above the fold — linkage, background, description and testing summary together | **300 words maximum**: a ceiling for a genuinely large change, not a target |
| background | 2-4 sentences: the problem, not its history |
| description | one paragraph, or at most 5 bullets: the solution and why this one |
| manual test checklist | not counted in the 300; **at most 8 grouped items** |
| depth | a collapsed `<details>` block or a commit message, never above the fold |

**The body states intent, not content**: background, why this solution where a reviewer might expect another, what is deliberately in and out of scope, and what could break. So no file-by-file inventory or "surface area changed" list, no restating what a function now does, no investigation log ("grepped for", "reproduced with", "verdict:"), and no account of the order things went wrong in. The diff is the content. **Over budget means cut**, never compress by deleting whitespace while keeping every fact.

**A genuinely trivial PR gets a near-empty body.** Do not manufacture prose to fill a template: delete a template heading with nothing real under it. **But where the gap is something the author can supply and this run cannot** — a capture of a visual change, a note only they hold — **keep the heading with one line naming what is needed**: deleting is right where the section will never apply to this change, and wrong where it hides a gap.

**Where a change is user-visible and the repository provides a way to capture it** — a screenshot skill, a Storybook or VRT harness, a browser-driving test — **capture one**. Where it does not, describe what changed visually and say that no capture was available; never describe the capture itself. **Never imply a visual check that was not performed** (notes: why this is conditional).

## What overrides brevity

**A documented PR-description style guide — the repository's, or the user's own configuration — governs, and its budget wins.** `create-pr` reads `CLAUDE.md`/`AGENTS.md` before writing a body, and voice rules live in a personal guide, not here. Everything above except the verification ban and the no-wrap rule is the floor for a repository with no guide; those two hold under any guide.

**Contents the write's own site mandates win over brevity**: `create-pr`'s linkage and `Depends on:` lines, `settle-outstanding-decisions`'s ruling record, the worker report's **judgment its subtraction requires** (`backlog-orchestrator`, *Before dispatch*, step 11). Brevity governs how each required element is written, never whether: one dropped to shorten a write is a defect. **Where a site defines its contents as a subtraction, brevity may not turn it into a list** — everything the subtraction leaves in is required, including what nobody thought to enumerate.

## Editing a PR body after it is created

Creating a PR is not an edit. After creation:

| case | may the run edit the body? |
|---|---|
| the PR is a draft | yes |
| the body still carries the attribution footer — the run's own text, which nobody has read | yes |
| the merge opt-in governing the PR — `auto-merge`, or `auto-merge-dependencies` for a dependency PR merged under that gate — is resolved on for it (the *agent policy* shared rule, *Precedence*) | yes |
| the `Depends on:` line, in any case | **always — that line and only that line**: it is stack metadata |
| **anything else** — a published PR whose body a person has read, that opt-in off | **never**: report the drift as an action point with a suggested replacement |

An allowed edit to a published PR is reported: which PR, what changed, and why. Both reports are made at settle (`settle-and-merge`, *Merge behavior*), or in the skill's own output where no settle follows. **An allowed edit to a body a person wrote — their draft, say — adds no footer**: the text is still theirs.

## The attribution footer marks the writes nobody read

**The footer is not a stamp on everything the run types.** At every write site the test is one question, asked of the write in front of you:

> Did this run obtain the invoking person's approval of **this exact text** before posting it?

**No → the write carries the footer. Yes → it does not.** Nothing else decides it: not which skill performs the write, not what typed the words, not how confident the run is.

```text

---
_Generated by [Claude Code](https://claude.ai/code)_
```

**Approval means this exact text.** A person who authorised the run, approved the plan, asked for the PR, or sat in the session has not approved a body they have not read. Where the run cannot say the person read the text, the answer is No and the footer goes on — the safe direction, and the common one.

| write | approval | footer |
|---|---|---|
| Worker report, automated review reply, mechanical supervision comment, a PR body opened by a dispatched worker | nobody read it | **yes** |
| A `create-pr` body drafted interactively, shown to the user, and confirmed or edited by them | this exact text | **no** |
| A `settle-outstanding-decisions` recorded ruling | **the complete comment**, shown to the owner and approved or edited — approving the answer inside it is not approving the record built around it | **no** where that happened, **yes** where it did not |
| A `NEEDS_USER` draft reply | not a write at all — material for a person, who authors it when they post it | **no** |
| A write with no body — a merge, a base retarget, a native dependency edge | nothing to govern: brevity and the footer reach only writes with text (`merge-stack` applies this to its three write kinds) | **no** |
| The review-trigger comment | — | **no**, below |

- **The footer says the posted text went unread, not who wrote the content**, so **an attribution already present is never itself a reason to omit it** — only the approval test is. A `settle-outstanding-decisions` ruling carries an owner-ruling marker and still carries the footer unless the owner was shown and approved the complete comment (that skill, *Recording the ruling*).
- **The forge's avatar is no substitute**: it varies with the transport that authored the write, and on the posting-identity rule's degraded path, the common one, shows the invoking user's login with nothing marking the write as agent-written (notes).
- **The footer is not identity evidence and not a discriminator.** It is text this run wrote: the posting-identity map is built only from observed write authorship, and a footer is never read back as an observation. Nothing may test for it to decide whether a comment is this run's own — that is the author-side carve-out the *review feedback* shared rule, *The thread-root test*, forbids maintaining separately, and it would misread every attended write, which carries none, and any comment a person pasted one into. The thread-root test and the no-new-threads rule keep that job. **Both hold unchanged under the approval test.**
- **The review-trigger comment carries no footer and nothing else**: it must read exactly as the repository's convention requires, and the convention fails silently when it does not (the *review trigger* shared rule owns the convention; the *posting identity* shared rule, *The review trigger*, owns its authorship). **That functional reason is the one to state**: the trigger is also unattended, so the approval test alone would ask for a footer, and the exemption overrides it.
