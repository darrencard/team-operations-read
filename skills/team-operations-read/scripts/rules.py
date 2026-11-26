"""Turn figures into bounded reads of Team Operations dimensions.

A rule reads one or more figures and, when its sample is large enough, sets a floor (the evidence
rules out lower stages) or a ceiling (the evidence rules out higher stages) on one dimension. Each
bound cites the rubric condition it tests. A dimension gets a single stage only when its floor and
ceiling meet. Survey answers are self-reported: they are shown beside the read and never move a bound.

Thresholds are Dacard v0.1 heuristics, listed in references/rules.md. They are assumptions to test,
not benchmarks.
"""

from __future__ import annotations

from framework import BY_ID, DIMENSION_IDS, STAGE_NAMES, overall_stage

MIN_COMPLETED_ITEMS = 30
MIN_CYCLES = 3
MIN_PRS = 20
MIN_SQUADS = 4
MIN_EPICS = 5
MIN_RETRO_ACTIONS = 5
MIN_SURVEY_RESPONSES = 5

# What a dimension needs before it can be read at all. Dimensions not listed here are not read from
# tracker, source-control or survey data; they need a full Dacard read of the artefacts named.
DATA_NEEDED = {
    "delivery_velocity": "items.csv with type, started and completed for 30 or more items",
    "roadmap_discipline": "items.csv with cycle and planned, cycles.csv covering 3 or more cycles, and epics.csv",
    "spec_context_quality": "items.csv with reopened and acceptance_criteria for 30 or more items",
    "team_orchestration": "squads.csv with roles, pull_requests.csv with first_review, and items.csv with assignee",
    "process_iteration": "retro_actions.csv with raised and closed dates for 5 or more actions",
    "quality_experimentation": "experiments.csv and pull_requests.csv with approvals",
}
NOT_IN_SCOPE_STEP = "Not readable from tracker, source-control or survey exports. Book a full Team Operations read to review the {what} directly."
ARTEFACTS = {
    "Strategy": "strategy documents, decision records and roadmap history",
    "Design": "research repository, prototypes and design system",
    "Development": "architecture records and build-or-buy decisions",
    "Intelligence": "analytics setup and customer feedback pipeline",
    "Operations": "operating documents, cost reporting and incident records",
    "Go-to-Market": "positioning, launch plans and pricing records",
}


def _f(figs: dict, fid: str) -> dict | None:
    return figs.get(fid)


def _finding(rule: str, figures: list[str], bound: tuple[str, int] | None, says: str, step: str) -> dict:
    return {"rule": rule, "figures": figures, "bound": list(bound) if bound else None, "says": says, "next_step": step}


def _skip(rule: str, figures: list[str], why: str) -> dict:
    return {"rule": rule, "figures": figures, "bound": None, "says": why, "next_step": None, "skipped": True}


def _delivery_velocity(figs: dict) -> list[dict]:
    out = []
    lr, ct = _f(figs, "lane_ratio"), _f(figs, "cycle_time_median")
    if ct is None or ct["n"] < MIN_COMPLETED_ITEMS:
        return [_skip("delivery_velocity.lanes", ["cycle_time_median"], f"Fewer than {MIN_COMPLETED_ITEMS} completed items in the window.")]
    if lr is None:
        return [
            _skip("delivery_velocity.lanes", ["cycle_time_median"], "Fewer than 2 work types with 10 or more completed items, so lanes cannot be compared.")
        ]
    if lr["value"] <= 0.5:
        out.append(
            _finding(
                "delivery_velocity.lanes",
                ["lane_ratio", "cycle_time_median"],
                ("floor", 3),
                f"{lr['label']} is {lr['display']}: one work type moves through in half the time or less, a proxy for a separate delivery lane (rubric Stage 3).",
                "Show Stage 4: add automated evaluation to the fast lane so its changes ship on a passing check, not a sprint review.",
            )
        )
    else:
        out.append(
            _finding(
                "delivery_velocity.lanes",
                ["lane_ratio", "cycle_time_median"],
                ("ceiling", 2),
                f"{lr['label']} is {lr['display']}: work types move at similar speeds, so all work appears to share one cycle (rubric Stage 2).",
                "Give the most common small work type its own lane with a shorter path to production, then compare its cycle time next quarter.",
            )
        )
    return out


