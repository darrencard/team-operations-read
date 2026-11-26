"""Rules: each bound fires at its threshold, holds back below its sample minimum, and never overclaims."""

from __future__ import annotations

import unittest

from helpers import fig, figs

from rules import describe, read_all, read_dimension


def dv(ratio: float, n: int = 100) -> dict:
    return figs(fig("cycle_time_median", 5, n, "days"), fig("lane_ratio", ratio, n, "ratio"))


class DeliveryVelocity(unittest.TestCase):
    def test_separate_lane_sets_floor_3_only(self):
        d = read_dimension("delivery_velocity", dv(0.5))
        self.assertEqual((d["read"], d["floor"], d["ceiling"]), ("range", 3, 5))
        self.assertEqual(describe(d), "Stage 3 or above")
        self.assertIsNone(d["stage"])

    def test_one_speed_sets_ceiling_2(self):
        d = read_dimension("delivery_velocity", dv(0.51))
        self.assertEqual((d["floor"], d["ceiling"]), (1, 2))
        self.assertEqual(describe(d), "Stage 2 or below")

    def test_small_sample_is_not_read(self):
        d = read_dimension("delivery_velocity", dv(0.2, n=29))
        self.assertEqual(d["read"], "not_read")
        self.assertIn("Export", d["next_step"])


class RoadmapDiscipline(unittest.TestCase):
    def base(self, unplanned=0.2, accuracy=0.8, epics=0.6, cycles=3):
        return figs(
            fig("cycles_in_window", cycles, cycles, "count"),
            fig("unplanned_share", unplanned),
            fig("planning_accuracy", accuracy),
            fig("epic_success_criteria", epics, 10),
        )

    def test_unplanned_over_40_percent_caps_at_2(self):
        self.assertEqual(read_dimension("roadmap_discipline", self.base(unplanned=0.41))["ceiling"], 2)
        self.assertEqual(read_dimension("roadmap_discipline", self.base(unplanned=0.40))["read"], "not_read")

    def test_low_accuracy_caps_at_2(self):
        self.assertEqual(read_dimension("roadmap_discipline", self.base(accuracy=0.59))["ceiling"], 2)

    def test_too_few_cycles_skips_planning_rules(self):
        d = read_dimension("roadmap_discipline", self.base(unplanned=0.9, accuracy=0.1, cycles=2))
        self.assertEqual(d["read"], "not_read")

    def test_success_criteria_floor(self):
        d = read_dimension("roadmap_discipline", self.base(epics=0.8))
        self.assertEqual((d["floor"], d["ceiling"]), (3, 5))

    def test_floor_and_ceiling_conflict(self):
        d = read_dimension("roadmap_discipline", self.base(unplanned=0.6, epics=0.9))
        self.assertEqual(d["read"], "conflict")
        self.assertIsNone(d["stage"])
        self.assertEqual(describe(d), "Conflicting evidence, no stage")
        self.assertIn("both ways", d["next_step"])


class TeamOrchestration(unittest.TestCase):
    def test_exact_stage_when_floor_meets_ceiling(self):
        f = figs(fig("cross_functional_squads", 0.8, 12), fig("review_wait_median", 30, 100, "hours"), fig("review_wait_p85", 60, 100, "hours"))
        d = read_dimension("team_orchestration", f)
        self.assertEqual((d["read"], d["stage"], d["stage_name"]), ("stage", 3, "Scaling"))
        self.assertIn("same-day", d["next_step"])  # the binding ceiling sets the next step

    def test_wip_ceiling(self):
        d = read_dimension("team_orchestration", figs(fig("wip_per_person", 3.5, 20, "per person")))
        self.assertEqual(d["ceiling"], 3)

    def test_too_few_squads(self):
        d = read_dimension("team_orchestration", figs(fig("cross_functional_squads", 1.0, 3)))
        self.assertEqual(d["read"], "not_read")


