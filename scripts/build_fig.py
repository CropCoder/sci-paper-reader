#!/usr/bin/env python3
"""
Build job.fig.html from paper.json + figures.json.

Usage:
    python3 build_fig.py --paper out/paper.json --figures out/figures.json \
        --out out/job.fig.html

figures.json shape (see references/schemas.md):
{
  "overview": {"lead": "...", "logic_summary": "...",
               "flow": [{"label": "Fig.1", "title": "...", "desc": "..."}],
               "note": "..."},
  "figures": [
    {"id": "fig1", "short": "...", "one_line": "...", "legend_zh": "...",
     "what": "...", "meaning": "...", "conclusion": "...",
     "panels": [{"label": "A", "text": "..."}],
     "caveats": ["..."], "connection": "...", "tags": ["..."]}
  ]
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
    ap.add_argument("--figures", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--template-dir", type=Path, default=Path(__file__).resolve().parent.parent / "templates")
    args = ap.parse_args()

    paper = load_json(args.paper)
    fdata = load_json(args.figures)
    interpretations = {f.get("id", ""): f for f in fdata.get("figures", [])}
    by_label = {str(f.get("label", "")).lower(): f for f in fdata.get("figures", [])}

    figures_out = []
    missing = []
    for f in paper.get("figures", []):
        fid = f.get("id", "")
        interp = interpretations.get(fid) or by_label.get(str(f.get("label", "")).lower())
        if interp is None:
            missing.append(f.get("label", fid))
            interp = {}
        figures_out.append({
            "id": fid,
            "label": f.get("label", fid),
            "page": f.get("page", ""),
            "image": f.get("image", ""),
            "caption_en": f.get("caption_en", ""),
            "short": interp.get("short", "") or f.get("label", fid),
            "one_line": interp.get("one_line", ""),
            "legend_zh": interp.get("legend_zh", ""),
            "what": interp.get("what", ""),
            "meaning": interp.get("meaning", ""),
            "conclusion": interp.get("conclusion", ""),
            "panels": interp.get("panels", []) or [],
            "caveats": interp.get("caveats", []) or [],
            "connection": interp.get("connection", ""),
            "tags": interp.get("tags", []) or [],
        })

    if not figures_out:
        print("WARN paper.json contains no figures; the page will render an empty gallery.")
    if missing:
        print(f"WARN no interpretation for: {', '.join(missing)}; placeholders used.")

    overview = fdata.get("overview") or {}
    if not overview.get("flow"):
        overview["flow"] = [
            {"label": f["label"], "title": f["short"], "desc": f["one_line"]}
            for f in figures_out
        ]
    if not overview.get("lead"):
        overview["lead"] = "先读整体逻辑，再逐张拆解：每一张主图回答一个小问题，串起来就是论文的证据链。"

    data = {
        "paper": paper_meta(paper, fdata),
        "overview": overview,
        "figures": figures_out,
    }
    html = inject(
        args.template_dir / "fig.html",
        args.template_dir / "theme.css",
        args.template_dir / "fig.js",
        data,
        page_title=f"Figure 图解 · {paper.get('source', {}).get('title', '论文')}",
        title_text=paper.get("source", {}).get("title", "")[:90],
        nav_script=args.template_dir / "site-nav.js",
    )
    write_html(args.out, html)
    print(f"     figures={len(figures_out)} with_details={len(figures_out)-len(missing)}")


if __name__ == "__main__":
    main()
