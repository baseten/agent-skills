# CI attribution

This is the rule other skills mean when they cite *CI attribution*: whether a red check on a PR is that PR's failure, and what confirms that it is not.

**It is not a skill and nobody invokes it.** It is a shared rule, held once at
`rules/ci-attribution.md` and copied into each skill that applies it by
`scripts/refresh_shared_rules.sh`. A skill reads its own
`references/ci-attribution.md`, which works after `bootstrap.sh` has
installed only that skill's directory, and travels with the skill if it is
moved into a plugin. Edit the source, never a copy; check_shared_rules.py fails if a generated copy diverges.

It binds both the layer that supervises a PR and decides whether to dispatch a repair, and the repair pass that decides whether to change code. What each then does with the answer — dispatch, repair, report, restack — is that skill's own.

## Classify per check, not per PR

A PR can be red for its own reason and someone else's at once, so each red check is attributed on its own. Four answers:

- **this PR's** — the default, and the answer wherever nothing below is confirmed;
- **the environment's** — a shared backing service, a build service, a runner, a harness (*The environment hypothesis*);
- **expected-red after a producer merge** (*A producer merge*);
- **flaky, or pre-existing and unrelated** — neither has an environment hypothesis to confirm, and neither needs one.

**A failure attributed anywhere but this PR, with no justified code change, consumes no repair cycle.**

## The environment hypothesis

**Where the failure is a mass one across files with nothing in common, test the environment before the code**: a shared backing service can die mid-session, and the result reads exactly like this branch breaking everything. The tell is in the error rather than the assertion — a refused connection, a missing socket, an absent container, a builder timeout, an image-build transport error, a browser-harness teardown message.

**That signature raises the hypothesis and does not settle it**, because the PR can produce it: a change to connection configuration or client setup refuses connections across every unrelated test file in the suite, with the same error and the same breadth. Confirm it independently — the service's own health, or **whether unrelated branches and the default branch fail the same job**. Where the diff touches the very thing the error names, the hypothesis points back at this PR and the confirmation is what tells the two apart.

- **An *unconfirmed* environment hypothesis is not an attribution.** Treat the check as this PR's. A supervising layer dispatches the repair pass rather than classifying the failure itself — the pass has the diff in front of it and is the cheaper place to be wrong — and a repair pass does not take its change-nothing branch on an unconfirmed hypothesis alone.
- **Where the failure is repository-wide** — the default branch and unrelated branches fail the same job — re-running is futile, and escalating to whoever owns the service is the useful action. Report it; do not iterate on it.

## A producer merge

**A merge in one repository can turn open PRs in another red, and that red is not those PRs' failure.** Where one repository's build consumes an artifact generated from another — an API schema regenerated from the producer's default branch and diffed in the consumer's CI — merging a producer PR changes that artifact, and every open consumer PR fails that check, the consumer's default branch with it.

**The confirmation is the consumer's default branch failing the same check.** A confirmed check is **expected-red** pending the refresh the consumer's tooling produces. It stops being expected-red, and belongs to the PR, where:

- the PR's own diff touches the artifact the check regenerates — then it was the PR's from the start;
- the check is still red once the refresh has landed and the PR has been brought onto it.

Every other red check on those PRs is attributed as usual.

## A narrowing signature

**Read a changed failure signature rather than retrying it.** A signature that narrows after a fix — every view blank, then a subset of shards failing one lookup — indicates one defect with several sites, one of them now corrected: not a failed fix. Read the new signature to locate the next site; reverting or retrying discards the evidence.
