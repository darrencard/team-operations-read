#!/usr/bin/env python3
"""Normalise one source's data into run/data/<source>.json.

Usage:
  python3 scripts/collect.py tracker --csv issues.csv --system Linear --run run
  python3 scripts/collect.py billing --json export.json --system Stripe --query "subscriptions, monthly" --run run
  python3 scripts/collect.py --list                      # every source and the columns it needs

The data can come from any connector the session has, or from a CSV upload.
Fetch the rows with whatever tool is available, save them as CSV or JSON, and
pass the file here. This script does not call any connector itself, so it
works the same with or without one.

It checks the columns, coerces numbers and dates, and records where the data
came from. A file with missing columns is rejected with the list of what is
missing. Rows are never invented or filled in.

Standard library only. Runs on Python 3.9 or later.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import json
import sys
from pathlib import Path
from typing import Any

Json = dict[str, Any]

# An export covers one reporting period for one source; a file over 50 MB is the wrong file, not a bigger period.
MAX_FILE_BYTES = 50 * 1024 * 1024
# Same reasoning by rows: one period of one source stays far under 500,000 rows, and more would not fit in memory in a sandbox.
MAX_ROWS = 500_000
# A file with many bad rows has one cause; the first 10 are enough to find it.
MAX_PROBLEMS_SHOWN = 10

# column: kind. Kinds: str, num, date, bool. A trailing ? marks an optional column.
SOURCES = {
    "tracker": {
        "label": "Issue tracker",
        "columns": {
            "id": "str",
            "title": "str",
            "work_type": "str",
            "status": "str",
            "estimate": "num",
            "completed_at": "date?",
            "product_line": "str?",
            "objective": "str?",
            "owner": "str?",
        },
    },
    "finance": {"label": "Finance actuals", "columns": {"line": "str", "period": "str", "plan": "num", "actual": "num"}},
    "billing": {"label": "Billing", "columns": {"account": "str", "month": "str", "arr": "num"}},
    "analytics": {"label": "Product analytics", "columns": {"metric": "str", "period": "str", "value": "num", "definition": "str?"}},
    "warehouse": {"label": "Warehouse", "columns": {"metric": "str", "period": "str", "value": "num", "query": "str"}},
    "crm": {"label": "CRM", "columns": {"deal": "str", "outcome": "str", "reason": "str"}},
    "support": {"label": "Support desk", "columns": {"ticket": "str", "theme": "str", "account": "str?"}},
    "customer_requests": {
        "label": "Customer requests",
        "columns": {"request": "str", "customer": "str", "linked_to": "str", "link": "str?", "created_at": "date"},
    },
    "research": {"label": "Research and call notes", "columns": {"id": "str", "date": "date", "finding": "str", "kind": "str?"}},
    "source_control": {
        "label": "Source control and CI",
        "columns": {
            "kind": "str",
            "id": "str",
            "opened_at": "date?",
            "merged_at": "date?",
            "review_hours": "num?",
            "deployed_at": "date?",
            "failed": "bool?",
            "reworked": "bool?",
            "troubled": "bool?",
            "agent_authored": "bool?",
        },
    },
    "incidents": {"label": "Incidents and status", "columns": {"id": "str", "started_at": "date", "restored_at": "date", "severity": "str?"}},
    "security": {"label": "Security tracker", "columns": {"finding": "str", "severity": "str", "opened_at": "date", "status": "str"}},
    "evals": {
        "label": "Evals and traces",
        "columns": {"version": "str", "run_at": "date", "cases": "num", "passed": "num", "cost_per_task": "num?", "tasks": "num?", "tasks_unassisted": "num?"},
    },
    "ai_tools": {"label": "AI tool admin data", "columns": {"tool": "str", "period": "str", "seats": "num", "weekly_active": "num", "cost": "num"}},
    "survey": {"label": "Developer survey", "columns": {"question": "str", "period": "str", "score": "num"}},
    "hr": {"label": "HR and hiring", "columns": {"function": "str", "now": "num", "plan": "num", "open_roles": "str?"}},
    "docs": {"label": "Documents", "columns": {"document": "str", "kind": "str", "updated_at": "date?", "location": "str?"}},
}

KIND_NAMES = {"num": "number", "date": "date (YYYY-MM-DD)", "bool": "yes or no"}
TRUE_WORDS = ("1", "true", "yes", "y")
FALSE_WORDS = ("0", "false", "no", "n")


def is_optional(kind: str) -> bool:
    return kind.endswith("?")


def parse_date(v: str) -> str:
    """Accept YYYY-MM-DD with or without a time. Anything else is an error, not a guess."""
    v = v.strip().replace("Z", "+00:00")
    try:
        return datetime.datetime.fromisoformat(v).isoformat(timespec="seconds")
    except ValueError:
        return datetime.datetime.fromisoformat(v + "T00:00:00").isoformat(timespec="seconds")


def parse_bool(text: str) -> bool:
    word = text.lower()
    if word in TRUE_WORDS:
        return True
    if word in FALSE_WORDS:
        return False
    raise ValueError(text)


def parse_number(text: str) -> float:
    return float(text.replace(",", "").replace("$", "").replace("%", ""))


def coerce(value: object, kind: str, column: str, line: int) -> str | float | bool | None:
    optional = is_optional(kind)
    kind = kind.rstrip("?")
    if value is None or str(value).strip() == "":
        if optional:
            return None
        raise ValueError(f"row {line}: {column} is empty")
    text = str(value).strip()
    try:
        if kind == "num":
            return parse_number(text)
        if kind == "date":
            return parse_date(text)
        if kind == "bool":
            return parse_bool(text)
    except ValueError:
        raise ValueError(f"row {line}: {column} has {text!r}, expected a {KIND_NAMES[kind]}") from None
    return text


def too_many_rows(origin: str) -> SystemExit:
    return SystemExit(
        f"collect: {origin} has more than {MAX_ROWS:,} rows. An export for one reporting period is far smaller; filter it to the period and pass that file."
    )


def read_csv(path: Path, origin: str) -> list[Json]:
    rows: list[Json] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if len(rows) >= MAX_ROWS:
                raise too_many_rows(origin)
            rows.append(row)
    return rows


def read_json(path: Path, origin: str) -> list[Json]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data["rows"] if isinstance(data, dict) and "rows" in data else data
    if not isinstance(rows, list):
        raise SystemExit(f"collect: {origin} must hold a list of rows, or an object with a rows list")
    if len(rows) > MAX_ROWS:
        raise too_many_rows(origin)
    if not all(isinstance(row, dict) for row in rows):
        raise SystemExit(f'collect: every row in {origin} must be an object of column: value, for example {{"id": "A-1"}}. Export it again as rows.')
    return rows


def load_rows(origin: str, kind: str) -> list[Json]:
    """Read the rows of a CSV or JSON export, or exit with one line that says what to do about it."""
    path = Path(origin)
    try:
        size = path.stat().st_size
        if not path.is_file():
            raise SystemExit(f"collect: {origin} is not a file. Pass the exported {kind.upper()} file itself.")
        if size > MAX_FILE_BYTES:
            raise SystemExit(
                f"collect: {origin} is {size / (1024 * 1024):.0f} MB; the limit is {MAX_FILE_BYTES // (1024 * 1024)} MB. "
                "An export for one reporting period is far smaller; filter it to the period and pass that file."
            )
        return read_csv(path, origin) if kind == "csv" else read_json(path, origin)
    except FileNotFoundError:
        raise SystemExit(f"collect: {origin} does not exist. Check the path, then run this again.") from None
    except UnicodeDecodeError:
        raise SystemExit(f"collect: {origin} is not UTF-8 text. Export it again as UTF-8 {kind.upper()}, then run this again.") from None
    except json.JSONDecodeError as e:
        raise SystemExit(f"collect: {origin} is not valid JSON (line {e.lineno}, column {e.colno}: {e.msg}). Fix the file or export it again.") from None
    except csv.Error as e:
        raise SystemExit(f"collect: {origin} is not a CSV this can read ({e}). Export it again as plain UTF-8 CSV.") from None
    except OSError as e:
        raise SystemExit(f"collect: cannot read {origin} ({e.strerror}). Check the file's permissions, then run this again.") from None


def describe_columns(spec: dict[str, str]) -> str:
    return ", ".join(column + (" (optional)" if is_optional(kind) else "") for column, kind in spec.items())


def collect(source: str, rows: list[Json], system: str, query: str | None, retrieved_at: str, origin: str) -> Json:
    spec = SOURCES[source]["columns"]
    if not rows:
        raise SystemExit(f"collect: {origin} has no rows. An empty source stays Unknown; do not create an empty file for it.")
    have = set(rows[0].keys())
    missing = [c for c, k in spec.items() if not is_optional(k) and c not in have]
    if missing:
        raise SystemExit(f"collect: {origin} is missing the column(s) {', '.join(missing)}. {SOURCES[source]['label']} needs: {describe_columns(spec)}.")
    out, problems = [], []
    for i, row in enumerate(rows, start=2):
        try:
            out.append({c: coerce(row.get(c), k, c, i) for c, k in spec.items()})
        except ValueError as e:
            problems.append(str(e))
    if problems:
        shown = "\n  ".join(problems[:MAX_PROBLEMS_SHOWN])
        raise SystemExit(f"collect: {origin} has {len(problems)} bad row(s). Fix the file; rows are not skipped silently.\n  {shown}")
    return {"source": source, "system": system, "query_or_url": query, "retrieved_at": retrieved_at, "origin": Path(origin).name, "rows": out}


def retrieved_date(given: str | None, origin: str) -> str:
    """The day the data was fetched: the one passed in, or the file's modified date."""
    if given is None:
        return datetime.date.fromtimestamp(Path(origin).stat().st_mtime).isoformat()
    try:
        datetime.date.fromisoformat(given)
    except ValueError:
        raise SystemExit(f"collect: --retrieved-at {given!r} is not a date. Use YYYY-MM-DD, for example 2026-09-30.") from None
    return given


