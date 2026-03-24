from __future__ import annotations

from typing import Any

from .dom import createNode
from .packages.react_reconciler.ReactFiberWorkLoop import flushPendingEffects
from .reconciler import createReconciler
from .renderer import render_dom


def create_root_node(width: int = 80, height: int = 24):
    root: Any = createNode("ink-root")
    root.width = width
    root.height = height
    return root


def renderToString(node, options=None, **kwargs) -> str:
    options = options or {}
    width = kwargs.get("columns", options.get("columns", 80))
    height = kwargs.get("rows", options.get("rows", 24))
    root = create_root_node(width=width, height=height)
    reconciler = createReconciler(root)
    container = reconciler.create_container(root, tag=0)
    reconciler.update_container_sync(node, container)
    output = render_dom(root, False).output
    flushPendingEffects()
    return output


__all__ = ["renderToString", "create_root_node"]
