"""Build the PR items of the work queue's "Your PRs" section into state.json.

    python3 -I prsteps.py --state state.json --prs prs.json --prdata prdata.json

Run after mergeq.py. prs.json lists each open PR of a run in this ledger, written
from the ledger each build:

    [{"repo": "acme/api", "pr": "101", "team": "payments",
      "session": "https://claude.ai/code/session_...",
      "review": {"href": "https://...", "label": "Tracker review", "drafts": 2},
      "issues": [{"label": "#2011", "href": "https://github.com/acme/api/issues/2011"}]}]

An issue link takes kind `iss` unless the entry gives its own `k`, as a tracker's
`tr`.

`team` and `review` are the caller's: this skill has no convention for either, so a
layer says where they come from. A review link's draft count is shown only where
it is an integer the caller read; absent or null, no count is shown or implied.

Each item's steps are read from the sweep's prdata.json, never ticked on the page:
Mark ready (not a draft), Request <team> (the team requested — `team` matched,
ignoring case, against a requested team's slug or name — or a person other than the
author has reviewed), Team approves (an approval from a person, and no person's
latest review requesting changes; while one does, the step reads "Changes
requested"), Merge (merged). Each item is stamped `stepsReadAt` (UTC), which
build.py requires: the stamp shows prsteps.py filled the steps, not that nobody
edited them after, which the contract forbids and no check can see. `waitsOn` is
"team" where the next step is the team's, else "owner". A merged PR leaves the
section for "Done recently"; a closed one leaves it too. A PR already a merge row
is not listed twice: its row takes the links. A PR with no prdata stops the
script, as mergeq.py does.
"""
import argparse
import datetime
import json

ap = argparse.ArgumentParser()
ap.add_argument("--state", required=True)
ap.add_argument("--prs", required=True)
ap.add_argument("--prdata", required=True)
a = ap.parse_args()

data = {(d["repo"], d["pr"]): d for d in json.load(open(a.prdata, encoding="utf-8"))}
st = json.load(open(a.state, encoding="utf-8"))
rows = {(m["repo"], str(m["pr"])): m for m in st.get("merge", [])}
done_recent = list(st.get("doneRecent", []))
read_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def links(e, d):
    out = []
    if e.get("session"):
        out.append({"k": "ses", "label": "Run session", "href": e["session"]})
    out.append({"k": "gh", "label": "#" + d["pr"], "href": d["url"]})
    rv = e.get("review")
    if rv and rv.get("href"):
        label = rv.get("label") or "Review"
        n = rv.get("drafts")
        if isinstance(n, int) and not isinstance(n, bool):
            label += f" · {n} draft{'' if n == 1 else 's'}"
        out.append({"k": "rv", "label": label, "href": rv["href"]})
    for i in e.get("issues") or []:
        out.append({"k": i.get("k") or "iss", "label": i["label"], "href": i["href"]})
    return out


items, missing = [], []
for e in json.load(open(a.prs, encoding="utf-8")):
    key = (e["repo"], str(e["pr"]))
    d = data.get(key)
    if d is None:
        missing.append(f"{key[0]}#{key[1]}")
        continue
    if d["merged"] or d["state"] != "open":
        verb = "merged" if d["merged"] else "closed"
        line = f'[#{d["pr"]}]({d["url"]}) {verb}: {d["title"]}'
        if line not in done_recent:
            done_recent.insert(0, line)
        continue
    lk = links(e, d)
    if key in rows:
        rows[key]["links"], rows[key]["noIssue"] = lk, not e.get("issues")
        continue
    team = e.get("team")
    wanted = (team or "").strip().lower()
    requested = any(wanted and wanted in (str(t.get("slug") or "").lower(), str(t.get("name") or "").lower())
                    for t in d.get("requested_teams") or [])
    changes = bool(d.get("changes"))
    steps = [
        {"label": "Mark ready", "done": not d["draft"]},
        {"label": f"Request {team}" if team else "Request review",
         "done": bool(requested or d.get("reviewed_by"))},
        {"label": "Changes requested" if changes else "Team approves",
         "done": bool(d["approvals"]) and not changes},
        {"label": "Merge", "done": False},
    ]
    nxt = next(i for i, s in enumerate(steps) if not s["done"])
    items.append(dict(repo=d["repo"], pr=d["pr"], url=d["url"], title=d["title"],
                      links=lk, noIssue=not e.get("issues"), steps=steps,
                      waitsOn="team" if nxt == 2 else "owner", stepsReadAt=read_at))
st["prs"] = items
st["doneRecent"] = done_recent
json.dump(st, open(a.state, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
if missing:
    raise SystemExit("no prdata for " + ", ".join(missing) + ": read them in the sweep first")
