"""Compute every figure a read uses. The model never does this arithmetic.

Each figure is a dict: id, label, value, unit, display, source, window (from, to), as_of, n, method,
the same fields the Landing Loop contract asks of every figure. A figure that cannot be computed (file
absent, or no rows in the window) is left out, never estimated.

Percentiles use the nearest-rank method. Medians use the standard median (mean of the middle two
for an even count). Durations: cycle time in whole calendar days, review latency in calendar hours.
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from datetime import date, timedelta

from framework import BY_ID

ROLES_FOR_CROSS_FUNCTIONAL = {"pm", "design", "eng"}
RETRO_CLOSE_DAYS = 30
MIN_ITEMS_PER_TYPE = 10
MIN_ROWS_PER_SQUAD = 10


def nearest_rank(values: list[float], pct: float) -> float:
    if not values:
        raise ValueError("no values")
    ordered = sorted(values)
    k = max(1, math.ceil(pct / 100 * len(ordered)))
    return ordered[k - 1]


def _fmt(value: float, unit: str) -> str:
    if unit == "share":
        return f"{round(value * 100)}%"
    if unit == "days":
        return f"{value:.1f} days"
    if unit == "hours":
        return f"{round(value)} hours"
    if unit == "ratio":
        return f"{value:.2f}"
    if unit == "per person":
        return f"{value:.1f} per person"
    if unit == "of 5":
        return f"{value:.1f} of 5"
    return f"{round(value)}"


class Ledger:
    def __init__(self, start: date, end: date) -> None:
        self.figures: dict[str, dict] = {}
        self.window = {"from": start.isoformat(), "to": end.isoformat()}
        self.as_of = end.isoformat()

    def add(self, fid: str, label: str, value: float, unit: str, source: str, n: int, method: str) -> None:
        self.figures[fid] = {
            "id": fid,
            "label": label,
            "value": round(value, 4),
            "unit": unit,
            "display": _fmt(value, unit),
            "source": source,
            "window": dict(self.window),
            "as_of": self.as_of,
            "n": n,
            "method": method,
        }


def _in(d: date | None, start: date, end: date) -> bool:
    return d is not None and start <= d <= end


def _by_squad(led: Ledger, key: str, label: str, rows: list[dict], value, unit: str, source: str) -> None:
    """Median per squad, for squads with enough rows. Context for a read, never a bound."""
    groups = defaultdict(list)
    for r in rows:
        if r["squad"]:
            groups[r["squad"]].append(value(r))
    for squad, vals in sorted(groups.items()):
        if len(vals) >= MIN_ROWS_PER_SQUAD:
            led.add(f"{key}.squad.{squad}", f"{label}, {squad}", statistics.median(vals), unit, source, len(vals), f"median for squad {squad}")


def _items(led: Ledger, items: list[dict], cycles: list[dict] | None, start: date, end: date) -> None:
    done = [r for r in items if _in(r["completed"], start, end) and r["started"]]
    if done:
        days = [(r["completed"] - r["started"]).days for r in done]
        led.add(
            "cycle_time_median",
            "Cycle time, median",
            statistics.median(days),
            "days",
            "items.csv",
            len(done),
            "completed minus started, items completed in the window",
        )
        led.add(
            "cycle_time_p85",
            "Cycle time, 85th percentile",
            nearest_rank(days, 85),
            "days",
            "items.csv",
            len(done),
            "nearest rank, items completed in the window",
        )
        by_type = defaultdict(list)
        for r in done:
            by_type[r["type"].lower() or "untyped"].append((r["completed"] - r["started"]).days)
        for t, vals in sorted(by_type.items()):
            led.add(
                f"cycle_time_median.{t}",
                f"Cycle time, median, {t}",
                statistics.median(vals),
                "days",
                "items.csv",
                len(vals),
                f"completed minus started, {t} items",
            )
        lanes = {t: statistics.median(v) for t, v in by_type.items() if len(v) >= MIN_ITEMS_PER_TYPE}
        if len(lanes) >= 2 and max(lanes.values()) > 0:
            fast, slow = min(lanes, key=lanes.get), max(lanes, key=lanes.get)
            led.add(
                "lane_ratio",
                f"Median cycle time, {fast} over {slow}",
                lanes[fast] / lanes[slow],
                "ratio",
                "items.csv",
                len(by_type[fast]) + len(by_type[slow]),
                f"fastest over slowest work-type median, types with {MIN_ITEMS_PER_TYPE} or more completed items",
            )

        _by_squad(led, "cycle_time", "Cycle time, median", done, lambda r: (r["completed"] - r["started"]).days, "days", "items.csv")

    done_r = [r for r in done if r["reopened"] is not None]
    if done_r:
        reopened = sum(1 for r in done_r if r["reopened"] > 0)
        led.add(
            "reopen_rate",
            "Share of completed items reopened",
            reopened / len(done_r),
            "share",
            "items.csv",
            len(done_r),
            "items with reopened above 0, of items completed in the window",
        )

    started = [r for r in items if _in(r["started"], start, end) and r["acceptance_criteria"] is not None]
    if started:
        ac = sum(1 for r in started if r["acceptance_criteria"])
        led.add(
            "acceptance_criteria_share",
            "Share of started items with acceptance criteria",
            ac / len(started),
            "share",
            "items.csv",
            len(started),
            "items started in the window",
        )

    # WIP: for each day in the window, items in progress per assignee who held any item in the window.
    people = {r["assignee"] for r in items if r["assignee"] and r["started"] and r["started"] <= end and (r["completed"] is None or r["completed"] >= start)}
    if people:
        total = 0
        day = start
        days = 0
        while day <= end:
            total += sum(
                1 for r in items if r["assignee"] in people and r["started"] and r["started"] <= day and (r["completed"] is None or r["completed"] > day)
            )
            days += 1
            day += timedelta(days=1)
        led.add(
            "wip_per_person",
            "Work in progress, mean",
            total / (days * len(people)),
            "per person",
            "items.csv",
            len(people),
            "items in progress per assignee per day, averaged over the window",
        )

    if cycles:
        in_window = [c for c in cycles if start <= c["end"] <= end]
        names = {c["cycle"]: c for c in in_window}
        scoped = [r for r in items if r["cycle"] in names and r["planned"] is not None]
        if in_window and scoped:
            led.add(
                "cycles_in_window", "Cycles ending in the window", len(in_window), "count", "cycles.csv", len(in_window), "cycles whose end falls in the window"
            )
            unplanned = sum(1 for r in scoped if not r["planned"])
            led.add(
                "unplanned_share",
                "Share of cycle work added after the cycle started",
                unplanned / len(scoped),
                "share",
                "items.csv + cycles.csv",
                len(scoped),
                "items with planned false, of items in cycles ending in the window",
            )
            planned = [r for r in scoped if r["planned"]]
            if planned:
                hit = sum(1 for r in planned if r["completed"] and r["completed"] <= names[r["cycle"]]["end"])
                led.add(
                    "planning_accuracy",
                    "Planning accuracy",
                    hit / len(planned),
                    "share",
                    "items.csv + cycles.csv",
                    len(planned),
                    "planned items completed by their cycle end, of planned items",
                )


def _prs(led: Ledger, prs: list[dict], start: date, end: date) -> None:
    in_window = [p for p in prs if _in(p["opened"].date(), start, end)]
    if in_window and in_window[0].get("author") is not None:
        authors = {p["author"] for p in in_window if p["author"]}
        led.add(
            "pr_authors",
            "Pull request authors",
            len(authors),
            "count",
            "pull_requests.csv",
            len(in_window),
            "distinct authors of pull requests opened in the window",
        )
    opened = [p for p in prs if _in(p["opened"].date(), start, end) and p["first_review"]]
    if opened:
        hours = [(p["first_review"] - p["opened"]).total_seconds() / 3600 for p in opened]
        led.add(
            "review_wait_median",
            "Time to first review, median",
            statistics.median(hours),
            "hours",
            "pull_requests.csv",
            len(opened),
            "first review minus opened, calendar hours",
        )
        led.add(
            "review_wait_p85",
            "Time to first review, 85th percentile",
            nearest_rank(hours, 85),
            "hours",
            "pull_requests.csv",
            len(opened),
            "nearest rank, calendar hours",
        )
        _by_squad(
            led,
            "review_wait",
            "Time to first review, median",
            opened,
            lambda p: (p["first_review"] - p["opened"]).total_seconds() / 3600,
            "hours",
            "pull_requests.csv",
        )
    merged = [p for p in prs if p["merged"] and _in(p["merged"].date(), start, end) and p["approvals"] is not None]
    if merged:
        approved = sum(1 for p in merged if p["approvals"] >= 1)
        led.add(
            "review_coverage",
            "Share of merged pull requests with an approval",
            approved / len(merged),
            "share",
            "pull_requests.csv",
            len(merged),
            "merged in the window with 1 or more approvals",
        )


def compute(data: dict, as_of: date, window_days: int) -> dict:
    start = as_of - timedelta(days=window_days - 1)
    led = Ledger(start, as_of)
    if "items" in data:
        _items(led, data["items"], data.get("cycles"), start, as_of)
    if "pull_requests" in data:
        _prs(led, data["pull_requests"], start, as_of)
    if data.get("squads"):
        sq = data["squads"]
        cross = sum(1 for s in sq if {x.strip().lower() for x in s["roles"].split(";")} >= ROLES_FOR_CROSS_FUNCTIONAL)
        led.add(
            "cross_functional_squads",
            "Share of squads with product, design and engineering",
            cross / len(sq),
            "share",
            "squads.csv",
            len(sq),
            "squads listing pm, design and eng roles",
        )
    if data.get("epics"):
        ep = data["epics"]
        led.add(
            "epic_success_criteria",
            "Share of epics with success criteria",
            sum(1 for e in ep if e["success_criteria"]) / len(ep),
            "share",
            "epics.csv",
            len(ep),
            "epics with success_criteria true",
        )
    if "retro_actions" in data:
        cutoff = as_of - timedelta(days=RETRO_CLOSE_DAYS)
        old = [a for a in data["retro_actions"] if start <= a["raised"] <= cutoff]
        if old:
            closed = sum(1 for a in old if a["closed"] and (a["closed"] - a["raised"]).days <= RETRO_CLOSE_DAYS)
            led.add(
                "retro_closed_30d",
                "Share of retro actions closed within 30 days",
                closed / len(old),
                "share",
                "retro_actions.csv",
                len(old),
                "actions raised in the window and at least 30 days before the as-of date",
            )
    if "experiments" in data:
        n = sum(1 for e in data["experiments"] if _in(e["launched"], start, as_of))
        led.add("experiments_launched", "Experiments launched", n, "count", "experiments.csv", n, "experiments with a launch date in the window")
    if data.get("survey"):
        by_dim = defaultdict(list)
        for r in data["survey"]:
            by_dim[r["dimension"]].append(r["score"])
        for dim, scores in sorted(by_dim.items()):
            led.add(
                f"survey.{dim}",
                f"Team survey, {BY_ID[dim]['name']}, mean score",
                statistics.mean(scores),
                "of 5",
                "survey.csv",
                len(scores),
                "mean of 1 to 5 responses, self-reported",
            )
    return {"window": {"start": start.isoformat(), "end": as_of.isoformat(), "days": window_days}, "figures": led.figures}
