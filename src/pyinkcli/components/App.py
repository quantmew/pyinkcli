from __future__ import annotations

from ..component import createElement
from .AppContext import create_app_context_value
from .StderrContext import create_stderr_context_value
from .StdinContext import create_stdin_context_value
from .StdoutContext import create_stdout_context_value


def App(*children, **props):
    return children[0] if len(children) == 1 else list(children)


def create_app_tree(node, *, app, stdin, stdout, stderr, interactive: bool):
    return node


def create_runtime_contexts(*, app, stdin, stdout, stderr, interactive: bool, exit_on_ctrl_c: bool = True):
    return {
        "app": create_app_context_value(app),
        "stdin": create_stdin_context_value(
            stdin=stdin,
            set_raw_mode=lambda value: app._register_input_interest() if value else app._unregister_input_interest(),
            set_bracketed_paste_mode=lambda value: app._register_paste_interest() if value else app._unregister_paste_interest(),
            is_raw_mode_supported=bool(getattr(stdin, "isatty", lambda: False)()),
            exit_on_ctrl_c=exit_on_ctrl_c,
        ),
        "stdout": create_stdout_context_value(stdout=stdout, write=app._write_to_stdout),
        "stderr": create_stderr_context_value(stderr=stderr, write=app._write_to_stderr),
        "interactive": interactive,
    }


__all__ = ["App", "create_app_tree", "create_runtime_contexts"]
