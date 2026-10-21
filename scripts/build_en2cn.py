#!/usr/bin/env python3
"""
Build job.en2cn.html from paper.json + translation.json.

Usage:
    python3 build_en2cn.py --paper out/paper.json --translation out/translation.json \
        --out out/job.en2cn.html

translation.json shape (see references/schemas.md):
{
  "paper_id": "optional-stable-id",
  "title_zh": "...",
  "short_title": "...",
  "one_liner": "...",
  "sections": [
    {"id": "s1", "title_zh": "摘要", "paras": {"p1": "……", "p2": "……"}}
  ]
}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from build_common import count_stats, inject, load_json, paper_meta, write_html

DEFAULT_TITLES = {
    "abstract": "摘要",
    "introduction": "引言",
    "methods": "材料与方法",
    "results": "结果",
    "discussion": "讨论",
    "other": "正文",
}


def normalise_translation(tr: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for sec in tr.get("sections", []):
        sid = sec.get("id", "")
        if not sid:
            continue
        paras = sec.get("paras", {})
        if isinstance(paras, list):
            paras = {p.get("id"): p.get("zh", "") for p in paras if p.get("id")}
        out[sid] = {"title_zh": sec.get("title_zh", ""), "paras": paras or {}}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--paper", type=Path, required=True)
    ap.add_argument("--translation", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--template-dir", type=Path, default=Path(__file__).resolve().parent.parent / "templates")
    args = ap.parse_args()

    paper = load_json(args.paper)
    tr = load_json(args.translation)
    tr_map = normalise_translation(tr)

    sections_out = []
    missing_sections = []
    missing_paras = 0
    total_paras = 0
    for sec in paper.get("sections", []):
        sid = sec.get("id", "")
        tm = tr_map.get(sid)
        if tm is None:
            missing_sections.append(sid or sec.get("title", "?"))
            tm = {"title_zh": "", "paras": {}}
        title_zh = tm.get("title_zh") or DEFAULT_TITLES.get(sec.get("role", ""), "") or sec.get("title", "")
        paras = []
        for p in sec.get("paras", []):
            total_paras += 1
            zh = (tm.get("paras", {}) or {}).get(p.get("id", ""), "")
            if not zh:
                missing_paras += 1
            paras.append({
                "id": p.get("id", ""),
                "page": p.get("page", ""),
                "en": p.get("en", ""),
                "zh": zh,
            })
        sections_out.append({
            "id": sid,
            "title": sec.get("title", ""),
            "title_zh": title_zh,
            "role": sec.get("role", "other"),
            "paras": paras,
        })

    if not sections_out:
        sys.exit("paper.json has no sections; run extract_pdf.py first and check the PDF text layer.")
    if not tr.get("title_zh"):
        print("WARN translation.title_zh is empty; use the English title.")
    if missing_sections:
        print(f"WARN no translation for section(s): {', '.join(missing_sections)}")
    if missing_paras:
        print(f"WARN {missing_paras}/{total_paras} paragraph(s) have no Chinese translation.")

    data = {
        "paper": paper_meta(paper, tr),
        "sections": sections_out,
        "stats": count_stats(sections_out),
    }
    html = inject(
        args.template_dir / "en2cn.html",
        args.template_dir / "theme.css",
        args.template_dir / "en2cn.js",
        data,
        page_title=f"{tr.get('short_title') or tr.get('title_zh') or paper.get('source', {}).get('title', '论文')} · 中英对照",
        title_text=paper.get("source", {}).get("title", "")[:90],
        nav_script=args.template_dir / "site-nav.js",
    )
    write_html(args.out, html)
    print(f"     sections={len(sections_out)} paragraphs={total_paras} zh_coverage={100*(total_paras-missing_paras)//max(1,total_paras)}%")


if __name__ == "__main__":
    main()
