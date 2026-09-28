# Review trigger

This is the rule other skills mean when they cite *review trigger*: which convention a PR's automated review trigger follows, what it is and from which account, and when review is triggered again.

**It is not a skill and nobody invokes it.** It is a shared rule, held once at
`rules/review-trigger.md` and copied into each skill that applies it by
`scripts/refresh_shared_rules.sh`. A skill reads its own
`references/review-trigger.md`, which works after `bootstrap.sh` has
installed only that skill's directory, and travels with the skill if it is
moved into a plugin. Edit the source, never a copy; check_shared_rules.py fails if a generated copy diverges.

It governs every trigger a skill issues — the first one after a PR is created, a re-trigger after a repair, and a trigger on a PR the run never created, such as a bot's. **Which of those a skill issues, and when, is that skill's own**; this rule says what each one is.

## The convention

Use the trigger the repository documents in its own `CLAUDE.md`/`AGENTS.md`; with none, default to `@codex review` where that convention is supported.

## Documentation-review routing

- **Where the repository documents a documentation-review convention and the PR's diff qualifies, that convention is the trigger** — that convention is the `review-docs` skill, **invoked on the PR rather than posted as a comment**, so confirmation that the trigger took effect is its completed pass and the review comment it posts, not a reviewer arriving. On a **documentation-only** diff it runs *instead of* the ordinary review trigger; on a **mixed** diff, only where the repository documented the mixed case as well, and then *in addition to* the ordinary trigger, which is still issued in full. `review-docs` owns the documentation test, its rounds, and what it reports — do not restate them here. Cannot tell whether a path is documentation → it is not, and the ordinary trigger stands alone.
  - **This governs re-triggers as much as the first trigger**: a routed convention is **re-invoked, not re-posted**, so there is no trigger comment and **no trigger author to select from the posting-identity map** — the selection step a re-triggering skill performs has nothing to select and is not skipped by oversight. `review-docs` bounds its own rounds and declines past them; **a decline is that convention's completed answer to a re-trigger**, not a trigger that failed.
  - **Skill unavailable → the ordinary trigger stands alone, and report that it did.** Same fail-safe direction as the cannot-tell rule above: a PR reviewed by the wrong instrument costs a reading, a PR reviewed by nothing costs the review.

## The trigger comment

**The trigger comment must come from the invoking user's own account, or the convention does not fire, and it carries the trigger text and nothing else — no attribution footer.** Both are exemptions from rules that govern every other authored write, and each is stated once where it lives: the authorship exception, with how the trigger's author is selected, in `references/posting-identity.md`, *The review trigger*; the footer exemption, with the reason to state for it, in `references/authored-write-form.md`. Apply them from there; do not restate them. **Both exemptions reach the trigger comment alone**: every other authored write the triggering skill makes follows both rules as written.

## Re-triggers

- **Do not re-trigger merely because subsequent CI checks run.**
- **Re-trigger after a substantive review-fix round only where repository convention requires it, and never after a mechanical push.** `references/mechanical-pushes.md` is the test for which is which; apply it from there.
