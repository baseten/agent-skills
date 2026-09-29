#!/usr/bin/env bash
# Copy each shared rule into every skill that applies it.
#
# A shared rule cannot live at the repo root and be read from an installed
# skill: bootstrap.sh copies `skills/<name>/` and nothing else, so
# `../../rules/x.md` does not exist on a machine that installed one skill. And
# it cannot live inside one skill either - many skills cite this one, and
# whichever skill owned it would become a dependency the rest carry for a rule
# they only read.
#
# So the rule is held once under rules/ and copied into each applying skill's
# references/ at install time - bootstrap.sh, ai-alex's update-local-claude-skills, the eval
# runner and CI all run this first. The copies are gitignored, never committed:
# rules/ is the only copy in the repository.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# rule source  ->  skills that apply it
AUTHORED_WRITE_FORM="backlog-orchestrator settle-and-merge create-pr normalize-github-dependencies
  npm-dependency-upgrade-orchestrator
  merge-stack repair-pr resolve-pr-comment review-docs review-skill settle-outstanding-decisions
  summarize-tranche upgrade-npm-dependency validate-backlog supervise-prs"

# One variable per rule, named for the rule file in upper snake case.
# check_shared_rules.py reads these assignments to learn which skills are
# declared consumers of which rule, so the spelling is load-bearing:
# ABSENCE_IS_NOT_A_VERDICT <-> rules/absence-is-not-a-verdict.md.
RULES="authored-write-form absence-is-not-a-verdict prose-review-round-budget
  establish-do-not-assume a-passing-test-is-not-a-verified-fix
  posting-identity agent-policy review-feedback draft-state
  repair-rounds mechanical-pushes review-trigger ci-and-review-verdicts
  ci-attribution watch-and-read wake-budget platform-pr-posture"

# Each list names only the skills that APPLY the rule, and every one of them
# must cite it in its own SKILL.md (check_shared_rules.py). A rule that cites
# another rule - `references/<x>.md` in its own text - does not add to these
# lists: the loop at the bottom derives that carriage per skill, transitively,
# and copies it too. So a skill here carries more than the lists say, and the
# lists still say exactly which skills apply what.
#
# Skills that make an authored forge/tracker write and select its author, or
# that pass or merge the run's posting-identity map.
POSTING_IDENTITY="backlog-orchestrator settle-and-merge swarm create-pr implement-issue
  implement-issue-core merge-stack repair-pr resolve-pr-comment review-docs
  settle-outstanding-decisions supervise-prs"

# Skills that read .claude/agent-policy.json, or gate on what it grants.
AGENT_POLICY="backlog-orchestrator settle-and-merge implement-issue
  npm-dependency-upgrade-orchestrator supervise-prs"

# Skills that promote a draft, decline to, or gate on the drafts it defines as held.
DRAFT_STATE="backlog-orchestrator settle-and-merge supervise-prs"

# Skills that dispatch a repair-pr pass, choose its model and count its cycles.
REPAIR_ROUNDS="supervise-prs"

# Skills that decide whether a push re-triggers review, or is re-reviewed.
MECHANICAL_PUSHES="review-docs backlog-orchestrator
  npm-dependency-upgrade-orchestrator supervise-prs"

# Skills that issue or re-trigger an automated review, or gate on the rounds
# its routing requires.
REVIEW_TRIGGER="create-pr backlog-orchestrator
  npm-dependency-upgrade-orchestrator settle-and-merge supervise-prs"

# Skills that gate on, or supervise a PR toward, green CI or a clean review.
CI_AND_REVIEW_VERDICTS="
  npm-dependency-upgrade-orchestrator settle-and-merge merge-stack supervise-prs"

# Skills that decide whether a red check - on CI or in a local run - is the
# change's own failure.
CI_ATTRIBUTION="backlog-orchestrator
  npm-dependency-upgrade-orchestrator repair-pr implement-issue-core supervise-prs"

# Skills that supervise what they track: arm its watch, report no-change
# results, and read its state within the credential's allowances.
WATCH_AND_READ="swarm backlog-orchestrator supervise-prs"

# Skills that arm a recurring check-in and bound it.
WAKE_BUDGET="backlog-orchestrator supervise-prs npm-dependency-upgrade-orchestrator"

