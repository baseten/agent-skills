# backlog-orchestrator — integration-branch mode

Part of `backlog-orchestrator`'s contract, read wherever an in-scope repository's `ci-mode` resolved `integration-branch`: at the first preflight, before dispatching into that repository, at a merge into the branch, at settle, and on a restart. `SKILL.md` points here from *Mandatory validation preflight*, *DAG and PR topology*, *Completion semantics* and *Settled wave*, and `restart-resume.md` from step 6. Its rules assume `SKILL.md` has been read. The reasoning is in `NOTES.md`, under *Integration-branch mode*.

## What the mode does

**Per repository, this run's issue PRs target the integration branch — the `integration-branch` key's name — instead of the default branch, run no CI, and are gated on a local gate.** They merge into that branch through invariant 12's gate on the mode's own grant (`references/agent-policy.md`, *Merge permissions*). Then **one integration PR** from the branch into the default branch runs CI once, as the backstop, and merges only under `auto-merge`; otherwise it is the owner's to merge. `supervise-prs`, *Integration-branch CI*, owns what happens on each PR. **Nothing in this run dispatches or re-runs a workflow** in such a repository — a dispatch on a branch cut from the integration branch would test its whole difference from the default branch, close to a full run. **Deploys that run on a push to the default branch move to the integration PR's merge**: the CI-cost audit names each such workflow, and opting into the mode is the owner accepting that delay.

## Establishing it

At the first preflight, before any dispatch into the repository, establish each of these from the default branch's head (`references/establish-do-not-assume.md`) and record them per repository:

1. **the token preconditions** `supervise-prs`, *Deferred CI*, names — a squash or merge-commit merge allowed, a review trigger that is not an Actions workflow on `pull_request` events, and a forge that honours `[skip ci]`, observed on the first tokened push;
2. **no workflow's `push` trigger matches the integration branch** — every merge into it would otherwise start a run;
3. **the integration branch's protection, where it has any, requires no check only CI produces and no PR for a push** — the forge would refuse every merge into it, a required check expected on a ticket PR's head is what a supervisor reads as owed CI, and the run pushes its level merges directly;
4. **the repository allows a merge-commit merge**, which the integration PR takes: a squash would leave the branch's head outside the default branch, so the branch would never read level again (*The branch*);
5. **a session can run the per-PR tier** (*The gate, in two tiers*);
6. **the integration branch is not the default branch** — that is a fail-closed `per-pr` (`references/agent-policy.md`, *Fail-closed handling*).

**Any missing → hold dispatch into that repository** with a `NEEDS_USER` carrying the CI-cost audit's proposal (`SKILL.md`, *Mandatory validation preflight*): the exact diff — `push: branches: [<default>]`, say — and the instruction to land it with `[skip ci]` in its message, so the fix costs no run. The options: dispatch once the fix lands, or dispatch under `per-pr` for this run. Only an owner reply choosing one releases it (`SKILL.md`, *Arming the wait when nothing is in flight*). The run never edits a workflow (`implement-issue-core`, *Hard constraints*).

## The branch

**Create it from the default branch's current head where it does not exist; where it does, adopt it as it stands** — it may carry merged work an earlier run left — and bring it level with the default branch by a merge, carrying no token; a conflict is `NEEDS_USER`. **The branch is level when the default branch contains its head**; **its batch** is the merges into it since it was last level. A branch whose integration PR merged without containing it — a squash — is `NEEDS_USER` for the owner to recreate it. Creating it and merging into it are on the invocation's authority, as per-issue branches are (`SKILL.md`, *Session branch mandates*). **Never reset, force-push or delete it**: it holds merged work no other ref may.

**A PR into it that this run did not create** — another run's, the owner's — is not this run's to merge, and still rides in the integration PR; that PR's body names it.

**While an integration PR is open, the branch is frozen**: nothing merges into it and no level merge is made, so its one CI run is never restarted by a `pull_request` event. A PR into the branch that passes its gate meanwhile waits, reported as `waiting for the integration PR`, and merges at the first settle after that PR merges or closes; its dependents wait with it. The only pushes to the branch then are repairs to the integration PR, each carrying the token (`supervise-prs`, *Integration-branch CI*). Merges into the branch at any other time carry no token (`merge-stack`), and start no run by precondition 2.

## Topology

