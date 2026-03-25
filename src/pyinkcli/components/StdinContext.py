from __future__ import annotations

import sys

from ..hooks.use_stdin import _StdinHandle
from ..packages.react_context import createContext

PublicProps = dict
Props = dict


def create_stdin_context_value(
    *,
    stdin=sys.stdin,
    is_raw_mode_supported: bool = False,
    exit_on_ctrl_c: bool = True,
    internal_event_emitter=None,
    on_exit=None,
):
    return _StdinHandle(
        stream=stdin,
        is_raw_mode_supported=is_raw_mode_supported,
        exit_on_ctrl_c=exit_on_ctrl_c,
        internal_event_emitter=internal_event_emitter,
        on_exit=on_exit,
    )


StdinContext = createContext(create_stdin_context_value())
StdinContext.displayName = "InternalStdinContext"


def set_stdin_context_value(
    *,
    stdin=sys.stdin,
    is_raw_mode_supported: bool = False,
    exit_on_ctrl_c: bool = True,
    internal_event_emitter=None,
    on_exit=None,
):
    value = create_stdin_context_value(
        stdin=stdin,
        is_raw_mode_supported=is_raw_mode_supported,
        exit_on_ctrl_c=exit_on_ctrl_c,
        internal_event_emitter=internal_event_emitter,
        on_exit=on_exit,
    )
    StdinContext.current_value = value
    return value

__all__ = ["StdinContext"]
