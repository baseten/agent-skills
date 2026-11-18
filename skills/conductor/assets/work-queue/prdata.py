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

Threads are read over GraphQL where it answers. Where it is refused with HTTP 403,
as it is from a Claude Code cloud session, they are read from the REST route
pulls/{n}/ccr/review_threads, with one REST read of each unresolved thread's last
comment, taken from one paginated read of pulls/{n}/comments; both routes feed
the same rule above. Where neither answers, the script stops. It only reads: the
ccr routes that resolve or unresolve a thread are never called, since the work
queue never resolves one.

A review still PENDING is visible only to the account that wrote it, and its
comments are absent from pulls/{n}/comments and 404 on pulls/comments/{id}. So
every PENDING review the reviews list returns has its comments read from
pulls/{n}/reviews/{id}/comments, before any single-comment read, and the GraphQL
route reads each comment's state. A thread whose last comment is in the owner's
own pending review is held by the owner: counted neither unresolved nor answered.
The owner's pending review is emitted as owner_pending_drafts (its comment count,
0 for none) and owner_pending_review (its id, or null). Where `gh api user` is not
the --owner login, or cannot be read, the owner's pending review cannot be seen:
owner_pending_drafts is null and owner_pending_read false, never 0. A pending last
comment by any other login counts as unresolved. Every other failed read still stops the
script.
"""
import argparse
import json
import subprocess
import sys

THREADS = """query($owner:String!,$name:String!,$n:Int!,$endCursor:String){
 repository(owner:$owner,name:$name){pullRequest(number:$n){
  reviewThreads(first:100,after:$endCursor){nodes{isResolved isOutdated
   comments(last:1){nodes{author{login} body state}}}
   pageInfo{hasNextPage endCursor}}}}}"""


class GhError(Exception):
    pass


def gh_try(*args):
    r = subprocess.run(["gh", "api", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise GhError(f"gh api {' '.join(args[:1])} failed: {(r.stderr or r.stdout).strip()}")
    return json.loads(r.stdout)


def gh(*args):
    try:
        return gh_try(*args)
    except GhError as e:
        sys.exit(str(e))


def pages(path):
    return gh("--paginate", "--slurp", path)


def threads_graphql(repo, n):
    owner, name = repo.split("/", 1)
    out = []
    for page in gh_try("graphql", "--paginate", "--slurp", "-f", f"query={THREADS}",
                       "-f", f"owner={owner}", "-f", f"name={name}", "-F", f"n={n}"):
        for t in page["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]:
            last = (t["comments"]["nodes"] or [None])[-1] or {}
            out.append(dict(resolved=t["isResolved"], outdated=t["isOutdated"],
                            login=(last.get("author") or {}).get("login"),
                            body=last.get("body") or "",
                            pending=last.get("state") == "PENDING"))
    return out


def threads_ccr(repo, n, pending_comments):
    entries = [t for page in gh_try("--paginate", "--slurp",
                                    f"repos/{repo}/pulls/{n}/ccr/review_threads")
               for t in (page if isinstance(page, list) else [page])]
    # one paginated read of the PR's review comments; a single read only for a miss
    by_id = {c["id"]: c for page in pages(f"repos/{repo}/pulls/{n}/comments?per_page=100")
             for c in page}
    # a pending review's comments are in neither read: taken from main's read of them
    by_id.update(pending_comments)
    out = []
    for t in entries:
        login, body, pending = None, "", False
        if not t["resolved"] and t.get("comment_ids"):
            cid = t["comment_ids"][-1]  # thread order, so the last is the newest
            c = by_id.get(cid) or gh(f"repos/{repo}/pulls/comments/{cid}")
            login, body = (c.get("user") or {}).get("login"), c.get("body") or ""
            pending = cid in pending_comments
        out.append(dict(resolved=t["resolved"], outdated=bool(t.get("outdated")),
                        login=login, body=body, pending=pending))
    return out


def threads(repo, n, pending_comments):
    try:
        return threads_graphql(repo, n)
    except GhError as e:
        if "403" not in str(e):
            sys.exit(str(e))
    try:
        return threads_ccr(repo, n, pending_comments)
    except GhError as e:
        sys.exit(f"review threads unreadable over GraphQL (403) and the ccr route: {e}")


def count_threads(ts, owner_login):
    """The one settled-thread rule, whichever route read the threads."""
    unresolved = answered = needs_reply = 0
    for t in ts:
        if t["resolved"]:
            continue
        if t.get("pending") and t["login"] == owner_login:
            continue  # held in the owner's unsubmitted review: neither open nor answered
        if t.get("pending"):
            unresolved += 1
        elif t["login"] == owner_login and "?" not in t["body"]:
            answered += 1
        else:
            unresolved += 1
            needs_reply += bool(t["outdated"])
    return unresolved, answered, needs_reply


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="owner/name")
    ap.add_argument("--owner", required=True, help="the owner's account login")
    ap.add_argument("prs", nargs="+")
    a = ap.parse_args()
    # a pending review is shown only to its author: read as anyone else, it is unread
    try:
        reader = gh_try("user").get("login")
    except GhError:
        reader = None
    owner_reads = reader == a.owner

    out = []
    for n in a.prs:
        p = gh(f"repos/{a.repo}/pulls/{n}")
        sha = p["head"]["sha"]
        latest, pending_comments, own_pending = {}, {}, None
        for page in pages(f"repos/{a.repo}/pulls/{n}/reviews?per_page=100"):
            for r in page:  # chronological, so the last state per reviewer wins
                if r["state"] in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED"):
                    latest[r["user"]["login"]] = (r["state"], r["user"].get("type"))
                elif r["state"] == "PENDING":
                    cs = [c for cp in pages(f"repos/{a.repo}/pulls/{n}/reviews/{r['id']}"
                                            "/comments?per_page=100") for c in cp]
                    pending_comments.update({c["id"]: c for c in cs})
                    if (r.get("user") or {}).get("login") == a.owner:
                        own_pending = (r["id"], len(cs))
        approvals = [u for u, (s, kind) in latest.items() if s == "APPROVED" and kind != "Bot"]
        changes = [u for u, (s, _) in latest.items() if s == "CHANGES_REQUESTED"]
        unresolved, answered, needs_reply = count_threads(threads(a.repo, n, pending_comments), a.owner)
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
                        owner_pending_drafts=(own_pending[1] if own_pending else 0)
                        if owner_reads else None,
                        owner_pending_review=own_pending[0] if own_pending and owner_reads
                        else None,
                        owner_pending_read=owner_reads,
                        checks=len(runs) + len(statuses), fail=fail, pending=pending))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
