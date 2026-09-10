---
name: resolve-pr-comment
description: Apply an appropriate fix as a new commit on the PR, push it, reply to the original review comment with the commit SHA, and resolve the conversation thread in GitHub.
---

# Resolve PR Comment(s)

You're helping resolve one or more GitHub PR review comments by applying the
appropriate fix, committing and pushing it, replying to each comment with the
commit SHA, and resolving each conversation thread.

Determine `owner/repo` from the current git remote (`git remote get-url
origin`) rather than assuming a fixed repo.

Replies and thread resolutions are authored writes, so they follow the
posting-identity rule stated once in `backlog-orchestrator` (*Posting
identity*): post as the distinct agent identity where the calling workflow
has established one, and as the invoking user where it has not — the common
case, and what the local `gh` path below always does, since it runs on the
user's own credential.

They follow the **authored write form** rule stated once beside it
(`backlog-orchestrator`, *Authored write form*) for the same reason: every
reply is short, and it carries the attribution footer unless this run obtained
the invoking person's approval of that exact reply text before posting it.
Apply both from there rather than restating them; step 5 carries only what they
mean for a reply.

## Task

Resolve PR comment(s): $ARGUMENTS

The argument should be a PR number/URL, one or more review comment URLs, or a
combination. If only a PR number/URL is given with no specific comments
called out, ask which comment(s) to target before proceeding.

## Workflow

### 1. Gather context

In a remote/web session (no `gh` CLI access), use the GitHub MCP tools:

- `mcp__github__pull_request_read` (method `get`) for PR metadata
- `mcp__github__pull_request_read` (method `get_review_comments`) for review
  threads — returns thread IDs (for resolving) and comment bodies/paths/lines

In a local session with `gh` CLI available:

```bash
gh pr view <PR> --repo <owner>/<repo> --json number,title,headRefName,url,comments
gh api repos/<owner>/<repo>/pulls/<PR>/comments

# Review threads are GraphQL-only - `reviewThreads` is not a `gh pr view`
# field, and asking for it fails the whole command. This is also the only
# source of a thread's resolvable id, which step 6 needs.
#
# Paginate it. A fixed `first:` silently truncates, and the failure is the bad
# kind: the reply in step 5 posts, then step 6 cannot find the thread it
# belongs to. `--paginate` needs both an `$endCursor` variable and a
# `pageInfo` selection to walk the connection.
gh api graphql --paginate -f query='
query($endCursor: String) {
  repository(owner: "<owner>", name: "<repo>") {
    pullRequest(number: <PR>) {
      reviewThreads(first: 50, after: $endCursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id isResolved isOutdated path line
          comments(first: 100) { nodes { databaseId author { login } body url } }
        }
      }
    }
  }
}'
```

If specific comment IDs or URLs were provided, fetch those directly. Read the
referenced files at the relevant lines to understand what each comment is
asking for.

### 2. Decide: single commit or separate commits

| Situation                                                     | Strategy                     |
| --------------------------------------------------------------| ----------------------------- |
| All comments are simple/mechanical (rename, typo, formatting) | Roll into one commit         |
| Comments touch unrelated concerns or one is complex           | Separate commits per concern |
| User says "one commit" or "separate commits"                  | Follow their instruction     |

Explain the batching decision before touching any files.

### 3. Apply the fix(es)

**Skipped entirely on a classify-only invocation** (below), along with steps 4-6.

- Make the minimal change needed to address each comment.
- Do not refactor, clean up, or change anything not mentioned in the comment.
- Check this repo's contribution doc (`CLAUDE.md`/`AGENTS.md`) for pre-commit
  checks (typecheck, lint, format, test, or equivalent) and run/fix them
  before committing.

### 4. Commit and push

For a single combined commit:

```bash
git add <files>
git commit -m "<concise description of what was fixed>"
git push -u origin <branch>
```

For separate commits, repeat per concern. Commit messages should describe the
fix, not reference the review comment ("Fix off-by-one in pagination", not
"Address PR comment").

After pushing, capture the SHA(s):

```bash
git rev-parse --short HEAD   # or HEAD~1, HEAD~2 as needed
```

### 5. Reply to each comment

