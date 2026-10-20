#!/bin/bash
# test_bootstrap_instructions.sh - runs bootstrap.sh against a throwaway HOME
# and checks the managed block it writes into ~/.claude/CLAUDE.md. Run after
# any edit to bootstrap.sh's global-instructions section. Exits 0 with
# "ALL PASS" only when every case passes.
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/bootstrap-instr.XXXXXX")" || exit 1
trap 'rm -rf "$TMP"' EXIT
unset AGENT_SKILLS_GH_MCP
PASS=0; FAILED=0

report() { # $1 name, $2 ok(0/1)
  if [ "$2" -eq 0 ]; then PASS=$((PASS+1)); echo "PASS: $1"
  else FAILED=$((FAILED+1)); echo "FAIL: $1"; fi
}
# $1 home. Output goes to $1.log for a failing case to show.
install() { mkdir -p "$1/.claude"; HOME="$1" bash "$ROOT/bootstrap.sh" >"$1.log" 2>&1; }
blocks() { grep -c '^<!-- agent-skills:begin' "$1/.claude/CLAUDE.md"; }
has_rule() { grep -qF -e "$(head -1 "$ROOT/global-instructions.md")" "$1/.claude/CLAUDE.md"; }

H="$TMP/fresh"; ok=1
if install "$H" && has_rule "$H" && [ "$(blocks "$H")" = 1 ]; then ok=0; fi
[ $ok -eq 0 ] || cat "$H.log"
report "no CLAUDE.md: created holding one block" $ok

H="$TMP/rerun"; ok=1
mkdir -p "$H/.claude"; printf '# Mine\n\nkeep me\n' > "$H/.claude/CLAUDE.md"
if install "$H" && install "$H" && [ "$(blocks "$H")" = 1 ] && has_rule "$H" \
   && [ "$(head -3 "$H/.claude/CLAUDE.md")" = "$(printf '# Mine\n\nkeep me')" ]; then ok=0; fi
[ $ok -eq 0 ] || cat "$H.log"
report "existing text kept, re-run leaves exactly one block" $ok

H="$TMP/stale"; ok=1
mkdir -p "$H/.claude"
printf 'before\n<!-- agent-skills:begin old -->\nSTALE RULE\n<!-- agent-skills:end -->\nafter\n' > "$H/.claude/CLAUDE.md"
if install "$H" && ! grep -q 'STALE RULE' "$H/.claude/CLAUDE.md" && has_rule "$H" \
   && [ "$(head -1 "$H/.claude/CLAUDE.md")" = before ] \
   && [ "$(tail -1 "$H/.claude/CLAUDE.md")" = after ]; then ok=0; fi
[ $ok -eq 0 ] || cat "$H.log"
report "stale block replaced in place, text either side kept" $ok

H="$TMP/broken"; ok=1
mkdir -p "$H/.claude"; printf 'x\n<!-- agent-skills:begin -->\nno end\n' > "$H/.claude/CLAUDE.md"
cp "$H/.claude/CLAUDE.md" "$TMP/broken.orig"
if install "$H" && cmp -s "$H/.claude/CLAUDE.md" "$TMP/broken.orig" \
   && grep -q 'unbalanced' "$H.log"; then ok=0; fi
[ $ok -eq 0 ] || cat "$H.log"
report "unbalanced markers: file untouched and reported" $ok

H="$TMP/link"; ok=1
mkdir -p "$H/.claude"; printf 'linked\n' > "$TMP/target.md"
ln -s "$TMP/target.md" "$H/.claude/CLAUDE.md"
if install "$H" && [ -L "$H/.claude/CLAUDE.md" ] && grep -q '^linked$' "$TMP/target.md" \
   && has_rule "$H"; then ok=0; fi
[ $ok -eq 0 ] || cat "$H.log"
report "a symlinked CLAUDE.md stays a symlink, written through" $ok

echo "passed $PASS, failed $FAILED"
[ "$FAILED" -eq 0 ] && echo "ALL PASS"
[ "$FAILED" -eq 0 ]
