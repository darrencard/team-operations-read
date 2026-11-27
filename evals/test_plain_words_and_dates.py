"""Plain words in the README and SKILL.md, and dates that never break on the sample page."""

import importlib
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "team-operations-read"
sys.path.insert(0, str(SKILL / "scripts"))
render = importlib.import_module("render_html")

BRIDGE = "A bet is a project you expect to move a number; its bar is the target its landing brief sets."
SKILL_WORD = "Use the user's word, project or bet; the record key stays `bet`."
DATE = re.compile(r"(?<![\w-])\d{4}-\d{2}-\d{2}(?![\w-])")


def prose(text: str) -> str:
    """The text a reader reads as words: code blocks, code spans and the two bridge sentences taken out."""
    text = re.sub(r"```.*?```", "", text, flags=re.S).replace(BRIDGE, "").replace(SKILL_WORD, "")
    return re.sub(r"`[^`]*`", "", text)


class PlainWords(unittest.TestCase):
    def setUp(self):
        self.readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")

    def test_the_readme_defines_bet_and_bar_once_under_its_opening_line(self):
        opening = re.search(r"^A free Claude skill[^\n]*\n\n([^\n]*)\n", self.readme, re.M)
        self.assertEqual(opening.group(1), BRIDGE)
        self.assertEqual(self.readme.count(BRIDGE), 1)

    def test_the_skill_uses_the_users_word_and_keeps_the_key(self):
        self.assertIn(SKILL_WORD, self.skill)

    def test_no_prose_says_bet_or_bar(self):
        for name, text in (("README.md", self.readme), ("SKILL.md", self.skill)):
            words = re.sub(r"<bet[^>]*>|landing/<bet>\.json|share bar", "", prose(text))
            self.assertEqual(re.findall(r"\b(?:bets?|bars?)\b", words, re.I), [], name)


class DatesHoldTogether(unittest.TestCase):
    def test_keep_dates_wraps_text_and_leaves_attributes(self):
        text = "Since 2026-09-07 14:05, to 2026-11-15, from 2026-11-16T16:00."
        out = render.keep_dates(f'<head><title>2026-09-07</title></head><body><h1 aria-label="since 2026-09-07">{text}</h1></body>')
        self.assertIn("<title>2026-09-07</title>", out)
        self.assertIn('aria-label="since 2026-09-07"', out)
        held = ['<span class="nw">2026-09-07 14:05</span>', '<span class="nw">2026-11-15</span>', '<span class="nw">2026-11-16T16:00</span>']
        self.assertIn("Since {}, to {}, from {}.".format(*held), out)

    def test_every_date_on_the_sample_page_is_held_on_one_line(self):
        page = (ROOT / "examples" / "acme" / "team-operations-read.html").read_text(encoding="utf-8")
        held = re.sub(r'<span class="nw">\d{4}-\d{2}-\d{2}(?:[ T][\d:]+Z?)?</span>', "", page.split("<body>", 1)[1])
        loose = [t for t in re.findall(r">([^<]+)<", held) if DATE.search(t)]
        self.assertTrue(DATE.search(page))
        self.assertEqual(loose, [])


if __name__ == "__main__":
    unittest.main()
