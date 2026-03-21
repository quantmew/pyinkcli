"""Minimal work tag constants aligned with ReactWorkTags responsibilities."""

from __future__ import annotations

FunctionComponent = 0
ClassComponent = 1
HostRoot = 3
HostComponent = 5
HostText = 6
Fragment = 7
SuspenseComponent = 13

__all__ = [
    "ClassComponent",
    "Fragment",
    "FunctionComponent",
    "HostComponent",
    "HostRoot",
    "HostText",
    "SuspenseComponent",
]
