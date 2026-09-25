# Notes — agent-policy

Reasoning for `rules/agent-policy.md`. Deliberately *not* bundled into
each skill: a copy of this per consumer would be design history with no reader,
and the audience for it is a person editing the rule, who has this checkout.

Moved here with the rule itself, from `backlog-orchestrator/NOTES.md`, where it
was reasoning about a section that no longer lives there.

**Why a config file and not prose or a skill override:** a `CLAUDE.md` paragraph gets interpreted, and interpretation must not decide whether a run may merge. A project-level skill override is not the mechanism either: `bootstrap.sh` installs these skills to `~/.claude/skills`, and a personal skill shadows a project skill of the same name, so a project copy would silently never load.

**Why there is no reviewer-identity option:** an `auto-fix-reviewers` key used to gate auto-fixing on the comment's author — a boolean, or a list of vetted bot logins tested against the forge's author type. It was removed rather than re-defaulted. Author identity is a poor proxy for the only thing that matters, which is whether the comment asks for a code change: automated reviewers routinely raise design questions no run should answer, and human reviewers routinely file one-line nits any run can fix. The key therefore erred in both directions at once, and no default fixed that — a permissive default auto-answered humans' design questions, a restrictive one reserved trivial fixes and stalled unattended runs. The kind test the repair path already applied was doing the real work the whole time; the key was a second gate in front of it that agreed with it only by accident. Removing it also collapsed a fail-closed special case: it was the one key whose built-in default was its permissive end, so a corrupt policy file had to resolve it *against* its default to avoid granting more than a parsed file would.

**Why `auto-merge` is one grant rather than per-consumer keys:** splitting the key per consumer would gate which skill happened to open the PR, which is not a security property, and would leave the real boundary — the gate — unchanged.
