"""Prepared commit effect helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CommitList:
    layout_effects: list[Any] = field(default_factory=list)


@dataclass
class PreparedCommit:
    work_root: Any
    commit_list: CommitList
    root_completion_state: dict[str, Any] | None = None


def runPreparedCommitEffects(reconciler, container, prepared: PreparedCommit) -> None:
    reconciler._last_root_completion_state = prepared.root_completion_state
    reconciler._last_root_commit_suspended = bool(
        prepared.root_completion_state and prepared.root_completion_state.get("containsSuspendedFibers")
    )
    for effect in prepared.commit_list.layout_effects:
        if effect.tag == "calculate_layout":
            calculate_layout = getattr(reconciler, "_calculate_layout", None)
            if callable(calculate_layout):
                calculate_layout(container)
        if effect.tag == "request_render":
            host_config = getattr(reconciler, "_host_config", None)
            request_render = getattr(host_config, "request_render", None)
            if callable(request_render):
                request_render(getattr(container, "current_update_priority", 0), True)
