"""Compatibility facade for the internal component runtime."""

from ink_python._component_runtime import (
    RenderableNode,
    component,
    createElement,
    isElement,
)

__all__ = ["createElement", "component", "isElement", "RenderableNode"]
