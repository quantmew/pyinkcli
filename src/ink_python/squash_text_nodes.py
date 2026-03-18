"""
Compatibility wrapper for squashTextNodes.

The canonical implementation lives in `ink_python.dom` so text squashing,
child transforms, and sanitize behavior stay aligned in one place.
"""

from __future__ import annotations

from ink_python.dom import squashTextNodes

__all__ = ["squashTextNodes"]
