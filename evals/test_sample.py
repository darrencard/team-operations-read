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

import render_html
from render_html import floor_fonts
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
        frame = svgkit.frames_in(page)[0]
        for word in ("--landed", "--watch", "--stalled", "--brass", 'class="sc-o"', 'class="st '):
            self.assertNotIn(word, frame, "the rows have no status colour, and no person's call to paint brass")
        css = page.split("</style>", 1)[0].split(floor_fonts(svgkit.CSS + svgkit.SCORECARD_CSS), 1)[1]
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
            'class="sc scg"',
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
    """The areas read as scorecard rows: a band as a band, an exact level as exact; the unread areas as one line."""

    @classmethod
    def setUpClass(cls):
        cls.page = (SAMPLE / f"{STEM}.html").read_text(encoding="utf-8")
        cls.doc = json.loads((SAMPLE / f"{STEM}.json").read_text(encoding="utf-8"))
        cls.read = [d for d in cls.doc["dimensions"] if d["read"] != "not_read"]
        cls.visuals = []

    def css(self) -> str:
        return self.page.split("<style>", 1)[1].split("</style>", 1)[0]

    def test_the_visual_draws_only_figures_the_page_prints(self):
        self.assertEqual(svgkit.unprinted(self.page), [])

    def test_one_frame_one_row_per_area_read_and_the_unread_as_one_line(self):
        frames = svgkit.frames_in(self.page)
        self.assertEqual(len(frames), 1)
        self.assertEqual(re.findall(r'<span class="sc-n">([^<]+)</span>', frames[0]), [html.escape(d["name"]) for d in self.read])
        unread = len(self.doc["dimensions"]) - len(self.read)
        self.assertIn(f'<div class="sc-x">{unread} areas not visible in these exports</div>', frames[0])
        self.assertEqual(frames[0].count('<span class="sc-w ink">Start here</span>'), 1)
        start = next(d for d in self.read if d["id"] == self.doc["start_here"]["dimension"])
        self.assertRegex(frames[0], rf'<span class="sc-n">{re.escape(start["name"])}</span>.*?<span class="sc-w ink">Start here</span>')

    def test_the_picture_is_exactly_as_precise_as_the_figure(self):
        frame = svgkit.frames_in(self.page)[0]
        lines = re.findall(r'<span class="sc-l"><b>([^<]+)</b></span>', frame)
        self.assertEqual(len(lines), len(self.read))
        for line, d in zip(lines, self.read, strict=True):
            self.assertRegex(line, r"^(level \d|level \d or (above|below)|level \d to \d|mixed evidence)$")
            words, filled, dashed = render_html.band(d)
            self.assertEqual(line, words)
            # Never less or more precise than the data: an exact level prints and draws exactly, a band as a band.
            if d["read"] == "stage":
                self.assertEqual((line, filled, dashed), (f"level {d['stage']}", d["stage"], 0))
            else:
                self.assertGreater(dashed, 0, d["name"])
        pips = re.findall(r'<svg class="sc-pp".*?</svg>', frame)
        self.assertEqual(len(pips), len(self.read))
        for svg, d in zip(pips, self.read, strict=True):
            _, filled, dashed = render_html.band(d)
            self.assertEqual(svg.count('class="on"'), filled)
            self.assertEqual(svg.count('class="off dash"'), dashed)
        self.assertEqual(render_html.band({"read": "range", "floor": 1, "ceiling": 2}), ("level 2 or below", 1, 1))
        self.assertEqual(render_html.band({"read": "range", "floor": 3, "ceiling": 5}), ("level 3 or above", 3, 2))
        self.assertEqual(render_html.band({"read": "stage", "stage": 3}), ("level 3", 3, 0))
        orchestration = next(d for d in self.read if d["id"] == "team_orchestration")
        self.assertEqual(render_html.band(orchestration), ("level 3", 3, 0))

    def test_the_visual_states_the_answer(self):
        labels = [html.unescape(x) for x in re.findall(r'role="img" aria-label="([^"]+)"', self.page)]
        self.assertEqual(
            labels,
            ["These exports show 6 of the 27 Team Operations areas and can't see the other 21; start with Roadmap Discipline, read at level 2 or below."],
        )

    # The scorecard grammar (landing-loop tools/SCORECARD-ROLLOUT.md, svgkit 1.2.0)

    def test_no_text_inside_a_picture_and_no_picture_scales(self):
        self.assertEqual(svgkit.svgs_with_text(self.page), [], "text inside an SVG")
        self.assertEqual(svgkit.scaled_svgs_in(self.page), [], "a picture with a viewBox would scale")

    def test_labels_render_12px_and_names_14px(self):
        css = self.css()
        self.assertEqual(set(svgkit.font_sizes(css)), {"var(--sc-m)", "var(--sc-n)"})
        self.assertIn("--sc-m:calc(12px / var(--sc-z))", css)
        self.assertIn("--sc-n:calc(14px / var(--sc-z))", css)
        self.assertIn(".scg{--sc-z:1;", css, "a sample page has no zoom")

    def test_no_box_inside_the_frame_and_no_overlap(self):
        self.assertEqual(svgkit.boxes_in_frames(self.page, self.css()), [])
        self.assertNotIn('class="chip', self.page.split("<details><summary>For your engineers", 1)[0])
        self.assertNotIn("position:absolute", svgkit.SCORECARD_CSS)
        self.assertNotIn("border", re.search(r"\.status\{[^}]*\}", render_html.PAGE_CSS).group(0), "words are text, never boxed chips")

    def test_no_legacy_svgkit_primitive_draws_on_the_page(self):
        import warnings

        self.assertEqual(svgkit.legacy_in(self.page), [])
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            render_html.page(self.doc)

    def test_public_copy_uses_the_plain_words(self):
        public = svgkit.page_text(self.page.split("<details><summary>For your engineers", 1)[0]).lower()
        for word in ("dimension", "stage", "rubric", "bet ", "bets", "record key", "landing/", "eval", "spec template", "book a"):
            self.assertNotIn(word, public)
        md = (SAMPLE / f"{STEM}.md").read_text(encoding="utf-8").split("## For your engineers", 1)[0].lower()
        for word in ("dimension", "stage", "rubric", "bet ", "record key", "book a"):
            self.assertNotIn(word, md)
        # The words a reader outside the loop does not know, as whole words.
        for text in (public, md):
            self.assertEqual(re.findall(r"\b(records?|bets?|the bar|prds?|arr|tokens?)\b", text), [])

    def test_no_text_smaller_than_11px_at_any_width(self):
        css = " ".join(re.findall(r"<style>(.*?)</style>", self.page, re.S) + re.findall(r'style="([^"]*)"', self.page))
        sizes = [float(m) for m in re.findall(r"(?:font-size:\s*|font:[^;{}]*?)(\d+(?:\.\d+)?)px", css)]
        sizes += [float(m) for m in re.findall(r'font-size="(\d+(?:\.\d+)?)"', self.page)]
        self.assertTrue(sizes)
        self.assertGreaterEqual(min(sizes), 11)
        # The vendored template is untouched on disk: the page raises its small sizes as it inlines them.
        template = ROOT / "skills/team-operations-read/assets/vendor/template.html"
        self.assertIn("font:400 10px/16px", template.read_text(encoding="utf-8"))

    def test_header_prints_the_plain_name_and_the_fold_the_code_name(self):
        header = re.search(r'<header class="sk-hdr">.*?</header>', self.page, re.S).group(0)
        self.assertIn("<span>Team operations read</span>", header)
        self.assertNotIn("team-operations-read", header)
        self.assertIn("<code>team-operations-read</code>", self.page.split("<details><summary>For your engineers", 1)[1])
        md = (SAMPLE / f"{STEM}.md").read_text(encoding="utf-8")
        self.assertIn("Skill: `team-operations-read`", md.split("## For your engineers", 1)[1])


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
