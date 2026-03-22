"""Prepared container update helpers."""

from __future__ import annotations

from types import SimpleNamespace


def commitContainerUpdate(reconciler, element, container):
    reconciler.update_container_sync(element, container)
    root_completion_state = {"tag": 3, "containsSuspendedFibers": False}
    commit_list = SimpleNamespace(
        layout_effects=[
            SimpleNamespace(tag="request_render", payload={"rootCompletionState": root_completion_state, "immediate": False}),
            SimpleNamespace(tag="root_completion_state", payload={"rootCompletionState": root_completion_state}),
        ]
    )
    prepared = SimpleNamespace(
        work_root=container,
        commit_list=commit_list,
        root_completion_state=root_completion_state,
    )
    reconciler._last_prepared_commit = prepared
    reconciler._last_root_completion_state = root_completion_state
    return prepared

