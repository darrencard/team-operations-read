"""The Acme sample: one command reproduces it byte for byte, every figure carries its source and window,
status words stay did-it-land's, and the read never touches a Landing Loop record."""

from __future__ import annotations

import html
import json
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from helpers import ROOT

from vendored import load

svgkit = load("svgkit")

SAMPLE = ROOT / "examples" / "acme"
STEM = "team-operations-read"
STATUS = re.compile(r"\b(landed|watch|stalled)\b", re.I)


def readme_command() -> list[str]:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    block = readme.split("## Try it on Acme", 1)[1].split("```bash", 1)[1].split("```", 1)[0]
    line = next(x for x in block.splitlines() if "read.py" in x)
    return shlex.split(line)


def visible(page: str) -> str:
    page = re.sub(r"<style>.*?</style>", " ", page, flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", " ", page))


class Reproduces(unittest.TestCase):
    def test_readme_command_reproduces_the_committed_files(self):
        cmd = readme_command()
        self.assertEqual(cmd[:2], ["python3", "skills/team-operations-read/scripts/read.py"])
        with tempfile.TemporaryDirectory() as tmp:
            args = list(cmd[1:])
            args[args.index("--out") + 1] = tmp
            started = time.monotonic()
            r = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True, check=False)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertLess(time.monotonic() - started, 60)
            for ext in ("html", "md", "json"):
                self.assertEqual((Path(tmp) / f"{STEM}.{ext}").read_bytes(), (SAMPLE / f"{STEM}.{ext}").read_bytes(), ext)


class Figures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads((SAMPLE / f"{STEM}.json").read_text(encoding="utf-8"))

    def test_every_figure_has_value_unit_source_window_and_as_of(self):
        self.assertTrue(self.doc["figures"])
        for fid, f in self.doc["figures"].items():
            self.assertIsInstance(f["value"], (int, float), fid)
            for key in ("unit", "source", "as_of"):
                self.assertTrue(str(f[key]).strip(), (fid, key))
            self.assertLessEqual(f["window"]["from"], f["window"]["to"], fid)
            self.assertEqual(f["as_of"], self.doc["as_of"], fid)

    def test_sample_is_marked_illustrative(self):
        self.assertTrue(self.doc["illustrative"])
        page = (SAMPLE / f"{STEM}.html").read_text(encoding="utf-8")
        self.assertIn('<span class="sk-ill">Illustrative</span>', page)
        self.assertIn(":root{--ill:#74A5DA}", page, "the Illustrative tag is blue")
        for system in self.doc["systems"].values():
            self.assertTrue(system.startswith("Illustrative"), system)


class StatusWords(unittest.TestCase):
    def test_no_bet_status_word_in_any_output(self):
        page = (SAMPLE / f"{STEM}.html").read_text(encoding="utf-8")
        for name, text in [
            ("html", visible(page)),
            ("md", (SAMPLE / f"{STEM}.md").read_text(encoding="utf-8")),
            ("json", (SAMPLE / f"{STEM}.json").read_text(encoding="utf-8")),
        ]:
            m = STATUS.search(text)
            self.assertIsNone(m, f"{name}: {m and m.group(0)}")

    def test_page_uses_no_status_colour_and_brass_only_for_a_persons_call(self):
        page = (SAMPLE / f"{STEM}.html").read_text(encoding="utf-8")
        # The four-bar brand mark carries its brass bar; the rest of the page uses brass only in the next-step box.
        body = re.sub(r"<svg.*?</svg>", "", page.split("</style>", 1)[1], flags=re.S)
        self.assertIsNone(re.search(r'class="[^"]*\b(st|rd|ac)\b', body))
        for word in ("--landed", "--watch", "--stalled", "--brass"):
            self.assertNotIn(word, body)
        for svg in svgkit.visuals_in(page):
            for word in ("--landed", "--watch", "--stalled", "--brass", "sk-st"):
                self.assertNotIn(word, svg, "the grid has no status colour, and no person's call to paint brass")
        css = page.split("</style>", 1)[0].split(svgkit.CSS, 1)[1]
        brass = re.findall(r"[^}]*var\(--brass[^}]*}", css)
        self.assertTrue(brass and all(r.lstrip().startswith((".next", "}.next")) for r in brass), "brass is only the person who decides the next step")
        self.assertEqual(body.count('class="o"'), 1)
        self.assertEqual(body.count('class="next"'), 1)

    def test_page_is_self_contained(self):
        page = (SAMPLE / f"{STEM}.html").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r'(src|href)="(https?:)?//', page))
        self.assertNotIn("<link", page)
        self.assertNotIn("<script", page)


