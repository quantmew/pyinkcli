from __future__ import annotations

import sys

from ..hooks.use_stdout import _StdoutHandle
from ..packages.react_context import createContext

Props = dict


def create_stdout_context_value(*, stdout=sys.stdout, write=lambda data: None):
    return _StdoutHandle(stdout, write=write)


StdoutContext = createContext(create_stdout_context_value())
StdoutContext.displayName = "InternalStdoutContext"


def set_stdout_context_value(*, stdout=sys.stdout, write=lambda data: None):
    value = create_stdout_context_value(stdout=stdout, write=write)
    StdoutContext.current_value = value
    return value


__all__ = ["StdoutContext", "create_stdout_context_value", "set_stdout_context_value"]
