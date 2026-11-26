"""Read one repository's PR facts from GitHub for the work queue's "Your PRs" section.

    python3 -I prdata.py --repo owner/name --owner LOGIN [--team SLUG] 101 102 > prdata.json
    python3 -I prdata.py --repo owner/name --owner LOGIN [--team SLUG] --from-json reads.json [101 102]

The first form reads GitHub through `gh api`. The second reads nothing: it takes
reads made some other way as one JSON document, `-` for stdin, and emits the same
output — the GitHub MCP tools' reads, with what those tools cannot read written
unread, or plain REST reads, where neither `gh` nor the MCP tools are available
(a cloud session whose instructions bar `gh`). Both feed one transform, `pr_row`.
The document's form is at `JsonSource` below.

Run as part of the sweep: its output is that sweep's snapshot of these PRs
(conductor, *The status snapshot*), and mergeq.py and prsteps.py render from it
rather than reading GitHub again. Any read that fails stops the script: a count it
could not read is never written as zero. Two reads are the exceptions, each
written as unread rather than stopping: the owner's pending review (below), and a
team's membership (`teams[slug].members` null), which the token may not see.

For the PR steps it also reports `ever_ready`, for a draft only, from the PR's
timeline (a `ready_for_review` or `convert_to_draft` event): a draft that was ever
ready is held (draft state); and `teams`, each requested team and each --team
slug with its name and members.

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

`ever_ready_read` is false only where the timeline had no read (the MCP route):
`ever_ready` is then null, and prsteps.py offers that draft no "Mark ready".

A review counts as a bot's where its user's type is Bot or, where the type is not
given (the MCP tools omit it), its login ends in [bot].
"""
import argparse
import datetime
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


def ccr_rows(entries, by_id, pending_comments, single):
    """Threads from pulls/{n}/ccr/review_threads, each unresolved one's last comment
    looked up in by_id (pulls/{n}/comments), then in the pending review's comments,
    then through `single`, the one-comment read."""
    by_id = {**by_id, **pending_comments}
    out = []
    for t in entries:
        login, body, pending = None, "", False
        if not t["resolved"] and t.get("comment_ids"):
            cid = t["comment_ids"][-1]  # thread order, so the last is the newest
            c = by_id.get(cid) or single(cid)
            login, body = (c.get("user") or {}).get("login"), c.get("body") or ""
            pending = cid in pending_comments
        out.append(dict(resolved=t["resolved"], outdated=bool(t.get("outdated")),
                        login=login, body=body, pending=pending))
    return out


def threads_ccr(repo, n, pending_comments):
    entries = [t for page in gh_try("--paginate", "--slurp",
                                    f"repos/{repo}/pulls/{n}/ccr/review_threads")
               for t in (page if isinstance(page, list) else [page])]
    # one paginated read of the PR's review comments; a single read only for a miss
    by_id = {c["id"]: c for page in pages(f"repos/{repo}/pulls/{n}/comments?per_page=100")
             for c in page}
    return ccr_rows(entries, by_id, pending_comments,
                    lambda cid: gh(f"repos/{repo}/pulls/comments/{cid}"))


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


def is_bot(user):
    return user.get("type") == "Bot" or (user.get("login") or "").endswith("[bot]")


class GhSource:
    """The default route: every read is a `gh api` call; any failure stops."""

    def __init__(self, repo):
        self.repo = repo

    def viewer(self):
        try:
            return gh_try("user").get("login")
        except GhError:
            return None

    def pull(self, n):
        return gh(f"repos/{self.repo}/pulls/{n}")

    def timeline(self, n):
        return [ev for page in pages(f"repos/{self.repo}/issues/{n}/timeline?per_page=100")
                for ev in page]

    def team(self, org, slug):
        try:  # membership may be unreadable to this token: then unverified, never a stop
            name = gh_try(f"orgs/{org}/teams/{slug}").get("name")
            members = sorted(m["login"] for pg in gh_try("--paginate", "--slurp",
                             f"orgs/{org}/teams/{slug}/members?per_page=100") for m in pg)
        except GhError:
            name, members = None, None
        return {"name": name, "members": members}

    def reviews(self, n):
        return [r for page in pages(f"repos/{self.repo}/pulls/{n}/reviews?per_page=100")
                for r in page]

    def review_comments(self, n, rid):
        return [c for cp in pages(f"repos/{self.repo}/pulls/{n}/reviews/{rid}"
                                  "/comments?per_page=100") for c in cp]

    def threads(self, n, pending_comments):
        return threads(self.repo, n, pending_comments)

    def check_runs(self, n, sha):
        return [r for page in pages(f"repos/{self.repo}/commits/{sha}/check-runs?per_page=100")
                for r in page["check_runs"]]

    def statuses(self, n, sha):
        return [s for page in pages(f"repos/{self.repo}/commits/{sha}/status?per_page=100")
                for s in page["statuses"]]


