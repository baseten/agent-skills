# Notes — node-and-pnpm-upgrades

Reasoning for `rules/node-and-pnpm-upgrades.md`. Deliberately *not* bundled into
each skill: the audience is a person editing the rule, who has this checkout.

## Where it came from (owner's request, 2026-11-22)

Learned on one of the owner's projects from 2026-11-19 to 2026-11-22: Node
24.13.1 to 26.13.1, Corepack removed, pnpm 10 to 12 queued. It is a shared rule
rather than a skill because it is a procedure other work reaches, chiefly a
dependency upgrade, and a pointer in `global-instructions.md` reaches it from a
session that loaded no skill.

## 1. Pick the targets from the source

**Why the source:** a session's memory of "the current LTS" is stale by
construction. A `.nvmrc` that said to track Active LTS had been read as "the
newest patch of the old major". **Why `engines`:** jsdom 30 and later needed Node
24.15 or later, and Astro 7 a newer Node, and CI was green regardless because pnpm
does not enforce `engines`. **Why the raw docs URL:** pnpm.io was blocked by a
cloud environment's network; the GitHub raw file was not.

## 2. One PR per tool, Node first

**Why the lockfile warning:** a pnpm major rewrites `pnpm-lock.yaml`, and CI on
the old pnpm refuses it, so every open PR touching the lockfile conflicts or
fails once it lands. **Why hosting:** Cloudflare Workers Builds picks its own Node
unless told; only the first production build log shows which.

## 3. Never Corepack

Node 25 and later do not bundle it, and pnpm's CI documentation says: "Do not use
Corepack. It runs pnpm through a Node.js shim on every call." The `npm install -g`
line reads `packageManager`, so the version is pinned in one place.

## 4–5. The environment's setup script and its rollout

**Why read versions from the repository:** a script that hardcodes them needs an
environment edit at every bump, and an environment can be edited only from a
session on it. **Why identical to the repository's copy:** the stored script on
that project had a duplicated clone appended by hand, invisible from the
repository. **Why run it as root first:** the environment change takes effect
only in a fresh container, so a broken script is found a session late unless it
is run by hand before the edit is proposed.

## 6. Other environments

**Why only Node 25 and later:** Node 24 still ships Corepack and is a supported LTS
line, so an environment on it is not broken. **Why secrets:** found in passing; a
key in a plain variable is visible to anything that reads the environment.

## Review (2026-11-22, review-skill before the PR)

The Node target now names the highest LTS major, since `index.json` is ordered by
date and its first LTS entry can be an older line's backport. §4 gained the
script's location, the fallback and the marker, because "identical to the
repository's copy" had no referent for an agent without context. The §3 version
claims were checked against pnpm's installation docs on 2026-11-22: pnpm 12 is a
native executable, `self-update` needs pnpm 11.10, and in a project pinning
`packageManager` it updates only the pin. `get_environment` and
`update_environment` are the cloud environment tools as the owner used them; this
repository has no session on which to run them.

