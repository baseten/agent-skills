"""Render the work queue page: template.html with the state block filled in.

    python3 -I build.py --state state.json --template template.html --out index.html

The page is the template plus one state block; the page script regenerates the
whole document from that state and never serialises the DOM. `<` is escaped so
no state value can close the script element.
"""
import argparse
import html
import json

ap = argparse.ArgumentParser()
ap.add_argument("--state", required=True)
ap.add_argument("--template", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()

with open(a.state, encoding="utf-8") as f:
    st = json.load(f)
with open(a.template, encoding="utf-8") as f:
    t = f.read()
for token in ("__STATE__", "<title>Work queue</title>"):
    if t.count(token) != 1:
        raise SystemExit(f"template must hold {token!r} exactly once")
js = json.dumps(st, ensure_ascii=False).replace("<", "\\u003c")
title = html.escape(str(st.get("title") or "Work queue"))
t = t.replace("<title>Work queue</title>", f"<title>{title}</title>")
with open(a.out, "w", encoding="utf-8") as f:
    f.write(t.replace("__STATE__", js))
