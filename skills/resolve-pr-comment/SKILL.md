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
gh pr view <PR> --repo <owner>/<repo> --json number,title,headRefName,url,comments,reviewThreads
gh api repos/<owner>/<repo>/pulls/<PR>/comments
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

In a local session with `gh` CLI:

```bash
gh api repos/<owner>/<repo>/pulls/<PR>/comments/<comment_id>/replies \
  --method POST \
  --field body="Fixed in <sha> — <short description of the fix>."
```

- If multiple comments were fixed in the same commit, each gets the same SHA.
- If each got its own commit, each gets its own SHA.

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

To find the `threadId`, look in the `reviewThreads` from step 1 or fetch via:

```bash
gh api graphql -f query='{ repository(owner:"<owner>", name:"<repo>") { pullRequest(number:<PR>) { reviewThreads(first:50) { nodes { id databaseId isResolved } } } } }'
```

Match `databaseId` to the comment ID you replied to.

## Unattended callers

`repair-pr` and the orchestrators invoke this skill with nobody watching. A
caller states that by passing an unattended context; treat a caller that
supplies a thread set it selected itself, rather than a human naming comments,
as unattended.

Unattended, the classification in *Handling queries* below still runs, but its
second branch changes: **do not answer the question and do not reply
substantively.** Return the thread to the caller as a `NEEDS_USER` item — thread
URL, root author, what it asks, and a **draft reply** (below) — and leave it
open. A reply the run composes on its own authority is an answer nobody
authorised: the question was addressed to a person, and a plausible-sounding
guess in their voice is worse than silence, because the reviewer reads it as the
owner's answer and stops asking.

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

### The draft reply

Escalating a question without the work of answering it wastes what this pass
already knows. You read the thread and the code around it; the owner would start
from nothing. So every `NEEDS_USER` item carries a draft the owner can send,
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

`backlog-orchestrator`, *Per-repository policy configuration*, owns the rule
that separates the two kinds. Apply it from there rather than inventing a
second test. Its short form: a thread asking for a code change this pass can
make and verify is repairable, whoever wrote it; a thread needing intent,
design, rationale, or a decision is `NEEDS_USER`. Author identity decides
nothing — a human's one-line nit is repaired, an automated reviewer's
architecture question is escalated.

Attended — a person invoked this skill and named the comments — the original
behaviour stands: answer the query in a reply and leave the thread open for
them. They are present to correct you, which is exactly the condition the
unattended path lacks.

## Handling ambiguity

- If a comment is vague or has multiple valid interpretations, ask before
  making any code changes.
- If the fix requires understanding broader context (e.g., a refactor or
  design decision), summarize the options and let the user decide.
- Never resolve a thread without also applying a code fix — a reply alone is
  not enough.

## Handling queries

If a comment's correct response is prose rather than a diff — asking for
clarification, rationale, or intent — post a reply with an appropriate response
but do **not** resolve the thread. Leave resolution to the user.

**An acknowledgement is not this branch.** "Thanks, this looks good" asks for no
prose either, so it is **no-action** and never `NEEDS_USER` (*A comment that
wants nothing*). Listing it here would route it through the unattended override
below, which returns this branch as a `NEEDS_USER` item — and an acknowledgement
escalated that way cannot be qualified by `settle-outstanding-decisions`, so it
would hold the merge gate with nothing able to clear it.

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
- the **prose** follows the attended/unattended split:

| Mode | The prose half |
| --- | --- |
| Classify-only | Not answered and not drafted-and-posted: a question item with its draft, returned alongside the deferred repair as the second of two entries for the one thread |
| Attended | Post the substantive answer in the thread, as the rule above gives for any query. The person is present and asked for it; withholding it here because the same comment also asked for a diff answers nobody |
| Unattended (*Unattended callers*) | Do not answer it. Return the question as a `NEEDS_USER` item with its draft, and reply only to report what changed if the mode permits a reply at all — a statement about work done, never written as though it answered the question |

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

**Unattended, do not post that reply** — return the thread as a `NEEDS_USER`
item instead (see *Unattended callers*). Either way the thread stays open: a
question is never resolved by this skill.

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
- **Any thread classified no-action**, one entry each: thread URL and why it
  wants nothing. No draft. This is what lets the caller mark it handled so it is
  not re-dispatched forever (see *A comment that wants nothing*)
- **Every `NEEDS_USER` item, one entry each — items, not threads**: thread URL,
  root author, what it asks, and then by item kind, because the kinds carry
  different things and one shape cannot hold both:
  - a **question item** carries its draft reply (see *Unattended callers*);
  - a **deferred-repair item** carries the change it asks for and **no draft**
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
  Unattended, none of these were answered or resolved, and the caller needs them
  individually: `repair-pr` propagates them, the orchestrators hold the merge
  gate on them, and `settle-outstanding-decisions` puts a question to the owner
  with its draft as the context that makes it answerable on the spot. A count
  supports none of that
