#!/usr/bin/env python3
"""Turn raw Linear exports into the tracker source, with no retyping.

Usage:
  python3 scripts/from_linear.py --issues page1.json [page2.json ...] --work-type-prefix "type:" --run run
  python3 scripts/from_linear.py --projects projects.json --period-start 2026-10-01 --period-end 2026-12-31 \
      [--project-updates updates.json] [--initiatives initiatives.json] --run run
  python3 scripts/from_linear.py --customer-needs needs.json --run run

Modes can be combined in one call. What each export becomes:
  --issues          completed issues, into the tracker source (slides 3, 4, 5). With --initiatives, an
                    issue with no objective label takes its project's initiative as its objective.
  --projects        projects, into run/linear/commitments.csv for slide 8: a project completed inside the
                    period is shipped; one with a target date inside the period that did not complete is
                    not. Its metric comes only from a "Landing brief" block in its description; with none,
                    the metric is left empty and the slide says so. A brief with a metric and a bar also goes
                    to run/linear/targets.csv, for slide 11. Both files are imported with intake.py import,
                    and the person confirms each row. Nothing here writes the intake.
  --project-updates the latest update per project, shown beside each commitment for the person to check.
                    Its text is never read as a result: results come from the team's metrics.
  --initiatives     initiatives and their projects, into run/linear/initiatives.csv for slide 3. Linear holds
                    no cause or confidence, so those columns stay empty for the interview to fill.
  --customer-needs  customer requests linked to issues or projects, into the customer_requests source
                    (slides 6 and 7). A request linked to neither is left out and counted.

Inputs are what Linear already gives you, saved to a file as it stands, one file per page:
  - the Linear connector's list_issues result ({"issues": [...], "hasNextPage": ..., "cursor": ...}),
    asked for completed issues with the fields id, title, estimate, completedAt, statusType, labels,
    project and assignee; or
  - the Linear GraphQL API's response ({"data": {"issues": {"nodes": [...]}}}).

How each completed issue maps to a tracker row, in code:
  work_type     the label that starts with --work-type-prefix, without the prefix, or a label named
                in --work-type (repeat it: --work-type "Bug=Keep the lights on"). An issue with
                neither is "Unlabelled", so the untyped share shows instead of being guessed.
  estimate      Linear's estimate. An issue with no estimate is left out and counted, never given one.
  product_line  the issue's project.
  objective     the label that starts with --objective-prefix, without the prefix, if one is given.
  owner         the assignee.

This script reads files and writes a file. It makes no network calls.

Standard library only. Runs on Python 3.9 or later.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import collect  # noqa: E402  (a sibling script, found through the path above)
import landing_brief  # noqa: E402  (a sibling script; the same file ships in the landing-brief skill)

Json = dict[str, Any]

UNLABELLED = "Unlabelled"


def fail(message: str) -> SystemExit:
    return SystemExit(f"from_linear: {message}")


def name_of(value: Any) -> str | None:
    """Linear's connector gives names as strings; its API gives objects with a name."""
    if isinstance(value, dict):
        return value.get("name") or value.get("displayName")
    return value if isinstance(value, str) and value else None


def labels_of(issue: Json) -> list[str]:
    raw = issue.get("labels") or []
    if isinstance(raw, dict):
        raw = raw.get("nodes") or []
    return [n for n in (name_of(x) for x in raw) if n]


def read_issues(paths: list[Path]) -> list[Json]:
    found: dict[str, Json] = {}
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
            raise fail(f"cannot read {path} ({e}). Save the export as it stands, as UTF-8 JSON.") from None
        if isinstance(data, dict) and "data" in data:
            data = (data["data"] or {}).get("issues") or {}
        items = data.get("issues", data.get("nodes")) if isinstance(data, dict) else data
        if isinstance(items, dict):
            items = items.get("nodes")
        if not isinstance(items, list) or not all(isinstance(x, dict) for x in items):
            raise fail(f"{path} holds no list of issues, as Linear returns it.")
        for issue in items:
            key = issue.get("identifier") or issue.get("id")
            if key:
                found[str(key)] = issue  # pages can overlap; one row per issue
    return list(found.values())


def completed(issue: Json) -> bool:
    state = issue.get("state")
    kind = issue.get("statusType") or (state.get("type") if isinstance(state, dict) else None)
    return bool(issue.get("completedAt")) and kind in (None, "completed")


