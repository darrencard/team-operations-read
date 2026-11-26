# Export formats

One folder of CSV files with a header row. Every file is optional. Dates are `YYYY-MM-DD`; timestamps are ISO 8601 (UTC if no offset). Booleans are `true` or `false`. Extra columns are ignored.

| File | Columns | Feeds |
|---|---|---|
| `items.csv` | id, type, squad, assignee, created, started, completed, cycle, planned, reopened, acceptance_criteria | Delivery Velocity, Spec & Context Quality, Roadmap Discipline, Team Orchestration |
| `cycles.csv` | cycle, start, end | Roadmap Discipline |
| `pull_requests.csv` | id, squad, opened, first_review, merged, approvals | Team Orchestration, Quality & Experimentation |
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

## Mapping a tool's export

Linear: issues export gives id, type (label), team (squad), assignee, created, started, completed and cycle. `planned` is true when the issue was added to the cycle on or before the cycle start. Jira: use the sprint report for `planned`. GitHub: the pulls API gives opened (`created_at`), merged (`merged_at`); the reviews API gives `first_review` and `approvals`.

If a column is not in the export, leave the file out. Do not fill a column with a guess.
