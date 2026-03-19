from __future__ import annotations

import array as array_module
import builtins
import datetime as datetime_module
import enum
from io import StringIO
from pathlib import Path
import re
from collections import OrderedDict
from unittest.mock import patch

from pyinkcli import Text, render
from pyinkcli._component_runtime import _Component
from pyinkcli.component import createElement
from pyinkcli.packages.react_devtools_core.hydration import (
    make_bridge_call,
    make_bridge_notification,
)
from pyinkcli.hooks import useState
from pyinkcli.suspense_runtime import SuspendSignal


class FakeStdout(StringIO):
    def isatty(self) -> bool:
        return False


class FakeStdin(StringIO):
    def isatty(self) -> bool:
        return False


class FakeThenable:
    def __init__(self, status: str, *, value: object = None, reason: object = None) -> None:
        self.status = status
        self.value = value
        self.reason = reason

    def then(self, callback):
        return callback


class FakeLazyPayload:
    def __init__(self, status: str, *, value: object = None, reason: object = None) -> None:
        self.status = status
        self.value = value
        self.reason = reason


class FakeLazy:
    __ink_devtools_react_lazy__ = True

    def __init__(self, payload: FakeLazyPayload) -> None:
        self._payload = payload


class FakeLegacyLazyPayload:
    def __init__(self, status: int, result: object) -> None:
        self._status = status
        self._result = result


class FakeHtmlElement:
    __ink_devtools_html_element__ = True

    def __init__(self, tag_name: str) -> None:
        self.tagName = tag_name


class FakeHtmlAllCollection:
    __ink_devtools_html_all_collection__ = True

    def __init__(self, *items: object) -> None:
        self._items = list(items)

    def __iter__(self):
        return iter(self._items)

    def __str__(self) -> str:
        return "HTMLAllCollection()"


class FakeBigInt:
    __ink_devtools_bigint__ = True

    def __init__(self, value: int) -> None:
        self.value = value

    def __str__(self) -> str:
        return str(self.value)


class FakeUnknown:
    __ink_devtools_unknown__ = True

    def __init__(self, preview: str) -> None:
        self.__ink_devtools_unknown_preview__ = preview


def test_inject_into_devtools_registers_renderer_metadata_and_tree_snapshot() -> None:
    class Greeting(_Component):
        def render(self):
            return Text(f"Hello {self.props['name']}")

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(createElement(Greeting, name="Ink"), stdout=stdout, stdin=stdin, debug=True)
    try:
        app.wait_until_render_flush(timeout=0.2)

        with patch("pyinkcli.packages.react_devtools_core.backend.initializeBackend", return_value=True):
            assert app._reconciler.injectIntoDevTools() is True

        global_scope = builtins.__dict__["__INK_DEVTOOLS_GLOBAL__"]
        renderer = global_scope["__INK_RECONCILER_DEVTOOLS_METADATA__"]
        snapshot = renderer["getTreeSnapshot"]()
        nodes_by_name = {}
        for node in snapshot["nodes"]:
            nodes_by_name.setdefault(node["displayName"], []).append(node)

        assert renderer["bundleType"] == 1
        assert renderer["rendererPackageName"] == "pyinkcli"
        assert renderer["version"] == renderer["reconcilerVersion"]
        assert renderer["rendererConfig"]["supportsClassComponents"] is True
        assert renderer["rendererConfig"]["supportsErrorBoundaries"] is True
        assert renderer["rendererConfig"]["supportsCommitPhaseErrorRecovery"] is True
        assert snapshot["rootID"] == "root"
        assert renderer["getDisplayNameForNode"]("root") == "Root"
        assert "InternalApp" in nodes_by_name
        assert "InternalErrorBoundary" in nodes_by_name
        assert "Greeting" in nodes_by_name
        assert nodes_by_name["InternalApp"][0]["elementType"] == "function"
        assert nodes_by_name["InternalErrorBoundary"][0]["isErrorBoundary"] is True
        assert nodes_by_name["Greeting"][0]["elementType"] == "class"
    finally:
        app.unmount()


def test_devtools_window_polyfill_exposes_renderer_registry_and_filters() -> None:
    global_scope = builtins.__dict__["__INK_DEVTOOLS_GLOBAL__"]
    filters = global_scope["__REACT_DEVTOOLS_COMPONENT_FILTERS__"]

    assert isinstance(global_scope["__INK_DEVTOOLS_RENDERERS__"], dict)
    assert any(entry["value"] == "InternalApp" for entry in filters if entry["type"] == 2)
    assert any(entry["value"] == "InternalFocusContext" for entry in filters if entry["type"] == 2)


def test_devtools_override_props_and_schedule_update_rerenders_function_component() -> None:
    def EditableLabel(*, value: str):
        return Text(value)

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(createElement(EditableLabel, value="before"), stdout=stdout, stdin=stdin, debug=True)
    try:
        app.wait_until_render_flush(timeout=0.2)

        with patch("pyinkcli.packages.react_devtools_core.backend.initializeBackend", return_value=True):
            app._reconciler.injectIntoDevTools()

        global_scope = builtins.__dict__["__INK_DEVTOOLS_GLOBAL__"]
        renderer = global_scope["__INK_RECONCILER_DEVTOOLS_METADATA__"]
        snapshot = renderer["getTreeSnapshot"]()
        label_node = next(node for node in snapshot["nodes"] if node["displayName"] == "EditableLabel")

        assert renderer["overrideProps"](label_node["id"], ["value"], "after") is True
        assert renderer["scheduleUpdate"](label_node["id"]) is True
        app.wait_until_render_flush(timeout=0.2)

        assert stdout.getvalue().endswith("after")
    finally:
        app.unmount()


def test_devtools_can_rename_and_delete_props_before_scheduling_update() -> None:
    def FlexibleLabel(**props):
        value = props.get("value", props.get("label", "missing"))
        return Text(value)

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(createElement(FlexibleLabel, label="alpha"), stdout=stdout, stdin=stdin, debug=True)
    try:
        app.wait_until_render_flush(timeout=0.2)

        with patch("pyinkcli.packages.react_devtools_core.backend.initializeBackend", return_value=True):
            app._reconciler.injectIntoDevTools()

        global_scope = builtins.__dict__["__INK_DEVTOOLS_GLOBAL__"]
        renderer = global_scope["__INK_RECONCILER_DEVTOOLS_METADATA__"]
        snapshot = renderer["getTreeSnapshot"]()
        label_node = next(node for node in snapshot["nodes"] if node["displayName"] == "FlexibleLabel")

        assert renderer["overridePropsRenamePath"](label_node["id"], ["label"], ["value"]) is True
        assert renderer["scheduleUpdate"](label_node["id"]) is True
        app.wait_until_render_flush(timeout=0.2)
        assert stdout.getvalue().endswith("alpha")

        assert renderer["overridePropsDeletePath"](label_node["id"], ["value"]) is True
        assert renderer["scheduleUpdate"](label_node["id"]) is True
        app.wait_until_render_flush(timeout=0.2)
        assert stdout.getvalue().endswith("missing")
    finally:
        app.unmount()


