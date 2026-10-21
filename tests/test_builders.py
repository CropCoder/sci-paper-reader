"""Smoke tests for the three HTML builders."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"


class BuilderSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="spr-test-"))
        for name in ("paper.json", "translation.json", "figures.json", "methods.json"):
            shutil.copy(FIXTURES / name, self.tmp / name)
        (self.tmp / "figs").mkdir()
        shutil.copy(FIXTURES / "figs" / "fig1.png", self.tmp / "figs" / "fig1.png")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_script(self, name: str, *args: str) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / name), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)

    def test_builders_emit_pages(self) -> None:
        self.run_script(
            "build_en2cn.py",
            "--paper", str(self.tmp / "paper.json"),
            "--translation", str(self.tmp / "translation.json"),
            "--out", str(self.tmp / "job.en2cn.html"),
        )
        self.run_script(
            "build_fig.py",
            "--paper", str(self.tmp / "paper.json"),
            "--figures", str(self.tmp / "figures.json"),
            "--out", str(self.tmp / "job.fig.html"),
        )
        self.run_script(
            "build_method.py",
            "--paper", str(self.tmp / "paper.json"),
            "--methods", str(self.tmp / "methods.json"),
            "--out", str(self.tmp / "job.method.html"),
        )

        en = (self.tmp / "job.en2cn.html").read_text(encoding="utf-8")
        fig = (self.tmp / "job.fig.html").read_text(encoding="utf-8")
        method = (self.tmp / "job.method.html").read_text(encoding="utf-8")
        for html in (en, fig, method):
            self.assertIn("const DATA =", html)
            self.assertIn("site-nav", html)
            self.assertIn("Times New Roman", html)
        self.assertIn("逐段精读", en)
        self.assertIn("Figure 1", fig)
        self.assertIn("测试方法", method)


if __name__ == "__main__":
    unittest.main()
