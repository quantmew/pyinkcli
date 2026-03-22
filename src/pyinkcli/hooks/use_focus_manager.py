from __future__ import annotations

from types import SimpleNamespace

from ..components import FocusContext as focus_context_module
from .use_focus import _focus_runtime


def _focus(id_: str) -> str:
    _focus_runtime.active_id = id_
    return id_


def useFocusManager():
    context = focus_context_module._focus_context
    if context is not None:
        return SimpleNamespace(
            active_id=context.active_id,
            enable_focus=context.enableFocus,
            disable_focus=context.disableFocus,
            focus_next=context.focusNext,
            focus_previous=context.focusPrevious,
            focus=context.focus,
        )

    def focus_next():
        ids = _focus_runtime.ordered_ids()
        if not ids:
            return None
        if _focus_runtime.active_id not in ids:
            _focus_runtime.active_id = ids[0]
        else:
            index = (ids.index(_focus_runtime.active_id) + 1) % len(ids)
            _focus_runtime.active_id = ids[index]
        return _focus_runtime.active_id

    def focus_previous():
        ids = _focus_runtime.ordered_ids()
        if not ids:
            return None
        if _focus_runtime.active_id not in ids:
            _focus_runtime.active_id = ids[-1]
        else:
            index = (ids.index(_focus_runtime.active_id) - 1) % len(ids)
            _focus_runtime.active_id = ids[index]
        return _focus_runtime.active_id

    def enable_focus():
        _focus_runtime.enabled = True

    def disable_focus():
        _focus_runtime.enabled = False
        _focus_runtime.active_id = None

    return SimpleNamespace(
        active_id=_focus_runtime.active_id,
        enable_focus=enable_focus,
        disable_focus=disable_focus,
        focus_next=focus_next,
        focus_previous=focus_previous,
        focus=_focus,
    )


__all__ = ["useFocusManager"]

