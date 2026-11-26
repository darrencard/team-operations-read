"""Run a Team Operations read from a folder of exports.

    python3 scripts/read.py --data DIR --as-of YYYY-MM-DD [--window-days 90] [--company NAME] [--out run]

Writes run/read.json (every figure, finding and bound) and run/read.md (the read to show the user).
Exit code 2 on bad input, with the file, line and column named.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from framework import FUNCTIONS  # noqa: E402
from inputs import InputError, load  # noqa: E402
from metrics import compute  # noqa: E402
from rules import describe, read_all  # noqa: E402

VERSION = "0.1.0"


def cell(text: object) -> str:
    """Escape text from an export for a markdown table cell. Source text is data, never markup."""
    s = str(text).replace("\\", "\\\\").replace("|", "\\|").replace("\r", " ").replace("\n", " ")
    for ch in "<>`*_[]":
        s = s.replace(ch, "\\" + ch)
    return s


def build(data_dir: Path, as_of: date, window_days: int, company: str | None) -> dict:
    data, manifest = load(data_dir)
    m = compute(data, as_of, window_days)
    r = read_all(m["figures"])
    illustrative = bool(manifest.get("illustrative"))
    return {
        "skill": "team-operations-read",
        "version": VERSION,
        "company": company or manifest.get("company") or "the team",
        "illustrative": illustrative,
        "as_of": as_of.isoformat(),
        "window": m["window"],
        "sources": sorted(k for k in data),
        "figures": m["figures"],
        **r,
    }


def render(doc: dict) -> str:
    tag = " (Illustrative)" if doc["illustrative"] else ""
    figs = doc["figures"]
    dims = doc["dimensions"]
    read = [d for d in dims if d["read"] != "not_read"]
    lines = [
        f"# Team Operations read: {cell(doc['company'])}{tag}",
        "",
        f"Window {doc['window']['start']} to {doc['window']['end']} ({doc['window']['days']} days). "
        f"{len(read)} of 27 dimensions read from {', '.join(doc['sources']) or 'no exports'}.",
        "",
    ]
    if doc["illustrative"]:
        lines += ["> Illustrative: every figure below comes from invented sample data, not a real company.", ""]
    ov = doc["overall"]
    if ov["claimed"]:
        lines += [f"**Overall:** Stage {ov['stage']} ({ov['stage_name']}), {ov['total']} of 135.", ""]
    else:
        lines += [f"**Overall:** no stage claimed. {ov['why']}", ""]

    lines += ["| Dimension | Function | Read | Next step |", "|---|---|---|---|"]
    for d in read:
        lines.append(f"| {d['name']} | {d['function']} | {describe(d)} | {cell(d['next_step'])} |")
    lines.append("")

    for d in read:
        lines += [f"## {d['name']}: {describe(d)}", "", f"*{d['question']}*", ""]
        for f in d["findings"]:
            mark = "" if f["bound"] else " (not scored)"
            lines.append(f"- {cell(f['says'])}{mark} [{f['rule']}]")
        if d["survey"]:
            lines.append(f"- {d['survey']['says']}")
        if d["survey_disagrees"]:
            lines.append(f"- {d['survey_disagrees']}")
        lines += ["", f"**Next step:** {d['next_step']}", ""]

    lines += ["## Not read", ""]
    for fn in FUNCTIONS:
        names = [d for d in dims if d["read"] == "not_read" and d["function"] == fn]
        steps: dict[str, list[dict]] = {}
        for d in names:
            steps.setdefault(d["next_step"], []).append(d)
        for step, group in steps.items():
            views = " ".join(f"{d['name']}: {d['survey']['says']}" for d in group if d["survey"] and d["survey"]["shown"])
            lines.append(f"- **{fn}:** {', '.join(d['name'] for d in group)}. {cell(step)}" + (f" {views}" if views else ""))
    lines.append("")

    lines += [
        "## Evidence ledger",
        "",
        "Every figure above, with its source. Computed by scripts/metrics.py; nothing is estimated.",
        "",
        "| Figure | Value | Source | Rows | Method |",
        "|---|---|---|---|---|",
    ]
    for f in figs.values():
        lines.append(f"| {f['label']}{tag} | {f['display']} | {f['source']} | {f['n']} | {f['method']} |")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Score how a product team works against Dacard's Team Operations framework.")
    ap.add_argument("--data", required=True, type=Path, help="folder of exports (see references/inputs.md)")
    ap.add_argument("--as-of", required=True, help="last day of the window, YYYY-MM-DD")
    ap.add_argument("--window-days", type=int, default=90)
    ap.add_argument("--company")
    ap.add_argument("--out", type=Path, default=Path("run"))
    a = ap.parse_args(argv)
    try:
        as_of = date.fromisoformat(a.as_of)
        if not 14 <= a.window_days <= 365:
            raise InputError("--window-days must be 14 to 365")
        doc = build(a.data, as_of, a.window_days, a.company)
    except (InputError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "read.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    (a.out / "read.md").write_text(render(doc), encoding="utf-8")
    n = sum(1 for d in doc["dimensions"] if d["read"] != "not_read")
    print(f"Read {n} of 27 dimensions. Wrote {a.out / 'read.md'} and {a.out / 'read.json'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
