# Team Operations read: Acme (Illustrative)

**Start with Roadmap Discipline. Share of cycle work added after the cycle started: 43%.**

- Read 6 of 27 areas from 8 exports over 90 days. No overall level: that needs all 27.
- Level 3 or higher: Delivery Velocity at level 3 or above; Quality & Experimentation at level 3 or above; Team Orchestration at level 3 (scaling).
- Level 2 or lower: Roadmap Discipline at level 2 or below; Spec & Context Quality at level 2 or below; Process & Iteration at level 2 or below.
- Open or mixed: none.
- Can't see from these exports: 21 areas. Re-check on 2026-12-20.

Team Operations scores how a product team works in 27 areas, each on five levels. Window 2026-08-23 to 2026-11-20 (90 days). 6 of 27 areas read from cycles, epics, experiments, items, pull_requests, retro_actions, squads, survey.

> Illustrative: every figure below comes from invented sample data, not a real company.

**Overall:** no level claimed. An overall level needs a single-level read on all 27 areas. This read has 1.

**What to do next:** Roadmap Discipline. Tag each unplanned item with its source (sales, incident, executive, customer) for 2 cycles, then cap the largest source.

**Re-check:** Share of cycle work added after the cycle started, now 43%. Run this read again on 2026-12-20 with the same window to see whether it moved.

**Decides:** Head of Product, Quoting squad.

| Area | Function | Level | Next step |
|---|---|---|---|
| Roadmap Discipline | Strategy | Level 2 or below | Tag each unplanned item with its source (sales, incident, executive, customer) for 2 cycles, then cap the largest source. |
| Spec & Context Quality | Development | Level 2 or below | Sample 10 reopened items, name the missing context in each, and add the most common gap to the build plan template. |
| Delivery Velocity | Development | Level 3 or above | To reach level 4: add automated quality tests to the fast lane so its changes ship on a passing check, not a sprint review. |
| Quality & Experimentation | Operations | Level 3 or above | To reach level 4: add a pre-registered success metric and a stop rule to every experiment. |
| Team Orchestration | Operations | Level 3 (Scaling) | Set a same-day first-review norm with a named reviewer rota per squad, and track the median weekly. |
| Process & Iteration | Operations | Level 2 or below | Cut each retro to one action with a named owner and a 2-week due date, and open the next retro with its result. |

## Roadmap Discipline: level 2 or below

*Is the roadmap shaped by evidence and strategy, or by opinions and requests?*

- Share of cycle work added after the cycle started: 43%. More than 40% of cycle work arrives after planning, which reads as reactive prioritisation. That caps it at level 2.

**Next step:** Tag each unplanned item with its source (sales, incident, executive, customer) for 2 cycles, then cap the largest source.

## Spec & Context Quality: level 2 or below

*Do specs carry enough context for developers to build without guessing?*

- Share of completed items reopened: 18%. More than 15% of finished work comes back, a sign builders are guessing at edge cases. That caps it at level 2.

**Next step:** Sample 10 reopened items, name the missing context in each, and add the most common gap to the build plan template.

## Delivery Velocity: level 3 or above

*Does the team have differentiated delivery pipelines for different work types?*

- Median cycle time, bug over feature is 0.20: one work type moves through in half the time or less, a proxy for a separate delivery lane. That shows level 3 at least.
- Slowest squads by median cycle time: Data (7.0 days), Integrations (6.0 days), Invoices (6.0 days). (context, not scored)
- Team view (self-reported): 3.2 of 5 from 38 responses.

**Next step:** To reach level 4: add automated quality tests to the fast lane so its changes ship on a passing check, not a sprint review.

## Quality & Experimentation: level 3 or above

*Does the team have experimentation culture and infrastructure?*

- Experiments launched: 4 in the window. Experimentation infrastructure is in use. That shows level 3 at least.

**Next step:** To reach level 4: add a pre-registered success metric and a stop rule to every experiment.

## Team Orchestration: level 3 (scaling)

*Are teams organised for cross-functional collaboration, not silos?*

- Share of squads with product, design and engineering: 83%. Cross-functional squads are the norm. That shows level 3 at least.
- Time to first review, median: 30 hours. Work waits more than a day for a second pair of eyes, so collaboration is not yet the default. That caps it at level 3.
- Slowest squads by median time to first review: Data (39 hours), Chasing (33 hours), Payments (33 hours). (context, not scored)
- Team view (self-reported): 3.4 of 5 from 38 responses.

**Next step:** Set a same-day first-review norm with a named reviewer rota per squad, and track the median weekly.

## Process & Iteration: level 2 or below

*Do retros and process reviews actually change how the team works?*

- Share of retro actions closed within 30 days: 20%. Retros surface friction but few fixes close. That caps it at level 2.
- Team view (self-reported): 4.1 of 5 from 38 responses.
- The team's own view sits more than a level away from what the exports show. Ask why before acting on either.

