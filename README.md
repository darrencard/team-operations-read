# Team Operations read: how your product team works, from its own exports

A free Claude skill that scores your team against Dacard's Team Operations framework from GitHub, Linear or CSV exports, and names one step to start with.

```text
Install the team-operations-read skill from https://github.com/darrencard/team-operations-read: clone it, find a Python 3.11 or later on this machine (macOS python3 is often 3.9), run its tests with it (python -m unittest discover -s evals), and copy skills/team-operations-read into ~/.claude/skills/. Then give me a Team Operations read of my team for the 90 days to today: pull our pull requests and Linear issues with the tools connected to this session (gh or the GitHub connector, the Linear connector), save each export as it stands, convert them with the skill's from_github.py and from_linear.py, and run read.py. Show me the start-here step and the read exactly as the script prints them, with the HTML page, then tell me which file would read more dimensions.
```

**Why it matters:** maturity scores usually come from a survey and a hunch. This one comes from how work moved: cycle time, work in progress, unplanned work, review wait, retro follow-through. Code computes every figure and cites its source, and the read claims no stage the evidence does not support.

**Where it sits:** outside the Landing Loop's bet record. The loop reads each bet; this skill reads the team that runs the bets. It writes no key into `landing/<bet>.json`.

## Try it on Acme

Acme is invented: invoicing software for trades businesses, about 400 people, 12 squads. Every figure is illustrative. From the repository root, with Python 3.11 or later:

```bash
python3 skills/team-operations-read/scripts/read.py --data examples/acme/data --as-of 2026-11-20 --out examples/acme --stem team-operations-read
```

That writes [examples/acme/team-operations-read.html](examples/acme/team-operations-read.html), one self-contained page in the Leader Report style, with its Markdown twin and JSON. It runs in under a second, and a test checks it reproduces the committed files byte for byte.

What it says: start with Roadmap Discipline, because 43% of cycle work arrives after planning; tag each unplanned item with its source for 2 cycles, then cap the largest source. Team Orchestration reads Stage 3. Delivery Velocity and Quality & Experimentation read Stage 3 or above. Roadmap Discipline, Spec & Context Quality and Process & Iteration read Stage 2 or below. No overall stage, because that needs all 27 dimensions. (Illustrative.)

## Install

In Claude Code:

```text
/plugin marketplace add darrencard/landing-loop
/plugin install team-operations-read@landing-loop
```

Standalone: clone this repository and copy `skills/team-operations-read` into `~/.claude/skills/`. Python 3.11 or later, standard library only, nothing else to install. The scripts make no network calls; the exports come from your own tools.

## Reads and writes

| | |
|---|---|
| **Reads** | Pull requests (GitHub, through `gh` or the GitHub connector), issues and cycles (Linear connector or API), and optional CSVs: squads, epics, retro actions, experiments, a team survey. Any tracker CSV maps by column name |
| **Live data** | The Leader Report's own GitHub and Linear collectors, vendored unchanged at a pinned commit, read the exports as the tools return them. CSV is the fallback |
| **Computes** | Cycle time by work type and squad, work in progress, unplanned share, planning accuracy, reopen rate, time to first review, review coverage, retro follow-through |
| **Writes** | `read.html`, `read.md` and `read.json` in your output folder. No Landing Loop record key |
| **Words** | Stage N, Stage N or above, Stage N or below, Stage N to M, conflicting evidence, not read. Never landed, watch or stalled: those are a bet's status, set only by did-it-land |

**Record key:** none. A team read is not a bet, so it leaves `landing/<bet>.json` exactly as it found it. Each figure in `read.json` has the same fields the loop asks of a figure:

```json
{
  "id": "unplanned_share",
  "label": "Share of cycle work added after the cycle started",
  "value": 0.4306,
  "unit": "share",
  "display": "43%",
  "source": "items.csv + cycles.csv",
  "window": {"from": "2026-08-23", "to": "2026-11-20"},
  "as_of": "2026-11-20",
  "n": 576,
  "method": "items with planned false, of items in cycles ending in the window"
}
```

Before you show any prose about a read, `check_claims.py` blocks a stage the read does not support, an overall stage it withholds, a figure not in the ledger, and bet status words.

## Limits

- **Not an outcome read.** It shows how work moves, not whether what shipped worked. Pair it with did-it-land for that.
- **Not targets.** Push a team to cut review wait and it will, whether or not collaboration improves. Use the figures to pick where to look.
- **Not benchmarks.** Thresholds are Dacard v0.1 heuristics, listed in [references/rules.md](skills/team-operations-read/references/rules.md). Each bound is a hypothesis to test with the team.
- **Not the whole framework.** Exports evidence 6 of the 27 dimensions, and no rule sets a floor above Stage 3, because Stages 4 and 5 describe practices exports do not record.
- **Linear gaps.** An issue export cannot say whether an item joined its cycle late or was reopened, so those figures need a CSV that holds them.

Not yet run on a real team's data.

## Licence

MIT. Built by [Dacard](https://www.dacard.ai). Version 0.3.0. Changes are in [CHANGELOG.md](CHANGELOG.md).

Claude is a trademark of Anthropic, PBC. This project is not made or endorsed by Anthropic.
