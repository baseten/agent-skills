"""Read one repository's PR facts from GitHub for the work queue's merge section.

    python3 -I prdata.py --repo owner/name --owner LOGIN 101 102 > prdata.json

Run as part of the sweep: its output is that sweep's snapshot of these PRs
(conductor, *The status snapshot*), and mergeq.py renders from it rather than
reading GitHub again. Any read that fails stops the script: a count it could not
read is never written as zero.

An unresolved thread counts as answered, not open, only where its last comment's
author login is the --owner login and the comment holds no "?". An open thread that
is outdated is also counted as fixed, needing the owner's reply. Authorship is the
login, never a footer or the text. This is how the work queue reads a PR; it never
resolves a thread and is not the merge gate's reading.
"""
import argparse
import json
import subprocess
import sys

THREADS = """query($owner:String!,$name:String!,$n:Int!,$endCursor:String){
 repository(owner:$owner,name:$name){pullRequest(number:$n){
  reviewThreads(first:100,after:$endCursor){nodes{isResolved isOutdated
   comments(last:1){nodes{author{login} body}}}
   pageInfo{hasNextPage endCursor}}}}}"""


def gh(*args):
    r = subprocess.run(["gh", "api", *args], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"gh api {' '.join(args[:1])} failed: {r.stderr.strip()}")
    return json.loads(r.stdout)


def pages(path):
    return gh("--paginate", "--slurp", path)


ap = argparse.ArgumentParser()
ap.add_argument("--repo", required=True, help="owner/name")
ap.add_argument("--owner", required=True, help="the owner's account login")
ap.add_argument("prs", nargs="+")
a = ap.parse_args()
owner, name = a.repo.split("/", 1)

out = []
for n in a.prs:
    p = gh(f"repos/{a.repo}/pulls/{n}")
    sha = p["head"]["sha"]
    latest = {}
    for page in pages(f"repos/{a.repo}/pulls/{n}/reviews?per_page=100"):
        for r in page:  # chronological, so the last state per reviewer wins
            if r["state"] in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED"):
                latest[r["user"]["login"]] = (r["state"], r["user"].get("type"))
    approvals = [u for u, (s, kind) in latest.items() if s == "APPROVED" and kind != "Bot"]
    changes = [u for u, (s, _) in latest.items() if s == "CHANGES_REQUESTED"]
    unresolved = answered = needs_reply = 0
    for page in gh("graphql", "--paginate", "--slurp", "-f", f"query={THREADS}",
                   "-f", f"owner={owner}", "-f", f"name={name}", "-F", f"n={n}"):
        nodes = page["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]
        for t in nodes:
            if t["isResolved"]:
                continue
            last = (t["comments"]["nodes"] or [None])[-1]
            login = ((last or {}).get("author") or {}).get("login")
            if login == a.owner and "?" not in last["body"]:
                answered += 1
            else:
                unresolved += 1
                needs_reply += t["isOutdated"]
    runs = [r for page in pages(f"repos/{a.repo}/commits/{sha}/check-runs?per_page=100")
            for r in page["check_runs"]]
    statuses = [s for page in pages(f"repos/{a.repo}/commits/{sha}/status?per_page=100")
                for s in page["statuses"]]
    fail = sorted({r["name"] for r in runs
                   if r["conclusion"] in ("failure", "timed_out", "cancelled", "action_required")}
                  | {s["context"] for s in statuses if s["state"] in ("failure", "error")})
    pending = sorted({r["name"] for r in runs if r["status"] != "completed"}
                     | {s["context"] for s in statuses if s["state"] == "pending"})
    out.append(dict(repo=a.repo, pr=str(n), url=p["html_url"], title=p["title"],
                    sha=sha, base=p["base"]["ref"], draft=p["draft"], state=p["state"],
                    merged=p["merged"], mergeable=p.get("mergeable_state"),
                    approvals=approvals, changes=changes, unresolved=unresolved, answered=answered,
                    needs_reply=needs_reply,
                    checks=len(runs) + len(statuses), fail=fail, pending=pending))
print(json.dumps(out, indent=1))
