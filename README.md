# agent-skills

Personal Claude Code / Codex skills, shared across all of Alex's projects.

## Local usage

This directory *is* `~/.claude-personal/skills` — the `claude-personal` shell
alias sets `CLAUDE_CONFIG_DIR=~/.claude-personal`, so Claude Code picks these
up automatically for any repo run under that alias.

Codex can read the same files via symlinks in `~/.codex/skills/`:

```bash
for s in create-pr resolve-pr-comment implement-issue backlog-orchestrator merge-stack; do
  ln -sfn "$HOME/.claude-personal/skills/$s" "$HOME/.codex/skills/$s"
done
```

## Cloud/container sessions

Cloud sandboxes don't have access to `~/.claude-personal/`. Each cloud
environment's setup script clones this repo and runs `bootstrap.sh` to install
the skills and permissions into `~/.claude/` before the session starts:

```bash
#!/bin/bash
set -euo pipefail

git clone --depth 1 https://github.com/baseten/agent-skills.git /tmp/agent-skills
bash /tmp/agent-skills/bootstrap.sh
rm -rf /tmp/agent-skills
```

`bootstrap.sh` installs all five skills listed below into `~/.claude/skills/`,
then merges `permissions.json` into `~/.claude/settings.json`.

## Permissions

`permissions.json` pre-approves MCP tools routinely used by issue/PR monitoring
and linked tracker workflows. This list only covers tools observed so far; if a
cloud session prompts for a new recurring GitHub/Linear/Claude Code Remote tool,
add it here rather than relying on a one-session approval.

## Skills

- `create-pr` — PR creation with GitHub/Linear issue linking, explicit-base
  support for stacks, automatic `Depends on: <parent PR>` metadata for stacked
  PRs, and the repository's review trigger.
- `resolve-pr-comment` — apply a fix, push, reply, and resolve the thread.
- `implement-issue` — end-to-end GitHub or Linear issue implementation; chains
  into `create-pr` and monitors CI/review where the environment supports it.
- `backlog-orchestrator` — execute a bounded dependency DAG across one or more
  repositories/projects with parallel implementation workers and durable GitHub
  state/recovery.
- `merge-stack` — merge one PR, a prefix, or an explicitly requested entire
  same-repository stack, rebasing and retargeting descendants after each merge
  so parent commits do not leak into child PR diffs (including squash merges).