def with_prefix(labels: list[str], prefix: str | None) -> str | None:
    if not prefix:
        return None
    return next((x[len(prefix) :].strip() for x in labels if x.lower().startswith(prefix.lower()) and x[len(prefix) :].strip()), None)


def one(values: list[str]) -> str:
    """The only value, or nothing: an issue whose project serves two initiatives is not given one of them."""
    return values[0] if len(values) == 1 else ""


def to_rows(
    issues: list[Json],
    type_prefix: str | None,
    type_map: dict[str, str],
    objective_prefix: str | None,
    initiatives: dict[str, list[str]] | None = None,
) -> tuple[list[Json], int]:
    """Tracker rows. An issue with no objective label takes its project's initiative, only when there is exactly one."""
    rows, unestimated = [], 0
    initiatives = initiatives or {}
    for issue in issues:
        if not completed(issue):
            continue
        if issue.get("estimate") is None:
            unestimated += 1
            continue
        labels = labels_of(issue)
        mapped = next((type_map[x] for x in labels if x in type_map), None)
        rows.append(
            {
                "id": str(issue.get("identifier") or issue.get("id")),
                "title": issue.get("title") or "",
                "work_type": with_prefix(labels, type_prefix) or mapped or UNLABELLED,
                "status": name_of(issue.get("status")) or name_of(issue.get("state")) or "Done",
                "estimate": issue["estimate"],
                "completed_at": issue["completedAt"],
                "product_line": name_of(issue.get("project")) or "",
                "objective": with_prefix(labels, objective_prefix) or one(initiatives.get(name_of(issue.get("project")) or "", [])),
                "owner": name_of(issue.get("assignee")) or "",
            }
        )
    return rows, unestimated


# ---- projects, updates, initiatives and customer requests ------------------


def read_items(paths: list[Path], kinds: tuple[str, ...], what: str) -> list[Json]:
    """Every object in Linear's own shapes: the connector's {"<kind>": [...]} pages, the API's
    {"data": {"<kind>": {"nodes": [...]}}}, a bare list, or one object holding a list of the kind."""
    out: list[Json] = []
    for path in paths:
        try:
            data: Any = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
            raise fail(f"cannot read {path} ({e}). Save the export as it stands, as UTF-8 JSON.") from None
        if isinstance(data, dict) and isinstance(data.get("data"), dict):
            data = data["data"]
        items: Any = data
        if isinstance(data, dict):
            items = next((data[k] for k in kinds if k in data), data.get("nodes"))
        if isinstance(items, dict):
            items = items.get("nodes")
        if not isinstance(items, list) or not all(isinstance(x, dict) for x in items):
            raise fail(f"{path} holds no list of {what}, as Linear returns them.")
        out.extend(items)
    return out


# A projects CSV, such as Linear's own export, read by column name. Name and status are required.
PROJECT_CSV = {
    "name": "name",
    "status": "status",
    "target date": "targetDate",
    "completed": "completedAt",
    "completed at": "completedAt",
    "lead": "lead",
    "description": "description",
    "url": "url",
    "initiatives": "initiatives",
}


def read_projects_csv(path: Path) -> list[Json]:
    """Projects from a CSV with named columns. A file without name and status columns is refused whole."""
    try:
        with path.open(newline="", encoding="utf-8-sig") as f:
            table = list(csv.reader(f))
    except (OSError, UnicodeDecodeError, csv.Error) as e:
        raise fail(f"cannot read {path} ({e}). Save the export as UTF-8 CSV.") from None
    header = [h.strip().lower() for h in table[0]] if table else []
    if not {"name", "status"} <= set(header):
        raise fail(f"{path} has no name and status columns. Found: {', '.join(header) or 'nothing'}. Nothing was read.")
    out = []
    for row in table[1:]:
        if not any(c.strip() for c in row):
            continue
        project: Json = {}
        for i, h in enumerate(header):
            if h in PROJECT_CSV and i < len(row) and row[i].strip():
                project[PROJECT_CSV[h]] = row[i].strip()
        if isinstance(project.get("initiatives"), str):
            project["initiatives"] = [{"name": x.strip()} for x in project["initiatives"].split(";") if x.strip()]
        out.append(project)
    return out