**Next step:** Cut each retro to one action with a named owner and a 2-week due date, and open the next retro with its result.

## How to use this read

- It reads how work moves through the team, not whether what shipped worked. Pair it with outcome data before judging the team.
- Do not turn these figures into targets. A team pushed to cut review wait or reopens can hit the number and miss the point. Use them to pick where to look.
- The thresholds are Dacard v0.1 heuristics, not industry benchmarks. Treat each bound as a hypothesis to test with the team.
- Read a gap with the squad that owns it before acting. The slowest squads are where to ask questions, not who to blame.

## Can't see from these exports

- **Strategy:** Market Intelligence, Decision Quality, Competitive Positioning. Not readable from tracker, source-control or survey exports. A full Team Operations read would review the strategy documents, decision logs and roadmap history directly.
- **Design:** Research & Discovery, Prototyping Speed, Experience Design, Design-to-Dev Handoff. Not readable from tracker, source-control or survey exports. A full Team Operations read would review the research repository, prototypes and design system directly. Design-to-Dev Handoff: Team view (self-reported): 2.4 of 5 from 38 responses.
- **Development:** Architecture & Systems, Build vs. Buy Decisions. Not readable from tracker, source-control or survey exports. A full Team Operations read would review the architecture notes and build-or-buy decisions directly.
- **Intelligence:** Customer Signal Synthesis, Product Analytics, Data Strategy & Flywheel, Feedback Loop Quality. Not readable from tracker, source-control or survey exports. A full Team Operations read would review the analytics setup and customer feedback pipeline directly.
- **Operations:** Knowledge Management, Unit Economics, Security & Compliance, Reliability & Resilience. Not readable from tracker, source-control or survey exports. A full Team Operations read would review the operating documents, cost reporting and incident logs directly. Knowledge Management: Team view (self-reported): 1.9 of 5 from 38 responses.
- **Go-to-Market:** Positioning & Messaging, Launch Execution, Adoption & Expansion, Pricing & Packaging. Not readable from tracker, source-control or survey exports. A full Team Operations read would review the positioning, launch plans and pricing history directly.

## Every figure, with its source

Computed in code from the exports named; nothing is estimated.

