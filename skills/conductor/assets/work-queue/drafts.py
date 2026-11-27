"""The work queue's draft entries, and the duplicate rule, shared by the scripts.

Not run on its own: build.py, carry.py, prune.py and refresh.py load it from
their own directory by path, so `python3 -I` still imports nothing from the
working directory.

A **draft** is text the owner posts themselves, wherever it goes (conductor,
work-queue.md, *Drafts to post*). Every entry carries `id`, `kind`, `label` (where
it goes, as the page groups it), `gist` (one line) and `text` (the exact text,
shown verbatim), and may carry `who` (whom it answers) and `note`. By kind:

    pr-thread  a reply in a PR review thread: repo, pr, and url, the thread's
               html_url as recorded
    pr-body    a line to change in a published PR body: repo, pr, url (the PR's
               html_url) and old, the line to replace; text is its replacement
    notion     a reply on a Notion comment thread: url
    linear     a comment on a Linear issue or document: url
    slack      a Slack message: label names the channel; url, the channel or a
               permalink, only where one is known
    post       any other text to post at an https url: url

Only pr-thread and pr-body are bound to a PR: they are the only kinds whose PR is
read from GitHub, and the only ones pruned on its state.
refresh.py stamps a PR-bound draft `prUnread`, with the reason, where its PR could
not be read: the page shows it as a warning, and prune.py never prunes it.

`replies` is the earlier name, for pr-thread drafts only, and still loads: each
entry becomes a pr-thread draft labelled with its PR number, unless `drafts`
already holds its id.
"""

KINDS = ("pr-thread", "pr-body", "notion", "linear", "slack", "post")
PR_KINDS = ("pr-thread", "pr-body")
REQUIRED = {
    "pr-thread": ("repo", "pr", "url"),
    "pr-body": ("repo", "pr", "url", "old"),
    "notion": ("url",),
    "linear": ("url",),
    "slack": (),
    "post": ("url",),
}
COMMON = ("id", "kind", "label", "gist", "text")


def from_reply(r):
    d = dict(r)
    d.setdefault("kind", "pr-thread")
    d.setdefault("label", f'#{r.get("pr")}' if r.get("pr") is not None else "Review thread")
    return d


def normalise(st):
    """Fold a state's `replies` into `drafts`, in place, and return the state."""
    drafts = list(st.get("drafts") or [])
    have = {str(d.get("id")) for d in drafts}
    for r in st.get("replies") or []:
        if str(r.get("id")) not in have:
            drafts.append(from_reply(r))
            have.add(str(r.get("id")))
    st.pop("replies", None)
    st["drafts"] = drafts
    return st


def pr_bound(d):
    return d.get("kind") in PR_KINDS


def problems(d):
    """What a draft lacks for its kind, as a list of short strings; empty when whole."""
    out = []
    kind = d.get("kind")
    if kind not in KINDS:
        return [f"kind {kind!r} is not one of {', '.join(KINDS)}"]
    for k in COMMON + REQUIRED[kind]:
        if not str(d.get(k) or "").strip():
            out.append(f"no {k}")
    url = d.get("url")
    if url and not str(url).startswith("https://"):
        out.append("url is not https")
    return out


def _merge_owner_marks(win, other):
    # an owner's saved answer or tick on a dropped copy is never lost
    if other.get("answer") is not None and win.get("answer") is None:
        win["answer"] = other["answer"]
        if win.get("status") in (None, "open"):
            win["status"] = "answered"
    if "done" in other and "done" not in win:
        win["done"], win["doneAt"] = other["done"], other.get("doneAt")


def dedupe(st, live=None):
    """Keep one entry per id in decisions, items and drafts, in place.

    The build's copy wins: where `live` (the live page's state) is given, a copy
    identical to the live page's entry is the one taken from it, so a copy that
    differs is preferred; otherwise the first. An owner's saved answer or tick on
    a dropped copy is kept on the winner. Returns the ids that were duplicated.
    """
    dup = []
    for key in ("decisions", "items", "drafts"):
        rows = st.get(key) or []
        groups, order = {}, []
        for x in rows:
            i = str(x.get("id"))
            if i not in groups:
                groups[i] = []
                order.append(i)
            groups[i].append(x)
        if len(order) == len(rows):
            continue
        lv = {str(x.get("id")): x for x in (live or {}).get(key) or []}
        out = []
        for i in order:
            copies = groups[i]
            if len(copies) > 1:
                dup.append(f"{key[:-1]} {i}")
                fresh = [c for c in copies if c != lv.get(i)]
                first = (fresh or copies)[0]
                win = dict(first)
                for c in copies:
                    if c is not first:
                        _merge_owner_marks(win, c)
                out.append(win)
            else:
                out.append(copies[0])
        st[key] = out
    return dup
