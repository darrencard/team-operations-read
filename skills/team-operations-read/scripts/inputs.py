"""Load and check the exports a read uses. Every file is optional; a missing file means its dimensions go unread.

Each loader returns rows as dicts with typed values, or raises InputError naming the file, row and column.
Text cells are data: they are never interpreted, only counted or escaped when shown.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from framework import DIMENSION_IDS


class InputError(ValueError):
    """An export is malformed. The message names the file, row and column."""


@dataclass(frozen=True)
class Spec:
    filename: str
    required: tuple[str, ...]
    dates: tuple[str, ...] = ()
    optional_dates: tuple[str, ...] = ()
    ints: tuple[str, ...] = ()
    bools: tuple[str, ...] = ()
    optional_times: tuple[str, ...] = ()
    times: tuple[str, ...] = ()


SPECS = {
    "items": Spec(
        "items.csv",
        ("id", "type", "squad", "assignee", "created", "started", "completed", "cycle", "planned", "reopened", "acceptance_criteria"),
        dates=("created",),
        optional_dates=("started", "completed"),
        ints=("reopened",),
        bools=("planned", "acceptance_criteria"),
    ),
    "cycles": Spec("cycles.csv", ("cycle", "start", "end"), dates=("start", "end")),
    "pull_requests": Spec(
        "pull_requests.csv",
        ("id", "squad", "opened", "first_review", "merged", "approvals"),
        times=("opened",),
        optional_times=("first_review", "merged"),
        ints=("approvals",),
    ),
    "squads": Spec("squads.csv", ("squad", "roles")),
    "epics": Spec("epics.csv", ("id", "squad", "success_criteria"), bools=("success_criteria",)),
    "retro_actions": Spec("retro_actions.csv", ("id", "squad", "raised", "closed"), dates=("raised",), optional_dates=("closed",)),
    "experiments": Spec("experiments.csv", ("id", "squad", "launched"), dates=("launched",)),
    "survey": Spec("survey.csv", ("respondent", "dimension", "score"), ints=("score",)),
}

TRUE = {"true", "yes", "y", "1"}
FALSE = {"false", "no", "n", "0", ""}


def _date(value: str, where: str) -> date:
    try:
        return date.fromisoformat(value.strip()[:10])
    except ValueError:
        raise InputError(f"{where}: expected a date as YYYY-MM-DD, got {value!r}") from None


def _time(value: str, where: str) -> datetime:
    try:
        t = datetime.fromisoformat(value.strip())
    except ValueError:
        raise InputError(f"{where}: expected an ISO 8601 timestamp, got {value!r}") from None
    return t if t.tzinfo else t.replace(tzinfo=UTC)


def _row(spec: Spec, raw: dict, line: int) -> dict:
    row = {k: (v or "").strip() for k, v in raw.items() if k is not None}
    for col in spec.dates:
        row[col] = _date(row[col], f"{spec.filename} line {line} column {col}")
    for col in spec.optional_dates:
        row[col] = _date(row[col], f"{spec.filename} line {line} column {col}") if row[col] else None
    for col in spec.times:
        row[col] = _time(row[col], f"{spec.filename} line {line} column {col}")
    for col in spec.optional_times:
        row[col] = _time(row[col], f"{spec.filename} line {line} column {col}") if row[col] else None
    for col in spec.ints:
        try:
            row[col] = int(row[col] or "0")
        except ValueError:
            raise InputError(f"{spec.filename} line {line} column {col}: expected a whole number, got {row[col]!r}") from None
    for col in spec.bools:
        v = row[col].lower()
        if v not in TRUE | FALSE:
            raise InputError(f"{spec.filename} line {line} column {col}: expected true or false, got {row[col]!r}")
        row[col] = v in TRUE
    return row


def load_file(path: Path, spec: Spec) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in spec.required if c not in (reader.fieldnames or [])]
        if missing:
            raise InputError(f"{spec.filename}: missing column(s) {', '.join(missing)}")
        return [_row(spec, raw, i) for i, raw in enumerate(reader, start=2)]


def _check(data: dict) -> None:
    for i, row in enumerate(data.get("survey", []), start=2):
        if row["dimension"] not in DIMENSION_IDS:
            raise InputError(f"survey.csv line {i} column dimension: {row['dimension']!r} is not a Team Operations dimension id")
        if not 1 <= row["score"] <= 5:
            raise InputError(f"survey.csv line {i} column score: expected 1 to 5, got {row['score']}")
    for i, row in enumerate(data.get("items", []), start=2):
        if row["started"] and row["completed"] and row["completed"] < row["started"]:
            raise InputError(f"items.csv line {i}: completed is before started")
    for i, row in enumerate(data.get("pull_requests", []), start=2):
        if row["first_review"] and row["first_review"] < row["opened"]:
            raise InputError(f"pull_requests.csv line {i}: first_review is before opened")
    for i, row in enumerate(data.get("cycles", []), start=2):
        if row["end"] < row["start"]:
            raise InputError(f"cycles.csv line {i}: end is before start")


def load(data_dir: Path) -> tuple[dict, dict]:
    """Return (data, manifest). data maps source key to rows for each file present."""
    if not data_dir.is_dir():
        raise InputError(f"{data_dir}: not a folder")
    data = {}
    for key, spec in SPECS.items():
        path = data_dir / spec.filename
        if path.exists():
            data[key] = load_file(path, spec)
    manifest_path = data_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    if not isinstance(manifest, dict):
        raise InputError("manifest.json: expected an object")
    _check(data)
    return data, manifest
