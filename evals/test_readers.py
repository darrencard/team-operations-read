"""Readers: GitHub pull request JSON and the generic CSV mapper, plus optional columns."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

from from_csv import convert as map_csv
from from_github import convert as from_gh
from helpers import AS_OF, SCRIPTS

from read import build, render

PRS = [
    {
        "number": 1,
        "createdAt": "2026-11-02T09:00:00Z",
        "mergedAt": "2026-11-03T09:00:00Z",
        "isDraft": False,
        "author": {"login": "dev-a", "is_bot": False},
        "labels": [{"name": "squad:Quotes"}],
        "reviews": [
            {"author": {"login": "dev-a"}, "state": "COMMENTED", "submittedAt": "2026-11-02T09:30:00Z"},
            {"author": {"login": "dev-b"}, "state": "CHANGES_REQUESTED", "submittedAt": "2026-11-02T12:00:00Z"},
            {"author": {"login": "dev-b"}, "state": "APPROVED", "submittedAt": "2026-11-02T15:00:00Z"},
            {"author": {"login": "dev-c"}, "state": "COMMENTED", "submittedAt": "2026-11-02T16:00:00Z"},
        ],
    },
    {"number": 2, "createdAt": "2026-11-02T09:00:00Z", "mergedAt": None, "isDraft": False, "author": {"login": "dependabot[bot]"}, "labels": [], "reviews": []},
    {"number": 3, "createdAt": "2026-11-02T09:00:00Z", "mergedAt": None, "isDraft": True, "author": {"login": "dev-a"}, "labels": [], "reviews": []},
]


class GitHub(unittest.TestCase):
    def test_first_review_excludes_author_and_bots_and_drafts(self):
        rows, skipped = from_gh(PRS, "acme-app", prefix="squad:")
        self.assertEqual(skipped, {"bot": 1, "draft": 1})
        self.assertEqual(rows, [["acme-app#1", "Quotes", "2026-11-02T09:00:00Z", "2026-11-02T12:00:00Z", "2026-11-03T09:00:00Z", 1, "dev-a"]])

    def test_cli_output_loads_into_a_read(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            (tmp / "prs.json").write_text(json.dumps(PRS), encoding="utf-8")
            r = subprocess.run(
                [sys.executable, str(SCRIPTS / "from_github.py"), "--input", str(tmp / "prs.json"), "--out", str(tmp / "data"), "--squad", "Quotes"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            doc = build(tmp / "data", date.fromisoformat(AS_OF), 90, None)
            self.assertEqual(doc["figures"]["review_wait_median"]["value"], 3)
            self.assertEqual(doc["figures"]["pr_authors"]["value"], 1)

    def test_bad_json_exits_2(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "prs.json"
            p.write_text("{}", encoding="utf-8")
            r = subprocess.run([sys.executable, str(SCRIPTS / "from_github.py"), "--input", str(p), "--out", t], capture_output=True, text=True, check=False)
            self.assertEqual(r.returncode, 2)


class CsvMapper(unittest.TestCase):
    ROWS = [
        {
            "ID": "A-1",
            "Team": "Quotes",
            "Assignee": "x",
            "Created": "2026-11-01 10:00:00",
            "Started": "2026-11-02T08:00:00Z",
            "Completed": "",
            "Labels": "Frontend, Bug",
        }
    ]
    MAP = {"id": "ID", "type": "Labels", "squad": "Team", "assignee": "Assignee", "created": "Created", "started": "Started", "completed": "Completed"}

    def test_maps_and_picks_type(self):
        header, rows = map_csv(self.ROWS, "items", self.MAP, ["bug", "feature"])
        self.assertEqual(header, ["id", "type", "squad", "assignee", "created", "started", "completed"])
        self.assertEqual(rows[0], ["A-1", "bug", "Quotes", "x", "2026-11-01", "2026-11-02", ""])

    def test_missing_required_mapping(self):
        with self.assertRaisesRegex(ValueError, "needs a mapping"):
            map_csv(self.ROWS, "items", {"id": "ID"})

    def test_unknown_target_column(self):
        with self.assertRaisesRegex(ValueError, "not a column"):
            map_csv(self.ROWS, "items", {**self.MAP, "velocity": "ID"})

    def test_unknown_source_column(self):
        with self.assertRaisesRegex(ValueError, "no column"):
            map_csv(self.ROWS, "items", {**self.MAP, "id": "Key"})


class OptionalColumns(unittest.TestCase):
    def test_items_without_optional_columns_still_read_cycle_time(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            with (tmp / "items.csv").open("w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["id", "type", "squad", "assignee", "created", "started", "completed"])
                for i in range(40):
                    t_ = "bug" if i % 2 else "feature"
                    w.writerow([i, t_, "Quotes", f"p{i % 4}", "2026-10-01", "2026-10-02", "2026-10-04" if t_ == "bug" else "2026-10-12"])
            doc = build(tmp, date.fromisoformat(AS_OF), 90, None)
            self.assertIn("cycle_time_median", doc["figures"])
            for fid in ("reopen_rate", "acceptance_criteria_share", "unplanned_share"):
                self.assertNotIn(fid, doc["figures"])
            dv = next(d for d in doc["dimensions"] if d["id"] == "delivery_velocity")
            self.assertEqual(dv["floor"], 3)
            self.assertEqual(doc["start_here"]["name"], "Delivery Velocity")
            self.assertIn("Start here", render(doc))


if __name__ == "__main__":
    unittest.main()


class GitHubOnlyFastTeam(unittest.TestCase):
    def test_nothing_bounded_still_says_what_to_add(self):
        prs = [
            {
                "number": i,
                "createdAt": "2026-11-02T09:00:00Z",
                "mergedAt": "2026-11-02T13:00:00Z",
                "isDraft": False,
                "author": {"login": "dev-a"},
                "labels": [],
                "reviews": [{"author": {"login": "dev-b"}, "state": "APPROVED", "submittedAt": "2026-11-02T11:00:00Z"}],
            }
            for i in range(30)
        ]
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            rows, _ = from_gh(prs, "app")
            with (tmp / "pull_requests.csv").open("w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["id", "squad", "opened", "first_review", "merged", "approvals", "author"])
                w.writerows([r[:-1] + [f"dev-{i % 4}"] for i, r in enumerate(rows)])
            doc = build(tmp, date.fromisoformat(AS_OF), 90, None)
            self.assertIsNone(doc["start_here"])
            md = render(doc)
            self.assertIn("no dimension is bounded yet", md)
            self.assertIn("squads.csv", md)


class SoloRepository(unittest.TestCase):
    def test_review_rules_hold_back_under_3_authors(self):
        from helpers import fig, figs

        from rules import read_dimension

        f = figs(fig("review_coverage", 0.0, 47), fig("pr_authors", 1, 47, "count"))
        self.assertEqual(read_dimension("quality_experimentation", f)["read"], "not_read")
        f = figs(fig("review_coverage", 0.0, 47), fig("pr_authors", 3, 47, "count"))
        self.assertEqual(read_dimension("quality_experimentation", f)["ceiling"], 3)
