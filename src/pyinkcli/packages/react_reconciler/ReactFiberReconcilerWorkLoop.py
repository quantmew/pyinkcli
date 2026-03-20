"""Work loop and commit composition methods for the reconciler."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pyinkcli.hooks._runtime import (
    _batched_updates_runtime,
    _discrete_updates_runtime,
)
from pyinkcli.packages.react_reconciler.ReactEventPriorities import UpdatePriority
from pyinkcli.packages.react_reconciler.ReactFiberCommitWork import (
    requestHostRender as _request_host_render_impl,
)
from pyinkcli.packages.react_reconciler.ReactFiberCommitWork import (
    resetAfterCommit as _reset_after_commit,
)
from pyinkcli.packages.react_reconciler.ReactFiberRoot import ReconcilerContainer
from pyinkcli.packages.react_reconciler.ReactFiberWorkLoop import (
    dispatchCommitRender as _dispatch_commit_render,
)
from pyinkcli.packages.react_reconciler.ReactFiberWorkLoop import (
    drainPendingRerenders as _drain_pending_rerenders,
)
from pyinkcli.packages.react_reconciler.ReactFiberWorkLoop import (
    priorityRank,
)
from pyinkcli.packages.react_reconciler.ReactFiberWorkLoop import (
    requestRerender as _request_rerender,
)


class ReactFiberReconcilerWorkLoop:
    @staticmethod
    def _priority_rank(priority: UpdatePriority) -> int:
        return priorityRank(priority)

    def batched_updates(self, callback: Callable[[], Any]) -> Any:
        """Compatibility surface mirroring React reconciler batchedUpdates()."""
        return _batched_updates_runtime(callback)

    def discrete_updates(self, callback: Callable[[], Any]) -> Any:
        """Compatibility surface mirroring React reconciler discreteUpdates()."""
        return _discrete_updates_runtime(callback)

    def request_rerender(
        self,
        container: ReconcilerContainer,
        *,
        priority: UpdatePriority,
    ) -> None:
        _request_rerender(self, container, priority=priority)

    def drain_pending_rerenders(
        self,
        container: ReconcilerContainer,
    ) -> None:
        _drain_pending_rerenders(self, container)

    def dispatch_commit_render(
        self,
        container: ReconcilerContainer,
    ) -> None:
        _dispatch_commit_render(self, container)

    def _after_commit(self, container: ReconcilerContainer) -> None:
        _reset_after_commit(self, container)

    def _request_host_render(
        self,
        priority: UpdatePriority,
        *,
        immediate: bool,
    ) -> None:
        _request_host_render_impl(self, priority, immediate=immediate)


__all__ = ["ReactFiberReconcilerWorkLoop"]
