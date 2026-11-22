"""Carry the owner's marks from the live page into the state about to be published.

    python3 -I carry.py --live live.html --state state.json

Run before every publish, on the version just read back from the artifact (or the
one a refused publish handed over), so a republish never drops what the owner
saved from inside the page, nor what the conductor put there in an earlier turn.

- **The owner's marks**: a decision the live page shows answered or done keeps
  that status and outcome; a reply or item keeps its `done`, as does a session row
  the build wrote no `done` for.
- **The owner's saved answer wins over the build's status**: where the live page
  carries an answer the build lacks, it is kept and the decision is at least
  answered. An answer the build carries, read from the ledger, is never replaced:
  a pick saved without reaching the conductor may since have been confirmed
  otherwise.
- **The conductor's own content**: a held reply or a decision the live page carries
  and the build lacks is carried into it, and named on stderr, unless the state
  lists its id under `closed` — the ids the ledger shows finished (a reply posted,
  a decision ruled and acted on). A build that drops one without saying why has
  lost it, as a build from memory does; carrying it keeps it on the page, and the
  message says to read it back into the ledger.

It never turns a mark into a ruling — conductor, work-queue.md, *Answers*.
"""
import argparse
import json
import re
import sys

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
closed = {str(i) for i in st.get("closed") or []}
by_id = {d["id"]: d for d in live.get("decisions", [])}
for d in st.get("decisions", []):
    old = by_id.get(d["id"])
    if not old:
        continue
    if ORDER.get(old.get("status"), 0) > ORDER.get(d.get("status"), 0):
        for k in ("status", "answer", "doneAt", "outcome"):
            if k in old:
                d[k] = old[k]
    if old.get("answer") is not None and d.get("answer") is None:
        # an answer the page saved wins over the build's status, never over an answer
        # the build read from the ledger: a pick saved but never sent may since have
        # been confirmed otherwise, at an owner pass
        d["answer"] = old["answer"]
        if ORDER.get(d.get("status"), 0) < ORDER["answered"]:
            d["status"] = "answered"
    for k in ("outcome", "doneAt"):
        if k in old and k not in d:
            d[k] = old[k]
carried = []
for kind, label in (("decisions", "decision"), ("replies", "reply")):
    have = {str(x["id"]) for x in st.get(kind, [])}
    for x in live.get(kind, []):
        if str(x["id"]) not in have and str(x["id"]) not in closed:
            st.setdefault(kind, []).append(x)
            carried.append(f"{label} {x['id']}")
if carried:
    print("carried from the live page, absent from this build: " + ", ".join(carried)
          + ". Read each back into the ledger, or list its id under closed where the ledger "
          "shows it finished.", file=sys.stderr)
for kind in ("replies", "items", "sessions"):
    marks = {x["id"]: x for x in live.get(kind, [])}
    for x in st.get(kind, []):
        old = marks.get(x["id"])
        if old and "done" in old and "done" not in x:
            x["done"], x["doneAt"] = old["done"], old.get("doneAt")
json.dump(st, open(a.state, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
