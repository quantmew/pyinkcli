"""Compatibility wrapper for `pyinkcli.packages.ink.render_node_to_output`."""

from pyinkcli.packages.ink import render_node_to_output as _render_node_to_output
from pyinkcli.packages.ink.render_node_to_output import *  # noqa: F401,F403
from pyinkcli.packages.ink.render_node_to_output import (
    render_node_to_output,
    render_node_to_screen_reader_output,
)

__all__ = _render_node_to_output.__all__
