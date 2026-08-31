#!/usr/bin/env bash
# Advisory: name any skill whose contract changed in this PR without its evals
# changing too. Never fails the build — it cannot know whether a change needs
# a new scenario, only that nobody added one. The repo's own precedent (#52)
# is that new machinery gets pinned by a scenario; this is the reminder, not
# the rule.
#
#   scripts/eval_reminder.sh origin/main
set -euo pipefail

base="${1:?usage: eval_reminder.sh <base-ref>}"

changed="$(git diff --name-only "$base"...HEAD)"

flagged=0
while read -r skill; do
  [ -n "$skill" ] || continue
  if ! printf '%s\n' "$changed" | grep -qx "skills/$skill/evals/evals.json"; then
    if [ -f "skills/$skill/evals/evals.json" ]; then
      printf '::warning file=skills/%s/SKILL.md::%s contract changed but skills/%s/evals/evals.json did not. If this change adds or removes a rule, consider a scenario pinning it.\n' \
        "$skill" "$skill" "$skill"
      flagged=1
    fi
  fi
done < <(printf '%s\n' "$changed" \
  | grep -E '^skills/[^/]+/(SKILL|NOTES)\.md$' \
  | cut -d/ -f2 \
  | sort -u)

if [ "$flagged" -eq 0 ]; then
  echo "No skill contract changed without its evals, or the skills touched have none."
fi
