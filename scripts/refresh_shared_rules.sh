#!/usr/bin/env bash
# Copy each shared rule into every skill that applies it.
#
# A shared rule cannot live at the repo root and be read from an installed
# skill: bootstrap.sh copies `skills/<name>/` and nothing else, so
# `../../rules/x.md` does not exist on a machine that installed one skill. And
# it cannot live inside one skill either - ten skills cite this one, and
# whichever skill owned it would be a dependency the other nine carry for a
# rule they only read.
#
# So the rule is held once under rules/ and copied into each applying skill's
# references/. The copies are generated: edit the source. check_shared_rules.py
# fails the build if a copy diverges.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# rule source  ->  skills that apply it
AUTHORED_WRITE_FORM="backlog-orchestrator create-pr npm-dependency-upgrade-orchestrator implement-issue
  merge-stack repair-pr resolve-pr-comment settle-outstanding-decisions
  summarize-tranche upgrade-npm-dependency validate-backlog"

echo "Refreshing shared rules..."
for skill in $AUTHORED_WRITE_FORM; do
  src="$ROOT/rules/authored-write-form.md"
  dest="$ROOT/skills/$skill/references/authored-write-form.md"
  [ -f "$src" ] || { echo "missing source: rules/authored-write-form.md" >&2; exit 1; }
  [ -d "$ROOT/skills/$skill" ] || { echo "no such skill: $skill" >&2; exit 1; }
  mkdir -p "$(dirname "$dest")"
  cp "$src" "$dest"
  echo "  skills/$skill/references/authored-write-form.md"
done
echo "Done."
