"""The Team Operations framework, as published by Dacard (framework v1.0, locked through Q2 2027).

27 dimensions across 6 functions. Each dimension is scored on 5 stages. The overall stage is the sum
of all 27 dimension stages (27 to 135), banded below. This module holds names only: no scoring logic.
"""

from __future__ import annotations

STAGE_NAMES = {1: "Foundation", 2: "Building", 3: "Scaling", 4: "Leading", 5: "Compounding"}

# Overall Team Operations stage bands: sum of the 27 dimension stages.
OVERALL_BANDS = [(1, 27, 48), (2, 49, 69), (3, 70, 90), (4, 91, 113), (5, 114, 135)]

# (id, name, function, key question), in framework order.
DIMENSIONS = [
    ("market_intelligence", "Market Intelligence", "Strategy", "Does your team have continuous, systematic visibility into market shifts?"),
    ("decision_quality", "Decision Quality", "Strategy", "Are product decisions backed by evidence and structured frameworks?"),
    ("roadmap_discipline", "Roadmap Discipline", "Strategy", "Is the roadmap shaped by evidence and strategy, or by opinions and requests?"),
    ("competitive_positioning", "Competitive Positioning", "Strategy", "Does the team track competitor capabilities and market shifts systematically?"),
    ("research_discovery", "Research & Discovery", "Design", "Does user research systematically feed product decisions?"),
    ("prototyping_speed", "Prototyping Speed", "Design", "How fast does the team move from insight to validated solution?"),
    ("experience_design", "Experience Design", "Design", "Does the product use modern interaction patterns?"),
    ("design_dev_handoff", "Design-to-Dev Handoff", "Design", "Is handoff a shared, continuous collaboration or a document toss?"),
    ("architecture_systems", "Architecture & Systems", "Development", "Does the architecture support real-time data, automation, and modern tooling?"),
    ("spec_context_quality", "Spec & Context Quality", "Development", "Do specs carry enough context for developers to build without guessing?"),
    ("build_vs_buy", "Build vs. Buy Decisions", "Development", "Is there a framework for evaluating build vs. buy tradeoffs?"),
    ("delivery_velocity", "Delivery Velocity", "Development", "Does the team have differentiated delivery pipelines for different work types?"),
    ("customer_signal_synthesis", "Customer Signal Synthesis", "Intelligence", "Is customer feedback synthesised across channels into actionable insights?"),
    ("product_analytics", "Product Analytics", "Intelligence", "Does the team have behavioural depth beyond page views and DAU?"),
    ("data_strategy_flywheel", "Data Strategy & Flywheel", "Intelligence", "Is data used strategically to improve decisions and product quality over time?"),
    ("feedback_loop_quality", "Feedback Loop Quality", "Intelligence", "Do feedback mechanisms connect directly to product improvement?"),
    ("knowledge_management", "Knowledge Management", "Operations", "Is institutional knowledge captured, accessible, and current?"),
    ("quality_experimentation", "Quality & Experimentation", "Operations", "Does the team have experimentation culture and infrastructure?"),
    ("team_orchestration", "Team Orchestration", "Operations", "Are teams organised for cross-functional collaboration, not silos?"),
    ("process_iteration", "Process & Iteration", "Operations", "Do retros and process reviews actually change how the team works?"),
    ("unit_economics", "Unit Economics", "Operations", "Does the team have visibility into per-feature cost and margin?"),
    ("security_compliance", "Security & Compliance", "Operations", "Are security and compliance built into the development process?"),
    ("reliability_resilience", "Reliability & Resilience", "Operations", "Can the system handle failures gracefully and recover quickly?"),
    ("positioning_messaging", "Positioning & Messaging", "Go-to-Market", "Does positioning describe differentiated value, not features?"),
    ("launch_execution", "Launch Execution", "Go-to-Market", "Is there a structured launch playbook?"),
    ("adoption_expansion", "Adoption & Expansion", "Go-to-Market", "Is there a product-led growth motion?"),
    ("pricing_packaging", "Pricing & Packaging", "Go-to-Market", "Does pricing capture the value the product creates?"),
]

DIMENSION_IDS = [d[0] for d in DIMENSIONS]
BY_ID = {d[0]: {"id": d[0], "name": d[1], "function": d[2], "question": d[3]} for d in DIMENSIONS}
FUNCTIONS = ["Strategy", "Design", "Development", "Intelligence", "Operations", "Go-to-Market"]

if len(DIMENSIONS) != 27:
    raise RuntimeError("Team Operations has 27 dimensions")


def overall_stage(total: int) -> int:
    """Return the overall stage for a sum of 27 dimension stages."""
    for stage, low, high in OVERALL_BANDS:
        if low <= total <= high:
            return stage
    raise ValueError(f"total {total} is outside 27 to 135")
