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

prdata.py's --from-json route is run on the GitHub MCP tools' reads, in the shapes
they returned live (2026-11-20), including what they cannot read, and on the same
fixture's REST reads in the document's REST form, which must emit what `gh` does.
refresh.py runs the whole pipeline over that REST document.
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


def mcp_doc(pending=False, draft=False, viewer=OWNER):
    """One PR's reads as the GitHub MCP tools return them (shapes read live, 2026-11-20)."""
    pull = {"number": int(N), "head": {"sha": "f" * 40}, "html_url": f"https://github.com/{REPO}/pull/{N}",
            "title": "Add thing", "base": {"ref": "main"}, "draft": draft, "state": "open",
            "merged": False, "mergeable_state": "unknown", "user": {"login": "author"}}
    reviews = [{"id": 700, "state": "APPROVED", "user": {"login": "chatgpt-codex-connector[bot]"}},
               {"id": 800, "state": "APPROVED", "user": {"login": "rev"}}]
    if pending:
        reviews.append({"id": 900, "state": "PENDING", "user": {"login": OWNER}})
    threads = [
        {"is_resolved": False, "is_outdated": False,
         "comments": [{"author": "rev", "body": "Typo here"},
                      {"author": OWNER, "body": "Fixed in abc1234"}]},
        {"is_resolved": False, "is_outdated": True,
         "comments": [{"author": "rev", "body": "Please add a test"}]},
        {"is_resolved": False, "is_outdated": False,
         "comments": [{"author": "rev", "body": "Why?"}, {"author": OWNER, "body": "Shall I?"}]},
        {"is_resolved": True, "is_outdated": False,
         "comments": [{"author": "rev", "body": "Nit"}]}]
    return {"viewer": viewer,
            "teams": {"fe-platform": {"name": "FE Platform", "members": ["rev", "kim"]}},
            "prs": {N: {"pull": pull, "reviews": reviews, "review_threads": threads,
                        "check_runs": {"total_count": 1, "check_runs": [
                            {"name": "ci", "status": "completed", "conclusion": "success"}]},
                        "status": {"state": "pending", "statuses": [], "total_count": 0}}}}


def run_json(tmp, doc, stdin=False, team=()):
    args = [sys.executable, "-I", os.path.join(WQ, "prdata.py"), "--repo", REPO, "--owner", OWNER]
    for t in team:
        args += ["--team", t]
    env = {"PATH": "/nonexistent"}  # no gh: the JSON route must read nothing
    if stdin:
        return subprocess.run(args + ["--from-json", "-"], input=json.dumps(doc),
                              capture_output=True, text=True, env=env)
    dp = os.path.join(tmp, "reads.json")
    with open(dp, "w") as f:
        json.dump(doc, f)
    return subprocess.run(args + ["--from-json", dp], capture_output=True, text=True, env=env)


