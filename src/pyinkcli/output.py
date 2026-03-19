"""Compatibility wrapper for `pyinkcli.packages.ink.output`."""

from pyinkcli.packages.ink import output as _output
from pyinkcli.packages.ink.output import *  # noqa: F401,F403

__all__ = _output.__all__