def test_devtools_override_hook_state_and_schedule_update_rerenders_hooks_component() -> None:
    def Counter():
        count, _ = useState(1)
        return Text(f"count:{count}")

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(createElement(Counter), stdout=stdout, stdin=stdin, debug=True)
    try:
        app.wait_until_render_flush(timeout=0.2)

        with patch("pyinkcli.packages.react_devtools_core.backend.initializeBackend", return_value=True):
            app._reconciler.injectIntoDevTools()

        global_scope = builtins.__dict__["__INK_DEVTOOLS_GLOBAL__"]
        renderer = global_scope["__INK_RECONCILER_DEVTOOLS_METADATA__"]
        snapshot = renderer["getTreeSnapshot"]()
        counter_node = next(node for node in snapshot["nodes"] if node["displayName"] == "Counter")

        assert renderer["overrideHookState"](counter_node["id"], [0], 5) is True
        assert renderer["scheduleUpdate"](counter_node["id"]) is True
        app.wait_until_render_flush(timeout=0.2)

        assert stdout.getvalue().endswith("count:5")
    finally:
        app.unmount()


def test_devtools_can_rename_and_delete_nested_hook_state_paths() -> None:
    def Counter():
        state, _ = useState({"label": "alpha"})
        return Text(state.get("value", state.get("label", "missing")))

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(createElement(Counter), stdout=stdout, stdin=stdin, debug=True)
    try:
        app.wait_until_render_flush(timeout=0.2)

        with patch("pyinkcli.packages.react_devtools_core.backend.initializeBackend", return_value=True):
            app._reconciler.injectIntoDevTools()

        global_scope = builtins.__dict__["__INK_DEVTOOLS_GLOBAL__"]
        renderer = global_scope["__INK_RECONCILER_DEVTOOLS_METADATA__"]
        snapshot = renderer["getTreeSnapshot"]()
        counter_node = next(node for node in snapshot["nodes"] if node["displayName"] == "Counter")

        assert renderer["overrideHookStateRenamePath"](counter_node["id"], [0, "label"], [0, "value"]) is True
        assert renderer["scheduleUpdate"](counter_node["id"]) is True
        app.wait_until_render_flush(timeout=0.2)
        assert stdout.getvalue().endswith("alpha")

        assert renderer["overrideHookStateDeletePath"](counter_node["id"], [0, "value"]) is True
        assert renderer["scheduleUpdate"](counter_node["id"]) is True
        app.wait_until_render_flush(timeout=0.2)
        assert stdout.getvalue().endswith("missing")
    finally:
        app.unmount()


def test_devtools_schedule_retry_rerenders_suspense_boundary() -> None:
    resolved = {"value": False}

    def MaybeSuspend():
        if not resolved["value"]:
            raise SuspendSignal("manual-devtools-retry")
        return Text("ready")

    def Suspense(*children, fallback=None):
        return createElement("__ink-suspense__", *children, fallback=fallback)

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(
        createElement(
            Suspense,
            createElement(MaybeSuspend),
            fallback=createElement(Text, "loading"),
        ),
        stdout=stdout,
        stdin=stdin,
        debug=True,
    )
    try:
        app.wait_until_render_flush(timeout=0.2)

        with patch("pyinkcli.packages.react_devtools_core.backend.initializeBackend", return_value=True):
            app._reconciler.injectIntoDevTools()

        global_scope = builtins.__dict__["__INK_DEVTOOLS_GLOBAL__"]
        renderer = global_scope["__INK_RECONCILER_DEVTOOLS_METADATA__"]
        snapshot = renderer["getTreeSnapshot"]()
        suspense_node = next(node for node in snapshot["nodes"] if node["displayName"] == "Suspense")

        resolved["value"] = True
        assert renderer["scheduleRetry"](suspense_node["id"]) is True
        app.wait_until_render_flush(timeout=0.2)

        assert stdout.getvalue().endswith("ready")
    finally:
        app.unmount()


def test_devtools_inspect_element_returns_props_state_and_hooks_payloads() -> None:
    class Greeting(_Component):
        def __init__(self, **props):
            super().__init__(**props)
            self.state = {"prefix": "Hello"}

        def render(self):
            return Text(f"{self.state['prefix']} {self.props['name']}")

    def Counter():
        count, _ = useState(3)
        return Text(f"count:{count}")

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(
        createElement(
            "ink-box",
            createElement(Greeting, name="Ink"),
            createElement(Counter),
        ),
        stdout=stdout,
        stdin=stdin,
        debug=True,
    )
    try:
        app.wait_until_render_flush(timeout=0.2)

        with patch("pyinkcli.packages.react_devtools_core.backend.initializeBackend", return_value=True):
            app._reconciler.injectIntoDevTools()

        global_scope = builtins.__dict__["__INK_DEVTOOLS_GLOBAL__"]
        renderer = global_scope["__INK_RECONCILER_DEVTOOLS_METADATA__"]
        snapshot = renderer["getTreeSnapshot"]()
        greeting_node = next(node for node in snapshot["nodes"] if node["displayName"] == "Greeting")
        counter_node = next(node for node in snapshot["nodes"] if node["displayName"] == "Counter")

        greeting_payload = renderer["inspectElement"](1, greeting_node["id"], {}, True)
        counter_payload = renderer["inspectElement"](2, counter_node["id"], {}, True)

        assert greeting_payload["type"] == "full-data"
        assert greeting_payload["value"]["props"]["data"]["name"] == "Ink"
        assert greeting_payload["value"]["state"]["data"] == {"prefix": "Hello"}
        assert greeting_payload["value"]["canEditFunctionProps"] is False

        assert counter_payload["type"] == "full-data"
        assert counter_payload["value"]["hooks"]["data"][0]["name"] == "State"
        assert counter_payload["value"]["hooks"]["data"][0]["value"] == 3
        assert counter_payload["value"]["canEditHooks"] is True

        assert renderer["getSerializedElementValueByPath"](greeting_node["id"], ["props", "name"]) == "\"Ink\""
        assert renderer["getSerializedElementValueByPath"](counter_node["id"], ["hooks", 0, "value"]) == "3"
    finally:
        app.unmount()


def test_devtools_can_edit_class_state_via_generic_value_path_api() -> None:
    class StatefulLabel(_Component):
        def __init__(self, **props):
            super().__init__(**props)
            self.state = {
                "count": 1,
                "label": "alpha",
            }

        def render(self):
            value = self.state.get("value", self.state.get("label", "missing"))
            return Text(f"count:{self.state['count']} value:{value}")

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(createElement(StatefulLabel), stdout=stdout, stdin=stdin, debug=True)
    try:
        app.wait_until_render_flush(timeout=0.2)

        with patch("pyinkcli.packages.react_devtools_core.backend.initializeBackend", return_value=True):
            app._reconciler.injectIntoDevTools()

        global_scope = builtins.__dict__["__INK_DEVTOOLS_GLOBAL__"]
        renderer = global_scope["__INK_RECONCILER_DEVTOOLS_METADATA__"]
        snapshot = renderer["getTreeSnapshot"]()
        stateful_node = next(
            node for node in snapshot["nodes"] if node["displayName"] == "StatefulLabel"
        )

        assert renderer["overrideValueAtPath"]("state", stateful_node["id"], None, ["count"], 7) is True
        assert renderer["scheduleUpdate"](stateful_node["id"]) is True
        app.wait_until_render_flush(timeout=0.2)
        assert stdout.getvalue().endswith("count:7 value:alpha")

        assert renderer["renamePath"](
            "state",
            stateful_node["id"],
            None,
            ["label"],
            ["value"],
        ) is True
        assert renderer["scheduleUpdate"](stateful_node["id"]) is True
        app.wait_until_render_flush(timeout=0.2)
        assert stdout.getvalue().endswith("count:7 value:alpha")

        assert renderer["deletePath"]("state", stateful_node["id"], None, ["value"]) is True
        assert renderer["scheduleUpdate"](stateful_node["id"]) is True
        app.wait_until_render_flush(timeout=0.2)
        assert stdout.getvalue().endswith("count:7 value:missing")
    finally:
        app.unmount()


