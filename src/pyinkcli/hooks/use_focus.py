from __future__ import annotations

from dataclasses import dataclass, field

from ._runtime import useEffect


@dataclass
class _FocusRuntime:
    entries: dict[str, dict] = field(default_factory=dict)
    active_id: str | None = None
    enabled: bool = True
    listeners: list[object] = field(default_factory=list)

    def ordered_ids(self) -> list[str]:
        return list(self.entries.keys())


_focus_runtime = _FocusRuntime()


def useFocus(*, id: str, auto_focus: bool = False):
    _focus_runtime.entries.setdefault(id, {"auto_focus": auto_focus})
    if auto_focus and _focus_runtime.active_id is None and _focus_runtime.enabled:
        _focus_runtime.active_id = id

    def cleanup():
        _focus_runtime.entries.pop(id, None)
        if _focus_runtime.active_id == id:
            _focus_runtime.active_id = None

    useEffect(lambda: cleanup, (id,))
    return (_focus_runtime.active_id == id), {"isFocused": _focus_runtime.active_id == id}


__all__ = ["_focus_runtime", "useFocus"]

