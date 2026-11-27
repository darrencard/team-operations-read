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

from helpers import AS_OF, SCRIPTS

from from_csv import convert as map_csv
from from_github import convert as from_gh
from from_linear import convert as from_linear
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


class GitHubRest(unittest.TestCase):
    def test_rest_shape_and_paginated_file(self):
        rest = [
            {
                "number": 7,
                "created_at": "2026-11-02T09:00:00Z",
                "merged_at": "2026-11-03T09:00:00Z",
                "draft": False,
                "user": {"login": "dev-a", "type": "User"},
                "labels": [],
                "reviews": [{"user": {"login": "dev-b"}, "state": "APPROVED", "submitted_at": "2026-11-02T10:00:00Z"}],
            },
            {"number": 8, "created_at": "2026-11-02T09:00:00Z", "user": {"login": "renovate", "type": "Bot"}},
        ]
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            # gh api --paginate writes one array per page, back to back.
            (tmp / "prs.json").write_text(json.dumps(rest[:1]) + json.dumps(rest[1:]), encoding="utf-8")
            r = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "from_github.py"),
                    "--input",
                    str(tmp / "prs.json"),
                    "--out",
                    str(tmp / "d"),
                    "--repo",
                    "acme/app",
                    "--retrieved-at",
                    "2026-11-20",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            rows = list(csv.reader((tmp / "d" / "pull_requests.csv").open(encoding="utf-8")))
            self.assertEqual(rows[1], ["prs#7", "", "2026-11-02T09:00:00Z", "2026-11-02T10:00:00Z", "2026-11-03T09:00:00Z", "1", "dev-a"])
            self.assertEqual(len(rows), 2)
            manifest = json.loads((tmp / "d" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["systems"]["pull_requests.csv"], "GitHub (acme/app), retrieved 2026-11-20")


LINEAR_CONNECTOR = {
    "issues": [
        {
            "identifier": "QUO-1",
            "team": "Quoting",
            "assignee": "Sam",
            "labels": ["type:bug"],
            "createdAt": "2026-10-01T09:00:00Z",
            "startedAt": "2026-10-02T09:00:00Z",
            "completedAt": "2026-10-04T09:00:00Z",
            "cycle": {"number": 12, "startsAt": "2026-09-28", "endsAt": "2026-10-11"},
            "description": "## Acceptance criteria\n- totals match",
        },
        {"identifier": "QUO-2", "team": "Quoting", "labels": [], "createdAt": "2026-10-01", "completedAt": "2026-10-03"},
    ],
    "hasNextPage": False,
}
LINEAR_GRAPHQL = {
    "data": {
        "issues": {
            "nodes": [
                {
                    "identifier": "INV-9",
                    "team": {"name": "Invoices"},
                    "assignee": {"name": "Ali"},
                    "labels": {"nodes": [{"name": "Feature"}]},
                    "createdAt": "2026-10-05T00:00:00Z",
                    "startedAt": "2026-10-06T00:00:00Z",
                    "completedAt": None,
                    "cycle": {"name": "Sprint 4", "startsAt": "2026-10-05T00:00:00Z", "endsAt": "2026-10-18T00:00:00Z"},
                }
            ]
        }
    }
}


class Linear(unittest.TestCase):
    def test_connector_shape(self):
        lr_issues = LINEAR_CONNECTOR["issues"]
        header, rows, cycles, counts = from_linear(lr_issues, type_prefix="type:", acceptance_heading="Acceptance criteria")
        self.assertEqual(header[-1], "acceptance_criteria")
        self.assertEqual(rows[0], ["QUO-1", "bug", "Quoting", "Sam", "2026-10-01", "2026-10-02", "2026-10-04", "Cycle 12", "true"])
        # No startedAt: kept and counted, with no completed date, so it adds no cycle time.
        self.assertEqual(rows[1][5:7], ["", ""])
        self.assertEqual(counts["no_started"], 1)
        self.assertEqual(cycles, [["Cycle 12", "2026-09-28", "2026-10-11"]])

    def test_graphql_shape_through_the_cli_loads_into_a_read(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            (tmp / "a.json").write_text(json.dumps(LINEAR_CONNECTOR), encoding="utf-8")
            (tmp / "b.json").write_text(json.dumps(LINEAR_GRAPHQL), encoding="utf-8")
            r = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "from_linear.py"),
                    "--issues",
                    str(tmp / "a.json"),
                    str(tmp / "b.json"),
                    "--out",
                    str(tmp / "d"),
                    "--type-values",
                    "bug,feature",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("planned and reopened", r.stdout)
            rows = list(csv.DictReader((tmp / "d" / "items.csv").open(encoding="utf-8")))
            self.assertEqual({x["id"]: x["type"] for x in rows}, {"QUO-1": "untyped", "QUO-2": "untyped", "INV-9": "feature"})
            self.assertEqual(next(x for x in rows if x["id"] == "INV-9")["squad"], "Invoices")
            doc = build(tmp / "d", date.fromisoformat(AS_OF), 90, None)
            self.assertEqual(doc["figures"]["cycle_time_median"]["n"], 1)
            self.assertIn("Linear", doc["systems"]["items.csv"])

    def test_unreadable_file_exits_2(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "x.json"
            p.write_text("{}", encoding="utf-8")
            r = subprocess.run([sys.executable, str(SCRIPTS / "from_linear.py"), "--issues", str(p), "--out", t], capture_output=True, text=True, check=False)
            self.assertEqual(r.returncode, 2)


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
