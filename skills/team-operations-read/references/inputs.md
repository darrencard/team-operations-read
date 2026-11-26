# Export formats

One folder of CSV files with a header row. Every file is optional. Dates are `YYYY-MM-DD`; timestamps are ISO 8601 (UTC if no offset). Booleans are `true` or `false`. Extra columns are ignored.

| File | Columns | Feeds |
|---|---|---|
| `items.csv` | id, type, squad, assignee, created, started, completed, cycle, planned, reopened, acceptance_criteria | Delivery Velocity, Spec & Context Quality, Roadmap Discipline, Team Orchestration |
| `cycles.csv` | cycle, start, end | Roadmap Discipline |
| `pull_requests.csv` | id, squad, opened, first_review, merged, approvals, author | Team Orchestration, Quality & Experimentation |
| `squads.csv` | squad, roles | Team Orchestration |
| `epics.csv` | id, squad, success_criteria | Roadmap Discipline |
| `retro_actions.csv` | id, squad, raised, closed | Process & Iteration |
| `experiments.csv` | id, squad, launched | Quality & Experimentation |
| `survey.csv` | respondent, dimension, score | Team view beside any dimension; never a read on its own |
| `manifest.json` | `{"company": "...", "illustrative": true}` | Labels. `illustrative` marks every figure Illustrative. |

## Column notes

- **items.csv.** `type` is the work type (feature, bug, chore, or your own). `started` and `completed` may be blank for work not started or not done. `cycle` names a row in `cycles.csv`. `planned` is true when the item was in the cycle at its start. `reopened` is how many times it was reopened (0 if never). `acceptance_criteria` is true when the item had them before work started.
- **pull_requests.csv.** `first_review` is the first review of any kind by someone other than the author. `approvals` is the count at merge.
- **squads.csv.** `roles` lists the roles in the squad, separated by `;`. A squad counts as cross-functional when it lists `pm`, `design` and `eng`.
- **retro_actions.csv.** One row per action raised in a retro. `closed` is blank if still open.
- **survey.csv.** One row per respondent per dimension. `dimension` is a Team Operations dimension id from `scripts/framework.py` (for example `design_dev_handoff`). `score` is 1 to 5. A dimension needs 5 or more responses before its team view is shown.

Optional columns: `cycle`, `planned`, `reopened` and `acceptance_criteria` in items.csv, and `approvals` and `author` in pull_requests.csv. Leave a column out when the export does not hold it; the figures that need it are not computed.

## Readers

**GitHub.** `scripts/from_github.py` reads `gh pr list --json number,createdAt,mergedAt,isDraft,author,reviews,labels` output and writes pull_requests.csv. It drops bot authors and drafts, ignores self-reviews, and counts an approval only when a reviewer's latest review is APPROVED. Squad comes from `--squad` or a label prefix such as `squad:`. Repeat `--input` for several repositories.

**Any tracker CSV.** `scripts/from_csv.py --target items` maps columns by name. Check the header of your own export first; column names change between tools and versions. Example mappings (assumptions to check against your file):

```bash
# Linear issues export
python3 scripts/from_csv.py --input linear.csv --target items --out run/data \
  --map id=ID --map squad=Team --map assignee=Assignee --map created=Created \
  --map started=Started --map completed=Completed --map type=Labels --map cycle="Cycle Name" \
  --type-values bug,feature,chore,improvement

# Jira issues export
python3 scripts/from_csv.py --input jira.csv --target items --out run/data \
  --map id="Issue key" --map type="Issue Type" --map squad="Project name" --map assignee=Assignee \
  --map created=Created --map started="Start date" --map completed=Resolved --map cycle=Sprint
```

`planned` (in the cycle at its start) is rarely a column in a plain export. Jira's sprint report and Linear's cycle history hold it; add it only from one of those.

Jira often exports dates as `18/Nov/26 10:22 AM`; set the export to ISO dates first, or the read stops with the file, line and column. A mapped `cycle` must match a `cycle` in cycles.csv.

If a column is not in the export, leave the column out. Do not fill it with a guess.
