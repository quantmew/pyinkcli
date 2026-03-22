from __future__ import annotations

from ..components.Text import Text


def ErrorOverview(error=None):
    return Text(str(error) if error is not None else "")


__all__ = ["ErrorOverview"]

