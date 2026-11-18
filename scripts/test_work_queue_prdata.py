#!/usr/bin/env python3
"""Run conductor's work-queue prdata.py and mergeq.py against a stubbed `gh`,
and build.py against fake states.

    python3 -I scripts/test_work_queue_prdata.py

Standard library only. A fake `gh` on PATH answers each `gh api` route from a
fixture and fails every other route with HTTP 404, as GitHub does, so the
scripts run unchanged. The fixture is the shape reported from a live run
(owner's report, 2026-11-18): the owner's PENDING review on a PR, whose comment
ids appear in the thread listing but 404 on pulls/comments/{id}. Each case
asserts what the scripts emit, and that every other failed read still stops.
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WQ = os.path.join(ROOT, "skills", "conductor", "assets", "work-queue")
REPO, N, OWNER = "acme/api", "101", "owner"

FAKE_GH = r'''#!/usr/bin/env python3 -I
import json, os, sys
fx = json.load(open(os.environ["FAKE_GH_FIXTURE"]))
args = [a for a in sys.argv[2:] if a not in ("--paginate", "--slurp")]
slurp = "--slurp" in sys.argv
route = args[0]
if route == "graphql":
    g = fx.get("graphql")
    if g is None:
        sys.exit("gh: GitHub GraphQL is not available (HTTP 403)")
    print(json.dumps([g]))
    sys.exit(0)
key = route.split("?")[0]
if key not in fx:
    sys.stderr.write(f"gh: Not Found (HTTP 404) {key}\n")
    sys.exit(1)
print(json.dumps([fx[key]] if slurp else fx[key]))
'''


def comment(cid, login, body):
    return {"id": cid, "user": {"login": login}, "body": body}


def base_fixture():
    p = f"repos/{REPO}/pulls/{N}"
    reviewer_q = comment(1001, "rev", "Why this default?")
    owner_pending_reply = comment(5001, OWNER, "Because the API requires it")
    owner_pending_new = comment(5002, OWNER, "Note to self: rename")
    reviewer_q2 = comment(1002, "rev", "Typo here")
    owner_done = comment(1003, OWNER, "Fixed in abc1234")
    reviewer_open = comment(1004, "rev", "Please add a test")
    return {
        p: {"head": {"sha": "f" * 40}, "html_url": f"https://github.com/{REPO}/pull/{N}",
            "title": "Add thing", "base": {"ref": "main"}, "draft": False, "state": "open",
            "merged": False, "mergeable_state": "clean"},
        f"{p}/reviews": [
            {"id": 800, "state": "APPROVED", "user": {"login": "rev", "type": "User"}},
            {"id": 900, "state": "PENDING", "user": {"login": OWNER, "type": "User"}},
        ],
        f"{p}/reviews/900/comments": [owner_pending_reply, owner_pending_new],
        # submitted comments only: the pending review's are absent, as on GitHub
        f"{p}/comments": [reviewer_q, reviewer_q2, owner_done, reviewer_open],
        f"{p}/ccr/review_threads": [
            {"comment_ids": [1001, 5001], "resolved": False, "outdated": False},
            {"comment_ids": [5002], "resolved": False, "outdated": False},
            {"comment_ids": [1002, 1003], "resolved": False, "outdated": False},
            {"comment_ids": [1004], "resolved": False, "outdated": True},
        ],
        f"repos/{REPO}/commits/{'f' * 40}/check-runs": {
            "check_runs": [{"name": "ci", "status": "completed", "conclusion": "success"}]},
        f"repos/{REPO}/commits/{'f' * 40}/status": {"statuses": []},
    }


def graphql_threads(fx):
    def node(login, body, state="SUBMITTED"):
        return {"author": {"login": login}, "body": body, "state": state}
    nodes = [
        {"isResolved": False, "isOutdated": False,
         "comments": {"nodes": [node(OWNER, "Because the API requires it", "PENDING")]}},
        {"isResolved": False, "isOutdated": False,
         "comments": {"nodes": [node(OWNER, "Note to self: rename", "PENDING")]}},
        {"isResolved": False, "isOutdated": False,
         "comments": {"nodes": [node(OWNER, "Fixed in abc1234")]}},
        {"isResolved": False, "isOutdated": True,
         "comments": {"nodes": [node("rev", "Please add a test")]}},
    ]
    fx["graphql"] = {"data": {"repository": {"pullRequest": {"reviewThreads": {
        "nodes": nodes, "pageInfo": {"hasNextPage": False, "endCursor": None}}}}}}
    return fx


def run_prdata(tmp, fx):
    fxp = os.path.join(tmp, "fixture.json")
    with open(fxp, "w") as f:
        json.dump(fx, f)
    env = dict(os.environ, FAKE_GH_FIXTURE=fxp, PATH=tmp + os.pathsep + os.environ["PATH"])
    return subprocess.run([sys.executable, "-I", os.path.join(WQ, "prdata.py"),
                           "--repo", REPO, "--owner", OWNER, N],
                          capture_output=True, text=True, env=env)


def expect_counts(name, r):
    assert r.returncode == 0, f"{name}: prdata.py failed: {r.stderr}"
    d = json.loads(r.stdout)[0]
    got = {k: d[k] for k in ("unresolved", "answered", "needs_reply",
                             "owner_pending_drafts", "owner_pending_review")}
    want = {"unresolved": 1, "answered": 1, "needs_reply": 1,
            "owner_pending_drafts": 2, "owner_pending_review": 900}
    assert got == want, f"{name}: {got} != {want}"
    print(f"ok  {name}: {got}")
    return r.stdout


def main():
    with tempfile.TemporaryDirectory() as tmp:
        gh = os.path.join(tmp, "gh")
        with open(gh, "w") as f:
            f.write(FAKE_GH.replace("#!/usr/bin/env python3 -I", f"#!{sys.executable} -I", 1))
        os.chmod(gh, 0o755)

        out = expect_counts("ccr route, owner's pending review",
                            run_prdata(tmp, base_fixture()))
        expect_counts("graphql route, owner's pending review",
                      run_prdata(tmp, graphql_threads(base_fixture())))

        fx = base_fixture()
        fx[f"repos/{REPO}/pulls/{N}/ccr/review_threads"].append(
            {"comment_ids": [7777], "resolved": False, "outdated": False})
        r = run_prdata(tmp, fx)
        assert r.returncode != 0 and "404" in r.stderr, \
            f"a 404 outside a pending review must stop: rc={r.returncode} {r.stderr}"
        print("ok  a 404 on a comment in no pending review stops the script")

        fx = base_fixture()
        del fx[f"repos/{REPO}/pulls/{N}/reviews/900/comments"]
        r = run_prdata(tmp, fx)
        assert r.returncode != 0, "an unreadable pending review must stop the script"
        print("ok  an unreadable pending review stops the script")

        fx = base_fixture()
        fx[f"repos/{REPO}/pulls/{N}/reviews"].pop()
        fx[f"repos/{REPO}/pulls/{N}/ccr/review_threads"] = \
            fx[f"repos/{REPO}/pulls/{N}/ccr/review_threads"][2:]
        r = run_prdata(tmp, fx)
        d = json.loads(r.stdout)[0]
        assert (d["owner_pending_drafts"], d["owner_pending_review"]) == (0, None), d
        print("ok  no pending review: owner_pending_drafts 0, owner_pending_review null")

        prp = os.path.join(tmp, "prdata.json")
        with open(prp, "w") as f:
            f.write(out)
        notes = os.path.join(tmp, "notes.json")
        with open(notes, "w") as f:
            json.dump([{"repo": REPO, "pr": N}], f)
        state = os.path.join(tmp, "state.json")
        with open(state, "w") as f:
            json.dump({}, f)
        r = subprocess.run([sys.executable, "-I", os.path.join(WQ, "mergeq.py"), "--state", state,
                            "--notes", notes, "--prdata", prp], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        row = json.load(open(state))["merge"][0]
        assert row["blockers"] == ["Your unsubmitted review: 2 drafts"], row["blockers"]
        print(f"ok  mergeq.py blocks the row: {row['blockers']}")

        # build.py: an interactive page never carries an open option with no ruling
        def build(st):
            sp, out = os.path.join(tmp, "build-state.json"), os.path.join(tmp, "index.html")
            with open(sp, "w") as f:
                json.dump(st, f)
            return subprocess.run([sys.executable, "-I", os.path.join(WQ, "build.py"),
                                   "--state", sp, "--template",
                                   os.path.join(WQ, "template.html"), "--out", out],
                                  capture_output=True, text=True)
        unruled = {"title": "Work queue", "decisions": [{"id": "d1", "status": "open",
                   "options": [{"id": "a", "label": "7 days", "ruling": "Owner ruling: 7 days."},
                               {"id": "b", "label": "30 days"}]}]}
        r = build(dict(unruled, interactive=True))
        assert r.returncode != 0 and "d1/b" in r.stderr, \
            f"an interactive state with an unruled option must not build: {r.returncode} {r.stderr}"
        print("ok  build.py refuses an interactive state with an unruled open option")
        r = build(dict(unruled, interactive=False))
        assert r.returncode == 0, r.stderr
        print("ok  build.py builds the same state read-only")
        with open(os.path.join(WQ, "state.example.json")) as f:
            r = build(json.load(f))
        assert r.returncode == 0, r.stderr
        print("ok  build.py builds state.example.json")


if __name__ == "__main__":
    main()
