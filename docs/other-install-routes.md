# Other install routes

The plugin is the way to install these skills: enable it on claude.ai, or install it
from the CLI (README, *Install as a plugin*). This page covers the routes that predate it,
and the one thing only `bootstrap.sh` still provides: a second GitHub MCP server for
reading cross-repository issue dependencies in a cloud session.

## What a cloud session can and cannot see

A cloud session — Claude Code on the web, a Desktop cloud container, an auto-fix
run — loads skills from exactly two places:

- the skills and plugins enabled for your **claude.ai account**, and
- the **cloned repository's** own `.claude/skills/`. A marketplace its
  `.claude/settings.json` declares is not added in an Anthropic-hosted cloud
  session, so a plugin from one does not load there.

It does **not** read `~/.claude/skills` from the machine you started it from.
Whatever you have installed locally is not there, and the failure is silent: the
session simply behaves as though the skill was never written.

So there are three ways to get these skills into one: the plugin enabled on
your claude.ai account, which is the recommended route and needs nothing in the
environment, or a setup script that installs them on disk, either as copies or
as the plugin.

## Install from a setup script

Put this in the **Setup script** field of your [cloud
environment](https://code.claude.com/docs/en/cloud-environments) — on claude.ai,
Settings > Cloud environments, then the environment you use:

```bash
git clone --depth 1 https://github.com/baseten/agent-skills.git /tmp/agent-skills
bash /tmp/agent-skills/bootstrap.sh
rm -rf /tmp/agent-skills
```

That field runs **before Claude Code launches**, which is what makes this work:
the skills are on disk before anything looks for them. Removing the clone
afterwards leaves the installed copy under `~/.claude/skills` as the only one in
the container, so nothing can read a second copy from `/tmp`.

`bootstrap.sh` discovers every directory under `skills/` containing a
`SKILL.md`, so the install list never drifts from the repository. It writes no
permission rules: the README's *Permissions* says why, and points to the way back if a worker
stalls on a prompt for a Claude Code Remote tool.

To see which revision a container is running, `cat ~/.claude/.agent-skills-install`
(on the plugin route, the `.source` beside any skill under the plugin's
directory, `plugins/synced/` for a plugin claude.ai syncs and `plugins/cache/`
for one the CLI installed):
it records the repository, the commit and its date, and when the install ran.
Each installed skill carries the same record as `.source`, which matters because
installing merges and never deletes: a skill whose `.source` differs from
`~/.claude/.agent-skills-install` is left over from an earlier install and can
be deleted. One with no `.source` came from an install older than the stamp or
from somewhere else entirely, which this script cannot tell apart, so check it
before deleting it. Whatever the install cannot read - no
`.git`, no recognisable origin - is recorded as `unknown` rather than guessed.

A session reads the stamp itself: every skill that starts a run opens its first
output with `running <skill> @ <commit> (<date>)`, from its own `.source` (or, for
an uploaded skill, its frontmatter's `metadata.version`), and `unknown` where
neither reads (`rules/run-start.md`). A coordinated run carries that line in each
report to its conductor, which records it in its ledger, so an audit can tell
which revision every session ran.

This is verified at the **Trusted** [network access
level](https://code.claude.com/docs/en/cloud-environments#access-levels), which
is the default. A more restrictive level may not permit the clone.

`bootstrap.sh` deletes nothing. It merges each skill over whatever is installed
and **reports** a skill this repository has retired rather than removing it,
because nothing in a script can tell its own stale copy from one you wrote
yourself under the same name.

The one thing it replaces is its own marked block in `~/.claude/CLAUDE.md`,
which carries `global-instructions.md`: rules a session needs before any skill
is loaded, such as linking every issue a chat reply names, preferring a
skill that extends another over the one it extends, and what may be written
without the user's approval, in a review thread or as a draft. The
markers make that block provably its own, so a re-run swaps it in place and
leaves the rest of the file alone.

## Why this repository is public

Because a setup script cannot reach a private one. The cloud GitHub proxy scopes
access to the repositories **attached to the session**, so a script cloning an
unattached private repository gets a 403. A session attaches the repository you
are working in, which is never this one.

That constraint is the whole reason for the split described in [Personal skills
stay out](../README.md#personal-skills-stay-out): a public repository is the only kind a
setup script can install, and anything that cannot be public has to reach cloud
sessions through a claude.ai account instead, today as a plugin from a private
marketplace.

## Reading issue dependencies and Projects v2

A cloud session's built-in GitHub MCP server arrives with no feature flags and a
restricted toolset list, so two things are missing from it — for unrelated
reasons, which is why each is switched back on differently:

| missing | why | how it is asked for |
| --- | --- | --- |
| `issue_dependency_read` / `_write` (native blocked-by/blocking) | behind the `issue_dependencies` **feature flag** | `?features=` on the URL |
| Projects v2 | `projects` is not one of the default **toolsets** (`context`, `issues`, `pull_requests`, `repos`, `users`) | `X-MCP-Toolsets` |

`bootstrap.sh` can install a second GitHub MCP server that has both. It is
**off by default** — set `AGENT_SKILLS_GH_MCP=1` — because a server configured
without a working credential fails to connect on every session start, and it is
unnecessary locally where an authenticated `gh` already reads cross-repo edges.

A second server is the only route. The built-in one's URL and headers are fixed
before the session starts, and a `.mcp.json` committed to the repository cannot
help either: a cloned repository is an untrusted folder, so
`enableAllProjectMcpServers` in it is ignored and the server sits at *Pending
approval* with nobody able to approve it. User scope written by the setup
script is what works, for the same reason the skills themselves are installed
that way — see [Install from a setup script](#install-from-a-setup-script).

### Why `curl` is not enough

The dependency REST endpoints do answer from a cloud session. But they answer
through the same GitHub proxy described in [Why this repository is
public](#why-this-repository-is-public), which scopes access to the
repositories attached to the session — and here that scoping is **silent**.
Asking for an unattached repository directly gives the familiar 403; asking for
it *inside another repository's response body* gives `200` and an empty array:

```
GET /repos/OWNER/ATTACHED/issues/192/dependencies/blocked_by   → 200, same-repo edge
GET /repos/OWNER/ATTACHED/issues/192/dependencies/blocking     → 200, []
GET /repos/OWNER/UNATTACHED/issues/106                         → 403, "use add_repo"
```

An empty `200` is indistinguishable from "no dependencies", so a graph read this
way cannot report its own incompleteness. A PAT does not widen it — the proxy's
scope applies regardless of the credentials supplied — and neither does running
`github-mcp-server` inside the container, whose calls exit the same way.
Projects v2 is GraphQL-only and unreachable through the proxy at all.
`api.githubcopilot.com` sidesteps this by making its GitHub calls server-side,
resolving visibility from its own token rather than the session's repository
set.

### Configuring it

| Variable | Default | Meaning |
| --- | --- | --- |
| `AGENT_SKILLS_GH_MCP` | `0` | `1` installs the server |
| `AGENT_SKILLS_GH_MCP_AUTH` | `proxy` | `proxy` or `pat` |
| `AGENT_SKILLS_GH_MCP_URL` | `…/mcp/?features=issue_dependencies` | feature flags |
| `AGENT_SKILLS_GH_MCP_TOOLSETS` | `projects` | `X-MCP-Toolsets` — replaces the defaults |
| `AGENT_SKILLS_GH_MCP_TOOLS` | `issue_dependency_read,issue_dependency_write` | `X-MCP-Tools` — named individually |

**`proxy` (preferred).** Add an **API credential** to the cloud environment:
type Bearer, allowed website `api.githubcopilot.com`, header `Authorization`,
prefix `Bearer`, value a PAT. The agent proxy attaches it after the request
leaves the VM, so the token never enters the container, and credential hosts
bypass the network allowlist. Needs an org admin role.

**`pat`.** Set `GITHUB_MCP_PAT` as an environment variable. No admin role, but
the token is readable by the session and everything it runs. Only the
unexpanded `${GITHUB_MCP_PAT}` is written to `~/.claude.json`; Claude Code
expands it at load time, so the secret lands in no file either way.

Use a **fine-grained PAT scoped to every repository whose issues take part in a
dependency edge** — that repository list is exactly what decides cross-repo
visibility, and it is the whole reason this reads what the proxy cannot. Issues:
Read (Read & write for `issue_dependency_write`), Projects: Read or Read &
write. Organization-owned projects need the *organization* Projects permission,
and an org may require approval for fine-grained PATs.

### Finding the tools, and keeping the two servers apart

The tools arrive under the server segment —
`mcp__github-deps__issue_dependency_read`, `mcp__github-deps__projects_list` —
not the bare names the upstream documentation uses. Two consequences, both
already handled:

- A permission rule you write for them names that full prefix, because rule
  matching is on the literal tool name. This is why the server name is **not**
  configurable: a renamed server would silently stop matching such a rule.
- Under tool search a model sees names first and loads schemas on demand, so one
  that does not know this server exists will not stumble onto it.
  `validate-backlog` therefore names the prefixed tool in its transport table
  rather than describing the capability abstractly.

Keep the second server **additive**. At these defaults the two surfaces do not
overlap — only this one offers `issue_dependency_read` and `projects_*`, only
the built-in offers `issue_read` and the rest — so nothing has to arbitrate
between them. Setting `X-MCP-Toolsets` at all replaces the defaults, which is
what prevents a duplicate GitHub surface. Widening it to include `issues` would
give two servers both offering `issue_read`, with the PAT's scope silently
differing from the session's.

## Verifying the install landed

`/plugin` is unavailable in a cloud session, so check from
the shell:

```bash
ls ~/.claude/skills
```

Every directory under `skills/` here should appear. On the plugin route they
are under the plugin's directory instead (`~/.claude/plugins/synced/` for a
plugin claude.ai syncs, `~/.claude/plugins/cache/baseten/agent-skills/` for one
the CLI installed), with `~/.claude/skills` holding none of them. If the list is empty the
setup script did not run or the clone failed; if it is short, compare it against
this repository rather than assuming a skill was retired — `bootstrap.sh`
deletes nothing.

The orchestration skills are environment-agnostic and work identically from a
local Claude Code setup.

## Local Codex usage

Codex reads a subset of the skills via symlinks in `~/.codex/skills/`. Point
`REPO` at your checkout of this repository:

```bash
REPO=$HOME/src/agent-skills
bash "$REPO/scripts/refresh_shared_rules.sh"   # references/ is generated, not committed
for s in create-pr resolve-pr-comment implement-issue; do
  ln -sfn "$REPO/skills/$s" "$HOME/.codex/skills/$s"
done
```

Personal writing skills are not in this repository — see [Personal skills stay
out](../README.md#personal-skills-stay-out).
