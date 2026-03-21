"""Compatibility wrapper for `pyinkcli.packages.react_reconciler.reconciler`."""

from pyinkcli.packages.react_reconciler.reconciler import *  # noqa: F401,F403
from pyinkcli.hooks._runtime import (
    _consume_pending_rerender_priority as consumePendingRerenderPriority,
)