def json_route(tmp, gh_out):
    r = run_json(tmp, mcp_doc(), team=["fe-platform"])
    assert r.returncode == 0, r.stderr
    d = json.loads(r.stdout)[0]
    assert set(d) == set(json.loads(gh_out)[0]), "the JSON route emits the gh route's fields"
    got = {k: d[k] for k in ("unresolved", "answered", "needs_reply", "approvals", "reviewed_by",
                             "owner_pending_drafts", "owner_pending_review", "owner_pending_read",
                             "checks", "mergeable", "teams", "requested_teams",
                             "requested_teams_read")}
    want = {"unresolved": 2, "answered": 1, "needs_reply": 1, "approvals": ["rev"],
            "reviewed_by": ["rev"], "owner_pending_drafts": 0, "owner_pending_review": None,
            "owner_pending_read": True, "checks": 1, "mergeable": "unknown",
            "requested_teams": None, "requested_teams_read": False,
            "teams": {"fe-platform": {"name": "FE Platform", "members": ["kim", "rev"]}}}
    assert got == want, f"MCP shape: {got} != {want}"
    print("ok  --from-json: the owner's non-question reply is answered, a question is not;"
          " a [bot] login never approves; mergeable unknown stays unknown")
    r2 = run_json(tmp, mcp_doc(), stdin=True, team=["fe-platform"])
    assert r2.returncode == 0 and r2.stdout == r.stdout, r2.stderr
    print("ok  --from-json - reads the document from stdin")
    doc = mcp_doc()
    doc["prs"][N]["status"]["statuses"] = [{"context": "UI Tests", "state": "pending"}]
    d = json.loads(run_json(tmp, doc).stdout)[0]
    assert (d["pending"], d["checks"]) == (["UI Tests"], 2), d
    print("ok  --from-json: a commit status counts beside the check runs")

    d = json.loads(run_json(tmp, mcp_doc(pending=True)).stdout)[0]
    got = (d["owner_pending_read"], d["owner_pending_drafts"], d["owner_pending_review"])
    assert got == (False, None, 900), got
    assert (d["answered"], d["unresolved"]) == (0, 1), d  # both owner-last threads held
    print("ok  --from-json: the owner's PENDING review is seen, its count unread (null), never 0;"
          " their own last reply is counted held, never answered")
    doc = mcp_doc()
    doc["prs"] = {}
    r = run_json(tmp, doc)
    assert r.returncode != 0 and "no PR" in r.stderr, r
    print("ok  --from-json: a document naming no PR stops the script")

    d = json.loads(run_json(tmp, mcp_doc(draft=True)).stdout)[0]
    assert (d["ever_ready"], d["ever_ready_read"]) == (None, False), d
    print("ok  --from-json: a draft's ready history is unread, ever_ready null")
    d = json.loads(run_json(tmp, mcp_doc(viewer=None)).stdout)[0]
    assert (d["owner_pending_read"], d["owner_pending_drafts"]) == (False, None), d
    print("ok  --from-json with no viewer: the owner's pending review is unread")
    d = json.loads(run_json(tmp, mcp_doc(), team=["other-team"]).stdout)[0]
    assert d["teams"]["other-team"] == {"name": None, "members": None}, d["teams"]
    print("ok  --from-json: a team with no reads has null members, unverified")

    for label, change in (("no check runs", lambda pr: pr.pop("check_runs")),
                          ("no review threads", lambda pr: pr.pop("review_threads")),
                          ("no reviews", lambda pr: pr.pop("reviews")),
                          ("no commit statuses", lambda pr: pr.pop("status"))):
        doc = mcp_doc()
        change(doc["prs"][N])
        r = run_json(tmp, doc)
        assert r.returncode != 0 and r.stderr, f"{label}: must stop, rc={r.returncode}"
        print(f"ok  --from-json: {label} stops the script")


def rest_doc(fx):
    """The gh fixture's REST reads, written into the document's REST form."""
    p = f"repos/{REPO}/pulls/{N}"
    sha = fx[p]["head"]["sha"]
    pending = {str(r["id"]): fx[f"{p}/reviews/{r['id']}/comments"]
               for r in fx[f"{p}/reviews"] if r["state"] == "PENDING"}
    pr = {"pull": fx[p], "reviews": fx[f"{p}/reviews"], "pending_review_comments": pending,
          "ccr_review_threads": fx[f"{p}/ccr/review_threads"], "comments": fx[f"{p}/comments"],
          "check_runs": fx[f"repos/{REPO}/commits/{sha}/check-runs"],
          "status": fx[f"repos/{REPO}/commits/{sha}/status"]}
    if f"repos/{REPO}/issues/{N}/timeline" in fx:
        pr["timeline"] = fx[f"repos/{REPO}/issues/{N}/timeline"]
    return {"viewer": fx["user"]["login"], "prs": {N: pr}}


