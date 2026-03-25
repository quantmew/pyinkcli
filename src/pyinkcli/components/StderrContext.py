from __future__ import annotations

import sys

from ..hooks.use_stderr import _StderrHandle
from ..packages.react_context import createContext

Props = dict


def create_stderr_context_value(*, stderr=sys.stderr, write=lambda data: None):
    return _StderrHandle(stderr, write=write)


StderrContext = createContext(create_stderr_context_value())
StderrContext.displayName = "InternalStderrContext"


def set_stderr_context_value(*, stderr=sys.stderr, write=lambda data: None):
    value = create_stderr_context_value(stderr=stderr, write=write)
    StderrContext.current_value = value
    return value


__all__ = ["StderrContext"]