In a remote/web session, use `mcp__github__add_reply_to_pull_request_comment`
with the resolved `owner`/`repo`, `pullNumber`, `commentId`, and a `body`
referencing the commit SHA and what changed, e.g.:

> Fixed in `<sha>` — \<short description of the fix\>.
>
> \<attribution footer\>

In a local session with `gh` CLI:

```bash
gh api repos/<owner>/<repo>/pulls/<PR>/comments/<comment_id>/replies \
  --method POST \
  --field body="Fixed in <sha> — <short description of the fix>.

<attribution footer>"
```

- If multiple comments were fixed in the same commit, each gets the same SHA.
- If each got its own commit, each gets its own SHA.

**That one line is the whole reply.** The reviewer wants to know the comment was
acted on and where to look; the diff is the explanation and the thread already
holds the request. Do not restate the comment back, justify the approach, or
narrate what else was considered.

**The footer goes on unless the person approved this reply text**
(`backlog-orchestrator`, *Authored write form*, the approval test). Unattended
and classify-only that is never true, so those replies carry it. Attended it is
true only where the person was actually shown the reply and confirmed or edited
it — invoking the skill is not that, and neither is being in the session. The
placeholder in the templates above is where it goes when it applies.

**A reply reports work done and never answers a query.** Where the comment asked
for prose, no reply of any kind carries the answer — see *Handling queries*,
which is absolute across modes. Where a comment asked for both, this reply says
what changed and stops there; the question is escalated with its draft
(*A comment can want both*).

### 6. Resolve the conversation thread

In a remote/web session, use `mcp__github__resolve_review_thread` with the
resolved `owner`/`repo` and the `threadId` (node ID) from step 1's
`get_review_comments` output.

In a local session with `gh` CLI:

```bash
gh api graphql -f query='
  mutation {
    resolveReviewThread(input: { threadId: "<THREAD_NODE_ID>" }) {
      thread { isResolved }
    }
  }
'
```

The `threadId` is the thread's `id` from the GraphQL query in step 1 — a node
id like `PRRT_kwDO…`, not a number. **A thread has no `databaseId`**; asking for
one fails the whole query. Match instead on the nested
`comments.nodes[].databaseId`, which is the numeric id of the comment you
replied to.

If a match is not found, **do not resolve anything** — say the thread id could
not be resolved for that comment and stop. A wrong thread resolved is worse than
one left open, and the likeliest cause is a truncated read rather than a missing
thread.

That query's `comments.nodes[].url` is also where a thread's URL comes from,
which *What a question item must contain* requires to be the API's own value
passed through verbatim rather than assembled.

## Unattended callers

`repair-pr` and the orchestrators invoke this skill with nobody watching. A
caller states that by passing an unattended context; treat a caller that
supplies a thread set it selected itself, rather than a human naming comments,
as unattended.

Unattended, the classification in *Handling queries* below runs and reaches the
same verdicts it reaches attended — **the prose branch is `NEEDS_USER` in every
mode, so this section overrides nothing about it.** What is unattended-specific
is only where the result goes: nobody is in the session to hand it to, so every
`NEEDS_USER` item is returned to the caller **carrying exactly what
*What a question item must contain* requires**, and the thread is left open. That
section owns the fields; this one does not restate them, because a second list is
where one of them gets quietly dropped.

**Do not reply substantively on any path, here or elsewhere.** A reply the run
composes on its own authority is an answer nobody authorised: the question was
addressed to a person, and it will be read as that person's position however it
is signed. Unattended there is also nobody to notice — but that is what makes
the failure loud here, not what makes it a failure.

### Classify-only invocations

A caller may invoke this skill to **classify and draft only**. It says so by
passing a classify-only context; `repair-pr` passes it whenever its remaining
repair budget is zero (`repair-pr`, *Review repair (`repair type = review`)*, step 2).

In that mode **steps 3-6 of the workflow do not run**: make no correction, run
no verification, commit nothing, push nothing, reply to nothing and resolve
nothing. Return every supplied thread as its classification and nothing else:

