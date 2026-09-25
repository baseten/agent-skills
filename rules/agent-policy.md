# Agent policy

This is the rule other skills mean when they cite *the policy file* or `.claude/agent-policy.json`.

**It is not a skill and nobody invokes it.** It is a shared rule, held once at
`rules/agent-policy.md` and copied into each skill that applies it by
`scripts/refresh_shared_rules.sh`. A skill reads its own
`references/agent-policy.md`, which works after `bootstrap.sh` has
installed only that skill's directory, and travels with the skill if it is
moved into a plugin. Edit the source, never a copy; check_shared_rules.py fails if a generated copy diverges.

It states the file's contract: where it lives, its schema, precedence, resolution, fail-closed handling and the merge permissions. Which keys a skill reads, and their built-in defaults, each reading skill states itself.

## The policy file

Personal and work repositories legitimately want opposite behavior from the same run — merge on settle versus leave every merge to the owner, a generous repair budget versus a tight one — so this policy belongs to the repository it governs, not to the run. A repository declares it in `.claude/agent-policy.json`, the one policy file every agent workflow in this repository reads — `backlog-orchestrator` and `implement-issue` read their budgets and `auto-merge` from it, and `npm-dependency-upgrade-orchestrator` reads its merge opt-in from it too. **`schemas/agent-policy.schema.json` indexes every key with its type, its default and which skills read it**; a file points at it with `"$schema": "https://raw.githubusercontent.com/baseten/agent-skills/main/schemas/agent-policy.schema.json"` so an editor, or an agent opening the file, can see what each key does.

**There is no key that waives a gate condition, and its absence is deliberate** — `settle-and-merge`, *The merge gate*, is the gate's only definition, and a config that could subtract from it would be a second definition controlled by whoever writes the file (see `settle-and-merge`, *Merge behavior*, for what to do with a request for one).

Every key is optional, and an absent key takes its built-in default. One file carries every option the reading skills' defaults name as well as the merge policy, deliberately: a second option surface is exactly how two mechanisms drift apart.

**There is no reviewer-identity option, and its absence is deliberate.** Whether a review comment may be auto-fixed is decided by what the comment asks for, never by who wrote it — see `references/review-feedback.md`, *What may be auto-fixed*. A key that gated on the author was removed because it answered a question the kind test already answers, and answered it worse: it reserved fixable comments from vetted humans while admitting unanswerable design questions from vetted bots.

**It is policy that can authorize merges, so it is a config file and not prose** — never a `CLAUDE.md` paragraph, and never a project-level skill override (NOTES: why neither mechanism works).

## Precedence

Two mechanisms override the built-in defaults, and the precedence is stated here and nowhere else: **an explicit invocation argument beats repo config, which beats the built-in defaults — for every key but the two merge permissions, `auto-merge` and `auto-merge-dependencies`.** For those the repository's opt-in is the only route to a merge, exactly as the merge gate states for `auto-merge` (`settle-and-merge`, *The merge gate*): an invocation argument can switch either off for a run, narrowing its gate, but never on — an invocation cannot open one. Without the exemption, an invocation could authorize merges in a repository that never opted in, which is precisely what invariant 12 exists to prevent.

## Resolution

**Policy resolves per PR, from the repository that PR lives in.** A run can span repositories — the manifest in one, PRs landing in several — and per-repo difference is the entire point, so there is no run-wide policy read once from the manifest's repo. In a tranche where one repository carries a config and another does not, the first repository's PRs follow its file and the second's follow the built-in defaults, in the same run, at the same settle. One config, resolved once and applied run-wide, would do the opposite of what the file is for: work-repo rules on a personal repo's PRs, or the reverse.

Keys scope to different objects, and each resolves from the repository that owns its object: a per-PR key from the PR's repository, a per-issue key from the issue's. A reading skill whose keys also scope to the run states where those resolve from.

