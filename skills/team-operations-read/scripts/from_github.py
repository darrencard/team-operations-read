"""Turn a GitHub pull request export into pull_requests.csv.

Live first: export with the GitHub CLI or the session's GitHub connector and save the response as it stands.

    gh pr list --repo OWNER/NAME --state all --limit 1000 \\
      --json number,createdAt,mergedAt,isDraft,author,reviews,labels > prs.json

The REST shape works too (`gh api repos/OWNER/NAME/pulls --paginate`, with reviews), as several arrays back to
back. Reading the file and its field names is done by the Leader Report's own collector (scripts/vendor/
from_github.py, vendored unchanged); this script adds only what a Team Operations read needs. Then:

    python3 scripts/from_github.py --input prs.json --out <data folder> [--squad NAME | --squad-label-prefix squad:] [--repo OWNER/NAME]

Rules, so the figures mean what they say:
  - pull requests opened by bots (author.is_bot, a user of type Bot, or a login ending in [bot]) are left out
  - drafts are left out
  - first_review is the earliest review by anyone other than the author
  - approvals counts distinct non-author reviewers whose latest review is APPROVED
Several repositories can go into one file: pass --input more than once.
"""

from __future__ import annotations

import sys

# Check the interpreter before importing anything that needs 3.11 (datetime.UTC, for one).
if sys.version_info < (3, 11):  # noqa: UP036
    sys.exit("team-operations-read needs Python 3.11 or later; try python3.12")

import argparse
import csv
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import vendored  # noqa: E402
from inputs import note_system  # noqa: E402

HEADER = ["id", "squad", "opened", "first_review", "merged", "approvals", "author"]
lr = vendored.load("from_github")


def _who(row: dict) -> dict:
    who = row.get("author") or row.get("user")
    return who if isinstance(who, dict) else {}


def _is_bot(author: dict) -> bool:
    if not author:
        return True
    return bool(author.get("is_bot")) or author.get("type") == "Bot" or str(author.get("login", "")).endswith("[bot]")


def _squad(pr: dict, fixed: str | None, prefix: str | None) -> str:
    if fixed:
        return fixed
    if prefix:
        for label in pr.get("labels") or []:
            name = str(label.get("name", "") if isinstance(label, dict) else label)
            if name.startswith(prefix):
                return name[len(prefix) :].strip()
    return ""


def _reviewed_at(review: dict):
    return lr.stamp(lr.field(review, "submittedAt", "submitted_at"))


def convert(prs: list[dict], source: str, squad: str | None = None, prefix: str | None = None) -> tuple[list[list], dict]:
    rows, skipped = [], {"bot": 0, "draft": 0}
    for pr in prs:
        author = _who(pr)
        if _is_bot(author):
            skipped["bot"] += 1
            continue
        if lr.field(pr, "isDraft", "draft"):
            skipped["draft"] += 1
            continue
        login = author.get("login")
        others = [r for r in pr.get("reviews") or [] if lr.field(r, "submittedAt", "submitted_at") and _who(r).get("login") not in (None, login)]
        others.sort(key=_reviewed_at)
        latest: dict[str, str] = {}
        for r in others:
            latest[_who(r)["login"]] = r.get("state", "")
        approvals = sum(1 for state in latest.values() if state == "APPROVED")
        rows.append(
            [
                f"{source}#{lr.field(pr, 'number', 'id')}",
                _squad(pr, squad, prefix),
                lr.field(pr, "createdAt", "created_at"),
                lr.field(others[0], "submittedAt", "submitted_at") if others else "",
                lr.field(pr, "mergedAt", "merged_at") or "",
                approvals,
                login,
            ]
        )
    return rows, skipped


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Convert a GitHub pull request export to pull_requests.csv.")
    ap.add_argument("--input", required=True, action="append", type=Path, help="gh pr list --json output, or gh api output; repeat for several repositories")
    ap.add_argument("--out", required=True, type=Path, help="data folder; pull_requests.csv is written here")
    ap.add_argument("--repo", help="OWNER/NAME, for the source line of each figure")
    ap.add_argument("--retrieved-at", help="YYYY-MM-DD the export was taken; defaults to today")
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--squad", help="one squad name for every pull request")
    group.add_argument("--squad-label-prefix", help="take the squad from a label with this prefix, such as squad:")
    a = ap.parse_args(argv)
    rows, skipped = [], {"bot": 0, "draft": 0}
    for path in a.input:
        try:
            prs = lr.read_arrays(path)
            r, s = convert(prs, path.stem, a.squad, a.squad_label_prefix)
        except SystemExit as e:  # the vendored reader stops with a message on a file it cannot read
            print(f"error: {e}", file=sys.stderr)
            return 2
        except (ValueError, KeyError, TypeError) as e:
            print(f"error: {path}: {e}", file=sys.stderr)
            return 2
        rows += r
        skipped = {k: skipped[k] + s[k] for k in skipped}
    a.out.mkdir(parents=True, exist_ok=True)
    with (a.out / "pull_requests.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(HEADER)
        w.writerows(rows)
    where = a.repo or ", ".join(p.stem for p in a.input)
    note_system(a.out, "pull_requests.csv", f"GitHub ({where}), retrieved {a.retrieved_at or date.today().isoformat()}")
    print(f"Wrote {len(rows)} pull requests to {a.out / 'pull_requests.csv'}. Left out {skipped['bot']} by bots and {skipped['draft']} drafts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
