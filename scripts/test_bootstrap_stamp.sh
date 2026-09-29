#!/bin/bash
# test_bootstrap_stamp.sh - runs bootstrap.sh against a throwaway HOME and
# checks the install stamp it writes. Run after any edit to bootstrap.sh's
# stamp section. Exits 0 with "ALL PASS" only when every case passes.
#
# HOME is replaced for every run, and AGENT_SKILLS_GH_MCP is unset, so the
# permissions and MCP steps only ever touch $HOME/.claude and $HOME/.claude.json
# inside the scratch directory - never the real ones.
set -u

# Hermetic identity for the scratch commits, as test-checkpoint-capture.sh does:
# a clean CI runner has none configured.
GIT_AUTHOR_NAME=stamp-test
GIT_AUTHOR_EMAIL=stamp-test@invalid
GIT_COMMITTER_NAME=stamp-test
GIT_COMMITTER_EMAIL=stamp-test@invalid
export GIT_AUTHOR_NAME GIT_AUTHOR_EMAIL GIT_COMMITTER_NAME GIT_COMMITTER_EMAIL
unset AGENT_SKILLS_GH_MCP

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)" || exit 1
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAILED=0

report() { # $1 name, $2 ok(0/1)
  if [ "$2" -eq 0 ]; then PASS=$((PASS+1)); echo "PASS: $1"
  else FAILED=$((FAILED+1)); echo "FAIL: $1"; fi
}

field() { sed -n "s/^$2=//p" "$1"; } # $1 file, $2 key

# $1 checkout, $2 home. Output goes to $2.log for a failing case to show.
install() {
  mkdir -p "$2"
  HOME="$2" bash "$1/bootstrap.sh" >"$2.log" 2>&1
}

# Every skill the checkout ships has a .source equal to the run's record.
all_stamped() { # $1 checkout, $2 home
  rec="$2/.claude/.agent-skills-install"
  [ -f "$rec" ] || return 1
  for skill_md in "$1"/skills/*/SKILL.md; do
    s="$(basename "$(dirname "$skill_md")")"
    cmp -s "$rec" "$2/.claude/skills/$s/.source" || { echo "  unstamped: $s"; return 1; }
  done
}

# The working tree, without .git: what a tarball install sees. tar rather than
# cp so .git is excluded the same way on BSD and GNU.
copy_tree() { # $1 dest
  mkdir -p "$1"
  (cd "$ROOT" && tar cf - --exclude=.git .) | (cd "$1" && tar xf -)
}

# --- case 1: stamp from this checkout ----------------------------------------
H="$TMP/home1"; ok=1
if install "$ROOT" "$H" && all_stamped "$ROOT" "$H"; then
  rec="$H/.claude/.agent-skills-install"
  [ "$(field "$rec" commit)" = "$(git -C "$ROOT" rev-parse HEAD)" ] \
    && [ "$(field "$rec" committed)" = "$(git -C "$ROOT" log -1 --format=%cI)" ] \
    && field "$rec" installed | grep -Eq '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$' \
    && field "$rec" repo | grep -Eq '^https://[^@]+$' \
    && ok=0
fi
[ $ok -eq 0 ] || cat "$H.log"
report "every installed skill stamped with git rev-parse HEAD" $ok

# --- case 2: a second run overwrites the stamp -------------------------------
ok=1
first="$(field "$H/.claude/.agent-skills-install" installed)"
sleep 1
if install "$ROOT" "$H" && all_stamped "$ROOT" "$H"; then
  [ "$(field "$H/.claude/.agent-skills-install" installed)" != "$first" ] && ok=0
fi
report "second run rewrites every stamp" $ok

# --- case 3: no .git still installs, as unknown ------------------------------
C="$TMP/nogit"; H="$TMP/home3"; ok=1
copy_tree "$C"
if [ ! -e "$C/.git" ] && install "$C" "$H" && all_stamped "$C" "$H"; then
  rec="$H/.claude/.agent-skills-install"
  [ "$(field "$rec" commit)" = unknown ] \
    && [ "$(field "$rec" committed)" = unknown ] \
    && [ "$(field "$rec" repo)" = https://github.com/baseten/agent-skills ] \
    && ok=0
fi
[ $ok -eq 0 ] || cat "$H.log"
report "checkout without .git installs and writes commit=unknown" $ok

# --- case 3b: no .git, unpacked inside someone else's repository -------------
# git would happily answer with the enclosing repository's HEAD.
O="$TMP/outer"; C="$O/vendor/agent-skills"; H="$TMP/home3b"; ok=1
git init -q "$O"
git -C "$O" commit -q --allow-empty -m outer
copy_tree "$C"
if install "$C" "$H" && all_stamped "$C" "$H"; then
  [ "$(field "$H/.claude/.agent-skills-install" commit)" = unknown ] && ok=0
fi
report "copy without .git inside another repo is not stamped with its HEAD" $ok

# --- case 4: credentials in the origin URL never reach the stamp -------------
C="$TMP/cred"; ok=0
copy_tree "$C"
git -C "$C" init -q
git -C "$C" add -A
git -C "$C" commit -q -m scratch
for url in \
  "https://x-access-token:SECRETTOKEN@github.com/example/fork.git" \
  "https://SECRETTOKEN@github.com/example/fork" \
  "ssh://git@github.com:22/example/fork.git" \
  "git@github.com:example/fork.git"; do
  git -C "$C" remote remove origin 2>/dev/null
  git -C "$C" remote add origin "$url"
  H="$TMP/home4-$PASS$FAILED-$(printf %s "$url" | cksum | cut -d' ' -f1)"
  if install "$C" "$H" && all_stamped "$C" "$H"; then
    got="$(field "$H/.claude/.agent-skills-install" repo)"
    if [ "$got" != https://github.com/example/fork ] \
       || grep -rq SECRETTOKEN "$H/.claude" "$H.log"; then
      echo "  $url -> $got"; ok=1
    fi
  else
    cat "$H.log"; ok=1
  fi
done
report "origin URL normalised to https with credentials stripped" $ok

# --- case 5: a remote that is not a URL falls back to the default ------------
git -C "$C" remote set-url origin "$TMP/some/local/path"
H="$TMP/home5"; ok=1
if install "$C" "$H"; then
  [ "$(field "$H/.claude/.agent-skills-install" repo)" = https://github.com/baseten/agent-skills ] \
    && [ "$(field "$H/.claude/.agent-skills-install" commit)" = "$(git -C "$C" rev-parse HEAD)" ] \
    && ok=0
fi
report "local-path origin falls back to the default repo URL" $ok

echo "passed $PASS, failed $FAILED"
[ "$FAILED" -eq 0 ] && echo "ALL PASS"
[ "$FAILED" -eq 0 ]
