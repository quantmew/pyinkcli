from __future__ import annotations

from types import SimpleNamespace

from ...reconciler import createReconciler as create_host_reconciler
from .ReactFiberCommitWork import CommitList, PreparedCommit


class _FiberReconciler:
    def __init__(self, root_node) -> None:
        self._host = create_host_reconciler(root_node)
        self._root_fiber = SimpleNamespace(tag=3)
        self._host_config = SimpleNamespace(request_render=lambda priority, immediate: None)
        self._last_prepared_commit = None
        self._last_root_completion_state = None
        self._last_root_commit_suspended = None

    def __getattr__(self, name):
        return getattr(self._host, name)

    def create_container(self, root_node, tag: int = 0):
        container = self._host.create_container(root_node, tag=tag)
        container.container = root_node
        container.current_render_lanes = 0
        container._reconciler = self
        return container

    def flush_sync_work(self, container) -> None:
        self.flush_scheduled_updates(container, getattr(container, "pending_lanes", 0), lanes=getattr(container, "pending_lanes", 0), consume_all=True)

    def flush_scheduled_updates(self, container=None, priority=None, lanes=None, *, consume_all=True) -> None:
        from . import ReactFiberWorkLoop as work_loop

        work_loop._work_in_progress_root = container
        work_loop._work_in_progress_root_render_lanes = lanes or 0
        container.current_render_lanes = lanes or 0
        element = getattr(container, "element", None)
        rendered = self._render_tree(element, priority) if hasattr(self, "_render_tree") else element
        work_loop._has_pending_commit_effects = True
        work_loop._root_with_pending_passive_effects = container
        work_loop._pending_passive_effect_lanes = lanes or 0
        if hasattr(self, "_attach_rendered_tree"):
            self._attach_rendered_tree(container)
        if rendered is not None and element is not None:
            self._host.update_container_sync(element, container)
        self._last_prepared_commit = PreparedCommit(
            work_root=container,
            commit_list=CommitList(),
            root_completion_state={"containsSuspendedFibers": False},
            passive_effect_state={
                "deferred_passive_mount_effects": 0,
                "pending_passive_unmount_fibers": 0,
                "has_deferred_passive_work": False,
                "lanes": lanes or 0,
            },
        )
        if hasattr(self, "_request_host_render"):
            self._request_host_render(container, priority)
        container.current_render_lanes = 0
        work_loop._has_pending_commit_effects = False
        work_loop._root_with_pending_passive_effects = None
        work_loop._pending_passive_effect_lanes = 0
        work_loop._work_in_progress_root = None
        work_loop._work_in_progress_root_render_lanes = 0

    def _render_tree(self, element, priority):
        return element

    def _attach_rendered_tree(self, container) -> None:
        return None

    def _request_host_render(self, container, priority) -> None:
        return None


def createReconciler(root_node):
    return _FiberReconciler(root_node)
