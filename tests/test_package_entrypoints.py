import pyinkcli.packages.react_reconciler.constants as reconciler_constants
from pyinkcli.packages import react
from pyinkcli.packages.react import useContext
from pyinkcli.components.Text import Text
from pyinkcli.packages.react_devtools_core import (
    connectToDevTools,
    connectWithCustomMessagingProtocol,
    initialize,
    installHook,
)
from pyinkcli.packages.react_devtools_core.standalone import DevtoolsUI
from pyinkcli.packages.react_reconciler.index import createReconciler
from pyinkcli.render_to_string import renderToString


def test_react_context_provider_round_trip() -> None:
    value_context = react.createContext("fallback")

    def Reader():
        return react.createElement(Text, useContext(value_context))

    tree = react.createElement(
        value_context.Provider,
        react.createElement(Reader),
        value="provided",
    )

    assert renderToString(tree).strip() == "provided"


def test_react_package_entrypoints_resolve() -> None:
    assert callable(react.createElement)
    assert callable(react.useState)
    assert hasattr(react, "ReactSharedInternals")


def test_react_component_type_helpers_match_js_style_shapes() -> None:
    def Sample(props):
        return Text(props["label"])

    memo_type = react.memo(Sample)
    forward_ref_type = react.forwardRef(lambda props, ref: Text(props["label"]))
    lazy_type = react.lazy(lambda: {"default": Sample})
    context = react.createContext("fallback")

    assert getattr(memo_type, "__ink_react_memo__", False) is True
    assert memo_type.type is Sample
    assert getattr(forward_ref_type, "__ink_react_forward_ref__", False) is True
    assert callable(forward_ref_type.render)
    assert getattr(lazy_type, "__ink_react_lazy__", False) is True
    assert callable(lazy_type._init)
    assert getattr(context.Provider, "__ink_react_provider__", False) is True
    assert getattr(context.Consumer, "__ink_react_consumer__", False) is True


def test_react_component_base_class_uses_updater_contract() -> None:
    calls: list[tuple[str, object]] = []

    class Updater:
        def enqueueSetState(self, public_instance, partial_state, callback=None, callerName=None):
            calls.append(("set", partial_state))

        def enqueueForceUpdate(self, public_instance, callback=None, callerName=None):
            calls.append(("force", callerName))

    instance = react.Component(updater=Updater())
    instance.setState({"value": 1})
    instance.forceUpdate()

    assert calls == [("set", {"value": 1}), ("force", "forceUpdate")]


def test_react_component_base_class_set_state_validates_partial_state() -> None:
    instance = react.Component()

    try:
        instance.setState("bad")
    except TypeError as error:
        assert "takes an object of state variables to update" in str(error)
    else:  # pragma: no cover
        raise AssertionError("expected setState validation to fail")


def test_react_context_consumer_forward_ref_and_lazy_render() -> None:
    value_context = react.createContext("fallback")
    seen_ref: dict[str, object] = {"current": None}

    def Reader(value):
        return react.createElement(Text, f"context={value}")

    Forwarded = react.forwardRef(
        lambda props, ref: react.createElement(Text, f"ref={ref is seen_ref}")
    )
    LazyText = react.lazy(lambda: {"default": lambda: react.createElement(Text, "lazy")})

    tree = react.createElement(
        react.Fragment,
        react.createElement(
            value_context.Provider,
            react.createElement(value_context.Consumer, Reader),
            value="provided",
        ),
        react.createElement(Forwarded, ref=seen_ref),
        react.createElement(LazyText),
    )

    rendered = renderToString(tree)

    assert "context=provided" in rendered
    assert "ref=True" in rendered
    assert "lazy" in rendered


def test_react_reconciler_package_entrypoints_resolve() -> None:
    assert callable(createReconciler)
    assert hasattr(reconciler_constants, "priorityRank")


def test_react_devtools_core_standalone_entrypoint_resolves() -> None:
    assert hasattr(DevtoolsUI, "setContentDOMNode")
    assert hasattr(DevtoolsUI, "startServer")
    assert hasattr(DevtoolsUI, "connectToSocket")
    assert hasattr(DevtoolsUI, "canViewElementSource")
    assert hasattr(DevtoolsUI, "viewElementSource")


def test_react_devtools_core_backend_entrypoints_resolve() -> None:
    assert callable(initialize)
    assert callable(connectToDevTools)
    assert callable(connectWithCustomMessagingProtocol)
    assert callable(installHook)
