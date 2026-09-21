# Notes — absence is not a verdict

Reasoning for `rules/absence-is-not-a-verdict.md`. Explains; never overrides.

**Why this is a rule and not six fixes.** It arrived as six separate findings
across three agents and two repositories, each filed as a local defect in the
thing that misread its own query. Patched individually they are six unrelated
one-line corrections. Held together they are one assumption — *the query answered,
so the answer is about the world* — which is the case `CLAUDE.md`'s **shape**
classification exists for. The instances have no common API, no common skill and
no common transport, which is exactly why nobody noticed they were one defect:
there is no file where they would have collided.

**Why it is dangerous rather than merely wrong.** Every instance failed in the
flattering direction. An empty review endpoint reads as *clean*, an ungraded
scenario as *passed*, a silent poll as *nothing happened*, a failed probe as *no
trigger fired*. Not one of them produced a red result that someone then had to
explain away — they produced green results nobody had reason to examine. Five of
the six survived at least one full run, and the trigger-eval instance survived
five iterations that scored identically because the variable under test was never
reaching the model at all.

**Why "name the lookup, not the world" is the operative sentence.** The other
formulations are corollaries of it, and it is the one that transfers to cases
nobody has hit yet. *"I did not find a review at `<endpoint>`"* and *"no review
ran"* differ by exactly the inference this rule forbids, and the first costs
nothing to say. The reporting half matters as much as the checking half: the
review-outage instance cost five days on an unactioned P1, and the check itself
was never wrong — only the sentence written about it.

**Why either/or is called out specifically.** The merge-gate instance went
through three revisions (`14` → `33` → `38` in the field reports) because each
assumed the two endpoints were summary-and-detail, so an empty one meant *nothing
to report*. They are neither: a clean review creates no review object and no
threads, so the thread endpoint is empty exactly when the summary carries the
answer. A prohibition written without its reason — *never establish a clean
review from `get_comments`* — then misfired in the opposite direction, which is
why the rule says a forbidden source must say **for what**.

**Why the guard clause at the end exists.** Writing this rule broke the check
that reads the generator, and the guard that fired was one added a week earlier
for precisely this: the check noticing it had stopped being able to see anything,
rather than reporting success over an empty set. A check whose inputs go missing
reads absence as *nothing wrong*, so it is the one place this rule has already
been implemented and is worth pointing at.
