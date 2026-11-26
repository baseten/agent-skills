"""One work-queue refresh: the whole pipeline in its order, from one command.

    python3 -I refresh.py --state state.json --prs prs.json --notes merge-notes.json \
        --owner LOGIN [--team SLUG] [--from-json owner/name=reads.json] \
        [--pending-blocker 'REGEX=Text'] (--live live.html | --first) --out index.html

Run it after writing state.json from the turn's snapshot, prs.json and the merge
notes from the ledger (conductor, work-queue.md, *Building it*), and reading the
live page (--live: the file the Artifact tool's `read` saved) or, where none is
published yet, --first. It reads no watch listing and publishes nothing: choosing
the page's row (*Which page*) and the publish stay the session's.

The PRs it reads are exactly the ones the build shows: each in prs.json, each the
merge notes name, and each held reply's in state.json, grouped by repository —
bar a held reply carry.py brings back from the live page, which it names for the
ledger. Repositories are read through `gh api`, or, with any --from-json, each from
its document (prdata.py's `JsonSource`: the MCP or REST route) and never through
`gh`: a session that may not use `gh` passes one per repository, and one missing
stops the refresh. Then, over that one read: prdata.py -> mergeq.py -> prsteps.py
-> prune.py -> carry.py (unless --first) -> build.py. Any step that fails stops
the refresh, naming it, and no page is written; state.json may be part-rebuilt,
and a re-run rebuilds it.

It prints the page's path and what changed against the live page: the merge rows,
PR items, decisions, replies, items and sessions added or dropped, and the merge
rows now Ready. carry.py's own lines (what it carried back) pass through on stderr;
each is read back into the ledger before the next build.
"""
import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def run(step, *args, stdout=None):
    r = subprocess.run([sys.executable, "-I", os.path.join(HERE, step), *args],
                       stdout=stdout if stdout is not None else subprocess.PIPE, text=True)
    if r.returncode != 0:
        sys.exit(f"refresh stopped at {step} (exit {r.returncode}); nothing was built")
    return r.stdout


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def live_state(path):
    page = open(path, encoding="utf-8").read()
    m = re.search(r'<script id="state" type="application/json">(.*?)</script>', page, re.S)
    return json.loads(m.group(1)) if m else {}


def ids(st, key):
    out = set()
    for x in st.get(key) or []:
        if isinstance(x, dict):
            out.add(str(x.get("id") or f'{x.get("repo")}#{x.get("pr")}'))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--prs", required=True)
    ap.add_argument("--notes", required=True)
    ap.add_argument("--owner", required=True)
    ap.add_argument("--team", action="append", default=[])
    ap.add_argument("--from-json", action="append", default=[], metavar="REPO=FILE")
    ap.add_argument("--pending-blocker", action="append", default=[])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--live", help="the live page as the Artifact tool's read saved it")
    g.add_argument("--first", action="store_true", help="no page is published yet")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    docs = {}
    for spec in a.from_json:
        repo, sep, path = spec.partition("=")
        if not sep or "/" not in repo:
            ap.error(f"--from-json takes owner/name=FILE, not {spec!r}")
        docs[repo] = path
    by_repo = {}
    for e in load(a.prs) + load(a.notes) + (load(a.state).get("replies") or []):
        by_repo.setdefault(e["repo"], set()).add(str(e["pr"]))

    # read before build.py runs: --out may name the live page itself
    old = live_state(a.live) if a.live else {}
    work = os.path.dirname(os.path.abspath(a.state))
    rows = []
    for repo in sorted(by_repo):
        args = ["--repo", repo, "--owner", a.owner]
        for t in a.team:
            args += ["--team", t]
        if repo in docs:
            args += ["--from-json", docs[repo]]
        elif docs:
            sys.exit(f"refresh stopped: {repo} has no --from-json document, and with any "
                     "document no repository is read through gh; nothing was built")
        rows += json.loads(run("prdata.py", *args, *sorted(by_repo[repo], key=int)))
    prdata = os.path.join(work, "prdata.json")
    with open(prdata, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=1)

    mq = ["--state", a.state, "--notes", a.notes, "--prdata", prdata]
    for b in a.pending_blocker:
        mq += ["--pending-blocker", b]
    run("mergeq.py", *mq)
    run("prsteps.py", "--state", a.state, "--prs", a.prs, "--prdata", prdata)
    run("prune.py", "--state", a.state, "--prdata", prdata)
    if a.live:
        run("carry.py", "--live", a.live, "--state", a.state)
    run("build.py", "--state", a.state, "--template", os.path.join(HERE, "template.html"),
        "--out", a.out)

    new = load(a.state)
    print(f"page: {os.path.abspath(a.out)}")
    print(f"read: {len(rows)} PRs in {len(by_repo)} repositories"
          + (f", {', '.join(sorted(docs))} from JSON" if docs else ""))
    for key in ("merge", "prs", "decisions", "replies", "items", "sessions"):
        added, dropped = ids(new, key) - ids(old, key), ids(old, key) - ids(new, key)
        if added or dropped:
            print(f"{key}: +{sorted(added)} -{sorted(dropped)}")
    was = {f'{x.get("repo")}#{x.get("pr")}' for x in old.get("merge") or [] if x.get("ready")}
    now = {f'{x.get("repo")}#{x.get("pr")}' for x in new.get("merge") or [] if x.get("ready")}
    if now != was:
        print(f"ready to merge: {sorted(now)} (was {sorted(was)})")


if __name__ == "__main__":
    main()