ORG_CHART = {"Head of Product, Quoting squad", "Lead, Quoting squad", "Tech lead, Quoting squad", "Product manager, Quoting squad"}
ENTRY = ["read.py", "check_claims.py", "from_csv.py", "from_github.py", "from_linear.py"]


class Scannable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = (SAMPLE / f"{STEM}.html").read_text(encoding="utf-8")

    def test_the_page_follows_the_sample_anatomy(self):
        body = self.page.split('<main class="solo">', 1)[1]
        order = [
            'class="sk-hdr"',
            "<h1>Start with Roadmap Discipline.</h1>",
            'class="status"',
            'class="sk-wide"',
            "What to do next",
            'class="cols"',
            "<details><summary>Each area in full</summary>",
            "<details><summary>Every figure, with its source</summary>",
            "<details><summary>For your engineers</summary>",
        ]
        at = [body.index(x) for x in order]
        self.assertEqual(at, sorted(at))
        top = body.split('<section class="slide">', 1)[0]
        self.assertNotIn("<details", top)
        self.assertNotIn("<table", body.split("<details>", 1)[0], "every table is folded")
        words = len(svgkit.page_text(top).split())
        self.assertLess(words, 250, "the unfolded top must read in 30 seconds")

    def test_one_owner_from_the_org_chart(self):
        doc = json.loads((SAMPLE / f"{STEM}.json").read_text(encoding="utf-8"))
        self.assertIn(doc["decides"], ORG_CHART)
        self.assertEqual(re.findall(r'class="o">([^<]*)<', self.page), ["Head of Product, Quoting squad"])
        for text in (self.page, (SAMPLE / f"{STEM}.md").read_text(encoding="utf-8")):
            self.assertIsNone(re.search(r"\bVP\b|on-call|Engineering\.", text))

    def test_selection_and_focus_print_in_ink_not_status_green(self):
        css = self.page.split("</style>", 1)[0]
        own = css.rsplit("::selection", 1)[1]
        self.assertTrue(own.startswith("{background:var(--t1)"))
        self.assertIn(":focus-visible{outline:2px solid var(--t1)", own)
        self.assertLess(css.find("::selection{background:var(--landed)"), css.rfind("::selection{background:var(--t1)"))


class Visual(unittest.TestCase):
    """The area grid: every one of the 27 areas, read ones shaded by level, the rest hatched, the place to start ringed."""

    @classmethod
    def setUpClass(cls):
        cls.page = (SAMPLE / f"{STEM}.html").read_text(encoding="utf-8")
        cls.doc = json.loads((SAMPLE / f"{STEM}.json").read_text(encoding="utf-8"))
        cls.visuals = svgkit.visuals_in(cls.page)

    def test_a_wide_and_a_tall_variant(self):
        self.assertEqual(len(self.visuals), 2)
        self.assertIn('class="sk-wide"', self.visuals[0])
        self.assertIn('class="sk-tall"', self.visuals[1])
        self.assertIn('viewBox="0 0 720 ', self.visuals[0])
        self.assertIn('viewBox="0 0 340 ', self.visuals[1])

    def test_the_visual_draws_only_figures_the_page_prints(self):
        self.assertEqual(svgkit.unprinted(self.page), [])

    def test_it_draws_every_area_and_hatches_the_unread_ones(self):
        unread = sum(1 for d in self.doc["dimensions"] if d["read"] == "not_read")
        for svg in self.visuals:
            texts = " ".join(svgkit.texts_in(svg))
            for d in self.doc["dimensions"]:
                for word in d["name"].split():
                    self.assertIn(word, texts, d["name"])
            hid = re.search(r'<pattern id="([^"]+)"', svg).group(1)
            self.assertEqual(svg.count(f'fill="url(#{hid})"'), unread + 1, "one hatched strip per unread area, and the key's")
            self.assertEqual(svgkit.texts_in(svg).count("START HERE"), 1)
            self.assertIn("CAN'T SEE FROM THESE EXPORTS", svgkit.texts_in(svg))
        ids = re.findall(r'<pattern id="([^"]+)"', self.page)
        self.assertEqual(len(ids), len(set(ids)), "each SVG has its own hatch id")

    def test_the_visual_states_the_answer(self):
        for svg in self.visuals:
            self.assertIn('role="img"', svg)
            label = html.unescape(re.search(r'aria-label="([^"]+)"', svg).group(1))
            self.assertEqual(
                label,
                "These exports show 6 of the 27 Team Operations areas and can't see the other 21; start with Roadmap Discipline, read at level 2 or below.",
            )

    def test_public_copy_uses_the_plain_words(self):
        public = svgkit.page_text(self.page.split("<details><summary>For your engineers", 1)[0]).lower()
        public += " " + " ".join(t for svg in self.visuals for t in svgkit.texts_in(svg)).lower()
        for word in ("dimension", "stage", "rubric", "bet ", "bets", "record key", "landing/", "eval", "spec template", "book a"):
            self.assertNotIn(word, public)
        md = (SAMPLE / f"{STEM}.md").read_text(encoding="utf-8").split("## For your engineers", 1)[0].lower()
        for word in ("dimension", "stage", "rubric", "bet ", "record key", "book a"):
            self.assertNotIn(word, md)


