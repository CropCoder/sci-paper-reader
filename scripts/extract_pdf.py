#!/usr/bin/env python3
"""
extract_pdf.py — turn a research-paper PDF into a structured, figure-aware JSON.

Usage:
    python3 extract_pdf.py paper.pdf -o outdir [--dpi 260] [--pages]

Outputs (inside outdir):
    paper.json     structured paper: front matter, sections/paragraphs, figures, tables, refs
    paper.txt      human-readable dump for quick reading / grep
    figs/figN.png  cropped figure images
    figs/tableN.png
    figs/page_N.png (when a figure/table lives on that page)

The extractor is deliberately conservative: when it cannot locate a figure
reliably it still writes a best-effort crop plus a warning, so the agent can
inspect the image and re-crop with crop_figure.py instead of silently shipping
a wrong picture.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    sys.exit(
        "PyMuPDF is required. Install it with:  python3 -m pip install --user pymupdf\n"
        "(The bundled DSH python usually already has it.)"
    )

# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #

LIGATURES = {
    "\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl", "\ufb03": "ffi",
    "\ufb04": "ffl", "\ufb05": "ft", "\ufb06": "st",
    "\u2010": "-", "\u2011": "-", "\u00ad": "",
}
HEADING_WORDS = {
    "abstract", "summary", "introduction", "background", "results",
    "results and discussion", "discussion", "conclusion", "conclusions",
    "materials and methods", "methods", "method", "experimental procedures",
    "experimental section", "star methods", "online methods", "data availability",
    "acknowledgements", "acknowledgments", "references", "bibliography",
    "literature cited", "supplementary information", "supplementary material",
    "author contributions", "funding", "competing interests", "conflict of interest",
}
CAPTION_RE = re.compile(
    r"^\s*(?P<kind>fig(?:ure)?|table)\s*\.?\s*(?P<num>\d+[A-Za-z]?)"
    r"(?:\s*[:.\u2014|]\s*|\n|\s{2,})",
    re.I,
)
DOI_RE = re.compile(r"\b(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)\b")
YEAR_RE = re.compile(r"\b(19[5-9]\d|20[0-4]\d)\b")


def clean_text(text: str) -> str:
    for src, dst in LIGATURES.items():
        text = text.replace(src, dst)
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def norm_key(text: str) -> str:
    text = clean_text(text).lower()
    return re.sub(r"\s+", " ", text)[:140]


def join_lines(lines: list[str]) -> str:
    """Join PDF text lines into one paragraph, repairing hyphenation."""
    out = ""
    for i, raw in enumerate(lines):
        line = raw.strip()
        if not line:
            continue
        if not out:
            out = line
            continue
        prev = out[-1]
        if prev == "-" and line[:1].islower():
            out = out[:-1] + line
        elif prev == "-" and line[:1].isupper() and re.match(r"^[A-Z]{2,}", line):
            out = out[:-1] + line  # keep all-caps words intact
        elif re.search(r"[\u4e00-\u9fff]$", out) or re.match(r"^[\u4e00-\u9fff]", line):
            out += line
        elif prev in "([{/" or line[0] in ")]},.;:%":
            out += line
        else:
            out += " " + line
    return re.sub(r"\s+", " ", out).strip()


@dataclass
class Line:
    text: str
    bbox: tuple[float, float, float, float]
    size: float
    bold: bool


@dataclass
class Block:
    page: int
    bbox: tuple[float, float, float, float]
    lines: list[Line]
    text: str = ""
    size: float = 0.0
    bold: bool = False
    kind: str = "body"  # body | heading | caption | figure | table | skip
    section: str = ""

    def __post_init__(self) -> None:
        if not self.text:
            self.text = join_lines([ln.text for ln in self.lines])
        if self.lines and not self.size:
            self.size = max(ln.size for ln in self.lines)
        if self.lines and not self.bold:
            chars = sum(len(ln.text.strip()) for ln in self.lines)
            bold_chars = sum(len(ln.text.strip()) for ln in self.lines if ln.bold)
            self.bold = chars > 0 and bold_chars / chars >= 0.6

    def paragraphs(self) -> list[str]:
        """Split one PDF text block into logical paragraphs using line gaps/indents."""
        if not self.lines:
            return [self.text]
        heights = [max(1.0, ln.bbox[3] - ln.bbox[1]) for ln in self.lines]
        med_h = sorted(heights)[len(heights) // 2]
        gaps = []
        for a, b in zip(self.lines, self.lines[1:]):
            gap = b.bbox[1] - a.bbox[3]
            if gap >= 0:
                gaps.append(gap)
        med_gap = sorted(gaps)[len(gaps) // 2] if gaps else 0
        groups: list[list[Line]] = [[self.lines[0]]]
        for prev, line in zip(self.lines, self.lines[1:]):
            gap = line.bbox[1] - prev.bbox[3]
            new_para = gap > max(3.0, med_gap + med_h * 0.55)
            indent = line.bbox[0] - self.bbox[0]
            if (
                not new_para
                and indent > med_h * 0.9
                and prev.text.rstrip().endswith((".", "。", "!", "?", ":", ";"))
                and len(prev.text.strip()) > 35
            ):
                new_para = True
            if new_para:
                groups.append([line])
            else:
                groups[-1].append(line)
        paras = []
        for g in groups:
            txt = join_lines([ln.text for ln in g])
            if txt:
                paras.append(txt)
        return paras or [self.text]

    @property
    def x0(self) -> float:
        return self.bbox[0]

    @property
    def y0(self) -> float:
        return self.bbox[1]

    @property
    def x1(self) -> float:
        return self.bbox[2]

    @property
    def y1(self) -> float:
        return self.bbox[3]

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2


@dataclass
class Visual:
    rect: tuple[float, float, float, float]
    kind: str  # image | drawing


# --------------------------------------------------------------------------- #
# extraction
# --------------------------------------------------------------------------- #

class PaperExtractor:
    def __init__(self, pdf_path: Path, outdir: Path, dpi: int = 260, save_pages: bool = False):
        self.pdf_path = pdf_path
        self.outdir = outdir
        self.fig_dir = outdir / "figs"
        self.fig_dir.mkdir(parents=True, exist_ok=True)
        self.dpi = dpi
        self.save_pages = save_pages
        self.doc = fitz.open(pdf_path)
        self.pages = list(self.doc)
        self.page_sizes = [(p.rect.width, p.rect.height) for p in self.pages]
        self.warnings: list[str] = []
        self.body_size = 10.0
        self.page_blocks: list[list[Block]] = []
        self.page_visuals: list[list[Visual]] = []
        self.repeated_margins: set[str] = set()
        self.figures: list[dict] = []
        self.tables: list[dict] = []

    # -- text blocks ------------------------------------------------------- #

    def _read_block(self, page_no: int, raw: dict) -> Block | None:
        lines: list[Line] = []
        for line in raw.get("lines", []):
            all_spans = line.get("spans", [])
            spans = [s for s in all_spans if s.get("text", "").strip()]
            if not spans:
                continue
            # Keep space-only spans for the text, and add a space when the PDF
            # encodes a gap positionally instead of as a space character.
            parts: list[str] = []
            prev = None
            for s in all_spans:
                t = s.get("text", "")
                if not t:
                    continue
                if prev is not None and parts and not parts[-1].endswith(" ") and not t.startswith(" "):
                    gap = float(s["bbox"][0]) - float(prev["bbox"][2])
                    size = max(float(s.get("size", 0)), 1.0)
                    if gap > max(1.0, size * 0.16):
                        parts.append(" ")
                parts.append(t)
                prev = s
            text = "".join(parts)
            size = max(float(s.get("size", 0)) for s in spans)
            flags = 0
            for s in spans:
                flags |= int(s.get("flags", 0))
            bold = bool(flags & 16) or any(
                re.search(r"bold|black|heavy|medi", str(s.get("font", "")), re.I) for s in spans
            )
            lines.append(Line(text=text, bbox=tuple(line["bbox"]), size=size, bold=bold))
        if not lines:
            return None
        text = join_lines([ln.text for ln in lines])
        if not text:
            return None
        return Block(page=page_no, bbox=tuple(raw["bbox"]), lines=lines, text=clean_text(text))

    def read_blocks(self) -> None:
        for pno, page in enumerate(self.pages):
            blocks: list[Block] = []
            for raw in page.get_text("dict")["blocks"]:
                if raw.get("type") != 0:
                    continue
                b = self._read_block(pno, raw)
                if b is None:
                    continue
                # drop page-number-only blocks and obvious furniture
                if re.fullmatch(r"\d{1,4}", b.text):
                    continue
                blocks.append(b)
            self.page_blocks.append(blocks)
        self._estimate_body_size()
        self._find_repeated_margins()

    def _estimate_body_size(self) -> None:
        counter: Counter[float] = Counter()
        for blocks in self.page_blocks:
            for b in blocks:
                for ln in b.lines:
                    n = len(ln.text.strip())
                    if n >= 20 and 4 < ln.size < 30:
                        counter[round(ln.size, 1)] += n
        if counter:
            self.body_size = counter.most_common(1)[0][0]

    def _find_repeated_margins(self) -> None:
        counts: Counter[str] = Counter()
        per_page: list[set[str]] = []
        for pno, blocks in enumerate(self.page_blocks):
            h = self.page_sizes[pno][1]
            found: set[str] = set()
            for b in blocks:
                if b.y1 < h * 0.075 or b.y0 > h * 0.925:
                    key = norm_key(b.text)
                    if 4 <= len(key) <= 120:
                        found.add(key)
            for k in found:
                counts[k] += 1
            per_page.append(found)
        threshold = max(3, int(len(self.pages) * 0.3))
        self.repeated_margins = {k for k, c in counts.items() if c >= threshold}
        # remember per-page so the filter can be precise
        self._margin_hits = per_page

    def _drop_furniture(self, pno: int, b: Block) -> bool:
        key = norm_key(b.text)
        if key in self.repeated_margins:
            return True
        low = key.lower()
        if pno == 0 and (
            b.text.lstrip().startswith(("∗", "†", "‡", "*", "‡"))
            or re.search(r"equal contribution|work performed while|conference on neural|"
                         r"corresponding author|to whom correspondence", low)
        ):
            return True
        if any(low.startswith(x) for x in (
            "downloaded from", "this article is protected", "for personal use only",
            "provided proper attribution", "arxiv:", "preprint", "bioRxiv preprint",
            "all rights reserved", "terms and conditions", "www.",
        )):
            return True
        if self.page_sizes[pno][1] > 0 and (
            b.y1 < self.page_sizes[pno][1] * 0.055 or b.y0 > self.page_sizes[pno][1] * 0.94
        ) and len(b.text) < 100:
            return True
        return False

    # -- reading order ----------------------------------------------------- #

    def order_blocks(self, pno: int) -> list[Block]:
        blocks = [b for b in self.page_blocks[pno] if not self._drop_furniture(pno, b)]
        if not blocks:
            return []
        w, h = self.page_sizes[pno]
        mid = w / 2
        left = [b for b in blocks if b.x1 < mid - 4]
        right = [b for b in blocks if b.x0 > mid + 4]
        left_chars = sum(len(b.text) for b in left)
        right_chars = sum(len(b.text) for b in right)
        two_col = left_chars > 250 and right_chars > 250
        if not two_col:
            return sorted(blocks, key=lambda b: (round(b.y0, 1), b.x0))

        full = [b for b in blocks if b.x0 < mid - 12 and b.x1 > mid + 12]
        body = [b for b in blocks if b not in full]
        ordered: list[Block] = []
        bands: list[list[Block]] = []
        full_sorted = sorted(full, key=lambda b: b.cy)
        prev = 0.0
        for fb in full_sorted:
            bands.append([b for b in body if prev <= b.cy < fb.cy])
            ordered.append(fb)
            prev = fb.cy
        bands.append([b for b in body if b.cy >= prev])
        # interleave full-width blocks with the bands, preserving y order
        result: list[Block] = []
        band_idx = 0
        cursor = 0.0
        for fb in full_sorted:
            band = [b for b in body if cursor <= b.cy < fb.cy]
            result.extend(sorted([b for b in band if b.cx < mid], key=lambda b: b.y0))
            result.extend(sorted([b for b in band if b.cx >= mid], key=lambda b: b.y0))
            result.append(fb)
            cursor = fb.cy
        band = [b for b in body if b.cy >= cursor]
        result.extend(sorted([b for b in band if b.cx < mid], key=lambda b: b.y0))
        result.extend(sorted([b for b in band if b.cx >= mid], key=lambda b: b.y0))
        return result

    # -- headings ---------------------------------------------------------- #

    def is_heading(self, b: Block) -> bool:
        txt = b.text.strip()
        if not txt or len(txt) > 150:
            return False
        if CAPTION_RE.match(txt):
            return False
        low = re.sub(r"^\d+(\.\d+)*[\.\s]+", "", txt.lower()).strip(" .:")
        if low in HEADING_WORDS:
            return True
        # numbered section heading: "3.1 Encoder and Decoder Stacks"
        if re.match(r"^\d+(\.\d+){0,2}\.?\s+[A-Z]", txt) and len(txt) < 100:
            if b.size >= self.body_size + 0.4 or b.bold:
                return True
        if b.size >= self.body_size + 1.1 and len(txt) < 120:
            return not txt.rstrip().endswith(".")
        if b.bold and b.size >= self.body_size + 0.15 and len(txt) < 80:
            return not txt.rstrip().endswith((".", ",", ";"))
        return False

    def normalize_heading(self, b: Block) -> str:
        txt = re.sub(r"\s*\n\s*", " ", b.text)
        txt = re.sub(r"^(\d+(?:\.\d+)*)\s+", r"\1 ", txt)
        return re.sub(r"\s+", " ", txt).strip(" .")

    # -- visuals ----------------------------------------------------------- #

    def collect_visuals(self) -> None:
        for pno, page in enumerate(self.pages):
            vis: list[Visual] = []
            for info in page.get_image_info():
                r = tuple(info["bbox"])
                if (r[2] - r[0]) > 6 and (r[3] - r[1]) > 6:
                    vis.append(Visual(r, "image"))
            for d in page.get_drawings():
                r = tuple(d["rect"])
                if (r[2] - r[0]) > 1.5 and (r[3] - r[1]) > 1.5:
                    vis.append(Visual(r, "drawing"))
            self.page_visuals.append(vis)

    def cluster_visuals(self, visuals: list[Visual], gap: float = 30) -> list[tuple[float, float, float, float]]:
        rects = [v.rect for v in visuals]
        groups: list[list[float]] = []
        for r in sorted(rects, key=lambda x: (x[1], x[0])):
            placed = False
            for g in groups:
                # merge when vertically close and horizontally related
                h_overlap = min(r[2], g[2]) - max(r[0], g[0])
                v_gap = max(r[1], g[1]) - min(r[3], g[3])
                if h_overlap > -30 and v_gap <= gap and min(r[3], g[3]) - max(r[1], g[1]) > -gap:
                    g[0], g[1] = min(g[0], r[0]), min(g[1], r[1])
                    g[2], g[3] = max(g[2], r[2]), max(g[3], r[3])
                    placed = True
                    break
            if not placed:
                groups.append([r[0], r[1], r[2], r[3]])
        # merge groups transitively
        changed = True
        while changed:
            changed = False
            for i in range(len(groups)):
                for j in range(i + 1, len(groups)):
                    a, b = groups[i], groups[j]
                    h_overlap = min(a[2], b[2]) - max(a[0], b[0])
                    v_gap = max(a[1], b[1]) - min(a[3], b[3])
                    if h_overlap > -30 and v_gap <= gap:
                        a[0], a[1] = min(a[0], b[0]), min(a[1], b[1])
                        a[2], a[3] = max(a[2], b[2]), max(a[3], b[3])
                        groups.pop(j)
                        changed = True
                        break
                if changed:
                    break
        return [tuple(g) for g in groups if (g[2] - g[0]) > 8 and (g[3] - g[1]) > 8]

    def pick_cluster(
        self, clusters: list[tuple[float, float, float, float]], side: str, anchor: float, page_h: float
    ) -> tuple[float, float, float, float] | None:
        if not clusters:
            return None
        if side == "above":
            cands = [c for c in clusters if c[3] <= anchor + 6 and c[3] > anchor - 0.8 * page_h]
            if not cands:
                return None
            # prefer large, close to the caption
            return max(cands, key=lambda c: (c[2] - c[0]) * (c[3] - c[1]) - 400 * max(0, anchor - c[3] - 30))
        cands = [c for c in clusters if c[1] >= anchor - 6 and c[1] < anchor + 0.8 * page_h]
        if not cands:
            return None
        return max(cands, key=lambda c: (c[2] - c[0]) * (c[3] - c[1]) - 400 * max(0, c[1] - anchor - 30))

    # -- figures and tables ------------------------------------------------ #

    def find_captions(self) -> list[tuple[int, Block, str, str]]:
        captions: list[tuple[int, Block, str, str]] = []
        for pno, blocks in enumerate(self.page_blocks):
            for b in blocks:
                if self._drop_furniture(pno, b):
                    continue
                m = CAPTION_RE.match(b.text)
                if not m:
                    m = re.match(r"^\s*(fig(?:ure)?|table)\.?\s*(\d+[A-Za-z]?)(?:\s+|$)", b.text, re.I)
                    if m:
                        rest = b.text[m.end():].lstrip()
                        if not (rest[:1].isupper() or rest[:1] in "(["):
                            m = None
                if not m:
                    continue
                kind = m.group(1).lower()
                label = f"{'Figure' if kind.startswith('fig') else 'Table'} {m.group(2)}"
                captions.append((pno, b, label, kind))
        # a body sentence that starts with "Table 2 summarizes..." also matches;
        # keep only caption-looking blocks: font <= body+1 and either a colon or short first line
        filtered: list[tuple[int, Block, str, str]] = []
        for pno, b, label, kind in captions:
            head = b.text[:160]
            if b.size <= self.body_size + 1.3 and (
                ":" in head or len(b.text) < 220
                or re.match(r"^(FIGURE|Figure|TABLE|Table)\s*\d+", head)
            ):
                filtered.append((pno, b, label, kind))
        return filtered

    def _expand_crop_h(self, crop: list[float], group: list[float], pno: int) -> None:
        w, _ = self.page_sizes[pno]
        content_left, content_right = 40.0, w - 40.0
        blocks = self.page_blocks[pno]
        if blocks:
            content_left = min(b.x0 for b in blocks)
            content_right = max(b.x1 for b in blocks)
        width = group[2] - group[0]
        content_w = max(1.0, content_right - content_left)
        if width > content_w * 0.55:
            crop[0] = max(20.0, content_left - 8)
            crop[2] = min(w - 20.0, content_right + 8)
        else:
            crop[0] = max(15.0, group[0] - 14)
            crop[2] = min(w - 15.0, group[2] + 14)

    def extract_figures(self) -> None:
        captions = self.find_captions()
        used_boxes: list[tuple[int, tuple[float, float, float, float]]] = []
        fig_no = 0
        tab_no = 0
        pages_to_render: set[int] = set()
        for pno, cap, label, kind in captions:
            page = self.pages[pno]
            w, h = self.page_sizes[pno]
            cap_rect = fitz.Rect(cap.bbox)
            # avoid a second caption nested inside an already-used region
            if any(up == pno and fitz.Rect(box).contains(cap_rect) for up, box in used_boxes):
                continue
            visuals = [
                v for v in self.page_visuals[pno]
                if not (v.rect[2] - v.rect[0] > w * 0.9 and v.rect[3] - v.rect[1] > h * 0.9)
            ]
            above = [v for v in visuals if v.rect[3] <= cap.y0 + 4]
            below = [v for v in visuals if v.rect[1] >= cap.y1 - 4]
            # keep only content in a plausible neighbourhood
            above = [v for v in above if v.rect[3] > cap.y0 - 0.85 * h]
            below = [v for v in below if v.rect[1] < cap.y1 + 0.85 * h]
            group_above = self.pick_cluster(self.cluster_visuals(above), "above", cap.y0, h)
            group_below = self.pick_cluster(self.cluster_visuals(below), "below", cap.y1, h)
            # side-by-side panels (Fig. 2 left/right, multi-panel rows) are often
            # separate image objects; merge neighbours that share a horizontal band
            clusters_all = self.cluster_visuals(above + below)
            if group_above:
                group_above = self._merge_panels(group_above, clusters_all, h)
            if group_below:
                group_below = self._merge_panels(group_below, clusters_all, h)
            side = None
            group = None
            if label.lower().startswith("table"):
                if group_below:
                    side, group = "below", group_below
                elif group_above:
                    side, group = "above", group_above
            else:
                # A journal may print the caption above or below its figure.
                # Choose the visual cluster whose gap to the caption is smallest.
                dist_above = (cap.y0 - group_above[3]) if group_above else 1e9
                dist_below = (group_below[1] - cap.y1) if group_below else 1e9
                if group_above and dist_above <= dist_below + 25:
                    side, group = "above", group_above
                elif group_below:
                    side, group = "below", group_below
            crop: list[float] = [0, 0, w, h]
            confidence = "low"
            if label.lower().startswith("table"):
                bottom = self._table_text_bottom(pno, cap, h)
                if bottom - (cap.y1 + 3) >= 30:
                    group = None
                    side = "below"
                    crop = [40, cap.y1 + 3, w - 40, bottom]
                    confidence = "guessed"
            if group:
                confidence = "high"
                crop = [group[0], group[1], group[2], group[3]]
                self._expand_crop_h(crop, group, pno)
                if side == "above":
                    crop[1] = max(10.0, group[1] - 12)
                    crop[3] = min(h - 10.0, cap.y0 - 3)
                else:
                    crop[1] = max(10.0, cap.y1 + 3)
                    crop[3] = min(h - 10.0, group[3] + 12)
            else:
                # fall back: text-bounded region on the appropriate side
                if side is None:
                    side = "below" if label.lower().startswith("table") else "above"
                if side == "above":
                    prev = [b for b in self.page_blocks[pno] if b.y1 < cap.y0 - 4]
                    top = max((b.y1 for b in prev), default=40.0) + 8
                    crop = [40, top, w - 40, cap.y0 - 3]
                    confidence = "guessed" if crop[3] - crop[1] > 40 else "low"
                else:
                    if label.lower().startswith("table"):
                        bottom = self._table_text_bottom(pno, cap, h)
                    else:
                        nxt = [b for b in self.page_blocks[pno] if b.y0 > cap.y1 + 4]
                        bottom = min((b.y0 for b in nxt), default=h - 40) - 8
                    crop = [40, cap.y1 + 3, w - 40, bottom]
                    confidence = "guessed" if crop[3] - crop[1] > 40 else "low"
            if crop[3] - crop[1] < 35 or crop[2] - crop[0] < 35:
                # last resort: full page
                crop = [20, 20, w - 20, h - 20]
                confidence = "full-page"
                self.warnings.append(f"{label} (p.{pno+1}): could not isolate figure; used full page.")
            crop_rect = fitz.Rect(*crop)
            if label.lower().startswith("table"):
                tab_no += 1
                name = f"table{tab_no}"
                entry = {
                    "id": name,
                    "label": label,
                    "page": pno + 1,
                    "caption_en": cap.text,
                    "image": f"figs/{name}.png",
                    "bbox": [round(x, 1) for x in crop],
                    "confidence": confidence,
                }
                self.tables.append(entry)
            else:
                fig_no += 1
                name = f"fig{fig_no}"
                entry = {
                    "id": name,
                    "label": label,
                    "page": pno + 1,
                    "caption_en": cap.text,
                    "image": f"figs/{name}.png",
                    "fullpage": f"figs/page_{pno+1}.png",
                    "bbox": [round(x, 1) for x in crop],
                    "confidence": confidence,
                }
                self.figures.append(entry)
                pages_to_render.add(pno)
            self._render_crop(page, crop_rect, self.fig_dir / f"{name}.png")
            used_boxes.append((pno, tuple(crop)))
            cap.kind = "caption"
            if confidence in ("low", "guessed"):
                self.warnings.append(
                    f"{label} (p.{pno+1}): crop confidence={confidence}; inspect {name}.png and re-crop if needed."
                )
        for pno in pages_to_render:
            self._render_crop(self.pages[pno], self.pages[pno].rect, self.fig_dir / f"page_{pno+1}.png", dpi=120)
        if self.save_pages:
            for pno, page in enumerate(self.pages):
                self._render_crop(page, page.rect, self.fig_dir / f"fullpage_{pno+1}.png", dpi=100)

    def _merge_panels(
        self, group: tuple[float, float, float, float], clusters: list[tuple[float, float, float, float]], page_h: float
    ) -> tuple[float, float, float, float]:
        """Merge clusters that sit beside/under the chosen group as one figure."""
        g = list(group)
        changed = True
        while changed:
            changed = False
            for c in clusters:
                if list(c) == g:
                    continue
                v_overlap = min(g[3], c[3]) - max(g[1], c[1])
                v_gap = max(g[1], c[1]) - min(g[3], c[3])
                h_gap = max(g[0], c[0]) - min(g[2], c[2])
                h_overlap = min(g[2], c[2]) - max(g[0], c[0])
                close = (
                    (v_overlap > 0.5 * min(g[3] - g[1], c[3] - c[1]) and h_gap < 130)
                    or (h_overlap > 0.5 * min(g[2] - g[0], c[2] - c[0]) and v_gap < 24)
                )
                if close and (c[3] - c[1]) < page_h * 0.8:
                    merged = [min(g[0], c[0]), min(g[1], c[1]), max(g[2], c[2]), max(g[3], c[3])]
                    if merged != g:
                        g = merged
                        changed = True
        return tuple(g)

    def _table_text_bottom(self, pno: int, cap: Block, page_h: float) -> float:
        """Find the bottom of a table that is made of text cells rather than images."""
        bottom = cap.y1
        for b in sorted(self.page_blocks[pno], key=lambda x: x.y0):
            if b.y0 <= cap.y1 + 2 or b.kind == "caption":
                continue
            if self.is_heading(b):
                break
            lines = max(1, len(b.lines))
            alpha = sum(ch.isalpha() for ch in b.text) / max(1, len(b.text))
            if (
                len(b.text) > 90
                and alpha > 0.62
                and lines <= 6
                and b.y0 - bottom > 12
                and re.search(r"[a-z]{4,}\s+[a-z]{4,}", b.text)
            ):
                break
            if b.text.startswith(("Figure", "Fig.", "Table")):
                break
            bottom = max(bottom, b.y1)
            if bottom - cap.y1 > page_h * 0.7:
                break
        return min(bottom + 8, page_h - 20)

    @staticmethod
    def _area(r: tuple[float, float, float, float]) -> float:
        return max(0.0, r[2] - r[0]) * max(0.0, r[3] - r[1])

    def _render_crop(self, page: "fitz.Page", rect: "fitz.Rect", path: Path, dpi: int | None = None) -> None:
        pix = page.get_pixmap(clip=rect, dpi=dpi or self.dpi, alpha=False)
        pix.save(str(path))

    # -- main text --------------------------------------------------------- #

    def build_structure(self) -> dict:
        self.read_blocks()
        self.collect_visuals()
        self.extract_figures()
        # mark caption/figure/table blocks so they do not become body text
        fig_boxes = [(e["page"] - 1, fitz.Rect(e["bbox"])) for e in self.figures + self.tables]
        for pno, blocks in enumerate(self.page_blocks):
            for b in blocks:
                if CAPTION_RE.match(b.text):
                    b.kind = "caption"
                for fp, box in fig_boxes:
                    if fp == pno and box.contains(fitz.Rect(b.bbox)):
                        b.kind = "figure" if box.height > 80 else "table"
                        break

        # metadata
        meta = self.doc.metadata or {}
        first_text = "\n".join(b.text for b in self.page_blocks[0]) if self.page_blocks else ""
        title = clean_text(meta.get("title") or "") or self._guess_title()
        authors = clean_text(meta.get("author") or "")
        doi = DOI_RE.search(first_text)
        year = self._guess_year(first_text)
        front = {
            "title": title,
            "authors": authors or self._guess_authors(),
            "journal": self._guess_journal(first_text),
            "year": year.group(1) if year else "",
            "doi": doi.group(1).rstrip(".,;)") if doi else "",
            "corresponding": self._guess_corresponding(first_text),
            "front_text": first_text[:2500],
        }

        sections: list[dict] = []
        current: dict | None = None
        in_refs = False
        refs: list[str] = []
        started = False
        para_no = 0
        # Many journal layouts (e.g. Frontiers) print the abstract without an
        # "Abstract" heading. Recover it before the main heading walk.
        recovered = self._recover_abstract()
        if recovered:
            sections.append({"id": "s1", "title": "Abstract", "title_zh": "", "role": "abstract",
                             "paras": [{"id": f"p{i+1}", "page": pg, "en": txt}
                                       for i, (pg, txt) in enumerate(recovered)]})
            para_no = len(recovered)
            started = True
        for pno in range(len(self.pages)):
            for b in self.order_blocks(pno):
                if b.kind in ("caption", "figure", "table", "skip"):
                    continue
                if self.is_heading(b):
                    htxt = self.normalize_heading(b)
                    low = re.sub(r"^\d+(\.\d+)*[\.\s]+", "", htxt.lower()).strip(" .:")
                    if low.startswith(("references", "bibliography", "literature cited")):
                        in_refs = True
                        current = None
                        continue
                    if low in ("acknowledgements", "acknowledgments", "supplementary information",
                               "supplementary material", "author contributions", "funding",
                               "data availability", "competing interests", "conflict of interest"):
                        in_refs = False
                        current = None
                        continue
                    if low.startswith(("abstract", "summary")):
                        started = True
                    elif not started:
                        if low.startswith(("introduction", "background", "materials", "methods",
                                           "results", "discussion", "conclusion")):
                            started = True
                        else:
                            # front matter before abstract: skip title/authors
                            continue
                    role = self._section_role(low)
                    current = {
                        "id": f"s{len(sections)+1}",
                        "title": htxt,
                        "title_zh": "",
                        "role": role,
                        "paras": [],
                    }
                    sections.append(current)
                    continue
                if in_refs:
                    refs.extend(b.paragraphs())
                    continue
                if not started:
                    continue
                if re.match(r"^(this work was supported|funding|acknowledg|conflict of interest|"
                            r"competing interests|author contributions|data availability)", b.text.lower()):
                    continue
                if current is None:
                    # body text before any heading after the abstract: put in a catch-all
                    current = {"id": f"s{len(sections)+1}", "title": "Main text", "title_zh": "",
                               "role": "other", "paras": []}
                    sections.append(current)
                for text in b.paragraphs():
                    para_no += 1
                    current["paras"].append({
                        "id": f"p{para_no}",
                        "page": pno + 1,
                        "en": text,
                    })

        # if abstract heading never appeared, recover the abstract from the first body block
        if not any(s["role"] == "abstract" for s in sections) and sections:
            first = sections[0]
            if first["role"] == "other" and first["paras"]:
                first["role"] = "abstract"
                first["title"] = "Abstract"

        if not sections:
            self.warnings.append(
                "No body text extracted. The PDF may be image-only/scanned; run OCR "
                "(e.g. ocrmypdf) first, then re-run this script."
            )

        # clean empty sections
        sections = [s for s in sections if s["paras"]]
        for i, s in enumerate(sections, 1):
            s["id"] = f"s{i}"

        self._write_outputs(front, sections, refs)
        return {"front": front, "sections": sections, "figures": self.figures}

    def _recover_abstract(self) -> list[tuple[int, str]] | None:
        """Return [(page, paragraph)] for a heading-less abstract, else None."""
        for blocks in self.page_blocks[:2]:
            for b in blocks:
                if self.is_heading(b) and re.match(r"^(abstract|summary)\b", b.text, re.I):
                    return None
        title_text = self._guess_title()
        title_y = -1.0
        for b in self.page_blocks[0] if self.page_blocks else []:
            if b.text == title_text:
                title_y = b.y1
                break
        skip_words = re.compile(
            r"^(KEYWORDS|CITATION|COPYRIGHT|OPEN ACCESS|EDITED BY|REVIEWED BY|"
            r"\*?CORRESPONDENCE|SPECIALTY SECTION|RECEIVED|ACCEPTED|PUBLISHED|TYPE |DOI )",
            re.I,
        )
        collected: list[tuple[int, str]] = []
        collected_blocks: list[Block] = []
        for pno in range(min(2, len(self.page_blocks))):
            for b in sorted(self.page_blocks[pno], key=lambda x: x.y0):
                if pno == 0 and b.y0 <= title_y + 2:
                    continue
                if b.kind in ("caption", "figure", "table"):
                    continue
                if skip_words.match(b.text):
                    continue
                if self.is_heading(b):
                    if collected:
                        break
                    continue
                if len(b.text) < 220:
                    continue
                if re.match(r"^\d+\s*(Department|Institute|Laboratory|College|School|Center)", b.text):
                    continue
                if len(b.text) < 700 and re.search(
                    r"\b(Department|Institute|University|Laboratory|Academy|School of)\b", b.text
                ) and b.text.count(",") >= 2:
                    continue
                alpha = sum(ch.isalpha() for ch in b.text) / max(1, len(b.text))
                if alpha < 0.55 or "@" in b.text or "frontiersin.org" in b.text:
                    continue
                for txt in b.paragraphs():
                    collected.append((pno + 1, txt))
                collected_blocks.append(b)
            if collected:
                break
        if not collected:
            return None
        # keep front matter from leaking into the text sections: everything on
        # page 1 is furniture; on later scanned pages only the collected blocks
        for pno, blocks in enumerate(self.page_blocks[:2]):
            for b in blocks:
                if pno == 0 or b in collected_blocks:
                    b.kind = "skip"
        return collected

    def _guess_title(self) -> str:
        if not self.page_blocks:
            return ""
        cands: list[Block] = []
        for b in self.page_blocks[0]:
            if b.y1 < self.page_sizes[0][1] * 0.55 and b.size >= self.body_size + 3 and len(b.text) > 12:
                if not re.search(r"arxiv|doi|copyright|license", b.text, re.I):
                    cands.append(b)
        if not cands:
            return ""
        return max(cands, key=lambda b: b.size * min(len(b.text), 160)).text

    def _guess_authors(self) -> str:
        """Names between the title and abstract on page 1 (best effort)."""
        if not self.page_blocks:
            return ""
        blocks = self.page_blocks[0]
        title_y = None
        abstract_y = None
        for b in blocks:
            if title_y is None and b.text == self._guess_title():
                title_y = b.y1
            if self.is_heading(b) and re.match(r"^(abstract|summary)", b.text, re.I):
                abstract_y = b.y0
        if title_y is None:
            return ""
        cands = []
        for b in sorted(blocks, key=lambda x: x.y0):
            if b.y0 < title_y - 2:
                continue
            if abstract_y is not None and b.y0 >= abstract_y:
                break
            first = re.split(r"[∗†‡*@]|\s{2,}", b.text.strip(), maxsplit=1)[0].strip()
            first = re.sub(r"\s+(Google|University|Research|Department|Institute|Inc\.?)\b.*$", "", first, flags=re.I)
            words = first.split()
            if 2 <= len(words) <= 5 and all(w[:1].isupper() or w[:1] in "ŁŚŻŹĆ" for w in words):
                cands.append(first)
        return ", ".join(dict.fromkeys(cands))[:400]

    def _guess_year(self, first_text: str) -> re.Match | None:
        lines = [ln.strip() for ln in first_text.split("\n") if ln.strip()]
        for ln in reversed(lines[-25:]):
            if re.search(r"conference|proceedings|nature|science|cell|publish|copyright|©|journal|volume|vol\.", ln, re.I):
                m = YEAR_RE.search(ln)
                if m:
                    return m
        return None

    def _guess_journal(self, first_text: str) -> str:
        lines = [ln.strip() for ln in first_text.split("\n") if ln.strip()]
        title = self._guess_title()
        # mastheads first
        for line in lines:
            if line == title or len(line) > 120:
                continue
            if re.match(r"^(Frontiers in|Nature|Science|Cell|Bioinformatics|Journal of|Proceedings|"
                        r"Nucleic Acids|Plant (Cell|Physiology|Journal)|Genome|eLife|PNAS)\b", line, re.I):
                if not re.search(r"doi|copyright|creative|license|section of the journal|submitted to", line, re.I):
                    return re.sub(r"\s+\d{1,3}\s+frontiersin\.org.*$", "", line).strip()
        for line in lines:
            if line == title or len(line) > 120:
                continue
            if re.search(
                r"\b(Nature|Science|Cell|Bioinformatics|Genome|Journal|Frontiers|PNAS|eLife|Nucleic|Conference|Proceedings)\b",
                line, re.I,
            ):
                if not re.search(r"doi|copyright|creative|license|section of the journal|submitted to", line, re.I):
                    return line
        return ""

    def _guess_corresponding(self, first_text: str) -> str:
        lines = [ln.strip() for ln in first_text.split("\n")]
        out = []
        for i, ln in enumerate(lines):
            if re.search(r"correspond|to whom|e-?mail", ln, re.I):
                out.append(ln)
                if i + 1 < len(lines):
                    out.append(lines[i + 1])
        return " ".join(out)[:500]

    @staticmethod
    def _section_role(low: str) -> str:
        if low.startswith(("abstract", "summary")):
            return "abstract"
        if low.startswith(("introduction", "background")):
            return "introduction"
        if low.startswith(("method", "materials", "experimental", "star methods")):
            return "methods"
        if low.startswith(("result",)):
            return "results"
        if low.startswith(("discussion", "conclusion")):
            return "discussion"
        return "other"

    def _write_outputs(self, front: dict, sections: list[dict], refs: list[str]) -> None:
        data = {
            "source": {
                "pdf": str(self.pdf_path.resolve()),
                "pages": len(self.pages),
                "title": front["title"],
                "authors": front["authors"],
                "journal": front["journal"],
                "year": front["year"],
                "doi": front["doi"],
                "corresponding": front["corresponding"],
                "front_text": front["front_text"],
            },
            "abstract": next((p["en"] for s in sections if s["role"] == "abstract" for p in s["paras"]), ""),
            "sections": sections,
            "figures": self.figures,
            "tables": self.tables,
            "references": "\n".join(refs),
            "extraction": {
                "body_font_size": self.body_size,
                "paragraphs": sum(len(s["paras"]) for s in sections),
                "figures_found": len(self.figures),
                "tables_found": len(self.tables),
                "warnings": self.warnings,
            },
        }
        (self.outdir / "paper.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

        # editable templates: fill these instead of hand-building the JSON
        tpl = {
            "paper_id": "",
            "title_zh": "",
            "short_title": "",
            "one_liner": "",
            "sections": [
                {"id": s["id"], "title_zh": "", "paras": {p["id"]: "" for p in s["paras"]}}
                for s in sections
            ],
        }
        (self.outdir / "translation.template.json").write_text(
            json.dumps(tpl, ensure_ascii=False, indent=1), encoding="utf-8")
        ftpl = {
            "paper_id": "",
            "title_zh": "",
            "short_title": "",
            "one_liner": "",
            "overview": {"lead": "", "logic_summary": "", "flow": [], "note": ""},
            "figures": [
                {
                    "id": f["id"], "short": "", "one_line": "", "legend_zh": "",
                    "what": "", "meaning": "", "conclusion": "",
                    "panels": [], "caveats": [], "connection": "", "tags": [],
                    "caption_en": f["caption_en"],
                }
                for f in self.figures
            ],
        }
        (self.outdir / "figures.template.json").write_text(
            json.dumps(ftpl, ensure_ascii=False, indent=1), encoding="utf-8")
        mtpl = {"paper_id": "", "title_zh": "", "short_title": "", "one_liner": "",
                "overview": "", "route": [], "methods": [], "notes": []}
        (self.outdir / "methods.template.json").write_text(
            json.dumps(mtpl, ensure_ascii=False, indent=1), encoding="utf-8")

        lines = []
        lines.append(f"TITLE: {front['title']}")
        lines.append(f"AUTHORS: {front['authors']}")
        lines.append(f"JOURNAL: {front['journal']}  YEAR: {front['year']}  DOI: {front['doi']}")
        lines.append("")
        for s in sections:
            lines.append(f"\n## [{s['id']}] {s['title']}  ({s['role']})")
            for p in s["paras"]:
                lines.append(f"\n[{p['id']} p.{p['page']}] {p['en']}")
        for f in self.figures:
            lines.append(f"\n\n## {f['label']} (p.{f['page']}) -> {f['image']}\n{f['caption_en']}")
        for t in self.tables:
            lines.append(f"\n\n## {t['label']} (p.{t['page']}) -> {t['image']}\n{t['caption_en']}")
        if refs:
            lines.append("\n\n## REFERENCES\n" + "\n".join(refs))
        (self.outdir / "paper.txt").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf", type=Path)
    ap.add_argument("-o", "--outdir", type=Path, required=True)
    ap.add_argument("--dpi", type=int, default=260, help="figure raster DPI (default 260)")
    ap.add_argument("--pages", action="store_true", help="also render every full page at 100 dpi")
    args = ap.parse_args()

    if not args.pdf.exists():
        sys.exit(f"PDF not found: {args.pdf}")
    args.outdir.mkdir(parents=True, exist_ok=True)
    ex = PaperExtractor(args.pdf, args.outdir, dpi=args.dpi, save_pages=args.pages)
    result = ex.build_structure()
    print(f"OK  pages={len(ex.pages)}  paragraphs={sum(len(s['paras']) for s in result['sections'])}  "
          f"figures={len(result['figures'])}  tables={len(ex.tables)}")
    print(f"    -> {args.outdir / 'paper.json'}")
    if ex.warnings:
        print(f"    {len(ex.warnings)} warning(s):")
        for w in ex.warnings[:8]:
            print("      -", w)


if __name__ == "__main__":
    main()