def test_devtools_override_suspense_uses_nearest_boundary_from_selected_child() -> None:
    def Label():
        return Text("ready")

    def Suspense(*children, fallback=None):
        return createElement("__ink-suspense__", *children, fallback=fallback)

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(
        createElement(
            Suspense,
            createElement(Label),
            fallback=createElement(Text, "loading"),
        ),
        stdout=stdout,
        stdin=stdin,
        debug=True,
    )
    try:
        app.wait_until_render_flush(timeout=0.2)

        with patch("pyinkcli.packages.react_devtools_core.backend.initializeBackend", return_value=True):
            app._reconciler.injectIntoDevTools()

        global_scope = builtins.__dict__["__INK_DEVTOOLS_GLOBAL__"]
        renderer = global_scope["__INK_RECONCILER_DEVTOOLS_METADATA__"]
        snapshot = renderer["getTreeSnapshot"]()
        label_node = next(node for node in snapshot["nodes"] if node["displayName"] == "Label")

        inspected = renderer["inspectElement"](3, label_node["id"], {}, True)
        assert inspected["value"]["canToggleSuspense"] is True

        assert renderer["overrideSuspense"](label_node["id"], True) is True
        app.wait_until_render_flush(timeout=0.2)
        assert stdout.getvalue().endswith("loading")

        assert renderer["overrideSuspense"](label_node["id"], False) is True
        app.wait_until_render_flush(timeout=0.2)
        assert stdout.getvalue().endswith("ready")
    finally:
        app.unmount()


def test_devtools_override_error_uses_nearest_boundary_from_selected_child() -> None:
    class SimpleBoundary(_Component):
        @staticmethod
        def getDerivedStateFromError(error: Exception) -> dict[str, bool]:
            return {"failed": True}

        def __init__(self, **props):
            super().__init__(**props)
            self.state = {"failed": False}

        def render(self):
            if self.state["failed"]:
                return Text("fallback")
            return self.props.get("children")

    def Label():
        return Text("ready")

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(
        createElement(SimpleBoundary, createElement(Label)),
        stdout=stdout,
        stdin=stdin,
        debug=True,
    )
    try:
        app.wait_until_render_flush(timeout=0.2)

        with patch("pyinkcli.packages.react_devtools_core.backend.initializeBackend", return_value=True):
            app._reconciler.injectIntoDevTools()

        global_scope = builtins.__dict__["__INK_DEVTOOLS_GLOBAL__"]
        renderer = global_scope["__INK_RECONCILER_DEVTOOLS_METADATA__"]
        snapshot = renderer["getTreeSnapshot"]()
        label_node = next(node for node in snapshot["nodes"] if node["displayName"] == "Label")

        inspected = renderer["inspectElement"](4, label_node["id"], {}, True)
        assert inspected["value"]["canToggleError"] is True

        assert renderer["overrideError"](label_node["id"], True) is True
        app.wait_until_render_flush(timeout=0.2)
        assert stdout.getvalue().endswith("fallback")

        assert renderer["overrideError"](label_node["id"], False) is True
        app.wait_until_render_flush(timeout=0.2)
        assert stdout.getvalue().endswith("ready")
    finally:
        app.unmount()


def test_devtools_inspect_element_includes_owners_source_and_stack_metadata() -> None:
    class Parent(_Component):
        def render(self):
            return createElement(Child)

    def Child():
        return createElement(Leaf)

    def Leaf():
        return Text("leaf")

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(createElement(Parent), stdout=stdout, stdin=stdin, debug=True)
    try:
        app.wait_until_render_flush(timeout=0.2)

        with patch("pyinkcli.packages.react_devtools_core.backend.initializeBackend", return_value=True):
            app._reconciler.injectIntoDevTools()

        global_scope = builtins.__dict__["__INK_DEVTOOLS_GLOBAL__"]
        renderer = global_scope["__INK_RECONCILER_DEVTOOLS_METADATA__"]
        snapshot = renderer["getTreeSnapshot"]()
        leaf_node = next(node for node in snapshot["nodes"] if node["displayName"] == "Leaf")
        text_node = next(node for node in snapshot["nodes"] if node["displayName"] == "ink-text")

        leaf_payload = renderer["inspectElement"](5, leaf_node["id"], {}, True)["value"]
        text_payload = renderer["inspectElement"](6, text_node["id"], {}, True)["value"]
        source_file = str(Path(__file__).resolve())

        assert leaf_payload["source"][0] == "Leaf"
        assert leaf_payload["source"][1] == source_file
        assert leaf_payload["stack"][0][0] == "Leaf"
        assert any(frame[0] == "Child" for frame in leaf_payload["stack"])
        assert any(frame[0] == "Parent" for frame in leaf_payload["stack"])

        owner_names = [owner["displayName"] for owner in text_payload["owners"]]
        assert owner_names[:3] == ["Leaf", "Child", "Parent"]
        assert text_payload["source"][0] == "Leaf"
        assert text_payload["stack"][0][0] == "Leaf"
    finally:
        app.unmount()


def test_devtools_inspect_element_supports_no_change_and_hydrated_path_responses() -> None:
    def EditableLabel(*, value: str):
        return Text(value)

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(createElement(EditableLabel, value="before"), stdout=stdout, stdin=stdin, debug=True)
    try:
        app.wait_until_render_flush(timeout=0.2)

        with patch("pyinkcli.packages.react_devtools_core.backend.initializeBackend", return_value=True):
            app._reconciler.injectIntoDevTools()

        global_scope = builtins.__dict__["__INK_DEVTOOLS_GLOBAL__"]
        renderer = global_scope["__INK_RECONCILER_DEVTOOLS_METADATA__"]
        snapshot = renderer["getTreeSnapshot"]()
        label_node = next(node for node in snapshot["nodes"] if node["displayName"] == "EditableLabel")

        first = renderer["inspectElement"](7, label_node["id"], None, False)
        assert first["type"] == "full-data"
        assert first["value"]["props"]["data"]["value"] == "before"

        second = renderer["inspectElement"](8, label_node["id"], None, False)
        assert second["type"] == "no-change"

        third = renderer["inspectElement"](9, label_node["id"], ["props", "value"], False)
        assert third["type"] == "hydrated-path"
        assert third["path"] == ["props", "value"]
        assert third["value"]["data"] == "before"

        assert renderer["overrideProps"](label_node["id"], ["value"], "after") is True
        assert renderer["scheduleUpdate"](label_node["id"]) is True
        app.wait_until_render_flush(timeout=0.2)

        fourth = renderer["inspectElement"](10, label_node["id"], None, False)
        assert fourth["type"] == "full-data"
        assert fourth["value"]["props"]["data"]["value"] == "after"
    finally:
        app.unmount()


