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
#
# permissions.json is a MANAGED SET, not an additive one. Bootstrap records
# what it installed in a sidecar and, on the next run, subtracts that record
# before adding the current file. Entries this repo has retired therefore
# disappear; anything you added to settings.json by hand survives untouched.
#
# The sidecar is what makes retirement possible at all. A plain
# `(existing + new | unique)` union can only ever grow, so a container that
# once installed a wrong entry kept it forever - and a wrong entry is
# invisible, because a rule that matches nothing looks exactly like one that
# works until an agent stops on it.
PERMISSIONS_FILE="$SCRIPT_DIR/permissions.json"
SETTINGS_FILE="$CLAUDE_DIR/settings.json"
MANAGED_FILE="$CLAUDE_DIR/.agent-skills-permissions.json"

mkdir -p "$CLAUDE_DIR"
chmod 700 "$CLAUDE_DIR"

# Record what we just installed, so the next run knows what it owns.
record_managed() {
  cp "$PERMISSIONS_FILE" "$MANAGED_FILE"
  chmod 600 "$MANAGED_FILE"
}

if [ ! -f "$PERMISSIONS_FILE" ]; then
  echo "No permissions.json found, skipping"
elif [ -f "$SETTINGS_FILE" ] && command -v jq >/dev/null 2>&1; then
  echo "Merging permissions into existing $SETTINGS_FILE..."

  PREV_FILE="$MANAGED_FILE"
  CLEANUP_PREV=""
  if [ ! -f "$PREV_FILE" ]; then
    # No record of a previous install, so nothing can be attributed to us and
    # nothing can be retired this run. Everything already in settings.json is
    # indistinguishable from a deliberate hand edit, so it is kept.
    PREV_FILE="$(mktemp)"
    CLEANUP_PREV="$PREV_FILE"
    printf '{"allow":[],"deny":[]}\n' > "$PREV_FILE"
    echo "  No prior install record. Existing entries are all preserved, so"
    echo "  any this repo has since retired will still be present. To install"
    echo "  a clean copy instead:"
    echo "    rm $SETTINGS_FILE && bash $0"
  fi

  jq --slurpfile perms "$PERMISSIONS_FILE" --slurpfile prev "$PREV_FILE" '
    .permissions //= {} |
    .permissions.allow =
      ((((.permissions.allow // []) - $prev[0].allow) + $perms[0].allow) | unique) |
    .permissions.deny =
      ((((.permissions.deny  // []) - $prev[0].deny ) + $perms[0].deny ) | unique)
  ' "$SETTINGS_FILE" > "$SETTINGS_FILE.tmp"
  mv "$SETTINGS_FILE.tmp" "$SETTINGS_FILE"
  [ -n "$CLEANUP_PREV" ] && rm -f "$CLEANUP_PREV"
  record_managed
elif [ -f "$SETTINGS_FILE" ]; then
  echo "WARNING: $SETTINGS_FILE already exists and jq is unavailable to merge." >&2
  echo "Leaving it untouched - install jq or merge permissions.json by hand." >&2
else
  echo "Writing permissions to new $SETTINGS_FILE..."
  if command -v jq >/dev/null 2>&1; then
    jq -n --slurpfile perms "$PERMISSIONS_FILE" '{permissions: $perms[0]}' > "$SETTINGS_FILE"
  else
    printf '{\n  "permissions": %s\n}\n' "$(cat "$PERMISSIONS_FILE")" > "$SETTINGS_FILE"
  fi
  record_managed
fi
if [ -f "$SETTINGS_FILE" ]; then
  chmod 600 "$SETTINGS_FILE"
fi

echo "Done!"
