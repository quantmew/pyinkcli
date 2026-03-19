"""Error boundary matching JS `components/ErrorBoundary.tsx`."""

from __future__ import annotations

from typing import Any, Optional

from pyinkcli._component_runtime import RenderableNode, _Component
from pyinkcli.components.ErrorOverview import ErrorOverview


class ErrorBoundary(_Component):
    displayName = "InternalErrorBoundary"

    def __init__(self, *, children: Any = None, onError=None, **props: Any):
        super().__init__(children=children, onError=onError, **props)
        self.state = {"error": None}

    @staticmethod
    def getDerivedStateFromError(error: Exception) -> dict[str, Exception]:
        return {"error": error}

    def componentDidCatch(self, error: Exception) -> None:
        on_error = self.props.get("onError")
        if callable(on_error):
            on_error(error)

    def render(self) -> RenderableNode:
        error = self.state.get("error")
        if isinstance(error, Exception):
            return ErrorOverview(error=error)

        return self.props.get("children")


__all__ = ["ErrorBoundary"]
