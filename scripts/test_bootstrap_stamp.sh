#!/bin/bash
# test_bootstrap_stamp.sh - runs bootstrap.sh against a throwaway HOME and
# checks the install stamp it writes. Run after any edit to bootstrap.sh's
# stamp section. Exits 0 with "ALL PASS" only when every case passes.
#
# HOME is replaced for every run, and AGENT_SKILLS_GH_MCP is unset, so the
# permissions and MCP steps only ever touch $HOME/.claude and $HOME/.claude.json
# inside the scratch directory - never the real ones.
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Resolved before the environment below is cleared: the GIT_DIR case needs it.
ROOT_GIT_DIR="$(git -C "$ROOT" rev-parse --absolute-git-dir)" || exit 1
# An explicit template, because BSD mktemp -d ignores TMPDIR without one.
TMP="$(mktemp -d "${TMPDIR:-/tmp}/bootstrap-stamp.XXXXXX")" || exit 1
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAILED=0

# Hermetic: nobody's global or system git config reaches the scratch repos. A
# commit.gpgsign or a hook there made the setup commits fail silently, and the
# cases built on them passed without testing anything. GIT_CONFIG_GLOBAL is
# also where the insteadOf case writes its rewrite.
HOME="$TMP/home"
GIT_CONFIG_GLOBAL="$TMP/gitconfig"
GIT_CONFIG_NOSYSTEM=1
GIT_AUTHOR_NAME=stamp-test
GIT_AUTHOR_EMAIL=stamp-test@invalid
GIT_COMMITTER_NAME=stamp-test
GIT_COMMITTER_EMAIL=stamp-test@invalid
export HOME GIT_CONFIG_GLOBAL GIT_CONFIG_NOSYSTEM
export GIT_AUTHOR_NAME GIT_AUTHOR_EMAIL GIT_COMMITTER_NAME GIT_COMMITTER_EMAIL
unset AGENT_SKILLS_GH_MCP XDG_CONFIG_HOME GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_COMMON_DIR
mkdir -p "$HOME"; : > "$GIT_CONFIG_GLOBAL"

report() { # $1 name, $2 ok(0/1)
  if [ "$2" -eq 0 ]; then PASS=$((PASS+1)); echo "PASS: $1"
  else FAILED=$((FAILED+1)); echo "FAIL: $1"; fi
}

# A setup step that fails is a broken test, never a passing case.
must() { "$@" || { echo "SETUP FAILED: $*" >&2; exit 1; }; }

field() { sed -n "s/^$2=//p" "$1"; } # $1 file, $2 key
rec_of() { echo "$1/.claude/.agent-skills-install"; } # $1 home

# $1 checkout, $2 home. Output goes to $2.log for a failing case to show.
install() {
  mkdir -p "$2"
  HOME="$2" bash "$1/bootstrap.sh" >"$2.log" 2>&1
}

