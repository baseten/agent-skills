# repair-pr — design notes

Companion to `SKILL.md`. That file is the contract; this one holds the reasoning, keyed by section. Read a section's note before changing its rules or when applying them to a case the contract doesn't obviously cover. Nothing here overrides the contract.

## Hard constraints

**Why waiting is neither performed nor delegated:** the caller is already supervising this PR, and a wake armed here (a scheduled check-in, trigger, or PR-activity subscription) outlives the repair pass that armed it — a second watcher duplicates supervision the caller owns and can act on a PR the caller is mid-repair on, and a worker often lacks permission to disarm what it armed.

**Why the every-reader scope reaches every repair type (Sept 2026):** the rule lives in `resolve-pr-comment` because that is the pass that writes a review fix and its reply — stated only here, it bound the caller while the callee's own "minimal change, nothing not mentioned" did the work. It reaches `ci` and `finding` repairs here because the incident below was a value's meaning going wrong, which a failing check or a settle-time finding reports as readily as a thread. The incident: one PR took five review rounds, each finding the same class of defect and each fix creating the next. A staleness value was read by a card, a status label, a timer, a memoized submit gate and a dismiss button; fixing the card first made its badge read *Expired* while the memoized gate, keyed on references that never changed, still allowed submission — an alert visibly expired and still submittable. Before any fix, badge and gate were wrong together, which is survivable; making one right created a contradiction a user could act on. A second PR ran the same way on a different axis, the next round finding the same pattern two lines above the last fix. Grepping the identifier found most of it and missed a dialog reached through a derived prop, which is why the rule follows the value to what it gates rather than stopping at who calls it, and why the reply states the method: "every consumer routes through these two functions" invites agreement, where "I grepped these two names" invites the catch.

**Why two lint rejections of one fix are a design signal:** a worker under budget pressure reaches for the suppression comment, and the rule it suppresses is usually protecting against exactly the special case the fix introduced. Two rejections of the same fix is the point at which rewording it stops being cheaper than redesigning it — and where the reviewer's requested behaviour needs the suppression, dropping that behaviour would be inventing product intent, so it goes to a human instead.

**Why the pass never selects or escalates its own model:** the caller chose this pass's model from the PR's own repair history (`rules/repair-rounds.md` states the trigger and caps the caller applies). A pass that judges itself under-powered reports the locus evidence and returns — exactly as `implement-issue-core` returns a reasoning-heavy failure rather than escalating one — because the escalation evidence must be readable from durable state so a restarted caller evaluates the same trigger.

**Why the posting-identity selection comes from the caller's map for this pass's own pair:** the caller's transports may not be this pass's, so a matching caller entry answers *selection* only; the read-back the Output contract requires still happens and is what the caller merges. Passing the selection into `resolve-pr-comment` (rather than letting it resolve one of its own) keeps one answer per pass. The full rule is `rules/posting-identity.md`.

## CI repair

The note on why the infrastructure tell raises the hypothesis rather than settling it moved to `rules/ci-attribution-notes.md` with the rule (#144).

## Finding repair

The `finding` type exists because `summarize-tranche` can derive an `IN_FLIGHT_FIX` from durable evidence that is neither CI- nor review-shaped — a worker's documented caveat, the diff itself, a coverage finding — and a code-changing walkthrough ruling arrives the same way. Neither `ci` nor `review` has a compliant invocation for it, and this skill is required (improvising is forbidden), so the documented action point used to force the run to block or improvise. The budget key (`finding-repair-cycles`) and the argument for it being its own counter are `rules/repair-rounds.md`'s (*The finding budget*); the caller-side outcome branching is each caller's own.

**Why a mooted finding returns `NO_CODE_CHANGE` with no cycle consumed:** a later push may already have fixed or superseded the finding; changing code anyway would spend budget re-litigating settled work, exactly as an external CI failure does not consume a CI cycle.

**Why a finding pass never touches review threads:** a finding is not a thread; where a thread carries the same work, the caller dispatches `review` instead, and thread mechanics (replies, resolution) belong to that path's `resolve-pr-comment` flow.

## Review repair

**Why draft state is never changed here:** promoting a draft once its first review round is resolved is a supervisor decision needing the whole-PR picture — which rounds completed, the as-created draft state, whether CI is green. This pass reports the remaining-thread count and leaves the decision with the caller, which is also why the count includes actionable threads *outside* the supplied round: the caller's promotion and settlement logic needs the whole number, not the round's.

## Recovery / checkpointing

**Why repair commits carry a `Repair-Type:` trailer (#144):** a supervisor's cycle counts live in its per-PR record, which is a cache. After a restart `supervise-prs` rebuilds them from the branch, and nothing distinguished a repair commit from an implementation checkpoint or a person's push — so the count could only be guessed, or treated as unknown, which is treated as spent. A trailer is a token rather than prose, reads the same for every repair type, and costs one line per commit.

**Why every code-changing repair ends with a pushed commit:** the remote branch is the durable state; repair work existing only in a local worktree is exactly the loss window checkpointing exists to close, and the caller adopts the pushed head, not the worktree.

## Output

**Why the posting-identity read-back is per (transport, credential) pair and includes `unestablished`:** a repair pass can run on transports the caller never used, so its observations are the caller's only evidence about those write paths — a `gh` reply here can establish an invoking-user path where the caller had only an agent-authored one, which is what re-opens a provisionally unavailable review trigger.

**Why the locus report exists:** whether a supplied finding sits on a locus an earlier repair of this PR wrote is the caller's strongest-model escalation trigger, and this pass has the branch history open while it works. The caller can read the same signal from commit history, so this is corroboration, not the only copy.
