"""Shared test setup: put the skill's scripts on the path and build small figure sets."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "team-operations-read"
SCRIPTS = SKILL / "scripts"
ACME = ROOT / "evals" / "fixtures" / "acme"
AS_OF = "2026-11-20"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def fig(fid: str, value: float, n: int = 100, unit: str = "share") -> dict:
    """A figure as metrics.py writes it, for rule tests."""
    from metrics import _fmt

    return {"id": fid, "label": fid, "value": value, "unit": unit, "display": _fmt(value, unit), "source": "test", "n": n, "method": "test"}


def figs(*items: dict) -> dict:
    return {f["id"]: f for f in items}