class JsonSource:
    """Reads handed over as one document, from the GitHub MCP tools or from REST.
    Gather every page of each read (`page`, or `after` for review threads) before
    writing it. From the MCP tools:

    {"viewer": "LOGIN" | null,                  # get_me
     "teams": {"SLUG": {"name": ..., "members": [LOGIN, ...]}},   # get_team_members
     "prs": {"101": {
        "pull": {...},                          # pull_request_read get
        "reviews": [...],                       # get_reviews, oldest first
        "review_threads": [...],                # get_review_comments' review_threads
        "check_runs": {"check_runs": [...]},    # get_check_runs
        "status": {"statuses": [...]}}}}        # get_status

    What these tools cannot read is written unread, never guessed and never zero:
    a draft's ready history (`ever_ready` null, `ever_ready_read` false: no
    timeline read); the PR's requested teams (`requested_teams` null,
    `requested_teams_read` false: `get` omits them); and, where the owner has a
    PENDING review, its draft count (`owner_pending_read` false,
    `owner_pending_drafts` null, `owner_pending_review` its id), since its
    comments have no read and thread comments carry no state. Each thread whose
    last comment is the owner's is then counted held in that review: neither open
    nor answered. A team missing from
    `teams` has null name and members. Any other key the document lacks is a read
    that failed, and stops the script as the gh route does, `status` included:
    an external check (Chromatic, a deploy preview) may report only there.

    The REST route writes the same document from plain REST reads, with every
    page of each, where neither `gh` nor the MCP tools are available:

     "viewer": GET user's login, else null
     "teams": orgs/{org}/teams/{slug} and its /members, where readable
     "prs": {"101": {
        "pull": pulls/{n},                      # carries requested_teams: read
        "timeline": issues/{n}/timeline,        # the ready history: read
        "reviews": pulls/{n}/reviews,
        "pending_review_comments": {"<review id>": pulls/{n}/reviews/{id}/comments},
                                                # one per PENDING review returned
        "ccr_review_threads": pulls/{n}/ccr/review_threads,
        "comments": pulls/{n}/comments,         # in place of review_threads
        "check_runs": commits/{sha}/check-runs,
        "status": commits/{sha}/status}}

    GraphQL is not needed: the ccr threads route is the one the gh route falls
    back to, read by the same rule. Absent `timeline` is unread, as on the MCP
    route, never "never ready". `pending_review_comments` is required for each
    PENDING review the reviews list returns: without it the review's count is
    unread, and a thread whose last comment is in it is found in no read, which
    stops the script, as does any thread comment found in neither read.
    """

    def __init__(self, doc):
        self.doc = doc

    def _pr(self, n):
        pr = self.doc.get("prs", {}).get(str(n))
        if pr is None:
            sys.exit(f"--from-json: no reads for PR {n}")
        return pr

    def _need(self, n, key):
        pr = self._pr(n)
        if pr.get(key) is None:
            sys.exit(f"--from-json: PR {n} lacks {key}")
        return pr[key]

    def viewer(self):
        return self.doc.get("viewer")

    def pull(self, n):
        p = dict(self._need(n, "pull"))
        p.setdefault("requested_teams", None)  # `get` omits it: unread, never none requested
        return p

    def timeline(self, n):
        return self._pr(n).get("timeline")  # absent on the MCP route: unread

    def team(self, org, slug):
        t = (self.doc.get("teams") or {}).get(slug) or {}
        m = t.get("members")
        return {"name": t.get("name"), "members": sorted(m) if m is not None else None}

    def reviews(self, n):
        return self._need(n, "reviews")

    def review_comments(self, n, rid):
        # no MCP read of a pending review's comments: unread unless REST gave them
        return (self._pr(n).get("pending_review_comments") or {}).get(str(rid))

    def threads(self, n, pending_comments):
        if self._pr(n).get("ccr_review_threads") is not None:  # the REST route
            by_id = {c["id"]: c for c in self._need(n, "comments")}

            def missing(cid):
                sys.exit(f"--from-json: PR {n}: comment {cid} is in neither `comments` "
                         "nor a pending review's comments")
            return ccr_rows(self._pr(n)["ccr_review_threads"], by_id, pending_comments, missing)
        out = []
        for t in self._need(n, "review_threads"):
            cs = t.get("comments") or []
            last = cs[-1] if cs else {}
            author = last.get("author") or last.get("user") or {}
            out.append(dict(resolved=bool(t["is_resolved"]), outdated=bool(t.get("is_outdated")),
                            login=author if isinstance(author, str) else author.get("login"),
                            body=last.get("body") or "", pending=False))
        return out

    def check_runs(self, n, sha):
        v = self._need(n, "check_runs")
        return v["check_runs"] if isinstance(v, dict) else v

    def statuses(self, n, sha):
        v = self._need(n, "status")
        return v["statuses"] if isinstance(v, dict) else v


