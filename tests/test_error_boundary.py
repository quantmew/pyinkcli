from __future__ import annotations

from io import StringIO

import pytest

from pyinkcli.ansi_tokenizer import tokenizeAnsi
from pyinkcli import Text, render
from pyinkcli._component_runtime import _Component
from pyinkcli.component import createElement


class FakeStdout(StringIO):
    def isatty(self) -> bool:
        return False


class FakeStdin(StringIO):
    def isatty(self) -> bool:
        return False


def _strip_ansi(text: str) -> str:
    return "".join(token.value for token in tokenizeAnsi(text) if token.type == "text")


def test_class_component_renders_through_reconciler() -> None:
    class Greeting(_Component):
        def render(self):
            return Text(f"Hello {self.props['name']}")

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(createElement(Greeting, name="Ink"), stdout=stdout, stdin=stdin, debug=True)
    try:
        app.wait_until_render_flush(timeout=0.2)
        assert "Hello Ink" in stdout.getvalue()
    finally:
        app.unmount()


def test_class_component_lifecycle_methods_drive_updates_and_cleanup() -> None:
    events: list[object] = []

    class Counter(_Component):
        def __init__(self, **props):
            super().__init__(**props)
            self.state = {"count": 0}

        def componentDidMount(self):
            events.append(("did-mount", self.props["label"], self.state["count"]))
            self.set_state(lambda prev_state, props: {"count": prev_state["count"] + 1})

        def componentDidUpdate(self, prev_props, prev_state):
            events.append(
                (
                    "did-update",
                    prev_props["label"],
                    prev_state["count"],
                    self.props["label"],
                    self.state["count"],
                )
            )

        def componentWillUnmount(self):
            events.append(("will-unmount", self.props["label"], self.state["count"]))

        def render(self):
            return Text(f"{self.props['label']}:{self.state['count']}")

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(createElement(Counter, label="A"), stdout=stdout, stdin=stdin, debug=True)
    try:
        app.wait_until_render_flush(timeout=0.2)
        assert "A:1" in stdout.getvalue()
        assert ("did-mount", "A", 0) in events
        assert ("did-update", "A", 0, "A", 1) in events

        app.rerender(createElement(Counter, label="B"))
        app.wait_until_render_flush(timeout=0.2)
        assert "B:1" in stdout.getvalue()
        assert ("did-update", "A", 1, "B", 1) in events
    finally:
        app.unmount()

    assert ("will-unmount", "B", 1) in events


def test_class_component_should_component_update_can_bail_out_render() -> None:
    events: list[object] = []

    class Gate(_Component):
        def shouldComponentUpdate(self, next_props, next_state):
            events.append(("should-update", next_props["value"]))
            return next_props["value"] != "skip"

        def componentDidUpdate(self, prev_props, prev_state):
            events.append(("did-update", prev_props["value"], self.props["value"]))

        def render(self):
            return Text(self.props["value"])

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(createElement(Gate, value="first"), stdout=stdout, stdin=stdin, debug=True)
    try:
        app.wait_until_render_flush(timeout=0.2)
        assert "first" in stdout.getvalue()

        app.rerender(createElement(Gate, value="skip"))
        app.wait_until_render_flush(timeout=0.2)
        assert _strip_ansi(stdout.getvalue()).endswith("first")
        assert ("should-update", "skip") in events
        assert ("did-update", "first", "skip") not in events

        app.rerender(createElement(Gate, value="second"))
        app.wait_until_render_flush(timeout=0.2)
        assert _strip_ansi(stdout.getvalue()).endswith("second")
        assert ("did-update", "skip", "second") in events
    finally:
        app.unmount()


def test_app_error_boundary_renders_error_overview_and_exits() -> None:
    def Boom():
        raise RuntimeError("Oh no")

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(createElement(Boom), stdout=stdout, stdin=stdin)

    with pytest.raises(RuntimeError, match="Oh no"):
        app.wait_until_exit()

    output = stdout.getvalue()
    assert "ERROR" in output
    assert "Oh no" in output


def test_app_error_boundary_catches_nested_component_errors() -> None:
    def NestedComponent():
        raise ValueError("Nested component error")

    def Parent():
        return Text("Before error", createElement(NestedComponent))

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(createElement(Parent), stdout=stdout, stdin=stdin)

    with pytest.raises(ValueError, match="Nested component error"):
        app.wait_until_exit()

    output = stdout.getvalue()
    assert "ERROR" in output
    assert "Nested component error" in output


def test_app_error_boundary_catches_component_did_mount_errors() -> None:
    class BoomOnMount(_Component):
        def componentDidMount(self):
            raise RuntimeError("mount boom")

        def render(self):
            return Text("before mount")

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(createElement(BoomOnMount), stdout=stdout, stdin=stdin)

    with pytest.raises(RuntimeError, match="mount boom"):
        app.wait_until_exit()

    output = stdout.getvalue()
    assert "ERROR" in output
    assert "mount boom" in output


def test_app_error_boundary_catches_component_did_update_errors() -> None:
    class BoomOnUpdate(_Component):
        def componentDidUpdate(self, prev_props, prev_state):
            raise RuntimeError(f"update boom: {prev_props['label']} -> {self.props['label']}")

        def render(self):
            return Text(self.props["label"])

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(createElement(BoomOnUpdate, label="first"), stdout=stdout, stdin=stdin)
    try:
        app.wait_until_render_flush(timeout=0.2)
        app.rerender(createElement(BoomOnUpdate, label="second"))

        with pytest.raises(RuntimeError, match="update boom: first -> second"):
            app.wait_until_exit()
    finally:
        if not getattr(app, "_is_unmounted", False):
            app.unmount()

    output = stdout.getvalue()
    assert "ERROR" in output
    assert "update boom: first -> second" in output


def test_app_error_boundary_catches_component_will_unmount_errors() -> None:
    class BoomOnUnmount(_Component):
        def componentWillUnmount(self):
            raise RuntimeError("unmount boom")

        def render(self):
            return Text("mounted")

    def Parent(*, visible: bool):
        if visible:
            return createElement(BoomOnUnmount)
        return Text("gone")

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(createElement(Parent, visible=True), stdout=stdout, stdin=stdin)
    try:
        app.wait_until_render_flush(timeout=0.2)
        app.rerender(createElement(Parent, visible=False))

        with pytest.raises(RuntimeError, match="unmount boom"):
            app.wait_until_exit()
    finally:
        if not getattr(app, "_is_unmounted", False):
            app.unmount()

    output = stdout.getvalue()
    assert "ERROR" in output
    assert "unmount boom" in output
