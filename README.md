# Score how your product team works

A free Claude skill that reads your GitHub and tracker exports and scores your team against Dacard's Team Operations framework, one dimension at a time.

**Why it matters:** maturity scores usually come from a survey and a hunch. This one comes from how work actually moved: cycle time, work in progress, planning accuracy and review latency. Code computes every figure, each one cites its source, and the skill claims no stage the evidence does not support.

**What you get:** one step to start with and a date to re-check it. For each dimension your data can evidence, a stage or a bounded range ("Stage 3 or above"), the evidence, the slowest squads as context, and one next step. Every other dimension is listed as not read, with what would read it.

## Install: paste one prompt into Claude Code

```text
Clone https://github.com/darrencard/team-operations-read with gh and copy its skills/team-operations-read folder into ~/.claude/skills/. Run its tests with python3 -m unittest discover -s evals and show me the result. Then give me a first Team Operations read from GitHub alone: export pull requests for OWNER/NAME with gh, convert them with scripts/from_github.py, and run scripts/read.py with today as the as-of date. Show me the start-here step and the read, then ask me for a squads list and tracker exports to read more dimensions.
```

Replace `OWNER/NAME`. Needs Python 3.11 or later and the `gh` CLI. Standard library only; nothing else to install. Runs locally and makes no network calls of its own. The read itself takes under a second (0.03 seconds on the Acme sample, measured on a laptop).

Tested so far on the Acme fixtures and once on a real single-author repository (47 pull requests), where the read correctly declined to score review data from fewer than 3 authors. Not yet run on a full team's data.

## How a read works

| Step | What happens |
|---|---|
| Read | `from_github.py` turns `gh pr list` output into the input file, dropping bots, drafts and self-reviews. `from_csv.py` maps any tracker CSV (Linear, Jira, a spreadsheet) by column name |
| Compute | `metrics.py` computes each figure (cycle time by work type and squad, WIP per person, unplanned work, planning accuracy, reopen rate, time to first review, review coverage, retro follow-through) into an evidence ledger with source file, row count and method |
| Bound | `rules.py` tests each figure against a condition from the published rubric and sets a floor or a ceiling on one dimension. One stage only when floor meets ceiling; floor above ceiling is reported as conflicting evidence |
| Start | The read opens with one next step (conflicting evidence first, then the lowest ceiling) and a re-check date 30 days out. If nothing is bounded yet, it names the quickest file to add |
| Gate | No overall Team Operations stage unless all 27 dimensions have a single-stage read. From exports alone that never happens, and the read says so |
| Check | `check_claims.py` blocks prose that states an unsupported stage, an overall stage, or a figure not in the ledger |

## What it is not

- **Not an outcome read.** It shows how work moves, not whether what shipped worked. Pair it with outcome data.
- **Not targets.** Push a team to cut review wait and it will, whether or not collaboration improves. Use the figures to choose where to look.
- **Not benchmarks.** Thresholds are Dacard v0.1 heuristics, listed in [references/rules.md](skills/team-operations-read/references/rules.md). Each bound is a hypothesis to test with the team.
- **Not the whole framework.** Exports evidence 6 of the 27 dimensions, and no rule sets a floor above Stage 3, because Stage 4 and 5 describe practices exports do not record.

## Try it on Acme

Acme is an invented company (invoicing software for trades businesses, about 400 people, 12 squads). Every figure in its sample is illustrative.

```bash
cd skills/team-operations-read && python3 scripts/read.py --data ../../evals/fixtures/acme --as-of 2026-11-20 --out run
```

Acme starts with Roadmap Discipline: 43% of cycle work arrives after planning, so the next step is to tag each unplanned item with its source for 2 cycles. Team Orchestration reads Stage 3; Delivery Velocity and Quality & Experimentation read Stage 3 or above; Roadmap Discipline, Spec & Context Quality and Process & Iteration read Stage 2 or below. No overall stage. (Illustrative.)

## Tests

```bash
python3 -m unittest discover -s evals
```

CI runs the tests on Python 3.11 and 3.13, and Ruff for lint and format. Input formats are in [references/inputs.md](skills/team-operations-read/references/inputs.md).

## Licence

MIT. Built by [Dacard](https://www.dacard.ai). Version 0.1.0.
