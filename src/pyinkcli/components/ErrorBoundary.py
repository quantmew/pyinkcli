from __future__ import annotations

from .._component_runtime import _Component


class ErrorBoundary(_Component):
    def render(self):
        return self.props.get("fallback") or None


__all__ = ["ErrorBoundary"]

