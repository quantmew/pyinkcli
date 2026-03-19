"""React-style event priority surface for the pyinkcli reconciler."""

from __future__ import annotations

from typing import Literal

UpdatePriority = Literal["default", "discrete", "render_phase"]

# Kept for parity with the upstream module naming, even though pyinkcli does not
# currently thread this value through the whole work loop.
currentUpdatePriority = 0

__all__ = ["UpdatePriority", "currentUpdatePriority"]

