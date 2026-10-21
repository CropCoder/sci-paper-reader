#!/usr/bin/env python3
"""
Re-crop one figure/table from the source PDF when the automatic crop is wrong.

Usage:
    # inspect what the extractor chose
    python3 crop_figure.py --paper out/paper.json --list

    # render a full page for orientation
    python3 crop_figure.py --paper out/paper.json --page 6 --out out/figs/page6.png

    # crop a manual rectangle (PDF points, origin top-left) and update paper.json
    python3 crop_figure.py --paper out/paper.json --fig fig2 --bbox 70,85,530,350 \
        --out out/figs/fig2.png --update

The bbox is x0,y0,x1,y1 in PDF coordinates (points). Use macOS Preview's
inspect window or `--list` to get page size: a US-Letter page is 612x792 pt.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import fitz
except ImportError:
    sys.exit("PyMuPDF is required: python3 -m pip install --user pymupdf")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--paper", type=Path, required=True)
    ap.add_argument("--fig", help="figure id, e.g. fig2")
    ap.add_argument("--page", type=int, help="1-based page number (overrides the figure page)")
    ap.add_argument("--bbox", help="x0,y0,x1,y1 in PDF points")
    ap.add_argument("--out", type=Path, help="output PNG path")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--update", action="store_true", help="update the figure entry in paper.json")
    ap.add_argument("--list", action="store_true", help="list figures and tables")
    args = ap.parse_args()

    paper = json.loads(args.paper.read_text(encoding="utf-8"))
    pdf = Path(paper.get("source", {}).get("pdf", ""))
    if not pdf.exists():
        alt = args.paper.parent / pdf.name
        if alt.exists():
            pdf = alt
        else:
            sys.exit(f"source PDF not found: {pdf} (also tried {alt})")

    entries = paper.get("figures", []) + paper.get("tables", [])
    if args.list:
        doc = fitz.open(pdf)
        for e in entries:
            pg = e.get("page", 1)
            w, h = doc[pg - 1].rect.width, doc[pg - 1].rect.height
            print(f"{e.get('id'):8s} {e.get('label'):10s} p.{pg:<3} page={w:.0f}x{h:.0f} "
                  f"bbox={e.get('bbox')} -> {e.get('image')}")
        return

    entry = next((e for e in entries if e.get("id") == args.fig), None)
    if args.fig and entry is None:
        sys.exit(f"figure id not found: {args.fig}")
    page_no = args.page or (entry or {}).get("page")
    if not page_no:
        sys.exit("provide --page (1-based) or --fig with a page in paper.json")
    out = args.out or (Path(entry["image"]) if entry and entry.get("image") else Path(f"page{page_no}.png"))
    out.parent.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf)
    page = doc[page_no - 1]
    if args.bbox:
        try:
            x0, y0, x1, y1 = [float(v) for v in args.bbox.split(",")]
        except ValueError:
            sys.exit("--bbox must be four numbers: x0,y0,x1,y1")
        rect = fitz.Rect(x0, y0, x1, y1)
        if rect.is_empty or not page.rect.contains(rect):
            sys.exit(f"bbox outside page {page.rect}")
    else:
        rect = page.rect
    pix = page.get_pixmap(clip=rect, dpi=args.dpi, alpha=False)
    pix.save(str(out))
    print(f"OK  {out}  {pix.width}x{pix.height}px  page {page_no}  bbox={list(rect)}")

    if args.update and entry is not None:
        entry["bbox"] = [round(v, 1) for v in rect]
        try:
            entry["image"] = str(out.resolve().relative_to(args.paper.parent.resolve())).replace("\\", "/")
        except ValueError:
            entry["image"] = str(out.resolve())
        entry["confidence"] = "manual"
        args.paper.write_text(json.dumps(paper, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"     updated {args.paper}")


if __name__ == "__main__":
    main()
