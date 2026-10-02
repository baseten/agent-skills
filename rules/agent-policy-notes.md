# Notes — agent-policy

Reasoning for `rules/agent-policy.md`. Deliberately *not* bundled into
each skill: a copy of this per consumer would be design history with no reader,
and the audience for it is a person editing the rule, who has this checkout.

Moved here with the rule itself, from `backlog-orchestrator/NOTES.md`, where it
was reasoning about a section that no longer lives there.

**Why a config file and not prose or a skill override:** a `CLAUDE.md` paragraph gets interpreted, and interpretation must not decide whether a run may merge. A project-level skill override is not the mechanism either: `bootstrap.sh` installs these skills to `~/.claude/skills`, and a personal skill shadows a project skill of the same name, so a project copy would silently never load.

**Why there is no reviewer-identity option:** an `auto-fix-reviewers` key used to gate auto-fixing on the comment's author — a boolean, or a list of vetted bot logins tested against the forge's author type. It was removed rather than re-defaulted. Author identity is a poor proxy for the only thing that matters, which is whether the comment asks for a code change: automated reviewers routinely raise design questions no run should answer, and human reviewers routinely file one-line nits any run can fix. The key therefore erred in both directions at once, and no default fixed that — a permissive default auto-answered humans' design questions, a restrictive one reserved trivial fixes and stalled unattended runs. The kind test the repair path already applied was doing the real work the whole time; the key was a second gate in front of it that agreed with it only by accident. Removing it also collapsed a fail-closed special case: it was the one key whose built-in default was its permissive end, so a corrupt policy file had to resolve it *against* its default to avoid granting more than a parsed file would.

**Why `auto-merge` is one grant rather than per-consumer keys:** splitting the key per consumer would gate which skill happened to open the PR, which is not a security property, and would leave the real boundary — the gate — unchanged.

**Why the off-only keys are listed only in *Precedence* (second blind audit of #175):** `implement-issue` restated the rule as "(`auto-merge`: off only)". When `auto-resolve-comments` became off-only too, that copy let an invocation turn the new key on, and the `true` flowed down to a skill that trusted its caller. Every other site now cites *Precedence*, and `resolve-pr-comment` trusts a `true` only when its source is the repository's file.

**Why `minimize-ci-runs` is not a waiver, and why only the file turns it on (#179; blind audit of #181):** it subtracts no condition from the gate. CI green on the current head and a clean review are still required, and the overlap narrowing of the stale-green re-check is written into `settle-and-merge` itself, so the gate keeps one definition. It was first given ordinary precedence on the reasoning that its permissive end is not a merge. The audit found that reasoning too narrow: `true` still loosens a check inside the merge gate, so an invocation able to turn it on could loosen the gate of a repository whose owner never opted in — the shape `auto-merge` and `auto-resolve-comments` are off-only for. An invocation can still turn it off.
