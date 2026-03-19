import pyinkcli.packages.react_reconciler.constants as reconciler_constants
from pyinkcli.packages.react_dom.client import createRootNode as create_root_node_from_client
from pyinkcli.packages.react_dom.index import createRootNode as create_root_node_from_index
from pyinkcli.packages.react_dom.server import renderToString as render_to_string_from_server
from pyinkcli.packages.react_dom.static import renderToString as render_to_string_from_static
from pyinkcli.packages.react_reconciler.index import createReconciler


def test_react_dom_package_entrypoints_resolve() -> None:
    assert create_root_node_from_index is create_root_node_from_client
    assert callable(render_to_string_from_server)
    assert callable(render_to_string_from_static)


def test_react_reconciler_package_entrypoints_resolve() -> None:
    assert callable(createReconciler)
    assert hasattr(reconciler_constants, "priorityRank")
