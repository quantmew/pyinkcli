"""DevTools reconciler composition layer."""

from __future__ import annotations

from pyinkcli.packages.react_reconciler.ReactFiberDevToolsHook import (
    injectIntoDevTools as _inject_into_devtools,
)
from pyinkcli.packages.react_reconciler.ReactFiberReconciler import packageInfo
from pyinkcli.packages.react_reconciler.ReactFiberReconcilerCommands import (
    ReactFiberReconcilerCommands,
)
from pyinkcli.packages.react_reconciler.ReactFiberReconcilerInspection import (
    ReactFiberReconcilerInspection,
)


class ReactFiberReconcilerDevTools(
    ReactFiberReconcilerInspection,
    ReactFiberReconcilerCommands,
):
    def injectIntoDevTools(self) -> bool:
        """Compatibility surface mirroring the upstream reconciler object."""
        return _inject_into_devtools(self, packageInfo)


__all__ = ["ReactFiberReconcilerDevTools"]