def test_devtools_hooks_hydration_keeps_hook_shell_but_dehydrates_nested_values() -> None:
    def Counter():
        state, _ = useState({"nested": {"label": "alpha"}})
        return Text(state["nested"]["label"])

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(createElement(Counter), stdout=stdout, stdin=stdin, debug=True)
    try:
        app.wait_until_render_flush(timeout=0.2)

        with patch("pyinkcli.packages.react_devtools_core.backend.initializeBackend", return_value=True):
            app._reconciler.injectIntoDevTools()

        global_scope = builtins.__dict__["__INK_DEVTOOLS_GLOBAL__"]
        renderer = global_scope["__INK_RECONCILER_DEVTOOLS_METADATA__"]
        snapshot = renderer["getTreeSnapshot"]()
        counter_node = next(node for node in snapshot["nodes"] if node["displayName"] == "Counter")

        initial = renderer["inspectElement"](11, counter_node["id"], None, False)
        hooks = initial["value"]["hooks"]
        hook_value = hooks["data"][0]["value"]
        assert hook_value["type"] == "object"
        assert hook_value["preview_short"] == "{…}"
        assert hook_value["preview_long"] == '{nested: {…}}'
        assert hook_value["size"] == 1
        assert hooks["cleaned"] == [[0, "value"]]

        hydrated_parent = renderer["inspectElement"](12, counter_node["id"], ["hooks", 0, "value"], False)
        assert hydrated_parent["type"] == "hydrated-path"
        assert hydrated_parent["value"]["data"]["nested"]["type"] == "object"
        assert hydrated_parent["value"]["cleaned"] == [["hooks", 0, "value", "nested"]]

        hydrated_leaf = renderer["inspectElement"](
            13,
            counter_node["id"],
            ["hooks", 0, "value", "nested", "label"],
            False,
        )
        assert hydrated_leaf["type"] == "hydrated-path"
        assert hydrated_leaf["value"]["data"] == "alpha"
        assert hydrated_leaf["value"]["cleaned"] == []
    finally:
        app.unmount()


def test_devtools_suspended_by_hydration_preserves_meta_and_dehydrates_deep_values() -> None:
    def MaybeSuspend():
        raise SuspendSignal("resource-alpha")

    def Suspense(*children, fallback=None):
        return createElement("__ink-suspense__", *children, fallback=fallback)

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(
        createElement(
            Suspense,
            createElement(MaybeSuspend),
            fallback=createElement(Text, "loading"),
        ),
        stdout=stdout,
        stdin=stdin,
        debug=True,
    )
    try:
        app.wait_until_render_flush(timeout=0.2)

        with patch("pyinkcli.packages.react_devtools_core.backend.initializeBackend", return_value=True):
            app._reconciler.injectIntoDevTools()

        global_scope = builtins.__dict__["__INK_DEVTOOLS_GLOBAL__"]
        renderer = global_scope["__INK_RECONCILER_DEVTOOLS_METADATA__"]
        snapshot = renderer["getTreeSnapshot"]()
        suspense_node = next(node for node in snapshot["nodes"] if node["displayName"] == "Suspense")

        inspected = renderer["inspectElement"](14, suspense_node["id"], None, False)
        suspended_by = inspected["value"]["suspendedBy"]
        assert suspended_by["data"][0]["awaited"]["value"]["resource"]["type"] == "object"
        assert [0, "awaited", "value", "resource"] in suspended_by["cleaned"]

        hydrated = renderer["inspectElement"](
            15,
            suspense_node["id"],
            ["suspendedBy", 0, "awaited", "value", "resource", "key"],
            False,
        )
        assert hydrated["type"] == "hydrated-path"
        assert hydrated["value"]["data"] == "'resource-alpha'"
    finally:
        app.unmount()


def test_devtools_special_number_values_use_cleaned_transport_placeholders() -> None:
    def Carrier(**props):
        return Text("ok")

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(
        createElement(
            Carrier,
            infinite=float("inf"),
            not_a_number=float("nan"),
        ),
        stdout=stdout,
        stdin=stdin,
        debug=True,
    )
    try:
        app.wait_until_render_flush(timeout=0.2)

        with patch("pyinkcli.packages.react_devtools_core.backend.initializeBackend", return_value=True):
            app._reconciler.injectIntoDevTools()

        renderer = builtins.__dict__["__INK_DEVTOOLS_GLOBAL__"]["__INK_RECONCILER_DEVTOOLS_METADATA__"]
        snapshot = renderer["getTreeSnapshot"]()
        carrier_node = next(node for node in snapshot["nodes"] if node["displayName"] == "Carrier")

        inspected = renderer["inspectElement"](16, carrier_node["id"], None, False)
        props = inspected["value"]["props"]

        assert ["infinite"] in props["cleaned"]
        assert ["not_a_number"] in props["cleaned"]
        assert props["data"]["infinite"] == {"type": "infinity"}
        assert props["data"]["not_a_number"] == {"type": "nan"}
    finally:
        app.unmount()


def test_devtools_date_regexp_symbol_and_iterator_preview_metadata_matches_transport_types() -> None:
    class Marker(enum.Enum):
        READY = "ready"

    def Carrier(**props):
        return Text("ok")

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(
        createElement(
            Carrier,
            today=datetime_module.date(2024, 1, 2),
            pattern=re.compile(r"ab+c"),
            marker=Marker.READY,
            mapping=OrderedDict([("first", 1), ("second", 2)]),
        ),
        stdout=stdout,
        stdin=stdin,
        debug=True,
    )
    try:
        app.wait_until_render_flush(timeout=0.2)

        with patch("pyinkcli.packages.react_devtools_core.backend.initializeBackend", return_value=True):
            app._reconciler.injectIntoDevTools()

        renderer = builtins.__dict__["__INK_DEVTOOLS_GLOBAL__"]["__INK_RECONCILER_DEVTOOLS_METADATA__"]
        snapshot = renderer["getTreeSnapshot"]()
        carrier_node = next(node for node in snapshot["nodes"] if node["displayName"] == "Carrier")

        inspected = renderer["inspectElement"](17, carrier_node["id"], None, False)
        props = inspected["value"]["props"]["data"]

        assert props["today"]["preview_short"] == "2024-01-02"
        assert props["today"]["type"] == "date"
        assert props["pattern"]["type"] == "regexp"
        assert "ab+c" in props["pattern"]["preview_short"]
        assert props["marker"]["type"] == "symbol"
        assert props["marker"]["preview_short"] == "Marker.READY"
        assert props["mapping"]["type"] == "iterator"
        assert props["mapping"]["preview_short"] == "OrderedDict(2)"
        assert '"first"' in props["mapping"]["preview_long"]
    finally:
        app.unmount()


