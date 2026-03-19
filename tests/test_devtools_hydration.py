from __future__ import annotations

import array as array_module
import builtins
import datetime as datetime_module
import enum
import math
import re
from collections import OrderedDict
from io import StringIO
from unittest.mock import patch

import pytest

from pyinkcli import Text, render
from pyinkcli.component import createElement
from pyinkcli.packages.react_devtools_core.hydration import (
    DEVTOOLS_UNDEFINED,
    HydratedDict,
    HydratedList,
    INSPECTED_KEY,
    META_KEY,
    SerializedMutationError,
    UNSERIALIZABLE_KEY,
    apply_serialized_mutation,
    apply_serialized_mutations,
    applySerializedMutation,
    applySerializedMutations,
    copy_with_metadata,
    copyWithMetadata,
    dispatch_bridge_message,
    dispatchBridgeMessage,
    handle_bridge_call,
    handle_bridge_notification,
    handleBridgeCall,
    handleBridgeNotification,
    handle_clear_errors_and_warnings_bridge_notification,
    handle_clear_errors_for_element_bridge_notification,
    handle_clear_warnings_for_element_bridge_notification,
    handle_copy_element_path_bridge_notification,
    handle_inspect_element_bridge_call,
    handleInspectElementBridgeCall,
    handle_inspect_screen_bridge_call,
    handle_override_suspense_milestone_bridge_notification,
    handleInspectScreenBridgeCall,
    handle_serialized_mutation_bridge_call,
    handle_store_as_global_bridge_notification,
    handleClearErrorsAndWarningsBridgeNotification,
    handleClearErrorsForElementBridgeNotification,
    handleClearWarningsForElementBridgeNotification,
    handleCopyElementPathBridgeNotification,
    handleOverrideSuspenseMilestoneBridgeNotification,
    handleSerializedMutationBridgeCall,
    handleStoreAsGlobalBridgeNotification,
    make_bridge_call,
    make_bridge_notification,
    make_clear_errors_and_warnings_bridge_handler,
    make_clear_errors_for_element_bridge_handler,
    make_clear_warnings_for_element_bridge_handler,
    make_copy_element_path_bridge_handler,
    make_devtools_backend_notification_handlers,
    make_inspect_element_bridge_handler,
    make_inspect_screen_bridge_handler,
    make_override_suspense_milestone_bridge_handler,
    make_serialized_mutation_bridge_handler,
    make_store_as_global_bridge_handler,
    makeBridgeCall,
    makeBridgeErrorResponse,
    makeBridgeNotification,
    makeClearErrorsAndWarningsBridgeHandler,
    makeClearErrorsForElementBridgeHandler,
    makeClearWarningsForElementBridgeHandler,
    makeCopyElementPathBridgeHandler,
    makeDevtoolsBackendNotificationHandlers,
    makeInspectElementBridgeHandler,
    makeInspectScreenBridgeHandler,
    makeOverrideSuspenseMilestoneBridgeHandler,
    makeSerializedMutationBridgeHandler,
    makeStoreAsGlobalBridgeHandler,
    make_bridge_request,
    make_bridge_response,
    make_bridge_error_response,
    makeBridgeRequest,
    makeBridgeResponse,
    makeBridgeSuccessResponse,
    make_bridge_success_response,
    delete_in_path,
    delete_path_in_object,
    deletePathInObject,
    fill_in_path,
    fillInPath,
    getMetadata,
    get_metadata,
    get_in_object,
    getInObject,
    hasMetadata,
    has_metadata,
    hydrate_helper,
    isInspected,
    is_inspected,
    isUnserializable,
    is_unserializable,
    markInspected,
    markUnserializable,
    mark_inspected,
    mark_unserializable,
    mutate_in_path,
    mutateInPath,
    normalize_clear_errors_and_warnings_bridge_payload,
    normalize_clear_errors_for_element_bridge_payload,
    normalize_clear_warnings_for_element_bridge_payload,
    normalize_copy_element_path_bridge_payload,
    normalize_inspect_element_bridge_payload,
    normalize_inspect_screen_bridge_payload,
    normalize_override_suspense_milestone_bridge_payload,
    normalize_serialized_mutation_bridge_payload,
    normalize_store_as_global_bridge_payload,
    normalizeClearErrorsAndWarningsBridgePayload,
    normalizeClearErrorsForElementBridgePayload,
    normalizeClearWarningsForElementBridgePayload,
    normalizeCopyElementPathBridgePayload,
    normalizeInspectElementBridgePayload,
    normalizeInspectScreenBridgePayload,
    normalizeOverrideSuspenseMilestoneBridgePayload,
    normalizeSerializedMutationBridgePayload,
    normalizeStoreAsGlobalBridgePayload,
    replace_in_path,
    replaceInPath,
    replace_metadata_value,
    replaceMetadataValue,
    rename_in_path,
    rename_path_in_object,
    renamePathInObject,
    setMetadata,
    set_metadata,
    set_in_object,
    setInObject,
    serialize_serialized_mutation_error,
    serialize_serialized_mutation_outcome,
    serialize_serialized_mutation_result,
    serialize_bridge_message_envelope,
    serialize_serialized_mutation_message,
    serializeBridgeMessageEnvelope,
    serializeSerializedMutationError,
    serializeSerializedMutationMessage,
    serializeSerializedMutationOutcome,
    serializeSerializedMutationResult,
    update_in_path,
    updateInPath,
)
from pyinkcli.hooks import useState


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


def test_devtools_hydration_helper_restores_special_cleaned_values() -> None:
    hydrated = hydrate_helper(
        {
            "data": {
                "infinite": {"type": "infinity"},
                "not_a_number": {"type": "nan"},
                "missing": {"type": "undefined"},
            },
            "cleaned": [["infinite"], ["not_a_number"], ["missing"]],
            "unserializable": [],
        }
    )

    assert hydrated["infinite"] == float("inf")
    assert math.isnan(hydrated["not_a_number"])
    assert hydrated["missing"] is DEVTOOLS_UNDEFINED


