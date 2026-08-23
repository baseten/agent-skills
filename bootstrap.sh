#!/bin/bash
# Install this repo's skills and permissions into ~/.claude for a Claude Code
# cloud/container session. Run from within a checkout of this repo, e.g.:
#
#   git clone --depth 1 https://github.com/baseten/agent-skills.git /tmp/agent-skills
#   bash /tmp/agent-skills/bootstrap.sh
#   rm -rf /tmp/agent-skills
#
# Every directory under skills/ containing a SKILL.md is installed. Adding a
# skill needs no edit here — create the directory and it ships.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"

# --- Skills ---
mkdir -p "$CLAUDE_DIR/skills"

echo "Installing skills..."
for skill_path in "$SCRIPT_DIR"/skills/*/; do
  skill_path="${skill_path%/}"
  # A directory without a SKILL.md is not a skill. This also absorbs the
  # unmatched glob if skills/ ever holds no directories.
  if [ ! -f "$skill_path/SKILL.md" ]; then
    continue
  fi
  # The trailing slash is stripped above because BSD cp reads
  # `cp -r src/ dest/` as "copy the contents of src", unlike GNU cp.
  cp -r "$skill_path" "$CLAUDE_DIR/skills/"
  echo "  + $(basename "$skill_path")"
done

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
