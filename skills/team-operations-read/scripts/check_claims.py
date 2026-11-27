"""Check prose about a read against read.json. Blocks overclaims before the user sees them.

    python3 scripts/check_claims.py --read run/read.json --draft draft.md

Errors (exit 1):
  - a stage for a dimension the read did not score, or outside its bounds, or stated as a single
    stage when the read only supports a range
  - an overall Team Operations stage or level when the read withholds one
  - a figure (a percentage, days, hours or a score of 5) that is not in the evidence ledger
  - shorthand for the framework (TO, F1, F2, F3), em dashes, or banned words
  - landed, watch or stalled: those are a bet's status words, and only did-it-land sets them. A team read
    speaks in stages
"""

from __future__ import annotations

import sys

# Check the interpreter before importing anything that needs 3.11 (datetime.UTC, for one).
if sys.version_info < (3, 11):  # noqa: UP036
    sys.exit("team-operations-read needs Python 3.11 or later; try python3.12")

import argparse
import json
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from framework import DIMENSIONS, STAGE_NAMES  # noqa: E402

EM_DASH = chr(0x2014)
BANNED = ["ai-powered", "unlock", "supercharge", "seamless", "robust", "get started", "revolutionizing", "revolutionising", "disrupting"]
RANGE_WORDS = re.compile(r"\b(or above|or below|at least|at most|to|between|range|no higher|no lower)\b", re.I)
STAGE_RE = re.compile(r"\bstage\s+([1-5])\b", re.I)
STAGE_NAME_RE = re.compile(r"\b(" + "|".join(STAGE_NAMES.values()) + r")\b")
FIGURE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(%|percent\b|days?\b|hours?\b|h\b|of 5\b|per person\b)", re.I)
SHORTHAND_RE = re.compile(r"\b(TO|F1|F2|F3)\b")
COMPARISON_RE = re.compile(r"\b(more than|less than|under|over|above|below|at least|at most|within|between|and|or more)\s*$", re.I)
# "rubric Stage 3" cites the rubric; "Show Stage 4" names a target. Neither claims a stage.
CITATION_RE = re.compile(r"\b(rubric|show|to show)\s+stage\s+[1-5]\b", re.I)
STATUS_RE = re.compile(r"\b(landed|watch|stalled)\b", re.I)
OVERALL_RE = re.compile(r"\b(overall|team operations (stage|level|score)|maturity (stage|level)|the team is (at|in) stage)\b", re.I)


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def _unit(u: str) -> str:
    u = u.lower()
    if u in ("%", "percent"):
        return "%"
    if u.startswith("day"):
        return "days"
    if u.startswith("hour") or u == "h":
        return "hours"
    return u


def _found(texts: list[str]) -> set[tuple[float, str]]:
    return {(float(m.group(1)), _unit(m.group(2))) for t in texts for m in FIGURE_RE.finditer(t)}


def _allowed_figures(read: dict) -> tuple[set, set]:
    """Figures the scripts wrote. Ledger values and the window may appear anywhere; rule thresholds
    (such as "more than 40%") only after a comparison word, so a threshold never reads as a result."""
    ledger = _found([f["display"] for f in read["figures"].values()] + [f"{read['window']['days']} days"])
    rule_text = [t for d in read["dimensions"] for t in [f["says"] for f in d["findings"]] + [d["next_step"]]]
    return ledger, _found(rule_text)


def check(read: dict, draft: str) -> list[str]:
    errors = []
    dims = {d["name"].lower(): d for d in read["dimensions"]}
    names = sorted((n for _, n, _, _ in DIMENSIONS), key=len, reverse=True)
    ledger, thresholds = _allowed_figures(read)
    withheld = not read["overall"]["claimed"]

    if EM_DASH in draft:
        errors.append("Em dash found. Use a comma, period or parentheses.")
    low = draft.lower()
    for w in BANNED:
        if w in low:
            errors.append(f"Banned word: {w!r}.")
    for m in STATUS_RE.finditer(draft):
        errors.append(f"Status word {m.group(1)!r}: landed, watch and stalled are a bet's status, set only by did-it-land. Describe the team in stages.")
    for m in SHORTHAND_RE.finditer(draft):
        errors.append(f"Shorthand {m.group(1)!r}: write the framework's full name, Team Operations.")

    for s in _sentences(draft):
        cited = CITATION_RE.sub("", s)
        mentioned = [n for n in names if n.lower() in s.lower()]
        stages = [int(x) for x in STAGE_RE.findall(cited)]
        if stages and mentioned:
            d = dims[mentioned[0].lower()]
            for st in stages:
                if d["read"] in ("not_read", "conflict"):
                    errors.append(f"{d['name']} has no stage in this read ({d['read'].replace('_', ' ')}), but the draft says Stage {st}: {s!r}")
                elif not d["floor"] <= st <= d["ceiling"]:
                    errors.append(f"{d['name']} is bounded to Stage {d['floor']} to {d['ceiling']}, but the draft says Stage {st}: {s!r}")
                elif d["read"] == "range" and not RANGE_WORDS.search(s):
                    errors.append(f"{d['name']} only supports a range ({d['floor']} to {d['ceiling']}); the draft states one stage: {s!r}")
        elif withheld and (stages or STAGE_NAME_RE.search(cited)) and re.search(r"\b(stage|level)\b", cited, re.I) and (OVERALL_RE.search(s) or not mentioned):
            errors.append(f"The read withholds an overall stage, but the draft claims one: {s!r}")

        for m in FIGURE_RE.finditer(s):
            key = (float(m.group(1)), _unit(m.group(2)))
            if key not in ledger and not (key in thresholds and COMPARISON_RE.search(s[: m.start()])):
                errors.append(f"Figure {m.group(0)!r} is not in the evidence ledger: {s!r}")
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Check prose about a Team Operations read for overclaims.")
    ap.add_argument("--read", required=True, type=Path)
    ap.add_argument("--draft", required=True, type=Path)
    a = ap.parse_args(argv)
    read = json.loads(a.read.read_text(encoding="utf-8"))
    errors = check(read, a.draft.read_text(encoding="utf-8"))
    for e in errors:
        print(f"error: {e}")
    print(f"{len(errors)} error(s).")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
