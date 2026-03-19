"""Server-style rendering entrypoint for the terminal renderer."""

from pyinkcli.packages.react_dom.client import createRootNode
from pyinkcli.render_to_string import create_root_node, renderToString

__all__ = ["createRootNode", "create_root_node", "renderToString"]
