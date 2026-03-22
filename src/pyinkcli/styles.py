from __future__ import annotations

from typing import TypedDict


class Styles(TypedDict, total=False):
    width: int
    height: int
    padding: int
    margin: int
    backgroundColor: str
    borderStyle: str
    borderColor: str
    flexDirection: str
    flexWrap: str


__all__ = ["Styles"]

