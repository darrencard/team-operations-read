"""Turn a GitHub pull request export into pull_requests.csv.

Make the export with the GitHub CLI, once per repository:

    gh pr list --repo OWNER/NAME --state all --limit 1000 \\
      --json number,createdAt,mergedAt,isDraft,author,reviews,labels > prs.json

Then:

    python3 scripts/from_github.py --input prs.json --out <data folder> [--squad NAME | --squad-label-prefix squad:]

Rules, so the figures mean what they say:
  - pull requests opened by bots (author.is_bot, or a login ending in [bot]) are left out
  - drafts are left out
  - first_review is the earliest review by anyone other than the author
  - approvals counts distinct non-author reviewers whose latest review is APPROVED
Several repositories can go into one file: pass --input more than once.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

HEADER = ["id", "squad", "opened", "first_review", "merged", "approvals", "author"]


def _is_bot(author: dict | None) -> bool:
    if not author:
        return True
    return bool(author.get("is_bot")) or str(author.get("login", "")).endswith("[bot]")


def _squad(pr: dict, fixed: str | None, prefix: str | None) -> str:
    if fixed:
        return fixed
    if prefix:
        for label in pr.get("labels") or []:
            name = str(label.get("name", ""))
            if name.startswith(prefix):
                return name[len(prefix) :].strip()
    return ""


def convert(prs: list[dict], source: str, squad: str | None = None, prefix: str | None = None) -> tuple[list[list], dict]:
    rows, skipped = [], {"bot": 0, "draft": 0}
    for pr in prs:
        author = pr.get("author")
        if _is_bot(author):
            skipped["bot"] += 1
            continue
        if pr.get("isDraft"):
            skipped["draft"] += 1
            continue
        login = author.get("login")
        others = [r for r in pr.get("reviews") or [] if r.get("submittedAt") and (r.get("author") or {}).get("login") not in (None, login)]
        first = min((r["submittedAt"] for r in others), default="")
        latest: dict[str, str] = {}
        for r in sorted(others, key=lambda r: r["submittedAt"]):
            latest[r["author"]["login"]] = r.get("state", "")
        approvals = sum(1 for state in latest.values() if state == "APPROVED")
        rows.append([f"{source}#{pr['number']}", _squad(pr, squad, prefix), pr["createdAt"], first, pr.get("mergedAt") or "", approvals, login])
    return rows, skipped


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Convert gh pr list JSON to pull_requests.csv.")
    ap.add_argument("--input", required=True, action="append", type=Path, help="gh pr list --json output; repeat for several repositories")
    ap.add_argument("--out", required=True, type=Path, help="data folder; pull_requests.csv is written here")
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--squad", help="one squad name for every pull request")
    group.add_argument("--squad-label-prefix", help="take the squad from a label with this prefix, such as squad:")
    a = ap.parse_args(argv)
    rows, skipped = [], {"bot": 0, "draft": 0}
    for path in a.input:
        try:
            prs = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(prs, list):
                raise ValueError("expected a JSON list")
            r, s = convert(prs, path.stem, a.squad, a.squad_label_prefix)
        except (ValueError, KeyError) as e:
            print(f"error: {path}: {e}", file=sys.stderr)
            return 2
        rows += r
        skipped = {k: skipped[k] + s[k] for k in skipped}
    a.out.mkdir(parents=True, exist_ok=True)
    with (a.out / "pull_requests.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(HEADER)
        w.writerows(rows)
    print(f"Wrote {len(rows)} pull requests to {a.out / 'pull_requests.csv'}. Left out {skipped['bot']} by bots and {skipped['draft']} drafts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
