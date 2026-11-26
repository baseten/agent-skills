"""Build the PR items of the work queue's "Your PRs" section into state.json.

    python3 -I prsteps.py --state state.json --prs prs.json --prdata prdata.json

Run after mergeq.py. prs.json lists each open PR of a run in this ledger, written
from the ledger each build:

    [{"repo": "acme/api", "pr": "101", "team": "payments",
      "session": "https://claude.ai/code/session_...", "awaitingPublish": false,
      "review": {"href": "https://...", "label": "Tracker review", "drafts": 2},
      "issues": [{"label": "#2011", "href": "https://github.com/acme/api/issues/2011"}]}]

An issue link takes kind `iss` unless the entry gives its own `k`, as a tracker's
`tr`.

`team` is the caller's: this skill has no convention for it, so a layer says where
it comes from. `review` is the PR's tracker review page: the conductor's own read of
it where the repository is linked to Linear (rules/linear-mechanics.md, Review
pages), or a layer's. Its label names the tracker account holding the drafts, and
its draft count is shown only where it is an integer that was read; absent or
null, no count is shown or implied.

Each item's steps are read from the sweep's prdata.json, never ticked on the page:

- Mark ready: done when not a draft. A draft that was ever ready is held (draft
  state) and reads "Held in draft". Draft state also holds drafts no timeline
  shows (an instruction, a preference, a convention), so a draft is offered to the
  owner to mark ready only where the entry carries `"awaitingPublish": true`, which
  the conductor sets from the run's own report that the draft awaits the owner's
  publish, and whose ready history was read (prdata.py's `ever_ready_read`); one
  awaiting publish whose history is unread waits as "unread"; any other draft
  reads "Draft" with no owner step.
- Request <team>, where prdata.py could not read the requested teams and no one
  has reviewed: not done, labelled "check: requests not read".
- Request <team>: done when the team is requested — `team` matched, ignoring case,
  against a team's slug or name — or a person other than the author has reviewed.
- Team approves: done on an approval from a member where the team's membership was
  read; where it was not, any person's approval, labelled "approved (team not
  verified)". While any person's latest review requests changes it reads "Changes
  requested" and is not done.
- The last step is never "Merge": a merge row reading Ready (mergeq.py) is the only
  merge offered, and this PR is not a merge row, so the step names what keeps it
  out — CI, open threads, the owner's unsubmitted review, or not being in the merge
  notes.

`waitsOn` is "owner" where the next step is the owner's (mark ready, request the
team), "team" where it is the team's approval or a change request, "held" for a
held draft, "draft" for one not offered, and "blocked" past approval. Each item is stamped `stepsReadAt` (UTC),
which build.py requires: the stamp shows prsteps.py filled the steps, not that
nobody edited them after, which the contract forbids and no check can see. A
merged PR leaves the section for "Done recently"; a closed one leaves it too. A PR
already a merge row is not listed twice: its row takes the links. A PR with no
prdata stops the script, as mergeq.py does.
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


def blocker(d):
    if d.get("fail"):
        return "Blocked: CI red (" + ", ".join(d["fail"]) + ")"
    if d.get("pending"):
        return "Blocked: CI running"
    if d.get("unresolved"):
        return f'Blocked: {d["unresolved"]} open thread{"" if d["unresolved"] == 1 else "s"}'
    if d.get("owner_pending_drafts", 0) is None:
        return "Blocked: your unsubmitted review is unread"
    if d.get("owner_pending_review") is not None:
        return "Blocked: your unsubmitted review"
    return "Not in the merge notes"


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

    def named(slug, name):
        return wanted and wanted in (str(slug or "").lower(), str(name or "").lower())
    requested = any(named(t.get("slug"), t.get("name")) for t in d.get("requested_teams") or [])
    # unread requests (the MCP route): the step stays the owner's, labelled unverified
    unread_requests = d.get("requested_teams_read") is False and not d.get("reviewed_by")
    members = next((t.get("members") for s, t in (d.get("teams") or {}).items()
                    if named(s, t.get("name")) and t.get("members") is not None), None)
    changes = bool(d.get("changes"))
    approvers = d["approvals"] if members is None else [u for u in d["approvals"] if u in members]
    held = bool(d["draft"] and d.get("ever_ready"))
    # fail closed: a hold can sit where no timeline shows it, so only a draft its run
    # reported as awaiting the owner's publish is offered to mark ready
    # and only where its ready history was read: an unread one may be held
    offered = bool(d["draft"] and not held and d.get("ever_ready_read") is not False
                   and e.get("awaitingPublish") is True)
    draft_label = "Held in draft" if held else "Mark ready" if offered or not d["draft"] else "Draft"
    if changes:
        approve = {"label": "Changes requested", "done": False}
    elif approvers and members is None:
        approve = {"label": "Team approves — approved (team not verified)", "done": True}
    else:
        approve = {"label": "Team approves", "done": bool(approvers)}
    steps = [
        {"label": draft_label, "done": not d["draft"]},
        {"label": (f"Request {team}" if team else "Request review")
                  + (" — check: requests not read" if unread_requests else ""),
         "done": bool(requested or d.get("reviewed_by"))},
        approve,
        # never "Merge" here: a merge row reading Ready is the only merge to offer, and
        # this PR is not one, so its last step names what keeps it out
        {"label": blocker(d), "done": False},
    ]
    nxt = next(i for i, s in enumerate(steps) if not s["done"])
    unread_draft = bool(d["draft"] and not held and d.get("ever_ready_read") is False
                        and e.get("awaitingPublish") is True)
    waits = ("held" if held else "unread" if unread_draft else "draft" if d["draft"] and not offered
             else "team" if nxt == 2 else "blocked" if nxt == 3 else "owner")
    items.append(dict(repo=d["repo"], pr=d["pr"], url=d["url"], title=d["title"],
                      links=lk, noIssue=not e.get("issues"), steps=steps,
                      waitsOn=waits, stepsReadAt=read_at, prdataReadAt=d.get("readAt")))
st["prs"] = items
st["doneRecent"] = done_recent
json.dump(st, open(a.state, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
if missing:
    raise SystemExit("no prdata for " + ", ".join(missing) + ": read them in the sweep first")
