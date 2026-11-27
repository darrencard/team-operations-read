"""House rules for every file in the repository: versions, wording, the vendored files and the README."""

from __future__ import annotations

import hashlib
import json
import re
import tomllib
import unittest

from helpers import ROOT, SKILL

from framework import DIMENSIONS
from read import VERSION

TEXT = [
    p
    for p in ROOT.rglob("*")
    if p.is_file() and p.suffix in {".md", ".py", ".json", ".csv", ".toml", ".yml", ".txt"} and not {".git", ".ruff_cache", "vendor", "run"} & set(p.parts)
]
BANNED = re.compile(r"\b(AI-powered|unlock|supercharge|seamless|robust|get started|sign up|leverag(?:e|es|ed|ing))\b", re.I)
# The overclaim check and the tests that exercise it name the banned words.
ALLOWED_BANNED = {"check_claims.py", "test_repo.py", "test_pipeline.py"}


class Versions(unittest.TestCase):
    def test_every_version_field_is_0_3_0(self):
        plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
        skill = re.search(r'version: "([^"]+)"', (SKILL / "SKILL.md").read_text(encoding="utf-8")).group(1)
        sample = json.loads((ROOT / "examples/acme/team-operations-read.json").read_text(encoding="utf-8"))["version"]
        self.assertEqual({plugin["version"], project, skill, VERSION, sample}, {"0.3.0"})
        self.assertEqual(plugin["name"], "team-operations-read")

    def test_changelog_has_a_dated_entry(self):
        text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertEqual(re.search(r"^## (.+)$", text, re.M).group(1), "0.3.0, 2026-11-26")

    def test_skill_frontmatter(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\nname: team-operations-read\n"))
        self.assertLessEqual(len(re.search(r"^description: (.+)$", text, re.M).group(1)), 1024)

    def test_27_dimensions_six_functions(self):
        self.assertEqual(len(DIMENSIONS), 27)
        self.assertEqual(len({d[2] for d in DIMENSIONS}), 6)


class Wording(unittest.TestCase):
    def test_no_em_or_en_dashes(self):
        for p in TEXT + [ROOT / "examples/acme/team-operations-read.html"]:
            text = p.read_text(encoding="utf-8")
            self.assertNotIn(chr(0x2014), text, p)
            self.assertNotIn(chr(0x2013), text, p)

    def test_no_banned_words(self):
        for p in TEXT:
            if p.name in ALLOWED_BANNED:
                continue
            m = BANNED.search(p.read_text(encoding="utf-8"))
            self.assertIsNone(m, f"{p}: {m and m.group(0)}")

    def test_full_framework_name_in_prose(self):
        for p in [ROOT / "README.md", SKILL / "SKILL.md", ROOT / "CHANGELOG.md"]:
            self.assertIsNone(re.search(r"\b(F1|F2|F3)\b", p.read_text(encoding="utf-8")), p)


class Vendored(unittest.TestCase):
    def test_vendored_files_match_their_pins(self):
        pins = json.loads((SKILL / "VENDORED.json").read_text(encoding="utf-8"))
        self.assertEqual(pins["commit"], "366da9bfede540ec19e9164ad5ad17ce28c1d06b")
        for rel, pin in pins["files"].items():
            self.assertEqual(hashlib.sha256((SKILL / rel).read_bytes()).hexdigest(), pin["sha256"], rel)

    def test_brief_parser_is_the_canonical_one(self):
        digest = hashlib.sha256((SKILL / "scripts/vendor/landing_brief.py").read_bytes()).hexdigest()
        self.assertTrue(digest.startswith("2d13573543c74ebe"))


class Readme(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (ROOT / "README.md").read_text(encoding="utf-8")

    def test_sections_in_order(self):
        order = ["```text", "## Try it on Acme", "## Install", "## Reads and writes", "## Limits", "## Licence"]
        at = [self.text.index(h) for h in order]
        self.assertEqual(at, sorted(at))

    def test_install_maturity_and_trademark(self):
        self.assertIn("/plugin marketplace add darrencard/landing-loop", self.text)
        self.assertIn("/plugin install team-operations-read@landing-loop", self.text)
        self.assertIn("Not yet run on a real team's data.", self.text)
        self.assertIn("Claude and Claude Code are trademarks of Anthropic, PBC. These skills are independent and not affiliated with or endorsed by Anthropic.", self.text)
        self.assertIn("reads the team that runs the bets", self.text)


if __name__ == "__main__":
    unittest.main()
