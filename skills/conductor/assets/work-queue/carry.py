"""Carry the owner's marks from the live page into the state about to be published.

    python3 -I carry.py --live live.html --state state.json

Run before every publish, on the version just read back from the artifact (or the
one a refused publish handed over), so a republish never drops what the owner
saved from inside the page. It carries marks only: a decision the live page shows
answered or done keeps that status, answer and outcome; a reply or item keeps its
`done`, as does a session row the build wrote no `done` for. It never turns a mark into a ruling — conductor, work-queue.md, *Answers*.
"""
import argparse
import json
import re

ap = argparse.ArgumentParser()
ap.add_argument("--live", required=True)
ap.add_argument("--state", required=True)
a = ap.parse_args()

page = open(a.live, encoding="utf-8").read()
m = re.search(r'<script id="state" type="application/json">(.*?)</script>', page, re.S)
if not m:
    raise SystemExit("no state block in the live page")
live = json.loads(m.group(1))
st = json.load(open(a.state, encoding="utf-8"))

ORDER = {"open": 0, "answered": 1, "done": 2}
by_id = {d["id"]: d for d in live.get("decisions", [])}
for d in st.get("decisions", []):
    old = by_id.get(d["id"])
    if old and ORDER.get(old.get("status"), 0) > ORDER.get(d.get("status"), 0):
        for k in ("status", "answer", "doneAt", "outcome"):
            if k in old:
                d[k] = old[k]
for kind in ("replies", "items", "sessions"):
    marks = {x["id"]: x for x in live.get(kind, [])}
    for x in st.get(kind, []):
        old = marks.get(x["id"])
        if old and "done" in old and "done" not in x:
            x["done"], x["doneAt"] = old["done"], old.get("doneAt")
json.dump(st, open(a.state, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
