"""Full column: every title and text block runs the content column, the scorecard frame's width.

The site's rule since 2026-11-25. The page's own CSS caps no text, and it overrides the vendored template's
intro cap and svgkit's caption cap after their rules, so neither hash-pinned file changes on disk.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/team-operations-read/scripts/render_html.py"
SAMPLE = ROOT / "examples" / "acme" / "team-operations-read.html"
OVERRIDE = ".solo h1,.solo h2,.solo h3,.solo .lede,.solo .next,.solo p,.solo li,.solo .sk figcaption{max-width:none}"


def page_css() -> str:
    return re.search(r'PAGE_CSS = """(.*?)"""', SCRIPT.read_text(encoding="utf-8"), re.S).group(1)


class FullColumn(unittest.TestCase):
    def test_the_page_css_caps_no_text(self) -> None:
        caps = [
            (sel.strip(), value.strip())
            for sel, body in re.findall(r"([^{}]*)\{([^{}]*)\}", page_css())
            for value in re.findall(r"(?<![\w(-])max-width:([^;]+)", body)
            if value.strip() != "none"
        ]
        # Only the footer keeps a width, the content column's own 1120px.
        self.assertEqual(caps, [(".foot", "1120px")])
        for sel in (".solo h1", ".solo .lede", ".solo p"):
            self.assertIn(sel, OVERRIDE)

    def test_the_sample_overrides_the_vendored_caps_after_them(self) -> None:
        page = SAMPLE.read_text(encoding="utf-8")
        at = page.index(OVERRIDE)
        self.assertGreater(at, page.index(".lede{"), "the template's intro cap comes first")
        self.assertGreater(at, page.index(".sk figcaption{"), "svgkit's caption cap comes first")
        self.assertIn(".solo h1{text-wrap:balance}.solo .lede,.solo p,.solo li,.solo .sk figcaption{text-wrap:pretty}", page)


if __name__ == "__main__":
    unittest.main()
