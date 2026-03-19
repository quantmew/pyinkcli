"""Facade class for the React-aligned pyinkcli reconciler."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pyinkcli.packages.ink.dom import DOMElement
from pyinkcli.packages.react_reconciler.ReactFiberReconcilerClassComponent import (
    ReactFiberReconcilerClassComponent,
)
from pyinkcli.packages.react_reconciler.ReactFiberReconcilerDevTools import (
    ReactFiberReconcilerDevTools,
)
from pyinkcli.packages.react_reconciler.ReactFiberReconcilerMutation import (
    ReactFiberReconcilerMutation,
)
from pyinkcli.packages.react_reconciler.ReactFiberReconcilerRoot import (
    ReactFiberReconcilerRoot,
)
from pyinkcli.packages.react_reconciler.ReactFiberReconcilerState import (
    initializeReconcilerState as _initialize_reconciler_state,
)
from pyinkcli.packages.react_reconciler.ReactFiberReconcilerWorkLoop import (
    ReactFiberReconcilerWorkLoop,
)

if TYPE_CHECKING:
    pass


class _Reconciler(
    ReactFiberReconcilerDevTools,
    ReactFiberReconcilerMutation,
    ReactFiberReconcilerClassComponent,
    ReactFiberReconcilerRoot,
    ReactFiberReconcilerWorkLoop,
):
    """
    Custom reconciler for rendering components to the terminal DOM.

    Similar to React's reconciler but adapted for terminal output.
    """

    def __init__(self, root_node: DOMElement):
        _initialize_reconciler_state(self, root_node)


__all__ = ["_Reconciler"]
