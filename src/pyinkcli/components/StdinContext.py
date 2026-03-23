from __future__ import annotations
import sys
from ..hooks.use_stdin import _StdinHandle

PublicProps = dict
Props = dict


def create_stdin_context_value(
    *,
    stdin=sys.stdin,
    set_raw_mode=lambda value: None,
    set_bracketed_paste_mode=lambda value: None,
    is_raw_mode_supported: bool = False,
    exit_on_ctrl_c: bool = True,
    internal_event_emitter=None,
):
    return {
        "stdin": stdin,
        "setRawMode": set_raw_mode,
        "setBracketedPasteMode": set_bracketed_paste_mode,
        "isRawModeSupported": is_raw_mode_supported,
        "internal_exitOnCtrlC": exit_on_ctrl_c,
        "internal_eventEmitter": internal_event_emitter or _StdinHandle(),
    }


StdinContext = create_stdin_context_value()

__all__ = ["StdinContext"]