class PythonFloor(unittest.TestCase):
    def test_every_entry_script_checks_the_version_before_any_other_import(self):
        import ast

        for name in ENTRY:
            tree = ast.parse((ROOT / "skills/team-operations-read/scripts" / name).read_text(encoding="utf-8"))
            body = [n for n in tree.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))]
            kinds = [type(n).__name__ for n in body[:3]]
            self.assertEqual(kinds, ["ImportFrom", "Import", "If"], name)
            self.assertEqual(body[0].module, "__future__", name)
            self.assertEqual([a.name for a in body[1].names], ["sys"], name)
            self.assertIn("version_info", ast.unparse(body[2].test), name)

    def test_an_old_python_gets_the_plain_message(self):
        old = next((p for p in ("/usr/bin/python3", "/usr/local/bin/python3.9", "/usr/bin/python3.9") if Path(p).exists()), None)
        if not old:
            self.skipTest("no Python older than 3.11 on this machine")
        probe = subprocess.run([old, "-c", "import sys; print(sys.version_info >= (3, 11))"], capture_output=True, text=True, check=False)
        if probe.stdout.strip() != "False":
            self.skipTest("the system python3 is 3.11 or later")
        for name in ENTRY:
            r = subprocess.run([old, str(ROOT / "skills/team-operations-read/scripts" / name), "--help"], capture_output=True, text=True, check=False)
            self.assertEqual(r.returncode, 1, name)
            self.assertEqual(r.stderr.strip(), "team-operations-read needs Python 3.11 or later; try python3.12", name)


class OutsideTheLoop(unittest.TestCase):
    def test_writes_no_record_key_and_leaves_a_record_byte_identical(self):
        record = {
            "schema": "landing-loop/1",
            "bet": "quote-drafting",
            "brief": {"path": "briefs/quote-drafting.md", "sha256": "0" * 64},
            "landed": {"status": "landed"},
        }
        with tempfile.TemporaryDirectory() as t:
            work = Path(t)
            (work / "landing").mkdir()
            rec = work / "landing" / "quote-drafting.json"
            rec.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
            before = rec.read_bytes()
            shutil.copytree(SAMPLE / "data", work / "data")
            script = ROOT / "skills/team-operations-read/scripts/read.py"
            r = subprocess.run(
                [sys.executable, str(script), "--data", "data", "--as-of", "2026-11-20", "--out", "run"], cwd=work, capture_output=True, text=True, check=False
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(rec.read_bytes(), before)
            self.assertEqual(sorted(p.name for p in (work / "landing").iterdir()), ["quote-drafting.json"])
            self.assertEqual(sorted(p.name for p in work.iterdir()), ["data", "landing", "run"])
            out = json.loads((work / "run" / "read.json").read_text(encoding="utf-8"))
            self.assertNotIn("schema", out)
            self.assertNotIn("bet", out)


if __name__ == "__main__":
    unittest.main()