def list_sources() -> None:
    for key in sorted(SOURCES):
        columns = ", ".join(c + ("?" if is_optional(k) else "") for c, k in SOURCES[key]["columns"].items())
        print(f"{key:<15} {columns}")


def run(source: str | None = None) -> int:
    ap = argparse.ArgumentParser(description="Normalise one source's data.")
    if source is None:
        ap.add_argument("source", nargs="?", choices=sorted(SOURCES))
    ap.add_argument("--csv")
    ap.add_argument("--json")
    ap.add_argument("--system", help='the system the data came from, for the ledger, for example "Linear"')
    ap.add_argument("--query", help="the query, report or URL that produced the data")
    ap.add_argument("--retrieved-at", help="YYYY-MM-DD; defaults to the file's modified date")
    ap.add_argument("--run", default="run", help="the run directory")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    source = source or args.source
    if args.list or not source:
        list_sources()
        return 0
    if bool(args.csv) == bool(args.json):
        raise SystemExit("collect: pass exactly one of --csv or --json")
    if not args.system:
        raise SystemExit("collect: --system is required. The ledger must name where each figure came from.")
    origin, kind = (args.csv, "csv") if args.csv else (args.json, "json")
    rows = load_rows(origin, kind)
    retrieved = retrieved_date(args.retrieved_at or None, origin)
    data = collect(source, rows, args.system, args.query, retrieved, origin)
    path = Path(args.run) / "data" / f"{source}.json"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    except OSError as e:
        raise SystemExit(f"collect: cannot write {path} ({e.strerror}). Check that --run names a folder you can write to.") from None
    print(f"collect: {SOURCES[source]['label']}, {len(data['rows'])} rows from {args.system}, retrieved {retrieved}, written to {path}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
