from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CommitList:
    layout_effects: list = field(default_factory=list)


@dataclass
class PreparedCommit:
    work_root: object
    commit_list: CommitList
    root_completion_state: dict | None = None
    passive_effect_state: dict | None = None


def runPreparedCommitEffects(reconciler, container, prepared: PreparedCommit) -> None:
    if prepared.root_completion_state is not None:
        reconciler._last_root_completion_state = prepared.root_completion_state
        reconciler._last_root_commit_suspended = prepared.root_completion_state.get(
            "containsSuspendedFibers",
            False,
        )
    for effect in prepared.commit_list.layout_effects:
        if effect.tag == "request_render":
            immediate = effect.payload.get("immediate", False)
            if prepared.root_completion_state and prepared.root_completion_state.get("containsSuspendedFibers"):
                immediate = True
            reconciler._host_config.request_render(getattr(container, "current_update_priority", 0), immediate)

