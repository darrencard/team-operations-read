# Changelog

## 0.3.0, 2026-11-26

- Same shape and version as the Landing Loop skills. It stays outside the bet record: it reads the team that runs the bets, writes no key into `landing/<bet>.json`, and a test checks a record beside it stays byte-identical.
- Sample: `examples/acme/team-operations-read.html`, one self-contained page in the Leader Report style, with its Markdown twin and JSON. One command from the repository root regenerates all three, and a test checks the bytes match.
- Every figure now carries value, unit, source, window (from, to) and as_of, and the read records where each file came from.
- Live data first: `from_github.py` reads the export through the Leader Report's GitHub collector, and the new `from_linear.py` reads Linear connector or GraphQL pages through its Linear collector. Both are vendored unchanged at a pinned commit (`VENDORED.json`). CSV stays the fallback.
- `read.py --stem` names the outputs and `--decides` names who owns the start-here step. The page prints that person and the re-check date in brass, and uses no status colour.
- The overclaim check blocks landed, watch and stalled: those are a bet's status words, set only by did-it-land.
- The Acme team's quoting squad is now "Quoting", to match the Landing Loop's Acme brief.

## 0.1.0, 2026-11-26

- First version: a stage or a bounded range for each Team Operations dimension that tracker, source-control and survey exports can evidence, with one start-here step, the evidence ledger and the overclaim check.
