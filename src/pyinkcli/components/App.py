from __future__ import annotations

from ..component import createElement
from ..hooks._runtime import useLayoutEffect
from ..hooks.use_input import useInput
from ..hooks.use_stdin import useStdin
from .AppContext import AppContext, set_app_context_value
from .StderrContext import StderrContext, set_stderr_context_value
from .StdinContext import StdinContext, set_stdin_context_value
from .StdoutContext import StdoutContext, set_stdout_context_value


def App(*children, **props):
    child = children[0] if len(children) == 1 else list(children)
    contexts = props["contexts"]
    interactive = bool(contexts.get("interactive"))
    stdin = useStdin()

    def manage_runtime():
        def cleanup():
            stdin._clear_pending_escape_flush()
            while getattr(stdin, "_raw_mode_enabled_count", 0) > 0:
                stdin.setRawMode(False)
            while getattr(stdin, "_bracketed_paste_enabled_count", 0) > 0:
                stdin.setBracketedPasteMode(False)

        return cleanup

    useLayoutEffect(manage_runtime, ())
    useInput(lambda _input, _key: None, is_active=interactive)

    return createElement(
        AppContext.Provider,
        createElement(
            StdinContext.Provider,
            createElement(
                StdoutContext.Provider,
                createElement(
                    StderrContext.Provider,
                    child,
                    value=contexts["stderr"],
                ),
                value=contexts["stdout"],
            ),
            value=contexts["stdin"],
        ),
        value=contexts["app"],
    )


def create_app_tree(node, *, contexts):
    return createElement(App, node, contexts=contexts)


def create_runtime_contexts(*, app, stdin, stdout, stderr, interactive: bool, exit_on_ctrl_c: bool = True):
    return {
        "app": set_app_context_value(app),
        "stdin": set_stdin_context_value(
            stdin=stdin,
            is_raw_mode_supported=bool(getattr(stdin, "isatty", lambda: False)()),
            exit_on_ctrl_c=exit_on_ctrl_c,
            on_exit=app.exit,
        ),
        "stdout": set_stdout_context_value(stdout=stdout, write=app._write_to_stdout),
        "stderr": set_stderr_context_value(stderr=stderr, write=app._write_to_stderr),
        "interactive": interactive,
    }


__all__ = ["App", "create_app_tree", "create_runtime_contexts"]
