#!/usr/bin/env python3
"""Shared helpers for the three HTML builders."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"JSON not found: {path}")
    except json.JSONDecodeError as e:
        sys.exit(f"Invalid JSON in {path}: {e}")


def paper_id(paper: dict, given: str = "") -> str:
    if given:
        return given
    key = paper.get("source", {}).get("doi") or paper.get("source", {}).get("title") or "paper"
    return hashlib.md5(key.encode("utf-8")).hexdigest()[:8]


def paper_meta(paper: dict, translation: dict | None = None) -> dict:
    src = paper.get("source", {})
    tr = translation or {}
    return {
        "id": paper_id(paper, tr.get("paper_id", "")),
        "title": src.get("title", ""),
        "title_zh": tr.get("title_zh", "") or src.get("title", ""),
        "short_title": tr.get("short_title", "") or tr.get("title_zh", "") or src.get("title", ""),
        "one_liner": tr.get("one_liner", ""),
        "authors": tr.get("authors") or src.get("authors", ""),
        "journal": tr.get("journal") or src.get("journal", ""),
        "year": str(tr.get("year") or src.get("year", "")),
        "doi": tr.get("doi") or src.get("doi", ""),
        "source_file": Path(src.get("pdf", "")).name,
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def count_stats(sections: list[dict]) -> dict:
    paras = [p for s in sections for p in s.get("paras", [])]
    en = " ".join(p.get("en", "") for p in paras)
    zh = " ".join(p.get("zh", "") for p in paras)
    words_en = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'’\-]*", en))
    chars_zh = len(re.findall(r"[\u4e00-\u9fff]", zh))
    minutes = max(1, round(words_en / 230 + chars_zh / 450))
    return {
        "sections": len(sections),
        "paras": len(paras),
        "words_en": words_en,
        "chars_zh": chars_zh,
        "minutes": minutes,
    }


def inject(template: Path, theme: Path, script: Path, data: dict, page_title: str, title_text: str,
           nav_script: Path | None = None) -> str:
    tpl = template.read_text(encoding="utf-8")
    css = theme.read_text(encoding="utf-8")
    js = script.read_text(encoding="utf-8")
    nav = nav_script.read_text(encoding="utf-8") if nav_script else ""
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = (tpl
            .replace("/*__THEME__*/", css)
            .replace("/*__NAV__*/", nav)
            .replace("/*__SCRIPT__*/", js)
            .replace("__DATA__", payload)
            .replace("__PAGE_TITLE__", page_title)
            .replace("__PAPER_TITLE__", title_text))
    if "__DATA__" in html or "__PAGE_TITLE__" in html:
        sys.exit("Template placeholder was not replaced; check the template files.")
    return html


def write_html(out: Path, html: str) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"OK  {out}  ({out.stat().st_size / 1024:.0f} KB)")