def nodes(value: Any) -> list[Any]:
    """A related list as the connector gives it (a list) or as the API does ({"nodes": [...]})."""
    if isinstance(value, dict):
        value = value.get("nodes")
    return value if isinstance(value, list) else []


def day(value: Any) -> datetime.date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.date.fromisoformat(value[:10])
    except ValueError:
        return None


def state_of(project: Json) -> str:
    """A project's status type: completed, canceled, started and so on."""
    status = project.get("status")
    if isinstance(status, dict):
        status = status.get("type") or status.get("name")
    return str(status or project.get("state") or "").strip().lower()


def latest_updates(projects: list[Json], updates: list[Json]) -> dict[str, str]:
    """The latest update per project name, as "date, health", for the person to check beside each row."""
    found: dict[str, tuple[str, str]] = {}
    pairs = [(name_of(u.get("project")) or u.get("projectName"), u) for u in updates]
    pairs += [(name_of(p), u) for p in projects for u in nodes(p.get("projectUpdates")) + ([p["lastUpdate"]] if isinstance(p.get("lastUpdate"), dict) else [])]
    for name, u in pairs:
        if not isinstance(u, dict):
            continue
        when = str(u.get("createdAt") or u.get("updatedAt") or "")[:10]
        if name and when and (name not in found or when > found[name][0]):
            found[name] = (when, str(u.get("health") or "no health set"))
    return {name: f"{when}, {health}" for name, (when, health) in found.items()}


def brief_of(project: Json) -> tuple[landing_brief.Brief | None, str]:
    """The project's landing brief, or None and why there is none. Nothing is guessed from other text."""
    text = "\n".join(project[k] for k in ("content", "description") if isinstance(project.get(k), str))
    if not any(landing_brief.HEADING.match(x.strip()) for x in text.splitlines()):
        return None, "no landing brief in the description"
    try:
        return landing_brief.parse(text), ""
    except landing_brief.BriefError as e:
        return None, f"its landing brief is incomplete ({str(e).splitlines()[-1].strip()})"


COMMITMENT_COLUMNS = ("commitment", "shipped", "metric", "owner", "source", "url", "status", "target date", "completed", "latest update", "note")
TARGET_COLUMNS = ("metric", "target", "better", "by", "owner", "source")


def projects_to_rows(
    projects: list[Json], start: datetime.date, end: datetime.date, workspace: str, updates: dict[str, str]
) -> tuple[list[Json], list[Json], list[str]]:
    """(commitments, targets, notes). A project is a commitment of the period when it completed inside it,
    or was due inside it and did not complete. Others are not this period's commitments and are left out."""
    commitments, targets, notes = [], [], []
    for p in projects:
        name = name_of(p)
        if not name:
            continue
        state, done, due = state_of(p), day(p.get("completedAt")), day(p.get("targetDate"))
        if state == "completed" and done is None:
            notes.append(f"{name}: completed, with no completion date, so it cannot be placed in the period. Left out.")
            continue
        shipped = state == "completed" and done is not None and start <= done <= end
        if not shipped and not (due and start <= due <= end and state != "completed"):
            continue
        brief, why = brief_of(p)
        if brief is None:
            notes.append(f"{name}: {why}. Its metric is left empty.")
        url = p.get("url") if isinstance(p.get("url"), str) and re.match(r"https://", p["url"]) else ""
        owner = name_of(p.get("lead")) or ""
        commitments.append(
            {
                "commitment": name,
                "shipped": "yes" if shipped else "no",
                "metric": brief.metric if brief else "",
                "owner": owner,
                "source": f"Linear projects ({workspace})",
                "url": url,
                "status": state or "not stated",
                "target date": due.isoformat() if due else "",
                "completed": done.isoformat() if done else "",
                "latest update": updates.get(name, "none"),
                "note": "" if brief else why,
            }
        )
        if brief:
            targets.append(
                {
                    "metric": brief.metric,
                    "target": brief.bar_text,
                    "better": "higher" if brief.higher_is_better else "lower",
                    "by": brief.by,
                    "owner": owner,
                    "source": f"Linear project {name}",
                }
            )
    return commitments, targets, notes