| Figure | Value | Source | Window | As of | Rows | Method |
|---|---|---|---|---|---|---|
| Cycle time, median (Illustrative) | 5.0 days | items.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 568 | completed minus started, items completed in the window |
| Cycle time, 85th percentile (Illustrative) | 11.0 days | items.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 568 | nearest rank, items completed in the window |
| Cycle time, median, bug (Illustrative) | 2.0 days | items.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 169 | completed minus started, bug items |
| Cycle time, median, chore (Illustrative) | 4.0 days | items.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 119 | completed minus started, chore items |
| Cycle time, median, feature (Illustrative) | 10.0 days | items.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 225 | completed minus started, feature items |
| Cycle time, median, improvement (Illustrative) | 6.0 days | items.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 55 | completed minus started, improvement items |
| Median cycle time, bug over feature (Illustrative) | 0.20 | items.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 394 | fastest over slowest work-type median, types with 10 or more completed items |
| Cycle time, median, Assistant (Illustrative) | 4.0 days | items.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 47 | median for squad Assistant |
| Cycle time, median, Chasing (Illustrative) | 5.0 days | items.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 48 | median for squad Chasing |
| Cycle time, median, Data (Illustrative) | 7.0 days | items.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 47 | median for squad Data |
| Cycle time, median, Growth (Illustrative) | 5.0 days | items.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 47 | median for squad Growth |
| Cycle time, median, Integrations (Illustrative) | 6.0 days | items.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 48 | median for squad Integrations |
| Cycle time, median, Invoices (Illustrative) | 6.0 days | items.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 48 | median for squad Invoices |
| Cycle time, median, Mobile (Illustrative) | 4.0 days | items.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 46 | median for squad Mobile |
| Cycle time, median, Payments (Illustrative) | 6.0 days | items.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 48 | median for squad Payments |
| Cycle time, median, Platform (Illustrative) | 6.0 days | items.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 48 | median for squad Platform |
| Cycle time, median, Quoting (Illustrative) | 6.0 days | items.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 46 | median for squad Quoting |
| Cycle time, median, Reporting (Illustrative) | 4.5 days | items.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 48 | median for squad Reporting |
| Cycle time, median, Scheduling (Illustrative) | 4.0 days | items.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 47 | median for squad Scheduling |
| Share of completed items reopened (Illustrative) | 18% | items.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 568 | items with reopened above 0, of items completed in the window |
| Share of started items with acceptance criteria (Illustrative) | 72% | items.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 576 | items started in the window |
| Work in progress, mean (Illustrative) | 0.7 per person | items.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 60 | items in progress per assignee per day, averaged over the window |
| Cycles ending in the window (Illustrative) | 6 | cycles.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 6 | cycles whose end falls in the window |
| Share of cycle work added after the cycle started (Illustrative) | 43% | items.csv + cycles.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 576 | items with planned false, of items in cycles ending in the window |
| Planning accuracy (Illustrative) | 90% | items.csv + cycles.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 328 | planned items completed by their cycle end, of planned items |
| Pull request authors (Illustrative) | 60 | pull_requests.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 900 | distinct authors of pull requests opened in the window |
| Time to first review, median (Illustrative) | 30 hours | pull_requests.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 900 | first review minus opened, calendar hours |
| Time to first review, 85th percentile (Illustrative) | 56 hours | pull_requests.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 900 | nearest rank, calendar hours |
| Time to first review, median, Assistant (Illustrative) | 29 hours | pull_requests.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 65 | median for squad Assistant |
| Time to first review, median, Chasing (Illustrative) | 33 hours | pull_requests.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 67 | median for squad Chasing |
| Time to first review, median, Data (Illustrative) | 39 hours | pull_requests.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 79 | median for squad Data |
| Time to first review, median, Growth (Illustrative) | 29 hours | pull_requests.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 79 | median for squad Growth |
| Time to first review, median, Integrations (Illustrative) | 32 hours | pull_requests.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 77 | median for squad Integrations |
| Time to first review, median, Invoices (Illustrative) | 27 hours | pull_requests.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 87 | median for squad Invoices |
| Time to first review, median, Mobile (Illustrative) | 32 hours | pull_requests.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 70 | median for squad Mobile |
| Time to first review, median, Payments (Illustrative) | 33 hours | pull_requests.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 62 | median for squad Payments |
| Time to first review, median, Platform (Illustrative) | 30 hours | pull_requests.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 83 | median for squad Platform |
| Time to first review, median, Quoting (Illustrative) | 29 hours | pull_requests.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 73 | median for squad Quoting |
| Time to first review, median, Reporting (Illustrative) | 29 hours | pull_requests.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 78 | median for squad Reporting |
| Time to first review, median, Scheduling (Illustrative) | 30 hours | pull_requests.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 80 | median for squad Scheduling |
| Share of merged pull requests with an approval (Illustrative) | 92% | pull_requests.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 892 | merged in the window with 1 or more approvals |
| Share of squads with product, design and engineering (Illustrative) | 83% | squads.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 12 | squads listing pm, design and eng roles |
| Share of epics with success criteria (Illustrative) | 60% | epics.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 30 | epics with success_criteria true |
| Share of retro actions closed within 30 days (Illustrative) | 20% | retro_actions.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 40 | actions raised in the window and at least 30 days before the as-of date |
| Experiments launched (Illustrative) | 4 | experiments.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 4 | experiments with a launch date in the window |
| Team survey, Delivery Velocity, mean score (Illustrative) | 3.2 of 5 | survey.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 38 | mean of 1 to 5 responses, self-reported |
| Team survey, Design-to-Dev Handoff, mean score (Illustrative) | 2.4 of 5 | survey.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 38 | mean of 1 to 5 responses, self-reported |
| Team survey, Knowledge Management, mean score (Illustrative) | 1.9 of 5 | survey.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 38 | mean of 1 to 5 responses, self-reported |
| Team survey, Process & Iteration, mean score (Illustrative) | 4.1 of 5 | survey.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 38 | mean of 1 to 5 responses, self-reported |
| Team survey, Team Orchestration, mean score (Illustrative) | 3.4 of 5 | survey.csv | 2026-08-23 to 2026-11-20 | 2026-11-20 | 38 | mean of 1 to 5 responses, self-reported |

Where each file came from: cycles.csv, Illustrative tracker export; epics.csv, Illustrative tracker export; experiments.csv, Illustrative experiment log; items.csv, Illustrative tracker export; pull\_requests.csv, Illustrative GitHub export; retro\_actions.csv, Illustrative retro log; squads.csv, Illustrative team list; survey.csv, Illustrative team survey.

## For your engineers

Skill: `team-operations-read` 0.3.1.

Each area's read as read.json stores it, and the rules behind it (references/rules.md). This page prints Stage as level and dimension as area.

| Area | Stored read | Rules |
|---|---|---|
| Roadmap Discipline (`roadmap_discipline`) | Stage 2 or below | roadmap\_discipline.unplanned |
| Spec & Context Quality (`spec_context_quality`) | Stage 2 or below | spec\_context\_quality.reopens |
| Delivery Velocity (`delivery_velocity`) | Stage 3 or above | delivery\_velocity.lanes, cycle\_time.by\_squad |
| Quality & Experimentation (`quality_experimentation`) | Stage 3 or above | quality\_experimentation.experiments |
| Team Orchestration (`team_orchestration`) | Stage 3 (Scaling) | team\_orchestration.squads, team\_orchestration.review\_wait, review\_wait.by\_squad |
| Process & Iteration (`process_iteration`) | Stage 2 or below | process\_iteration.retro\_actions |

Record key: none. A team read writes nothing into a Landing Loop project file (`landing/<bet>.json`).
