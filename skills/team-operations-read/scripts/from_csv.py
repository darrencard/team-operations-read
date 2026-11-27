"""Map any tracker's CSV export (Linear, Jira, Shortcut, a spreadsheet) onto a file the read uses.

    python3 scripts/from_csv.py --input export.csv --target items --out <data folder> \\
      --map id=ID --map squad=Team --map assignee=Assignee --map created=Created \\
      --map started=Started --map completed=Completed --map type=Labels \\
      --type-values bug,feature,chore

--map TARGET=SOURCE names the export column for each target column (see references/inputs.md).
Optional target columns may be left unmapped; their figures are then not computed, never guessed.
--type-values picks the work type from a comma-separated cell (such as Labels): the first listed
value found wins, otherwise the type is "untyped". Dates are cut to YYYY-MM-DD; the read checks them.
The mapping is printed so the user can confirm it before the read runs.
"""

from __future__ import annotations

import sys

# Check the interpreter before importing anything that needs 3.11 (datetime.UTC, for one).
if sys.version_info < (3, 11):  # noqa: UP036
    sys.exit("team-operations-read needs Python 3.11 or later; try python3.12")

import argparse
import csv
from pathlib import Path

from inputs import SPECS, note_system


def _type(cell: str, values: list[str]) -> str:
    parts = [p.strip().lower() for p in cell.split(",")]
    for v in values:
        if v in parts:
            return v
    return "untyped"


def convert(rows: list[dict], target: str, mapping: dict[str, str], type_values: list[str] | None = None) -> tuple[list[str], list[list]]:
    spec = SPECS[target]
    allowed = set(spec.required) | set(spec.optional)
    unknown = sorted(set(mapping) - allowed)
    if unknown:
        raise ValueError(f"not a column of {spec.filename}: {', '.join(unknown)}")
    missing = [c for c in spec.required if c not in mapping]
    if missing:
        raise ValueError(f"{spec.filename} needs a mapping for: {', '.join(missing)}")
    header = list(spec.required) + [c for c in spec.optional if c in mapping]
    date_cols = set(spec.dates) | set(spec.optional_dates)
    out = []
    for row in rows:
        line = []
        for col in header:
            src = mapping[col]
            if src not in row:
                raise ValueError(f"export has no column {src!r} (mapped to {col})")
            v = (row[src] or "").strip()
            if col == "type" and type_values:
                v = _type(v, type_values)
            elif col in date_cols and v:
                v = v[:10]
            line.append(v)
        out.append(line)
    return header, out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Map a tracker CSV export onto a Team Operations read input file.")
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--target", required=True, choices=sorted(SPECS))
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--map", action="append", default=[], help="TARGET=SOURCE; repeat per column")
    ap.add_argument("--type-values", help="comma-separated work types to pick from the type cell, in priority order")
    a = ap.parse_args(argv)
    try:
        mapping = dict(m.split("=", 1) for m in a.map)
    except ValueError:
        print("error: each --map is TARGET=SOURCE", file=sys.stderr)
        return 2
    types = [t.strip().lower() for t in a.type_values.split(",")] if a.type_values else None
    with a.input.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    try:
        header, out = convert(rows, a.target, mapping, types)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    a.out.mkdir(parents=True, exist_ok=True)
    path = a.out / SPECS[a.target].filename
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(out)
    note_system(a.out, SPECS[a.target].filename, f"CSV export {a.input.name}")
    for col in header:
        print(f"  {col} <- {mapping[col]}")
    print(f"Wrote {len(out)} rows to {path}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
