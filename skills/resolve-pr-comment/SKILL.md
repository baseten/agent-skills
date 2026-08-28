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

## Handling ambiguity

- If a comment is vague or has multiple valid interpretations, ask before
  making any code changes.
- If the fix requires understanding broader context (e.g., a refactor or
  design decision), summarize the options and let the user decide.
- Never resolve a thread without also applying a code fix — a reply alone is
  not enough.

## Handling queries

If a comment is a question or doesn't require a code change (e.g., asking for
clarification, explaining intent, or acknowledging something), post a reply
with an appropriate response but do **not** resolve the thread. Leave
resolution to the user.

## Output

After completing all steps, summarize:

- Which comments were resolved
- The commit SHA(s) applied
- Confirmation that replies were posted and threads marked resolved
