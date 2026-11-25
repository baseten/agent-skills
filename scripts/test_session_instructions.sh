#!/bin/bash
# test_session_instructions.sh - runs the plugin's SessionStart hook against
# throwaway config directories and checks when it prints the rules. Exits 0
# with "ALL PASS" only when every case passes.
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOK="$ROOT/hooks/session-instructions.sh"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/session-instr.XXXXXX")" || exit 1
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAILED=0

report() { # $1 name, $2 ok(0/1)
  if [ "$2" -eq 0 ]; then PASS=$((PASS+1)); echo "PASS: $1"
  else FAILED=$((FAILED+1)); echo "FAIL: $1"; fi
}
# $1 config dir, $2 plugin root. Prints the hook's stdout; returns its status.
run() { env -u CLAUDE_CONFIG_DIR HOME="$TMP/home" CLAUDE_CONFIG_DIR="$1" \
          CLAUDE_PLUGIN_ROOT="$2" bash "$HOOK"; }
# Every line of global-instructions.md, not only its first.
has_rules() {
  local line
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    grep -qxF -e "$line" "$1" || return 1
  done < "$ROOT/global-instructions.md"
}

C="$TMP/none"; mkdir -p "$C"; ok=1
if run "$C" "$ROOT" > "$TMP/out1" && has_rules "$TMP/out1"; then ok=0; fi
report "no CLAUDE.md: prints every rule" $ok

C="$TMP/plain"; mkdir -p "$C"; printf '# Mine\n' > "$C/CLAUDE.md"; ok=1
if run "$C" "$ROOT" > "$TMP/out2" && has_rules "$TMP/out2"; then ok=0; fi
report "CLAUDE.md without the block: prints every rule" $ok

C="$TMP/block"; mkdir -p "$C"; ok=1
printf '# Mine\n\n<!-- agent-skills:begin - x -->\nrules\n<!-- agent-skills:end -->\n' > "$C/CLAUDE.md"
if run "$C" "$ROOT" > "$TMP/out3" && [ ! -s "$TMP/out3" ]; then ok=0; fi
report "CLAUDE.md carrying the block: prints nothing" $ok

# The block in another profile's CLAUDE.md must not silence this one.
mkdir -p "$TMP/home/.claude"; cp "$TMP/block/CLAUDE.md" "$TMP/home/.claude/CLAUDE.md"
C="$TMP/other"; mkdir -p "$C"; ok=1
if run "$C" "$ROOT" > "$TMP/out4" && has_rules "$TMP/out4"; then ok=0; fi
report "reads CLAUDE_CONFIG_DIR, not ~/.claude" $ok

ok=1
if run "$TMP/none" "$TMP/no-plugin-here" > "$TMP/out5"; [ $? -eq 0 ] && [ ! -s "$TMP/out5" ]; then ok=0; fi
report "missing rules file: exits 0 and prints nothing" $ok

ok=1
if python3 - "$ROOT/hooks/hooks.json" <<'PY'
import json, sys
h = json.load(open(sys.argv[1]))["hooks"]["SessionStart"]
cmds = [x["command"] for e in h for x in e["hooks"]]
assert any("hooks/session-instructions.sh" in c for c in cmds), cmds
PY
then ok=0; fi
report "hooks.json runs the hook script" $ok

echo
if [ $FAILED -eq 0 ]; then echo "ALL PASS ($PASS)"; exit 0; fi
echo "$FAILED FAILED, $PASS passed"; exit 1
