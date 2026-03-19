"""Host-context helpers aligned with ReactFiberHostContext responsibilities."""

from __future__ import annotations

from typing import TypedDict


class HostContext(TypedDict):
    is_inside_text: bool


def getRootHostContext() -> HostContext:
    return {"is_inside_text": False}


def getChildHostContext(
    parent_host_context: HostContext,
    element_name: str,
) -> HostContext:
    previous_is_inside_text = parent_host_context.get("is_inside_text", False)
    is_inside_text = element_name in ("ink-text", "ink-virtual-text")

    if previous_is_inside_text == is_inside_text:
        return parent_host_context

    return {"is_inside_text": is_inside_text}


__all__ = ["HostContext", "getChildHostContext", "getRootHostContext"]

