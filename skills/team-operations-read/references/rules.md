# Rules and thresholds (v0.1)

Each rule tests one condition from the published Team Operations rubric and sets a floor or a ceiling on one dimension. Thresholds are Dacard v0.1 heuristics: assumptions to test against real teams, not industry benchmarks. Change them in `scripts/rules.py` and the tests together.

A dimension gets one stage only when its floor meets its ceiling. A floor above a ceiling is reported as conflicting evidence. A rule below its minimum sample does not fire.

| Dimension | Rule | Minimum sample | Condition | Bound | Rubric condition tested |
|---|---|---|---|---|---|
| Delivery Velocity | lanes | 30 completed items; 2 work types with 10 or more each | fastest type median cycle time over slowest is 0.5 or less | floor 3 | Stage 3: separate iteration pipelines for different work types |
| Delivery Velocity | lanes | as above | ratio above 0.5 | ceiling 2 | Stage 2: all changes follow the same cycle |
| Roadmap Discipline | unplanned | 3 cycles ending in the window | more than 40% of cycle items added after the cycle started | ceiling 2 | Stage 2: prioritisation still reactive |
| Roadmap Discipline | accuracy | 3 cycles | under 60% of planned items done by cycle end | ceiling 2 | Stage 2: prioritisation still reactive |
| Roadmap Discipline | success criteria | 5 epics | 80% or more of epics have success criteria | floor 3 | Stage 3: initiatives have clear success criteria |
| Roadmap Discipline | success criteria | 5 epics | under 50% | ceiling 2 | Stage 3 not met |
| Spec & Context Quality | reopens | 30 completed items | more than 15% reopened | ceiling 2 | Stage 2: developers make assumptions about edge cases |
| Spec & Context Quality | acceptance | 30 started items | 80% or more have acceptance criteria | floor 3 | Stage 3: specs include behaviour details |
| Spec & Context Quality | acceptance | 30 started items | under 50% | ceiling 2 | Stage 3 not met |
| Team Orchestration | squads | 4 squads | 75% or more list pm, design and eng | floor 3 | Stage 3: cross-functional squads forming |
| Team Orchestration | squads | 4 squads | under 25% | ceiling 2 | Stage 2: cross-functional work is ad hoc |
| Team Orchestration | review wait | 20 reviewed pull requests | median time to first review above 24 hours | ceiling 3 | Stage 4: collaboration is default, not exceptional |
| Team Orchestration | WIP | any | mean work in progress above 3 per person | ceiling 3 | Stage 4: collaboration is default |
| Process & Iteration | retro actions | 5 actions raised 30 or more days ago | under 25% closed within 30 days | ceiling 2 | Stage 2: retros surface friction but fixes are slow |
| Process & Iteration | retro actions | as above | 70% or more closed within 30 days | floor 2 | rules out Stage 1: retros rarely change how the team works |
| Quality & Experimentation | experiments | experiments.csv present | 3 or more launched in the window | floor 3 | Stage 3: A/B testing infrastructure operational |
| Quality & Experimentation | experiments | experiments.csv present | none launched | ceiling 2 | Stage 2: A/B testing talked about, not practised |
| Quality & Experimentation | review gate | 20 merged pull requests | under 80% merged with an approval | ceiling 3 | Stage 4: quality gates block bad releases |

## What these exports cannot show

No rule sets a floor above 3. Stage 4 and 5 in every dimension describe practices (automated evaluation, living specs, self-improving processes) that tracker and source-control exports do not record. A read can show that a team is at least Stage 3; it cannot show Stage 4.

## The overall stage

The overall Team Operations stage is the sum of all 27 dimension stages, banded 27 to 48 Foundation, 49 to 69 Building, 70 to 90 Scaling, 91 to 113 Leading, 114 to 135 Compounding. It is claimed only when every one of the 27 dimensions has a single-stage read. From these exports alone that never happens, so a read from exports never states an overall stage.

## The survey

Survey means are shown beside a dimension as the team's own view, from 5 or more responses. They never move a floor or a ceiling. When the mean sits more than a stage outside the evidence bounds, the read says the two disagree.
