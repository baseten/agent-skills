#!/bin/bash
# Install this repo's skills and permissions into ~/.claude for a Claude Code
# cloud/container session. Run from within a checkout of this repo, e.g.:
#
#   git clone --depth 1 https://github.com/baseten/agent-skills.git /tmp/agent-skills
#   bash /tmp/agent-skills/bootstrap.sh
#   rm -rf /tmp/agent-skills
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"

# --- Skills ---
echo "Installing skills..."
mkdir -p "$CLAUDE_DIR/skills"
SKILLS=(
  create-pr
  resolve-pr-comment
  implement-issue-core
  repair-pr
  implement-issue
  validate-backlog
  normalize-github-dependencies
  backlog-orchestrator
  merge-stack
)
for skill in "${SKILLS[@]}"; do
  cp -r "$SCRIPT_DIR/$skill" "$CLAUDE_DIR/skills/"
done
echo "  Installed: ${SKILLS[*]}"

# --- Permissions ---
PERMISSIONS_FILE="$SCRIPT_DIR/permissions.json"
SETTINGS_FILE="$CLAUDE_DIR/settings.json"

mkdir -p "$CLAUDE_DIR"
chmod 700 "$CLAUDE_DIR"

if [ ! -f "$PERMISSIONS_FILE" ]; then
  echo "No permissions.json found, skipping"
elif [ -f "$SETTINGS_FILE" ] && command -v jq >/dev/null 2>&1; then
  echo "Merging permissions into existing $SETTINGS_FILE..."
  jq --slurpfile perms "$PERMISSIONS_FILE" '
    .permissions //= {} |
    .permissions.allow = ((.permissions.allow // []) + $perms[0].allow | unique) |
    .permissions.deny = ((.permissions.deny // []) + $perms[0].deny | unique)
  ' "$SETTINGS_FILE" > "$SETTINGS_FILE.tmp"
  mv "$SETTINGS_FILE.tmp" "$SETTINGS_FILE"
elif [ -f "$SETTINGS_FILE" ]; then
  echo "WARNING: $SETTINGS_FILE already exists and jq is unavailable to merge." >&2
  echo "Leaving it untouched — install jq or merge permissions.json by hand." >&2
else
  echo "Writing permissions to new $SETTINGS_FILE..."
  if command -v jq >/dev/null 2>&1; then
    jq -n --slurpfile perms "$PERMISSIONS_FILE" '{permissions: $perms[0]}' > "$SETTINGS_FILE"
  else
    printf '{\n  "permissions": %s\n}\n' "$(cat "$PERMISSIONS_FILE")" > "$SETTINGS_FILE"
  fi
fi
[ -f "$SETTINGS_FILE" ] && chmod 600 "$SETTINGS_FILE"

echo "Done!"