def _roadmap_discipline(figs: dict) -> list[dict]:
    out = []
    cyc, un, pa, ep = (_f(figs, k) for k in ("cycles_in_window", "unplanned_share", "planning_accuracy", "epic_success_criteria"))
    if cyc is None or cyc["value"] < MIN_CYCLES or un is None:
        out.append(_skip("roadmap_discipline.unplanned", ["unplanned_share"], f"Fewer than {MIN_CYCLES} cycles end in the window."))
    else:
        if un["value"] > 0.40:
            out.append(
                _finding(
                    "roadmap_discipline.unplanned",
                    ["unplanned_share"],
                    ("ceiling", 2),
                    f"{un['label']}: {un['display']}. More than 40% of cycle work arrives after planning, which reads as reactive prioritisation (rubric Stage 2).",
                    "Tag each unplanned item with its source (sales, incident, executive, customer) for 2 cycles, then cap the largest source.",
                )
            )
        if pa is not None and pa["value"] < 0.60:
            out.append(
                _finding(
                    "roadmap_discipline.accuracy",
                    ["planning_accuracy"],
                    ("ceiling", 2),
                    f"{pa['label']}: {pa['display']}. Under 60% of planned work finishes in its cycle, so the plan is not yet a reliable commitment (rubric Stage 2).",
                    "Commit to less: plan each cycle to the median completed load of the last 3 cycles and track the hit rate.",
                )
            )
    if ep is None or ep["n"] < MIN_EPICS:
        out.append(_skip("roadmap_discipline.success_criteria", ["epic_success_criteria"], f"Fewer than {MIN_EPICS} epics exported."))
    elif ep["value"] >= 0.80:
        out.append(
            _finding(
                "roadmap_discipline.success_criteria",
                ["epic_success_criteria"],
                ("floor", 3),
                f"{ep['label']}: {ep['display']}. Initiatives carry clear success criteria (rubric Stage 3).",
                "Show Stage 4: link each epic's success criteria to the signal that triggered it, so prioritisation traces to data.",
            )
        )
    elif ep["value"] < 0.50:
        out.append(
            _finding(
                "roadmap_discipline.success_criteria",
                ["epic_success_criteria"],
                ("ceiling", 2),
                f"{ep['label']}: {ep['display']}. Most initiatives have no stated success criteria (rubric Stage 3 needs them).",
                "Add a success criterion to every open epic before the next planning session; reject new epics without one.",
            )
        )
    return out


def _spec_context_quality(figs: dict) -> list[dict]:
    out = []
    rr, ac = _f(figs, "reopen_rate"), _f(figs, "acceptance_criteria_share")
    if rr is None or rr["n"] < MIN_COMPLETED_ITEMS:
        out.append(_skip("spec_context_quality.reopens", ["reopen_rate"], f"Fewer than {MIN_COMPLETED_ITEMS} completed items in the window."))
    elif rr["value"] > 0.15:
        out.append(
            _finding(
                "spec_context_quality.reopens",
                ["reopen_rate"],
                ("ceiling", 2),
                f"{rr['label']}: {rr['display']}. More than 15% of finished work comes back, a sign builders are guessing at edge cases (rubric Stage 2).",
                "Sample 10 reopened items, name the missing context in each, and add the most common gap to the spec template.",
            )
        )
    if ac is None or ac["n"] < MIN_COMPLETED_ITEMS:
        out.append(_skip("spec_context_quality.acceptance", ["acceptance_criteria_share"], f"Fewer than {MIN_COMPLETED_ITEMS} items started in the window."))
    elif ac["value"] >= 0.80 and (rr is None or rr["value"] <= 0.10):
        out.append(
            _finding(
                "spec_context_quality.acceptance",
                ["acceptance_criteria_share", "reopen_rate"],
                ("floor", 3),
                f"{ac['label']}: {ac['display']}, with few reopens. Specs carry behaviour detail (rubric Stage 3).",
                "Show Stage 4: make specs machine-readable so the same context feeds people and coding agents.",
            )
        )
    elif ac["value"] >= 0.80:
        out.append(
            _finding(
                "spec_context_quality.acceptance",
                ["acceptance_criteria_share", "reopen_rate"],
                ("floor", 3),
                f"{ac['label']}: {ac['display']}. Specs carry acceptance criteria (rubric Stage 3), but reopens are above 10%.",
                "Check whether reopened items had acceptance criteria; if they did, the criteria miss edge cases.",
            )
        )
    elif ac["value"] < 0.50:
        out.append(
            _finding(
                "spec_context_quality.acceptance",
                ["acceptance_criteria_share"],
                ("ceiling", 2),
                f"{ac['label']}: {ac['display']}. Most work starts without acceptance criteria.",
                "Require acceptance criteria before an item can move to in progress.",
            )
        )
    return out


