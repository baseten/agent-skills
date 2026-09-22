#!/usr/bin/env python3
"""Scaffold and score an eval round, per CLAUDE.md's comparison method.

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
  python3 scripts/run_evals.py prepare --skill swarm-dispatch --base origin/main
  # 2. dispatch one reader per packet; save its answer to <packet-dir>/answer.md
  # 3. grade each answer against that scenario's assertions, writing
  #    grading.json with expectations[{text, passed, evidence}]
  # 4. score, and read the disagreements
  python3 scripts/run_evals.py score --round <dir>

A new skill has no old arm. `prepare` says so and emits one arm; its scores are
a baseline for the next round rather than a result, because there is nothing to
disagree with.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Fields a reader must never see. `expected_output` and `assertions` are the
# answer; `name` telegraphs it in three words.
WITHHELD = ("expected_output", "assertions", "name")


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


def prepare(skill: str, base: str | None, ids: set[int] | None, round_dir: Path) -> int:
    evals_path = ROOT / "skills" / skill / "evals" / "evals.json"
    if not evals_path.exists():
        print(f"no evals at {_disp(evals_path)}", file=sys.stderr)
        return 1
    data = json.loads(evals_path.read_text(encoding="utf-8"))
    cases = [c for c in data["evals"] if ids is None or c["id"] in ids]
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

    if round_dir.exists():
        shutil.rmtree(round_dir)
    round_dir.mkdir(parents=True)

    for arm, contents in arms.items():
        for rel, text in contents.items():
            dest = round_dir / arm / "contract" / Path(rel).name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="utf-8")

    for arm in arms:
        for c in cases:
            pdir = round_dir / arm / f"eval-{c['id']:02d}"
            pdir.mkdir(parents=True, exist_ok=True)
            packet = {k: v for k, v in c.items() if k not in WITHHELD}
            packet["contract_dir"] = _disp(round_dir / arm / "contract")
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
        "scenarios": [c["id"] for c in cases],
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "single_arm_reason": single_arm_reason,
    }, indent=2) + "\n", encoding="utf-8")

    print(f"round: {_disp(round_dir)}")
    print(f"  skill      {skill}")
    print(f"  arms       {', '.join(sorted(arms))}")
    print(f"  scenarios  {len(cases)}")
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