**Every issue whose PR would target the default branch targets the integration branch instead**; a stacked PR keeps its parent as base (`SKILL.md`, *DAG and PR topology*): `integration -> A -> B`. **An adopted open PR in scope that targets the default branch is retargeted** to the integration branch at adoption, and reported. Work that must reach the default branch alone — a hotfix — is not this run's: `implement-issue` applies `per-pr` to it.

## The gate, in two tiers

**Derive the gate once per repository** as the pre-PR gate is derived (`SKILL.md`, *Implementation worker contract*) — from the default branch's required checks, since those are what the integration PR must pass — with the toolchain the repository declares, **and split it**:

- **the per-PR tier** — format, lint, typecheck, and the unit and component suites of the packages a change touches, selected by the repository's own change-set tooling (the script or path rules its CI selects jobs with) where it has one, otherwise by its workspace dependency graph. It goes in every dispatch prompt into the repository as the pre-PR gate, and to `supervise-prs` as each PR's local gate;
- **the full tier** — everything, end-to-end and conformance suites included — run on the integration branch only, at its checkpoints: before the integration PR opens (*The integration PR*), and after any group of merges an invocation names.

**Establish once, at preflight, that a session can run the per-PR tier**, by running it on the default branch's head — which is also the baseline `SKILL.md`, *Mandatory validation preflight*, measures per base. A check that cannot run there — a database, browser or emulator the session lacks — is `not locally runnable` for the run: listed per repository in the state block with what is missing, with the suggestion of a session-start hook that provides it, and owed by the integration PR's CI. **An unrun check never passes**: it is carried in every record as `not locally runnable`, never dropped (`references/ci-and-review-verdicts.md`, *CI is green*). A per-PR tier no session can run at all leaves the mode without effect — the hold under *Establishing it*.

A full-tier failure at a checkpoint is bisected over the batch, first-parent — from the last passing full run where the run recorded one, otherwise the whole batch — to the first merge whose tree fails, and raised as a `NEEDS_USER` naming the failing checks and that merge's PR, with options: dispatch a fix — an issue filed under the manifest, dispatched into the branch within `new-issue-budget` — or open the integration PR anyway, or leave it to the owner. Only an owner reply choosing one releases it. An environment failure is not a gate failure (`references/ci-attribution.md`, *The environment hypothesis*): a container too slow or on the wrong toolchain runs the tier in a remote session instead.

## Merges and completion

**A merge into the integration branch is a frontier-advancing event** (`SKILL.md`, *Frontier advance on merge*) for its same-repository dependents, which become READY with the integration branch as their base; pass that edge to `validate-backlog` as satisfied caller context. **A cross-repository dependent still waits for the integration PR to merge**: nothing it can build on exists on the other repository's default branch. **It is not completion**: the issue is `MERGED_TO_INTEGRATION` (`SKILL.md`, *Durable remote state and restart*) — never redispatched, never `DONE` — until the integration PR carrying it merges. A GitHub closing keyword closes nothing outside the default branch; Linear automation that marks an issue done on a merge into any branch does not make it `DONE` either (*Completion semantics* there: closing state is evidence, not definition). A restart reads the batch from the branch's first-parent history.

## The integration PR

When the run settles with every one of its PRs into the integration branch merged, surfaced or waiting for the integration PR, a non-empty batch, and **no integration PR from the branch open**:

1. bring the branch level with the default branch, as under *The branch*;
2. run the full tier on its head, as above; a failure stops here;
3. **open the integration PR through `create-pr`** (*The integration PR* there): base the default branch, head the integration branch, **on a head carrying no token** — the step-1 merge commit, or the last merge into the branch, whose messages carry none (`merge-stack`) — so its opening starts its one CI run, with the full tier's result as its gate. The review trigger is issued as for any PR;
4. adopt it into `supervise-prs` with `ci-mode: integration-branch` and, for `review-defer-severity`, the manifest's root issue as its follow-up site. It is one of this run's PRs: open, it un-settles the run, and at the next settle the gate evaluates it under `auto-merge` alone, merging it with a merge commit. Without `auto-merge`, the closing report names it as the owner's merge to make, by merge commit.

**Closed unmerged, it is not reopened**: a `NEEDS_USER` names the batch, and no integration PR opens again until an owner reply chooses to.

## Restart

`restart-resume.md` classifies the batch's issues `MERGED_TO_INTEGRATION` at step 5, before any branch adoption; step 6 adopts the branch as it stands, every open PR into it, and the integration PR where one is open. Where the batch is non-empty and no integration PR is open, *The integration PR* runs at the next settle.