def initiative_map(initiatives: list[Json], projects: list[Json]) -> dict[str, list[str]]:
    """Each project's initiatives, from the initiatives' project lists and the projects' own initiative lists."""
    found: dict[str, list[str]] = {}
    for i in initiatives:
        for p in nodes(i.get("projects")):
            if name_of(p) and name_of(i):
                found.setdefault(name_of(p), []).append(name_of(i))
    for p in projects:
        for i in nodes(p.get("initiatives")):
            if name_of(p) and name_of(i):
                found.setdefault(name_of(p), []).append(name_of(i))
    return {k: list(dict.fromkeys(v)) for k, v in found.items()}


def needs_to_rows(needs: list[Json]) -> tuple[list[Json], int]:
    """Customer requests linked to an issue or a project. A request linked to neither is left out and counted."""
    rows, unlinked = [], 0
    for n in needs:
        issue, project = n.get("issue"), n.get("project")
        target = issue if isinstance(issue, dict) else project if isinstance(project, dict) else None
        if target is None:
            unlinked += 1
            continue
        if target is issue:
            linked = " ".join(x for x in (target.get("identifier"), target.get("title")) if isinstance(x, str) and x) or str(target.get("id") or "")
        else:
            linked = name_of(target) or str(target.get("id") or "")
        url = target.get("url") if isinstance(target.get("url"), str) and target["url"].startswith("https://") else None
        rows.append(
            {
                "request": str(n.get("id") or ""),
                "customer": name_of(n.get("customer")) or "",
                "linked_to": linked,
                "link": url,
                "created_at": n.get("createdAt"),
            }
        )
    return rows, unlinked


def cell(value: Any) -> Any:
    """A cell a spreadsheet will not run as a formula: text from Linear that starts with = + - or @ gets a leading quote."""
    return f"'{value}" if isinstance(value, str) and value[:1] in ("=", "+", "-", "@") else value


def write_csv(path: Path, columns: tuple[str, ...], rows: list[Json]) -> None:
    rows = [{k: cell(v) for k, v in r.items()} for r in rows]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(columns))
        writer.writeheader()
        writer.writerows(rows)


def parse_day(value: str | None, flag: str) -> datetime.date:
    try:
        return datetime.date.fromisoformat(value or "")
    except ValueError:
        raise fail(f"{flag} needs a date as YYYY-MM-DD, got {value!r}.") from None


