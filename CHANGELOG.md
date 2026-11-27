# Changelog

## 0.3.1, 2026-11-27

- The HTML page follows the Landing Loop sample anatomy: the shared header (mark, DACARD, skill, date, version, blue Illustrative tag), where to start as the heading ("Start with Roadmap Discipline."), the area and count chips, the signature picture, one next step with the decider in brass and the re-check date, then the areas read and what the exports can't see in two columns. Each area in full, what would read the other areas, every figure with its source, and "For your engineers" (the stored reads, rule ids, command, overclaim check, record key) are folded.
- The signature picture is the area grid: all 27 areas under their function. The areas these exports can read are shaded, with five marks for levels 1 to 5 (filled where the evidence shows the level, outlined where it allows it but cannot confirm it); the rest are hatched, can't see from these exports; the place to start is ringed. A 720 wide variant for desktop and a 340 wide one for phones; the aria-label states the answer. Drawn with svgkit, vendored byte-identical from landing-loop 5d01756 and pinned in `VENDORED.json` under `landing-loop`.
- Plain words on the page and in the Markdown twin: area for dimension, level for stage, scoring guide for rubric, build plan template for spec template. Each finding says what it does to the level ("That caps it at level 2."). The not-read text no longer asks the reader to book anything. `read.json` keeps the framework's words; only `version` changes.
- `check_claims.py` holds "level N" to the same bounds as "Stage N", and reads "caps it at level", "shows level" and "to reach level" as citations, not claims.
- Tests: the picture draws only printed figures, every area appears and the unread ones are hatched, no status colour, an aria-label that states the answer, plain words in public copy, and the svgkit pin.

## 0.3.0, 2026-11-26

- Same shape and version as the Landing Loop skills. It stays outside the bet record: it reads the team that runs the bets, writes no key into `landing/<bet>.json`, and a test checks a record beside it stays byte-identical.
- Sample: `examples/acme/team-operations-read.html`, one self-contained page in the Leader Report style, with its Markdown twin and JSON. One command from the repository root regenerates all three, and a test checks the bytes match.
- Every figure now carries value, unit, source, window (from, to) and as_of, and the read records where each file came from.
- Live data first: `from_github.py` reads the export through the Leader Report's GitHub collector, and the new `from_linear.py` reads Linear connector or GraphQL pages through its Linear collector. Both are vendored unchanged at a pinned commit (`VENDORED.json`). CSV stays the fallback.
- `read.py --stem` names the outputs and `--decides` names who owns the start-here step. The page prints that person and the re-check date in brass, and uses no status colour.
- The overclaim check blocks landed, watch and stalled: those are a bet's status words, set only by did-it-land.
- The Acme team's quoting squad is now "Quoting", to match the Landing Loop's Acme brief.
- The page opens with a one-line answer, five summary lines and the start-here step; the rest folds under one `<details>`. The Markdown opens the same way.
- The start-here step has one owner from the Acme org chart: Head of Product, Quoting squad.
- Every entry script checks for Python 3.11 before any other import, so Python 3.9 gets a plain message, not an ImportError.
- Selection and focus print in ink; the template's green is did-it-land's colour.

## 0.1.0, 2026-11-26

- First version: a stage or a bounded range for each Team Operations dimension that tracker, source-control and survey exports can evidence, with one start-here step, the evidence ledger and the overclaim check.
