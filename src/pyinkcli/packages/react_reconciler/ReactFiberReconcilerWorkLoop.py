"""Work loop and commit composition methods for the reconciler."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pyinkcli.packages.react_reconciler.ReactEventPriorities import UpdatePriority
from pyinkcli.packages.react_reconciler.ReactFiberReconciler import (
    flushScheduledUpdates,
    flushSyncFromReconciler,
)
from pyinkcli.packages.react_reconciler.ReactFiberCommitWork import (
    requestHostRender as _request_host_render_impl,
)
from pyinkcli.packages.react_reconciler.ReactFiberCommitWork import (
    resetAfterCommit as _reset_after_commit,
)
from pyinkcli.packages.react_reconciler.ReactFiberRoot import ReconcilerContainer
from pyinkcli.packages.react_reconciler.ReactFiberWorkLoop import (
    batchedUpdates as _batched_updates,
)
from pyinkcli.packages.react_reconciler.ReactFiberWorkLoop import (
    discreteUpdates as _discrete_updates,
)
from pyinkcli.packages.react_reconciler.ReactFiberWorkLoop import (
    dispatchCommitRender as _dispatch_commit_render,
)
from pyinkcli.packages.react_reconciler.ReactFiberWorkLoop import (
    priorityRank,
)
from pyinkcli.packages.react_reconciler.ReactFiberWorkLoop import (
    requestUpdateLane as _request_update_lane,
)
from pyinkcli.packages.react_reconciler.ReactFiberWorkLoop import (
    requestRerender as _request_rerender,
)
from pyinkcli.packages.react_reconciler.ReactFiberWorkLoop import (
    scheduleUpdateOnFiber as _schedule_update_on_fiber,
)


class ReactFiberReconcilerWorkLoop:
    @staticmethod
    def _priority_rank(priority: UpdatePriority) -> int:
        return priorityRank(priority)

    def batched_updates(self, callback: Callable[[], Any]) -> Any:
        """Compatibility surface mirroring React reconciler batchedUpdates()."""
        return _batched_updates(callback)

    def discrete_updates(self, callback: Callable[[], Any]) -> Any:
        """Compatibility surface mirroring React reconciler discreteUpdates()."""
        return _discrete_updates(callback)

    def request_rerender(
        self,
        container: ReconcilerContainer,
        *,
        priority: UpdatePriority,
    ) -> None:
        _schedule_update_on_fiber(self, container, priority)

    def request_update_lane(self, fiber: object | None = None) -> UpdatePriority:
        return _request_update_lane(fiber)

    def schedule_update_on_fiber(
        self,
        container: ReconcilerContainer,
        lane: UpdatePriority,
    ) -> None:
        _schedule_update_on_fiber(self, container, lane)

    def flush_scheduled_updates(self) -> bool:
        return flushScheduledUpdates()

    def flush_sync_from_reconciler(self, callback: Callable[[], Any] | None = None) -> Any:
        return flushSyncFromReconciler(callback)

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