def _team_orchestration(figs: dict) -> list[dict]:
    out = []
    cf, rw, wip = _f(figs, "cross_functional_squads"), _f(figs, "review_wait_median"), _f(figs, "wip_per_person")
    if cf is None or cf["n"] < MIN_SQUADS:
        out.append(_skip("team_orchestration.squads", ["cross_functional_squads"], f"Fewer than {MIN_SQUADS} squads in squads.csv."))
    elif cf["value"] >= 0.75:
        out.append(
            _finding(
                "team_orchestration.squads",
                ["cross_functional_squads"],
                ("floor", 3),
                f"{cf['label']}: {cf['display']}. Cross-functional squads are the norm (rubric Stage 3).",
                "Show Stage 4: move operational expertise into squads so no separate team gates their work.",
            )
        )
    elif cf["value"] < 0.25:
        out.append(
            _finding(
                "team_orchestration.squads",
                ["cross_functional_squads"],
                ("ceiling", 2),
                f"{cf['label']}: {cf['display']}. Most squads are single-function, so work crosses silos (rubric Stage 2).",
                "Pilot one squad with product, design and engineering on a single goal for a quarter.",
            )
        )
    if rw is None or rw["n"] < MIN_PRS:
        out.append(_skip("team_orchestration.review_wait", ["review_wait_median"], f"Fewer than {MIN_PRS} reviewed pull requests in the window."))
    elif rw["value"] > 24:
        out.append(
            _finding(
                "team_orchestration.review_wait",
                ["review_wait_median", "review_wait_p85"],
                ("ceiling", 3),
                f"{rw['label']}: {rw['display']}. Work waits more than a day for a second pair of eyes, so collaboration is not yet the default (rubric Stage 4).",
                "Set a same-day first-review norm with a named reviewer rota per squad, and track the median weekly.",
            )
        )
    if wip is not None and wip["value"] > 3:
        out.append(
            _finding(
                "team_orchestration.wip",
                ["wip_per_person"],
                ("ceiling", 3),
                f"{wip['label']}: {wip['display']}. Each person carries more than 3 items at once, a sign of waiting on handoffs (rubric Stage 4).",
                "Set a WIP limit of 2 per person on the board and swarm on blocked items before starting new ones.",
            )
        )
    return out


def _process_iteration(figs: dict) -> list[dict]:
    ra = _f(figs, "retro_closed_30d")
    if ra is None or ra["n"] < MIN_RETRO_ACTIONS:
        return [_skip("process_iteration.retro_actions", ["retro_closed_30d"], f"Fewer than {MIN_RETRO_ACTIONS} retro actions raised at least 30 days ago.")]
    if ra["value"] < 0.25:
        return [
            _finding(
                "process_iteration.retro_actions",
                ["retro_closed_30d"],
                ("ceiling", 2),
                f"{ra['label']}: {ra['display']}. Retros surface friction but few fixes land (rubric Stage 2).",
                "Cut each retro to one action with a named owner and a 2-week due date, and open the next retro with its result.",
            )
        ]
    if ra["value"] >= 0.70:
        return [
            _finding(
                "process_iteration.retro_actions",
                ["retro_closed_30d"],
                ("floor", 2),
                f"{ra['label']}: {ra['display']}. Retro actions get done, which rules out Stage 1; closing a ticket does not show the change stuck.",
                "Show Stage 3 or above: record, for each closed action, the measure it was meant to move and whether it moved.",
            )
        ]
    return [_skip("process_iteration.retro_actions", ["retro_closed_30d"], "Retro closure sits between 25% and 70%, which does not bound a stage.")]


def _quality_experimentation(figs: dict) -> list[dict]:
    out = []
    ex, rc = _f(figs, "experiments_launched"), _f(figs, "review_coverage")
    if ex is not None:
        if ex["value"] >= 3:
            out.append(
                _finding(
                    "quality_experimentation.experiments",
                    ["experiments_launched"],
                    ("floor", 3),
                    f"{ex['label']}: {ex['display']} in the window. Experimentation infrastructure is in use (rubric Stage 3).",
                    "Show Stage 4: add a pre-registered success metric and a stop rule to every experiment.",
                )
            )
        elif ex["value"] == 0:
            out.append(
                _finding(
                    "quality_experimentation.experiments",
                    ["experiments_launched"],
                    ("ceiling", 2),
                    "No experiments launched in the window. Testing is talked about, not practised (rubric Stage 2).",
                    "Run one A/B test on a live decision this quarter, with the metric and stop rule written first.",
                )
            )
    if rc is None or rc["n"] < MIN_PRS:
        out.append(_skip("quality_experimentation.review_gate", ["review_coverage"], f"Fewer than {MIN_PRS} merged pull requests in the window."))
    elif rc["value"] < 0.80:
        out.append(
            _finding(
                "quality_experimentation.review_gate",
                ["review_coverage"],
                ("ceiling", 3),
                f"{rc['label']}: {rc['display']}. Changes reach production without an approval, so quality gates do not block bad releases (rubric Stage 4).",
                "Require one approval on the default branch and report the bypass count each week.",
            )
        )
    return out


