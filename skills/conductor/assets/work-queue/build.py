"""Render the work queue page: template.html with the state block filled in.

    python3 -I build.py --state state.json --template template.html --out index.html

The page is the template plus one state block; the page script regenerates the
whole document from that state and never serialises the DOM. `<` is escaped so
no state value can close the script element. An interactive state whose open
decision has an option with no `ruling` is refused: its answer could not be
recorded. So is a decision `done`, `progress` or `yours` with no `outcome`: the
card would show no record, no session and no next step. So is a "Your PRs" item without prsteps.py's `stepsReadAt` stamp, or
whose steps do not each carry a `done`: the stamp shows prsteps.py filled them, and
cannot show that nobody edited them after.

**A state built from an earlier turn is refused.** Every merge row and "Your PRs"
item carries `prdataReadAt`, the time prdata.py read that PR, copied by mergeq.py
and prsteps.py; a PR item carries `stepsReadAt` too. Each must be within
FRESH_MINUTES of this build's own clock. A stamp that is missing or older means the
PR list was reused rather than read this turn: re-run refresh.py, which reads the
PRs again and builds. The window is no proof the rest of the state is this
turn's (conductor, work-queue.md, *Building it*), only that the PR list is.
**An item that links a pull request and whose `what` opens by asking to merge it,
mark it ready or request review is warned of**, not refused: it is how a hand-patched state shows a PR's
steps, which belong in "Your PRs" from prsteps.py, but an item can link a PR for
another reason.
"""
import argparse
import datetime
import html
import json
import re
import sys

FRESH_MINUTES = 30

ap = argparse.ArgumentParser()
ap.add_argument("--state", required=True)
ap.add_argument("--template", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()

with open(a.state, encoding="utf-8") as f:
    st = json.load(f)
with open(a.template, encoding="utf-8") as f:
    t = f.read()
if st.get("interactive") is True:
    # an answer records the option's ruling text: a card without one cannot be answered
    unruled = [f'{d.get("id")}/{o.get("id")}' for d in st.get("decisions") or []
               if d.get("status") == "open" for o in d.get("options") or []
               if not str(o.get("ruling") or "").strip()]
    if unruled:
        raise SystemExit("refused: on an interactive page every option of an open decision "
                         "carries its ruling (work-queue.md, Building it); missing on "
                         + ", ".join(unruled))
# an answer the conductor has read is done, in progress or the owner's step, and says which
# (work-queue.md, Answers, step 4): a card in one of those states with no outcome is refused
bare = [str(d.get("id")) for d in st.get("decisions") or []
        if d.get("status") in ("done", "progress", "yours") and not str(d.get("outcome") or "").strip()]
if bare:
    raise SystemExit("refused: a decision done, in progress or the owner's step carries its "
                     "outcome (work-queue.md, Answers); missing on " + ", ".join(bare))
# a PR's steps are filled by prsteps.py, which stamps the item. The stamp catches steps
# it never filled; a hand edit after it is forbidden by the contract, not seen here.
unread = [f'{p.get("repo")}#{p.get("pr")}' for p in st.get("prs") or []
          if not p.get("stepsReadAt") or not p.get("steps")
          or any(not isinstance(s.get("done"), bool) for s in p["steps"])]
if unread:
    raise SystemExit("PR items whose steps were not read by prsteps.py: " + ", ".join(unread))
# a PR's merge or review step belongs in "Your PRs", through prsteps.py; an item that
# links a pull request and asks for one of those steps is likely a hand-written copy
PR_STEP = re.compile(r"^\W*(merge|mark\b.*\bready|request\b.*\breview)\b", re.I)
hand = [str(i.get("id")) for i in st.get("items") or []
        if any(re.search(r"/pull/\d+", str(l.get("href") or "")) for l in i.get("links") or [])
        and PR_STEP.search(str(i.get("what") or ""))]
if hand:
    print("warning: items that link a PR and ask to merge, mark it ready or request review: "
          + ", ".join(hand) + ". A PR's steps come from prsteps.py into \"Your PRs\" "
          "(work-queue.md, Building it); run refresh.py rather than writing them as items",
          file=sys.stderr)
now = datetime.datetime.now(datetime.timezone.utc)


def fresh(stamp):
    try:
        t = datetime.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=datetime.timezone.utc)
    except (TypeError, ValueError):
        return False
    return datetime.timedelta(minutes=-5) <= now - t <= datetime.timedelta(minutes=FRESH_MINUTES)


stale = [f'{kind} {x.get("repo")}#{x.get("pr")}'
         for kind, rows, keys in (("merge row", st.get("merge") or [], ("prdataReadAt",)),
                                  ("PR item", st.get("prs") or [], ("prdataReadAt", "stepsReadAt")))
         for x in rows if not all(fresh(x.get(k)) for k in keys)]
if stale:
    raise SystemExit(f"refused: the PR list was not read this turn (no prdata.py stamp within "
                     f"{FRESH_MINUTES} minutes): " + ", ".join(stale) + ". Re-run refresh.py, which "
                     "reads the PRs again and builds; never patch a state.json carried from "
                     "an earlier turn")
for token in ("__STATE__", "<title>Work queue</title>"):
    if t.count(token) != 1:
        raise SystemExit(f"template must hold {token!r} exactly once")
js = json.dumps(st, ensure_ascii=False).replace("<", "\\u003c")
title = html.escape(str(st.get("title") or "Work queue"))
t = t.replace("<title>Work queue</title>", f"<title>{title}</title>")
with open(a.out, "w", encoding="utf-8") as f:
    f.write(t.replace("__STATE__", js))