def pr_row(src, repo, n, owner, owner_reads, extra_teams):
    """One PR's row: the one transform both routes share."""
    p = src.pull(n)
    sha = p["head"]["sha"]
    # a draft that was ever ready is held (draft state): read from the timeline,
    # never from a record; a failed read stops the script like any other
    ever_ready = False
    if p["draft"]:
        events = src.timeline(n)
        ever_ready = None if events is None else any(
            ev.get("event") in ("ready_for_review", "convert_to_draft") for ev in events)
    org = repo.split("/", 1)[0]
    teams = {}
    requested_read = p.get("requested_teams") is not None or isinstance(src, GhSource)
    for slug in sorted({t.get("slug") for t in p.get("requested_teams") or []} | set(extra_teams)):
        if slug:
            teams[slug] = src.team(org, slug)
    latest, pending_comments, own_pending, reviewed_by = {}, {}, None, set()
    author = (p.get("user") or {}).get("login")
    for r in src.reviews(n):  # chronological, so the last state per reviewer wins
        u = r.get("user") or {}
        if (r["state"] in ("APPROVED", "CHANGES_REQUESTED", "COMMENTED")
                and not is_bot(u) and u.get("login") != author):
            reviewed_by.add(u.get("login"))
        if r["state"] in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED"):
            latest[u["login"]] = (r["state"], is_bot(u))
        elif r["state"] == "PENDING":
            cs = src.review_comments(n, r["id"])
            pending_comments.update({c["id"]: c for c in cs or []})
            if u.get("login") == owner:
                own_pending = (r["id"], None if cs is None else len(cs))
    # where its comments could not be read, the owner's pending review is unread
    owner_read = owner_reads and not (own_pending and own_pending[1] is None)
    approvals = [u for u, (s, bot) in latest.items() if s == "APPROVED" and not bot]
    changes = [u for u, (s, _) in latest.items() if s == "CHANGES_REQUESTED"]
    ts = src.threads(n, pending_comments)
    if own_pending and own_pending[1] is None:
        # which comments sit in the owner's pending review is unread, so each thread
        # whose last comment is theirs may be held there: counted held, never answered
        for t in ts:
            if t["login"] == owner:
                t["pending"] = True
    unresolved, answered, needs_reply = count_threads(ts, owner)
    runs, statuses = src.check_runs(n, sha), src.statuses(n, sha)
    fail = sorted({r["name"] for r in runs
                   if r.get("conclusion") in ("failure", "timed_out", "cancelled", "action_required")}
                  | {s["context"] for s in statuses if s["state"] in ("failure", "error")})
    pending = sorted({r["name"] for r in runs if r["status"] != "completed"}
                     | {s["context"] for s in statuses if s["state"] == "pending"})
    return dict(repo=repo, pr=str(n), url=p["html_url"], title=p["title"],
                sha=sha, base=p["base"]["ref"], draft=p["draft"], state=p["state"],
                merged=p["merged"], mergeable=p.get("mergeable_state"),
                requested_teams=[{"slug": t.get("slug"), "name": t.get("name")}
                                 for t in p.get("requested_teams") or []]
                if requested_read else None,
                requested_teams_read=requested_read,
                reviewed_by=sorted(reviewed_by), ever_ready=ever_ready, teams=teams,
                approvals=approvals, changes=changes, unresolved=unresolved, answered=answered,
                needs_reply=needs_reply,
                ever_ready_read=ever_ready is not None,
                owner_pending_drafts=(own_pending[1] if own_pending else 0)
                if owner_read else None,
                owner_pending_review=own_pending[0] if own_pending and owner_reads
                else None,
                owner_pending_read=owner_read,
                checks=len(runs) + len(statuses), fail=fail, pending=pending)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="owner/name")
    ap.add_argument("--owner", required=True, help="the owner's account login")
    ap.add_argument("--team", action="append", default=[],
                    help="a team slug whose membership the PR steps check, beside requested teams")
    ap.add_argument("--from-json", metavar="FILE",
                    help="read nothing: take the reads from this JSON document, - for stdin")
    ap.add_argument("prs", nargs="*")
    a = ap.parse_args()
    if a.from_json:
        with (sys.stdin if a.from_json == "-" else open(a.from_json)) as f:
            src = JsonSource(json.load(f))
        prs = a.prs or list(src.doc.get("prs") or {})
        if not prs:
            sys.exit("--from-json: the document names no PR")
    else:
        if not a.prs:
            ap.error("name the PRs to read")
        src, prs = GhSource(a.repo), a.prs
    # a pending review is shown only to its author: read as anyone else, it is unread
    owner_reads = src.viewer() == a.owner
    rows = [pr_row(src, a.repo, n, a.owner, owner_reads, a.team) for n in prs]
    # the read's time, carried by mergeq.py and prsteps.py, which build.py checks is this turn's
    read_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for r in rows:
        r["readAt"] = read_at
    print(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
