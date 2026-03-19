"""
pyinkcli public package surface.

The canonical JS-parity export surface lives in `index.py`.
Extra Python-specific helpers remain available via lazy compatibility exports.
"""

from __future__ import annotations

from pyinkcli.index import *  # noqa: F401,F403
from pyinkcli.index import __all__ as _index_all

__version__ = "0.1.0"
__all__ = list(_index_all)