def main() -> int:
    ap = argparse.ArgumentParser(description="Turn raw Linear exports into the update's sources.")
    ap.add_argument("--issues", nargs="+", help="completed issues as Linear returns them, one file per page")
    ap.add_argument("--projects", nargs="+", help="projects as Linear returns them, with status, dates, lead and description")
    ap.add_argument("--project-updates", nargs="+", default=[], help="project updates as Linear returns them")
    ap.add_argument("--initiatives", nargs="+", default=[], help="initiatives as Linear returns them, with their projects")
    ap.add_argument("--customer-needs", nargs="+", help="customer requests as Linear returns them, with their issue or project")
    ap.add_argument("--period-start", help="--projects: the first day of the period, YYYY-MM-DD")
    ap.add_argument("--period-end", help="--projects: the last day of the period, YYYY-MM-DD")
    ap.add_argument("--work-type-prefix", help='the label prefix that names a work type, for example "type:"')
    ap.add_argument("--work-type", action="append", default=[], metavar="LABEL=TYPE", help="a label that stands for a work type; repeat it")
    ap.add_argument("--objective-prefix", help='the label prefix that names an objective, for example "objective:"')
    ap.add_argument("--workspace", default="Linear", help="the workspace or team name, for the ledger")
    ap.add_argument("--retrieved-at", help="YYYY-MM-DD; defaults to the first file's modified date")
    ap.add_argument("--run", default="run")
    args = ap.parse_args()
    if not (args.issues or args.projects or args.initiatives or args.customer_needs):
        raise fail("pass at least one of --issues, --projects, --initiatives or --customer-needs.")
    run = Path(args.run)

    project_files = [Path(p) for p in args.projects or []]
    projects = read_items([p for p in project_files if p.suffix.lower() != ".csv"], ("projects",), "projects")
    projects += [x for p in project_files if p.suffix.lower() == ".csv" for x in read_projects_csv(p)]
    initiatives = read_items([Path(p) for p in args.initiatives], ("initiatives",), "initiatives")
    by_project = initiative_map(initiatives, projects)

    if args.projects:
        start, end = parse_day(args.period_start, "--period-start"), parse_day(args.period_end, "--period-end")
        if end < start:
            raise fail("--period-end is before --period-start.")
        updates = read_items([Path(p) for p in args.project_updates], ("statusUpdates", "projectUpdates", "updates"), "project updates")
        commitments, targets, notes = projects_to_rows(projects, start, end, args.workspace, latest_updates(projects, updates))
        if not commitments:
            raise fail(f"found no project completed or due between {start} and {end}. Slide 8 stays a gap; do not create a file for it.")
        write_csv(run / "linear" / "commitments.csv", COMMITMENT_COLUMNS, commitments)
        shipped = sum(1 for c in commitments if c["shipped"] == "yes")
        print(f"from_linear: {len(commitments)} commitments ({shipped} shipped), written to {run / 'linear' / 'commitments.csv'}.")
        for note in notes:
            print(f"from_linear:   {note}")
        if targets:
            write_csv(run / "linear" / "targets.csv", TARGET_COLUMNS, targets)
            print(f"from_linear: {len(targets)} target metric(s) stated in landing briefs, written to {run / 'linear' / 'targets.csv'}.")
        print("from_linear: show the rows to the person, then import with intake.py import --commitments (and --targets).")

    if initiatives:
        rows = [
            {
                "initiative": name_of(i),
                "owner": name_of(i.get("owner")) or "",
                "projects": "; ".join(p for p, names in sorted(by_project.items()) if name_of(i) in names),
                "cause": "",
                "confidence": "",
            }
            for i in initiatives
            if name_of(i)
        ]
        write_csv(run / "linear" / "initiatives.csv", ("initiative", "owner", "projects", "cause", "confidence"), rows)
        print(f"from_linear: {len(rows)} initiative(s), written to {run / 'linear' / 'initiatives.csv'}.")
        print("from_linear: Linear holds no cause or confidence. Ask the person for each before slide 3 can show the branch.")

    if args.customer_needs:
        needs = read_items([Path(p) for p in args.customer_needs], ("customerNeeds", "needs"), "customer requests")
        needs += [
            dict(n, project=n.get("project") or {"name": name_of(p), "url": p.get("url")})
            for p in projects
            for n in nodes(p.get("customerNeeds"))
            if isinstance(n, dict)
        ]
        rows, unlinked = needs_to_rows(needs)
        if not rows:
            raise fail("found no customer requests linked to an issue or a project. The source stays Unknown; do not create a file for it.")
        retrieved = collect.retrieved_date(args.retrieved_at, args.customer_needs[0])
        data = collect.collect(
            "customer_requests", rows, f"Linear ({args.workspace})", "Linear customer requests", retrieved, Path(args.customer_needs[0]).name
        )
        out = run / "data" / "customer_requests.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"from_linear: {len(rows)} customer requests linked to an issue or project, written to {out}.")
        if unlinked:
            print(f"from_linear: {unlinked} request(s) are linked to no issue or project and are left out.")

    if args.issues:
        issues = read_issues([Path(p) for p in args.issues])
        type_map = {}
        for pair in args.work_type:
            if "=" not in pair:
                raise fail(f'--work-type takes LABEL=TYPE, for example --work-type "Bug=Keep the lights on". Got {pair!r}.')
            label, kind = pair.split("=", 1)
            type_map[label.strip()] = kind.strip()
        rows, unestimated = to_rows(issues, args.work_type_prefix, type_map, args.objective_prefix, by_project)
        if not rows:
            extra = f" {unestimated} completed issue(s) had no estimate." if unestimated else ""
            raise fail(f"found no completed issues with an estimate.{extra} The tracker stays Unknown; do not create a file for it.")
        retrieved = collect.retrieved_date(args.retrieved_at, args.issues[0])
        query = "Linear list_issues (completed, with estimate, labels, project, assignee)"
        data = collect.collect("tracker", rows, f"Linear ({args.workspace})", query, retrieved, Path(args.issues[0]).name)
        out = run / "data" / "tracker.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        untyped = sum(1 for r in rows if r["work_type"] == UNLABELLED)
        print(f"from_linear: {len(rows)} completed issues with an estimate, written to {out}.")
        if unestimated:
            print(f"from_linear: {unestimated} completed issue(s) have no estimate and are left out. They are not given one.")
        if untyped:
            print(f'from_linear: {untyped} issue(s) carry no work-type label and count as "{UNLABELLED}".')
    return 0


if __name__ == "__main__":
    sys.exit(main())
