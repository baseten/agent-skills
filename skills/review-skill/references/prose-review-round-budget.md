# Prose review terminates on a budget, not on a verdict

**A reviewer of prose has no oracle, so it needs a ceiling fixed in advance.**
Code review terminates because it borrows one it does not own — a test passes, a
compiler accepts, and the round ends whether or not anyone is satisfied. Prose
has nothing equivalent. *"Is there anything left to say"* is a question whose
answer is always yes, so it cannot be the stopping rule, and a reviewer using it
grinds until a person intervenes. Observed: one document took nine rounds and 28
threads, and was not materially better after round four.

The word **prose** is doing work here. This budget is wrong for a CI repair loop,
where a failing check is a real terminator and stopping early ships a defect.

## The budget

**Round 1** is the full pass.

**Round 2** reads only round 1's findings and says of each: *fixed*, *not fixed*,
or *fixed wrongly*. It raises no new findings about text round 1 already read —
re-reading a rewritten section is a fresh unbounded reading, which is the loop
this exists to break, and a section that improved in a way nobody asked about is
not an occasion to say so.

**Two things round 2 may still raise**, and both are the same case — a fix that
created the failure the reviewer exists for:

- a fix that introduces a new instance of that failure class. Reported *inside*
  the finding whose fix created it, never as a finding of its own, and it earns
  no additional round.
- material the author **added** since round 1, where the reviewer's report
  certifies a revision marker. Certifying prose nobody read is that same failure
  arriving through the marker meant to prevent it. Check the delta only — never a
  re-pass — or **decline to certify**: report the outcomes, omit the marker, and
  say the additions were not reviewed. A missing marker leaves a consumer's gate
  shut, which is the safe direction; a present one over unread prose opens it.

**There is no round 3.** What is unresolved after round 2 is named and handed to
the author with its evidence and the statement that the review is over. A caller
invoking a third time gets a **declined pass naming the residue** — the decline
is the deliverable, not an error, and it posts nothing. A decline is a completed
outcome, not a pass that failed to happen.

## What makes the budget hold

**Count the round off the pull request, never off run state.** No prior comment
from this reviewer → round 1; exactly one → round 2; two → declined. A restarted
session, a different worker and a person invoking by hand all count the same,
because the count lives where the comments do. A count held in a session is one a
fresh session launders.

**The budget is per pull request.** Work that returns as a new PR gets its own two
rounds: a new PR is a new decision to review.

**It is a contract rule and deliberately not configurable.** A ceiling is not a
decision, and the run that has spent nine rounds is exactly the run that would
raise the limit.

**One comment per round. Never a thread per finding.** Twenty-eight threads was
not twenty-eight problems; it was one reviewer with no stopping rule, and the
thread count is what made an unbounded review look like diligence.

**Phrasing, ordering and terminology are not findings at any round.** A reviewer
that reports them has stopped distinguishing a defect from a preference, and
every one of them costs a round.
