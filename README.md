# agent-skills

Personal Claude Code / Codex skills, shared across all of Alex's projects.

## Local usage

This directory *is* `~/.claude-personal/skills` — the `claude-personal` shell
alias sets `CLAUDE_CONFIG_DIR=~/.claude-personal`, so Claude Code picks these
up automatically for any repo run under that alias.

Codex reads the same files via symlinks in `~/.codex/skills/`:

```bash
for s in create-pr resolve-pr-comment implement-issue; do
  ln -sfn "$HOME/.claude-personal/skills/$s" "$HOME/.codex/skills/$s"
done
```

## Cloud/container sessions

Cloud sandboxes (Claude Code on the web, cloud environments) don't have
access to `~/.claude-personal/`. Each cloud environment's setup script clones
this repo and runs `bootstrap.sh` to install the skills and permissions into
`~/.claude/` before the session starts — see the environment's setup script
config for the exact invocation, but it looks like:

```bash
#!/bin/bash
set -euo pipefail

git clone --depth 1 https://github.com/baseten/agent-skills.git /tmp/agent-skills
bash /tmp/agent-skills/bootstrap.sh
rm -rf /tmp/agent-skills
```

`bootstrap.sh` copies `create-pr`, `resolve-pr-comment`, and
`implement-issue` into `~/.claude/skills/`, then merges `permissions.json`
into `~/.claude/settings.json` (creating the file if it doesn't exist yet,
merging with `jq` on top of anything already there otherwise) so the
container doesn't have to prompt mid-session for tool calls these skills
routinely make.

## Permissions

`permissions.json` pre-approves the MCP tools `implement-issue`'s PR
monitoring step (and `create-pr`'s issue linking) rely on:

- `mcp__github__list_issues`
- `mcp__linear__get_issue`, `mcp__linear__get_project`, `mcp__linear__update_issue`
- `mcp__claude-code-remote__update_trigger`, `mcp__claude-code-remote__send_later`,
  `mcp__claude-code-remote__subscribe_pr_activity` — rescheduling the next PR
  check-in, messaging the user, and subscribing to webhook-driven PR activity
  (comments, CI status, reviews) without blocking on approval each time.

This list only covers tools observed so far. If a skill starts needing a new
one — or a container prompts for a new `(Claude Code Remote)`/`(Linear)`/
`(GitHub)` tool call — add it here rather than approving it ad hoc in a
running container; that approval doesn't persist to the next session.

## Skills

- `create-pr` — PR creation (draft for work repos, full for personal ones)
  with GitHub/Linear issue linking and an automatic `@codex review` trigger.
- `resolve-pr-comment` — apply a fix, push, reply, resolve the thread.
- `implement-issue` — end-to-end GitHub or Linear issue implementation,
  chains into `create-pr`, and (where scheduled wakeups are supported)
  monitors the PR for CI failures and review comments.
