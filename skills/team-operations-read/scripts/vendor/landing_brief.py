#!/usr/bin/env python3
"""Read a landing brief from a Linear project description, and draft the project update it implies.

Usage:
  python3 scripts/landing_brief.py check project.md          # parse the brief, or say what is wrong with it
  python3 scripts/landing_brief.py update project.md --current 46 --prior 41 --as-of 2026-11-23
                                                           # draft a project update: landed, watch or stalled
  python3 scripts/landing_brief.py update project.json --current 46 --json
                                                           # the same, as JSON with the Linear health value

The input is a Markdown file holding the project description, or the JSON Linear returns for one
project (its description or content field is read). The brief is the section under a heading named
"Landing brief", written as "Key: value" lines (see assets/project-template.md):

  the problem         Problem
  definition of good  Metric, Bar, Better (higher or lower), By (YYYY-MM-DD)
  the non-goals       Non-goals
  the cost budget     Tokens per task, Price per token (two lines)
  the line            The line: "fixed code" or "model call", then why
  and who decides     Decides the next step

A brief with any missing, unknown, repeated or unreadable part is refused whole, with every problem listed.

The status rule is the same as the Product & Technology Leader Report's (draft.status_for):
  landed   the bar is met
  watch    not there, moving the right way; or no prior value yet
  stalled  not there, and flat or moving the wrong way

This script reads a file and prints text. It makes no network calls; posting to Linear is the agent's
job, through the Linear connector, after the person confirms. This file is kept identical in the
landing-brief and product-engineering-update skills, and the tests check that.

Standard library only. Runs on Python 3.9 or later.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# A project description is a few pages at most. Anything larger is not one.
MAX_CHARS = 100_000
HEADING = re.compile(r"^(#{1,6})\s*landing brief\s*#*\s*$", re.I)
ANY_HEADING = re.compile(r"^(#{1,6})\s")
LINE = re.compile(r"^\s*(?:[-*+]\s+)?(?:\*\*|__)?([A-Za-z][A-Za-z \-]*?)\s*(?::\s*(?:\*\*|__)|(?:\*\*|__)\s*:|:)\s*(.*?)\s*$")
NUMBER = re.compile(r"^\s*(\$|£|€)?\s*(\d[\d,]*(?:\.\d+)?|\.\d+)\s*([A-Za-z%]{0,12})\s*$")
LINES_ALLOWED = ("fixed code", "model call")
# Each key a brief may hold, by the spellings a person writes it in.
KEYS = {
    "problem": "problem",
    "the problem": "problem",
    "metric": "metric",
    "bar": "bar",
    "better": "better",
    "by": "by",
    "non-goals": "non_goals",
    "non goals": "non_goals",
    "nongoals": "non_goals",
    "tokens per task": "tokens_per_task",
    "price per token": "price_per_token",
    "the line": "line",
    "line": "line",
    "decides the next step": "decides",
    "decides": "decides",
}
REQUIRED = ("problem", "metric", "bar", "better", "by", "non_goals", "tokens_per_task", "price_per_token", "line", "decides")
# Linear's project health for each status word, for the agent's save_status_update call.
HEALTH = {"landed": "onTrack", "watch": "atRisk", "stalled": "offTrack"}


class BriefError(ValueError):
    """A brief that cannot be used. The message lists every problem found."""


@dataclass(frozen=True)
class Brief:
    problem: str
    metric: str
    bar_text: str
    bar: float
    prefix: str
    unit: str
    higher_is_better: bool
    by: str
    non_goals: str
    tokens_per_task: float | None
    price_per_token: float | None
    line: str
    line_note: str
    decides: str

    def show(self, value: float) -> str:
        """A value in the bar's own form: "$0.33", "46%", "38h"."""
        return f"{self.prefix}{value:,.10g}{self.unit}"


def status_for(value: float, prior: float | None, target: float | None, higher_is_better: bool) -> str:
    """landed: the target is met. watch: moving the right way, not there yet. stalled: flat or moving the wrong way."""
    if target is None:
        return "watch"
    met = value >= target if higher_is_better else value <= target
    if met:
        return "landed"
    if prior is None:
        return "watch"
    improving = value > prior if higher_is_better else value < prior
    return "watch" if improving else "stalled"


