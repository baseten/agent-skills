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
this repo and copies the skills into `~/.claude/skills/` inside the sandbox
before the session starts — see the environment's setup script config for the 
exact clone command. But it may look something like:

```
#!/bin/bash                                                                                                                                                                                                                  

mkdir -p ~/.claude/skills
git clone --depth 1 https://github.com/baseten/agent-skills.git /tmp/agent-skills
cp -r /tmp/agent-skills/* ~/.claude/skills/
rm -rf /tmp/agent-skills
```  

## Skills

- `create-pr` — PR creation (draft for work repos, full for personal ones)
  with GitHub/Linear issue linking and an automatic `@codex review` trigger.
- `resolve-pr-comment` — apply a fix, push, reply, resolve the thread.
- `implement-issue` — end-to-end GitHub or Linear issue implementation,
  chains into `create-pr`, and (where scheduled wakeups are supported)
  monitors the PR for CI failures and review comments.
