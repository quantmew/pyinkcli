from __future__ import annotations
import sys

Props = dict


def create_stderr_context_value(*, stderr=sys.stderr, write=lambda data: None):
    return {
        "stderr": stderr,
        "write": write,
    }


StderrContext = create_stderr_context_value()

__all__ = ["StderrContext"]
