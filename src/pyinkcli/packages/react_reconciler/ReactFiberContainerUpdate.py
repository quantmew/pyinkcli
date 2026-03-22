from __future__ import annotations

from .ReactFiberCommitWork import CommitList, PreparedCommit


def commitContainerUpdate(reconciler, element, container) -> None:
    reconciler.update_container_sync(element, container)
    root_completion_state = {"tag": 3, "containsSuspendedFibers": False}
    prepared = PreparedCommit(
        work_root=container,
        commit_list=CommitList(
            layout_effects=[
                type("Effect", (), {"tag": "request_render", "payload": {"rootCompletionState": root_completion_state, "immediate": False}})(),
                type("Effect", (), {"tag": "root_completion_state", "payload": {"rootCompletionState": root_completion_state}})(),
            ]
        ),
        root_completion_state=root_completion_state,
        passive_effect_state={
            "deferred_passive_mount_effects": 0,
            "pending_passive_unmount_fibers": 0,
            "has_deferred_passive_work": False,
            "lanes": getattr(container, "pending_lanes", 0),
        },
    )
    reconciler._last_prepared_commit = prepared
    reconciler._last_root_completion_state = root_completion_state

