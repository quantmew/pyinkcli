"""Root/container composition methods for the reconciler."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Optional

from pyinkcli.packages.ink.dom import DOMElement
from pyinkcli.packages.ink.host_config import ReconcilerHostConfig
from pyinkcli.packages.react_reconciler.ReactFiberContainerUpdate import (
    commitContainerUpdate as _commit_container_update_impl,
    createContainer as _create_container_impl,
    flushSyncWork as _flush_sync_work_impl,
    submitContainer as _submit_container_impl,
    updateContainer as _update_container_impl,
    updateContainerSync as _update_container_sync_impl,
)
from pyinkcli.packages.react_reconciler.ReactFiberReconcilerState import (
    configureHost as _configure_host_impl,
    setCommitHandlers as _set_commit_handlers_impl,
)
from pyinkcli.packages.react_reconciler.ReactFiberRoot import ReconcilerContainer

if TYPE_CHECKING:
    from pyinkcli.component import RenderableNode


class ReactFiberReconcilerRoot:
    def create_container(
        self,
        container: DOMElement,
        tag: int = 0,
        hydrate: bool = False,
    ) -> ReconcilerContainer:
        return _create_container_impl(self, container, tag=tag, hydrate=hydrate)

    def set_commit_handlers(
        self,
        *,
        on_commit: Optional[Callable[[], None]] = None,
        on_immediate_commit: Optional[Callable[[], None]] = None,
    ) -> None:
        _set_commit_handlers_impl(
            self,
            on_commit=on_commit,
            on_immediate_commit=on_immediate_commit,
        )

    def configure_host(
        self,
        host_config: Optional[ReconcilerHostConfig],
    ) -> None:
        _configure_host_impl(self, host_config)

    def update_container(
        self,
        element: "RenderableNode",
        container: ReconcilerContainer,
        parent_component: Optional[Any] = None,
        callback: Optional[Callable[[], None]] = None,
    ) -> None:
        _update_container_impl(
            self,
            element,
            container,
            parent_component=parent_component,
            callback=callback,
        )

    def update_container_sync(
        self,
        element: "RenderableNode",
        container: ReconcilerContainer,
        parent_component: Optional[Any] = None,
        callback: Optional[Callable[[], None]] = None,
    ) -> None:
        _update_container_sync_impl(
            self,
            element,
            container,
            parent_component=parent_component,
            callback=callback,
        )

    def flush_sync_work(self, container: Optional[ReconcilerContainer] = None) -> None:
        _flush_sync_work_impl(self, container)

    def submit_container(
        self,
        element: "RenderableNode",
        container: ReconcilerContainer,
        parent_component: Optional[Any] = None,
        callback: Optional[Callable[[], None]] = None,
    ) -> None:
        _submit_container_impl(
            self,
            element,
            container,
            parent_component=parent_component,
            callback=callback,
        )

    def _commit_container_update(
        self,
        element: "RenderableNode",
        container: ReconcilerContainer,
        parent_component: Optional[Any] = None,
        callback: Optional[Callable[[], None]] = None,
    ) -> None:
        _commit_container_update_impl(
            self,
            element,
            container,
            parent_component=parent_component,
            callback=callback,
        )


__all__ = ["ReactFiberReconcilerRoot"]
