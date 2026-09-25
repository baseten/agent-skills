#!/usr/bin/env python3
"""Scaffold and score an eval round, per CLAUDE.md's comparison method.

Companions (an evals.json's top-level "companions") are read from the new
revision's evals.json for both arms: the list says which skills a reader needs
today, and each arm then gets those skills' files as they stood at that arm's
revision.

The method is not this script's invention and it is not negotiable here:

  * two arms, the old contract and the new, graded against the same assertions;
  * the baseline comes from git into a scratch directory, never a copy in the
    tree, which would be a second contract to maintain;
  * a reader holds **only the contract and the prompt** - one that has seen
    `expected_output` or the assertions is grading its own answer;
  * the information is entirely in the **disagreement**. A single-arm run
    returns a clean sweep and teaches nothing.

What is deterministic lives here: materialising the arms, emitting reader
packets that cannot leak the answer, and scoring. The model calls do not - this
repository has no API key and `checks.yml` keeps model-graded work out of CI on
purpose. Dispatch the packets yourself, one reader per packet, and write each
answer back beside it.

  # 1. scaffold both arms
  python3 scripts/run_evals.py prepare --skill swarm --base origin/main
  # 2. dispatch one reader per packet; save its answer to <packet-dir>/answer.md
  # 3. grade each answer against that scenario's assertions, writing
  #    grading.json with expectations[{text, passed, evidence}]
  # 4. score, and read the disagreements
  python3 scripts/run_evals.py score --round <dir>

A new skill has no old arm. `prepare` says so and emits one arm; its scores are
a baseline for the next round rather than a result, because there is nothing to
disagree with.

A skill whose contract cites another skill's rules as its own - an orchestrator
that defers its worker mechanics to `swarm` - names that skill in a top-level
`"companions": ["swarm"]` array in its evals.json. `prepare` then puts each
companion's SKILL.md and NOTES.md into both arms' contract directories as
`<companion>-SKILL.md` and `<companion>-NOTES.md`, the old arm's read from git at
the base, and tells the reader they are part of the contract. Without it a
reader holds a contract that says "apply it from there" with nothing there, and
a rule moved between skills reads as a rule deleted. A companion that does not
exist at the base contributes nothing to the old arm, which is the truth about
that base.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Fields a reader must never see. `expected_output` and `assertions` are the
# answer; `name` telegraphs it in three words.
WITHHELD = ("expected_output", "assertions", "name")

# What a companion skill contributes to a contract directory, per arm.
COMPANION_FILES = ("SKILL.md", "NOTES.md")

# Whether a reference a rule cites joins the contract too. A shared rule that
# cites `references/<x>.md` is carried with <x> beside it (refresh_shared_rules.sh
# derives that closure), so a reader holding only the first rule is holding a
# pointer to a file it was never given.
FOLLOW_RULE_CITATIONS = True


def _disp(p: Path) -> str:
    """A path to show a human: repo-relative inside the tree, absolute outside.

    The round directory is normally a scratch path outside the repo - CLAUDE.md
    requires the baseline never be committed - so relative_to(ROOT) is the
    exceptional case rather than the expected one.
    """
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def _git_show(ref: str, path: str) -> str | None:
    r = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        cwd=ROOT, capture_output=True, text=True,
    )
    return r.stdout if r.returncode == 0 else None


def _contract_files(skill: str, base: str | None = None) -> list[str]:
    """The files a reader is given: the contract and its companions, never evals.

    The union of both revisions, not the working tree alone. A change that
    deletes or renames a NOTES.md or a reference leaves that file out of the
    checkout, so enumerating only what is present now drops it from BOTH arms -
    and the base arm then carries a contract the base never had, usually an old
    SKILL.md citing a reference that is not beside it. The comparison reports
    agreement against a baseline that was never real.
    """
    out: set[str] = set()
    d = ROOT / "skills" / skill
    for rel in ("SKILL.md", "NOTES.md"):
        if (d / rel).exists():
            out.add(f"skills/{skill}/{rel}")
    refs = d / "references"
    if refs.is_dir():
        out |= {f"skills/{skill}/references/{p.name}" for p in refs.glob("*.md")}

    if base is not None:
        listing = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", base, f"skills/{skill}/"],
            cwd=ROOT, capture_output=True, text=True,
        )
        for rel in listing.stdout.split("\n"):
            rel = rel.strip()
            if not rel or "/evals/" in rel or not rel.endswith(".md"):
                continue
            tail = rel[len(f"skills/{skill}/"):]
            if tail in ("SKILL.md", "NOTES.md") or tail.startswith("references/"):
                out.add(rel)
    return sorted(out)


def _cited_refs(text: str) -> set[str]:
    return set(re.findall(r"`references/([a-z0-9-]+\.md)`", text))


def _reached_refs(arm: str, base: str | None, text: str, owner: str) -> dict[str, str]:
    """The references `text` cites, and those rules' own citations, transitively."""
    out: dict[str, str] = {}
    todo = sorted(_cited_refs(text))
    while todo:
        name = todo.pop()
        if name in out:
            continue
        ref = _ref_text(arm, base, name, owner)
        if ref is None:
            continue
        out[name] = ref
        if FOLLOW_RULE_CITATIONS:
            todo.extend(sorted(_cited_refs(ref) - set(out)))
    return out


