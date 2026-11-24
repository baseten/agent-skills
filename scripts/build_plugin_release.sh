#!/usr/bin/env bash
# Build, in this checkout, the tree the `release` branch carries: this commit
# plus the two things an install generates and the repository never commits.
#
# The plugin route installs the repository as committed (README, *Install as a
# plugin*), so nothing runs refresh_shared_rules.sh or writes a stamp on the
# installing machine. The marketplace therefore points at `release`, which the
# release workflow rebuilds from every push to main with this script:
#
#   - each skill's references/, from rules/, exactly as an install generates it;
#   - each skill's .source, the stamp rules/run-start.md reads for the version
#     line, naming the main commit the build came from - never the release
#     commit, which exists only to carry the generated files.
#
# main stays the only source: release is rebuilt, never edited.
#
# Usage: bash scripts/build_plugin_release.sh [repo-url]
# The repo URL defaults to the GitHub Actions repository, else `unknown`.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

bash "$ROOT/scripts/refresh_shared_rules.sh" >/dev/null

repo="${1:-}"
if [ -z "$repo" ] && [ -n "${GITHUB_REPOSITORY:-}" ]; then
  repo="${GITHUB_SERVER_URL:-https://github.com}/$GITHUB_REPOSITORY"
fi
[ -n "$repo" ] || repo="unknown"

commit="$(git -C "$ROOT" rev-parse --verify -q HEAD 2>/dev/null)" || commit=""
committed="$(git -C "$ROOT" log -1 --format=%cI 2>/dev/null)" || committed=""
built="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
[ -n "$commit" ] || commit="unknown"
[ -n "$committed" ] || committed="unknown"

# The same four keys bootstrap.sh writes, so the version line reads either
# install route the same way. `installed` is when this build ran: the plugin's
# files are fixed from then on, whenever a machine fetches them.
count=0
for skill_md in "$ROOT"/skills/*/SKILL.md; do
  [ -f "$skill_md" ] || continue
  printf 'repo=%s\ncommit=%s\ncommitted=%s\ninstalled=%s\n' \
    "$repo" "$commit" "$committed" "$built" > "$(dirname "$skill_md")/.source"
  count=$((count + 1))
done

echo "Built plugin tree: $count skills stamped $commit"
