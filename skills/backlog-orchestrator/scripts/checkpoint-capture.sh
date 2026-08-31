#!/bin/sh
# checkpoint-capture.sh — ref-neutral parent-side capture of a live worker's
# uncommitted work, pushed to a recovery ref. The tested implementation of the
# capture sequence in SKILL.md (Checkpoint compliance). Run
# test-checkpoint-capture.sh after ANY edit to this file: every defect this
# sequence has ever had was found by executing it, none by reading it.
#
# Usage:
#   checkpoint-capture.sh <worktree> <issue-branch> <worker-head-sha> \
#                         <issue-owned-paths-file> [remote]
#
# <issue-owned-paths-file>: one repo-relative path per line; both the paths
# staged into the capture and the allowlist the capture is validated against.
#
# Guarantees (any substitute must satisfy all of them):
#   - moves NOTHING the worker holds: not its index (GIT_INDEX_FILE isolates a
#     scratch index), not any ref (commit-tree attaches the commit to no ref),
#     not its worktree;
#   - seeds the scratch index from the worker's head BEFORE overlaying paths,
#     so unlisted files are never recorded as deletions;
#   - validates the capture against its parent BEFORE pushing, and fails
#     closed: no construction or validation step can fail into the push;
#   - diff-tree runs alone (never piped), and grep's exit status is checked
#     explicitly, so a failed validator never reads as an empty match;
#   - pathnames are compared in raw form (diff-tree -z), never the C-quoted
#     line form, so non-ASCII/backslash names match the literal allowlist;
#   - pushes to exactly one ref per issue branch (refs/checkpoints/<encoded>),
#     force-replaced on each capture;
#   - encodes the branch name into a single ref component, escaping % before /,
#     so the mapping is injective and no branch's ref can occupy a path
#     another branch's ref needs.
#
# Exit status: 0 = capture pushed and contains at least one changed path;
# 3 = nothing to capture (empty allowlist or no staged difference — nothing
# pushed; the caller must re-check what it thought needed capturing rather
# than treat the work as secured); any other non-zero = a step failed,
# nothing pushed, existing ref untouched. Deliberately &&-chained rather
# than relying on `set -e`:
# errexit is not honoured inside a subshell in every host shell, and this
# logic must not depend on the host shell's state.

WORKTREE=$1
BRANCH=$2
WORKER_HEAD=$3
PATHS_FILE=$4
REMOTE=${5:-origin}

[ -n "$WORKTREE" ] && [ -n "$BRANCH" ] && [ -n "$WORKER_HEAD" ] && [ -n "$PATHS_FILE" ] || {
  echo "usage: checkpoint-capture.sh <worktree> <issue-branch> <worker-head-sha> <issue-owned-paths-file> [remote]" >&2
  exit 2
}

# The allowlist must be readable before anything else runs — an unreadable
# allowlist must abort, never read as an empty list.
[ -r "$PATHS_FILE" ] || { echo "checkpoint-capture: allowlist not readable: $PATHS_FILE" >&2; exit 1; }

IDX=$(mktemp) || exit 1
rm -f "$IDX"

fail() { rm -f "$IDX"; exit 1; }

# Encode % before / so the mapping is reversible and injective:
# feature/foo -> feature%2Ffoo ; feature%2Ffoo -> feature%252Ffoo.
ref=$(printf %s "$BRANCH" | sed 's/%/%25/g; s|/|%2F|g') || fail

# Seed from the worker's head FIRST: a scratch index starts empty, and adding
# a path list into an empty index records every other file as a deletion.
GIT_INDEX_FILE=$IDX git -C "$WORKTREE" read-tree "$WORKER_HEAD" || fail

# Overlay only the issue-owned paths — every add runs under the scratch index
# and never touches the worker's own. A path that fails to add (stale, gone)
# aborts before anything is pushed.
# `|| [ -n "$p" ]` keeps a final line with no trailing newline: read returns
# non-zero at EOF even when it filled $p, and dropping that entry would stage
# nothing for a single-path file — a no-op checkpoint pushed successfully,
# licensing an archive that destroys the only copy of the work.
while IFS= read -r p || [ -n "$p" ]; do
  [ -n "$p" ] || continue
  GIT_INDEX_FILE=$IDX git -C "$WORKTREE" --literal-pathspecs add -- "$p" || fail
