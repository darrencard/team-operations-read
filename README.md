# Score how your product team works

A free Claude skill that reads your tracker and source-control exports and scores your team against Dacard's Team Operations framework, one dimension at a time.

**Why it matters:** maturity scores usually come from a survey and a hunch. This one comes from how work actually moved: cycle time, work in progress, planning accuracy and review latency. Code computes every figure, each one cites its source, and the skill claims no stage the evidence does not support.

**What you get:** for each dimension your data can evidence, a stage or a bounded range ("Stage 3 or above"), the evidence behind it and one next step. Every other dimension is listed as not read, with what would read it. An optional team survey sits beside the read as the team's own view, never as the score.

## Install: paste one prompt into Claude Code

```text
Install the team-operations-read skill from https://github.com/darrencard/team-operations-read by copying its skills/team-operations-read folder into ~/.claude/skills/. Run its tests with python3 -m unittest discover -s evals and show me the result. Then run it on the Acme sample in evals/fixtures/acme with --as-of 2026-11-20 and show me the read. After that, ask me for my own exports (items, cycles, pull requests, and an optional team survey) and read my team.
```

Needs Python 3.11 or later. Standard library only; nothing to install. Runs locally and makes no network calls.

## How a read works

| Step | What happens |
|---|---|
| Compute | `scripts/metrics.py` computes each figure (cycle time by work type, WIP per person, unplanned work, planning accuracy, reopen rate, time to first review, review coverage, retro follow-through) and writes it to an evidence ledger with its source file, row count and method |
| Bound | `scripts/rules.py` tests each figure against a condition from the published rubric and sets a floor or a ceiling on one dimension. One stage only when floor meets ceiling; a floor above a ceiling is reported as conflicting evidence |
| Gate | No overall Team Operations stage unless all 27 dimensions have a single-stage read. From exports alone, that never happens, and the read says so |
| Check | `scripts/check_claims.py` blocks prose that states an unsupported stage, an overall stage, or a figure not in the ledger |

Exports can evidence 6 of the 27 dimensions: Roadmap Discipline, Spec & Context Quality, Delivery Velocity, Quality & Experimentation, Team Orchestration and Process & Iteration. No rule sets a floor above Stage 3, because Stage 4 and 5 describe practices exports do not record. Rules and thresholds are in [references/rules.md](skills/team-operations-read/references/rules.md); they are v0.1 heuristics, stated as assumptions. Export formats are in [references/inputs.md](skills/team-operations-read/references/inputs.md).

## Try it on Acme

Acme is an invented company (invoicing software for trades businesses, about 400 people, 12 squads). Every figure in its sample is illustrative.

```bash
cd skills/team-operations-read && python3 scripts/read.py --data ../../evals/fixtures/acme --as-of 2026-11-20 --out run
```

Acme reads as Team Orchestration at Stage 3, Delivery Velocity and Quality & Experimentation at Stage 3 or above, and Roadmap Discipline, Spec & Context Quality and Process & Iteration at Stage 2 or below. No overall stage. (Illustrative.)

## Tests

```bash
python3 -m unittest discover -s evals
```

CI runs the tests on Python 3.11 and 3.13, and Ruff for lint and format.

## Licence

MIT. Built by [Dacard](https://www.dacard.ai). Version 0.1.0.
