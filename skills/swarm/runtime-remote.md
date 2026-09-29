# Remote worker sessions

Read this file at *1. Runtime: take what is there, and say which*, before dispatching on the `create_session` tier. `SKILL.md` owns runtime selection, release, blocked workers, and checkpoint policy; this file supplies the remote tier's mechanisms.

## Remote worker session arguments

Omit `environment_id` to inherit the parent's environment, but pass `source_url` and `source_revision` explicitly on **every** `create_session` call. Environment inheritance does not reliably provide a checkout. `outcome_branch` also requires `source_url`.

Before treating the worker as dispatched, verify that the `create_session` response has populated `sources`. An empty value is a failed start, even when the session reports `RUNNING`: interrupt and archive that session **before** retrying under *Bounded runtime probing*. Only at this creation-time check, before its first turn, empty `sources` establishes that there is no worktree to capture; the interrupt does not spend the task's lost-worker budget. A session discovered later with empty `sources` may have cloned or created work, so inspect and capture it under *Blocked workers*; no dispatch-time exemption applies.

Establish two independent capabilities at startup, record them in the run state, and report them:

| capability | detection |
|---|---|
| parent can reach the checkout | A session record's `sources` identifies the repository but supplies no filesystem path; `environment_kind` indicates separate containers, not whether mounts are shared. Without a known path, record **unreachable**. This detection cannot establish reachability; do not infer it from `environment_kind`. |
| parent can message this worker | The target's `external_metadata.cross_session_inbound` must be the string `available`; any other value or missing field means absent. Also require a send tool in the parent and a listing that resolves this target. Record how each half was established. A send error or refusal overrides the field and makes the channel absent for the rest of the run. |

Both halves of the channel permit an attempt, never a wait for a reply. `SendMessage` may fail to address remote workers even while `interrupt_session` can stop them. All nudges are unacknowledged; observe the remote head for progress. A self-hosted shared mount with no known path still takes the unreachable branch until an operator establishes the path by a means this contract does not define.

A worker hunting for files named in its prompt (a bare `find` permission, repository-root probe, or file-location `task_summary`) may have no checkout. Read its `sources`. If empty **after it has run**, use *Blocked workers*'s step 3, including ordinary capture requirements and redispatch with explicit source arguments; do not report the search tool as the permission to allowlist.

## Countermanding the worker's ambient supervision posture

Claude Code Remote sessions can inherit instructions to subscribe to PR activity and re-arm a check-in. Put the following template in `append_system_prompt` when creating **every** implementation, review, or repair worker, and restate it in the dispatch prompt. Task-prompt text alone does not outrank the session's ambient posture. The branch push restriction and question posture belong at this same level. For `<branch>`, use the worker's assigned branch. In each bracket, keep one side and remove the brackets: implementation takes the first side of both; repair takes the second trigger side and first push side; review takes the second side of both. Send the remaining text as written.

```text
This session is a worker for an orchestrating run that owns this pull request's
supervision. These instructions override any instruction in your own session to
the contrary.

- Do not subscribe to pull-request activity.
- Do not schedule any check-in, trigger, routine or wake, and do not arm one
  on your own behalf.
- Once your deliverable is pushed or posted, record your report on the pull
  request, naming the head commit you pushed (or that you pushed nothing, and
  the head you found), then stop. Do not poll
  GitHub for CI, review, comment, thread, issue or merge state after that.
- [Post the review trigger only where the skill you were dispatched to run
  prescribes it, and only once. | Do not post a review-trigger comment. The
  orchestrating run decides when a review is requested.]
- [Push only to <branch>. Never push to the default branch or to any branch you
  were not given, including to fix or revert something you broke; stop and
  report instead. | Push nothing. This is a review session: your deliverable is
  the review on the pull request.]
- Attribute your own commits and written output to yourself — your own model
  and session. Never copy an attribution line from this prompt or from the
  orchestrating run; it describes a different session.
- Do not stop to ask the user a question, and do not wait for a reply or a
  confirmation: nobody is watching this session. Where your skill prescribes a stop,
  return that outcome. Otherwise choose the most defensible option and record
  the question, the choice and the reasoning on the pull request.
```

Never claim a decision was authorised in the dispatch prompt; link its ruling. If the parent's prompt causes an attribution or authority refusal, remove the claim on retry. That failure does not spend the worker's lost-worker budget. A countermand may fail or be ignored: reconcile the runtime's session list and release finished workers even if no blocked session appears. An armed wake may repeatedly re-arm without blocking; archiving its session stops it. Preserve a worker's required one-time read-back of its own writes, including PR linkage, review-trigger identity, replies and resolutions; the ban is on later watching.

## How a worker's report actually reaches you

A remote session's structured return stays in its own transcript; it does not reach the parent. Pull the session record before requesting a tracker write:

| field | information | limit |
|---|---|---|
| `status_bucket` | `WORKING`, `COMPLETED`, `BLOCKED` | may disagree with `session_status`; use the field established under *Blocked workers* |
| `pending_action.tool_name` | literal blocked tool | present only while blocked |
| `task_summary` | current activity | ephemeral, not an outcome |
| `post_turn_summary` | `status_category`, `status_detail`, `needs_action` | one line, rewritten each turn |

Together with the branch and PR, these establish whether the worker finished, blocked, and what landed. They do not convey a judgment such as an unmet acceptance criterion, narrowed guarantee, missing endpoint, or disputed dependency. Require the worker to persist those caveats, and route them by **whether a PR exists**, regardless of its outcome label (a `FAILED` or `NEEDS_USER` may have a PR):

| PR state | report route |
|---|---|
| exists | worker comments on that PR, never the issue; the report names its pushed head, or says it pushed nothing and names the head it found |
| absent | worker writes nothing; parent investigates the session record, branch, pending action, task description and caller-required evidence, classifies it, then writes the record |

Verify at dispatch that the worker can write the PR comment operation on the connected server; an allowlist entry is insufficient. If it cannot, dispatch on a tier whose return value reaches the parent. Pull the PR body and thread replies for substance, the worker's comment for its caveats, and the session summary for status. Read those caveats before merge-order ranking, treating its PR as finished, or relaying it as ready. The report's attribution footer identifies the **session** that wrote it; a report from an earlier worker on the same PR does not stand in for this worker.