def test_devtools_typed_array_data_view_array_buffer_thenable_and_lazy_previews() -> None:
    def Carrier(**props):
        return Text("ok")

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(
        createElement(
            Carrier,
            numbers=array_module.array("i", [1, 2, 3]),
            raw=bytearray(b"abc"),
            view=memoryview(b"abcd"),
            pending=FakeThenable("pending"),
            fulfilled=FakeThenable("fulfilled", value="done"),
            lazy=FakeLazy(FakeLazyPayload("fulfilled", value="ready")),
        ),
        stdout=stdout,
        stdin=stdin,
        debug=True,
    )
    try:
        app.wait_until_render_flush(timeout=0.2)

        with patch("pyinkcli.packages.react_devtools_core.backend.initializeBackend", return_value=True):
            app._reconciler.injectIntoDevTools()

        renderer = builtins.__dict__["__INK_DEVTOOLS_GLOBAL__"]["__INK_RECONCILER_DEVTOOLS_METADATA__"]
        snapshot = renderer["getTreeSnapshot"]()
        carrier_node = next(node for node in snapshot["nodes"] if node["displayName"] == "Carrier")

        inspected = renderer["inspectElement"](18, carrier_node["id"], None, False)
        props = inspected["value"]["props"]["data"]

        assert props["numbers"]["type"] == "typed_array"
        assert props["numbers"]["preview_short"] == "array(3)"
        assert props["raw"]["type"] == "array_buffer"
        assert props["raw"]["preview_short"] == "ArrayBuffer(3)"
        assert props["view"]["type"] == "data_view"
        assert props["view"]["preview_short"] == "DataView(4)"
        assert props["pending"]["type"] == "thenable"
        assert props["pending"]["preview_short"] == "pending FakeThenable"
        assert props["fulfilled"]["type"] == "thenable"
        assert props["fulfilled"]["preview_short"] == "fulfilled FakeThenable {…}"
        assert props["lazy"]["type"] == "react_lazy"
        assert props["lazy"]["preview_short"] == "fulfilled lazy() {…}"
    finally:
        app.unmount()


def test_devtools_tail_marker_type_and_legacy_lazy_previews_match_transport_types() -> None:
    class ModuleNamespace:
        def __init__(self, default: object) -> None:
            self.default = default

    def Carrier(**props):
        return Text("ok")

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(
        createElement(
            Carrier,
            element=FakeHtmlElement("DIV"),
            collection=FakeHtmlAllCollection("a", "b"),
            bigint=FakeBigInt(123),
            unknown=FakeUnknown("boom"),
            legacy_lazy=FakeLazy(FakeLegacyLazyPayload(1, ModuleNamespace("ready"))),
            resolved_model=FakeThenable("resolved_model"),
        ),
        stdout=stdout,
        stdin=stdin,
        debug=True,
    )
    try:
        app.wait_until_render_flush(timeout=0.2)

        with patch("pyinkcli.packages.react_devtools_core.backend.initializeBackend", return_value=True):
            app._reconciler.injectIntoDevTools()

        renderer = builtins.__dict__["__INK_DEVTOOLS_GLOBAL__"]["__INK_RECONCILER_DEVTOOLS_METADATA__"]
        snapshot = renderer["getTreeSnapshot"]()
        carrier_node = next(node for node in snapshot["nodes"] if node["displayName"] == "Carrier")

        inspected = renderer["inspectElement"](19, carrier_node["id"], None, False)
        props = inspected["value"]["props"]["data"]

        assert props["element"]["type"] == "html_element"
        assert props["element"]["preview_short"] == "<div />"
        assert props["collection"]["type"] == "html_all_collection"
        assert props["collection"]["readonly"] is True
        assert props["bigint"]["type"] == "bigint"
        assert props["bigint"]["preview_short"] == "123n"
        assert props["unknown"]["type"] == "unknown"
        assert props["unknown"]["preview_short"] == "[Exception]"
        assert props["legacy_lazy"]["type"] == "react_lazy"
        assert props["legacy_lazy"]["preview_short"] == "fulfilled lazy() {…}"
        assert props["resolved_model"]["type"] == "thenable"
        assert props["resolved_model"]["preview_short"] == "FakeThenable"
    finally:
        app.unmount()


def test_devtools_backend_facade_dispatches_inspect_and_edit_requests() -> None:
    def EditableLabel(*, value: str):
        return Text(value)

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(createElement(EditableLabel, value="before"), stdout=stdout, stdin=stdin, debug=True)
    try:
        app.wait_until_render_flush(timeout=0.2)

        with patch("pyinkcli.packages.react_devtools_core.backend.initializeBackend", return_value=True):
            app._reconciler.injectIntoDevTools()

        renderer = builtins.__dict__["__INK_DEVTOOLS_GLOBAL__"]["__INK_RECONCILER_DEVTOOLS_METADATA__"]
        backend = renderer["backend"]
        snapshot = renderer["getTreeSnapshot"]()
        label_node = next(node for node in snapshot["nodes"] if node["displayName"] == "EditableLabel")

        inspect_element_response = backend["dispatchBridgeMessage"](
            make_bridge_call(
                "inspectElement",
                {
                    "id": label_node["id"],
                    "rendererID": id(app._reconciler),
                    "forceFullData": True,
                },
            )
        )
        assert inspect_element_response["type"] == "response"
        assert inspect_element_response["event"] == "inspectedElement"
        assert inspect_element_response["payload"]["ok"] is True
        assert inspect_element_response["payload"]["type"] == "full-data"
        assert inspect_element_response["payload"]["value"]["props"]["data"]["value"] == "before"

        inspect_screen_response = backend["dispatchBridgeMessage"](
            make_bridge_call(
                "inspectScreen",
                {
                    "id": renderer["getRootID"](),
                    "forceFullData": True,
                },
            )
        )
        assert inspect_screen_response["event"] == "inspectedScreen"
        assert inspect_screen_response["payload"]["ok"] is True
        assert inspect_screen_response["payload"]["id"] == "root"

        override_response = backend["dispatchBridgeMessage"](
            make_bridge_call(
                "overrideValueAtPath",
                {
                    "id": label_node["id"],
                    "valueType": "props",
                    "path": ["value"],
                    "value": "after",
                },
            )
        )
        assert override_response["event"] == "overrideValueAtPath"
        assert override_response["payload"]["ok"] is True
        assert override_response["payload"]["value"] is True

        update_response = backend["dispatchBridgeMessage"](
            make_bridge_call(
                "scheduleUpdate",
                {
                    "id": label_node["id"],
                },
            )
        )
        assert update_response["event"] == "scheduleUpdate"
        assert update_response["payload"]["ok"] is True
        assert update_response["payload"]["value"] is True
        app.wait_until_render_flush(timeout=0.2)

        assert stdout.getvalue().endswith("after")
    finally:
        app.unmount()


