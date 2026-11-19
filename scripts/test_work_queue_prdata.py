#!/usr/bin/env python3
"""Run conductor's work-queue prdata.py and mergeq.py against a stubbed `gh`,
and build.py and prsteps.py against fake states.

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
        "user": {"login": OWNER},
        p: {"head": {"sha": "f" * 40}, "html_url": f"https://github.com/{REPO}/pull/{N}",
            "title": "Add thing", "base": {"ref": "main"}, "draft": False, "state": "open",
            "merged": False, "mergeable_state": "clean", "user": {"login": "author"},
            "requested_teams": [{"slug": "fe-platform", "name": "FE Platform"}]},
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
        d = json.loads(out)[0]
        assert (d["requested_teams"], d["reviewed_by"]) == ([{"slug": "fe-platform", "name": "FE Platform"}], ["rev"]), d
        assert d["teams"] == {"fe-platform": {"name": None, "members": None}} and d["ever_ready"] is False, d
        print("ok  prdata.py reads requested teams and who reviewed, for the PR steps;"
              " an unreadable team's members are null, not a stop")
        fx = base_fixture()
        fx["orgs/acme/teams/fe-platform"] = {"name": "FE Platform"}
        fx["orgs/acme/teams/fe-platform/members"] = [{"login": "rev"}, {"login": "kim"}]
        fx[f"repos/{REPO}/pulls/{N}"]["draft"] = True
        fx[f"repos/{REPO}/issues/{N}/timeline"] = [{"event": "ready_for_review"}, {"event": "convert_to_draft"}]
        r = run_prdata(tmp, fx)
        assert r.returncode == 0, r.stderr
        d = json.loads(r.stdout)[0]
        assert d["teams"] == {"fe-platform": {"name": "FE Platform", "members": ["kim", "rev"]}}, d["teams"]
        assert d["ever_ready"] is True, d
        print("ok  prdata.py reads a team's members where it can, and a draft's ready history from its timeline")
        del fx[f"repos/{REPO}/issues/{N}/timeline"]
        r = run_prdata(tmp, fx)
        assert r.returncode != 0, "an unreadable timeline must stop the script"
        print("ok  an unreadable timeline stops the script")
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

        unread_out = None
        for label, user in (("another account", {"login": "someone-else"}), ("no user read", None)):
            fx = base_fixture()
            fx[f"repos/{REPO}/pulls/{N}/reviews"].pop()  # its pending review is invisible
            fx[f"repos/{REPO}/pulls/{N}/ccr/review_threads"] = \
                fx[f"repos/{REPO}/pulls/{N}/ccr/review_threads"][2:]
            if user is None:
                del fx["user"]
            else:
                fx["user"] = user
            r = run_prdata(tmp, fx)
            assert r.returncode == 0, r.stderr
            d = json.loads(r.stdout)[0]
            got = (d["owner_pending_drafts"], d["owner_pending_review"], d["owner_pending_read"])
            assert got == (None, None, False), f"{label}: {got}"
            unread_out = r.stdout
            print(f"ok  read as {label}: the owner's pending review is unread (null), never 0")

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

        with open(prp, "w") as f:
            f.write(unread_out)
        with open(state, "w") as f:
            json.dump({}, f)
        r = subprocess.run([sys.executable, "-I", os.path.join(WQ, "mergeq.py"), "--state", state,
                            "--notes", notes, "--prdata", prp], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        row = json.load(open(state))["merge"][0]
        assert any("unread" in b for b in row["blockers"]), row["blockers"]
        print(f"ok  mergeq.py shows an unread pending review as a blocker: {row['blockers']}")
        assert row["ready"] is False
        clean = dict(json.loads(unread_out)[0], owner_pending_drafts=0, owner_pending_review=None,
                     unresolved=0, approvals=["rev"], changes=[], fail=[], pending=[], checks=1)
        with open(prp, "w") as f:
            json.dump([clean, dict(clean, pr="102", url=clean["url"] + "2")], f)
        with open(notes, "w") as f:
            json.dump([{"repo": REPO, "pr": N}, {"repo": REPO, "pr": "102", "after": N}], f)
        with open(state, "w") as f:
            json.dump({}, f)
        r = subprocess.run([sys.executable, "-I", os.path.join(WQ, "mergeq.py"), "--state", state,
                            "--notes", notes, "--prdata", prp], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        ready = {m["pr"]: m["ready"] for m in json.load(open(state))["merge"]}
        assert ready == {N: True, "102": False}, ready
        print(f"ok  mergeq.py marks only a clean row Ready, not one still after another: {ready}")

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
        for label, item in (("no done", {"repo": REPO, "pr": "7", "steps": [{"label": "Merge"}],
                                          "stepsReadAt": "2026-11-19T09:00:00Z"}),
                            ("no stamp", {"repo": REPO, "pr": "7", "steps": [{"label": "Merge", "done": False}]})):
            r = build({"title": "Work queue", "prs": [item]})
            assert r.returncode != 0 and f"{REPO}#7" in r.stderr, (label, r.stderr)
        print("ok  build.py refuses a PR item without prsteps.py's stamp, or with a step lacking done")

        # prsteps.py: the "Your PRs" items, steps read from prdata, never ticked
        def pr(n, **kw):
            base = dict(repo=REPO, pr=n, url=f"https://github.com/{REPO}/pull/{n}", title=f"PR {n}",
                        draft=False, state="open", merged=False, approvals=[], changes=[],
                        requested_teams=[], reviewed_by=[])
            base.update(kw)
            return base
        prdata = [pr("1", draft=True), pr("12", draft=True), pr("13", draft=True, ever_ready=True), pr("2", requested_teams=[{"slug": "fe-platform", "name": "FE Platform"}]),
                  pr("9", draft=True, ever_ready=True),
                  pr("10", reviewed_by=["out"], approvals=["out"],
                     teams={"fe-platform": {"name": "FE Platform", "members": ["kim"]}}),
                  pr("11", reviewed_by=["kim"], approvals=["kim"], fail=["e2e"],
                     teams={"fe-platform": {"name": "FE Platform", "members": ["kim"]}}),
                  pr("3", reviewed_by=["rev"], approvals=["rev"]), pr("4", merged=True, state="closed"),
                  pr("5", approvals=["rev"]),
                  pr("6", reviewed_by=["rev", "dana"], approvals=["rev"], changes=["dana"]),
                  pr("8", requested_teams=[{"slug": "fe-platform", "name": "FE Platform"}])]
        prs = [{"repo": REPO, "pr": "1", "team": "payments"},
               {"repo": REPO, "pr": "12", "awaitingPublish": True},
               {"repo": REPO, "pr": "13", "awaitingPublish": True},
               {"repo": REPO, "pr": "2", "team": "FE Platform",
                "review": {"href": "https://tracker.example.com/r/2", "label": "Tracker review", "drafts": 2},
                "issues": [{"label": "#9", "href": f"https://github.com/{REPO}/issues/9"}]},
               {"repo": REPO, "pr": "3", "team": "payments",
                "review": {"href": "https://tracker.example.com/r/3", "label": "Tracker review", "drafts": None},
                "issues": [{"k": "tr", "label": "T-1", "href": "https://tracker.example.com/T-1"}]},
               {"repo": REPO, "pr": "4"},
               {"repo": REPO, "pr": "6", "team": "payments"},
               {"repo": REPO, "pr": "8", "team": "fe platform"},
               {"repo": REPO, "pr": "9", "team": "payments"},
               {"repo": REPO, "pr": "10", "team": "FE Platform"},
               {"repo": REPO, "pr": "11", "team": "fe-platform"},
               {"repo": REPO, "pr": "5", "session": "https://claude.ai/code/session_X",
                "review": {"href": "https://tracker.example.com/r/5", "label": "Tracker review"}}]
        for name, val in (("prdata.json", prdata), ("prs.json", prs),
                          ("state.json", {"merge": [{"repo": REPO, "pr": "5", "blockers": []}],
                                          "doneRecent": []})):
            with open(os.path.join(tmp, name), "w") as f:
                json.dump(val, f)
        r = subprocess.run([sys.executable, "-I", os.path.join(WQ, "prsteps.py"), "--state", state,
                            "--prs", os.path.join(tmp, "prs.json"), "--prdata", os.path.join(tmp, "prdata.json")],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        st = json.load(open(state))
        steps = {p["pr"]: [s["done"] for s in p["steps"]] for p in st["prs"]}
        assert steps == {"1": [False, False, False, False], "12": [False, False, False, False],
                         "13": [False, False, False, False], "2": [True, True, False, False],
                         "3": [True, True, True, False], "6": [True, True, False, False],
                         "8": [True, True, False, False], "9": [False, False, False, False],
                         "10": [True, True, False, False], "11": [True, True, True, False]}, steps
        print(f"ok  prsteps.py reads each step from prdata: {steps}")
        by = {p["pr"]: p for p in st["prs"]}
        assert by["2"]["steps"][1]["label"] == "Request FE Platform"
        print("ok  the caller's team matches the forge team's name or slug, ignoring case")
        assert by["6"]["steps"][2]["label"] == "Changes requested" and by["6"]["waitsOn"] == "team"
        print("ok  an outstanding change request holds Team approves, shown as Changes requested, never Merge next")
        assert by["9"]["steps"][0]["label"] == "Held in draft" and by["9"]["waitsOn"] == "held"
        assert by["13"]["steps"][0]["label"] == "Held in draft" and by["13"]["waitsOn"] == "held"
        assert by["1"]["steps"][0]["label"] == "Draft" and by["1"]["waitsOn"] == "draft"
        assert by["12"]["steps"][0]["label"] == "Mark ready" and by["12"]["waitsOn"] == "owner"
        print("ok  a draft is offered to mark ready only where its run reported it awaiting the owner's publish;"
              " one ever ready stays held even so, and any other is a plain Draft")
        assert by["10"]["steps"][2] == {"label": "Team approves", "done": False}
        assert by["3"]["steps"][2]["label"] == "Team approves — approved (team not verified)"
        print("ok  where the team's members were read only a member's approval counts; otherwise it is labelled unverified")
        assert all(p["steps"][3]["label"] != "Merge" for p in st["prs"])
        assert by["3"]["steps"][3]["label"] == "Not in the merge notes" and by["3"]["waitsOn"] == "blocked"
        assert by["11"]["steps"][3]["label"] == "Blocked: CI red (e2e)" and by["11"]["waitsOn"] == "blocked"
        print("ok  an approved PR that is not a Ready merge row names its blocker, never Merge")
        assert {k: p["waitsOn"] for k, p in by.items()} == {"1": "draft", "12": "owner", "13": "held", "2": "team", "3": "blocked",
                                                           "6": "team", "8": "team", "9": "held",
                                                           "10": "team", "11": "blocked"}
        assert all(p.get("stepsReadAt") for p in st["prs"])
        print("ok  each item says whose step is next and carries prsteps.py's stamp")
        labels = {p["pr"]: [(l["k"], l["label"]) for l in p["links"]] for p in st["prs"]}
        assert labels["2"] == [("gh", "#2"), ("rv", "Tracker review · 2 drafts"), ("iss", "#9")], labels["2"]
        assert labels["3"] == [("gh", "#3"), ("rv", "Tracker review"), ("tr", "T-1")], labels["3"]
        assert by["1"]["noIssue"] and not by["2"]["noIssue"]
        print("ok  the review link sits right after the PR link, with a count only where one was read;"
              " an issue keeps a caller's kind, and none says so")
        assert st["doneRecent"] and "#4" in st["doneRecent"][0] and "merged" in st["doneRecent"][0], st["doneRecent"]
        assert "4" not in steps
        print(f"ok  a merged PR leaves the section for Done recently: {st['doneRecent'][0]}")
        assert "5" not in steps and [l["k"] for l in st["merge"][0]["links"]] == ["ses", "gh", "rv"], st["merge"]
        print("ok  a PR that is a merge row is not listed twice, and its row takes the links")
        r = build(dict(st, title="Work queue"))
        assert r.returncode == 0, r.stderr
        print("ok  build.py builds the prsteps.py output")


if __name__ == "__main__":
    main()
