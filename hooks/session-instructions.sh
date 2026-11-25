#!/usr/bin/env bash
# SessionStart hook of the agent-skills plugin: prints global-instructions.md,
# which Claude Code adds to the session's context. It is how the rules reach a
# session that has the plugin and no setup script, such as one where the
# plugin is enabled on a claude.ai account.
#
# It prints nothing when the user's CLAUDE.md already carries the rules in a
# block opening `<!-- agent-skills:begin` (bootstrap.sh writes one; so does any
# installer that generates the file with the rules in it), so a session never
# reads them twice. It always exits 0: a missing file must not disturb a session.
set -u
root="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
rules="$root/global-instructions.md"
user_md="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/CLAUDE.md"

if [ -f "$user_md" ] && grep -q '^<!-- agent-skills:begin' "$user_md" 2>/dev/null; then
  exit 0
fi
[ -f "$rules" ] || exit 0

printf '# General rules (agent-skills plugin)\n\nThese apply in every session, as instructions in CLAUDE.md do.\n\n'
cat "$rules"
exit 0
