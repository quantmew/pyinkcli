from __future__ import annotations
import sys

Props = dict


def create_stdout_context_value(*, stdout=sys.stdout, write=lambda data: None):
    return {
        "stdout": stdout,
        "write": write,
    }


StdoutContext = create_stdout_context_value()

__all__ = ["StdoutContext"]
