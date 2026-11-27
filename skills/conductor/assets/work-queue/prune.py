"""Drop drafts the owner marked posted once their PR has merged or closed.

    python3 -I prune.py --state state.json --prdata prdata.json

Reads the sweep's prdata.json for each PR-bound draft's PR: a reply in a review
thread or a PR body edit (drafts.py). An unposted draft stays, merged PR or not:
the person who asked is still unanswered. A draft whose PR the sweep did not read
stays too: an unread PR is unknown, never merged or closed, as on a draft
refresh.py stamped `prUnread`. **A draft bound to no PR — Notion, Linear, Slack, any other site — is
never pruned on a PR's state**: it leaves the page only when the build omits it
and lists its id under `closed`, once its posted tick is read back into the ledger
(conductor, work-queue.md, *Drafts to post*). A draft whose id `closed` lists is
dropped whatever its kind, since the ledger shows it finished. A state carrying
only `replies` is read as review-thread drafts and written back as `drafts`.
"""
import argparse
import importlib.util
import json
import os

_spec = importlib.util.spec_from_file_location(
    "wq_drafts", os.path.join(os.path.dirname(os.path.abspath(__file__)), "drafts.py"))
drafts = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(drafts)

ap = argparse.ArgumentParser()
ap.add_argument("--state", required=True)
ap.add_argument("--prdata", required=True)
a = ap.parse_args()

st = drafts.normalise(json.load(open(a.state, encoding="utf-8")))
prs = {(d["repo"], d["pr"]): d for d in json.load(open(a.prdata, encoding="utf-8"))}
finished = {str(i) for i in st.get("closed") or []}
keep, gone = [], []
for r in st["drafts"]:
    if str(r.get("id")) in finished:
        gone.append(r)
        continue
    d = prs.get((r.get("repo"), str(r.get("pr")))) if drafts.pr_bound(r) else None
    closed = d is not None and (d["merged"] or d["state"] != "open")
    (gone if r.get("done") and closed else keep).append(r)
st["drafts"] = keep
json.dump(st, open(a.state, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"pruned {len(gone)}, kept {len(keep)}")
