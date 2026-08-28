#!/bin/sh
# test-checkpoint-capture.sh — executes checkpoint-capture.sh against scratch
# repositories. Run after ANY edit to checkpoint-capture.sh; reading it and
# agreeing is not verification (every defect the sequence has had was found by
# executing it). Exits 0 with "ALL PASS" only when every case passes.

set -u
SCRIPT=$(cd "$(dirname "$0")" && pwd)/checkpoint-capture.sh
TMP=$(mktemp -d) || exit 1
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAILED=0

report() { # $1 name, $2 ok(0/1)
  if [ "$2" -eq 0 ]; then PASS=$((PASS+1)); echo "PASS: $1"
  else FAILED=$((FAILED+1)); echo "FAIL: $1"; fi
}

# Build a scratch remote + worker clone with one committed file and dirty edits.
# Sets globals: d (case dir) and HEAD_SHA (worker head).
# $1 = case dir name, $2 = branch name
setup() {
  d=$TMP/$1
  git init -q --bare "$d/remote.git"
  git init -q "$d/wt"
  git -C "$d/wt" -c user.email=t@t -c user.name=t commit -q --allow-empty -m base
  echo one > "$d/wt/owned.txt"
  git -C "$d/wt" add owned.txt
  git -C "$d/wt" -c user.email=t@t -c user.name=t commit -q -m owned
  git -C "$d/wt" branch -M "$2"
  git -C "$d/wt" remote add origin "$d/remote.git"
  git -C "$d/wt" push -q origin "$2"
  HEAD_SHA=$(git -C "$d/wt" rev-parse HEAD)
  # dirty state: an owned edit and an unrelated (non-allowlisted) edit
  echo two >> "$d/wt/owned.txt"
  echo stray > "$d/wt/stray.txt"
  printf 'owned.txt\n' > "$d/paths"
}

enc() { printf %s "$1" | sed 's/%/%25/g; s|/|%2F|g'; }

# --- case 1: clean capture ---------------------------------------------------
setup case1 feat/one; ok=1
if "$SCRIPT" "$d/wt" feat/one "$HEAD_SHA" "$d/paths" >/dev/null 2>&1; then
  ref="refs/checkpoints/$(enc feat/one)"
  cap=$(git -C "$d/remote.git" rev-parse "$ref" 2>/dev/null)
  headnow=$(git -C "$d/wt" rev-parse HEAD)
  dirty=$(git -C "$d/wt" status --porcelain)
  files=$(git -C "$d/wt" diff-tree -r --name-only --no-commit-id "$HEAD_SHA" "$cap")
  # ref written; HEAD unmoved; worktree still dirty; capture touches only owned.txt
  [ -n "$cap" ] && [ "$headnow" = "$HEAD_SHA" ] && [ -n "$dirty" ] && [ "$files" = "owned.txt" ] && ok=0
fi
report "clean capture: ref written, HEAD unmoved, worktree dirty, only owned paths" $ok

# --- case 2: unreadable/missing allowlist aborts before push ------------------
setup case2 feat/two; ok=1
if ! "$SCRIPT" "$d/wt" feat/two "$HEAD_SHA" "$d/absent-paths" >/dev/null 2>&1; then
  git -C "$d/remote.git" rev-parse "refs/checkpoints/$(enc feat/two)" >/dev/null 2>&1 || ok=0
fi
report "missing allowlist: non-zero exit, no ref pushed" $ok

# --- case 3: stale path in allowlist aborts before push -----------------------
setup case3 feat/three; ok=1
printf 'owned.txt\nno-such-file.txt\n' > "$d/paths"
if ! "$SCRIPT" "$d/wt" feat/three "$HEAD_SHA" "$d/paths" >/dev/null 2>&1; then
  git -C "$d/remote.git" rev-parse "refs/checkpoints/$(enc feat/three)" >/dev/null 2>&1 || ok=0
fi
report "stale allowlisted path: git add fails, no ref pushed" $ok

# --- case 4: recapture replaces the single per-branch ref ---------------------
setup case4 feat/four; ok=1
if "$SCRIPT" "$d/wt" feat/four "$HEAD_SHA" "$d/paths" >/dev/null 2>&1; then
  ref="refs/checkpoints/$(enc feat/four)"
  first=$(git -C "$d/remote.git" rev-parse "$ref")
  echo three >> "$d/wt/owned.txt"
  if "$SCRIPT" "$d/wt" feat/four "$HEAD_SHA" "$d/paths" >/dev/null 2>&1; then
    second=$(git -C "$d/remote.git" rev-parse "$ref")
    count=$(git -C "$d/remote.git" for-each-ref 'refs/checkpoints/**' | wc -l)
    [ "$first" != "$second" ] && [ "$count" -eq 1 ] && ok=0
  fi
fi
report "recapture: one ref per branch, force-replaced" $ok

# --- case 5: ref encoding is injective (feature/foo vs feature%2Ffoo) ----------
a=$(enc 'feature/foo'); b=$(enc 'feature%2Ffoo'); ok=1
[ "$a" = 'feature%2Ffoo' ] && [ "$b" = 'feature%252Ffoo' ] && [ "$a" != "$b" ] && ok=0
report "encoding: % escaped before /, mapping injective" $ok

# --- case 6: prefix-related branches cannot collide (no nested ref paths) -----
setup case6 feature/foo; ok=1
if "$SCRIPT" "$d/wt" feature/foo "$HEAD_SHA" "$d/paths" >/dev/null 2>&1; then
  # a capture for prefix-related branch feature/foo/bar against the same remote
  # (the branch need not exist locally — only the ref name is derived from it;
  # note refs/heads/feature/foo would itself block refs/heads/feature/foo/bar,
  # which is exactly the collision the encoding removes for checkpoint refs)
  echo more >> "$d/wt/owned.txt"
  if "$SCRIPT" "$d/wt" feature/foo/bar "$HEAD_SHA" "$d/paths" >/dev/null 2>&1; then
    n=$(git -C "$d/remote.git" for-each-ref 'refs/checkpoints/**' | wc -l)
    [ "$n" -eq 2 ] && ok=0
  fi
fi
report "prefix-related branches: both refs coexist (no directory collision)" $ok

# --- case 7: non-ASCII pathname captures (raw vs C-quoted comparison) ---------
setup case7 feat/seven; ok=1
printf 'body\n' > "$d/wt/café.txt"
git -C "$d/wt" add café.txt
git -C "$d/wt" -c user.email=t@t -c user.name=t commit -q -m utf8
git -C "$d/wt" push -q origin feat/seven
HEAD_SHA=$(git -C "$d/wt" rev-parse HEAD)
printf 'more\n' >> "$d/wt/café.txt"
printf 'café.txt\n' > "$d/paths"
if "$SCRIPT" "$d/wt" feat/seven "$HEAD_SHA" "$d/paths" >/dev/null 2>&1; then
  cap=$(git -C "$d/remote.git" rev-parse "refs/checkpoints/$(enc feat/seven)" 2>/dev/null)
  [ -n "$cap" ] && ok=0
fi
report "non-ASCII pathname: capture succeeds (raw comparison, not C-quoted)" $ok

echo
if [ "$FAILED" -eq 0 ]; then echo "ALL PASS ($PASS cases)"; exit 0
else echo "$FAILED FAILED, $PASS passed"; exit 1; fi