class OtherDimensions(unittest.TestCase):
    def test_spec_quality_conflict_when_criteria_present_but_reopens_high(self):
        d = read_dimension("spec_context_quality", figs(fig("reopen_rate", 0.2), fig("acceptance_criteria_share", 0.9)))
        self.assertEqual(d["read"], "conflict")

    def test_spec_quality_floor(self):
        d = read_dimension("spec_context_quality", figs(fig("reopen_rate", 0.05), fig("acceptance_criteria_share", 0.9)))
        self.assertEqual((d["floor"], d["ceiling"]), (3, 5))

    def test_retro_bands(self):
        self.assertEqual(read_dimension("process_iteration", figs(fig("retro_closed_30d", 0.2, 10)))["ceiling"], 2)
        self.assertEqual(read_dimension("process_iteration", figs(fig("retro_closed_30d", 0.7, 10)))["floor"], 2)
        self.assertEqual(read_dimension("process_iteration", figs(fig("retro_closed_30d", 0.5, 10)))["read"], "not_read")
        self.assertEqual(read_dimension("process_iteration", figs(fig("retro_closed_30d", 0.0, 4)))["read"], "not_read")

    def test_experiments(self):
        self.assertEqual(read_dimension("quality_experimentation", figs(fig("experiments_launched", 0, 0, "count")))["ceiling"], 2)
        self.assertEqual(read_dimension("quality_experimentation", figs(fig("experiments_launched", 3, 3, "count")))["floor"], 3)
        self.assertEqual(read_dimension("quality_experimentation", figs(fig("experiments_launched", 2, 2, "count")))["read"], "not_read")

    def test_dimension_with_no_rule_is_never_scored(self):
        d = read_dimension("pricing_packaging", figs(fig("survey.pricing_packaging", 5.0, 50, "of 5")))
        self.assertEqual(d["read"], "not_read")
        self.assertIsNone(d["floor"])
        self.assertIn("full Team Operations read", d["next_step"])


class Survey(unittest.TestCase):
    def test_survey_never_moves_a_bound(self):
        low = read_dimension("delivery_velocity", {**dv(0.2), **figs(fig("survey.delivery_velocity", 1.0, 40, "of 5"))})
        high = read_dimension("delivery_velocity", {**dv(0.2), **figs(fig("survey.delivery_velocity", 5.0, 40, "of 5"))})
        self.assertEqual((low["floor"], low["ceiling"]), (high["floor"], high["ceiling"]))

    def test_small_survey_is_hidden(self):
        d = read_dimension("delivery_velocity", {**dv(0.2), **figs(fig("survey.delivery_velocity", 4.0, 4, "of 5"))})
        self.assertFalse(d["survey"]["shown"])

    def test_disagreement_is_flagged(self):
        d = read_dimension("delivery_velocity", {**dv(0.2), **figs(fig("survey.delivery_velocity", 1.5, 40, "of 5"))})
        self.assertIsNotNone(d["survey_disagrees"])
        d = read_dimension("delivery_velocity", {**dv(0.2), **figs(fig("survey.delivery_velocity", 3.0, 40, "of 5"))})
        self.assertIsNone(d["survey_disagrees"])


class Overall(unittest.TestCase):
    def test_withheld_unless_all_27_have_one_stage(self):
        r = read_all(figs(fig("cross_functional_squads", 0.8, 12), fig("review_wait_median", 30, 100, "hours")))
        self.assertFalse(r["overall"]["claimed"])
        self.assertEqual(r["overall"]["single_stage_reads"], 1)
        self.assertNotIn("stage", r["overall"])

    def test_claimed_when_every_dimension_is_pinned(self):
        import rules

        pinned = {
            d: (lambda f, _d=d: [rules._finding(_d, [], ("floor", 3), "x", "y"), rules._finding(_d, [], ("ceiling", 3), "x", "y")]) for d in rules.DIMENSION_IDS
        }
        saved = dict(rules.RULES)
        try:
            rules.RULES.clear()
            rules.RULES.update(pinned)
            r = read_all({})
        finally:
            rules.RULES.clear()
            rules.RULES.update(saved)
        self.assertTrue(r["overall"]["claimed"])
        self.assertEqual((r["overall"]["total"], r["overall"]["stage"], r["overall"]["stage_name"]), (81, 3, "Scaling"))

    def test_stage_bands(self):
        from framework import overall_stage

        self.assertEqual([overall_stage(x) for x in (27, 48, 49, 69, 70, 90, 91, 113, 114, 135)], [1, 1, 2, 2, 3, 3, 4, 4, 5, 5])
        with self.assertRaises(ValueError):
            overall_stage(136)


if __name__ == "__main__":
    unittest.main()