def test_devtools_backend_facade_dispatches_backend_notifications_to_reconciler() -> None:
    def Carrier(*, value: str):
        return Text(value)

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(createElement(Carrier, value="alpha"), stdout=stdout, stdin=stdin, debug=True)
    try:
        app.wait_until_render_flush(timeout=0.2)

        with patch("pyinkcli.packages.react_devtools_core.backend.initializeBackend", return_value=True):
            app._reconciler.injectIntoDevTools()

        global_scope = builtins.__dict__["__INK_DEVTOOLS_GLOBAL__"]
        renderer = global_scope["__INK_RECONCILER_DEVTOOLS_METADATA__"]
        backend = renderer["backend"]
        snapshot = renderer["getTreeSnapshot"]()
        carrier_node = next(node for node in snapshot["nodes"] if node["displayName"] == "Carrier")
        renderer_id = id(app._reconciler)

        backend["dispatchBridgeMessage"](
            make_bridge_notification(
                "copyElementPath",
                {
                    "rendererID": renderer_id,
                    "id": carrier_node["id"],
                    "path": ["props", "value"],
                },
            )
        )
        assert renderer["getLastCopiedValue"]() == '"alpha"'
        assert global_scope["__INK_DEVTOOLS_LAST_COPIED_VALUE__"] == '"alpha"'

        backend["dispatchBridgeMessage"](
            make_bridge_notification(
                "storeAsGlobal",
                {
                    "rendererID": renderer_id,
                    "id": carrier_node["id"],
                    "path": ["props", "value"],
                    "count": 5,
                },
            )
        )
        assert renderer["getStoredGlobals"]()["$reactTemp5"] == "alpha"
        assert global_scope["$reactTemp5"] == "alpha"

        backend["dispatchBridgeMessage"](
            make_bridge_notification(
                "clearErrorsAndWarnings",
                {
                    "rendererID": renderer_id,
                },
            )
        )
        backend["dispatchBridgeMessage"](
            make_bridge_notification(
                "clearWarningsForElementID",
                {
                    "rendererID": renderer_id,
                    "id": carrier_node["id"],
                },
            )
        )

        events = [entry["event"] for entry in renderer["getBackendNotificationLog"]()]
        assert events == [
            "copyElementPath",
            "storeAsGlobal",
            "clearErrorsAndWarnings",
            "clearWarningsForElementID",
        ]
        assert backend["backendState"]["lastNotification"]["event"] == "clearWarningsForElementID"
    finally:
        app.unmount()


def test_devtools_backend_facade_supports_legacy_override_message_types() -> None:
    class StatefulLabel(_Component):
        def __init__(self, **props):
            super().__init__(**props)
            self.state = {"label": "alpha"}

        def render(self):
            return Text(f"{self.props['value']}|{self.state['label']}")

    def Counter():
        state, _ = useState({"count": 1})
        return Text(f"count:{state['count']}")

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(
        createElement(
            "ink-box",
            createElement(StatefulLabel, value="before"),
            createElement(Counter),
        ),
        stdout=stdout,
        stdin=stdin,
        debug=True,
    )
    try:
        app.wait_until_render_flush(timeout=0.2)

        with patch("pyinkcli.packages.react_devtools_core.backend.initializeBackend", return_value=True):
            app._reconciler.injectIntoDevTools()

        renderer = builtins.__dict__["__INK_DEVTOOLS_GLOBAL__"]["__INK_RECONCILER_DEVTOOLS_METADATA__"]
        backend = renderer["backend"]
        snapshot = renderer["getTreeSnapshot"]()
        stateful_node = next(node for node in snapshot["nodes"] if node["displayName"] == "StatefulLabel")
        counter_node = next(node for node in snapshot["nodes"] if node["displayName"] == "Counter")

        props_response = backend["dispatchBridgeMessage"](
            make_bridge_call(
                "overrideProps",
                {
                    "id": stateful_node["id"],
                    "path": ["value"],
                    "value": "after",
                },
            )
        )
        hook_response = backend["dispatchBridgeMessage"](
            make_bridge_call(
                "overrideHookState",
                {
                    "id": counter_node["id"],
                    "hookID": 0,
                    "path": ["count"],
                    "value": 5,
                },
            )
        )
        state_response = backend["dispatchBridgeMessage"](
            make_bridge_call(
                "overrideState",
                {
                    "id": stateful_node["id"],
                    "path": ["label"],
                    "value": "omega",
                },
            )
        )

        assert props_response["payload"]["ok"] is True
        assert props_response["payload"]["value"] is True
        assert hook_response["payload"]["ok"] is True
        assert hook_response["payload"]["value"] is True
        assert state_response["payload"]["ok"] is True
        assert state_response["payload"]["value"] is True

        backend["dispatchBridgeMessage"](make_bridge_call("scheduleUpdate", {"id": stateful_node["id"]}))
        backend["dispatchBridgeMessage"](make_bridge_call("scheduleUpdate", {"id": counter_node["id"]}))
        app.wait_until_render_flush(timeout=0.2)

        assert stdout.getvalue().endswith("after|omega\ncount:5")

        skipped_response = backend["dispatchBridgeMessage"](
            make_bridge_call(
                "overrideProps",
                {
                    "id": stateful_node["id"],
                    "path": ["value"],
                    "value": "ignored",
                    "wasForwarded": True,
                },
            )
        )
        assert skipped_response["payload"]["ok"] is True
        assert skipped_response["payload"]["value"] is False

        backend["dispatchBridgeMessage"](make_bridge_call("scheduleUpdate", {"id": stateful_node["id"]}))
        app.wait_until_render_flush(timeout=0.2)
        assert stdout.getvalue().endswith("after|omega\ncount:5")
    finally:
        app.unmount()


def test_devtools_backend_facade_supports_override_suspense_milestone_notifications() -> None:
    def Suspense(*children, fallback=None):
        return createElement("__ink-suspense__", *children, fallback=fallback)

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(
        createElement(
            "ink-box",
            createElement(
                Suspense,
                createElement(Text, "A"),
                fallback=createElement(Text, "loading-a"),
            ),
            createElement(Text, "|"),
            createElement(
                Suspense,
                createElement(Text, "B"),
                fallback=createElement(Text, "loading-b"),
            ),
        ),
        stdout=stdout,
        stdin=stdin,
        debug=True,
    )
    try:
        app.wait_until_render_flush(timeout=0.2)

        with patch("pyinkcli.packages.react_devtools_core.backend.initializeBackend", return_value=True):
            app._reconciler.injectIntoDevTools()

        global_scope = builtins.__dict__["__INK_DEVTOOLS_GLOBAL__"]
        renderer = global_scope["__INK_RECONCILER_DEVTOOLS_METADATA__"]
        backend = renderer["backend"]
        snapshot = renderer["getTreeSnapshot"]()
        suspense_nodes = [node for node in snapshot["nodes"] if node["displayName"] == "Suspense"]
        renderer_id = id(app._reconciler)

        backend["dispatchBridgeMessage"](
            make_bridge_notification(
                "overrideSuspenseMilestone",
                {
                    "rendererID": renderer_id,
                    "suspendedSet": [suspense_nodes[0]["id"]],
                },
            )
        )
        app.wait_until_render_flush(timeout=0.2)
        assert stdout.getvalue().endswith("loading-a\n|\nB")

        backend["dispatchBridgeMessage"](
            make_bridge_notification(
                "overrideSuspenseMilestone",
                {
                    "rendererID": renderer_id,
                    "suspendedSet": [suspense_nodes[1]["id"]],
                },
            )
        )
        app.wait_until_render_flush(timeout=0.2)
        assert stdout.getvalue().endswith("A\n|\nloading-b")

        backend["dispatchBridgeMessage"](
            make_bridge_notification(
                "overrideSuspenseMilestone",
                {
                    "rendererID": renderer_id,
                    "suspendedSet": [],
                },
            )
        )
        app.wait_until_render_flush(timeout=0.2)
        assert stdout.getvalue().endswith("A\n|\nB")

        log = renderer["getBackendNotificationLog"]()
        assert log[-1]["event"] == "overrideSuspenseMilestone"
        assert log[-1]["suspendedSet"] == []
        assert backend["backendState"]["lastNotification"]["event"] == "overrideSuspenseMilestone"
    finally:
        app.unmount()