def number(text: str) -> tuple[str, float, str] | None:
    """(prefix, value, unit) for "50%", "$0.000003", "12,000" or "40h"; None when it is not one number."""
    found = NUMBER.match(text)
    if not found:
        return None
    return found.group(1) or "", float(found.group(2).replace(",", "")), found.group(3) or ""


def section(text: str) -> list[str]:
    """The lines under the one "Landing brief" heading, up to the next heading of the same or a higher level."""
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if HEADING.match(line.strip())]
    if not starts:
        raise BriefError('there is no "Landing brief" heading. Paste the block from assets/project-template.md into the project description.')
    if len(starts) > 1:
        raise BriefError(f'there are {len(starts)} "Landing brief" headings. Keep one.')
    level = len(HEADING.match(lines[starts[0]].strip()).group(1))
    out = []
    for line in lines[starts[0] + 1 :]:
        head = ANY_HEADING.match(line.strip())
        if head and len(head.group(1)) <= level:
            break
        out.append(line)
    return out


def parse(text: str) -> Brief:
    """The brief in a project description. Refused whole, with every problem listed, if any part is wrong."""
    if not isinstance(text, str) or not text.strip():
        raise BriefError("the project description is empty.")
    if len(text) > MAX_CHARS:
        raise BriefError(f"the description is over {MAX_CHARS:,} characters, so it is not a project description.")
    found: dict[str, str] = {}
    problems: list[str] = []
    for raw in section(text):
        line = raw.strip()
        if not line or re.fullmatch(r"[-*_]{3,}", line) or ANY_HEADING.match(line):
            continue
        m = LINE.match(line)
        key = KEYS.get(m.group(1).strip().lower()) if m else None
        if not m or not key:
            problems.append(f'"{line[:80]}" is not one of the brief\'s parts. Write it as "Key: value" with a key from the template.')
            continue
        if key in found:
            problems.append(f"{m.group(1).strip()} is given twice. Keep one.")
            continue
        found[key] = m.group(2).strip().strip("*_").strip()
    for key in REQUIRED:
        if not found.get(key):
            problems.append(f"{key.replace('_', ' ')} is missing or empty.")
    if problems:
        raise BriefError("the landing brief cannot be used:\n  " + "\n  ".join(problems))

    bar = number(found["bar"])
    if bar is None:
        problems.append(f'bar "{found["bar"]}" is not one number, such as 50%, $0.30 or 40h.')
    better = found["better"].lower()
    if better not in ("higher", "lower"):
        problems.append(f'better is "{found["better"]}". Write higher or lower.')
    try:
        datetime.date.fromisoformat(found["by"])
    except ValueError:
        problems.append(f'by is "{found["by"]}". Write the date as YYYY-MM-DD.')
    kind = next((k for k in LINES_ALLOWED if found["line"].lower().startswith(k)), None)
    if kind is None:
        problems.append(f'the line is "{found["line"][:60]}". Start it with "fixed code" or "model call".')
    budget: dict[str, float | None] = {}
    for key in ("tokens_per_task", "price_per_token"):
        value = found[key]
        if value.lower() == "none":
            if kind != "fixed code":
                problems.append(f"{key.replace('_', ' ')} is none, but the line is a model call. State the budget.")
            budget[key] = None
            continue
        parsed = number(value)
        if parsed is None:
            problems.append(f'{key.replace("_", " ")} is "{value}". Write one number, or none when the line is fixed code.')
        budget[key] = parsed[1] if parsed else None
    if problems:
        raise BriefError("the landing brief cannot be used:\n  " + "\n  ".join(problems))
    assert bar is not None and kind is not None  # noqa: S101  (narrowed by the checks above)
    note = found["line"][len(kind) :].lstrip(" .:;,").strip()
    return Brief(
        problem=found["problem"],
        metric=found["metric"],
        bar_text=found["bar"],
        bar=bar[1],
        prefix=bar[0],
        unit=bar[2],
        higher_is_better=better == "higher",
        by=found["by"],
        non_goals=found["non_goals"],
        tokens_per_task=budget["tokens_per_task"],
        price_per_token=budget["price_per_token"],
        line=kind,
        line_note=note,
        decides=found["decides"],
    )