# Every skill the checkout ships has a .source equal to the run's record.
all_stamped() { # $1 checkout, $2 home
  local rec s skill_md
  rec="$(rec_of "$2")"
  [ -f "$rec" ] || return 1
  for skill_md in "$1"/skills/*/SKILL.md; do
    s="$(basename "$(dirname "$skill_md")")"
    cmp -s "$rec" "$2/.claude/skills/$s/.source" || { echo "  unstamped: $s"; return 1; }
  done
}

# $1 home, $2 repo, $3 commit, $4 committed. Also: exactly the four fields.
record_is() {
  local rec
  rec="$(rec_of "$1")"
  [ "$(wc -l < "$rec" | tr -d ' ')" = 4 ] \
    && [ "$(field "$rec" repo)" = "$2" ] \
    && [ "$(field "$rec" commit)" = "$3" ] \
    && [ "$(field "$rec" committed)" = "$4" ] \
    || { echo "  record:"; sed 's/^/    /' "$rec"; return 1; }
}

# The working tree, without .git: what a tarball install sees. tar rather than
# cp so .git is excluded the same way on BSD and GNU.
copy_tree() { # $1 dest
  must mkdir -p "$1"
  (cd "$ROOT" && tar cf - --exclude=.git .) | (cd "$1" && tar xf -) \
    || { echo "SETUP FAILED: copy to $1" >&2; exit 1; }
}

# A committed git copy of the working tree with origin set to $2.
git_copy() { # $1 dest, $2 origin url
  copy_tree "$1"
  must git -C "$1" init -q
  must git -C "$1" add -A
  must git -C "$1" commit -q -m scratch
  must git -C "$1" remote add origin "$2"
}

head_of() { git -C "$1" rev-parse HEAD; }
date_of() { git -C "$1" log -1 --format=%cI; }

# --- stamp from this checkout ------------------------------------------------
H="$TMP/h-root"; ok=1
if install "$ROOT" "$H" && all_stamped "$ROOT" "$H"; then
  rec="$(rec_of "$H")"
  record_is "$H" "$(field "$rec" repo)" "$(head_of "$ROOT")" "$(date_of "$ROOT")" \
    && field "$rec" installed | grep -Eq '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$' \
    && ok=0
fi
[ $ok -eq 0 ] || cat "$H.log"
report "every installed skill stamped with git rev-parse HEAD" $ok

# --- a second run replaces the stamp, and does not append to it -------------
ok=1
first="$(field "$(rec_of "$H")" installed)"
sleep 1
if install "$ROOT" "$H" && all_stamped "$ROOT" "$H"; then
  set -- "$ROOT"/skills/*/SKILL.md
  one="$H/.claude/skills/$(basename "$(dirname "$1")")/.source"
  [ "$(field "$(rec_of "$H")" installed)" != "$first" ] \
    && [ "$(grep -c '^installed=' "$(rec_of "$H")")" = 1 ] \
    && [ "$(grep -c '^installed=' "$one")" = 1 ] \
    && [ "$(wc -l < "$one" | tr -d ' ')" = 4 ] \
    && ok=0
fi
report "second run rewrites every stamp, one record each" $ok

# --- no .git still installs, as unknown --------------------------------------
C="$TMP/nogit"; H="$TMP/h-nogit"; ok=1
copy_tree "$C"
if [ ! -e "$C/.git" ] && install "$C" "$H" && all_stamped "$C" "$H" \
   && record_is "$H" unknown unknown unknown; then ok=0; fi
[ $ok -eq 0 ] || cat "$H.log"
report "checkout without .git installs and writes unknown" $ok

# --- no .git, unpacked inside someone else's repository ----------------------
# git would happily answer with the enclosing repository's HEAD.
O="$TMP/outer"; C="$O/vendor/agent-skills"; H="$TMP/h-outer"; ok=1
must git init -q "$O"
must git -C "$O" commit -q --allow-empty -m outer
copy_tree "$C"
if install "$C" "$H" && all_stamped "$C" "$H" \
   && record_is "$H" unknown unknown unknown; then ok=0; fi
report "copy without .git inside another repo is not stamped with its HEAD" $ok

# --- an inherited GIT_DIR cannot lend another repository's HEAD --------------
C="$TMP/nogit"; H="$TMP/h-gitdir"; ok=1
if GIT_DIR="$ROOT_GIT_DIR" install "$C" "$H" && all_stamped "$C" "$H" \
   && record_is "$H" unknown unknown unknown; then ok=0; fi
report "GIT_DIR in the environment does not bypass the own-checkout check" $ok

# --- origin URLs: normalised, credentials never written ----------------------
# Each is "origin url|expected repo". SECRETTOKEN must appear nowhere after.
C="$TMP/cred"; ok=0
git_copy "$C" https://placeholder.invalid/x
fork=https://github.com/example/fork
for pair in \
  "https://x-access-token:SECRETTOKEN@github.com/example/fork.git|$fork" \
  "https://SECRETTOKEN@github.com/example/fork|$fork" \
  "https://github.com/example/fork?token=SECRETTOKEN|$fork" \
  "https://github.com/example/fork.git#SECRETTOKEN|$fork" \
  "ssh://git@github.com:22/example/fork.git|$fork" \
  "git@github.com:example/fork.git|$fork" \
  "https://u.s:SECRETTOKEN/en@github.com/o/r|unknown" \
  "http://127.0.0.1:8080/git/example/fork|unknown" \
  "http://localhost/git/example/fork|unknown" \
  "$TMP/some/local/path|unknown" \
  "file://$TMP/some/local/path|unknown"; do
  url="${pair%|*}"; want="${pair##*|}"
  must git -C "$C" remote set-url origin "$url"
  H="$TMP/h-url-$(printf %s "$url" | cksum | cut -d' ' -f1)"
  if install "$C" "$H" && all_stamped "$C" "$H" \
     && record_is "$H" "$want" "$(head_of "$C")" "$(date_of "$C")" \
     && ! grep -rq SECRETTOKEN "$H/.claude" "$H.log"; then :; else
    echo "  $url -> $(field "$(rec_of "$H")" repo) (want $want)"; ok=1
  fi
done
report "origin URLs normalised; credentials, IPs, local paths never written" $ok

# --- insteadOf is not applied: the configured origin is what is stamped ------
H="$TMP/h-insteadof"; ok=1
must git -C "$C" remote set-url origin https://github.com/example/fork.git
must git config --global url."http://127.0.0.1:9/git/".insteadOf https://github.com/
if install "$C" "$H" && record_is "$H" "$fork" "$(head_of "$C")" "$(date_of "$C")"; then ok=0; fi
must git config --global --unset url."http://127.0.0.1:9/git/".insteadOf
report "an insteadOf rewrite to a local proxy does not replace the origin" $ok

# --- no origin at all ------------------------------------------------------
H="$TMP/h-noorigin"; ok=1
must git -C "$C" remote remove origin
if install "$C" "$H" && record_is "$H" unknown "$(head_of "$C")" "$(date_of "$C")"; then ok=0; fi
report "no origin remote writes repo=unknown" $ok

# --- a repository with no commits yet --------------------------------------
C="$TMP/unborn"; H="$TMP/h-unborn"; ok=1
copy_tree "$C"
must git -C "$C" init -q
must git -C "$C" remote add origin https://github.com/example/fork
if install "$C" "$H" && all_stamped "$C" "$H" \
   && record_is "$H" "$fork" unknown unknown; then ok=0; fi
[ $ok -eq 0 ] || cat "$H.log"
report "unborn HEAD installs and writes commit=unknown" $ok

# --- a shallow clone, as the setup script makes ----------------------------
# CI checks out with full history, so this is the only place depth 1 runs.
# The working tree's bootstrap.sh is copied over the clone's so an uncommitted
# edit is what gets tested.
C="$TMP/shallow"; H="$TMP/h-shallow"; ok=1
must git clone -q --depth 1 "file://$ROOT" "$C"
must cp "$ROOT/bootstrap.sh" "$C/bootstrap.sh"
if [ "$(git -C "$C" rev-parse --is-shallow-repository)" = true ] \
   && install "$C" "$H" && all_stamped "$C" "$H" \
   && record_is "$H" unknown "$(head_of "$C")" "$(date_of "$C")"; then ok=0; fi
[ $ok -eq 0 ] || cat "$H.log"
report "depth-1 clone stamped with its HEAD" $ok

echo "passed $PASS, failed $FAILED"
[ "$FAILED" -eq 0 ] && echo "ALL PASS"
[ "$FAILED" -eq 0 ]
