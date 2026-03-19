"""Compatibility wrapper for `pyinkcli.packages.ink.dom`."""

from pyinkcli.packages.ink import dom as _dom
from pyinkcli.packages.ink.dom import *  # noqa: F401,F403
from pyinkcli.packages.ink.dom import add_layout_listener, emit_layout_listeners

__all__ = _dom.__all__