def test_devtools_backend_facade_inspect_screen_merges_roots_across_renderers() -> None:
    def MaybeSuspendAlpha():
        raise SuspendSignal("alpha-resource")

    def MaybeSuspendBeta():
        raise SuspendSignal("beta-resource")

    def Suspense(*children, fallback=None):
        return createElement("__ink-suspense__", *children, fallback=fallback)

    stdout_a = FakeStdout()
    stdin_a = FakeStdin()
    app_a = render(
        createElement(
            Suspense,
            createElement(MaybeSuspendAlpha),
            fallback=createElement(Text, "loading-a"),
        ),
        stdout=stdout_a,
        stdin=stdin_a,
        debug=True,
    )
    stdout_b = FakeStdout()
    stdin_b = FakeStdin()
    app_b = render(
        createElement(
            Suspense,
            createElement(MaybeSuspendBeta),
            fallback=createElement(Text, "loading-b"),
        ),
        stdout=stdout_b,
        stdin=stdin_b,
        debug=True,
    )
    try:
        app_a.wait_until_render_flush(timeout=0.2)
        app_b.wait_until_render_flush(timeout=0.2)

        with patch("pyinkcli.packages.react_devtools_core.backend.initializeBackend", return_value=True):
            app_a._reconciler.injectIntoDevTools()
            app_b._reconciler.injectIntoDevTools()

        global_scope = builtins.__dict__["__INK_DEVTOOLS_GLOBAL__"]
        renderer_a = global_scope["__INK_RECONCILER_DEVTOOLS_METADATA__"]
        backend = renderer_a["backend"]
        original_renderers = dict(global_scope["__INK_DEVTOOLS_RENDERERS__"])
        global_scope["__INK_DEVTOOLS_RENDERERS__"] = {
            id(app_a._reconciler): original_renderers[id(app_a._reconciler)],
            id(app_b._reconciler): original_renderers[id(app_b._reconciler)],
        }
        try:
            response = backend["dispatchBridgeMessage"](
                make_bridge_call(
                    "inspectScreen",
                    {
                        "id": renderer_a["getRootID"](),
                        "forceFullData": True,
                    },
                )
            )
            assert response["event"] == "inspectedScreen"
            assert response["payload"]["ok"] is True
            assert response["payload"]["type"] == "full-data"
            suspended_by = response["payload"]["value"]["suspendedBy"]
            assert len(suspended_by["data"]) == 2

            hydrated = backend["dispatchBridgeMessage"](
                make_bridge_call(
                    "inspectScreen",
                    {
                        "id": renderer_a["getRootID"](),
                        "path": ["suspendedBy", 1, "awaited", "value", "resource", "key"],
                    },
                )
            )
            assert hydrated["event"] == "inspectedScreen"
            assert hydrated["payload"]["ok"] is True
            assert hydrated["payload"]["type"] == "hydrated-path"
            assert hydrated["payload"]["path"] == ["suspendedBy", 1, "awaited", "value", "resource", "key"]
            assert hydrated["payload"]["value"]["data"] == "'beta-resource'"
        finally:
            global_scope["__INK_DEVTOOLS_RENDERERS__"] = original_renderers
    finally:
        app_a.unmount()
        app_b.unmount()


def test_devtools_backend_facade_exposes_agent_style_methods() -> None:
    def EditableLabel(*, value: str):
        return Text(value)

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(createElement(EditableLabel, value="before"), stdout=stdout, stdin=stdin, debug=True)
    try:
        app.wait_until_render_flush(timeout=0.2)

        with patch("pyinkcli.packages.react_devtools_core.backend.initializeBackend", return_value=True):
            app._reconciler.injectIntoDevTools()

        global_scope = builtins.__dict__["__INK_DEVTOOLS_GLOBAL__"]
        renderer = global_scope["__INK_RECONCILER_DEVTOOLS_METADATA__"]
        backend = renderer["backend"]
        snapshot = renderer["getTreeSnapshot"]()
        label_node = next(node for node in snapshot["nodes"] if node["displayName"] == "EditableLabel")
        renderer_id = id(app._reconciler)

        inspect_response = backend["inspectElement"](
            {
                "id": label_node["id"],
                "rendererID": renderer_id,
                "requestID": 41,
                "forceFullData": True,
            }
        )
        assert inspect_response["event"] == "inspectedElement"
        assert inspect_response["requestId"] == 41
        assert inspect_response["payload"]["ok"] is True
        assert inspect_response["payload"]["value"]["props"]["data"]["value"] == "before"

        override_response = backend["overrideProps"](
            {
                "id": label_node["id"],
                "rendererID": renderer_id,
                "path": ["value"],
                "value": "after",
            }
        )
        assert override_response["event"] == "overrideProps"
        assert override_response["payload"]["ok"] is True
        assert override_response["payload"]["value"] is True

        backend["scheduleUpdate"]({"id": label_node["id"], "rendererID": renderer_id})
        app.wait_until_render_flush(timeout=0.2)
        assert stdout.getvalue().endswith("after")

        notification_result = backend["copyElementPath"](
            {
                "rendererID": renderer_id,
                "id": label_node["id"],
                "path": ["props", "value"],
            }
        )
        assert notification_result is None
        assert renderer["getLastCopiedValue"]() == '"after"'
        assert backend["backendState"]["lastNotification"]["event"] == "copyElementPath"
    finally:
        app.unmount()


def test_devtools_backend_facade_exposes_agent_metadata_and_logging_methods() -> None:
    class Parent(_Component):
        def render(self):
            return createElement(Child)

    def Child():
        return Text("leaf")

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(createElement(Parent), stdout=stdout, stdin=stdin, debug=True)
    try:
        app.wait_until_render_flush(timeout=0.2)

        with patch("pyinkcli.packages.react_devtools_core.backend.initializeBackend", return_value=True):
            app._reconciler.injectIntoDevTools()

        global_scope = builtins.__dict__["__INK_DEVTOOLS_GLOBAL__"]
        renderer = global_scope["__INK_RECONCILER_DEVTOOLS_METADATA__"]
        backend = renderer["backend"]
        snapshot = renderer["getTreeSnapshot"]()
        child_node = next(node for node in snapshot["nodes"] if node["displayName"] == "Child")
        text_node = next(node for node in snapshot["nodes"] if node["displayName"] == "ink-text")
        renderer_id = id(app._reconciler)

        owners_response = backend["getOwnersList"](
            {
                "id": text_node["id"],
                "rendererID": renderer_id,
                "requestID": 51,
            }
        )
        assert owners_response["event"] == "ownersList"
        assert owners_response["requestId"] == 51
        assert owners_response["payload"]["ok"] is True
        assert [owner["displayName"] for owner in owners_response["payload"]["owners"]][:2] == [
            "Child",
            "Parent",
        ]

        version_response = backend["getBackendVersion"]({"requestID": 52})
        assert version_response["event"] == "backendVersion"
        assert version_response["payload"]["ok"] is True
        assert version_response["payload"]["version"] == renderer["version"]

        protocol_response = backend["getBridgeProtocol"]({"requestID": 53})
        assert protocol_response["event"] == "bridgeProtocol"
        assert protocol_response["payload"]["ok"] is True
        assert protocol_response["payload"]["bridgeProtocol"]["version"] == 2

        notification_result = backend["logElementToConsole"](
            {
                "rendererID": renderer_id,
                "id": child_node["id"],
            }
        )
        assert notification_result is None
        assert renderer["getLastLoggedElement"]()["id"] == child_node["id"]
        assert global_scope["__INK_DEVTOOLS_LAST_LOGGED_ELEMENT__"]["id"] == child_node["id"]
        assert backend["backendState"]["lastNotification"]["event"] == "logElementToConsole"
    finally:
        app.unmount()