def _ref_text(arm: str, base: str | None, name: str, owner: str) -> str | None:
    """A generated reference for one arm: rules/ at that arm's revision."""
    if arm == "new":
        src = ROOT / "rules" / name
        return src.read_text(encoding="utf-8") if src.exists() else None
    return _git_show(base, f"rules/{name}") or _git_show(base, f"skills/{owner}/references/{name}")


def _companion_files(arm: str, base: str | None, companion: str) -> dict[str, str]:
    """A companion's contract files for one arm, keyed by the name a reader sees.

    Empty where the companion has no SKILL.md at that arm's revision: a skill
    that did not exist at the base is not part of the base's contract.
    """
    out: dict[str, str] = {}
    for name in COMPANION_FILES:
        rel = f"skills/{companion}/{name}"
        if arm == "new":
            path = ROOT / rel
            text = path.read_text(encoding="utf-8") if path.exists() else None
        else:
            text = _git_show(base, rel)
        if text is not None:
            out[f"{companion}-{name}"] = text
    if f"{companion}-SKILL.md" not in out:
        return {}
    return out


def prepare(skill: str, base: str | None, ids: set[int] | None, round_dir: Path) -> int:
    evals_path = ROOT / "skills" / skill / "evals" / "evals.json"
    if not evals_path.exists():
        print(f"no evals at {_disp(evals_path)}", file=sys.stderr)
        return 1
    data = json.loads(evals_path.read_text(encoding="utf-8"))
    # Both shapes are accepted: {"evals": [...], "companions": [...]} or a bare list.
    all_cases = data if isinstance(data, list) else data["evals"]
    companions = [] if isinstance(data, list) else list(data.get("companions") or [])
    cases = [c for c in all_cases if ids is None or c["id"] in ids]
    if not cases:
        print("no scenarios selected", file=sys.stderr)
        return 1

    files = _contract_files(skill, base)
    arms: dict[str, dict[str, str]] = {"new": {}}
    for rel in files:
        if (ROOT / rel).exists():
            arms["new"][rel] = (ROOT / rel).read_text(encoding="utf-8")

    single_arm_reason = None
    if base is None:
        single_arm_reason = "no --base given"
    else:
        old = {rel: _git_show(base, rel) for rel in files}
        if old.get(f"skills/{skill}/SKILL.md") is None:
            single_arm_reason = f"{skill} does not exist at {base} - it is new"
        else:
            arms["old"] = {rel: text for rel, text in old.items() if text is not None}

    # references/ is generated from rules/ and not committed, so neither arm can
    # read it off the tree or out of git. Rebuild it for each arm from that
    # arm's own rules/ - the working tree for new, the base revision for old -
    # for exactly the references that arm's SKILL.md reaches: what it cites,
    # plus what those rules cite in turn, as check_shared_rules.py defines it.
    # An old base from before the copies stopped being committed falls back to
    # its copy.
    for arm, contents in arms.items():
        skill_text = contents.get(f"skills/{skill}/SKILL.md", "")
        for name, text in _reached_refs(arm, base, skill_text, skill).items():
            contents[f"skills/{skill}/references/{name}"] = text

    # Companion skills, per arm, and the references their own SKILL.md reaches.
    # Kept apart from `arms` because their names are prefixed in the contract dir.
    extra: dict[str, dict[str, str]] = {arm: {} for arm in arms}
    present: dict[str, list[str]] = {arm: [] for arm in arms}
    for arm in arms:
        for comp in companions:
            files = _companion_files(arm, base, comp)
            if not files:
                continue
            present[arm].append(comp)
            extra[arm].update(files)
            reached = _reached_refs(arm, base, files.get(f"{comp}-SKILL.md", ""), comp)
            for name, text in sorted(reached.items()):
                if f"skills/{skill}/references/{name}" in arms[arm] or name in extra[arm]:
                    continue
                extra[arm][name] = text

    if round_dir.exists():
        shutil.rmtree(round_dir)
    round_dir.mkdir(parents=True)

    for arm, contents in arms.items():
        named = {Path(rel).name: text for rel, text in contents.items()}
        named.update(extra[arm])
        for name, text in named.items():
            dest = round_dir / arm / "contract" / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="utf-8")

    for arm in arms:
        for c in cases:
            pdir = round_dir / arm / f"eval-{c['id']:02d}"
            pdir.mkdir(parents=True, exist_ok=True)
            packet = {k: v for k, v in c.items() if k not in WITHHELD}
            packet["contract_dir"] = _disp(round_dir / arm / "contract")
            if present[arm]:
                names = [f"`{c}-{f}`" for c in present[arm] for f in COMPANION_FILES
                         if f"{c}-{f}" in extra[arm]]
                packet["contract_note"] = (
                    "Every file in contract_dir is part of the contract you are executing. "
                    f"Besides the skill's own files it holds {', '.join(names)}: the contract "
                    f"of {', '.join(f'`{c}`' for c in present[arm])}, which this skill cites for "
                    "rules it applies as its own. Where the contract says a rule lives in that "
                    "skill, it is in those files and binds you exactly as the skill's own text does.")
            (pdir / "packet.json").write_text(
                json.dumps(packet, indent=2) + "\n", encoding="utf-8")
            # The grading key sits beside the packet, not inside it. A reader is
            # given packet.json; a grader is given key.json and answer.md.
            (pdir / "key.json").write_text(json.dumps(
                {"id": c["id"], "name": c["name"],
                 "expected_output": c["expected_output"],
                 "assertions": c["assertions"]}, indent=2) + "\n", encoding="utf-8")

    (round_dir / "round.json").write_text(json.dumps({
        "skill": skill, "base": base, "arms": sorted(arms),
        "companions": {arm: present[arm] for arm in sorted(arms)},
        "scenarios": [c["id"] for c in cases],
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "single_arm_reason": single_arm_reason,
    }, indent=2) + "\n", encoding="utf-8")

    print(f"round: {_disp(round_dir)}")
    print(f"  skill      {skill}")
    print(f"  arms       {', '.join(sorted(arms))}")
    print(f"  scenarios  {len(cases)}")
    for arm in sorted(arms):
        if companions:
            print(f"  companions {arm}: {', '.join(present[arm]) or 'none at this revision'}")
    print(f"  packets    {len(cases) * len(arms)}  (each: packet.json for a reader, key.json for a grader)")
    if single_arm_reason:
        print(f"\n  ONE ARM ONLY - {single_arm_reason}.")
        print("  The information in this method is the disagreement between arms, so treat")
        print("  these scores as a baseline for the next round, not as a result.")
    print("\nNext: dispatch one reader per packet.json, save its reply to answer.md")
    print("beside it, then grade answer.md against key.json into grading.json.")
    return 0


