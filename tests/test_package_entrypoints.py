import pyinkcli.packages.react_reconciler.constants as reconciler_constants
from pyinkcli.packages.react_devtools_core.standalone import DevtoolsUI
from pyinkcli.packages.react_reconciler.index import createReconciler


def test_react_reconciler_package_entrypoints_resolve() -> None:
    assert callable(createReconciler)
    assert hasattr(reconciler_constants, "priorityRank")


def test_react_devtools_core_standalone_entrypoint_resolves() -> None:
    assert hasattr(DevtoolsUI, "setContentDOMNode")
    assert hasattr(DevtoolsUI, "startServer")
    assert hasattr(DevtoolsUI, "connectToSocket")
    assert hasattr(DevtoolsUI, "canViewElementSource")
    assert hasattr(DevtoolsUI, "viewElementSource")
