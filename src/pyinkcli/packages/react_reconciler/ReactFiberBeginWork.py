from __future__ import annotations

from .ReactFiberNewContext import checkIfContextChanged

_did_receive_update = False


def resetWorkInProgressReceivedUpdate() -> None:
    global _did_receive_update
    _did_receive_update = False


def checkIfWorkInProgressReceivedUpdate() -> bool:
    return _did_receive_update


def beginWork(reconciler, current, work_in_progress, element, root, path, index, key):
    reconciler.update_container_sync(element, reconciler.create_container(root))
    return 1


def _mark_received_update(flag: bool) -> None:
    global _did_receive_update
    _did_receive_update = flag

