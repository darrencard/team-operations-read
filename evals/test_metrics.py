"""Figures: each computed on hand-checked rows."""

from __future__ import annotations

import unittest
from datetime import UTC, date, datetime, timedelta

import helpers  # noqa: F401

from metrics import compute, nearest_rank

AS_OF = date(2026, 11, 20)


def item(i, t="feature", started=None, completed=None, assignee="a", cycle="", planned=True, reopened=0, ac=True):
    return {
        "id": str(i),
        "type": t,
        "squad": "S",
        "assignee": assignee,
        "created": started or AS_OF,
        "started": started,
        "completed": completed,
        "cycle": cycle,
        "planned": planned,
        "reopened": reopened,
        "acceptance_criteria": ac,
    }


class Percentiles(unittest.TestCase):
    def test_nearest_rank(self):
        self.assertEqual(nearest_rank([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 85), 9)
        self.assertEqual(nearest_rank([5], 85), 5)
        self.assertEqual(nearest_rank([3, 1, 2], 50), 2)

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            nearest_rank([], 50)


class Items(unittest.TestCase):
    def test_cycle_time_and_lanes(self):
        d0 = date(2026, 11, 1)
        rows = [item(i, "feature", d0, d0 + timedelta(days=10)) for i in range(10)]
        rows += [item(100 + i, "bug", d0, d0 + timedelta(days=2)) for i in range(10)]
        f = compute({"items": rows}, AS_OF, 90)["figures"]
        self.assertEqual(f["cycle_time_median"]["value"], 6)
        self.assertEqual(f["cycle_time_median.bug"]["value"], 2)
        self.assertEqual(f["cycle_time_median.feature"]["value"], 10)
        self.assertAlmostEqual(f["lane_ratio"]["value"], 0.2)
        self.assertEqual(f["lane_ratio"]["display"], "0.20")

    def test_no_lane_ratio_below_minimum_per_type(self):
        d0 = date(2026, 11, 1)
        rows = [item(i, "feature", d0, d0 + timedelta(days=10)) for i in range(10)]
        rows += [item(100 + i, "bug", d0, d0 + timedelta(days=2)) for i in range(9)]
        self.assertNotIn("lane_ratio", compute({"items": rows}, AS_OF, 90)["figures"])

    def test_items_outside_window_are_ignored(self):
        rows = [item(1, started=date(2026, 1, 1), completed=date(2026, 1, 5))]
        f = compute({"items": rows}, AS_OF, 90)["figures"]
        self.assertNotIn("cycle_time_median", f)

    def test_reopen_and_acceptance_shares(self):
        d0 = date(2026, 11, 1)
        rows = [item(i, started=d0, completed=d0, reopened=1 if i < 2 else 0, ac=i < 5) for i in range(10)]
        f = compute({"items": rows}, AS_OF, 90)["figures"]
        self.assertAlmostEqual(f["reopen_rate"]["value"], 0.2)
        self.assertAlmostEqual(f["acceptance_criteria_share"]["value"], 0.5)
        self.assertEqual(f["reopen_rate"]["display"], "20%")

    def test_wip_per_person(self):
        # One person holds 2 items open across the whole 14-day window: WIP is 2.
        start = AS_OF - timedelta(days=13)
        rows = [item(1, started=start - timedelta(days=1)), item(2, started=start - timedelta(days=1))]
        f = compute({"items": rows}, AS_OF, 14)["figures"]
        self.assertAlmostEqual(f["wip_per_person"]["value"], 2.0)

    def test_planning_accuracy_and_unplanned(self):
        cycles = [{"cycle": "C1", "start": date(2026, 11, 1), "end": date(2026, 11, 14)}]
        rows = [
            item(1, started=date(2026, 11, 1), completed=date(2026, 11, 10), cycle="C1", planned=True),
            item(2, started=date(2026, 11, 1), completed=date(2026, 11, 18), cycle="C1", planned=True),
            item(3, started=date(2026, 11, 5), completed=date(2026, 11, 8), cycle="C1", planned=False),
            item(4, started=date(2026, 11, 1), completed=None, cycle="C1", planned=True),
        ]
        f = compute({"items": rows, "cycles": cycles}, AS_OF, 90)["figures"]
        self.assertAlmostEqual(f["planning_accuracy"]["value"], 1 / 3, places=3)
        self.assertAlmostEqual(f["unplanned_share"]["value"], 0.25)
        self.assertEqual(f["cycles_in_window"]["value"], 1)


class PullRequests(unittest.TestCase):
    def test_review_wait_and_coverage(self):
        t0 = datetime(2026, 11, 2, 9, tzinfo=UTC)
        prs = [
            {
                "id": str(i),
                "squad": "S",
                "opened": t0,
                "first_review": t0 + timedelta(hours=h),
                "merged": t0 + timedelta(hours=h + 1),
                "approvals": 1 if i else 0,
            }
            for i, h in enumerate([2, 4, 6, 8])
        ]
        f = compute({"pull_requests": prs}, AS_OF, 90)["figures"]
        self.assertEqual(f["review_wait_median"]["value"], 5)
        self.assertEqual(f["review_wait_p85"]["value"], 8)
        self.assertAlmostEqual(f["review_coverage"]["value"], 0.75)


class Other(unittest.TestCase):
    def test_squads_epics_retro_experiments_survey(self):
        data = {
            "squads": [
                {"squad": "A", "roles": "pm;design;eng"},
                {"squad": "B", "roles": "eng"},
                {"squad": "C", "roles": "PM; Design; Eng; QA"},
                {"squad": "D", "roles": "pm;eng"},
            ],
            "epics": [{"id": "1", "squad": "A", "success_criteria": True}, {"id": "2", "squad": "A", "success_criteria": False}],
            "retro_actions": [
                {"id": "1", "squad": "A", "raised": date(2026, 9, 1), "closed": date(2026, 9, 20)},
                {"id": "2", "squad": "A", "raised": date(2026, 9, 1), "closed": date(2026, 10, 20)},
                {"id": "3", "squad": "A", "raised": date(2026, 9, 1), "closed": None},
                {"id": "4", "squad": "A", "raised": date(2026, 11, 10), "closed": None},  # too recent to judge
            ],
            "experiments": [{"id": "1", "squad": "A", "launched": date(2026, 10, 1)}, {"id": "2", "squad": "A", "launched": date(2025, 1, 1)}],
            "survey": [{"respondent": str(i), "dimension": "knowledge_management", "score": s} for i, s in enumerate([1, 2, 3, 4, 5])],
        }
        f = compute(data, AS_OF, 90)["figures"]
        self.assertAlmostEqual(f["cross_functional_squads"]["value"], 0.5)
        self.assertAlmostEqual(f["epic_success_criteria"]["value"], 0.5)
        self.assertAlmostEqual(f["retro_closed_30d"]["value"], 1 / 3, places=3)
        self.assertEqual(f["retro_closed_30d"]["n"], 3)
        self.assertEqual(f["experiments_launched"]["value"], 1)
        self.assertEqual(f["survey.knowledge_management"]["value"], 3)
        self.assertIn("Knowledge Management", f["survey.knowledge_management"]["label"])

    def test_every_figure_has_source_n_and_method(self):
        from helpers import ACME

        from inputs import load

        data, _ = load(ACME)
        for f in compute(data, AS_OF, 90)["figures"].values():
            for key in ("source", "n", "method", "display", "label"):
                self.assertTrue(f[key] != "" and f[key] is not None, (f["id"], key))


if __name__ == "__main__":
    unittest.main()