| Classification | Returned as |
| --- | --- |
| Wants a code change | The thread with the change it asks for — **not applied**. It comes back as a deferred-repair item, which is a kind of `NEEDS_USER` item and not an alternative to one (*Output*) |
| Wants an answer | A `NEEDS_USER` item with its draft reply, exactly as unattended |
| Wants nothing | A no-action entry, exactly as unattended |
| Wants both (*A comment can want both*) | Both entries for the one thread — the change unapplied as a deferred repair, and the question as a `NEEDS_USER` item with its draft. The thread is handled only once the caller has recorded both |

**The mode has to be explicit, because this skill's default workflow pushes.**
A caller that wants classification without repair and does not say so gets the
mutation workflow anyway — the first branch above applies, commits and pushes a
fix. That is how a caller's repair cap is exceeded by the callee: `repair-pr`
skipping its own steps 3-5 constrains `repair-pr`, not the skill it invoked
(`repair-pr`, *Review repair (`repair type = review`)*, step 2 states the same
requirement from the caller's side).

### What a question item must contain

**The reason the answer is not posted is so that a person can post it. That makes
the item's job to be actionable without hunting**, and an item they have to
reconstruct from a thread URL defeats the whole rule. Every `NEEDS_USER`
**question item** carries exactly these five things, in this order:

| # | field | rule |
| --- | --- | --- |
| 1 | **the thread's `html_url`** | **as returned by the API, verbatim — never a hand-built anchor.** A review-comment thread and a PR-level comment use different fragment forms, so a URL assembled from a PR number and a comment id silently resolves to the wrong place, or to the top of the PR, and the failure is invisible from here: the link works, it just does not land on the thread. Take the field the API gave you (`html_url` on the comment from `get_review_comments`, or the `gh api` equivalent) and pass it through unchanged. Not sure a URL came from the API → it did not; re-read the thread |
| 2 | **the ask, quoted** | the reviewer's own words, **at most 2 lines**, trimmed with an ellipsis rather than paraphrased. A paraphrase is where the question quietly becomes the one the pass found easier to answer |
| 3 | **the recommended reply — and it is paste-ready only for one of the two draft kinds** | **An answerable-from-work draft** is paste-ready: one line where the answer fits in one, written as the person would post it rather than as a report to them — no "the reviewer asks whether…" preamble, no meta-commentary. **A decision-only draft is not**, and must not be presented as though it were: it lists the options and their costs and deliberately makes no pick (*The draft reply*), so pasting it into the thread posts a non-answer over a question still undecided. Label it **`decision — not for posting`** and say what the person's next step is: decide, then answer in their own words, or route it to `settle-outstanding-decisions`, which asks the underlying options and records the one chosen (*Handling queries*). Neither kind carries an attribution footer — they author whatever they post |
| 4 | **the SHA of any code change made for this thread, or `none`** | explicitly `none` where nothing was pushed. A blank field reads as "not recorded" and sends the person to the diff to check; on a mixed thread (*A comment can want both*) this is where the pushed fix is named, which is the only place the two halves of that thread meet |
| 5 | **why it was not posted** | one clause — *needs your intent*, *product decision*, *only you can confirm the constraint*. Not a restatement of the rule; the person knows the rule, they need to know which of its branches this thread is |

**A thread URL anywhere in this skill's output obeys row 1**, not only in a
question item: a no-action entry and a deferred-repair item name the same thread
and are read by the same person. Row 1 is what "thread URL" means here.

**Where the session has a notification channel, notify as well as record.** The
record is the durable half and the notification is not: **a subscription dies
with the session that armed it**, so a person may never see the notification, and
nothing may depend on their having seen it. The item is complete when it is
recorded; the notification is a courtesy that shortens the wait. Never post the
notification into the thread — that is the reply this whole section exists to
withhold.

### The draft reply

Escalating a question without the work of answering it wastes what this pass
already knows. You read the thread and the code around it; the owner would start
from nothing. So the recommended reply above is a draft the owner can send,
edit, or throw away — **never posted by this skill, on any path.** It is
material for a person, not a pending write.

What the draft contains depends on which kind of question it is, and the two
must not be blurred:

| Question | Draft |
| --- | --- |
| **Answerable from the work** — "why this approach", "does this handle X", "where is this covered" | The actual answer, with the evidence: the file and line, the constraint that forced the choice, the test that covers the case. State it as a claim the owner can check, not as a hedge |
| **A decision only the owner can make** — which behaviour is wanted, whether to accept a tradeoff, product intent | The options and what each costs, and **no pick**. A draft that quietly chooses is the autonomous answer this section exists to prevent, wearing a different hat |

Mark every assumption inline, in the draft itself rather than in a preamble the
owner skips — write `[assumes the retry budget is per-request, not per-batch]`
where the claim sits. The draft will be read quickly and may be pasted; an
assumption noted anywhere else is an assumption nobody read. Where the thread
cannot be answered without information the pass does not have, say what is
missing instead of writing around it — that is a useful draft, and a confident
one built on a gap is not.

Keep it to what the thread asks. A draft that reopens the design is a new
review round, not a reply.

**The draft carries no attribution footer, and this follows from the rule
rather than sitting beside it as a special case.** A draft is not a write at
all — the person who posts it authors it, as themselves, which is the point of
handing it over — so there is no posted text for the approval test to ask about
(`backlog-orchestrator`, *Authored write form*). **That absolute is about the
draft, and it stops there.**

**It does not carry over to the write that later contains the answer.** Where a
workflow posts a drafted answer — `settle-outstanding-decisions`,
*Recording the ruling* — the write is the **ruling comment**, not the draft, and
that comment also carries the question as asked, a dated owner-ruling marker and
what the ruling confirms, none of which the owner has necessarily read. Its
footer is decided there, by the approval test asked of the complete comment, and
**that answer can be yes**: approving the answer inside a record settles nothing
about the record around it. Do not read this section as promising otherwise.

`backlog-orchestrator`, *Per-repository policy configuration*, owns the rule
that separates the two kinds. Apply it from there rather than inventing a
second test. Its short form: a thread asking for a code change this pass can
make and verify is repairable, whoever wrote it; a thread needing intent,
design, rationale, or a decision is `NEEDS_USER`. Author identity decides
nothing — a human's one-line nit is repaired, an automated reviewer's
architecture question is escalated.

Attended — a person invoked this skill and named the comments — **the draft goes
to them, in this session's output, and still not to the thread.** What they can
do with it **depends on which kind it is**, and telling them otherwise is how a
question ends up looking handled while still being open:

- an **answerable-from-work** draft they send, edit first, or throw away —
  posting it as themselves is the point, because then the reviewer is reading an
  answer its author stands behind;
- a **decision-only** draft is not theirs to send at all, because it answers
  nothing: it is the options and their costs with no pick. Their next step is to
  decide. Then they answer in their own words, or hand the thread to
  `settle-outstanding-decisions`, which is built for exactly this — it asks the
  underlying options and records the one chosen, and *"approve the draft" would
  record a ruling that chose nothing* (that skill, *What qualifies as an
  outstanding decision*). Their presence
makes handing it over cheap and does not license posting: what a reviewer reads
is the posted reply, not the correction that followed it, and by the time they
could correct it the answer is already in their voice on a public thread.

## Handling ambiguity

- If a comment is vague or has multiple valid interpretations, ask before
  making any code changes.
- If the fix requires understanding broader context (e.g., a refactor or
  design decision), summarize the options and let the user decide.
- Never resolve a thread without also applying a code fix — a reply alone is
  not enough.

## Handling queries

If a comment's correct response is prose rather than a diff — asking for
clarification, rationale, or intent — **it is `NEEDS_USER` in every mode, and
this skill posts no answer to it.** Classify it, write the draft (*The draft
reply*), leave the thread open and unresolved, and hand the draft to whoever is
waiting on this pass: the person who invoked it attended, the caller as a
`NEEDS_USER` item unattended. **A thread that ends without a code change is never
closed out by prose from this skill** — the only outcomes it has are a pushed fix,
an escalation, or no-action.

The reason is authority, not disclosure. The reviewer asked a **person**, and
nobody authorised this pass to answer for them — so the reply would be read as
that person's position whatever signs it. **A footer would not
license it** (`backlog-orchestrator`, *Authored write form*): saying that nobody
reviewed an answer says nothing about whose position it is, and a reader who
accepts a footered reply as the owner's position has read it correctly, because
it is posted in a thread addressed to them. Disclosure would be the whole story only
if the defect were the reviewer's confusion; the defect is that the position is
not the run's to state. Handing over the draft costs one paste and keeps the
answer attributable to whoever actually stands behind it.

**One path posts an answer this skill drafted, and it is not this skill**:
`settle-outstanding-decisions`, *Recording the ruling*, posts the approved or
edited text after the owner has read it, marked as their ruling. That is the
negation this rule is written on — not that the answer never reaches the thread,
but that it never reaches it on this pass's authority.

**An acknowledgement is not this branch.** "Thanks, this looks good" asks for no
prose either, so it is **no-action** and never `NEEDS_USER` (*A comment that
wants nothing*). Listing it here would make it a `NEEDS_USER` item, since that is
what this branch now returns in every mode — and an acknowledgement escalated
that way cannot be qualified by `settle-outstanding-decisions`, so it would hold
the merge gate with nothing able to clear it.

### A comment can want both

One comment can ask for a diff **and** for prose — *"add the null guard, and say
why the shared helper is unsuitable here."* It is not a third thing to classify;
it is both classifications at once, and it gets both treatments. **This section
adds a case to the classification and no exception to any mode rule** — each half
is handled exactly as that half is handled on its own, which is what keeps this
from contradicting the modes above:

- the **change** is repaired wherever a change request is repaired, and is
  therefore *not* repaired under a classify-only invocation, where it comes back
  as a deferred repair instead (*Classify-only invocations*);
- the **prose** is a query like any other, so **no mode answers it in the
  thread** (*Handling queries*). What the mode decides is only who receives the
  draft, and whether there is a fix to report alongside it:

| Mode | The prose half |
| --- | --- |
| Classify-only | A question item with its draft, returned alongside the deferred repair as the second of two entries for the one thread. Nothing is posted at all |
| Attended | Not answered in the thread. The draft goes to the person who invoked this skill, in this session's output; an answerable-from-work draft they may post as themselves, a decision-only one they decide first (*Handling queries*). The fix is pushed and reported as the fix |
| Unattended (*Unattended callers*) | Not answered in the thread. Return the question as a `NEEDS_USER` item with its draft, and reply only to report what changed — a statement about work done, never written as though it answered the question |

**Attended is not an exception here, and this section does not make one**: a
person being present makes handing the draft over cheap, not posting it safe
(*Handling queries*). The half-fix instinct — the same comment asked for a diff,
so surely the prose can go back with it — is exactly the case the query rule
covers, since what a reviewer reads is one thread with one voice in it.

**No mode resolves the thread.** Attended, resolution of a query thread is the
user's; unattended, the thread is reserved and a reserved thread is never
resolved; classify-only resolves nothing at all. So a mixed comment never closes
on a pushed fix, whichever mode handled it.

Forcing it into one classification fails in a different way each direction, and
the repairable direction fails silently:

| Read as | What happens |
| --- | --- |
| Repairable only | The fix lands and the thread is resolved with the rationale unanswered — and a resolved thread is not a reserved one, so the merge gate reads the review as clean over a question nobody answered. This is the outcome the reserved-thread rule exists to prevent, reached through the fix rather than around it |
| `NEEDS_USER` only | A fix the pass could have made and verified is left undone, waiting on a person who was only ever asked for prose |

The resolution rule is what makes this safe, and it is unchanged: a thread is
never resolved without an applied fix, **and a reserved thread is never resolved
at all.** A mixed thread meets the first and fails the second, so unattended the
fix is pushed and the thread stays open for the owner.

**Judge that by what the comment asks for, not by whether it is phrased as a
question.** "Could you add a null check here?" is a change request wearing a
question mark: it is repairable, and routing it here on its punctuation would
reserve a straightforward fix and hold the merge gate shut over it. Conversely a
comment with no question mark at all ("I don't follow why this needs a second
pass") wants prose. The kind test is the intent (`backlog-orchestrator`,
*Per-repository policy configuration*).

**No mode posts that reply** — the thread comes back as a `NEEDS_USER` item with
its draft, to the caller unattended and to the invoking person attended (see
*Handling queries*). Either way the thread stays open: a question is never
resolved by this skill.

### A comment that wants nothing

Prose is not the same as a request. "Thanks, this looks good", "nice catch",
"agreed" — an acknowledgement asks for neither a diff nor an answer, so it is
**no-action**: not repairable, and **not `NEEDS_USER`**. Return it as no-action,
reply to nothing, resolve nothing, escalate nothing.

Escalating one is a trap rather than a harmless over-report. It is neither an
answerable-from-work question nor a choice only the owner can make, so
`settle-outstanding-decisions` cannot qualify it under its bar — the item is
declined, the thread stays reserved, and it holds the merge gate with nothing
able to clear it. A three-way split is what avoids that: **a diff, an answer, or
nothing at all** — three things a comment can want, not three boxes it must
choose between. One comment can want the first two together (*A comment can want
both*); what none of them can be is silently dropped.

**Return no-action threads to the caller explicitly, one entry each.** Silence
is not the same as no-action: an unattended caller's predicate re-groups any
thread it has not recorded as handled, so a no-action thread the pass simply
omitted comes back on the next supervision cycle, is classified again, and —
because a classify-only pass consumes no cycle — loops without bound. The entry
is what marks it handled. It carries no draft and asks nothing of the owner; it
exists so the caller can record that this thread needs no one.

## Output

After completing all steps, summarize:

- Which comments were resolved
- The commit SHA(s) applied
- Confirmation that replies were posted and threads marked resolved
- **Any thread classified no-action**, one entry each: the thread's API
  `html_url` (*What a question item must contain*, row 1) and why it wants
  nothing. No draft. This is what lets the caller mark it handled so it is not
  re-dispatched forever (see *A comment that wants nothing*)
- **Every `NEEDS_USER` item, one entry each — items, not threads**, and then by
  item kind, because the kinds carry different things and one shape cannot hold
  both:
  - a **question item** carries **all five fields of *What a question item must
    contain***, in that order and none omitted — API `html_url`, the ask quoted
    to at most 2 lines, the recommended reply with no footer — paste-ready, or
    labelled `decision — not for posting` where the draft is decision-only — the
    SHA of any code change for this thread or an explicit `none`, and the
    one-clause reason it was not posted. Report the root author alongside them.
    **A count, a summary, or four of the five is not this entry**: the person
    receiving it posts the reply themselves, and every field they have to go and
    find is a field this pass already had. That holds **in every mode, because
    the prose branch is `NEEDS_USER` in every mode** (*Handling queries*).
    Attended, this output *is* the delivery — the person who invoked the skill is
    the one being handed the item, so an attended run reports it in full exactly
    as an unattended one does rather than treating it as already dealt with;
  - a **deferred-repair item** carries the thread's API `html_url`, the change it
    asks for, and **no draft**
    (see *Classify-only invocations*) — it wants a diff that the budget stopped,
    so there is nothing to answer, and demanding a draft here would leave the
    zero-budget case satisfiable only by fabricating a question-shaped one or
    dropping the item. Dropping it is worse than it looks: the request goes
    unrecorded, the thread is never marked handled, and it is dispatched again on
    every cycle, since a classify-only pass consumes none.

  **Under a classify-only invocation a mixed thread returns two entries** — a
  deferred repair and a question at the one URL (*A comment can want both*) —
  which is why this is keyed by item. With budget remaining the change was
  repaired, so only the question item comes back and the fix is reported as the
  fix.
  None of these were answered or resolved, in any mode, and whoever is waiting on
  the pass needs them individually. Unattended that is the caller: `repair-pr`
  propagates them, the orchestrators hold the merge gate on them, and
  `settle-outstanding-decisions` puts a question to the owner with its draft as
  the context that makes it answerable on the spot — the one path on which a
  drafted answer is ever posted, and only after the owner approves it. Attended
  it is the person reading this output, who posts what they choose to post as
  themselves — subject to the kind split above, since a decision-only draft is
  one they decide rather than one they post. A count supports none of that.

- **Whether a notification was sent for each `NEEDS_USER` item, and on what
  channel** — or that no channel was available. The record above is what the
  caller and the merge gate read; this line only says whether anyone was told
  sooner. Never report a notification as delivery: the subscription may have
  died with the session that armed it (*What a question item must contain*)
