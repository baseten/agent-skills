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

**Why the sentinel rule is scoped to positional and value comparisons (round 1,
Sept 2026).** Stated unconditionally it broke the legitimate case it most
resembles: `expect(items.indexOf(x)).toBe(-1)` is a test whose *subject* is the
absence, and demanding a presence assertion first contradicts the behaviour under
test. The defect is not the sentinel appearing in an assertion; it is the sentinel
being silently accepted as an answer to the comparison being made. That
distinction is still decidable by reading the test, which is the bar every entry
here has to clear.

**Why two of the four carry explicit carve-outs and two do not (round 1, Sept
2026).** The sentinel and sample-size entries each condemn, on a literal reading,
the legitimate test they most resemble — an assertion whose subject is the
absence, and one whose subject is the degenerate input. Both are exactly the right
test for their defect, and a worker optimising for a green suite reads a rule
literally. The premise and fixture entries have no such neighbour: an assertion
that would hold with the module deleted is never the right test, and a fixture
containing the thing the test says is absent is never deliberate. Carve-outs where
a false positive exists, none where it does not — a rule padded with unnecessary
exceptions is as unusable as one that over-reaches.

**Why the fixture entry stopped keying on the test's name.** It was written as
"a test whose name contains *no X* or *only Y*", which reaches the motivating case
only because that case happened to be called "Late stream, no workers". The same
defect in one called *stream-only path* passed the checklist untouched. The name
is a flag; the subject is the test.
