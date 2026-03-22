"""Minimal begin-work stubs."""

from __future__ import annotations

_work_in_progress_received_update = False


class SelectiveHydrationException(Exception):
    pass


def beginWork(reconciler, _current, _work_in_progress, pending_props, root, *_args, **_kwargs):
    global _work_in_progress_received_update
    _work_in_progress_received_update = False
    if reconciler is not None and hasattr(reconciler, "create_container"):
        container = reconciler.create_container(root)
        reconciler.update_container_sync(pending_props, container)
        return 1
    return None


def replayFunctionComponent(*_args, **_kwargs):
    return None


def checkIfWorkInProgressReceivedUpdate() -> bool:
    return _work_in_progress_received_update


def markWorkInProgressReceivedUpdate() -> None:
    global _work_in_progress_received_update
    _work_in_progress_received_update = True


def resetWorkInProgressReceivedUpdate() -> None:
    global _work_in_progress_received_update
    _work_in_progress_received_update = False


__all__ = [
    "SelectiveHydrationException",
    "beginWork",
    "replayFunctionComponent",
    "checkIfWorkInProgressReceivedUpdate",
    "markWorkInProgressReceivedUpdate",
    "resetWorkInProgressReceivedUpdate",
]
