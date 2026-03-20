"""
useFocus hook for pyinkcli.

Maintains a focus registry inspired by Ink's focus runtime.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass

from pyinkcli.hooks._runtime import useEffect, useState
from pyinkcli.hooks.use_stdin import useStdin


@dataclass
class _FocusEntry:
    id: str
    is_active: bool = True


class _FocusRuntime:
    def __init__(self) -> None:
        self.enabled = True
        self.active_id: str | None = None
        self.entries: list[_FocusEntry] = []
        self.listeners: list[Callable[[], None]] = []

    def subscribe(self, listener: Callable[[], None]) -> Callable[[], None]:
        self.listeners.append(listener)

        def unsubscribe() -> None:
            with suppress(ValueError):
                self.listeners.remove(listener)

        return unsubscribe

    def notify(self) -> None:
        for listener in list(self.listeners):
            with suppress(Exception):
                listener()

    def add(self, element_id: str, auto_focus: bool = False) -> None:
        changed = False
        if not any(entry.id == element_id for entry in self.entries):
            self.entries.append(_FocusEntry(id=element_id, is_active=True))
            changed = True

        if auto_focus and self.active_id is None:
            self.active_id = element_id
            changed = True

        if changed:
            self.notify()

    def remove(self, element_id: str) -> None:
        previous_count = len(self.entries)
        self.entries = [entry for entry in self.entries if entry.id != element_id]
        changed = len(self.entries) != previous_count
        if self.active_id == element_id:
            self.active_id = None
            changed = True
        if changed:
            self.notify()

    def activate(self, element_id: str) -> None:
        changed = False
        for entry in self.entries:
            if entry.id == element_id and not entry.is_active:
                entry.is_active = True
                changed = True
                break

        if changed:
            self.notify()

    def deactivate(self, element_id: str) -> None:
        changed = False
        for entry in self.entries:
            if entry.id == element_id and entry.is_active:
                entry.is_active = False
                changed = True
                break

        if self.active_id == element_id:
            self.active_id = None
            changed = True

        if changed:
            self.notify()

    def focus(self, element_id: str) -> None:
        if (
            self.active_id != element_id
            and any(entry.id == element_id and entry.is_active for entry in self.entries)
        ):
            self.active_id = element_id
            self.notify()

    def focus_next(self) -> None:
        active_entries = [entry for entry in self.entries if entry.is_active]
        if not active_entries:
            self.active_id = None
            self.notify()
            return

        if self.active_id is None:
            self.active_id = active_entries[0].id
            self.notify()
            return

        ids = [entry.id for entry in active_entries]
        try:
            index = ids.index(self.active_id)
        except ValueError:
            self.active_id = ids[0]
            self.notify()
            return

        self.active_id = ids[(index + 1) % len(ids)]
        self.notify()

    def focus_prev(self) -> None:
        active_entries = [entry for entry in self.entries if entry.is_active]
        if not active_entries:
            self.active_id = None
            self.notify()
            return

        if self.active_id is None:
            self.active_id = active_entries[-1].id
            self.notify()
            return

        ids = [entry.id for entry in active_entries]
        try:
            index = ids.index(self.active_id)
        except ValueError:
            self.active_id = ids[-1]
            self.notify()
            return

        self.active_id = ids[(index - 1) % len(ids)]
        self.notify()

    def enable_focus(self) -> None:
        if not self.enabled:
            self.enabled = True
            self.notify()

    def disable_focus(self) -> None:
        changed = self.enabled or self.active_id is not None
        self.enabled = False
        self.active_id = None
        if changed:
            self.notify()


_focus_runtime = _FocusRuntime()
_focus_counter = 0


def _create_focus_id() -> str:
    global _focus_counter
    _focus_counter += 1
    return f"focus-{_focus_counter}"


def useFocus(
    *,
    id: str | None = None,
    auto_focus: bool = False,
    is_active: bool = True,
) -> tuple[bool, Callable[[str | None], None]]:
    """
    Hook to manage focus state.
    """

    element_id = id or _create_focus_id()
    _, set_version = useState(0)
    stdin = useStdin()

    def force_update() -> None:
        set_version(lambda value: value + 1)

    def subscribe_runtime():
        return _focus_runtime.subscribe(force_update)

    useEffect(subscribe_runtime, (element_id,))

    def register_focusable():
        _focus_runtime.add(element_id, auto_focus=auto_focus)

        def cleanup():
            _focus_runtime.remove(element_id)

        return cleanup

    useEffect(register_focusable, (element_id, auto_focus))

    def sync_active_state():
        if is_active:
            _focus_runtime.activate(element_id)
        else:
            _focus_runtime.deactivate(element_id)
        return None

    useEffect(sync_active_state, (element_id, is_active))

    def manage_raw_mode():
        if not is_active:
            return None

        stdin.set_raw_mode(True)

        def cleanup():
            stdin.set_raw_mode(False)

        return cleanup

    useEffect(manage_raw_mode, (element_id, is_active))

    def focus(target_id: str | None = None) -> None:
        _focus_runtime.focus(target_id or element_id)

    is_focused = (
        _focus_runtime.enabled
        and is_active
        and _focus_runtime.active_id == element_id
    )
    return (is_focused, focus)
def focusNext() -> None:
    _focus_runtime.focus_next()


def focusPrev() -> None:
    _focus_runtime.focus_prev()
