"""Write the Acme fixture: invented, illustrative exports for a read.

Acme is a made-up company: invoicing software for trades businesses, Series C, about 400 people,
12 squads, with an assistant that drafts quotes and chases invoices. The Quoting squad is the team
behind the quote-drafting bet in the Landing Loop's Acme sample. Every row is synthetic.

    python3 evals/make_fixture.py   # rewrites examples/acme/data/
"""

from __future__ import annotations

import csv
import json
import random
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "examples" / "acme" / "data"
AS_OF = date(2026, 11, 20)
SQUADS = ["Quoting", "Invoices", "Chasing", "Payments", "Scheduling", "Mobile", "Platform", "Data", "Assistant", "Growth", "Integrations", "Reporting"]
# Median days in progress per work type. Bugs move far faster than features.
TYPES = [("feature", 0.40, 10), ("bug", 0.30, 2), ("chore", 0.20, 4), ("improvement", 0.10, 6)]


def _write(name: str, header: list[str], rows: list[list]) -> None:
    with (OUT / name).open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def main() -> None:
    rng = random.Random(20261120)
    OUT.mkdir(parents=True, exist_ok=True)

    cycles = []
    start = date(2026, 8, 24)
    for i in range(7):
        s = start + timedelta(days=14 * i)
        cycles.append([f"C{i + 1}", s.isoformat(), (s + timedelta(days=13)).isoformat()])
    _write("cycles.csv", ["cycle", "start", "end"], cycles)

    items = []
    n = 0
    for sq in SQUADS:
        people = [f"{sq.lower()}-eng-{k}" for k in range(1, 6)]
        for c in cycles[:6]:
            c_start = date.fromisoformat(c[1])
            for _ in range(8):
                n += 1
                t = rng.choices([x[0] for x in TYPES], [x[1] for x in TYPES])[0]
                median = dict((x[0], x[2]) for x in TYPES)[t]
                planned = rng.random() > 0.45
                started = c_start + timedelta(days=0 if planned else rng.randint(1, 10))
                duration = max(0, round(rng.lognormvariate(0, 0.5) * median))
                completed = started + timedelta(days=duration)
                done = "" if completed > AS_OF else completed.isoformat()
                reopened = 1 if rng.random() < 0.18 else 0
                ac = "true" if rng.random() < 0.70 else "false"
                items.append(
                    [
                        f"ACME-{n}",
                        t,
                        sq,
                        rng.choice(people),
                        (started - timedelta(days=3)).isoformat(),
                        started.isoformat(),
                        done,
                        c[0],
                        str(planned).lower(),
                        reopened,
                        ac,
                    ]
                )
    _write("items.csv", ["id", "type", "squad", "assignee", "created", "started", "completed", "cycle", "planned", "reopened", "acceptance_criteria"], items)

    prs = []
    window_start = AS_OF - timedelta(days=89)
    for k in range(1, 901):
        sq = rng.choice(SQUADS)
        opened = datetime.combine(window_start, datetime.min.time(), tzinfo=UTC) + timedelta(hours=rng.randint(0, 88 * 24))
        wait = rng.lognormvariate(3.4, 0.6)  # median about 30 hours
        first = opened + timedelta(hours=wait)
        merged = first + timedelta(hours=rng.randint(1, 48))
        approvals = 0 if rng.random() < 0.08 else rng.randint(1, 2)
        # The author is set from the row number, not drawn, so adding it left every other row unchanged.
        author = f"{sq.lower()}-eng-{k % 5 + 1}"
        prs.append([f"PR-{k}", sq, opened.isoformat(), first.isoformat(), merged.isoformat() if merged.date() <= AS_OF else "", approvals, author])
    _write("pull_requests.csv", ["id", "squad", "opened", "first_review", "merged", "approvals", "author"], prs)

    squads = [[sq, "eng" if sq in ("Platform", "Data") else "pm;design;eng"] for sq in SQUADS]
    _write("squads.csv", ["squad", "roles"], squads)

    epics = [[f"EPIC-{k}", SQUADS[k % 12], "true" if k % 5 < 3 else "false"] for k in range(1, 31)]
    _write("epics.csv", ["id", "squad", "success_criteria"], epics)

    retro = []
    for k in range(1, 41):
        raised = window_start + timedelta(days=rng.randint(0, 55))
        closed = raised + timedelta(days=rng.randint(5, 25)) if k % 5 == 0 else (raised + timedelta(days=rng.randint(40, 60)) if k % 3 == 0 else None)
        retro.append([f"RETRO-{k}", SQUADS[k % 12], raised.isoformat(), closed.isoformat() if closed and closed <= AS_OF else ""])
    _write("retro_actions.csv", ["id", "squad", "raised", "closed"], retro)

    experiments = [
        ["EXP-1", "Quoting", "2026-09-10"],
        ["EXP-2", "Chasing", "2026-10-01"],
        ["EXP-3", "Growth", "2026-10-22"],
        ["EXP-4", "Assistant", "2026-11-05"],
    ]
    _write("experiments.csv", ["id", "squad", "launched"], experiments)

    survey = []
    means = {"delivery_velocity": 3.4, "design_dev_handoff": 2.3, "knowledge_management": 2.1, "team_orchestration": 3.2, "process_iteration": 3.9}
    for r in range(1, 39):
        for dim, mean in means.items():
            score = min(5, max(1, round(rng.gauss(mean, 0.7))))
            survey.append([f"R{r}", dim, score])
    _write("survey.csv", ["respondent", "dimension", "score"], survey)

    manifest = {
        "company": "Acme",
        "illustrative": True,
        "note": "Invented sample data. Acme is not a real company and no figure here describes one.",
        "decides": "Head of Product, Quoting squad",
        "systems": {
            "items.csv": "Illustrative tracker export",
            "cycles.csv": "Illustrative tracker export",
            "epics.csv": "Illustrative tracker export",
            "pull_requests.csv": "Illustrative GitHub export",
            "squads.csv": "Illustrative team list",
            "retro_actions.csv": "Illustrative retro log",
            "experiments.csv": "Illustrative experiment log",
            "survey.csv": "Illustrative team survey",
        },
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