def test_devtools_hydration_helper_upgrades_unserializable_transport_metadata() -> None:
    def Carrier(**props):
        return Text("ok")

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(
        createElement(
            Carrier,
            fallback=createElement(Text, "loading"),
            failure=ValueError("bad"),
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

        inspected = renderer["inspectElement"](1, carrier_node["id"], None, False)
        props_transport = inspected["value"]["props"]

        assert ["fallback"] in props_transport["unserializable"]
        assert ["failure"] in props_transport["unserializable"]
        assert props_transport["data"]["fallback"]["type"] == "react_element"
        assert props_transport["data"]["fallback"]["readonly"] is True
        assert props_transport["data"]["fallback"]["props"]["type"] == "object"
        assert props_transport["data"]["failure"]["type"] == "error"
        assert props_transport["data"]["failure"]["readonly"] is True
        assert props_transport["data"]["failure"]["message"] == "bad"
        assert "ValueError: bad" in props_transport["data"]["failure"]["stack"]

        hydrated_props = hydrate_helper(props_transport)
        fallback = hydrated_props["fallback"]
        failure = hydrated_props["failure"]

        assert isinstance(fallback, HydratedDict)
        assert has_metadata(fallback) is True
        assert is_unserializable(fallback) is True
        assert get_metadata(fallback)["type"] == "react_element"
        assert get_metadata(fallback)["readonly"] is True
        assert get_metadata(fallback["props"])["type"] == "object"
        assert is_inspected(fallback) is False
        assert META_KEY not in fallback.keys()

        assert isinstance(failure, HydratedDict)
        assert is_unserializable(failure) is True
        assert get_metadata(failure)["type"] == "error"
        assert get_metadata(failure)["readonly"] is True
        assert failure["message"] == "bad"
        assert "ValueError: bad" in failure["stack"]
        assert META_KEY not in failure.keys()

        fallback_path = renderer["inspectElement"](2, carrier_node["id"], ["props", "fallback"], False)
        hydrated_fallback = hydrate_helper(fallback_path["value"], path=["props", "fallback"])
        assert is_unserializable(hydrated_fallback) is True
        assert is_inspected(hydrated_fallback) is True
        assert get_metadata(hydrated_fallback)["readonly"] is True
    finally:
        app.unmount()


def test_devtools_class_instance_transport_matches_hydration_shape() -> None:
    class Payload:
        def __init__(self) -> None:
            self.label = "alpha"
            self.values = [1, float("inf")]

    def Carrier(**props):
        return Text("ok")

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(
        createElement(
            Carrier,
            model=Payload(),
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

        inspected = renderer["inspectElement"](3, carrier_node["id"], None, False)
        props_transport = inspected["value"]["props"]
        model = props_transport["data"]["model"]

        assert ["model"] in props_transport["unserializable"]
        assert model["type"] == "class_instance"
        assert model["readonly"] is True
        assert model["name"] == "Payload"
        assert model["label"] == "alpha"
        assert model["values"]["type"] == "array"

        hydrated_props = hydrate_helper(props_transport)
        hydrated_model = hydrated_props["model"]
        assert is_unserializable(hydrated_model) is True
        assert get_metadata(hydrated_model)["type"] == "class_instance"
        assert get_metadata(hydrated_model)["readonly"] is True
        assert hydrated_model["label"] == "alpha"
        assert get_metadata(hydrated_model["values"])["type"] == "array"

        model_path = renderer["inspectElement"](4, carrier_node["id"], ["props", "model"], False)
        hydrated_model_path = hydrate_helper(model_path["value"], path=["props", "model"])
        assert is_inspected(hydrated_model_path) is True
        assert get_metadata(hydrated_model_path["values"])["type"] == "array"

        values_path = renderer["inspectElement"](5, carrier_node["id"], ["props", "model", "values"], False)
        hydrated_values_path = hydrate_helper(values_path["value"], path=["props", "model", "values"])
        assert hydrated_values_path[0] == 1
        assert hydrated_values_path[1] == float("inf")
    finally:
        app.unmount()


def test_devtools_hydration_helper_upgrades_cleaned_date_regexp_and_symbol_metadata() -> None:
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

        inspected = renderer["inspectElement"](6, carrier_node["id"], None, False)
        props_transport = inspected["value"]["props"]

        assert ["today"] in props_transport["cleaned"]
        assert ["pattern"] in props_transport["cleaned"]
        assert ["marker"] in props_transport["cleaned"]
        assert props_transport["data"]["today"]["type"] == "date"
        assert props_transport["data"]["pattern"]["type"] == "regexp"
        assert props_transport["data"]["marker"]["type"] == "symbol"

        hydrated_props = hydrate_helper(props_transport)
        assert get_metadata(hydrated_props["today"])["type"] == "date"
        assert get_metadata(hydrated_props["pattern"])["type"] == "regexp"
        assert get_metadata(hydrated_props["marker"])["type"] == "symbol"
    finally:
        app.unmount()


def test_devtools_iterator_transport_matches_set_and_map_like_shapes() -> None:
    def Carrier(**props):
        return Text("ok")

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(
        createElement(
            Carrier,
            labels={"alpha"},
            mapping=OrderedDict([("first", 1), ("second", {"nested": "x"})]),
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

        inspected = renderer["inspectElement"](7, carrier_node["id"], None, False)
        props_transport = inspected["value"]["props"]
        mapping = props_transport["data"]["mapping"]
        labels = props_transport["data"]["labels"]

        assert ["mapping"] in props_transport["unserializable"]
        assert ["labels"] in props_transport["unserializable"]
        assert mapping["type"] == "iterator"
        assert mapping["readonly"] is True
        assert mapping["size"] == 2
        assert mapping[0] == ["first", 1]
        assert mapping[1][0] == "second"
        assert mapping[1][1]["type"] == "object"
        assert labels["type"] == "iterator"
        assert labels["readonly"] is True
        assert labels["size"] == 1

        hydrated_props = hydrate_helper(props_transport)
        hydrated_mapping = hydrated_props["mapping"]
        hydrated_labels = hydrated_props["labels"]
        assert isinstance(hydrated_mapping, HydratedList)
        assert isinstance(hydrated_labels, HydratedList)
        assert is_unserializable(hydrated_mapping) is True
        assert get_metadata(hydrated_mapping)["type"] == "iterator"
        assert hydrated_mapping[0] == ["first", 1]
        assert get_metadata(hydrated_mapping[1][1])["type"] == "object"
        assert is_unserializable(hydrated_labels) is True
        assert get_metadata(hydrated_labels)["type"] == "iterator"
        assert list(hydrated_mapping) == [["first", 1], ["second", hydrated_mapping[1][1]]]
    finally:
        app.unmount()


def test_devtools_typed_array_array_buffer_and_data_view_transport_shapes() -> None:
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

        inspected = renderer["inspectElement"](8, carrier_node["id"], None, False)
        props_transport = inspected["value"]["props"]

        assert ["numbers"] in props_transport["unserializable"]
        assert ["raw"] in props_transport["cleaned"]
        assert ["view"] in props_transport["cleaned"]
        assert props_transport["data"]["numbers"]["type"] == "typed_array"
        assert props_transport["data"]["numbers"]["size"] == 3
        assert props_transport["data"]["numbers"][0] == 1
        assert props_transport["data"]["raw"]["type"] == "array_buffer"
        assert props_transport["data"]["raw"]["size"] == 3
        assert props_transport["data"]["view"]["type"] == "data_view"
        assert props_transport["data"]["view"]["size"] == 4

        hydrated_props = hydrate_helper(props_transport)
        assert is_unserializable(hydrated_props["numbers"]) is True
        assert get_metadata(hydrated_props["numbers"])["type"] == "typed_array"
        assert hydrated_props["numbers"][0] == 1
        assert get_metadata(hydrated_props["raw"])["type"] == "array_buffer"
        assert get_metadata(hydrated_props["view"])["type"] == "data_view"
    finally:
        app.unmount()


def test_devtools_thenable_and_react_lazy_transport_shapes() -> None:
    def Carrier(**props):
        return Text("ok")

    stdout = FakeStdout()
    stdin = FakeStdin()
    app = render(
        createElement(
            Carrier,
            pending=FakeThenable("pending"),
            fulfilled=FakeThenable("fulfilled", value={"label": "done"}),
            rejected=FakeThenable("rejected", reason=ValueError("boom")),
            lazy=FakeLazy(FakeLazyPayload("fulfilled", value="resolved")),
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

        inspected = renderer["inspectElement"](9, carrier_node["id"], None, False)
        props_transport = inspected["value"]["props"]
        pending = props_transport["data"]["pending"]
        fulfilled = props_transport["data"]["fulfilled"]
        rejected = props_transport["data"]["rejected"]
        lazy = props_transport["data"]["lazy"]

        assert ["pending"] in props_transport["cleaned"]
        assert ["fulfilled"] in props_transport["unserializable"]
        assert ["rejected"] in props_transport["unserializable"]
        assert ["lazy"] in props_transport["unserializable"]
        assert pending["type"] == "thenable"
        assert fulfilled["type"] == "thenable"
        assert fulfilled["value"]["type"] == "object"
        assert rejected["type"] == "thenable"
        assert rejected["reason"]["type"] == "error"
        assert lazy["type"] == "react_lazy"
        assert lazy["_payload"]["type"] == "class_instance"

        hydrated_props = hydrate_helper(props_transport)
        assert get_metadata(hydrated_props["pending"])["type"] == "thenable"
        assert is_unserializable(hydrated_props["fulfilled"]) is True
        assert get_metadata(hydrated_props["fulfilled"]["value"])["type"] == "object"
        assert get_metadata(hydrated_props["rejected"]["reason"])["type"] == "error"
        assert is_unserializable(hydrated_props["lazy"]) is True
        assert get_metadata(hydrated_props["lazy"]["_payload"])["type"] == "class_instance"
    finally:
        app.unmount()


def test_devtools_frontend_path_helpers_handle_hydrated_list_like_values() -> None:
    hydrated = hydrate_helper(
        {
            "data": {
                "items": {
                    0: "alpha",
                    1: "beta",
                    "type": "iterator",
                    "name": "Set",
                    "readonly": True,
                    "preview_short": "Set(2)",
                    "preview_long": 'Set(2) {"alpha", "beta"}',
                    "inspectable": True,
                    "size": 2,
                    "unserializable": True,
                }
            },
            "cleaned": [],
            "unserializable": [["items"]],
        }
    )

    items = hydrated["items"]
    assert isinstance(items, HydratedList)
    assert META_KEY not in hydrated.keys()
    assert has_metadata(items) is True
    assert get_metadata(items)["type"] == "iterator"

    filled = fill_in_path(hydrated, "gamma", ["items", 1])
    assert filled["items"][1] == "gamma"
    assert get_metadata(filled["items"])["type"] == "iterator"

    deleted = delete_in_path(hydrated, ["items", 0])
    assert list(deleted["items"]) == ["beta"]
    assert get_metadata(deleted["items"])["type"] == "iterator"

    renamed = rename_in_path(hydrated, ["items", 1], ["items", 0])
    assert list(renamed["items"]) == ["beta"]
    assert is_inspected(renamed["items"]) is False


def test_devtools_frontend_object_helpers_mutate_mixed_exotic_containers() -> None:
    hydrated = hydrate_helper(
        {
            "data": {
                "collection": {
                    0: "alpha",
                    1: "beta",
                    "type": "html_all_collection",
                    "name": "HTMLAllCollection",
                    "readonly": True,
                    "preview_short": "HTMLAllCollection()",
                    "preview_long": "HTMLAllCollection()",
                    "inspectable": True,
                    "unserializable": True,
                },
                "thenable": {
                    "type": "thenable",
                    "name": "fulfilled Thenable",
                    "preview_short": "fulfilled Thenable {…}",
                    "preview_long": 'fulfilled Thenable {"ready"}',
                    "inspectable": True,
                    "unserializable": True,
                    "value": {
                        "type": "object",
                        "name": "",
                        "preview_short": "{…}",
                        "preview_long": '{nested: "ready"}',
                        "inspectable": True,
                    },
                },
                "lazy": {
                    "type": "react_lazy",
                    "name": "lazy()",
                    "preview_short": "fulfilled lazy() {…}",
                    "preview_long": 'fulfilled lazy() {"ready"}',
                    "inspectable": True,
                    "unserializable": True,
                    "_payload": {
                        "type": "class_instance",
                        "name": "Payload",
                        "preview_short": "Payload",
                        "preview_long": "Payload",
                        "inspectable": True,
                        "readonly": True,
                        "unserializable": True,
                        "value": "ready",
                    },
                },
            },
            "cleaned": [["thenable", "value"]],
            "unserializable": [["collection"], ["thenable"], ["lazy"], ["lazy", "_payload"]],
        }
    )

    assert get_in_object(hydrated, ["collection", 1]) == "beta"
    assert get_metadata(getInObject(hydrated, ["thenable", "value"]))["type"] == "object"

    set_in_object(hydrated, ["collection", 0], "changed")
    setInObject(hydrated, ["lazy", "_payload", "value"], "updated")
    assert hydrated["collection"][0] == "changed"
    assert hydrated["lazy"]["_payload"]["value"] == "updated"
    assert get_metadata(hydrated["collection"])["type"] == "html_all_collection"
    assert get_metadata(hydrated["lazy"]["_payload"])["type"] == "class_instance"

    delete_path_in_object(hydrated, ["collection", 1])
    deletePathInObject(hydrated, ["lazy", "_payload", "value"])
    assert list(hydrated["collection"]) == ["changed"]
    assert "value" not in hydrated["lazy"]["_payload"].keys()
    assert get_metadata(hydrated["lazy"]["_payload"])["type"] == "class_instance"

    rename_path_in_object(hydrated, ["collection", 0], ["collection", 0])
    renamePathInObject(hydrated, ["thenable", "value"], ["thenable", "result"])
    assert hydrated["collection"][0] == "changed"
    assert "value" not in hydrated["thenable"].keys()
    assert get_metadata(hydrated["thenable"]["result"])["type"] == "object"
    assert is_unserializable(hydrated["thenable"]) is True

    refilled = fillInPath(hydrated, "done", ["thenable", "result", "nested"])
    assert refilled["thenable"]["result"]["nested"] == "done"


def test_devtools_tail_marker_types_and_legacy_lazy_payload_transport_shapes() -> None:
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

        inspected = renderer["inspectElement"](10, carrier_node["id"], None, False)
        props_transport = inspected["value"]["props"]

        assert ["element"] in props_transport["cleaned"]
        assert ["collection"] in props_transport["unserializable"]
        assert ["bigint"] in props_transport["cleaned"]
        assert ["unknown"] in props_transport["cleaned"]
        assert ["legacy_lazy"] in props_transport["unserializable"]
        assert props_transport["data"]["element"]["type"] == "html_element"
        assert props_transport["data"]["collection"]["type"] == "html_all_collection"
        assert props_transport["data"]["collection"]["readonly"] is True
        assert props_transport["data"]["collection"][0] == "a"
        assert props_transport["data"]["bigint"]["type"] == "bigint"
        assert props_transport["data"]["unknown"]["type"] == "unknown"
        assert props_transport["data"]["legacy_lazy"]["type"] == "react_lazy"
        assert props_transport["data"]["legacy_lazy"]["_payload"]["type"] == "class_instance"

        hydrated_props = hydrate_helper(props_transport)
        assert get_metadata(hydrated_props["element"])["type"] == "html_element"
        assert is_unserializable(hydrated_props["collection"]) is True
        assert get_metadata(hydrated_props["collection"])["type"] == "html_all_collection"
        assert get_metadata(hydrated_props["bigint"])["type"] == "bigint"
        assert get_metadata(hydrated_props["unknown"])["type"] == "unknown"
        assert is_unserializable(hydrated_props["legacy_lazy"]) is True
    finally:
        app.unmount()


def test_devtools_hydration_helper_can_fill_in_hydrated_paths() -> None:
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

        renderer = builtins.__dict__["__INK_DEVTOOLS_GLOBAL__"]["__INK_RECONCILER_DEVTOOLS_METADATA__"]
        snapshot = renderer["getTreeSnapshot"]()
        counter_node = next(node for node in snapshot["nodes"] if node["displayName"] == "Counter")

        full_data = renderer["inspectElement"](2, counter_node["id"], None, False)
        hooks_value = hydrate_helper(full_data["value"]["hooks"])
        assert get_metadata(hooks_value[0]["value"])["type"] == "object"
        assert full_data["value"]["hooks"]["cleaned"] == [[0, "value"]]

        hydrated_parent = renderer["inspectElement"](3, counter_node["id"], ["hooks", 0, "value"], False)
        assert hydrated_parent["value"]["cleaned"] == [["hooks", 0, "value", "nested"]]
        merged_hooks = fill_in_path(
            hooks_value,
            hydrate_helper(hydrated_parent["value"], path=["hooks", 0, "value"]),
            [0, "value"],
        )
        assert get_metadata(merged_hooks[0]["value"]["nested"])["type"] == "object"

        hydrated_leaf = renderer["inspectElement"](
            4,
            counter_node["id"],
            ["hooks", 0, "value", "nested", "label"],
            False,
        )
        merged_hooks = fill_in_path(
            merged_hooks,
            hydrate_helper(hydrated_leaf["value"], path=["hooks", 0, "value", "nested", "label"]),
            [0, "value", "nested", "label"],
        )
        assert merged_hooks[0]["value"]["nested"]["label"] == "alpha"
    finally:
        app.unmount()


def test_devtools_metadata_accessors_cover_wrapped_and_legacy_shapes() -> None:
    hydrated = hydrate_helper(
        {
            "data": {
                "value": {
                    "type": "object",
                    "name": "",
                    "preview_short": "{…}",
                    "preview_long": '{label: "ready"}',
                    "inspectable": True,
                }
            },
            "cleaned": [["value"]],
            "unserializable": [],
        }
    )

    wrapped = hydrated["value"]
    assert hasMetadata(wrapped) is True
    assert getMetadata(wrapped)["type"] == "object"
    assert isInspected(wrapped) is False
    assert isUnserializable(wrapped) is False

    set_metadata(wrapped, {"type": "object", "readonly": True})
    mark_inspected(wrapped)
    mark_unserializable(wrapped)
    assert get_metadata(wrapped)["readonly"] is True
    assert is_inspected(wrapped) is True
    assert is_unserializable(wrapped) is True

    legacy = {
        META_KEY: {"type": "legacy"},
        INSPECTED_KEY: True,
        UNSERIALIZABLE_KEY: True,
        "value": 1,
    }
    assert has_metadata(legacy) is True
    assert get_metadata(legacy) == {"type": "legacy"}
    assert is_inspected(legacy) is True
    assert is_unserializable(legacy) is True

    setMetadata(legacy, {"type": "legacy", "preview_short": "Legacy"})
    markInspected(legacy, False)
    markUnserializable(legacy, False)
    assert getMetadata(legacy)["preview_short"] == "Legacy"
    assert isInspected(legacy) is False
    assert isUnserializable(legacy) is False

    assert has_metadata({"value": 1}) is False
    assert get_metadata({"value": 1}) is None


def test_devtools_metadata_mutation_helpers_preserve_wrapper_metadata() -> None:
    hydrated = hydrate_helper(
        {
            "data": {
                "items": {
                    0: "alpha",
                    1: "beta",
                    "type": "iterator",
                    "name": "Set",
                    "readonly": True,
                    "preview_short": "Set(2)",
                    "preview_long": 'Set(2) {"alpha", "beta"}',
                    "inspectable": True,
                    "size": 2,
                    "unserializable": True,
                }
            },
            "cleaned": [],
            "unserializable": [["items"]],
        }
    )

    items = hydrated["items"]
    cloned = copy_with_metadata(items)
    assert cloned is not items
    assert isinstance(cloned, HydratedList)
    assert list(cloned) == ["alpha", "beta"]
    assert get_metadata(cloned)["type"] == "iterator"
    assert is_unserializable(cloned) is True

    cloned[0] = "changed"
    assert items[0] == "alpha"

    replaced = replace_metadata_value(items, ["gamma", "delta"])
    assert isinstance(replaced, HydratedList)
    assert list(replaced) == ["gamma", "delta"]
    assert get_metadata(replaced)["type"] == "iterator"
    assert is_unserializable(replaced) is True


def test_devtools_metadata_mutation_helpers_support_legacy_payloads() -> None:
    legacy = {
        META_KEY: {"type": "legacy", "readonly": True},
        INSPECTED_KEY: True,
        UNSERIALIZABLE_KEY: False,
        "nested": {"label": "ready"},
    }

    cloned = copyWithMetadata(legacy)
    assert cloned == legacy
    assert cloned is not legacy

    replaced = replaceMetadataValue(legacy, {"next": 1})
    assert isinstance(replaced, HydratedDict)
    assert replaced["next"] == 1
    assert getMetadata(replaced)["type"] == "legacy"
    assert getMetadata(replaced)["readonly"] is True
    assert isInspected(replaced) is True
    assert isUnserializable(replaced) is False


def test_devtools_replace_in_path_preserves_node_metadata() -> None:
    hydrated = hydrate_helper(
        {
            "data": {
                "thenable": {
                    "type": "thenable",
                    "name": "fulfilled Thenable",
                    "preview_short": "fulfilled Thenable {…}",
                    "preview_long": 'fulfilled Thenable {"ready"}',
                    "inspectable": True,
                    "unserializable": True,
                    "value": {
                        "type": "object",
                        "name": "",
                        "preview_short": "{…}",
                        "preview_long": '{nested: "ready"}',
                        "inspectable": True,
                    },
                },
            },
            "cleaned": [["thenable", "value"]],
            "unserializable": [["thenable"]],
        }
    )

    replaced = replace_in_path(hydrated, {"nested": "done", "extra": 1}, ["thenable", "value"])
    assert replaced["thenable"]["value"]["nested"] == "done"
    assert replaced["thenable"]["value"]["extra"] == 1
    assert get_metadata(replaced["thenable"]["value"])["type"] == "object"
    assert is_unserializable(replaced["thenable"]) is True
    assert "extra" not in hydrated["thenable"]["value"].keys()
    assert get_metadata(hydrated["thenable"]["value"])["type"] == "object"


def test_devtools_replace_in_path_supports_root_metadata_preserving_replace() -> None:
    hydrated = hydrate_helper(
        {
            "data": {
                0: "alpha",
                1: "beta",
                "type": "iterator",
                "name": "Set",
                "readonly": True,
                "preview_short": "Set(2)",
                "preview_long": 'Set(2) {"alpha", "beta"}',
                "inspectable": True,
                "size": 2,
                "unserializable": True,
            },
            "cleaned": [],
            "unserializable": [[]],
        }
    )

    replaced = replaceInPath(hydrated, ["gamma"], [])
    assert isinstance(replaced, HydratedList)
    assert list(replaced) == ["gamma"]
    assert getMetadata(replaced)["type"] == "iterator"
    assert isUnserializable(replaced) is True
    assert list(hydrated) == ["alpha", "beta"]


def test_devtools_update_in_path_preserves_node_metadata() -> None:
    hydrated = hydrate_helper(
        {
            "data": {
                "thenable": {
                    "type": "thenable",
                    "name": "fulfilled Thenable",
                    "preview_short": "fulfilled Thenable {…}",
                    "preview_long": 'fulfilled Thenable {"ready"}',
                    "inspectable": True,
                    "unserializable": True,
                    "value": {
                        "type": "object",
                        "name": "",
                        "preview_short": "{…}",
                        "preview_long": '{nested: "ready"}',
                        "inspectable": True,
                    },
                },
            },
            "cleaned": [["thenable", "value"]],
            "unserializable": [["thenable"]],
        }
    )

    updated = update_in_path(
        hydrated,
        ["thenable", "value"],
        lambda current: {"nested": "updated", "previous_type": get_metadata(current)["type"]},
    )
    assert updated["thenable"]["value"]["nested"] == "updated"
    assert updated["thenable"]["value"]["previous_type"] == "object"
    assert get_metadata(updated["thenable"]["value"])["type"] == "object"
    assert is_unserializable(updated["thenable"]) is True
    assert "previous_type" not in hydrated["thenable"]["value"].keys()


def test_devtools_update_in_path_supports_root_updates() -> None:
    hydrated = hydrate_helper(
        {
            "data": {
                0: "alpha",
                1: "beta",
                "type": "iterator",
                "name": "Set",
                "readonly": True,
                "preview_short": "Set(2)",
                "preview_long": 'Set(2) {"alpha", "beta"}',
                "inspectable": True,
                "size": 2,
                "unserializable": True,
            },
            "cleaned": [],
            "unserializable": [[]],
        }
    )

    updated = updateInPath(hydrated, [], lambda current: list(current) + ["gamma"])
    assert isinstance(updated, HydratedList)
    assert list(updated) == ["alpha", "beta", "gamma"]
    assert getMetadata(updated)["type"] == "iterator"
    assert isUnserializable(updated) is True
    assert list(hydrated) == ["alpha", "beta"]


def test_devtools_mutate_in_path_supports_in_place_node_mutation() -> None:
    hydrated = hydrate_helper(
        {
            "data": {
                "thenable": {
                    "type": "thenable",
                    "name": "fulfilled Thenable",
                    "preview_short": "fulfilled Thenable {…}",
                    "preview_long": 'fulfilled Thenable {"ready"}',
                    "inspectable": True,
                    "unserializable": True,
                    "value": {
                        "type": "object",
                        "name": "",
                        "preview_short": "{…}",
                        "preview_long": '{nested: "ready"}',
                        "inspectable": True,
                    },
                },
            },
            "cleaned": [["thenable", "value"]],
            "unserializable": [["thenable"]],
        }
    )

    def mutate(current):
        current["nested"] = "mutated"
        current["extra"] = get_metadata(current)["type"]
        mark_inspected(current)

    mutated = mutate_in_path(hydrated, ["thenable", "value"], mutate)
    assert mutated["thenable"]["value"]["nested"] == "mutated"
    assert mutated["thenable"]["value"]["extra"] == "object"
    assert get_metadata(mutated["thenable"]["value"])["type"] == "object"
    assert is_inspected(mutated["thenable"]["value"]) is True
    assert "extra" not in hydrated["thenable"]["value"].keys()


def test_devtools_mutate_in_path_supports_root_transactional_updates() -> None:
    hydrated = hydrate_helper(
        {
            "data": {
                0: "alpha",
                1: "beta",
                "type": "iterator",
                "name": "Set",
                "readonly": True,
                "preview_short": "Set(2)",
                "preview_long": 'Set(2) {"alpha", "beta"}',
                "inspectable": True,
                "size": 2,
                "unserializable": True,
            },
            "cleaned": [],
            "unserializable": [[]],
        }
    )

    def mutate_root(current):
        current.append("gamma")
        markInspected(current, False)

    mutated = mutateInPath(hydrated, [], mutate_root)
    assert isinstance(mutated, HydratedList)
    assert list(mutated) == ["alpha", "beta", "gamma"]
    assert getMetadata(mutated)["type"] == "iterator"
    assert isInspected(mutated) is False
    assert isUnserializable(mutated) is True
    assert list(hydrated) == ["alpha", "beta"]


def test_devtools_apply_serialized_mutation_dispatches_bridge_style_ops() -> None:
    hydrated = hydrate_helper(
        {
            "data": {
                "thenable": {
                    "type": "thenable",
                    "name": "fulfilled Thenable",
                    "preview_short": "fulfilled Thenable {…}",
                    "preview_long": 'fulfilled Thenable {"ready"}',
                    "inspectable": True,
                    "unserializable": True,
                    "value": {
                        "type": "object",
                        "name": "",
                        "preview_short": "{…}",
                        "preview_long": '{nested: "ready"}',
                        "inspectable": True,
                    },
                },
                "items": {
                    0: "alpha",
                    1: "beta",
                    "type": "iterator",
                    "name": "Set",
                    "readonly": True,
                    "preview_short": "Set(2)",
                    "preview_long": 'Set(2) {"alpha", "beta"}',
                    "inspectable": True,
                    "size": 2,
                    "unserializable": True,
                },
            },
            "cleaned": [["thenable", "value"]],
            "unserializable": [["thenable"], ["items"]],
        }
    )

    mutated = apply_serialized_mutation(
        hydrated,
        {"op": "set", "path": ["thenable", "value", "nested"], "value": "set"},
    )
    assert mutated["thenable"]["value"]["nested"] == "set"

    deleted = applySerializedMutation(mutated, {"op": "delete", "path": ["items", 1]})
    assert list(deleted["items"]) == ["alpha"]

    renamed = apply_serialized_mutation(
        deleted,
        {"op": "rename", "oldPath": ["thenable", "value", "nested"], "newPath": ["thenable", "value", "label"]},
    )
    assert renamed["thenable"]["value"]["label"] == "set"
    assert "nested" not in renamed["thenable"]["value"].keys()

    replaced = apply_serialized_mutation(
        renamed,
        {"op": "replace", "path": ["thenable", "value"], "value": {"done": True}},
    )
    assert replaced["thenable"]["value"]["done"] is True
    assert get_metadata(replaced["thenable"]["value"])["type"] == "object"

    updated = apply_serialized_mutation(
        replaced,
        {
            "op": "update",
            "path": ["thenable", "value"],
            "updater": lambda current: {"done": current["done"], "status": "updated"},
        },
    )
    assert updated["thenable"]["value"]["status"] == "updated"
    assert get_metadata(updated["thenable"]["value"])["type"] == "object"

    transactional = apply_serialized_mutation(
        updated,
        {
            "op": "mutate",
            "path": ["thenable", "value"],
            "mutator": lambda current: current.update({"tx": "ok"}),
        },
    )
    assert transactional["thenable"]["value"]["tx"] == "ok"
    assert get_metadata(transactional["thenable"]["value"])["type"] == "object"
    assert is_unserializable(transactional["thenable"]) is True


def test_devtools_apply_serialized_mutation_validates_operation_shape() -> None:
    hydrated = hydrate_helper({"data": {"value": 1}, "cleaned": [], "unserializable": []})

    with pytest.raises(ValueError, match="include an 'op'"):
        apply_serialized_mutation(hydrated, {"path": ["value"]})

    with pytest.raises(ValueError, match="non-empty path"):
        apply_serialized_mutation(hydrated, {"op": "delete", "path": []})

    with pytest.raises(TypeError, match="callable 'updater'"):
        apply_serialized_mutation(hydrated, {"op": "update", "path": ["value"], "value": 1})

    with pytest.raises(TypeError, match="callable 'mutator'"):
        apply_serialized_mutation(hydrated, {"op": "mutate", "path": ["value"], "value": 1})

    with pytest.raises(ValueError, match="Unsupported serialized mutation op"):
        apply_serialized_mutation(hydrated, {"op": "merge", "path": ["value"]})


def test_devtools_apply_serialized_mutations_is_fail_fast_by_default() -> None:
    hydrated = hydrate_helper({"data": {"value": 1}, "cleaned": [], "unserializable": []})

    with pytest.raises(SerializedMutationError, match="Serialized mutation failed at index 1") as exc_info:
        apply_serialized_mutations(
            hydrated,
            [
                {"op": "set", "path": ["value"], "value": 2},
                {"op": "merge", "path": ["value"]},
            ],
        )

    error = exc_info.value
    assert error.index == 1
    assert error.operation["op"] == "merge"
    assert isinstance(error.cause, ValueError)
    assert "Unsupported serialized mutation op" in str(error.cause)
    assert error.partial_result["mode"] == "fail-fast"
    assert error.partial_result["applied"] == 1
    assert error.partial_result["applied_indices"] == [0]
    assert error.partial_result["failed_indices"] == [1]
    assert error.partial_result["rolled_back"] is False
    assert error.partial_result["value"]["value"] == 2
    assert error.partial_result["errors"][0]["error_type"] == "ValueError"


def test_devtools_apply_serialized_mutations_supports_best_effort_mode() -> None:
    hydrated = hydrate_helper({"data": {"value": 1, "other": 2}, "cleaned": [], "unserializable": []})

    result = applySerializedMutations(
        hydrated,
        [
            {"op": "set", "path": ["value"], "value": 2},
            {"op": "merge", "path": ["value"]},
            {"op": "delete", "path": ["other"]},
        ],
        mode="best-effort",
    )

    assert result["mode"] == "best-effort"
    assert result["applied"] == 2
    assert result["applied_indices"] == [0, 2]
    assert result["failed_indices"] == [1]
    assert result["rolled_back"] is False
    assert result["value"]["value"] == 2
    assert "other" not in result["value"].keys()
    assert len(result["errors"]) == 1
    assert result["errors"][0]["index"] == 1
    assert result["errors"][0]["operation"]["op"] == "merge"
    assert result["errors"][0]["error_type"] == "ValueError"


def test_devtools_apply_serialized_mutations_preserves_sequential_metadata_updates() -> None:
    hydrated = hydrate_helper(
        {
            "data": {
                "thenable": {
                    "type": "thenable",
                    "name": "fulfilled Thenable",
                    "preview_short": "fulfilled Thenable {…}",
                    "preview_long": 'fulfilled Thenable {"ready"}',
                    "inspectable": True,
                    "unserializable": True,
                    "value": {
                        "type": "object",
                        "name": "",
                        "preview_short": "{…}",
                        "preview_long": '{nested: "ready"}',
                        "inspectable": True,
                    },
                },
            },
            "cleaned": [["thenable", "value"]],
            "unserializable": [["thenable"]],
        }
    )

    result = apply_serialized_mutations(
        hydrated,
        [
            {"op": "replace", "path": ["thenable", "value"], "value": {"step": 1}},
            {
                "op": "mutate",
                "path": ["thenable", "value"],
                "mutator": lambda current: current.update({"step": current["step"] + 1}) or mark_inspected(current),
            },
        ],
    )

    final_value = result["value"]["thenable"]["value"]
    assert result["mode"] == "fail-fast"
    assert result["applied"] == 2
    assert result["applied_indices"] == [0, 1]
    assert result["failed_indices"] == []
    assert result["rolled_back"] is False
    assert result["errors"] == []
    assert final_value["step"] == 2
    assert get_metadata(final_value)["type"] == "object"
    assert is_inspected(final_value) is True


def test_devtools_apply_serialized_mutations_supports_best_effort_rollback() -> None:
    hydrated = hydrate_helper({"data": {"value": 1, "other": 2}, "cleaned": [], "unserializable": []})

    result = apply_serialized_mutations(
        hydrated,
        [
            {"op": "set", "path": ["value"], "value": 2},
            {"op": "merge", "path": ["value"]},
            {"op": "delete", "path": ["other"]},
        ],
        mode="best-effort",
        rollback=True,
    )

    assert result["mode"] == "best-effort"
    assert result["applied"] == 2
    assert result["applied_indices"] == [0, 2]
    assert result["failed_indices"] == [1]
    assert result["rolled_back"] is True
    assert result["value"] == hydrated
    assert result["value"] is not hydrated
    assert result["value"]["value"] == 1
    assert result["value"]["other"] == 2
    assert len(result["errors"]) == 1


def test_devtools_apply_serialized_mutations_fail_fast_can_roll_back_in_partial_result() -> None:
    hydrated = hydrate_helper({"data": {"value": 1, "other": 2}, "cleaned": [], "unserializable": []})

    with pytest.raises(SerializedMutationError) as exc_info:
        apply_serialized_mutations(
            hydrated,
            [
                {"op": "set", "path": ["value"], "value": 2},
                {"op": "merge", "path": ["value"]},
                {"op": "delete", "path": ["other"]},
            ],
            rollback=True,
        )

    partial = exc_info.value.partial_result
    assert partial["mode"] == "fail-fast"
    assert partial["applied"] == 1
    assert partial["applied_indices"] == [0]
    assert partial["failed_indices"] == [1]
    assert partial["rolled_back"] is True
    assert partial["value"] == hydrated
    assert partial["value"] is not hydrated
    assert partial["errors"][0]["operation"]["op"] == "merge"


def test_devtools_apply_serialized_mutations_validates_mode() -> None:
    hydrated = hydrate_helper({"data": {"value": 1}, "cleaned": [], "unserializable": []})

    with pytest.raises(ValueError, match="Batch mutation mode"):
        apply_serialized_mutations(hydrated, [], mode="ignore")

    with pytest.raises(TypeError, match="rollback flag"):
        apply_serialized_mutations(hydrated, [], rollback="yes")


def test_devtools_serialize_serialized_mutation_result_builds_bridge_payload() -> None:
    hydrated = hydrate_helper({"data": {"value": 1}, "cleaned": [], "unserializable": []})
    result = apply_serialized_mutations(
        hydrated,
        [{"op": "set", "path": ["value"], "value": 2}],
    )

    payload = serialize_serialized_mutation_result(result)
    camel_payload = serializeSerializedMutationResult(result)

    assert payload["ok"] is True
    assert payload["failure"] is None
    assert payload["value"]["value"] == 2
    assert payload["applied_indices"] == [0]
    assert payload["failed_indices"] == []
    assert payload["rolled_back"] is False
    assert payload == camel_payload
    assert payload["value"] is not result["value"]


def test_devtools_serialize_serialized_mutation_error_builds_bridge_payload() -> None:
    hydrated = hydrate_helper({"data": {"value": 1}, "cleaned": [], "unserializable": []})

    with pytest.raises(SerializedMutationError) as exc_info:
        apply_serialized_mutations(
            hydrated,
            [
                {"op": "set", "path": ["value"], "value": 2},
                {"op": "merge", "path": ["value"]},
            ],
        )

    payload = serialize_serialized_mutation_error(exc_info.value)
    camel_payload = serializeSerializedMutationError(exc_info.value)

    assert payload["ok"] is False
    assert payload["value"]["value"] == 2
    assert payload["applied_indices"] == [0]
    assert payload["failed_indices"] == [1]
    assert payload["rolled_back"] is False
    assert payload["failure"]["index"] == 1
    assert payload["failure"]["operation"]["op"] == "merge"
    assert payload["failure"]["error_type"] == "ValueError"
    assert payload == camel_payload


def test_devtools_serialize_serialized_mutation_outcome_accepts_result_or_error() -> None:
    hydrated = hydrate_helper({"data": {"value": 1}, "cleaned": [], "unserializable": []})
    result = apply_serialized_mutations(
        hydrated,
        [{"op": "set", "path": ["value"], "value": 2}],
    )
    result_payload = serialize_serialized_mutation_outcome(result)
    assert result_payload["ok"] is True
    assert result_payload["failure"] is None

    with pytest.raises(SerializedMutationError) as exc_info:
        apply_serialized_mutations(
            hydrated,
            [{"op": "merge", "path": ["value"]}],
            rollback=True,
        )

    error_payload = serializeSerializedMutationOutcome(exc_info.value)
    assert error_payload["ok"] is False
    assert error_payload["rolled_back"] is True
    assert error_payload["failure"]["operation"]["op"] == "merge"


def test_devtools_serialize_bridge_message_envelope_wraps_payload() -> None:
    payload = {"ok": True, "value": {"count": 1}}
    message = serialize_bridge_message_envelope(
        payload,
        event="devtools:mutation",
        message_type="response",
        request_id="req-1",
    )
    camel_message = serializeBridgeMessageEnvelope(
        payload,
        event="devtools:mutation",
        message_type="response",
        request_id="req-1",
    )

    assert message["event"] == "devtools:mutation"
    assert message["type"] == "response"
    assert message["requestId"] == "req-1"
    assert message["payload"] == payload
    assert message["payload"] is not payload
    assert message == camel_message

    with pytest.raises(ValueError, match="event"):
        serialize_bridge_message_envelope(payload, event="")

    with pytest.raises(ValueError, match="type"):
        serialize_bridge_message_envelope(payload, event="x", message_type="")


def test_devtools_make_bridge_request_and_response_use_standard_types() -> None:
    request_payload = {"kind": "inspect", "path": ["props"]}
    request = make_bridge_request("devtools:inspect", request_payload)
    camel_request = makeBridgeRequest("devtools:inspect", request_payload, request_id="req-explicit")

    assert request["event"] == "devtools:inspect"
    assert request["type"] == "request"
    assert isinstance(request["requestId"], int)
    assert request["payload"] == request_payload

    assert camel_request["type"] == "request"
    assert camel_request["requestId"] == "req-explicit"

    response_payload = {"ok": True}
    response = make_bridge_response("devtools:inspect", response_payload, request_id=request["requestId"])
    camel_response = makeBridgeResponse("devtools:inspect", response_payload)

    assert response["event"] == "devtools:inspect"
    assert response["type"] == "response"
    assert response["requestId"] == request["requestId"]
    assert response["payload"] == response_payload

    assert camel_response["type"] == "response"
    assert isinstance(camel_response["requestId"], int)


def test_devtools_make_bridge_call_and_notification_distinguish_rpc_shapes() -> None:
    call_payload = {"method": "inspectElement", "params": {"id": 1}}
    call = make_bridge_call("devtools:call", call_payload)
    camel_call = makeBridgeCall("devtools:call", call_payload, request_id="call-1")

    assert call["event"] == "devtools:call"
    assert call["type"] == "request"
    assert isinstance(call["requestId"], int)
    assert call["payload"] == call_payload

    assert camel_call["type"] == "request"
    assert camel_call["requestId"] == "call-1"

    notification_payload = {"topic": "treeUpdated"}
    notification = make_bridge_notification("devtools:notify", notification_payload)
    camel_notification = makeBridgeNotification("devtools:notify", notification_payload)

    assert notification["event"] == "devtools:notify"
    assert notification["type"] == "notification"
    assert "requestId" not in notification
    assert notification["payload"] == notification_payload

    assert camel_notification["type"] == "notification"
    assert "requestId" not in camel_notification


def test_devtools_handle_bridge_call_builds_success_response() -> None:
    message = make_bridge_call(
        "devtools:inspect",
        {"id": 1},
        request_id="req-1",
    )

    response = handle_bridge_call(
        message,
        {
            "devtools:inspect": lambda payload, raw_message: {
                "inspectedId": payload["id"],
                "sourceRequest": raw_message["requestId"],
            }
        },
    )
    camel_response = handleBridgeCall(
        message,
        {"devtools:inspect": lambda payload, _raw_message: {"inspectedId": payload["id"]}},
    )

    assert response["type"] == "response"
    assert response["requestId"] == "req-1"
    assert response["payload"]["ok"] is True
    assert response["payload"]["failure"] is None
    assert response["payload"]["inspectedId"] == 1
    assert response["payload"]["sourceRequest"] == "req-1"
    assert camel_response["payload"]["inspectedId"] == 1


def test_devtools_handle_bridge_call_serializes_structured_errors() -> None:
    hydrated = hydrate_helper({"data": {"value": 1}, "cleaned": [], "unserializable": []})
    message = make_bridge_call(
        "devtools:mutation",
        {"operations": [{"op": "merge", "path": ["value"]}], "rollback": True},
        request_id=9,
    )

    def mutation_handler(payload, _message):
        return apply_serialized_mutations(
            hydrated,
            payload["operations"],
            rollback=payload.get("rollback", False),
        )

    response = handle_bridge_call(message, {"devtools:mutation": mutation_handler})
    assert response["type"] == "response"
    assert response["requestId"] == 9
    assert response["payload"]["ok"] is False
    assert response["payload"]["rolled_back"] is True
    assert response["payload"]["failure"]["error_type"] == "ValueError"


def test_devtools_handle_bridge_call_returns_lookup_error_for_unknown_event() -> None:
    message = make_bridge_call("devtools:missing", {"id": 1}, request_id="missing")
    response = handle_bridge_call(message, {})

    assert response["type"] == "response"
    assert response["requestId"] == "missing"
    assert response["payload"]["ok"] is False
    assert response["payload"]["failure"]["error_type"] == "LookupError"


def test_devtools_normalize_serialized_mutation_bridge_payload_applies_defaults() -> None:
    payload = normalize_serialized_mutation_bridge_payload(
        {"operations": [{"op": "set", "path": ["value"], "value": 2}]}
    )
    camel_payload = normalizeSerializedMutationBridgePayload(
        {"operations": [{"op": "set", "path": ["value"], "value": 2}]}
    )

    assert payload["mode"] == "fail-fast"
    assert payload["rollback"] is False
    assert payload["operations"][0]["op"] == "set"
    assert payload == camel_payload

    with pytest.raises(TypeError, match="dict"):
        normalize_serialized_mutation_bridge_payload([])

    with pytest.raises(TypeError, match="'operations' must be a list"):
        normalize_serialized_mutation_bridge_payload({"operations": {}})

    with pytest.raises(TypeError, match="dict items"):
        normalize_serialized_mutation_bridge_payload({"operations": [1]})

    with pytest.raises(TypeError, match="'mode' must be a string"):
        normalize_serialized_mutation_bridge_payload({"mode": 1})

    with pytest.raises(TypeError, match="'rollback' must be a bool"):
        normalize_serialized_mutation_bridge_payload({"rollback": "yes"})


def test_devtools_make_serialized_mutation_bridge_handler_applies_operations() -> None:
    target = hydrate_helper({"data": {"value": 1}, "cleaned": [], "unserializable": []})
    handler = make_serialized_mutation_bridge_handler(target)
    camel_handler = makeSerializedMutationBridgeHandler(lambda: target)

    result = handler({"operations": [{"op": "set", "path": ["value"], "value": 2}]}, {})
    camel_result = camel_handler({"operations": [{"op": "set", "path": ["value"], "value": 3}]}, {})

    assert result["value"]["value"] == 2
    assert result["applied_indices"] == [0]
    assert camel_result["value"]["value"] == 3


def test_devtools_handle_serialized_mutation_bridge_call_wraps_standard_response() -> None:
    target = hydrate_helper({"data": {"value": 1}, "cleaned": [], "unserializable": []})
    message = make_bridge_call(
        "devtools:mutation",
        {"operations": [{"op": "set", "path": ["value"], "value": 2}]},
        request_id=11,
    )

    response = handle_serialized_mutation_bridge_call(message, target)
    camel_response = handleSerializedMutationBridgeCall(message, lambda: target)

    assert response["type"] == "response"
    assert response["requestId"] == 11
    assert response["payload"]["ok"] is True
    assert response["payload"]["value"]["value"] == 2
    assert camel_response["payload"]["value"]["value"] == 2


def test_devtools_normalize_inspect_element_bridge_payload_aligns_request_fields() -> None:
    payload = normalize_inspect_element_bridge_payload(
        {"id": "node-1", "path": ["props", "value"], "forceFullData": True, "rendererID": 1},
        request_id=42,
    )
    camel_payload = normalizeInspectElementBridgePayload(
        {"id": "node-1", "path": ["props", "value"], "forceFullData": True, "rendererID": 1},
        request_id=42,
    )

    assert payload["id"] == "node-1"
    assert payload["path"] == ["props", "value"]
    assert payload["forceFullData"] is True
    assert payload["rendererID"] == 1
    assert payload["requestID"] == 42
    assert payload == camel_payload

    with pytest.raises(TypeError, match="dict"):
        normalize_inspect_element_bridge_payload([])

    with pytest.raises(ValueError, match="include 'id'"):
        normalize_inspect_element_bridge_payload({})

    with pytest.raises(TypeError, match="'path' must be a list or None"):
        normalize_inspect_element_bridge_payload({"id": "node", "path": {}})

    with pytest.raises(TypeError, match="'forceFullData' must be a bool"):
        normalize_inspect_element_bridge_payload({"id": "node", "forceFullData": 1})


def test_devtools_make_inspect_element_bridge_handler_calls_inspector() -> None:
    calls: list[dict[str, Any]] = []

    def inspector(request_id, node_id, path, force_full_data):
        calls.append(
            {
                "request_id": request_id,
                "node_id": node_id,
                "path": path,
                "force_full_data": force_full_data,
            }
        )
        return {"type": "full-data", "value": {"id": node_id}}

    handler = make_inspect_element_bridge_handler(inspector)
    camel_handler = makeInspectElementBridgeHandler(inspector)
    result = handler({"id": "node-1", "path": ["props"], "forceFullData": True}, {"requestId": 7})
    camel_result = camel_handler({"id": "node-2"}, {"requestId": 8})

    assert result["responseID"] == 7
    assert result["id"] == "node-1"
    assert result["type"] == "full-data"
    assert result["value"]["id"] == "node-1"
    assert camel_result["responseID"] == 8
    assert calls[0]["path"] == ["props"]
    assert calls[0]["force_full_data"] is True


def test_devtools_handle_inspect_element_bridge_call_uses_inspected_element_response_event() -> None:
    def inspector(request_id, node_id, path, force_full_data):
        return {
            "responseID": request_id,
            "id": node_id,
            "type": "hydrated-path" if path else "full-data",
            "path": path,
            "value": {"node": node_id, "force": force_full_data},
        }

    message = make_bridge_call(
        "inspectElement",
        {"id": "node-1", "path": ["props", "value"], "forceFullData": True},
        request_id=13,
    )
    response = handle_inspect_element_bridge_call(message, inspector)
    camel_response = handleInspectElementBridgeCall(message, inspector)

    assert response["event"] == "inspectedElement"
    assert response["type"] == "response"
    assert response["requestId"] == 13
    assert response["payload"]["ok"] is True
    assert response["payload"]["responseID"] == 13
    assert response["payload"]["type"] == "hydrated-path"
    assert response["payload"]["path"] == ["props", "value"]
    assert camel_response["payload"]["responseID"] == 13


def test_devtools_handle_inspect_element_bridge_call_serializes_errors() -> None:
    message = make_bridge_call(
        "inspectElement",
        {"id": "node-1"},
        request_id=14,
    )

    response = handle_inspect_element_bridge_call(
        message,
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("boom")),
    )
    assert response["event"] == "inspectedElement"
    assert response["payload"]["ok"] is False
    assert response["payload"]["failure"]["error_type"] == "ValueError"

    with pytest.raises(ValueError, match="event must be 'inspectElement'"):
        handle_inspect_element_bridge_call(
            make_bridge_call("wrongEvent", {"id": "node"}, request_id=1),
            lambda *_args: {},
        )


def test_devtools_normalize_inspect_screen_bridge_payload_aligns_request_fields() -> None:
    payload = normalize_inspect_screen_bridge_payload(
        {"id": "root-1", "path": ["screen"], "forceFullData": True},
        request_id=21,
    )
    camel_payload = normalizeInspectScreenBridgePayload(
        {"id": "root-1", "path": ["screen"], "forceFullData": True},
        request_id=21,
    )

    assert payload["id"] == "root-1"
    assert payload["path"] == ["screen"]
    assert payload["forceFullData"] is True
    assert payload["rendererID"] is None
    assert payload["requestID"] == 21
    assert payload == camel_payload

    with pytest.raises(TypeError, match="dict"):
        normalize_inspect_screen_bridge_payload([])

    with pytest.raises(ValueError, match="include 'id'"):
        normalize_inspect_screen_bridge_payload({})


def test_devtools_make_inspect_screen_bridge_handler_calls_inspector() -> None:
    calls: list[dict[str, Any]] = []

    def inspector(request_id, node_id, path, force_full_data):
        calls.append(
            {
                "request_id": request_id,
                "node_id": node_id,
                "path": path,
                "force_full_data": force_full_data,
            }
        )
        return {"type": "full-data", "value": {"root": node_id}}

    handler = make_inspect_screen_bridge_handler(inspector)
    camel_handler = makeInspectScreenBridgeHandler(inspector)
    result = handler({"id": "root-1", "path": ["screen"]}, {"requestId": 22})
    camel_result = camel_handler({"id": "root-2"}, {"requestId": 23})

    assert result["responseID"] == 22
    assert result["id"] == "root-1"
    assert result["type"] == "full-data"
    assert result["value"]["root"] == "root-1"
    assert camel_result["responseID"] == 23
    assert calls[0]["path"] == ["screen"]


def test_devtools_handle_inspect_screen_bridge_call_uses_inspected_screen_response_event() -> None:
    def inspector(request_id, node_id, path, force_full_data):
        return {
            "responseID": request_id,
            "id": node_id,
            "type": "hydrated-path" if path else "full-data",
            "path": path,
            "value": {"root": node_id, "force": force_full_data},
        }

    message = make_bridge_call(
        "inspectScreen",
        {"id": "root-1", "path": ["screen"], "forceFullData": True},
        request_id=24,
    )
    response = handle_inspect_screen_bridge_call(message, inspector)
    camel_response = handleInspectScreenBridgeCall(message, inspector)

    assert response["event"] == "inspectedScreen"
    assert response["type"] == "response"
    assert response["requestId"] == 24
    assert response["payload"]["ok"] is True
    assert response["payload"]["responseID"] == 24
    assert response["payload"]["type"] == "hydrated-path"
    assert response["payload"]["path"] == ["screen"]
    assert camel_response["payload"]["responseID"] == 24


def test_devtools_notification_payload_normalizers_align_backend_events() -> None:
    clear_payload = normalize_clear_errors_and_warnings_bridge_payload({"rendererID": 1})
    camel_clear_payload = normalizeClearErrorsAndWarningsBridgePayload({"rendererID": 1})
    assert clear_payload == {"rendererID": 1}
    assert clear_payload == camel_clear_payload

    copy_payload = normalize_copy_element_path_bridge_payload(
        {"rendererID": 1, "id": "node-1", "path": ["props", "value"]}
    )
    camel_copy_payload = normalizeCopyElementPathBridgePayload(
        {"rendererID": 1, "id": "node-1", "path": ["props", "value"]}
    )
    assert copy_payload["path"] == ["props", "value"]
    assert copy_payload == camel_copy_payload

    store_payload = normalize_store_as_global_bridge_payload(
        {"rendererID": 1, "id": "node-1", "path": ["props"], "count": 0}
    )
    camel_store_payload = normalizeStoreAsGlobalBridgePayload(
        {"rendererID": 1, "id": "node-1", "path": ["props"], "count": 0}
    )
    assert store_payload["count"] == 0
    assert store_payload == camel_store_payload

    milestone_payload = normalize_override_suspense_milestone_bridge_payload(
        {"rendererID": 1, "suspendedSet": ["suspense-a", "suspense-b"]}
    )
    camel_milestone_payload = normalizeOverrideSuspenseMilestoneBridgePayload(
        {"rendererID": 1, "suspendedSet": ["suspense-a", "suspense-b"]}
    )
    assert milestone_payload["suspendedSet"] == ["suspense-a", "suspense-b"]
    assert milestone_payload == camel_milestone_payload

    with pytest.raises(ValueError, match="rendererID"):
        normalize_clear_errors_for_element_bridge_payload({"id": "node-1"})

    with pytest.raises(TypeError, match="'path' must be a list"):
        normalize_copy_element_path_bridge_payload({"rendererID": 1, "id": "node-1", "path": "bad"})

    with pytest.raises(TypeError, match="'suspendedSet' must be a list"):
        normalize_override_suspense_milestone_bridge_payload({"rendererID": 1, "suspendedSet": "bad"})


def test_devtools_notification_handler_factories_and_direct_helpers_normalize_payloads() -> None:
    received: list[tuple[str, dict[str, Any], dict[str, Any]]] = []

    def recorder(label):
        return lambda payload, message: received.append((label, payload, message))

    clear_handler = make_clear_errors_and_warnings_bridge_handler(recorder("clear-all"))
    camel_clear_handler = makeClearErrorsAndWarningsBridgeHandler(recorder("clear-all-camel"))
    clear_handler({"rendererID": 1}, {"type": "notification", "event": "clearErrorsAndWarnings"})
    camel_clear_handler({"rendererID": 2}, {"type": "notification", "event": "clearErrorsAndWarnings"})

    copy_message = make_bridge_notification(
        "copyElementPath",
        {"rendererID": 1, "id": "node-1", "path": ["props", "value"]},
    )
    handle_copy_element_path_bridge_notification(copy_message, recorder("copy"))
    handleCopyElementPathBridgeNotification(copy_message, recorder("copy-camel"))

    store_message = make_bridge_notification(
        "storeAsGlobal",
        {"rendererID": 1, "id": "node-1", "path": ["props"], "count": 3},
    )
    handle_store_as_global_bridge_notification(store_message, recorder("store"))
    handleStoreAsGlobalBridgeNotification(store_message, recorder("store-camel"))

    milestone_handler = make_override_suspense_milestone_bridge_handler(recorder("milestone"))
    camel_milestone_handler = makeOverrideSuspenseMilestoneBridgeHandler(recorder("milestone-camel"))
    milestone_handler(
        {"rendererID": 1, "suspendedSet": ["suspense-a"]},
        {"type": "notification", "event": "overrideSuspenseMilestone"},
    )
    camel_milestone_handler(
        {"rendererID": 2, "suspendedSet": ["suspense-b"]},
        {"type": "notification", "event": "overrideSuspenseMilestone"},
    )
    milestone_message = make_bridge_notification(
        "overrideSuspenseMilestone",
        {"rendererID": 3, "suspendedSet": ["suspense-c"]},
    )
    handle_override_suspense_milestone_bridge_notification(milestone_message, recorder("milestone-direct"))
    handleOverrideSuspenseMilestoneBridgeNotification(milestone_message, recorder("milestone-direct-camel"))

    assert received[0][1] == {"rendererID": 1}
    assert received[1][1] == {"rendererID": 2}
    assert received[2][1]["path"] == ["props", "value"]
    assert received[4][1]["count"] == 3
    assert received[6][1]["suspendedSet"] == ["suspense-a"]
    assert received[7][1]["suspendedSet"] == ["suspense-b"]
    assert received[8][1]["suspendedSet"] == ["suspense-c"]
    assert received[9][1]["suspendedSet"] == ["suspense-c"]

    with pytest.raises(ValueError, match="type='notification'"):
        handle_bridge_notification(
            {"type": "request", "event": "copyElementPath", "payload": {}},
            recorder("bad"),
            event="copyElementPath",
            normalizer=normalize_copy_element_path_bridge_payload,
        )


def test_devtools_make_devtools_backend_notification_handlers_builds_backend_event_map() -> None:
    received: list[str] = []
    handlers = make_devtools_backend_notification_handlers(
        clear_errors_and_warnings=lambda payload, _message: received.append(f"clear:{payload['rendererID']}"),
        clear_errors_for_element=lambda payload, _message: received.append(f"clear-element:{payload['id']}"),
        clear_warnings_for_element=lambda payload, _message: received.append(f"warn-element:{payload['id']}"),
        copy_element_path=lambda payload, _message: received.append(f"copy:{'.'.join(str(part) for part in payload['path'])}"),
        store_as_global=lambda payload, _message: received.append(f"store:{payload['count']}"),
        override_suspense_milestone=lambda payload, _message: received.append(
            f"milestone:{','.join(payload['suspendedSet'])}"
        ),
    )
    camel_handlers = makeDevtoolsBackendNotificationHandlers(
        copy_element_path=lambda payload, _message: received.append(f"camel-copy:{payload['id']}")
    )

    dispatch_bridge_message(
        make_bridge_notification("clearErrorsAndWarnings", {"rendererID": 1}),
        notification_handlers=handlers,
    )
    dispatch_bridge_message(
        make_bridge_notification("clearErrorsForElementID", {"rendererID": 1, "id": "node-1"}),
        notification_handlers=handlers,
    )
    dispatch_bridge_message(
        make_bridge_notification("clearWarningsForElementID", {"rendererID": 1, "id": "node-2"}),
        notification_handlers=handlers,
    )
    dispatch_bridge_message(
        make_bridge_notification("copyElementPath", {"rendererID": 1, "id": "node-3", "path": ["props"]}),
        notification_handlers=handlers,
    )
    dispatch_bridge_message(
        make_bridge_notification("storeAsGlobal", {"rendererID": 1, "id": "node-4", "path": ["state"], "count": 5}),
        notification_handlers=handlers,
    )
    dispatch_bridge_message(
        make_bridge_notification(
            "overrideSuspenseMilestone",
            {"rendererID": 1, "suspendedSet": ["node-6", "node-7"]},
        ),
        notification_handlers=handlers,
    )
    dispatchBridgeMessage(
        make_bridge_notification("copyElementPath", {"rendererID": 1, "id": "node-5", "path": ["hooks"]}),
        notification_handlers=camel_handlers,
    )

    assert received == [
        "clear:1",
        "clear-element:node-1",
        "warn-element:node-2",
        "copy:props",
        "store:5",
        "milestone:node-6,node-7",
        "camel-copy:node-5",
    ]
def test_devtools_handle_bridge_call_validates_request_shape() -> None:
    with pytest.raises(TypeError, match="dict"):
        handle_bridge_call([], {})

    with pytest.raises(ValueError, match="type='request'"):
        handle_bridge_call({"type": "notification", "event": "x", "payload": {}}, {})

    with pytest.raises(ValueError, match="event"):
        handle_bridge_call({"type": "request", "payload": {}, "requestId": 1}, {})

    with pytest.raises(ValueError, match="requestId"):
        handle_bridge_call({"type": "request", "event": "x", "payload": {}}, {})

    with pytest.raises(TypeError, match="payload"):
        handle_bridge_call({"type": "request", "event": "x", "payload": 1, "requestId": 1}, {})


def test_devtools_dispatch_bridge_message_routes_request_and_notification() -> None:
    request = make_bridge_call("devtools:inspect", {"id": 2}, request_id=2)
    request_response = dispatch_bridge_message(
        request,
        call_handlers={"devtools:inspect": lambda payload, _message: {"inspectedId": payload["id"]}},
    )
    assert request_response["payload"]["ok"] is True
    assert request_response["payload"]["inspectedId"] == 2

    notifications: list[tuple[dict[str, Any], dict[str, Any]]] = []
    notification = make_bridge_notification("devtools:notify", {"topic": "treeUpdated"})
    notification_result = dispatchBridgeMessage(
        notification,
        notification_handlers={
            "devtools:notify": lambda payload, raw_message: notifications.append((payload, raw_message))
        },
    )
    assert notification_result is None
    assert notifications[0][0]["topic"] == "treeUpdated"
    assert notifications[0][1]["type"] == "notification"

    assert dispatch_bridge_message(notification, notification_handlers={}) is None

    with pytest.raises(ValueError, match="request' or 'notification"):
        dispatch_bridge_message({"type": "response", "event": "x", "payload": {}})


def test_devtools_make_bridge_success_and_error_response_normalize_rpc_payload() -> None:
    success = make_bridge_success_response(
        "devtools:mutation",
        {"value": {"count": 1}, "applied": 1},
        request_id="req-1",
    )
    camel_success = makeBridgeSuccessResponse(
        "devtools:mutation",
        {"value": {"count": 1}, "applied": 1},
        request_id="req-1",
    )
    assert success["type"] == "response"
    assert success["requestId"] == "req-1"
    assert success["payload"]["ok"] is True
    assert success["payload"]["failure"] is None
    assert success["payload"]["applied"] == 1
    assert success == camel_success

    failure = {"index": 1, "error_type": "ValueError", "error_message": "boom"}
    error = make_bridge_error_response(
        "devtools:mutation",
        failure,
        {"value": {"count": 0}, "applied": 0},
        request_id="req-2",
    )
    camel_error = makeBridgeErrorResponse(
        "devtools:mutation",
        failure,
        {"value": {"count": 0}, "applied": 0},
        request_id="req-2",
    )
    assert error["type"] == "response"
    assert error["requestId"] == "req-2"
    assert error["payload"]["ok"] is False
    assert error["payload"]["failure"] == failure
    assert error["payload"]["value"]["count"] == 0
    assert error == camel_error


def test_devtools_serialize_serialized_mutation_message_wraps_outcome_payload() -> None:
    hydrated = hydrate_helper({"data": {"value": 1}, "cleaned": [], "unserializable": []})
    result = apply_serialized_mutations(
        hydrated,
        [{"op": "set", "path": ["value"], "value": 2}],
    )

    result_message = serialize_serialized_mutation_message(
        result,
        event="devtools:mutation-result",
        request_id=7,
    )
    assert result_message["event"] == "devtools:mutation-result"
    assert result_message["type"] == "response"
    assert result_message["requestId"] == 7
    assert result_message["payload"]["ok"] is True
    assert result_message["payload"]["failure"] is None
    assert result_message["payload"]["value"]["value"] == 2

    with pytest.raises(SerializedMutationError) as exc_info:
        apply_serialized_mutations(
            hydrated,
            [{"op": "merge", "path": ["value"]}],
            rollback=True,
        )

    error_message = serializeSerializedMutationMessage(
        exc_info.value,
        event="devtools:mutation-result",
        request_id=8,
    )
    assert error_message["event"] == "devtools:mutation-result"
    assert error_message["type"] == "response"
    assert error_message["requestId"] == 8
    assert error_message["payload"]["ok"] is False
    assert error_message["payload"]["failure"]["error_type"] == "ValueError"
    assert error_message["payload"]["failure"]["operation"]["op"] == "merge"
