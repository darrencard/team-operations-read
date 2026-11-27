"""Run a Team Operations read from a folder of exports.

    python3 scripts/read.py --data DIR --as-of YYYY-MM-DD [--window-days 90] [--company NAME] [--decides WHO] [--out run] [--stem read]

Writes, in --out: <stem>.json (every figure, finding and bound), <stem>.md (the read to show the user) and
<stem>.html (the same read as one self-contained page in the Leader Report style). Nothing in the output
depends on the clock or the machine, so the same inputs give the same bytes.
Exit code 2 on bad input, with the file, line and column named.

The read is about a team, not a bet. It writes no key into any Landing Loop record (landing/<bet>.json)
and never opens one.
"""

from __future__ import annotations

import sys

# Check the interpreter before importing anything that needs 3.11 (datetime.UTC, for one).
if sys.version_info < (3, 11):  # noqa: UP036
    sys.exit("team-operations-read needs Python 3.11 or later; try python3.12")

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from framework import FUNCTIONS  # noqa: E402
from inputs import InputError, load  # noqa: E402
from metrics import compute  # noqa: E402
from render_html import LIMITS, answer, page, summary  # noqa: E402
from rules import describe, read_all  # noqa: E402

VERSION = "0.3.0"
RECHECK_DAYS = 30


def cell(text: object) -> str:
    """Escape text from an export for a markdown table cell. Source text is data, never markup."""
    s = str(text).replace("\\", "\\\\").replace("|", "\\|").replace("\r", " ").replace("\n", " ")
    for ch in "<>`*_[]":
        s = s.replace(ch, "\\" + ch)
    return s


def _recheck(doc: dict, sh: dict) -> str:
    f = doc["figures"].get(sh["recheck_figure"]) if sh["recheck_figure"] else None
    what = f"{cell(f['label'])}, now {f['display']}" if f else "the figures behind it"
    return f"**Re-check:** {what}. Run this read again on {doc['recheck_on']} with the same window to see whether it moved."


def build(data_dir: Path, as_of: date, window_days: int, company: str | None, decides: str | None = None) -> dict:
    data, manifest = load(data_dir)
    m = compute(data, as_of, window_days)
    r = read_all(m["figures"])
    illustrative = bool(manifest.get("illustrative"))
    systems = manifest.get("systems") if isinstance(manifest.get("systems"), dict) else {}
    return {
        "skill": "team-operations-read",
        "version": VERSION,
        "company": company or manifest.get("company") or "the team",
        "illustrative": illustrative,
        "decides": decides or manifest.get("decides") or None,
        "as_of": as_of.isoformat(),
        "window": m["window"],
        "sources": sorted(k for k in data),
        "systems": {str(k): str(v) for k, v in sorted(systems.items())},
        "recheck_on": (as_of + timedelta(days=RECHECK_DAYS)).isoformat(),
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
        f"**{answer(doc)}**",
        "",
        *[f"- {x}" for x in summary(doc)],
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
    sh = doc["start_here"]
    if not sh:
        lines += [
            "**Start here:** no dimension is bounded yet: the data is below every rule's minimum sample or inside every threshold. "
            "The quickest addition is squads.csv (one row per squad with its roles), then items.csv from your tracker. See references/inputs.md.",
            "",
        ]
    else:
        lines += [
            f"**Start here:** {sh['name']}. {cell(sh['next_step'])}",
            "",
            _recheck(doc, sh),
            "",
        ]
        if doc["decides"]:
            lines += [f"**Decides:** {cell(doc['decides'])}.", ""]

    lines += ["| Dimension | Function | Read | Next step |", "|---|---|---|---|"]
    for d in read:
        lines.append(f"| {d['name']} | {d['function']} | {describe(d)} | {cell(d['next_step'])} |")
    lines.append("")

    for d in read:
        lines += [f"## {d['name']}: {describe(d)}", "", f"*{d['question']}*", ""]
        for f in d["findings"]:
            mark = "" if f["bound"] else (" (context, not scored)" if f.get("context") else " (not scored)")
            lines.append(f"- {cell(f['says'])}{mark} [{f['rule']}]")
        if d["survey"]:
            lines.append(f"- {d['survey']['says']}")
        if d["survey_disagrees"]:
            lines.append(f"- {d['survey_disagrees']}")
        lines += ["", f"**Next step:** {d['next_step']}", ""]

    lines += [
        "## How to use this read",
        "",
        *[f"- {x}" for x in LIMITS],
        "",
    ]

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
        "| Figure | Value | Source | Window | As of | Rows | Method |",
        "|---|---|---|---|---|---|---|",
    ]
    for f in figs.values():
        w = f"{f['window']['from']} to {f['window']['to']}"
        lines.append(f"| {cell(f['label'])}{tag} | {f['display']} | {f['source']} | {w} | {f['as_of']} | {f['n']} | {f['method']} |")
    lines.append("")
    if doc["systems"]:
        lines += ["Where each file came from: " + "; ".join(f"{cell(k)}, {cell(v)}" for k, v in doc["systems"].items()) + ".", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Score how a product team works against Dacard's Team Operations framework.")
    ap.add_argument("--data", required=True, type=Path, help="folder of exports (see references/inputs.md)")
    ap.add_argument("--as-of", required=True, help="last day of the window, YYYY-MM-DD")
    ap.add_argument("--window-days", type=int, default=90)
    ap.add_argument("--company")
    ap.add_argument("--decides", help="who decides the start-here step, one role from the org chart, such as 'Head of Product, Quoting squad'")
    ap.add_argument("--out", type=Path, default=Path("run"))
    ap.add_argument("--stem", default="read", help="file name for the three outputs, without the extension (default: read)")
    a = ap.parse_args(argv)
    try:
        as_of = date.fromisoformat(a.as_of)
        if not 14 <= a.window_days <= 365:
            raise InputError("--window-days must be 14 to 365")
        if not a.stem or "/" in a.stem or "\\" in a.stem or a.stem.startswith("."):
            raise InputError("--stem must be a plain file name, such as read")
        doc = build(a.data, as_of, a.window_days, a.company, a.decides)
    except (InputError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    a.out.mkdir(parents=True, exist_ok=True)
    paths = {ext: a.out / f"{a.stem}.{ext}" for ext in ("json", "md", "html")}
    paths["json"].write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    paths["md"].write_text(render(doc), encoding="utf-8")
    paths["html"].write_text(page(doc), encoding="utf-8")
    n = sum(1 for d in doc["dimensions"] if d["read"] != "not_read")
    print(f"Read {n} of 27 dimensions. Wrote {paths['html']}, {paths['md']} and {paths['json']}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