def description_of(path: Path) -> str:
    """A project description from a Markdown file, or from the JSON Linear returns for a project."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise BriefError(f"cannot read {path} ({e}). Save the description as UTF-8 Markdown or the project as JSON.") from None
    if path.suffix.lower() != ".json":
        return text
    try:
        data: Any = json.loads(text)
    except json.JSONDecodeError as e:
        raise BriefError(f"{path} is not valid JSON ({e.msg}, line {e.lineno}).") from None
    project = data.get("project", data) if isinstance(data, dict) else None
    if not isinstance(project, dict):
        raise BriefError(f"{path} holds no project object.")
    parts = [project.get(k) for k in ("content", "description") if isinstance(project.get(k), str)]
    with_brief = [p for p in parts if any(HEADING.match(x.strip()) for x in p.splitlines())]
    if not parts:
        raise BriefError(f"{path} has no description or content field.")
    return (with_brief or parts)[0]


def draft_update(brief: Brief, current: float, prior: float | None, as_of: str | None = None) -> dict[str, str]:
    """The project update a person reviews before it is posted: the status word, the number against the bar and
    date, and who decides the next step. It says nothing about cause."""
    status = status_for(current, prior, brief.bar, brief.higher_is_better)
    against = f"{brief.metric} is {brief.show(current)}, against a bar of {brief.bar_text} by {brief.by}."
    was = f" It was {brief.show(prior)} at the last reading." if prior is not None else ""
    if status == "landed":
        why = "The bar is met."
    elif prior is None:
        why = "Not there yet, and there is no earlier reading to compare, so it is too early to call."
    elif status == "watch":
        why = "Moving the right way, not there yet."
    elif current == prior:
        why = "Not there, and flat since the last reading."
    else:
        why = "Not there, and moving the wrong way."
    late = ""
    if as_of and status != "landed" and datetime.date.fromisoformat(as_of) > datetime.date.fromisoformat(brief.by):
        late = f" The date, {brief.by}, has passed."
    body = "\n\n".join(
        [
            f"**{status}**. {against}{was}",
            f"{why}{late} A metric moving is not proof that this project moved it.",
            f"Who decides the next step: {brief.decides}.",
        ]
    )
    return {"status": status, "health": HEALTH[status], "body": body}


def main() -> int:
    ap = argparse.ArgumentParser(description="Read a landing brief and draft the project update it implies.")
    ap.add_argument("command", choices=["check", "update"])
    ap.add_argument("path", help="a Markdown file with the project description, or Linear's JSON for the project")
    ap.add_argument("--current", type=float, help="update: the metric's value now, from the team's own data")
    ap.add_argument("--prior", type=float, help="update: the value at the last reading; leave it out when there is none")
    ap.add_argument("--as-of", help="update: today's date, YYYY-MM-DD, to say when the date has passed")
    ap.add_argument("--json", action="store_true", help="update: print status, Linear health and body as JSON")
    args = ap.parse_args()
    try:
        brief = parse(description_of(Path(args.path)))
        if args.as_of:
            datetime.date.fromisoformat(args.as_of)
    except BriefError as e:
        raise SystemExit(f"landing_brief: {e}") from None
    except ValueError:
        raise SystemExit(f"landing_brief: --as-of is {args.as_of!r}. Write it as YYYY-MM-DD.") from None
    if args.command == "check":
        print(json.dumps(asdict(brief), indent=2, ensure_ascii=False))
        print("landing_brief: the brief is complete.", file=sys.stderr)
        return 0
    if args.current is None:
        raise SystemExit("landing_brief: update needs --current, the metric's value now. Never estimate it.")
    update = draft_update(brief, args.current, args.prior, args.as_of)
    print(json.dumps(update, indent=2, ensure_ascii=False) if args.json else update["body"])
    print("landing_brief: this is a draft. Show it to the person; post it only after they confirm.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
