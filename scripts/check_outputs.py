#!/usr/bin/env python3
"""
Validate a finished interpretation bundle.

Usage:
    python3 check_outputs.py <outdir>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REQUIRED = [
    "job.md",
    "job.en2cn.html",
    "job.fig.html",
    "job.method.html",
    "job.weixin.md",
    "job.talk.md",
]
HTML = ["job.en2cn.html", "job.fig.html", "job.method.html"]
PLACEHOLDERS = ["__DATA__", "__PAGE_TITLE__", "TODO", "待补充", "Lorem ipsum"]


def cjk_len(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", text))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("outdir", type=Path)
    args = ap.parse_args()
    root = args.outdir
    errors: list[str] = []
    warns: list[str] = []
    oks: list[str] = []

    for name in REQUIRED:
        p = root / name
        if not p.exists():
            errors.append(f"missing {name}")
        elif p.stat().st_size < 200:
            errors.append(f"{name} is suspiciously small ({p.stat().st_size} bytes)")
        else:
            oks.append(name)

    paper = None
    try:
        paper = json.loads((root / "paper.json").read_text(encoding="utf-8"))
    except Exception as e:
        warns.append(f"paper.json unreadable: {e}")

    if paper:
        figs = paper.get("figures", [])
        for f in figs:
            img = root / f.get("image", "")
            if not f.get("image") or not img.exists():
                errors.append(f"{f.get('label')} image missing: {f.get('image')}")
        if not figs:
            warns.append("paper.json has no figures; check extraction and crop_figure.py")

    for name in HTML:
        p = root / name
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        if "const DATA =" not in text:
            errors.append(f"{name}: embedded DATA not found")
        for ph in PLACEHOLDERS:
            if ph in text:
                warns.append(f"{name}: contains placeholder {ph!r}")
        if len(text) < 20_000:
            warns.append(f"{name}: unusually small HTML ({len(text)//1024} KB)")

    tr = root / "translation.json"
    if tr.exists():
        try:
            t = json.loads(tr.read_text(encoding="utf-8"))
            if not t.get("title_zh"):
                warns.append("translation.json: title_zh is empty")
            if not t.get("sections"):
                warns.append("translation.json: no sections")
        except Exception as e:
            errors.append(f"translation.json invalid: {e}")
    else:
        warns.append("translation.json not found (cannot verify translation coverage)")

    fpath = root / "figures.json"
    if fpath.exists() and paper:
        try:
            fd = json.loads(fpath.read_text(encoding="utf-8"))
            have = {f.get("id") for f in fd.get("figures", [])}
            missing = [f.get("id") for f in paper.get("figures", []) if f.get("id") not in have]
            if missing:
                warns.append(f"figures.json missing interpretations: {', '.join(missing)}")
            if not (fd.get("overview") or {}).get("lead"):
                warns.append("figures.json: overview.lead is empty")
        except Exception as e:
            errors.append(f"figures.json invalid: {e}")

    mpath = root / "methods.json"
    if mpath.exists():
        try:
            md = json.loads(mpath.read_text(encoding="utf-8"))
            if not md.get("methods"):
                warns.append("methods.json: no methods")
            for m in md.get("methods", []):
                if not (m.get("citation") or {}).get("doi") and not (m.get("citation") or {}).get("url"):
                    warns.append(f"methods.json: {m.get('name','?')} has no DOI/URL")
        except Exception as e:
            errors.append(f"methods.json invalid: {e}")

    wx = root / "job.weixin.md"
    if wx.exists():
        t = wx.read_text(encoding="utf-8", errors="replace")
        n = cjk_len(t)
        if n < 1200:
            warns.append(f"job.weixin.md: only {n} Chinese chars (target 1500–3000)")
        if "![" not in t:
            warns.append("job.weixin.md: no images inserted")
        if not re.search(r"(Fig|图)\s*\d", t):
            warns.append("job.weixin.md: no figure references")
        body = t.split("\n---\n", 1)[1] if "\n---\n" in t else t
        short_paras = []
        for para in re.split(r"\n\s*\n", body):
            para = para.strip()
            if not para or para.startswith(("![", "#", ">", "**", "- ", "* ", "|")):
                continue
            n = cjk_len(para)
            if n < 200:
                short_paras.append((n, para[:24]))
        if short_paras:
            warns.append(f"job.weixin.md: {len(short_paras)} paragraph(s) under 200 Chinese chars")
        q_count = t.count("？") + t.count("?")
        if q_count > 6:
            warns.append(f"job.weixin.md: {q_count} question marks (keep ≤2 in body)")

    talk = root / "job.talk.md"
    if talk.exists():
        t = talk.read_text(encoding="utf-8", errors="replace")
        n = cjk_len(t)
        if n < 600:
            warns.append(f"job.talk.md: only {n} Chinese chars (3–5 min ≈ 900–1300)")
        if n > 3000:
            warns.append(f"job.talk.md: {n} Chinese chars is too long for 3–5 min")
        for kw in ["期刊", "通讯", "背景", "问题", "结果", "创新"]:
            if kw not in t:
                warns.append(f"job.talk.md: missing section/keyword {kw!r}")

    md = root / "job.md"
    if md.exists():
        t = md.read_text(encoding="utf-8", errors="replace")
        if len(t) < 100:
            warns.append("job.md: too short")
        if "短标题" not in t and "Short title" not in t and not t.lstrip().startswith("# "):
            warns.append("job.md: no short-title block")

    print(f"Bundle: {root}")
    for x in oks:
        print(f"  OK   {x}")
    for w in warns:
        print(f"  WARN {w}")
    for e in errors:
        print(f"  FAIL {e}")
    if errors:
        print(f"\n{len(errors)} error(s), {len(warns)} warning(s).")
        sys.exit(1)
    print(f"\nPASS with {len(warns)} warning(s).")


if __name__ == "__main__":
    main()