Read the file at the run's preflight — its start, where it has no separate preflight — once per repository in the run's scope, from the head of that repository's default branch as the run finds it at start — and never again during the run. **This file can authorize merges, so it is owner-authored configuration, and a run must never honour a version written by one of its own workers**: not from a worker's branch, not from a PR, not re-read after a mid-run merge moves the default branch. The policy governing a run is the one in the repository state it started from; a config change takes effect at the next run's preflight. A restart's preflight is a fresh read — that is the restart re-deriving from durable truth, not a worker write leaking in.

## Fail-closed handling

**The file was `.claude/backlog-orchestrator.json` before it was shared**; where `.claude/agent-policy.json` is absent and that one exists, read it and report the old name, so a repository configured under it keeps its policy. A file that is absent means the built-in defaults, unchanged — the file is opt-in and absence is the common case. A file that is present but cannot be honoured **fails closed**, and since this file no longer carries a key whose built-in default is the permissive reading, closed and built-in now coincide for every key: an unparseable file resolves to the built-in defaults for that repository, reported as unreadable in the checkpoint output rather than guessed at, and a key the schema does not know (`schemas/agent-policy.schema.json`, `$schema` itself excepted), a wrong-typed value, or a `0` for `concurrent-open-prs` or `concurrent-workers` — a cap no work could ever start under, so the run would rest with nothing armed — fails the same way at key granularity — defaulted and reported, because a misspelled `auto-merge` must produce no merges, not a guess. Nothing needs a guard beyond that. `auto-merge`'s built-in `false` is already its closed end, so its misspelling produces no merges; the budget keys and `auto-request-settle` fall back to built-ins that grant no authority the owner withheld — a missed tighter budget costs bounded extra attempts and a missed settle opt-out costs a request made to a present user, where zeroing every budget on any stray key would turn a typo into a dead run rather than a closed one. **This simplicity is a consequence of removing the reviewer-identity key and should not be reintroduced casually:** any future key whose permissive value is its default brings back a fail-closed special case, because a corrupt file must never grant more than a parsed one would.

**A key the schema knows but the reading skill does not read** — `auto-merge-dependencies`, say, which only `npm-dependency-upgrade-orchestrator` reads — is ignored, not reported: the file is shared, so every reader sees keys that belong to another.

Report the resolved policy per PR in the checkpoint output, with its source — invocation argument, repo config, or built-ins — so an auto-merge is visible in the record before it is a surprise.

## Merge permissions

**`auto-merge`** — whether invariant 12's gate can open for this repository's PRs at all. `false` is today's behavior: the run never merges. `true` permits a merge only through the gate `settle-and-merge`, *The merge gate*, defines — the key is the opt-in the gate requires, never a bypass of its other conditions. This file is the only place `true` can come from: the precedence rule above (*Precedence*) exempts `auto-merge` from invocation override, so an invocation argument can narrow the gate, never open it. Execution mechanics, including the publish-before-merge step, live in `settle-and-merge`, *Merge behavior*.

**One grant covers every consumer of this key, `implement-issue` included, and that is deliberate.** The permission is scoped to the *gate*, not to the skill that evaluates it: `auto-merge` does not say "this orchestrator may merge", it says a PR this owner's agentic workflow produced may merge **when invariant 12's whole gate holds** (`settle-and-merge`, *The merge gate*, is its only definition, and its *Merge behavior* owns when it is evaluated). Every consumer defers to those for all of it rather than carrying a copy, so a run that satisfies the gate is not riskier because a different skill drove it (NOTES: why not per-consumer keys). What the invocation-override exemption guards *is* a real distinction, and it stands: an argument's authority comes from whoever composed the prompt, a committed file from someone with write access to the repository.

The consequence is worth naming rather than discovering: a config written before a consumer existed grants that consumer too, from the moment the skills are reinstalled. An owner who wants no autonomous merging at all sets both `auto-merge` and `auto-merge-dependencies` to `false`, and an invocation argument narrows either for a single run.
