"""Drop held replies the owner marked posted once their PR has merged or closed.

    python3 -I prune.py --state state.json --prdata prdata.json

Reads the sweep's prdata.json for each reply's PR. An unposted reply stays, merged
PR or not: the person who asked is still unanswered. A reply whose PR the sweep did
not read stays too.
"""
import argparse
import json

ap = argparse.ArgumentParser()
ap.add_argument("--state", required=True)
ap.add_argument("--prdata", required=True)
a = ap.parse_args()

st = json.load(open(a.state, encoding="utf-8"))
prs = {(d["repo"], d["pr"]): d for d in json.load(open(a.prdata, encoding="utf-8"))}
keep, gone = [], []
for r in st.get("replies", []):
    d = prs.get((r["repo"], str(r["pr"])))
    closed = d is not None and (d["merged"] or d["state"] != "open")
    (gone if r.get("done") and closed else keep).append(r)
st["replies"] = keep
json.dump(st, open(a.state, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"pruned {len(gone)}, kept {len(keep)}")
