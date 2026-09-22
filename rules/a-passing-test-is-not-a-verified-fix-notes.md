# Notes — a passing test is not a verified fix

Reasoning for `rules/a-passing-test-is-not-a-verified-fix.md`. Explains; never
overrides.

**Why a checklist rather than the general instruction.** The general instruction
already existed — reproduce the failure on the unfixed code before accepting the
fix — and three of the four defeats passed it trivially, because the fix and the
test were written in the same pass. A rule that names the check without naming
what defeats it can only be followed by someone who already knows what to look
for. Four in one tranche is not bad luck; it is what that gap produces.

**Why these four and not a longer list.** Each is decidable by reading the test
alone, without running anything and without knowing the domain: does a lookup
here have a not-found sentinel, does the sample have enough elements to
discriminate, would this assertion hold with the module deleted, does the fixture
contain the thing the name says is absent. A defeat that needed judgement about
the subject would not survive being applied by a worker optimising for a green
suite, which is the reader this is written for.

**Why the time rule is stated with the four rather than beside them.** It is the
same failure wearing a different face: an assertion that appears to be about the
behaviour and is actually about the measurement apparatus. It also defeats the
same fallback — the unfixed code passes it most of the time — so a reader who has
just been told that running it again is not the method needs the case where
running it 400 times is.
