"""Behavior-focused audit tests for Python runtime differences."""

from __future__ import annotations

import time
from threading import Event
from io import StringIO

from pyinkcli import Text, render, renderToString
from pyinkcli.component import createElement
from pyinkcli.hooks import useEffect, useState
from pyinkcli.hooks.state import _consume_pending_rerender_priority
from pyinkcli.suspense_runtime import (
    SuspendSignal,
    peekResource,
    readResource,
    resetAllResources,
    resetResource,
)


class FakeStdout(StringIO):
    def isatty(self) -> bool:
        return False


class FakeStdin(StringIO):
    def isatty(self) -> bool:
        return False


def Suspense(*children, fallback=None):
    return createElement("__ink-suspense__", *children, fallback=fallback)


def _clear_stream(stream: StringIO) -> None:
    stream.seek(0)
    stream.truncate(0)


def teardown_function() -> None:
    resetAllResources()


def test_render_to_string_runs_effect_but_returns_initial_render_output() -> None:
    calls: list[tuple[str, str]] = []

    def Example():
        value, set_value = useState("initial")

        def effect():
            calls.append(("effect", value))
            set_value("updated")

        useEffect(effect, ())
        return Text(value)

    output = renderToString(Example())

    assert output == "initial"
    assert calls == [("effect", "initial")]


def test_suspense_resource_loader_starts_only_once_for_same_pending_key() -> None:
    key = "tests:audit:single-loader"
    started = Event()
    released = Event()
    calls: list[str] = []

    def loader() -> str:
        calls.append("load")
        started.set()
        released.wait(0.2)
        return "value"

    resetResource(key)

    try:
        readResource(key, loader)
    except SuspendSignal:
        pass
    else:  # pragma: no cover
        raise AssertionError("expected initial readResource call to suspend")

    assert started.wait(0.1)

    try:
        readResource(key, lambda: "other")
    except SuspendSignal:
        pass
    else:  # pragma: no cover
        raise AssertionError("expected second readResource call to suspend while pending")

    released.set()
    time.sleep(0.05)

    assert calls == ["load"]
    assert peekResource(key) == "value"


def test_suspense_resource_rejection_is_cached_until_reset() -> None:
    key = "tests:audit:rejection"
    error = RuntimeError("boom")

    resetResource(key)

    try:
        readResource(key, lambda: (_ for _ in ()).throw(error))
    except SuspendSignal:
        pass
    else:  # pragma: no cover
        raise AssertionError("expected initial readResource call to suspend")

    time.sleep(0.05)

    for _ in range(2):
        try:
            readResource(key, lambda: "unused")
        except RuntimeError as caught:
            assert str(caught) == "boom"
        else:  # pragma: no cover
            raise AssertionError("expected cached rejection to be re-thrown")

    resetResource(key)


def test_suspense_resolution_without_active_renderer_does_not_leak_rerender() -> None:
    key = "tests:audit:no-renderer-rerender"

    resetResource(key)

    try:
        readResource(key, lambda: "value")
    except SuspendSignal:
        pass
    else:  # pragma: no cover
        raise AssertionError("expected initial readResource call to suspend")

    time.sleep(0.05)

    assert peekResource(key) == "value"
    assert _consume_pending_rerender_priority() is None


def test_suspense_reveals_each_boundary_as_its_resource_resolves() -> None:
    stdout = FakeStdout()
    stdin = FakeStdin()

    def Child(name: str, delay: float):
        return Text(readResource(name, lambda: (time.sleep(delay), name.upper())[1]))

    vnode = createElement(
        "ink-box",
        createElement(
            Suspense,
            createElement(Child, name="a", delay=0.02),
            fallback=createElement(Text, "A..."),
        ),
        createElement(
            Suspense,
            createElement(Child, name="b", delay=0.08),
            fallback=createElement(Text, "B..."),
        ),
    )

    app = render(vnode, stdout=stdout, stdin=stdin, concurrent=True, debug=True)
    try:
        time.sleep(0.01)
        app.wait_until_render_flush(timeout=0.3)
        assert stdout.getvalue().splitlines()[-2:] == ["A...", "B..."]

        _clear_stream(stdout)
        time.sleep(0.04)
        app.wait_until_render_flush(timeout=0.3)
        assert stdout.getvalue().splitlines()[-2:] == ["A", "B..."]

        _clear_stream(stdout)
        time.sleep(0.08)
        app.wait_until_render_flush(timeout=0.3)
        assert stdout.getvalue().splitlines()[-2:] == ["A", "B"]
    finally:
        app.unmount()


def test_suspense_reset_reenters_fallback_before_resolving_again() -> None:
    stdout = FakeStdout()
    stdin = FakeStdin()
    key = "tests:audit:reset-output"

    def Example():
        return Text(readResource(key, lambda: (time.sleep(0.03), "READY")[1]))

    vnode = createElement(
        Suspense,
        createElement(Example),
        fallback=createElement(Text, "Loading..."),
    )

    resetResource(key)
    app = render(vnode, stdout=stdout, stdin=stdin, concurrent=True, debug=True)
    try:
        time.sleep(0.01)
        app.wait_until_render_flush(timeout=0.3)
        assert stdout.getvalue().splitlines()[-1] == "Loading..."

        _clear_stream(stdout)
        time.sleep(0.05)
        app.wait_until_render_flush(timeout=0.3)
        assert stdout.getvalue().splitlines()[-1] == "READY"

        resetResource(key)
        _clear_stream(stdout)
        app.render(vnode)

        time.sleep(0.01)
        app.wait_until_render_flush(timeout=0.3)
        assert stdout.getvalue().splitlines()[-1] == "Loading..."

        _clear_stream(stdout)
        time.sleep(0.05)
        app.wait_until_render_flush(timeout=0.3)
        assert stdout.getvalue().splitlines()[-1] == "READY"
    finally:
        app.unmount()
