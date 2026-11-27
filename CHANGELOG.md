# Changelog

## 0.3.4, 2026-11-27

- 12px floor: every label on the page (the header, the next step, who decides and who owns it, status lines, section labels, the figures table, owner names and due dates) renders at 12px or more. The page raises any smaller size in the vendored template and svgkit to 12px as it inlines them (was 11px), 11.5px text included; the vendored files are unchanged. A test checks no font size under 12px in the page CSS.
- Dates never break: every ISO date in the page's text (headings, intro, figure lines) is held on one line with `white-space: nowrap`, so a narrow screen never splits one at a hyphen. A test checks every date on the sample.
- Plain words: the README defines a bet once, under its opening line ("A bet is a project you expect to move a number; its bar is the target its landing brief sets."), and SKILL.md tells Claude to use the user's word, project or bet, while the record key stays `bet`. A test checks no other README or SKILL.md prose says bet or bar.

## 0.3.3, 2026-11-27

- Full column: the heading, the intro, the next step, section text and captions run the full width of the content column, the same width as the scorecard frame (the site's rule since 2026-11-25). The page's own CSS drops its caps on text (the heading's 20ch and the folds' 80ch) and overrides the vendored template's 62ch intro and svgkit's 76ch caption after their rules, so neither hash-pinned file changes. The heading balances its lines; text breaks with `text-wrap: pretty`. A test checks the page CSS caps no text and the sample carries the override.

## 0.3.2, 2026-11-27

- Scorecard fix round: each function (Development, Operations and the rest) is a hairline group heading over its areas, as /update groups its scorecard rows, so the word column carries only START HERE. The figure column prints in one case, numerals and capitals ("LEVEL 2 OR BELOW"), as /update. Tests for both.
- The picture is scorecard rows in the grammar of the outcome scorecard on dacard.ai/update (svgkit 1.2.0, landing-loop 78784ef): one row per area these exports can read, five pips for levels 1 to 5 filled to the band's floor and dashed for the rest of the band, the read in words, exactly as precise as the data: a band stays a band ("level 2 or below", "level 3 or above"), and an exact level fills exactly that many pips with none dashed ("level 3", Team Orchestration), START HERE in ink on the one to start with, and the 21 areas the exports can't see as one muted line. Geist Mono 12px for labels and figures, Geist 14px for names, no text inside a picture, no box inside the frame. The area grid, its panel and the boxed status chips are gone; words print as text.
- README and SKILL.md in plain words: project, the project file. Keys, file names and flags are unchanged. SKILL.md uses the user's own word if they say bet.
- Tests from the rollout recipe: no text inside an SVG, no scaled SVG, labels 12px and names 14px, no box inside the frame, no legacy svgkit primitive (rendered with DeprecationWarning as an error), one frame with one row per area read and the unread areas as one line, the picture exactly as precise as the printed figure, and the aria-label states the answer.

## 0.3.1, 2026-11-27

- The HTML page follows the Landing Loop sample anatomy: the shared header (mark, DACARD, skill, date, version, blue Illustrative tag), where to start as the heading ("Start with Roadmap Discipline."), the area and count chips, the signature picture, one next step with the decider in brass and the re-check date, then the areas read and what the exports can't see in two columns. Each area in full, what would read the other areas, every figure with its source, and "For your engineers" (the stored reads, rule ids, command, overclaim check, record key) are folded.
- The signature picture is the area grid: all 27 areas under their function. The areas these exports can read are shaded, with five marks for levels 1 to 5 (filled where the evidence shows the level, outlined where it allows it but cannot confirm it); the rest are hatched, can't see from these exports; the place to start is ringed. A 720 wide variant for desktop and a 340 wide one for phones; the aria-label states the answer. Drawn with svgkit, vendored byte-identical from landing-loop 5d01756 and pinned in `VENDORED.json` under `landing-loop`.
- Plain words on the page and in the Markdown twin: area for dimension, level for stage, scoring guide for rubric, build plan template for spec template. Each finding says what it does to the level ("That caps it at level 2."). The not-read text no longer asks the reader to book anything. `read.json` keeps the framework's words; only `version` changes.
- `check_claims.py` holds "level N" to the same bounds as "Stage N", and reads "caps it at level", "shows level" and "to reach level" as citations, not claims.
- Tests: the picture draws only printed figures, every area appears and the unread ones are hatched, no status colour, an aria-label that states the answer, plain words in public copy, and the svgkit pin.
- Design fix round 2: no text below 11px at any width (the page raises the vendored template's and svgkit's smaller sizes as it inlines them; the files on disk are unchanged); the header prints the plain name, Team operations read, and the code name moves to the engineers' fold, on the page and in the Markdown twin; public copy drops record, bet, the bar, PRD, ARR and tokens (decision logs, architecture notes, incident logs, pricing history; exports "do not capture").
- On phones up to 440px the picture's panel gives it its full 340px, so its 11px labels render at 11px at 390 and 375 wide.

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
