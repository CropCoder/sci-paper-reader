#!/usr/bin/env python3
"""
Build job.method.html from paper.json + methods.json.

Usage:
    python3 build_method.py --paper out/paper.json --methods out/methods.json \
        --out out/job.method.html

methods.json shape (see references/schemas.md):
{
  "overview": "一句话技术路线总览",
  "route": [{"step": "01", "name": "样本/数据", "desc": "..."}],
  "methods": [
    {"id": "m1", "name": "……", "name_en": "……", "category": "实验/测序/计算/统计",
     "what": "原理", "how": "本文怎么用", "params": "关键参数",
     "interpretation": "解读", "used_in": ["Fig. 1"],
     "citation": {"text": "……", "doi": "...", "url": "..."}}
  ],
  "notes": ["……"]
}
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from build_common import inject, load_json, paper_meta, write_html


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--paper", type=Path, required=True)
    ap.add_argument("--methods", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--template-dir", type=Path, default=Path(__file__).resolve().parent.parent / "templates")
    args = ap.parse_args()

    paper = load_json(args.paper)
    mdata = load_json(args.methods)
    methods = mdata.get("methods", [])
    if not methods:
        sys.exit("methods.json has no 'methods' entries.")
    for i, m in enumerate(methods, 1):
        m.setdefault("id", f"m{i}")
        if not m.get("name"):
            print(f"WARN method #{i} has no name.")
        cite = m.get("citation") or {}
        if not (cite.get("doi") or cite.get("url")):
            print(f"WARN method '{m.get('name','?')}' has no DOI/URL; add one if the original paper is known.")

    data = {
        "paper": paper_meta(paper, mdata),
        "overview": mdata.get("overview", ""),
        "route": mdata.get("route", []),
        "methods": methods,
        "notes": mdata.get("notes", []),
    }
    html = inject(
        args.template_dir / "method.html",
        args.template_dir / "theme.css",
        args.template_dir / "method.js",
        data,
        page_title=f"方法拆解 · {paper.get('source', {}).get('title', '论文')}",
        title_text=paper.get("source", {}).get("title", "")[:90],
        nav_script=args.template_dir / "site-nav.js",
    )
    write_html(args.out, html)
    print(f"     methods={len(methods)} route_steps={len(data['route'])}")


if __name__ == "__main__":
    main()
