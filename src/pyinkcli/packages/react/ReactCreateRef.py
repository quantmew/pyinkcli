"""Ref helpers aligned with ReactCreateRef."""

from __future__ import annotations

from pyinkcli.hooks._runtime import Ref


def createRef() -> Ref[object]:
    return Ref(None)


__all__ = ["createRef"]
