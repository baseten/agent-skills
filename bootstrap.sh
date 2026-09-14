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
#
# Installing merges: `cp -r` over an existing directory leaves any file this
# repo has since deleted from that skill in place. Replacing instead would mean
# deleting a directory first, and nothing here can establish that the directory
# is ours — a name collision with something you installed yourself looks
# identical. Two review rounds went into trying to infer that ownership and each
# attempt was a way to destroy somebody's work: refusing collisions froze every
# pre-sidecar install, and adopting them took over skills that were never ours.
# So this deletes nothing, and a retired skill is reported for you to remove.
mkdir -p "$CLAUDE_DIR/skills"

echo "Installing skills..."
installed=""
for skill_path in "$SCRIPT_DIR"/skills/*/; do
  skill_path="${skill_path%/}"
  # A directory without a SKILL.md is not a skill. This also absorbs the
  # unmatched glob if skills/ ever holds no directories.
  if [ ! -f "$skill_path/SKILL.md" ]; then
    continue
  fi
  skill="$(basename "$skill_path")"
  # The trailing slash is stripped above because BSD cp reads
  # `cp -r src/ dest/` as "copy the contents of src", unlike GNU cp.
  cp -r "$skill_path" "$CLAUDE_DIR/skills/"
  echo "  + $skill"
  installed="$installed$skill
"
done

# Skills this repository has removed. Reported, never deleted: an install that
# has one may have got it from here or may have its own, and this script cannot
# tell. Naming it is enough — the reader can.
RETIRED="draft-blog-post draft-slack-message upgrade-major-dependency dependency-upgrade-orchestrator"
for prev in $RETIRED; do
  # Match a whole entry, not a substring. `installed` holds one name per line,
  # so prefixing a newline delimits every entry on both sides; without it a
  # retired name that is a SUFFIX of a current one matches the current one and
  # the warning is skipped. `dependency-upgrade-orchestrator` inside
  # `npm-dependency-upgrade-orchestrator` is exactly that case.
  case $'\n'"$installed" in
    *$'\n'"$prev"$'\n'*) continue ;;
  esac
  if [ -d "$CLAUDE_DIR/skills/$prev" ]; then
    echo "  ! $prev is installed and this repository no longer ships it." >&2
    echo "    If it came from here it is stale: delete" >&2
    echo "    $CLAUDE_DIR/skills/$prev yourself." >&2
  fi
done

echo "  Installed: $(ls "$CLAUDE_DIR/skills" | tr '\n' ' ')"

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

# --- Extra GitHub MCP server ---
#
# Deliberately not called a sidecar: that word already means
# ~/.claude/.agent-skills-permissions.json everywhere else in this repository.
#
# A cloud session's built-in GitHub MCP server is provisioned with no feature
# flags and a restricted toolset list, so two things are missing from it, for
# unrelated reasons:
#
#   issue_dependency_read/_write  - behind the `issue_dependencies` FEATURE
#                                   FLAG, which travels on the connection as
#                                   ?features= or X-MCP-Features
#   Projects v2                   - `projects` is simply not one of the default
#                                   TOOLSETS (context, issues, pull_requests,
#                                   repos, users)
#
# Neither that server's URL nor its headers can be changed from inside a
# session, and a project-scoped .mcp.json cannot help: a cloned repository is an
# untrusted folder, so a committed enableAllProjectMcpServers is ignored and the
# server sits at "Pending approval" with nobody able to approve it. A second
# server in USER scope is the only route, which is why this lives here and has
# to run from the setup script - see README, "Install from a setup script".
#
# The REST fallback cannot substitute. Requests to api.github.com exit through
# the cloud GitHub proxy already described under "Why this repository is
# public": it scopes access to the repositories attached to the session. A
# dependency edge pointing into an unattached repository therefore comes back as
# HTTP 200 and an empty array - the same 403 that stops a clone, but silent and
# inside a response body, so a truncated graph is indistinguishable from an
# empty one. Projects v2 is GraphQL-only and unreachable that way at all.
# api.githubcopilot.com escapes both by making its GitHub calls server-side,
# resolving visibility from its own token rather than the session's repo set.
#
# OFF unless AGENT_SKILLS_GH_MCP=1. A server configured without a working
# credential fails to connect on every session start, and it is unnecessary
# locally, where an authenticated `gh` already reads cross-repo edges.
MCP_CONFIG_FILE="$HOME/.claude.json"
# Deliberately NOT configurable, and load-bearing for the allowlist.
# permissions.json allows mcp__github-deps__* - a glob is permitted in the tool
# position but only after a literal mcp__<server>__ prefix, so the server
# segment is the one part that must not move. A configurable name would
# silently stop matching, and the symptom is a permission prompt mid-run on a
# tool that looks allowlisted, exactly as the dual Claude Code Remote
# registration does.
#
# The tool and toolset variables below stay configurable precisely because the
# allowlist is a glob over this prefix: whatever surface they select is covered,
# including tools upstream renames. Narrowing that glob to fixed tool names
# would make every override drift out of the allowlist.
MCP_NAME="github-deps"
# features= is the query-parameter channel (github/github-mcp-server#3146)
# rather than X-MCP-Features, because the header wins whenever it is present -
# including when empty or misspelled - and a silently-losing query parameter is
# a bad failure mode. Set one channel or the other, never both.
MCP_URL="${AGENT_SKILLS_GH_MCP_URL:-https://api.githubcopilot.com/mcp/?features=issue_dependencies}"
# Two channels, because the two gaps above are missing for different reasons.
# The dependency tools are named individually - their names come from the
# server's own feature-flag documentation, so naming them is safe. Projects is
# requested as a toolset, because its grouped tool names (projects_get,
# projects_list, projects_write) may be renamed upstream and an unrecognised
# name in X-MCP-Tools is dropped silently rather than erroring.
#
# The two compose: a tool named in X-MCP-Tools is available even when its
# toolset is not enabled. Setting X-MCP-Toolsets at all replaces the defaults,
# which is what keeps this surface disjoint from the built-in server's - no
# overlapping tool names, so nothing has to arbitrate between them.
MCP_TOOLSETS="${AGENT_SKILLS_GH_MCP_TOOLSETS:-projects}"
MCP_TOOLS="${AGENT_SKILLS_GH_MCP_TOOLS:-issue_dependency_read,issue_dependency_write}"

if [ "${AGENT_SKILLS_GH_MCP:-0}" != "1" ]; then
  # Remove rather than merely skip. An entry left behind by an earlier run with
  # the flag set keeps connecting on every Claude start, and if the credential
  # went away at the same time that is precisely the repeated startup failure
  # the opt-in exists to avoid - a wrong entry that is invisible, the same
  # failure mode permissions.json keeps a managed-set record for. Only this
  # entry is touched; unrelated configuration is preserved.
  if [ -f "$MCP_CONFIG_FILE" ] && command -v jq >/dev/null 2>&1 \
     && jq -e --arg n "$MCP_NAME" '.mcpServers[$n] // empty' \
          "$MCP_CONFIG_FILE" >/dev/null 2>&1; then
    jq --arg n "$MCP_NAME" 'del(.mcpServers[$n])' \
      "$MCP_CONFIG_FILE" > "$MCP_CONFIG_FILE.tmp"
    mv "$MCP_CONFIG_FILE.tmp" "$MCP_CONFIG_FILE"
    echo "Extra GitHub MCP server disabled - removed '$MCP_NAME'"
  else
    echo "Extra GitHub MCP server disabled (set AGENT_SKILLS_GH_MCP=1 to install)"
  fi
elif ! command -v jq >/dev/null 2>&1; then
  echo "WARNING: jq unavailable, cannot install the extra GitHub MCP server." >&2
else
  echo "Installing extra GitHub MCP server as '$MCP_NAME'..."
  [ -f "$MCP_CONFIG_FILE" ] || printf '{}\n' > "$MCP_CONFIG_FILE"

  # Single-quoted so ${GITHUB_MCP_PAT} reaches the file unexpanded, for Claude
  # Code to resolve when it loads the server. Under the default proxy auth the
  # token never enters the container at all; under pat auth only this
  # placeholder is written, so the secret lands in no file either way.
  MCP_AUTH_VALUE='Bearer ${GITHUB_MCP_PAT}'
  [ "${AGENT_SKILLS_GH_MCP_AUTH:-proxy}" = "pat" ] || MCP_AUTH_VALUE=""

  jq --arg name "$MCP_NAME" \
     --arg url "$MCP_URL" \
     --arg tools "$MCP_TOOLS" \
     --arg toolsets "$MCP_TOOLSETS" \
     --arg auth "$MCP_AUTH_VALUE" '
    .mcpServers //= {} |
    .mcpServers[$name] = (
      {type: "http", url: $url,
       headers: {"X-MCP-Tools": $tools, "X-MCP-Toolsets": $toolsets}}
      | if $auth == "" then . else .headers.Authorization = $auth end
    )
  ' "$MCP_CONFIG_FILE" > "$MCP_CONFIG_FILE.tmp"
  mv "$MCP_CONFIG_FILE.tmp" "$MCP_CONFIG_FILE"
  chmod 600 "$MCP_CONFIG_FILE"
  echo "  + $MCP_NAME (auth: ${AGENT_SKILLS_GH_MCP_AUTH:-proxy})"
fi

echo "Done!"
