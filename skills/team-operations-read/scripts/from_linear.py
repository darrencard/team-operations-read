"""Turn a Linear issue export into items.csv (and cycles.csv when the issues carry their cycles).

Live first: ask the session's Linear connector (list_issues) or Linear's GraphQL API for the team's issues
over the window, with id, identifier, team, assignee, labels, createdAt, startedAt, completedAt and cycle
(name or number, startsAt, endsAt), and save each page as it stands. Reading the pages is done by the Leader
Report's own Linear collector (scripts/vendor/from_linear.py, vendored unchanged); this script adds only what
a Team Operations read needs. Then:

    python3 scripts/from_linear.py --issues page1.json [page2.json ...] --out <data folder> \\
      [--type-prefix type: | --type-values bug,feature,chore] [--squad-label-prefix squad:] \\
      [--acceptance-heading "Acceptance criteria"]

How each issue maps, in code:
  squad      the issue's team, or the label after --squad-label-prefix
  type       the label after --type-prefix, or the first of --type-values found in the labels; else "untyped"
  started    startedAt. An issue with no startedAt is kept, and counted, but adds no cycle time
  cycle      the cycle's name, or "Cycle N"; cycles.csv gets each cycle's start and end
  acceptance_criteria  only with --acceptance-heading: true when the description contains that heading

Left out on purpose: `planned` and `reopened`. An issue export cannot say whether an item joined its cycle
after the cycle started, or was reopened; those need Linear's issue history. Their figures stay uncomputed,
never guessed. The CSV route (from_csv.py) maps them when your export holds them.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import vendored  # noqa: E402
from inputs import note_system  # noqa: E402

lr = vendored.load("from_linear")


def _day(value: object) -> str:
    return str(value)[:10] if value else ""


def _cycle(issue: dict) -> tuple[str, str, str]:
    c = issue.get("cycle")
    if isinstance(c, dict):
        name = c.get("name") or (f"Cycle {c['number']}" if c.get("number") is not None else "")
        return name, _day(c.get("startsAt")), _day(c.get("endsAt"))
    if isinstance(c, (int, float)):
        return f"Cycle {int(c)}", "", ""
    return (str(c) if c else ""), "", ""


def _after(labels: list[str], prefix: str | None) -> str | None:
    if not prefix:
        return None
    return next((x[len(prefix) :].strip() for x in labels if x.lower().startswith(prefix.lower()) and x[len(prefix) :].strip()), None)


def _type(labels: list[str], prefix: str | None, values: list[str] | None) -> str:
    found = _after(labels, prefix)
    if found:
        return found.lower()
    low = {x.lower() for x in labels}
    return next((v for v in values or [] if v in low), "untyped")


def convert(
    issues: list[dict],
    type_prefix: str | None = None,
    type_values: list[str] | None = None,
    squad_prefix: str | None = None,
    acceptance_heading: str | None = None,
) -> tuple[list[str], list[list], list[list], dict]:
    """Return (items header, item rows, cycle rows, counts)."""
    header = ["id", "type", "squad", "assignee", "created", "started", "completed", "cycle"] + (["acceptance_criteria"] if acceptance_heading else [])
    rows, cycles, counts = [], {}, {"issues": 0, "no_started": 0, "no_created": 0}
    for issue in issues:
        created = _day(issue.get("createdAt"))
        if not created:
            counts["no_created"] += 1
            continue
        counts["issues"] += 1
        labels = lr.labels_of(issue)
        started, completed = _day(issue.get("startedAt")), _day(issue.get("completedAt"))
        if not started:
            counts["no_started"] += 1
        name, c_start, c_end = _cycle(issue)
        if name and c_start and c_end:
            cycles[name] = [name, c_start, c_end]
        row = [
            str(issue.get("identifier") or issue.get("id")),
            _type(labels, type_prefix, type_values),
            _after(labels, squad_prefix) or lr.name_of(issue.get("team")) or "",
            lr.name_of(issue.get("assignee")) or "",
            created,
            started,
            completed if started else "",
            name,
        ]
        if acceptance_heading:
            row.append("true" if acceptance_heading.lower() in str(issue.get("description") or "").lower() else "false")
        rows.append(row)
    return header, rows, sorted(cycles.values(), key=lambda c: (c[1], c[0])), counts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Convert a Linear issue export to items.csv and cycles.csv.")
    ap.add_argument("--issues", required=True, nargs="+", type=Path, help="Linear connector or GraphQL pages, saved as they stand")
    ap.add_argument("--out", required=True, type=Path)
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--type-prefix", help="labels like type:bug give the work type")
    group.add_argument("--type-values", help="comma-separated label names that are work types, in priority order")
    ap.add_argument("--squad-label-prefix", help="take the squad from a label with this prefix instead of the team")
    ap.add_argument("--acceptance-heading", help="a heading in the description that marks acceptance criteria")
    ap.add_argument("--retrieved-at", help="YYYY-MM-DD the export was taken; defaults to today")
    a = ap.parse_args(argv)
    try:
        issues = lr.read_issues(a.issues)
    except SystemExit as e:  # the vendored reader stops with a message on a file it cannot read
        print(f"error: {e}", file=sys.stderr)
        return 2
    values = [v.strip().lower() for v in a.type_values.split(",")] if a.type_values else None
    header, rows, cycles, counts = convert(issues, a.type_prefix, values, a.squad_label_prefix, a.acceptance_heading)
    a.out.mkdir(parents=True, exist_ok=True)
    with (a.out / "items.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    system = f"Linear, retrieved {a.retrieved_at or date.today().isoformat()}"
    note_system(a.out, "items.csv", system)
    if cycles:
        with (a.out / "cycles.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["cycle", "start", "end"])
            w.writerows(cycles)
        note_system(a.out, "cycles.csv", system)
    print(f"Wrote {len(rows)} issues to {a.out / 'items.csv'}" + (f" and {len(cycles)} cycles to {a.out / 'cycles.csv'}." if cycles else "."))
    if counts["no_started"]:
        print(f"{counts['no_started']} issues have no startedAt, so they add no cycle time. Ask the connector for startedAt.")
    if counts["no_created"]:
        print(f"Left out {counts['no_created']} issues with no createdAt.")
    print("Not mapped: planned and reopened need Linear's issue history, so those figures are not computed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
