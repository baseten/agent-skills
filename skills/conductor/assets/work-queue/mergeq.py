"""Build the merge rows of the work queue's "Your PRs" section into state.json.

    python3 -I mergeq.py --state state.json --notes merge-notes.json --prdata prdata.json \
        [--pending-blocker 'REGEX=Text shown as a blocker'] ...

Reads the sweep's prdata.json, never GitHub. A row is listed only while its PR is
open, approved by a person and has no outstanding change request. `after` and
the blockers come from the owner's merge notes; only open threads block, and
threads prdata.py read as answered, or as fixed and needing a reply, show as counts; `--pending-blocker` turns a
pending check whose name matches REGEX into a named blocker, for a check that
waits on a person rather than on CI. The owner's own unsubmitted review, which
prdata.py reads as owner_pending_review, is always a blocker, never part of a Ready
row; where prdata.py could not read it (owner_pending_drafts null), the row says it
is unread, a blocker too. Nothing here decides a merge: the owner does.
"""
import argparse
import json
import re

ap = argparse.ArgumentParser()
ap.add_argument("--state", required=True)
ap.add_argument("--notes", required=True)
ap.add_argument("--prdata", required=True)
ap.add_argument("--pending-blocker", action="append", default=[])
a = ap.parse_args()

rules = []
for spec in a.pending_blocker:
    pattern, _, text = spec.partition("=")
    rules.append((re.compile(pattern), text or pattern))

notes = json.load(open(a.notes, encoding="utf-8"))
data = {(d["repo"], d["pr"]): d for d in json.load(open(a.prdata, encoding="utf-8"))}
st = json.load(open(a.state, encoding="utf-8"))
rows, missing = [], []
for n in notes:
    d = data.get((n["repo"], str(n["pr"])))
    if d is None:
        missing.append(f'{n["repo"]}#{n["pr"]}')
        continue
    if d["merged"] or d["state"] != "open" or d["changes"] or not d["approvals"]:
        continue
    ci = "red" if d["fail"] else "running" if d["pending"] else "green" if d["checks"] else "none"
    blockers, auto = list(n.get("blockers", [])), []
    if d["unresolved"]:
        auto.append("threads")
    if d.get("owner_pending_drafts", 0) is None:
        blockers.insert(0, "Your unsubmitted review: unread (gh is not your account)")
    elif d.get("owner_pending_review") is not None:
        k = d.get("owner_pending_drafts", 0)
        blockers.insert(0, f"Your unsubmitted review: {k} draft{'' if k == 1 else 's'}")
    if ci == "red":
        blockers.insert(0, "CI red: " + ", ".join(d["fail"]))
    elif ci == "running":
        named = [text for rx, text in rules if all(rx.search(p) for p in d["pending"])]
        if named:
            blockers.insert(0, named[0])
        else:
            auto.append("ci")
    elif ci == "none":
        auto.append("ci")
    rows.append(dict(repo=d["repo"], pr=d["pr"], url=d["url"], title=d["title"], sha=d["sha"][:8],
                     approvals=d["approvals"], unresolved=d["unresolved"],
                     answered=d.get("answered", 0), needs_reply=d.get("needs_reply", 0), ci=ci,
                     after=n.get("after"), group=n.get("group"), blockers=blockers,
                     auto=auto, note=n.get("note", "")))
st["merge"] = rows
json.dump(st, open(a.state, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
if missing:
    raise SystemExit("no prdata for " + ", ".join(missing) + ": read them in the sweep first")
