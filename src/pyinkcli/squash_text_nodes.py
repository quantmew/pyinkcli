"""
Compatibility wrapper for squashTextNodes.

The canonical implementation lives in `pyinkcli.dom` so text squashing,
child transforms, and sanitize behavior stay aligned in one place.
"""

from __future__ import annotations

from pyinkcli.dom import squashTextNodes

__all__ = ["squashTextNodes"]