# Skills whose session arms a PR-activity subscription, receives its wakes, or
# reports to the user that the platform's posture was overridden. Swarm cites
# this rule to distinguish its worker countermand from a standalone supervisor.
PLATFORM_PR_POSTURE="backlog-orchestrator supervise-prs
  npm-dependency-upgrade-orchestrator implement-issue swarm"

# Skills that classify, repair, report or gate on review threads.
REVIEW_FEEDBACK="backlog-orchestrator repair-pr resolve-pr-comment
  review-docs summarize-tranche supervise-prs"

# Skills that act on something asserted by an agent, assumed about a provider,
# or that author a write making claims about existing code or current state.
ESTABLISH_DO_NOT_ASSUME="backlog-orchestrator swarm settle-and-merge repair-pr
  validate-backlog review-skill implement-issue-core create-pr resolve-pr-comment
  summarize-tranche settle-outstanding-decisions implement-issue supervise-prs"

# Skills that write or change a test as part of their work.
A_PASSING_TEST_IS_NOT_A_VERIFIED_FIX="implement-issue-core repair-pr
  upgrade-npm-dependency resolve-pr-comment"

# The prose reviewers. Both terminate on the same budget; neither owns it.
PROSE_REVIEW_ROUND_BUDGET="review-docs review-skill repair-pr"
# Skills that make a decision on the result of a lookup, where an empty result
# and a clean result are the same bytes.
ABSENCE_IS_NOT_A_VERDICT="backlog-orchestrator settle-and-merge repair-pr
  resolve-pr-comment merge-stack plan-merge-order validate-backlog
  normalize-github-dependencies
  upgrade-npm-dependency implement-issue-core
  review-docs review-skill summarize-tranche supervise-prs"


is_rule() { case " $(echo $RULES) " in *" $1 "*) return 0 ;; esac; return 1; }
cites_of() {  # the generated rules rules/$1.md cites, itself excluded
  { grep -oE '`references/[a-z0-9-]+\.md`' "$ROOT/rules/$1.md" || true; } \
    | sed -E 's/^`references\/(.*)\.md`$/\1/' | sort -u
}

echo "Refreshing shared rules..."
for rule in $RULES; do
  var="$(echo "$rule" | tr 'a-z-' 'A-Z_')"
  eval "consumers=\$$var"
  [ -n "$consumers" ] || { echo "no consumer list for rules/$rule.md (expected \$$var)" >&2; exit 1; }
  [ -f "$ROOT/rules/$rule.md" ] || { echo "missing source: rules/$rule.md" >&2; exit 1; }
  for skill in $consumers; do
    [ -d "$ROOT/skills/$skill" ] || { echo "no such skill: $skill" >&2; exit 1; }
  done
done

for skill_md in "$ROOT"/skills/*/SKILL.md; do
  skill="$(basename "$(dirname "$skill_md")")"
  # declared: the lists above; then derived: what those rules cite, to a fixed point.
  declared=" "
  for rule in $RULES; do
    var="$(echo "$rule" | tr 'a-z-' 'A-Z_')"
    eval "consumers=\$$var"
    case " $(echo $consumers) " in *" $skill "*) declared="$declared$rule " ;; esac
  done
  carried="$declared"
  changed=1
  while [ "$changed" = 1 ]; do
    changed=0
    for r in $carried; do
      for c in $(cites_of "$r"); do
        [ "$c" = "$r" ] && continue
        is_rule "$c" || continue
        case "$carried" in *" $c "*) ;; *) carried="$carried$c "; changed=1 ;; esac
      done
    done
  done
  dest_dir="$ROOT/skills/$skill/references"
  # A generated rule this skill no longer carries is removed, so a stale copy
  # cannot stand in for a derivation the generator stopped making.
  for rule in $RULES; do
    case "$carried" in *" $rule "*) ;; *) rm -f "$dest_dir/$rule.md" ;; esac
  done
  for r in $carried; do
    mkdir -p "$dest_dir"
    cp "$ROOT/rules/$r.md" "$dest_dir/$r.md"
    case "$declared" in
      *" $r "*) echo "  skills/$skill/references/$r.md" ;;
      *) echo "  skills/$skill/references/$r.md  (derived)" ;;
    esac
  done
done
echo "Done."