done < "$PATHS_FILE"

tree=$(GIT_INDEX_FILE=$IDX git -C "$WORKTREE" write-tree) || fail
[ -n "$tree" ] || fail
# commit-tree reads the author/committer identity from the environment and
# config, and fails without one. A container with git unconfigured would
# therefore lose the capture at exactly the moment work needs rescuing, so
# supply a fallback rather than failing — never overriding an identity that is
# already set, since a real one is more useful on the ref than a synthetic one.
# Fill in only the components git cannot resolve. `git var` fails when the
# identity is incomplete, so a config with user.name but no user.email would
# otherwise have its real name replaced along with the missing address.
fill_ident() { # $1 = AUTHOR|COMMITTER
  eval "have_name=\${GIT_${1}_NAME:-}"
  eval "have_email=\${GIT_${1}_EMAIL:-}"
  if [ -z "$have_name" ]; then
    have_name=$(git -C "$WORKTREE" config --get user.name 2>/dev/null) || have_name=
    [ -n "$have_name" ] || have_name=backlog-orchestrator
  fi
  if [ -z "$have_email" ]; then
    have_email=$(git -C "$WORKTREE" config --get user.email 2>/dev/null) || have_email=
    [ -n "$have_email" ] || have_email=backlog-orchestrator@invalid
  fi
  eval "GIT_${1}_NAME=\$have_name; export GIT_${1}_NAME"
  eval "GIT_${1}_EMAIL=\$have_email; export GIT_${1}_EMAIL"
}
git -C "$WORKTREE" var GIT_COMMITTER_IDENT >/dev/null 2>&1 || fill_ident COMMITTER
git -C "$WORKTREE" var GIT_AUTHOR_IDENT >/dev/null 2>&1 || fill_ident AUTHOR

commit=$(git -C "$WORKTREE" commit-tree "$tree" -p "$WORKER_HEAD" \
    -m "wip: parent checkpoint capture") || fail
[ -n "$commit" ] || fail

# Validate BEFORE pushing, and fail closed.
# diff-tree runs alone, never piped: in a pipeline only the last command's
# status survives, and a failed diff-tree would read as an empty match.
# -z (NUL-terminated) emits raw pathnames: the default line mode C-quotes
# non-ASCII/backslash names ("caf\303\251.txt"), which would never match the
# literal allowlist and abort every capture containing such a file. The
# output goes to a file, not a pipe, so diff-tree's own status still gates
# the push; tr then converts NUL to newline in a separate, status-checked step
# (a pathname containing a newline is unrepresentable in the line-based
# allowlist anyway, and the unexpected-path check fails closed on it).
git -C "$WORKTREE" diff-tree -r -z --name-only --no-commit-id \
    "$WORKER_HEAD" "$commit" > "$IDX.paths" || { rm -f "$IDX.paths"; fail; }
changed=$(tr '\0' '\n' < "$IDX.paths") || { rm -f "$IDX.paths"; fail; }
rm -f "$IDX.paths"

# grep: 1 = no unexpected paths (the pass case); 2 = grep itself failed,
# which must abort rather than read as empty.
unexpected=$(printf %s "$changed" | grep -vxF -f "$PATHS_FILE")
rc=$?
[ "$rc" -le 1 ] || fail
[ -z "$unexpected" ] || { echo "checkpoint-capture: capture touches unlisted paths:" >&2; printf '%s\n' "$unexpected" >&2; fail; }

# A capture that changed nothing must not read as a successful checkpoint:
# an empty allowlist, or listed paths with no staged difference, would push a
# no-op commit and exit 0 — and a caller reading that as "work secured" may
# archive the worker while its dirty files remain only in the destroyed
# worktree. Exit 3 (distinct from validation failure) so the caller re-checks
# what it thought needed capturing instead of proceeding.
[ -n "$changed" ] || {
  echo "checkpoint-capture: no changes captured (empty allowlist, or no staged difference on the listed paths); nothing pushed" >&2
  rm -f "$IDX"; exit 3
}

git -C "$WORKTREE" push --force "$REMOTE" "$commit:refs/checkpoints/$ref"
status=$?
rm -f "$IDX"
exit $status