def test_devtools_backend_facade_exposes_host_instance_and_profiling_methods() -> None:
    def Suspense(*children, fallback=None):
        return createElement("__ink-suspense__", *children, fallback=fallback)

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(
        createElement(
            Suspense,
            createElement(Text, "ready"),
            fallback=createElement(Text, "loading"),
        ),
        stdout=stdout,
        stdin=stdin,
        debug=True,
    )
    try:
        app.wait_until_render_flush(timeout=0.2)

        with patch("pyinkcli.packages.react_devtools_core.backend.initializeBackend", return_value=True):
            app._reconciler.injectIntoDevTools()

        global_scope = builtins.__dict__["__INK_DEVTOOLS_GLOBAL__"]
        renderer = global_scope["__INK_RECONCILER_DEVTOOLS_METADATA__"]
        backend = renderer["backend"]
        snapshot = renderer["getTreeSnapshot"]()
        suspense_node = next(node for node in snapshot["nodes"] if node["displayName"] == "Suspense")
        text_node = next(node for node in snapshot["nodes"] if node["displayName"] == "ink-text")
        host_instance = app._root_node.child_nodes[0]

        profiling_response = backend["getProfilingStatus"]({"requestID": 61})
        assert profiling_response["event"] == "profilingStatus"
        assert profiling_response["requestId"] == 61
        assert profiling_response["payload"]["ok"] is True
        assert profiling_response["payload"]["isProfiling"] is False

        host_match = backend["getIDForHostInstance"](host_instance)
        assert host_match == {
            "id": text_node["id"],
            "rendererID": id(app._reconciler),
        }

        suspense_match = backend["getIDForHostInstance"](host_instance, True)
        assert suspense_match == {
            "id": suspense_node["id"],
            "rendererID": id(app._reconciler),
        }

        assert backend["getComponentNameForHostInstance"](host_instance) == "ink-text"
    finally:
        app.unmount()


def test_devtools_backend_facade_exposes_profiling_and_selection_methods() -> None:
    class Parent(_Component):
        def render(self):
            return createElement(Child)

    def Child():
        return Text("leaf")

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(createElement(Parent), stdout=stdout, stdin=stdin, debug=True)
    try:
        app.wait_until_render_flush(timeout=0.2)

        with patch("pyinkcli.packages.react_devtools_core.backend.initializeBackend", return_value=True):
            app._reconciler.injectIntoDevTools()

        global_scope = builtins.__dict__["__INK_DEVTOOLS_GLOBAL__"]
        renderer = global_scope["__INK_RECONCILER_DEVTOOLS_METADATA__"]
        backend = renderer["backend"]
        snapshot = renderer["getTreeSnapshot"]()
        child_node = next(node for node in snapshot["nodes"] if node["displayName"] == "Child")

        profiling_data_response = backend["getProfilingData"]({"requestID": 71})
        assert profiling_data_response["event"] == "profilingData"
        assert profiling_data_response["payload"]["ok"] is True
        assert profiling_data_response["payload"]["rendererID"] == id(app._reconciler)
        assert profiling_data_response["payload"]["timelineData"] is None
        assert profiling_data_response["payload"]["dataForRoots"][0]["rootID"] == "root"

        path = backend["getPathForElement"](child_node["id"])
        assert path is not None
        assert path[-1]["displayName"] == "Child"

        backend["setTrackedPath"](path)
        assert renderer["getTrackedPath"]() == path

        backend["setTrackedPath"](None)
        assert renderer["getTrackedPath"]() is None

        backend["stopInspectingNative"](True)
        assert backend["backendState"]["lastStopInspectingHostSelected"] is True
        assert global_scope["__INK_DEVTOOLS_STOP_INSPECTING_HOST__"] is True
    finally:
        app.unmount()


def test_devtools_backend_facade_tracks_and_clears_persisted_selection_on_manual_inspect() -> None:
    class Parent(_Component):
        def render(self):
            return createElement(Child)

    def Child():
        return Text("leaf")

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(createElement(Parent), stdout=stdout, stdin=stdin, debug=True)
    try:
        app.wait_until_render_flush(timeout=0.2)

        with patch("pyinkcli.packages.react_devtools_core.backend.initializeBackend", return_value=True):
            app._reconciler.injectIntoDevTools()

        global_scope = builtins.__dict__["__INK_DEVTOOLS_GLOBAL__"]
        renderer = global_scope["__INK_RECONCILER_DEVTOOLS_METADATA__"]
        backend = renderer["backend"]
        snapshot = renderer["getTreeSnapshot"]()
        child_node = next(node for node in snapshot["nodes"] if node["displayName"] == "Child")
        renderer_id = id(app._reconciler)
        path = backend["getPathForElement"](child_node["id"])
        assert path is not None

        backend["setPersistedSelection"]({"rendererID": renderer_id, "path": path})
        assert backend["getPersistedSelection"]() == {
            "rendererID": renderer_id,
            "path": path,
        }
        assert renderer["getTrackedPath"]() == path

        backend["setPersistedSelectionMatch"]({"id": child_node["id"], "isFullMatch": False})
        assert backend["getPersistedSelectionMatch"]() == {
            "id": child_node["id"],
            "isFullMatch": False,
        }
        backend["inspectElement"](
            {
                "id": child_node["id"],
                "rendererID": renderer_id,
                "requestID": 81,
                "forceFullData": True,
            }
        )
        assert backend["getPersistedSelection"]() == {
            "rendererID": renderer_id,
            "path": path,
        }
        assert renderer["getTrackedPath"]() == path

        backend["setPersistedSelectionMatch"]({"id": "stale-node", "isFullMatch": False})
        inspect_response = backend["inspectElement"](
            {
                "id": child_node["id"],
                "rendererID": renderer_id,
                "requestID": 82,
                "forceFullData": True,
            }
        )
        assert inspect_response["event"] == "inspectedElement"
        assert backend["getPersistedSelection"]() is None
        assert backend["getPersistedSelectionMatch"]() is None
        assert renderer["getTrackedPath"]() is None
        assert backend["backendState"]["lastSelectedElementID"] == child_node["id"]
        assert backend["backendState"]["lastSelectedRendererID"] == renderer_id

        backend["setPersistedSelection"]({"rendererID": renderer_id, "path": path})
        backend["clearPersistedSelection"]()
        assert backend["getPersistedSelection"]() is None
        assert backend["getPersistedSelectionMatch"]() is None
        assert renderer["getTrackedPath"]() is None
    finally:
        app.unmount()