def rest_route(tmp, gh_out):
    fx = base_fixture()
    fx[f"repos/{REPO}/issues/{N}/timeline"] = []
    r = run_json(tmp, rest_doc(fx))
    assert r.returncode == 0, r.stderr
    strip = lambda rows: [{k: v for k, v in d.items() if k != "readAt"} for d in rows]
    assert strip(json.loads(r.stdout)) == strip(json.loads(gh_out)), \
        f"REST form differs from gh: {r.stdout} vs {gh_out}"
    print("ok  --from-json REST form: the gh route's output exactly, pending review and"
          " requested teams read, threads by the ccr route")
    doc = rest_doc(fx)
    doc["prs"][N]["comments"] = []
    r = run_json(tmp, doc)
    assert r.returncode != 0 and "neither" in r.stderr, r
    print("ok  --from-json REST form: a thread's last comment in no read stops the script")
    doc = rest_doc(fx)
    del doc["prs"][N]["timeline"]
    doc["prs"][N]["pull"] = dict(doc["prs"][N]["pull"], draft=True)
    d = json.loads(run_json(tmp, doc).stdout)[0]
    assert (d["ever_ready"], d["ever_ready_read"]) == (None, False), d
    print("ok  --from-json REST form: a draft with no timeline key is unread, never 'never ready'")

    st = json.load(open(os.path.join(WQ, "state.example.json")))
    st.update(merge=[], prs=[], replies=[], interactive=False)
    paths = {}
    for name, v in (("state", st), ("prs", [{"repo": REPO, "pr": N, "team": "fe-platform"}]),
                    ("notes", [{"repo": REPO, "pr": N}]), ("reads", rest_doc(fx))):
        paths[name] = os.path.join(tmp, f"r-{name}.json")
        with open(paths[name], "w") as f:
            json.dump(v, f)
    out = os.path.join(tmp, "r-index.html")
    args = [sys.executable, "-I", os.path.join(WQ, "refresh.py"), "--state", paths["state"],
            "--prs", paths["prs"], "--notes", paths["notes"], "--owner", OWNER,
            "--from-json", f"{REPO}={paths['reads']}", "--out", out]
    env = {"PATH": "/nonexistent"}  # no gh: a repository with a document reads nothing else
    r = subprocess.run(args + ["--first"], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    built = json.load(open(paths["state"]))
    assert [m["pr"] for m in built["merge"]] == [N] and built["merge"][0]["ready"] is False, built["merge"]
    assert "merge: +['acme/api#101']" in r.stdout and os.path.exists(out), r.stdout
    print("ok  refresh.py: the REST document through mergeq, prsteps, prune and build;"
          " the owner's unsubmitted review keeps the row from Ready")
    r = subprocess.run(args + ["--live", out], capture_output=True, text=True, env=env)
    assert r.returncode == 0 and "merge:" not in r.stdout, (r.stdout, r.stderr)
    print("ok  refresh.py --live: carry.py over the published page; nothing reported changed")
    r = subprocess.run(args[:-4] + ["--out", out, "--first"], capture_output=True, text=True, env=env)
    assert r.returncode != 0 and "refresh stopped at prdata.py" in r.stderr, r
    print("ok  refresh.py: a repository with no document and no gh stops the refresh")
    with open(paths["notes"], "w") as f:
        json.dump([{"repo": REPO, "pr": N}, {"repo": "acme/web", "pr": "7"}], f)
    r = subprocess.run(args + ["--first"], capture_output=True, text=True, env=env)
    assert r.returncode != 0 and "acme/web has no --from-json" in r.stderr, r
    print("ok  refresh.py: with any document, a repository without one stops; gh is never tried")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        gh = os.path.join(tmp, "gh")
        with open(gh, "w") as f:
            f.write(FAKE_GH.replace("#!/usr/bin/env python3 -I", f"#!{sys.executable} -I", 1))
        os.chmod(gh, 0o755)

        out = expect_counts("ccr route, owner's pending review",
                            run_prdata(tmp, base_fixture()))
        json_route(tmp, out)
        rest_route(tmp, out)
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
        import datetime
        def stamp(minutes_ago=0):
            t = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=minutes_ago)
            return t.strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(os.path.join(WQ, "state.example.json")) as f:
            example = json.load(f)
        r = build(example)
        assert r.returncode != 0 and "Re-run refresh.py" in r.stderr and "acme/api#101" in r.stderr, r.stderr
        print("ok  build.py refuses state.example.json as it stands: its PR stamps are not this turn's")
        def restamp(st, minutes_ago):
            st = json.loads(json.dumps(st))
            for x in st.get("merge", []) + st.get("prs", []):
                x["prdataReadAt"] = stamp(minutes_ago)
            for x in st.get("prs", []):
                x["stepsReadAt"] = stamp(minutes_ago)
            return st
        r = build(restamp(example, 2))
        assert r.returncode == 0, r.stderr
        print("ok  build.py builds state.example.json stamped this turn")
        r = build(restamp(example, 120))
        assert r.returncode != 0 and "not read this turn" in r.stderr, r.stderr
        print("ok  build.py refuses a PR list read two hours ago, naming what to re-run")
        noprd = restamp(example, 2)
        del noprd["prs"][0]["prdataReadAt"]
        r = build(noprd)
        assert r.returncode != 0 and "PR item acme/api#102" in r.stderr, r.stderr
        print("ok  build.py refuses a PR item with steps stamped but no prdata stamp")
        for status in ("done", "progress", "yours"):
            bare = {"title": "Work queue", "decisions": [{"id": "d9", "status": status, "options": [],
                                                          "answer": {"choice": "a"}}]}
            r = build(bare)
            assert r.returncode != 0 and "d9" in r.stderr, (status, r.stderr)
            r = build({"title": "Work queue", "decisions": [dict(bare["decisions"][0],
                                                                 outcome="Session [B](https://x) is on it.")]})
            assert r.returncode == 0, (status, r.stderr)
        print("ok  build.py refuses a read answer's card with no outcome: done, in progress or your step")

        # carry.py: the owner's answers and the conductor's own content both survive a rebuild
        def carry(live_state, new_state):
            lp, sp = os.path.join(tmp, "live.html"), os.path.join(tmp, "carry-state.json")
            with open(lp, "w") as f:
                f.write('<script id="state" type="application/json">' + json.dumps(live_state) + "</script>")
            with open(sp, "w") as f:
                json.dump(new_state, f)
            r = subprocess.run([sys.executable, "-I", os.path.join(WQ, "carry.py"), "--live", lp,
                                "--state", sp], capture_output=True, text=True)
            assert r.returncode == 0, r.stderr
            return json.load(open(sp)), r.stderr
        live = {"decisions": [
                    {"id": "d1", "status": "answered", "answer": "a", "options": []},
                    {"id": "d2", "status": "answered", "options": [],
                     "answer": {"option": "a", "messaged": False}},
                    {"id": "d5", "status": "answered", "options": [],
                     "answer": {"option": "b", "messaged": True}},
                    {"id": "d3", "status": "done", "answer": "a", "outcome": "Ruled: 7 days.", "options": []},
                    {"id": "d4", "status": "open", "options": []}],
                "replies": [{"id": "r1", "text": "Held reply one"}, {"id": "r2", "text": "Held reply two"},
                            {"id": "r3", "text": "Posted already"}]}
        new = {"decisions": [{"id": "d1", "status": "open", "options": []},
                             {"id": "d2", "status": "done", "options": [], "outcome": "Acted on B.",
                              "answer": {"option": "b", "messaged": True}},
                             {"id": "d5", "status": "open", "options": []}],
               "replies": [], "closed": ["r3", "d4"]}
        got, err = carry(live, new)
        dec = {d["id"]: d for d in got["decisions"]}
        assert (dec["d1"]["status"], dec["d1"]["answer"]) == ("answered", "a"), dec["d1"]
        print("ok  carry.py keeps an answered decision answered where the rebuild reset it to open")
        assert (dec["d2"]["status"], dec["d2"]["answer"]["option"]) == ("done", "b"), dec["d2"]
        print("ok  carry.py never replaces the ledger's confirmed answer with a pick saved but never sent")
        assert (dec["d5"]["status"], dec["d5"]["answer"]["option"]) == ("answered", "b"), dec["d5"]
        print("ok  carry.py keeps the owner's saved answer over a build that reset its status")
        assert dec["d3"]["outcome"] == "Ruled: 7 days." and "d4" not in dec, dec
        assert [x["id"] for x in got["replies"]] == ["r1", "r2"], got["replies"]
        assert "reply r1" in err and "decision d3" in err and "r3" not in err, err
        print("ok  carry.py carries held replies and decisions the rebuild dropped, names them,"
              " and leaves out what closed lists")
        got, _ = carry({"decisions": [{"id": "e1", "status": "progress", "outcome": "Drafting.", "options": []},
                                      {"id": "e2", "status": "answered", "answer": "a", "options": []}]},
                       {"decisions": [{"id": "e1", "status": "yours", "outcome": "Type go.", "options": []},
                                      {"id": "e2", "status": "progress", "outcome": "Run B.", "answer": "a",
                                       "options": []}]})
        dec = {d["id"]: d for d in got["decisions"]}
        assert (dec["e1"]["status"], dec["e1"]["outcome"]) == ("yours", "Type go."), dec["e1"]
        assert (dec["e2"]["status"], dec["e2"]["outcome"]) == ("progress", "Run B."), dec["e2"]
        print("ok  carry.py never puts a read card back to waiting, and the ledger's state wins between"
              " in progress and your step")
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
                        requested_teams=[], reviewed_by=[], readAt=stamp())
            base.update(kw)
            return base
        prdata = [pr("1", draft=True), pr("12", draft=True), pr("13", draft=True, ever_ready=True), pr("14", draft=True, ever_ready=None, ever_ready_read=False), pr("2", requested_teams=[{"slug": "fe-platform", "name": "FE Platform"}]),
                  pr("9", draft=True, ever_ready=True),
                  pr("10", reviewed_by=["out"], approvals=["out"],
                     teams={"fe-platform": {"name": "FE Platform", "members": ["kim"]}}),
                  pr("11", reviewed_by=["kim"], approvals=["kim"], fail=["e2e"],
                     teams={"fe-platform": {"name": "FE Platform", "members": ["kim"]}}),
                  pr("3", reviewed_by=["rev"], approvals=["rev"]), pr("4", merged=True, state="closed"),
                  pr("5", approvals=["rev"]),
                  pr("6", reviewed_by=["rev", "dana"], approvals=["rev"], changes=["dana"]),
                  pr("8", requested_teams=[{"slug": "fe-platform", "name": "FE Platform"}]),
                  pr("15", requested_teams=None, requested_teams_read=False)]
        prs = [{"repo": REPO, "pr": "1", "team": "payments"},
               {"repo": REPO, "pr": "12", "awaitingPublish": True},
               {"repo": REPO, "pr": "13", "awaitingPublish": True},
               {"repo": REPO, "pr": "14", "awaitingPublish": True},
               {"repo": REPO, "pr": "2", "team": "FE Platform",
                "review": {"href": "https://tracker.example.com/r/2", "label": "Tracker review", "drafts": 2},
                "issues": [{"label": "#9", "href": f"https://github.com/{REPO}/issues/9"}]},
               {"repo": REPO, "pr": "3", "team": "payments",
                "review": {"href": "https://tracker.example.com/r/3", "label": "Tracker review", "drafts": None},
                "issues": [{"k": "tr", "label": "T-1", "href": "https://tracker.example.com/T-1"}]},
               {"repo": REPO, "pr": "4"},
               {"repo": REPO, "pr": "6", "team": "payments"},
               {"repo": REPO, "pr": "8", "team": "fe platform"},
               {"repo": REPO, "pr": "15", "team": "payments"},
               {"repo": REPO, "pr": "9", "team": "payments"},
               {"repo": REPO, "pr": "10", "team": "FE Platform"},
               {"repo": REPO, "pr": "11", "team": "fe-platform"},
               {"repo": REPO, "pr": "5", "session": "https://claude.ai/code/session_X",
                "review": {"href": "https://tracker.example.com/r/5", "label": "Tracker review"}}]
        for name, val in (("prdata.json", prdata), ("prs.json", prs),
                          ("state.json", {"merge": [{"repo": REPO, "pr": "5", "blockers": [],
                                                     "prdataReadAt": stamp()}],
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
                         "13": [False, False, False, False], "14": [False, False, False, False], "2": [True, True, False, False],
                         "3": [True, True, True, False], "6": [True, True, False, False],
                         "8": [True, True, False, False], "15": [True, False, False, False], "9": [False, False, False, False],
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
        assert by["14"]["steps"][0]["label"] == "Draft" and by["14"]["waitsOn"] == "unread"
        assert by["12"]["steps"][0]["label"] == "Mark ready" and by["12"]["waitsOn"] == "owner"
        print("ok  a draft is offered to mark ready only where its run reported it awaiting the owner's publish;"
              " one ever ready stays held even so; one awaiting publish with unread history is not offered and"
              " waits as unread; any other is a plain Draft")
        assert by["15"]["steps"][1]["label"] == "Request payments — check: requests not read"
        print("ok  unread team requests leave Request the owner's step, labelled unverified")
        assert by["10"]["steps"][2] == {"label": "Team approves", "done": False}
        assert by["3"]["steps"][2]["label"] == "Team approves — approved (team not verified)"
        print("ok  where the team's members were read only a member's approval counts; otherwise it is labelled unverified")
        assert all(p["steps"][3]["label"] != "Merge" for p in st["prs"])
        assert by["3"]["steps"][3]["label"] == "Not in the merge notes" and by["3"]["waitsOn"] == "blocked"
        assert by["11"]["steps"][3]["label"] == "Blocked: CI red (e2e)" and by["11"]["waitsOn"] == "blocked"
        print("ok  an approved PR that is not a Ready merge row names its blocker, never Merge")
        assert {k: p["waitsOn"] for k, p in by.items()} == {"1": "draft", "12": "owner", "13": "held", "14": "unread", "2": "team", "3": "blocked",
                                                           "6": "team", "8": "team", "15": "owner", "9": "held",
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
