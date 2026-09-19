#!/usr/bin/env python3
"""Fixtures for run_evals.py's two guards.

Run from the repository root:

    python3 scripts/test_run_evals.py

Why this file exists: both guards fail silently and in the flattering
direction. A packet that leaks `expected_output` or the assertions produces a
reader grading its own answer, which looks like a clean sweep; a round that
counts an ungraded scenario as passing looks like a better result than it is.
Neither shows up as an error, so a green round is evidence about the tree and
none at all about the guards.

Each case is run twice: it must hold against the module intact, and must fail
against the same module with that one guard neutered and nothing else. A case
that holds either way is pinning nothing, and the file says so rather than
reporting a pass.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(withheld=None):
    """Load run_evals fresh, optionally with the leak guard neutered."""
    spec = importlib.util.spec_from_file_location(
        f"run_evals_{id(withheld)}", ROOT / "scripts" / "run_evals.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if withheld is not None:
        mod.WITHHELD = withheld
    return mod


def _fixture(tmp: Path) -> Path:
    """A skill directory with one scenario, as prepare() expects to find it."""
    skill = tmp / "skills" / "fixture-skill"
    (skill / "evals").mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: fixture-skill\ndescription: fixture\n---\n\n# Fixture\n", encoding="utf-8")
    (skill / "evals" / "evals.json").write_text(json.dumps({
        "skill_name": "fixture-skill",
        "description": "fixture",
        "evals": [{
            "id": 0,
            "name": "the-name-telegraphs-the-verdict",
            "prompt": "Question: what do you do?",
            "expected_output": "THE ANSWER",
            "assertions": ["THE ASSERTION"],
        }],
    }), encoding="utf-8")
    return skill


def guard_packet_withholds_the_answer() -> list[str]:
    """A reader's packet must carry neither the answer nor a name hinting at it."""
    failures = []
    for label, withheld, expect_leak in (
        ("intact", None, False),
        ("guard neutered", (), True),
    ):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            mod = _load(withheld)
            mod.ROOT = tmp
            _fixture(tmp)
            with contextlib.redirect_stdout(io.StringIO()):
                rc = mod.prepare("fixture-skill", None, None, tmp / "round")
            if rc != 0:
                failures.append(f"{label}: prepare returned {rc}")
                continue
            packet = json.loads((tmp / "round" / "new" / "eval-00" / "packet.json").read_text())
            leaked = [k for k in ("expected_output", "assertions", "name") if k in packet]
            if expect_leak and not leaked:
                failures.append(
                    "guard neutered but the packet still withheld the answer — "
                    "WITHHELD is not what keeps it out, so this case pins nothing")
            if not expect_leak and leaked:
                failures.append(f"intact module leaked {leaked} into the reader's packet")
            # The key must carry it either way, or the grader has nothing to grade.
            key = json.loads((tmp / "round" / "new" / "eval-00" / "key.json").read_text())
            if key.get("expected_output") != "THE ANSWER" or key.get("assertions") != ["THE ASSERTION"]:
                failures.append(f"{label}: key.json does not carry the grading material")
    return failures


def guard_ungraded_is_not_passing() -> list[str]:
    """score() must report an ungraded scenario, not silently omit it."""
    failures = []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        mod = _load()
        mod.ROOT = tmp
        _fixture(tmp)
        rd = tmp / "round"
        with contextlib.redirect_stdout(io.StringIO()):
            mod.prepare("fixture-skill", None, None, rd)
        # No grading.json written at all.
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = mod.score(rd)
        out = buf.getvalue()
        if rc != 0:
            failures.append(f"score returned {rc} on an ungraded round")
        if "Ungraded" not in out:
            failures.append("score did not report the ungraded scenario as ungraded")
        if "0/0" not in out and "scenarios graded" not in out:
            failures.append("score did not report how many scenarios were graded")
    return failures


def guard_single_arm_is_labelled() -> list[str]:
    """A skill absent from the base ref has no old arm, and must be said so."""
    failures = []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        mod = _load()
        mod.ROOT = tmp
        _fixture(tmp)
        rd = tmp / "round"
        # ROOT is not a git repo, so _git_show returns None: the new-skill case.
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            mod.prepare("fixture-skill", "origin/main", None, rd)
        meta = json.loads((rd / "round.json").read_text())
        if meta["arms"] != ["new"]:
            failures.append(f"expected a single arm, got {meta['arms']}")
        if not meta.get("single_arm_reason"):
            failures.append("single-arm round carries no reason, so a reader cannot tell")
        if "ONE ARM ONLY" not in buf.getvalue():
            failures.append("prepare did not say the round has one arm")
    return failures


GUARDS = (
    ("packet withholds the answer", guard_packet_withholds_the_answer),
    ("ungraded is not passing", guard_ungraded_is_not_passing),
    ("single arm is labelled", guard_single_arm_is_labelled),
)


def main() -> int:
    bad = 0
    for name, fn in GUARDS:
        failures = fn()
        if failures:
            bad += 1
            print(f"FAIL  {name}")
            for f in failures:
                print(f"        {f}")
        else:
            print(f"ok    {name}")
    print(f"\n{len(GUARDS)} guard(s) checked · {bad} failure(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
