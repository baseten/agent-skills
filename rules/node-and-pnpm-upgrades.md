# Node and pnpm upgrades

This is the rule other skills mean when they cite *Node and pnpm upgrades*: how to
move a project to a new Node or pnpm version, and its Claude Code cloud
environment with it.

**It is not a skill and nobody invokes it.** It is a shared rule, held once at
`rules/node-and-pnpm-upgrades.md` and copied into each skill that applies it by
`scripts/refresh_shared_rules.sh`. Edit the source, never a copy. The reasoning is
in `rules/node-and-pnpm-upgrades-notes.md`.

## 1. Pick the targets from the source, never from memory

- **Node**: the current Active LTS line, from `https://nodejs.org/dist/index.json`:
  among the entries whose `lts` field is a name, the highest major, at its newest
  version. The file is ordered by date, so its first LTS entry can be an older
  line's patch. A `.nvmrc` comment saying "track
  Active LTS" means that line, not the newest patch of the old major.
- **pnpm**: `npm view pnpm dist-tags` (`latest`), and the Node compatibility table
  in `https://raw.githubusercontent.com/pnpm/pnpm.io/main/docs/installation.md`.
  pnpm.io itself may be blocked by a cloud environment's network.
- **Find what forces the move**: the `engines` of the project's dependencies. pnpm
  does not enforce `engines`, so CI can pass on a Node a dependency does not
  support.

## 2. Change the repository: one PR per tool, Node first

- **Node**: every `.nvmrc`, `engines`, `@types/node` and Docker image; and remove
  any Dependabot rule that ignores `@types/node` majors.
- **pnpm**: `package.json`'s `packageManager`; regenerate `pnpm-lock.yaml` with the
  new pnpm; adapt each setting the release notes rename or remove.
- **CI usually reads those files** (`setup-node` with `node-version-file`;
  `pnpm/action-setup` reading `packageManager`). Edit a workflow only where it pins
  a version itself.
- **A pnpm major rewrites the lockfile**, and pnpm refuses a newer-major lockfile
  in CI. Land it only when no other run has an open PR touching the lockfile, or
  each such PR is accepted to conflict.
- **Hosting**: confirm the build platform uses the new Node, in its first
  production build log, or set its Node version variable (Cloudflare Workers
  Builds: `NODE_VERSION`).

## 3. Install pnpm the supported way

- **Never use Corepack.** Node 25 and later do not ship it, and pnpm's CI docs say
  not to use it.
- **In a setup script or session hook**:
  `npm install -g "pnpm@$(node -p "require('./package.json').packageManager.split('@')[1].split('+')[0]")"`
  (Node 18 or later).
- **Alternatives**: from pnpm 12, the native executable from
  `https://get.pnpm.io/install.sh` (that host must be allowed); from pnpm 11.10,
  `pnpm self-update`, which inside a project pinning `packageManager` only updates
  the pin.
- **`packageManager` is the one source of truth**: pnpm switches to that version on
  first use.

## 4. The cloud environment's setup script

- **Keep the script in the repository**, at the path the repository already uses
  for it, else `scripts/cloud-setup.sh`, and store exactly that file in the
  environment, with no hand-pasted lines.
- **Read versions from the repository**: the script runs in the parent directory
  of the cloned repositories, after the clone, so it reads `<clone>/.nvmrc` for
  Node and `<clone>/package.json`'s `packageManager` for pnpm, running the §3
  install from inside the clone. A later bump then needs no environment change.
- **Never let it fail**: where no clone exists, it installs fallback versions
  written as constants in the script.
- **Have it write a marker**, such as `/etc/claude-cloud-env`, holding the
  versions it installed, so a session can confirm which script built it.
- **Remove variables that existed only for Corepack**, such as
  `COREPACK_ENABLE_DOWNLOAD_PROMPT`.

## 5. Roll out an environment change

1. Merge the repository change first.
2. In a session on that environment, run the new script as root from the
   checkout's parent directory. Confirm `node -v`, `pnpm -v` and the marker file
   (§4).
3. Propose the edit with `get_environment`, then `update_environment`. The owner
   approves the exact script. Only the current session's environment can be
   edited, so change each project's environment from a session on it.
4. It takes effect when a fresh container is built. Confirm it in the next new
   session.

## 6. Other projects' environments

- **An environment needs this only when its repository moves to Node 25 or later**,
  which has no bundled Corepack, or changes how pnpm is installed. Node 24 is
  still a supported LTS line.
- **A `COREPACK_ENABLE_DOWNLOAD_PROMPT` variable** is a sign the environment uses
  Corepack.
- **An API key stored as a plain environment variable** belongs in the
  environment's network secrets instead. Say so to the owner; moving it is theirs.
