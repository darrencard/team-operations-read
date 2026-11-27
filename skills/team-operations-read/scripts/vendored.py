"""Load the Leader Report's collectors from scripts/vendor/, copied unchanged at the commit in VENDORED.json.

Each vendored script puts its own folder first on the import path so it can find its siblings (collect.py,
landing_brief.py). This loader restores the path afterwards, so this skill's own scripts always win a name.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

VENDOR = Path(__file__).resolve().parent / "vendor"
_loaded: dict[str, ModuleType] = {}


def load(name: str) -> ModuleType:
    """Return the vendored module `name` (such as from_github), loaded under a private name."""
    if name in _loaded:
        return _loaded[name]
    saved = list(sys.path)
    try:
        spec = importlib.util.spec_from_file_location(f"leader_report_{name}", VENDOR / f"{name}.py")
        if spec is None or spec.loader is None:
            raise ImportError(f"no vendored module {name}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = saved
    _loaded[name] = module
    return module