def score(round_dir: Path) -> int:
    meta_path = round_dir / "round.json"
    if not meta_path.exists():
        print(f"not an eval round: {round_dir}", file=sys.stderr)
        return 1
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    results: dict[str, dict[int, list[bool]]] = {}
    missing: list[str] = []
    for arm in meta["arms"]:
        results[arm] = {}
        for sid in meta["scenarios"]:
            g = round_dir / arm / f"eval-{sid:02d}" / "grading.json"
            if not g.exists():
                missing.append(f"{arm}/eval-{sid:02d}")
                continue
            gd = json.loads(g.read_text(encoding="utf-8"))
            exps = gd.get("expectations")
            if not isinstance(exps, list) or not exps:
                missing.append(f"{arm}/eval-{sid:02d} (no expectations array)")
                continue
            results[arm][sid] = [bool(e.get("passed")) for e in exps]

    for arm in meta["arms"]:
        graded = results[arm]
        total = sum(len(v) for v in graded.values())
        passed = sum(sum(v) for v in graded.values())
        rate = f"{passed}/{total}" + (f"  {passed / total:.0%}" if total else "")
        print(f"{arm:>5}: {len(graded)}/{len(meta['scenarios'])} scenarios graded · assertions {rate}")

    if len(meta["arms"]) == 2 and results.get("old") and results.get("new"):
        print("\nDisagreements — this is the whole point of the round:")
        any_diff = False
        for sid in meta["scenarios"]:
            o, n = results["old"].get(sid), results["new"].get(sid)
            if o is None or n is None or len(o) != len(n):
                continue
            for i, (a, b) in enumerate(zip(o, n)):
                if a != b:
                    any_diff = True
                    key = json.loads((round_dir / "new" / f"eval-{sid:02d}" / "key.json")
                                     .read_text(encoding="utf-8"))
                    moved = "REGRESSED" if a and not b else "gained"
                    print(f"  eval {sid:02d} ({key['name']}) assertion {i}: {moved}")
                    print(f"      {key['assertions'][i]}")
        if not any_diff:
            print("  none — the rewrite changed no verdict on any graded assertion.")
    elif meta.get("single_arm_reason"):
        print(f"\nOne arm only ({meta['single_arm_reason']}) — baseline, not a result.")

    if missing:
        print(f"\nUngraded ({len(missing)}): {', '.join(missing[:8])}"
              + (" …" if len(missing) > 8 else ""))
        print("An ungraded scenario is not a passing one. Report it as ungraded.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("prepare", help="materialise both arms and emit reader packets")
    p.add_argument("--skill", required=True)
    p.add_argument("--base", default="origin/main",
                   help="ref for the old arm; omit or pass '' for a single-arm baseline")
    p.add_argument("--ids", default=None, help="comma-separated scenario ids (default: all)")
    p.add_argument("--out", default=None, help="round directory (default: a scratch path)")

    s = sub.add_parser("score", help="read grading.json files and report disagreements")
    s.add_argument("--round", required=True)

    a = ap.parse_args()
    if a.cmd == "prepare":
        ids = {int(x) for x in a.ids.split(",")} if a.ids else None
        out = Path(a.out) if a.out else Path("/tmp") / f"evals-{a.skill}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
        return prepare(a.skill, a.base or None, ids, out.resolve())
    return score(Path(a.round).resolve())


if __name__ == "__main__":
    raise SystemExit(main())
