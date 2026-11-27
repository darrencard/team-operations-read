#!/usr/bin/env python3
"""Turn raw GitHub exports into the source_control source, with no retyping.

Usage:
  python3 scripts/from_github.py --prs prs.json --deployments deployments.json --repo owner/name --run run

Inputs are the JSON GitHub already gives you, saved to a file as it stands:
  --prs          merged pull requests, from `gh pr list --state merged --json number,createdAt,mergedAt,reviews,labels,author`
                 or the same fields from a GitHub connector
  --agent-labels optional: labels that mark a pull request as written by an agent, comma separated
  --agent-authors optional: logins that mark it, such as an agent's bot account, comma separated
  --deployments  optional: deployments, from `gh api repos/OWNER/NAME/deployments --paginate`

It writes run/data/source_control.json, the same file collect.py writes, so
compute_metrics.py runs next as usual.

What it derives, in code:
  review_hours   hours from a pull request opening to its first review
  reworked       whether any review asked for changes
  agent_authored whether a label or author you named marks it as written by an agent;
                 empty when you name none, so nothing is guessed
  deploys        one row per deployment to the named environment

What it leaves empty on purpose: `failed`. GitHub can say a deployment did
not build. It cannot say a change failed in production, and a change failure
rate built from build failures would overclaim. Collect incident data for that.

This script reads files and writes a file. It makes no network calls; the
export commands above are run by you or by the session's GitHub connector.

Standard library only. Runs on Python 3.9 or later.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import collect  # noqa: E402  (a sibling script, found through the path above)

Json = dict[str, Any]

# GitHub's review states. Only this one means the author was asked to redo work.
CHANGES_REQUESTED = "CHANGES_REQUESTED"


def read_arrays(path: Path) -> list[Json]:
    """Read one JSON array, or several back to back, which is what `gh api --paginate` writes."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise SystemExit(f"from_github: cannot read {path} ({e}). Save the export as a UTF-8 JSON file and run this again.") from None
    decoder = json.JSONDecoder()
    rows: list[Json] = []
    position = 0
    while position < len(text):
        while position < len(text) and text[position].isspace():
            position += 1
        if position >= len(text):
            break
        try:
            value, position = decoder.raw_decode(text, position)
        except json.JSONDecodeError as e:
            raise SystemExit(f"from_github: {path} is not valid JSON ({e.msg} at character {e.pos}). Save the export again without editing it.") from None
        if not isinstance(value, list) or not all(isinstance(x, dict) for x in value):
            raise SystemExit(f"from_github: {path} must hold a list of objects, as GitHub returns it.")
        rows.extend(value)
    return rows


def stamp(value: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))


def field(row: Json, *names: str) -> Any:
    """GitHub's GraphQL and REST APIs name the same field differently (createdAt, created_at)."""
    return next((row[n] for n in names if row.get(n) is not None), None)


def agent_mark(pr: Json, labels: set[str], authors: set[str]) -> str:
    """yes or no when the person named what marks agent work; empty when they named nothing, so the share stays Unknown."""
    if not labels and not authors:
        return ""
    names = {(x.get("name") if isinstance(x, dict) else str(x)).lower() for x in pr.get("labels") or []}
    author = pr.get("author") or pr.get("user") or {}
    login = ((author.get("login") or "") if isinstance(author, dict) else str(author)).lower()
    return "yes" if names & labels or login in authors else "no"


def pull_request_rows(prs: list[Json], labels: set[str] | None = None, authors: set[str] | None = None) -> list[Json]:
    labels, authors = labels or set(), authors or set()
    rows: list[Json] = []
    for pr in prs:
        opened, merged = field(pr, "createdAt", "created_at"), field(pr, "mergedAt", "merged_at")
        if not opened or not merged:
            continue  # not merged, so it is not delivered work
        reviews = [r for r in (pr.get("reviews") or []) if field(r, "submittedAt", "submitted_at")]
        first = min((stamp(field(r, "submittedAt", "submitted_at")) for r in reviews), default=None)
        review_hours = round((first - stamp(opened)).total_seconds() / 3600, 2) if first else ""
        reworked = ("yes" if any(r.get("state") == CHANGES_REQUESTED for r in reviews) else "no") if reviews else ""
        rows.append(
            {
                "kind": "pull_request",
                "id": f"pr-{field(pr, 'number', 'id')}",
                "opened_at": opened,
                "merged_at": merged,
                "review_hours": review_hours,
                "deployed_at": "",
                "failed": "",
                "reworked": reworked,
                "agent_authored": agent_mark(pr, labels, authors),
            }
        )
    return rows


def deployment_rows(deployments: list[Json], environment: str) -> list[Json]:
    wanted = environment.lower()
    return [
        {
            "kind": "deploy",
            "id": f"deploy-{d.get('id')}",
            "opened_at": "",
            "merged_at": "",
            "review_hours": "",
            "deployed_at": field(d, "created_at", "createdAt"),
            "failed": "",
            "reworked": "",
        }
        for d in deployments
        if str(d.get("environment", "")).lower() == wanted and field(d, "created_at", "createdAt")
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description="Turn raw GitHub exports into the source_control source.")
    ap.add_argument("--prs", required=True, help="merged pull requests as JSON")
    ap.add_argument("--deployments", help="deployments as JSON (optional)")
    ap.add_argument("--environment", default="Production", help="the deployment environment that counts as a deploy (default: Production)")
    ap.add_argument("--repo", required=True, help="owner/name, for the ledger")
    ap.add_argument("--retrieved-at", help="YYYY-MM-DD; defaults to the pull request file's modified date")
    ap.add_argument("--agent-labels", default="", help="labels that mark a pull request as written by an agent, comma separated")
    ap.add_argument("--agent-authors", default="", help="logins that mark a pull request as written by an agent, comma separated")
    ap.add_argument("--run", default="run")
    args = ap.parse_args()

    def names(text: str) -> set[str]:
        return {x.strip().lower() for x in text.split(",") if x.strip()}

    prs_path = Path(args.prs)
    rows = pull_request_rows(read_arrays(prs_path), names(args.agent_labels), names(args.agent_authors))
    reviewed = sum(1 for r in rows if r["review_hours"] != "")
    deploys: list[Json] = []
    if args.deployments:
        deploys = deployment_rows(read_arrays(Path(args.deployments)), args.environment)
    if not rows and not deploys:
        raise SystemExit("from_github: found no merged pull requests and no deployments. Check the export, then run this again.")

    retrieved = collect.retrieved_date(args.retrieved_at, str(prs_path))
    query = "gh pr list --state merged --json number,createdAt,mergedAt,reviews,labels,author" + ("; gh api repos/.../deployments" if args.deployments else "")
    data = collect.collect("source_control", deploys + rows, f"GitHub ({args.repo})", query, retrieved, prs_path.name)
    out = Path(args.run) / "data" / "source_control.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    print(f"from_github: {len(rows)} merged pull requests ({reviewed} with a review) and {len(deploys)} deploys to {args.environment}, written to {out}")
    if rows and not reviewed:
        print("from_github: no pull request has a review, so there is no review time or rework rate. Speed will be held back until a quality metric exists.")
    marked = [r for r in rows if r["agent_authored"] == "yes"]
    if args.agent_labels or args.agent_authors:
        print(f"from_github: {len(marked)} of {len(rows)} merged pull requests are marked as written by an agent.")
    if not deploys:
        print("from_github: no deployments supplied, so there is no deploys per week.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