RULES = {
    "delivery_velocity": _delivery_velocity,
    "roadmap_discipline": _roadmap_discipline,
    "spec_context_quality": _spec_context_quality,
    "team_orchestration": _team_orchestration,
    "process_iteration": _process_iteration,
    "quality_experimentation": _quality_experimentation,
}


def _survey(figs: dict, dim: str) -> dict | None:
    s = figs.get(f"survey.{dim}")
    if s is None:
        return None
    if s["n"] < MIN_SURVEY_RESPONSES:
        return {"figure": s["id"], "shown": False, "says": f"Fewer than {MIN_SURVEY_RESPONSES} survey responses, so the team view is not shown."}
    return {"figure": s["id"], "shown": True, "says": f"Team view (self-reported): {s['display']} from {s['n']} responses."}


def read_dimension(dim: str, figs: dict) -> dict:
    meta = BY_ID[dim]
    findings = RULES[dim](figs) if dim in RULES else []
    bounds = [f for f in findings if f["bound"]]
    floor = max([f["bound"][1] for f in bounds if f["bound"][0] == "floor"], default=1)
    ceiling = min([f["bound"][1] for f in bounds if f["bound"][0] == "ceiling"], default=5)
    if not bounds:
        kind = "not_read"
    elif floor > ceiling:
        kind = "conflict"
    elif floor == ceiling:
        kind = "stage"
    else:
        kind = "range"

    # One next step. A conflict comes first, then the binding ceiling (what holds the dimension back),
    # then the strongest floor (what would show the next stage), then the data needed.
    ceilings = sorted([f for f in bounds if f["bound"][0] == "ceiling"], key=lambda f: f["bound"][1])
    floors = sorted([f for f in bounds if f["bound"][0] == "floor"], key=lambda f: -f["bound"][1])
    if kind == "conflict":
        step = "The evidence points both ways. Pull 10 recent items behind the conflicting figures and check which one reflects how work really runs."
    elif ceilings:
        step = ceilings[0]["next_step"]
    elif floors:
        step = floors[0]["next_step"]
    elif dim in DATA_NEEDED:
        step = f"Export {DATA_NEEDED[dim]} to read this dimension."
    else:
        step = NOT_IN_SCOPE_STEP.format(what=ARTEFACTS[meta["function"]])

    survey = _survey(figs, dim)
    disagree = None
    if survey and survey["shown"] and kind in ("stage", "range"):
        mean = figs[survey["figure"]]["value"]
        if mean > ceiling + 1 or mean < floor - 1:
            disagree = "The team's own view sits more than a stage away from what the exports show. Ask why before acting on either."

    return {
        **meta,
        "read": kind,
        "floor": floor if bounds else None,
        "ceiling": ceiling if bounds else None,
        "stage": floor if kind == "stage" else None,
        "stage_name": STAGE_NAMES[floor] if kind == "stage" else None,
        "findings": findings,
        "survey": survey,
        "survey_disagrees": disagree,
        "next_step": step,
    }


def read_all(figs: dict) -> dict:
    dims = [read_dimension(d, figs) for d in DIMENSION_IDS]
    exact = [d for d in dims if d["read"] == "stage"]
    overall = {"claimed": False, "single_stage_reads": len(exact), "of": 27}
    if len(exact) == 27:
        total = sum(d["stage"] for d in exact)
        st = overall_stage(total)
        overall.update(claimed=True, total=total, stage=st, stage_name=STAGE_NAMES[st])
    else:
        overall["why"] = (
            f"An overall Team Operations stage needs a single-stage read on all 27 dimensions. This read has {len(exact)}, so no overall stage or level is claimed."
        )
    return {"dimensions": dims, "overall": overall}


def describe(d: dict) -> str:
    """The one phrase a read may use for a dimension's stage."""
    if d["read"] == "stage":
        return f"Stage {d['stage']} ({d['stage_name']})"
    if d["read"] == "range":
        if d["ceiling"] == 5:
            return f"Stage {d['floor']} or above"
        if d["floor"] == 1:
            return f"Stage {d['ceiling']} or below"
        return f"Stage {d['floor']} to {d['ceiling']}"
    if d["read"] == "conflict":
        return "Conflicting evidence, no stage"
    return "Not read"
