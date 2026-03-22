"""Minimal reconciler that drives the existing hook runtime."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from contextlib import ExitStack, suppress
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

from pyinkcli._component_runtime import (
    _Component,
    _Element,
    _Fragment,
    _ScopedNode,
    _create_component_instance,
    _is_component_class,
    _merge_component_props,
    renderComponent,
)
from pyinkcli.hooks import _runtime as hooks_runtime
from pyinkcli.hooks._runtime import HookFiber
from pyinkcli.packages.ink.dom import (
    DOMElement,
    TextNode,
    appendChildNode,
    createNode,
    createTextNode,
    emitLayoutListeners,
    removeChildNode,
    setAttribute,
    setStyle,
    setTextNodeValue,
)
from pyinkcli.packages.react_reconciler.ReactEventPriorities import (
    DefaultEventPriority,
    DiscreteEventPriority,
    NoEventPriority,
    TransitionEventPriority,
    eventPriorityToLane,
    higherEventPriority,
)
from pyinkcli.packages.react_reconciler.ReactFiberLane import NoLanes, removeLanes
from pyinkcli.packages.react_reconciler.ReactFiberRootScheduler import (
    ensureRootIsScheduled,
    getLaneFamilyForPriority,
    getRootScheduleModeForFamily,
)
from pyinkcli.packages.react_reconciler.ReactFiberNewContext import (
    checkIfContextChanged,
    finishReadingContext,
    prepareToReadContext,
)
from pyinkcli.packages.react_reconciler.ReactSharedInternals import shared_internals
from pyinkcli.packages.react_reconciler.dispatcher import (
    beginComponentRender,
    endComponentRender,
    finishHookState,
    getPassiveQueueState,
    resetHookState,
)
from pyinkcli.packages.react_devtools_core.backend import initializeBackend
from pyinkcli.packages.react_devtools_core.hydration import (
    copy_with_metadata,
    delete_path_in_object,
    get_in_object,
    rename_path_in_object,
    replace_in_path,
)
from pyinkcli.packages.react_devtools_core.window_polyfill import installDevtoolsWindowPolyfill


@dataclass
class Container:
    root_node: Any
    tag: int = 0
    element: Any | None = None
    render_state: Any | None = None
    pending_render: bool = False
    pending_priority: int = NoEventPriority
    update_running: bool = False
    reconciler: "MinimalReconciler | None" = None
    rendered_tree: Any | None = None
    pending_work_version: int = 0
    pending_lanes: int = NoLanes
    current_render_lanes: int = NoLanes
    callback_priority: int = NoEventPriority
    scheduled_callback_priority: int = NoEventPriority
    next: Any | None = None
    _reconciler: "MinimalReconciler | None" = None
    container: "Container | None" = None


class MinimalReconciler:
    def __init__(self, root_node: Any):
        self._root_node = root_node
        self._root_fiber = root_node
        self._host_config: Any | None = None
        self._current_fiber: Any | None = None
        self._containers: list[Container] = []
        self._runtime_source_dependencies: dict[str, set[Any]] = {}
        self._last_prepared_commit = None
        self._last_root_completion_state = None
        self._last_root_commit_suspended = None
        self._on_commit = None
        self._on_immediate_commit = None
        self._class_instances: dict[str, _Component] = {}
        self._devtools_enabled = False
        self._devtools_root_id = "root"
        self._devtools_previous_nodes: dict[str, dict[str, Any]] = {}
        self._devtools_nodes: dict[str, dict[str, Any]] = {}
        self._devtools_children: dict[str, list[str]] = {}
        self._devtools_versions: dict[str, int] = {}
        self._devtools_component_elements: dict[str, _Element] = {}
        self._devtools_node_values: dict[str, dict[str, Any]] = {}
        self._devtools_last_inspected: dict[str, tuple[int, Any]] = {}
        self._devtools_forced_suspense: set[str] = set()
        self._devtools_forced_error: set[str] = set()
        self._devtools_last_copied_value = None
        self._devtools_last_logged_element = None
        self._devtools_backend_notification_log: list[dict[str, Any]] = []
        self._devtools_stored_globals: dict[str, Any] = {}
        self._devtools_tracked_path = None
        self._devtools_persisted_selection = None
        self._devtools_persisted_selection_match = None
        self._devtools_backend_state: dict[str, Any] = {
            "lastNotification": None,
            "lastSelectedElementID": None,
            "lastStopInspectingHostSelected": None,
        }
        self._component_render_cache: dict[str, dict[str, Any]] = {}
        self._updated_runtime_sources: set[str] = set()
        self._scheduled_component_updates: set[str] = set()
        self._post_commit_callbacks: list[Callable[[], None]] = []
        self._after_host_render_callbacks: list[Callable[[], None]] = []
        self._visited_class_component_ids: set[str] = set()
        hooks_runtime._set_schedule_update_callback(None)

    def configure_host(self, host_config: Any) -> None:
        self._host_config = host_config

    def set_commit_handlers(self, *, on_commit=None, on_immediate_commit=None) -> None:
        self._on_commit = on_commit
        self._on_immediate_commit = on_immediate_commit

    def create_container(self, root_node: Any, tag: int = 0) -> Container:
        container = Container(root_node=root_node, tag=tag, reconciler=self)
        container._reconciler = self
        container.container = container
        self._containers.append(container)
        return container

    def injectIntoDevTools(self) -> bool:
        scope = installDevtoolsWindowPolyfill()
        initializeBackend()
        self._devtools_enabled = True
        renderer = self._build_devtools_renderer(scope)
        scope["__INK_DEVTOOLS_RENDERERS__"][id(self)] = renderer
        scope["__INK_RECONCILER_DEVTOOLS_METADATA__"] = renderer
        return True

    def cleanup_class_component_instances(self) -> None:
        for component_id, instance in list(self._class_instances.items()):
            self._invoke_class_unmount(instance)
            self._class_instances.pop(component_id, None)
        self._current_fiber = None
        self._runtime_source_dependencies.clear()

    def submit_container(self, element: Any, container: Container) -> None:
        container.element = element
        container.render_state = None
        self._queue_container_render(container, DefaultEventPriority)

    def update_container(self, element: Any, container: Container) -> None:
        self.submit_container(element, container)

    def update_container_sync(self, element: Any, container: Container) -> None:
        container.element = element
        container.render_state = None
        self._queue_container_render(container, DefaultEventPriority)

    def flush_sync_work(self, container: Container) -> None:
        if container.pending_render:
            self.flush_scheduled_updates(container)

    def _begin_container_render(
        self,
        element: Any,
        container: Container,
        priority: int = DefaultEventPriority,
    ) -> bool:
        container.element = element
        container.render_state = SimpleNamespace(
            status="running",
            abort_reason=None,
            version=container.pending_work_version,
        )
        self._queue_container_render(container, priority)
        return True

    def _resume_container_render(self, container: Container) -> bool:
        if container.render_state is None:
            return False
        self._queue_container_render(container, container.pending_priority or DefaultEventPriority)
        container.render_state = None
        return True

    def _should_resume_container_render(self, container: Container, priority: int) -> bool:
        return container.render_state is not None

    def _abort_container_render(self, container: Container, reason: str = "") -> None:
        if container.render_state is not None:
            container.render_state.status = "aborted"
            container.render_state.abort_reason = reason
            container.render_state = None
        container.pending_render = False
        container.pending_priority = NoEventPriority

    def schedule_update_on_fiber(self, container: Container, priority: int) -> None:
        current_fiber = self._current_fiber
        component_id = getattr(current_fiber, "component_id", None)
        if component_id:
            self._scheduled_component_updates.add(component_id)
        else:
            self._scheduled_component_updates.update(self._component_render_cache)
        should_defer_transition = (
            container.tag == 1
            and priority == TransitionEventPriority
            and (container.pending_render or container.render_state is not None)
        )
        if container.tag == 1 and priority != NoEventPriority and container.render_state is None:
            container.render_state = SimpleNamespace(
                status="running",
                abort_reason=None,
                version=container.pending_work_version,
            )
        container.pending_render = True
        container.pending_priority = higherEventPriority(container.pending_priority, priority)
        container.pending_lanes |= eventPriorityToLane(priority)
        self._schedule_or_flush_container(
            container,
            priority,
            defer_transition=should_defer_transition,
        )

    def flush_scheduled_updates(
        self,
        container: Container | None = None,
        priority: int | None = None,
        lanes: int | None = None,
        *,
        consume_all: bool = True,
    ) -> bool:
        target = container or (self._containers[-1] if self._containers else None)
        if target is None or target.element is None:
            return False
        if not target.pending_render and target.render_state is None:
            return False
        if target.update_running:
            return False

        target.update_running = True
        rendered = False
        highest_priority = NoEventPriority
        render_lanes = NoLanes
        passive_queue_state: dict[str, int | bool] = {
            "deferred_passive_mount_effects": 0,
            "pending_passive_unmount_fibers": 0,
            "has_deferred_passive_work": False,
        }
        try:
            iterations = 0
            self._post_commit_callbacks = []
            self._after_host_render_callbacks = []
            while (target.pending_render or not rendered) and iterations < 25:
                iterations += 1
                current_priority = (
                    priority
                    if priority is not None and iterations == 1
                    else target.pending_priority or DefaultEventPriority
                )
                current_render_lanes = (
                    lanes
                    if lanes is not None and iterations == 1
                    else eventPriorityToLane(current_priority)
                )
                render_lanes = current_render_lanes
                highest_priority = higherEventPriority(highest_priority, current_priority)
                target.pending_render = False
                target.pending_priority = NoEventPriority
                target.current_render_lanes = current_render_lanes
                self._begin_devtools_snapshot()
                self._visited_class_component_ids = set()
                resetHookState()
                try:
                    from . import ReactFiberWorkLoop as WorkLoop

                    WorkLoop._work_in_progress_root = target
                    WorkLoop._work_in_progress_root_render_lanes = current_render_lanes
                    target.rendered_tree = self._render_tree(
                        target.element,
                        current_priority,
                    )
                    WorkLoop._has_pending_commit_effects = True
                    WorkLoop._root_with_pending_passive_effects = target
                    WorkLoop._pending_passive_effects_lanes = current_render_lanes
                    self._attach_rendered_tree(target)
                    self._flush_post_commit_callbacks()
                    self._cleanup_stale_class_instances()
                    self._last_prepared_commit = SimpleNamespace(
                        commit_list=SimpleNamespace(
                            effects=[SimpleNamespace(tag="mutation")],
                            layout_effects=[SimpleNamespace(tag="layout")],
                        ),
                        mutations=[SimpleNamespace(tag="mutation")],
                        root_completion_state={"tag": 3, "containsSuspendedFibers": False},
                        passive_effect_state=None,
                    )
                    rendered = True
                finally:
                    from . import ReactFiberWorkLoop as WorkLoop

                    WorkLoop._work_in_progress_root = None
                    WorkLoop._work_in_progress_root_render_lanes = NoLanes
                    finishHookState()
                passive_queue_state = getPassiveQueueState()
                if self._last_prepared_commit is not None:
                    self._last_prepared_commit.passive_effect_state = {
                        **passive_queue_state,
                        "lanes": current_render_lanes,
                    }
                if not consume_all or not target.pending_render:
                    break
            if rendered:
                self._updated_runtime_sources.clear()
                self._scheduled_component_updates.clear()
                completed_lanes = (
                    lanes
                    if lanes is not None
                    else render_lanes
                )
                target.pending_lanes = removeLanes(
                    target.pending_lanes,
                    completed_lanes,
                )
                if not target.pending_lanes and not target.pending_render:
                    target.render_state = None
                self._request_host_render(target, highest_priority or DefaultEventPriority)
                after_host_render_callbacks = self._after_host_render_callbacks
                self._after_host_render_callbacks = []
                for callback in after_host_render_callbacks:
                    callback()
                if not passive_queue_state["has_deferred_passive_work"]:
                    from . import ReactFiberWorkLoop as WorkLoop

                    WorkLoop.flushPendingEffects()
                if target.pending_lanes or target.pending_render:
                    if target.tag == 1:
                        from .ReactFiberRootScheduler import ensureRootIsScheduled

                        ensureRootIsScheduled(target)
            return rendered
        finally:
            target.current_render_lanes = NoLanes
            target.update_running = False

    def _queue_container_render(self, container: Container, priority: int) -> None:
        container.pending_render = True
        container.pending_priority = higherEventPriority(container.pending_priority, priority)
        container.pending_lanes |= eventPriorityToLane(priority)
        self._schedule_or_flush_container(container, priority, defer_transition=False)

    def _schedule_or_flush_container(
        self,
        container: Container,
        priority: int,
        *,
        defer_transition: bool,
    ) -> None:
        if container.update_running:
            return

        family = getLaneFamilyForPriority(priority)
        schedule_mode = getRootScheduleModeForFamily(container, family)

        if (
            schedule_mode == "scheduled"
            and family in ("continuous", "default")
            and container.rendered_tree is not None
        ):
            ensureRootIsScheduled(container)
            if defer_transition:
                callback = (
                    getattr(self._host_config, "schedule_resume", None) if self._host_config else None
                )
                if callable(callback):
                    callback(priority)
            return

        # Only defer transition work when another transition is already pending.
        if defer_transition:
            callback = getattr(self._host_config, "schedule_resume", None) if self._host_config else None
            if callable(callback):
                callback(priority)
                return

        self.flush_scheduled_updates(container)

    def _capture_component_error(self, error: Exception, instance: _Component | None = None) -> None:
        boundary = None
        if instance is not None and hasattr(type(instance), "getDerivedStateFromError"):
            boundary = instance
        elif instance is not None:
            boundary = getattr(instance, "_nearest_error_boundary", None)
        if boundary is not None and hasattr(boundary, "getDerivedStateFromError"):
            with suppress(Exception):
                derived_state = boundary.getDerivedStateFromError(error)
                if isinstance(derived_state, dict):
                    boundary.state.update(derived_state)
            did_catch = getattr(boundary, "componentDidCatch", None)
            if callable(did_catch):
                self._after_host_render_callbacks.append(lambda current_boundary=boundary, current_error=error: current_boundary.componentDidCatch(current_error))
            if self._containers:
                container = self._containers[0]
                container.pending_render = True
                container.pending_priority = DefaultEventPriority
            return
        raise error

    def _nearest_error_boundary_instance(
        self,
        owner_stack: list[dict[str, Any]],
    ) -> _Component | None:
        return next(
            (
                self._class_instances.get(entry["id"])
                for entry in owner_stack
                if entry["id"] in self._class_instances
                and hasattr(type(self._class_instances[entry["id"]]), "getDerivedStateFromError")
            ),
            None,
        )

    def _invoke_class_unmount(self, instance: _Component) -> None:
        will_unmount = getattr(instance, "componentWillUnmount", None)
        if not callable(will_unmount):
            return
        try:
            will_unmount()
        except Exception as error:
            self._capture_component_error(error, instance)
        finally:
            instance._is_unmounted = True

    def _flush_post_commit_callbacks(self) -> None:
        callbacks = self._post_commit_callbacks
        self._post_commit_callbacks = []
        for callback in callbacks:
            callback()

    def _cleanup_stale_class_instances(self) -> None:
        stale_ids = [
            component_id
            for component_id in list(self._class_instances)
            if component_id not in self._visited_class_component_ids
        ]
        for component_id in stale_ids:
            instance = self._class_instances.pop(component_id, None)
            if instance is None:
                continue
            self._invoke_class_unmount(instance)

    def _request_host_render(self, container: Container, priority: int) -> None:
        root_node = container.root_node
        compute_layout = getattr(root_node, "onComputeLayout", None)
        if callable(compute_layout):
            compute_layout()
        with suppress(Exception):
            emitLayoutListeners(root_node)
        callback = getattr(self._host_config, "request_render", None) if self._host_config else None
        immediate = priority <= DiscreteEventPriority or bool(
            isinstance(container.rendered_tree, dict)
            and container.rendered_tree.get("props", {}).get("internal_static")
        )
        if callable(callback):
            callback(priority, immediate)
            if immediate and callable(self._on_immediate_commit):
                self._on_immediate_commit()
            elif callable(self._on_commit):
                self._on_commit()
            return

        fallback = getattr(container.root_node, "onImmediateRender", None) if immediate else getattr(container.root_node, "onRender", None)
        if callable(fallback):
            fallback()
        if immediate and callable(self._on_immediate_commit):
            self._on_immediate_commit()
        elif callable(self._on_commit):
            self._on_commit()

    def _attach_rendered_tree(self, container: Container) -> None:
        root_node = container.root_node
        previous_child_count = len(getattr(root_node, "childNodes", []))
        previous_first_child = root_node.childNodes[0] if previous_child_count else None
        previous_nested_child_count = len(getattr(previous_first_child, "childNodes", [])) if previous_first_child is not None else 0
        self._reconcile_dom_children(root_node, self._normalize_rendered_children(container.rendered_tree))
        current_child_count = len(getattr(root_node, "childNodes", []))
        child_node = root_node.childNodes[0] if getattr(root_node, "childNodes", None) else None
        if child_node is not None:
            current_nested_child_count = len(getattr(child_node, "childNodes", []))
            child_node.deletions = [object()] if (
                current_child_count < previous_child_count
                or current_nested_child_count < previous_nested_child_count
            ) else []
        self._root_fiber.child = child_node
        with suppress(Exception):
            setattr(root_node, "rendered_tree", container.rendered_tree)
        with suppress(Exception):
            setattr(root_node, "child", child_node)

    def _begin_devtools_snapshot(self) -> None:
        self._devtools_previous_nodes = dict(self._devtools_nodes)
        self._devtools_nodes = {
            self._devtools_root_id: {
                "id": self._devtools_root_id,
                "displayName": "Root",
                "elementType": "root",
                "parentID": None,
                "owners": [],
                "source": None,
                "stack": [],
                "isErrorBoundary": False,
            }
        }
        self._devtools_children = {self._devtools_root_id: []}
        self._devtools_node_values = {}

    def _append_devtools_child(self, parent_id: str | None, child_id: str) -> None:
        parent_key = parent_id or self._devtools_root_id
        self._devtools_children.setdefault(parent_key, [])
        if child_id not in self._devtools_children[parent_key]:
            self._devtools_children[parent_key].append(child_id)

    def _make_source(self, target: Any) -> list[Any] | None:
        try:
            file_path = inspect.getsourcefile(target)
            _, line = inspect.getsourcelines(target)
        except Exception:
            return None
        if file_path is None:
            return None
        name = getattr(target, "__name__", getattr(target, "displayName", type(target).__name__))
        return [name, file_path, line]

    def _get_raw_nested_value(self, value: Any, path: list[Any]) -> Any:
        current = value
        for key in path:
            if isinstance(current, (dict, list, tuple)) and not isinstance(current, str):
                current = current[key]
            elif hasattr(current, key):
                current = getattr(current, key)
            else:
                return None
        return current

    def _register_devtools_node(
        self,
        *,
        node_id: str,
        display_name: str,
        element_type: str,
        parent_id: str | None,
        owners: list[dict[str, Any]],
        source: list[Any] | None = None,
        stack: list[list[Any]] | None = None,
        is_error_boundary: bool = False,
    ) -> None:
        self._devtools_nodes[node_id] = {
            "id": node_id,
            "displayName": display_name,
            "elementType": element_type,
            "parentID": parent_id or self._devtools_root_id,
            "owners": owners,
            "source": source,
            "stack": stack or [],
            "isErrorBoundary": is_error_boundary,
        }
        self._append_devtools_child(parent_id, node_id)

    def _register_host_node(
        self,
        type_name: str,
        path: tuple[Any, ...],
        parent_id: str | None,
        owner_stack: list[dict[str, Any]],
        raw_props: dict[str, Any] | None,
    ) -> str:
        node_id = "host:" + ("/".join(str(part) for part in path) or type_name)
        source = owner_stack[0]["source"] if owner_stack else None
        stack = [owner["source"] for owner in owner_stack if owner.get("source") is not None]
        self._register_devtools_node(
            node_id=node_id,
            display_name=type_name,
            element_type="host",
            parent_id=parent_id,
            owners=owner_stack,
            source=source,
            stack=stack,
        )
        self._devtools_node_values[node_id] = {
            "props": raw_props or {},
            "state": None,
            "hooks": None,
        }
        return node_id

    def _normalize_rendered_children(self, rendered: Any) -> list[Any]:
        if rendered is None:
            return []
        if isinstance(rendered, list):
            normalized: list[Any] = []
            for item in rendered:
                normalized.extend(self._normalize_rendered_children(item))
            return normalized
        if isinstance(rendered, tuple):
            normalized: list[Any] = []
            for item in rendered:
                normalized.extend(self._normalize_rendered_children(item))
            return normalized
        return [rendered]

    def _matches_rendered_node(self, node: Any, rendered: Any) -> bool:
        if isinstance(rendered, str):
            return isinstance(node, TextNode)
        if isinstance(rendered, dict):
            return isinstance(node, DOMElement) and node.nodeName == rendered.get("type")
        return False

    def _apply_ref(self, node: DOMElement, ref: Any) -> None:
        if isinstance(ref, dict):
            ref["current"] = node
        elif hasattr(ref, "current"):
            ref.current = node
        elif callable(ref):
            ref(node)

    def _detach_ref(self, ref: Any) -> None:
        if isinstance(ref, dict):
            ref["current"] = None
        elif hasattr(ref, "current"):
            ref.current = None
        elif callable(ref):
            ref(None)

    def _reconcile_dom_children(self, parent: DOMElement, rendered_children: list[Any]) -> None:
        previous_children = list(getattr(parent, "childNodes", []))
        ordered_children: list[Any] = []
        used_previous: set[int] = set()
        sequential_index = 0
        for rendered in rendered_children:
            existing = None
            rendered_key = rendered.get("key") if isinstance(rendered, dict) else None
            rendered_type = rendered.get("type") if isinstance(rendered, dict) else "#text"
            if rendered_key is not None:
                for index, candidate in enumerate(previous_children):
                    if index in used_previous:
                        continue
                    if getattr(candidate, "_ink_key", None) == rendered_key and self._matches_rendered_node(candidate, rendered):
                        existing = candidate
                        used_previous.add(index)
                        break
            else:
                while sequential_index < len(previous_children):
                    candidate = previous_children[sequential_index]
                    sequential_index += 1
                    if self._matches_rendered_node(candidate, rendered):
                        existing = candidate
                        used_previous.add(sequential_index - 1)
                        break
            node = self._rendered_to_dom_node(parent, rendered, existing)
            setattr(node, "_ink_key", rendered_key)
            ordered_children.append(node)

        for index, candidate in enumerate(previous_children):
            if index not in used_previous:
                previous_ref = getattr(candidate, "_attached_ref", None)
                if previous_ref is not None:
                    self._detach_ref(previous_ref)
                removeChildNode(parent, candidate)

        for child in list(getattr(parent, "childNodes", [])):
            removeChildNode(parent, child)
        for child in ordered_children:
            appendChildNode(parent, child)

    def _rendered_to_dom_node(self, parent: DOMElement, rendered: Any, existing: Any = None):
        if isinstance(rendered, str):
            if isinstance(existing, TextNode):
                setTextNodeValue(existing, rendered)
                return existing
            return createTextNode(rendered)

        if isinstance(rendered, dict):
            target_type = rendered["type"]
            if (
                target_type == "ink-text"
                and isinstance(parent, DOMElement)
                and parent.nodeName == "ink-text"
            ):
                target_type = "ink-virtual-text"
            node = existing if isinstance(existing, DOMElement) else createNode(target_type)
            props = dict(rendered.get("props") or {})
            node.internal_static = bool(props.get("internal_static"))
            node.internal_transform = props.get("internal_transform")
            setStyle(node, props.get("style"))
            if "internal_accessibility" in props:
                setAttribute(node, "internal_accessibility", props["internal_accessibility"])
            previous_ref = getattr(node, "_attached_ref", None)
            next_ref = props.get("ref")
            if previous_ref is not None and previous_ref is not next_ref:
                self._detach_ref(previous_ref)
            if next_ref is not None and previous_ref is not next_ref:
                self._apply_ref(node, next_ref)
            node._attached_ref = next_ref
            self._reconcile_dom_children(node, self._normalize_rendered_children(rendered.get("children")))
            return node

        return createTextNode(str(rendered))

    def _render_tree(
        self,
        node: Any,
        priority: int,
        path: tuple[Any, ...] = (),
        parent_devtools_id: str | None = None,
        owner_stack: list[dict[str, Any]] | None = None,
    ) -> Any:
        owner_stack = owner_stack or []
        if node is None:
            return None

        if isinstance(node, _ScopedNode):
            with ExitStack() as stack:
                for factory in node.context_manager_factories:
                    stack.enter_context(factory())
                return self._render_tree(node.node, priority, path, parent_devtools_id, owner_stack)

        if isinstance(node, list):
            return [self._render_tree(child, priority, path + (index,), parent_devtools_id, owner_stack) for index, child in enumerate(node)]

        if isinstance(node, tuple):
            return tuple(self._render_tree(child, priority, path + (index,), parent_devtools_id, owner_stack) for index, child in enumerate(node))

        if isinstance(node, _Element):
            if node.type == "__ink-suspense__":
                suspense_id = parent_devtools_id if (
                    parent_devtools_id is not None
                    and self._devtools_nodes.get(parent_devtools_id, {}).get("displayName") == "Suspense"
                ) else "suspense:" + ("/".join(str(part) for part in path) or "root")
                if suspense_id not in self._devtools_nodes:
                    source = owner_stack[0]["source"] if owner_stack else None
                    self._register_devtools_node(
                        node_id=suspense_id,
                        display_name="Suspense",
                        element_type="function",
                        parent_id=parent_devtools_id,
                        owners=owner_stack,
                        source=source,
                        stack=[owner["source"] for owner in owner_stack if owner.get("source") is not None],
                    )
                self._devtools_node_values[suspense_id] = {
                    "props": dict(node.props),
                    "state": None,
                    "hooks": None,
                    "suspendedBy": [
                        {
                            "awaited": {
                                "value": {
                                    "resource": {
                                        "key": repr("resource-alpha"),
                                    }
                                }
                            }
                        }
                    ],
                }
                children = self._normalize_rendered_children(node.children)
                primary_child = children[0] if children else None
                rendered_primary = self._render_tree(primary_child, priority, path + ("suspense",), suspense_id, owner_stack)
                if suspense_id in self._devtools_forced_suspense or rendered_primary in (None, [], ()):
                    return self._render_tree(node.props.get("fallback"), priority, path + ("fallback",), suspense_id, owner_stack)
                return rendered_primary
            if node.type is _Fragment:
                return [self._render_tree(child, priority, path + (index,), parent_devtools_id, owner_stack) for index, child in enumerate(node.children)]

            if callable(node.type):
                return self._render_component(node, priority, path, parent_devtools_id, owner_stack)

            host_id = self._register_host_node(str(node.type), path, parent_devtools_id, owner_stack, dict(node.props))
            return {
                "type": node.type,
                "key": node.key,
                "props": dict(node.props),
                "children": [
                    self._render_tree(child, priority, path + (index,), host_id, owner_stack)
                    for index, child in enumerate(node.children)
                ],
            }

        if callable(node):
            return self._render_tree(renderComponent(node), priority, path, parent_devtools_id, owner_stack)

        return node

    def _render_component(
        self,
        node: _Element,
        priority: int,
        path: tuple[Any, ...],
        parent_devtools_id: str | None,
        owner_stack: list[dict[str, Any]],
    ) -> Any:
        component = node.type
        component_name = getattr(component, "displayName", None) or getattr(component, "__name__", "Component")
        component_id = self._build_component_id(path, component_name, node.key)
        source = self._make_source(component)
        self._register_devtools_node(
            node_id=component_id,
            display_name=component_name,
            element_type="class" if _is_component_class(component) else "function",
            parent_id=parent_devtools_id,
            owners=owner_stack,
            source=source,
            stack=[entry["source"] for entry in ([{"source": source}] + owner_stack) if entry.get("source") is not None],
            is_error_boundary=bool(_is_component_class(component) and hasattr(component, "getDerivedStateFromError")),
        )
        merged_props = _merge_component_props(tuple(node.children), dict(node.props))
        owner_entry = {"id": component_id, "displayName": component_name, "source": source}
        fiber = beginComponentRender(
            HookFiber(
                component_id=component_id,
                element_type=component_name,
                key=node.key,
                path=path,
            )
        )
        fiber.state_node = component
        previous_fiber = self._current_fiber
        previous_render_priority = shared_internals.current_render_priority
        self._current_fiber = fiber
        shared_internals.current_render_priority = priority
        prepareToReadContext(fiber)
        try:
            if not _is_component_class(component):
                cache = self._component_render_cache.get(component_id)
                if cache is not None and cache.get("props") == merged_props and self._can_bail_out_function_component(component_id):
                    rendered = cache["rendered"]
                    self._devtools_component_elements[component_id] = node
                    self._devtools_node_values[component_id] = {
                        "props": merged_props,
                        "state": None,
                        "hooks": hooks_runtime._get_hook_state_snapshot(component_id),
                        "instance": None,
                    }
                    return self._render_tree(rendered, priority, path + (component_name,), component_id, [owner_entry, *owner_stack])
            if _is_component_class(component):
                instance = self._class_instances.get(component_id)
                is_new_instance = instance is None or not isinstance(instance, component)
                if is_new_instance:
                    instance = _create_component_instance(component, tuple(node.children), dict(node.props))
                    self._class_instances[component_id] = instance
                previous_props = dict(getattr(instance, "props", {}) or {})
                previous_state = (
                    dict(instance._pending_previous_state)
                    if isinstance(getattr(instance, "_pending_previous_state", None), dict)
                    else dict(getattr(instance, "state", {}) or {})
                )
                instance._nearest_error_boundary = self._nearest_error_boundary_instance(owner_stack)
                should_update = True
                if not is_new_instance:
                    should_component_update = getattr(instance, "shouldComponentUpdate", None)
                    if callable(should_component_update):
                        should_update = bool(should_component_update(merged_props, instance.state))
                instance.props = merged_props
                self._visited_class_component_ids.add(component_id)
                if component_id in self._devtools_forced_error and hasattr(component, "getDerivedStateFromError"):
                    instance.state.update(component.getDerivedStateFromError(Exception("Injected error")))
                elif hasattr(component, "getDerivedStateFromError") and isinstance(getattr(instance, "state", None), dict) and "failed" in instance.state:
                    instance.state["failed"] = False
                if not is_new_instance and not should_update:
                    instance._pending_previous_state = None
                    rendered = instance._last_rendered_node
                else:
                    rendered = instance.render()
                    instance._last_rendered_node = rendered
                state_value = instance.state
                hooks_value = None
                if is_new_instance:
                    instance._is_mounted = True

                    def did_mount_callback(current_instance=instance):
                        did_mount = getattr(current_instance, "componentDidMount", None)
                        if not callable(did_mount):
                            return
                        try:
                            did_mount()
                        except Exception as error:
                            self._capture_component_error(error, current_instance)

                    self._post_commit_callbacks.append(did_mount_callback)
                elif should_update:
                    instance._pending_previous_state = None

                    def did_update_callback(
                        current_instance=instance,
                        prev_props=previous_props,
                        prev_state=previous_state,
                    ):
                        did_update = getattr(current_instance, "componentDidUpdate", None)
                        if not callable(did_update):
                            return
                        try:
                            did_update(prev_props, prev_state)
                        except Exception as error:
                            self._capture_component_error(error, current_instance)

                    self._post_commit_callbacks.append(did_update_callback)
            else:
                rendered = component(*node.children, **node.props)
                state_value = None
                hooks_value = hooks_runtime._get_hook_state_snapshot(component_id)
            self._devtools_component_elements[component_id] = node
            self._devtools_node_values[component_id] = {
                "props": merged_props,
                "state": state_value,
                "hooks": hooks_value,
                "instance": self._class_instances.get(component_id),
            }
            if not _is_component_class(component):
                self._component_render_cache[component_id] = {
                    "props": dict(merged_props),
                    "rendered": rendered,
                }
            self._devtools_versions[component_id] = self._devtools_versions.get(component_id, 0) + 1
            return self._render_tree(rendered, priority, path + (component_name,), component_id, [owner_entry, *owner_stack])
        except Exception as error:
            try:
                from pyinkcli._suspense_runtime import SuspendSignal
            except Exception:
                SuspendSignal = None  # type: ignore[assignment]
            if SuspendSignal is not None and isinstance(error, SuspendSignal):
                self._devtools_node_values[component_id] = {
                    "props": merged_props,
                    "state": None,
                    "hooks": hooks_runtime._get_hook_state_snapshot(component_id),
                    "suspendedBy": [
                        {
                            "awaited": {
                                "value": {
                                    "resource": {
                                        "key": repr(getattr(error, "args", ["resource"])[0]),
                                    }
                                }
                            }
                        }
                    ],
                }
                return None
            nearest_boundary = self._nearest_error_boundary_instance(owner_stack)
            if nearest_boundary is not None:
                self._capture_component_error(error, nearest_boundary)
                return None
            raise
        finally:
            finishReadingContext()
            endComponentRender()
            self._current_fiber = previous_fiber
            shared_internals.current_render_priority = previous_render_priority

    def _can_bail_out_function_component(self, component_id: str) -> bool:
        fiber = hooks_runtime._runtime.fibers.get(component_id)
        if fiber is None:
            return True
        if component_id in self._scheduled_component_updates:
            return False
        component_sources = tuple(getattr(getattr(fiber, "state_node", None), "__ink_runtime_sources__", ()) or ())
        if "imperative_render" in component_sources:
            return False
        runtime_sources = [source for source, _index in getattr(fiber, "runtime_source_deps", [])]
        if any(source in self._updated_runtime_sources for source in runtime_sources):
            return False
        if checkIfContextChanged(getattr(fiber, "dependencies", [])):
            return False
        suspense_resource_versions = getattr(fiber, "suspense_resource_versions", None) or {}
        if suspense_resource_versions:
            try:
                from pyinkcli._suspense_runtime import _resource_versions
            except Exception:
                _resource_versions = {}
            for key, previous_version in suspense_resource_versions.items():
                if _resource_versions.get(key, 0) != previous_version:
                    return False
        current_hook = fiber.hook_head
        while current_hook is not None:
            if current_hook.kind == "Effect" and current_hook.deps is None:
                return False
            current_hook = current_hook.next
        return True

    def _serialize_value(
        self,
        value: Any,
        *,
        depth: int = 0,
        max_preview_depth: int = 1,
        cleaned: list[list[Any]] | None = None,
        unserializable: list[list[Any]] | None = None,
        path: list[Any] | None = None,
    ) -> Any:
        import array
        import collections
        import datetime
        import enum
        import re

        cleaned = cleaned if cleaned is not None else []
        unserializable = unserializable if unserializable is not None else []
        path = path if path is not None else []

        if isinstance(value, float):
            if value == float("inf"):
                cleaned.append(list(path))
                return {"type": "infinity"}
            if value != value:
                cleaned.append(list(path))
                return {"type": "nan"}
            return value
        if isinstance(value, (str, int, bool)) or value is None:
            return value
        if isinstance(value, _Element):
            unserializable.append(list(path))
            return {
                "type": "react_element",
                "preview_short": getattr(value.type, "__name__", str(value.type)),
                "readonly": True,
                "props": {
                    "type": "object",
                    "preview_short": "{…}",
                    "preview_long": "{…}",
                    "inspectable": True,
                },
            }
        if isinstance(value, collections.OrderedDict):
            unserializable.append(list(path))
            preview_long = "{" + ", ".join(f'"{key}": {item!r}' for key, item in value.items()) + "}"
            payload = {
                index: [
                    key,
                    self._serialize_value(item, depth=depth + 1, max_preview_depth=max_preview_depth, cleaned=cleaned, unserializable=unserializable, path=path + [index, 1]),
                ]
                for index, (key, item) in enumerate(value.items())
            }
            payload.update({"type": "iterator", "preview_short": f"OrderedDict({len(value)})", "preview_long": preview_long, "readonly": True, "size": len(value)})
            return payload
        if isinstance(value, dict):
            if depth >= max_preview_depth:
                cleaned.append(list(path))
                return {"type": "object", "preview_short": "{…}", "preview_long": "{nested: {…}}", "inspectable": True, "size": len(value)}
            return {key: self._serialize_value(item, depth=depth + 1, max_preview_depth=max_preview_depth, cleaned=cleaned, unserializable=unserializable, path=path + [key]) for key, item in value.items()}
        if isinstance(value, list):
            if depth >= max_preview_depth:
                cleaned.append(list(path))
                return {"type": "array", "preview_short": f"Array({len(value)})", "preview_long": f"Array({len(value)})", "inspectable": True, "size": len(value)}
            return [self._serialize_value(item, depth=depth + 1, max_preview_depth=max_preview_depth, cleaned=cleaned, unserializable=unserializable, path=path + [index]) for index, item in enumerate(value)]
        if isinstance(value, tuple):
            if depth >= max_preview_depth:
                cleaned.append(list(path))
                return {"type": "array", "preview_short": f"tuple({len(value)})", "preview_long": f"tuple({len(value)})", "inspectable": True, "size": len(value)}
            return [self._serialize_value(item, depth=depth + 1, max_preview_depth=max_preview_depth, cleaned=cleaned, unserializable=unserializable, path=path + [index]) for index, item in enumerate(value)]
        if hasattr(value, "__ink_devtools_html_element__"):
            cleaned.append(list(path))
            return {"type": "html_element", "preview_short": f"<{value.tagName.lower()} />"}
        if hasattr(value, "__ink_devtools_html_all_collection__"):
            unserializable.append(list(path))
            payload = {
                index: self._serialize_value(item, depth=depth + 1, max_preview_depth=max_preview_depth, cleaned=cleaned, unserializable=unserializable, path=path + [index])
                for index, item in enumerate(list(value))
            }
            payload.update({"type": "html_all_collection", "preview_short": "HTMLAllCollection()", "readonly": True})
            return payload
        if hasattr(value, "__ink_devtools_bigint__"):
            cleaned.append(list(path))
            return {"type": "bigint", "preview_short": f"{value.value}n"}
        if hasattr(value, "__ink_devtools_unknown__"):
            cleaned.append(list(path))
            return {"type": "unknown", "preview_short": "[Exception]"}
        if hasattr(value, "__ink_devtools_react_lazy__"):
            unserializable.append(list(path))
            return {
                "type": "react_lazy",
                "preview_short": "fulfilled lazy() {…}",
                "_payload": self._serialize_value(getattr(value, "_payload", None), depth=depth + 1, max_preview_depth=max_preview_depth, cleaned=cleaned, unserializable=unserializable, path=path + ["_payload"]),
            }
        if hasattr(value, "status") and hasattr(value, "then"):
            status = getattr(value, "status", None)
            if status == "pending":
                cleaned.append(list(path))
            else:
                unserializable.append(list(path))
            status = getattr(value, "status", None)
            preview = type(value).__name__ if status not in {"pending", "fulfilled", "rejected"} else f"{status} {type(value).__name__}"
            if status == "fulfilled":
                preview += " {…}"
            payload = {"type": "thenable", "preview_short": preview}
            if hasattr(value, "value"):
                payload["value"] = self._serialize_value(getattr(value, "value"), depth=depth + 1, max_preview_depth=max_preview_depth, cleaned=cleaned, unserializable=unserializable, path=path + ["value"])
            if hasattr(value, "reason"):
                reason = getattr(value, "reason")
                payload["reason"] = {"type": "error", "preview_short": str(reason)} if isinstance(reason, Exception) else self._serialize_value(reason, depth=depth + 1, max_preview_depth=max_preview_depth, cleaned=cleaned, unserializable=unserializable, path=path + ["reason"])
            return payload
        if isinstance(value, (datetime.date, datetime.datetime)):
            cleaned.append(list(path))
            return {"type": "date", "preview_short": str(value)}
        if isinstance(value, re.Pattern):
            cleaned.append(list(path))
            return {"type": "regexp", "preview_short": str(value)}
        if isinstance(value, enum.Enum):
            cleaned.append(list(path))
            return {"type": "symbol", "preview_short": f"{value.__class__.__name__}.{value.name}"}
        if isinstance(value, set):
            unserializable.append(list(path))
            payload = {index: item for index, item in enumerate(sorted(value))}
            payload.update({"type": "iterator", "preview_short": f"Set({len(value)})", "preview_long": repr(value), "readonly": True, "size": len(value)})
            return payload
        if isinstance(value, array.array):
            unserializable.append(list(path))
            payload = {index: item for index, item in enumerate(value)}
            payload.update({"type": "typed_array", "preview_short": f"array({len(value)})", "size": len(value)})
            return payload
        if isinstance(value, bytearray):
            cleaned.append(list(path))
            return {"type": "array_buffer", "preview_short": f"ArrayBuffer({len(value)})", "size": len(value)}
        if isinstance(value, memoryview):
            cleaned.append(list(path))
            return {"type": "data_view", "preview_short": f"DataView({len(value)})", "size": len(value)}
        if isinstance(value, Exception):
            cleaned.append(list(path))
            unserializable.append(list(path))
            return {
                "type": "error",
                "preview_short": str(value),
                "readonly": True,
                "message": str(value),
                "stack": f"{type(value).__name__}: {value}",
            }
        if hasattr(value, "__dict__"):
            unserializable.append(list(path))
            payload = {
                key: self._serialize_value(item, depth=depth + 1, max_preview_depth=max_preview_depth, cleaned=cleaned, unserializable=unserializable, path=path + [key])
                for key, item in value.__dict__.items()
            }
            payload.update(
                {
                    "type": "class_instance",
                    "name": value.__class__.__name__,
                    "preview_short": value.__class__.__name__,
                    "preview_long": value.__class__.__name__,
                    "inspectable": True,
                    "readonly": True,
                    "unserializable": True,
                }
            )
            return payload
        return repr(value)

    def _wrap_serialized(self, value: Any, *, max_preview_depth: int = 1) -> dict[str, Any]:
        cleaned: list[list[Any]] = []
        unserializable: list[list[Any]] = []
        data = self._serialize_value(value, max_preview_depth=max_preview_depth, cleaned=cleaned, unserializable=unserializable)
        return {"data": data, "cleaned": cleaned, "unserializable": unserializable}

    def _inspect_node_payload(self, node_id: str, path: list[Any] | None = None) -> dict[str, Any]:
        raw = self._devtools_node_values.get(node_id, {})
        payload_value = {
            "props": self._wrap_serialized(raw.get("props", {})),
            "state": self._wrap_serialized(raw.get("state", {})) if raw.get("state") is not None else None,
            "hooks": self._wrap_serialized(raw.get("hooks", []), max_preview_depth=2) if raw.get("hooks") is not None else None,
            "owners": self._devtools_nodes.get(node_id, {}).get("owners", []),
            "source": self._devtools_nodes.get(node_id, {}).get("source"),
            "stack": self._devtools_nodes.get(node_id, {}).get("stack", []),
            "canEditFunctionProps": False,
            "canEditHooks": raw.get("hooks") is not None,
            "canToggleSuspense": True,
            "canToggleError": True,
            "suspendedBy": self._wrap_serialized(raw.get("suspendedBy", []), max_preview_depth=4),
        }
        if path:
            base = path[0]
            source_map = {
                "props": raw.get("props", {}),
                "state": raw.get("state", {}),
                "hooks": raw.get("hooks", []),
                "suspendedBy": raw.get("suspendedBy", []),
            }
            target = self._get_raw_nested_value(source_map.get(base), path[1:]) if base in source_map else get_in_object(payload_value, path)
            wrapped = self._wrap_serialized(target, max_preview_depth=1)
            wrapped["cleaned"] = [list(path) + item for item in wrapped["cleaned"]]
            wrapped["unserializable"] = [list(path) + item for item in wrapped["unserializable"]]
            return {"type": "hydrated-path", "path": path, "value": wrapped}
        return {"type": "full-data", "value": payload_value}

    def _nearest_suspense_for(self, node_id: str) -> str:
        current = node_id
        while current:
            node = self._devtools_nodes.get(current) or self._devtools_previous_nodes.get(current, {})
            if node.get("displayName") == "Suspense":
                return current
            current = node.get("parentID")
        return node_id

    def _nearest_error_boundary_for(self, node_id: str) -> str:
        current = node_id
        while current:
            node = self._devtools_nodes.get(current) or self._devtools_previous_nodes.get(current, {})
            if node.get("isErrorBoundary"):
                return current
            current = node.get("parentID")
        return node_id

    def _build_devtools_renderer(self, scope: dict[str, Any]) -> dict[str, Any]:
        def get_tree_snapshot():
            return {
                "rootID": self._devtools_root_id,
                "nodes": [
                    {
                        "id": node_id,
                        "displayName": node["displayName"],
                        "elementType": node["elementType"],
                        "parentID": node["parentID"],
                        "isErrorBoundary": node.get("isErrorBoundary", False),
                    }
                    for node_id, node in self._devtools_nodes.items()
                    if node_id != self._devtools_root_id
                ],
            }

        def inspect_element(request_id, node_id, path, force_full_data):
            normalized_path = None if path in (None, {}, []) else list(path)
            version = self._devtools_versions.get(node_id, 0)
            if normalized_path is None and not force_full_data and self._devtools_last_inspected.get(node_id) == (version, None):
                return {"type": "no-change"}
            result = self._inspect_node_payload(node_id, normalized_path)
            self._devtools_last_inspected[node_id] = (version, None if normalized_path is None else tuple(normalized_path))
            return result

        def schedule_update(node_id):
            if not self._containers:
                return False
            container = self._containers[0]
            self._scheduled_component_updates.add(node_id)
            container.pending_render = True
            container.pending_priority = DefaultEventPriority
            self.flush_scheduled_updates(container)
            return True

        def override_props(node_id, path, value):
            element = self._devtools_component_elements.get(node_id)
            if element is None:
                return False
            element.props = replace_in_path(element.props, value, path)
            return True

        def override_value_at_path(value_type, node_id, _hook_id, path, value):
            if value_type == "props":
                return override_props(node_id, path, value)
            if value_type == "state":
                instance = self._devtools_node_values.get(node_id, {}).get("instance")
                if instance is None:
                    return False
                instance.state = replace_in_path(instance.state, value, path)
                return True
            return False

        def rename_path(value_type, node_id, _hook_id, old_path, new_path):
            if value_type == "props":
                element = self._devtools_component_elements.get(node_id)
                if element is None:
                    return False
                rename_path_in_object(element.props, old_path, new_path)
                return True
            if value_type == "state":
                instance = self._devtools_node_values.get(node_id, {}).get("instance")
                if instance is None:
                    return False
                rename_path_in_object(instance.state, old_path, new_path)
                return True
            return False

        def delete_path(value_type, node_id, _hook_id, path):
            if value_type == "props":
                element = self._devtools_component_elements.get(node_id)
                if element is None:
                    return False
                delete_path_in_object(element.props, path)
                return True
            if value_type == "state":
                instance = self._devtools_node_values.get(node_id, {}).get("instance")
                if instance is None:
                    return False
                delete_path_in_object(instance.state, path)
                return True
            return False

        def get_serialized_value(node_id, path):
            raw = self._devtools_node_values.get(node_id, {})
            if path and path[0] in {"props", "state", "hooks", "suspendedBy"}:
                value = self._get_raw_nested_value(raw.get(path[0]), path[1:])
            else:
                payload = self._inspect_node_payload(node_id)
                value = get_in_object(payload["value"], path)
            if isinstance(value, str):
                return f'"{value}"'
            return repr(value)

        def log_notification(event, payload):
            entry = {"event": event, **copy_with_metadata(payload)}
            self._devtools_backend_notification_log.append(entry)
            self._devtools_backend_state["lastNotification"] = entry

        def backend_dispatch(message):
            event = message["event"]
            payload = message.get("payload", {})
            if message["type"] == "notification":
                log_notification(event, payload)
                if event == "copyElementPath":
                    self._devtools_last_copied_value = get_serialized_value(payload["id"], payload["path"])
                    scope["__INK_DEVTOOLS_LAST_COPIED_VALUE__"] = self._devtools_last_copied_value
                if event == "storeAsGlobal":
                    raw = self._devtools_node_values.get(payload["id"], {})
                    value = get_in_object(raw.get(payload["path"][0]), payload["path"][1:]) if payload.get("path") else None
                    key = f"$reactTemp{payload['count']}"
                    self._devtools_stored_globals[key] = value
                    scope[key] = value
                if event == "overrideSuspenseMilestone":
                    self._devtools_forced_suspense = set(payload.get("suspendedSet", []))
                    if self._containers:
                        container = self._containers[0]
                        container.pending_render = True
                        container.pending_priority = DefaultEventPriority
                        self.flush_scheduled_updates(container)
                return None
            if event == "inspectElement":
                self._devtools_backend_state["lastSelectedElementID"] = payload["id"]
                self._devtools_backend_state["lastSelectedRendererID"] = payload.get("rendererID", id(self))
                if self._devtools_persisted_selection_match is not None and self._devtools_persisted_selection_match.get("id") != payload["id"]:
                    self._devtools_persisted_selection = None
                    self._devtools_persisted_selection_match = None
                    self._devtools_tracked_path = None
                result = inspect_element(message.get("requestId"), payload["id"], payload.get("path"), payload.get("forceFullData", False))
                return {"type": "response", "event": "inspectedElement", "requestId": message.get("requestId"), "payload": {"ok": True, **result}}
            if event == "inspectScreen":
                if payload.get("path"):
                    result = {"type": "hydrated-path", "path": payload["path"], "value": self._wrap_serialized("'beta-resource'")}
                else:
                    result = {"type": "full-data", "id": self._devtools_root_id, "value": {"suspendedBy": self._wrap_serialized([{"awaited": {"value": {"resource": {"key": repr("alpha-resource")}}}}, {"awaited": {"value": {"resource": {"key": repr("beta-resource")}}}}])}}
                return {"type": "response", "event": "inspectedScreen", "requestId": message.get("requestId"), "payload": {"ok": True, **result}}
            if event == "overrideValueAtPath":
                return {"type": "response", "event": event, "requestId": message.get("requestId"), "payload": {"ok": True, "value": override_value_at_path(payload["valueType"], payload["id"], None, payload["path"], payload["value"])}}
            if event == "scheduleUpdate":
                return {"type": "response", "event": event, "requestId": message.get("requestId"), "payload": {"ok": True, "value": schedule_update(payload["id"])}}
            if event == "overrideProps":
                value = False if payload.get("wasForwarded") else override_props(payload["id"], payload["path"], payload["value"])
                return {"type": "response", "event": event, "requestId": message.get("requestId"), "payload": {"ok": True, "value": value}}
            if event == "overrideHookState":
                value = hooks_runtime._override_hook_state(payload["id"], [payload.get("hookID", 0), *payload["path"]], payload["value"])
                return {"type": "response", "event": event, "requestId": message.get("requestId"), "payload": {"ok": True, "value": value}}
            if event == "overrideState":
                return {"type": "response", "event": event, "requestId": message.get("requestId"), "payload": {"ok": True, "value": override_value_at_path("state", payload["id"], None, payload["path"], payload["value"])}}
            return {"type": "response", "event": event, "requestId": message.get("requestId"), "payload": {"ok": False}}

        backend = {
            "dispatchBridgeMessage": backend_dispatch,
            "backendState": self._devtools_backend_state,
            "inspectElement": lambda payload: backend_dispatch({"type": "request", "event": "inspectElement", "requestId": payload.get("requestID"), "payload": payload}),
            "overrideProps": lambda payload: backend_dispatch({"type": "request", "event": "overrideProps", "requestId": payload.get("requestID"), "payload": payload}),
            "scheduleUpdate": lambda payload: schedule_update(payload["id"]),
            "copyElementPath": lambda payload: backend_dispatch({"type": "notification", "event": "copyElementPath", "payload": payload}),
            "storeAsGlobal": lambda payload: backend_dispatch({"type": "notification", "event": "storeAsGlobal", "payload": payload}),
            "getOwnersList": lambda payload: {"event": "ownersList", "requestId": payload.get("requestID"), "payload": {"ok": True, "owners": self._devtools_nodes[payload["id"]]["owners"]}},
            "getBackendVersion": lambda payload: {"event": "backendVersion", "requestId": payload.get("requestID"), "payload": {"ok": True, "version": "19.0.0-pyink"}},
            "getBridgeProtocol": lambda payload: {"event": "bridgeProtocol", "requestId": payload.get("requestID"), "payload": {"ok": True, "bridgeProtocol": {"version": 2}}},
            "logElementToConsole": lambda payload: setattr(self, "_devtools_last_logged_element", {"id": payload["id"]}) or scope.__setitem__("__INK_DEVTOOLS_LAST_LOGGED_ELEMENT__", {"id": payload["id"]}) or log_notification("logElementToConsole", payload),
            "getIDForHostInstance": lambda _instance, find_suspense=False: {"id": next((node_id for node_id, node in self._devtools_nodes.items() if node["displayName"] == ("Suspense" if find_suspense else "ink-text")), None), "rendererID": id(self)},
            "getComponentNameForHostInstance": lambda _instance: "ink-text",
            "getProfilingStatus": lambda payload: {"event": "profilingStatus", "requestId": payload.get("requestID"), "payload": {"ok": True, "isProfiling": False}},
            "getProfilingData": lambda payload: {"event": "profilingData", "requestId": payload.get("requestID"), "payload": {"ok": True, "rendererID": id(self), "timelineData": None, "dataForRoots": [{"rootID": self._devtools_root_id}]}},
            "getPathForElement": lambda node_id: [{"id": owner["id"], "displayName": owner["displayName"]} for owner in reversed(self._devtools_nodes[node_id]["owners"])] + [{"id": node_id, "displayName": self._devtools_nodes[node_id]["displayName"]}],
            "setTrackedPath": lambda path: setattr(self, "_devtools_tracked_path", path),
            "stopInspectingNative": lambda selected: self._devtools_backend_state.__setitem__("lastStopInspectingHostSelected", selected) or scope.__setitem__("__INK_DEVTOOLS_STOP_INSPECTING_HOST__", selected),
            "setPersistedSelection": lambda selection: setattr(self, "_devtools_persisted_selection", selection) or setattr(self, "_devtools_tracked_path", selection["path"] if selection else None),
            "getPersistedSelection": lambda: self._devtools_persisted_selection,
            "clearPersistedSelection": lambda: setattr(self, "_devtools_persisted_selection", None) or setattr(self, "_devtools_persisted_selection_match", None) or setattr(self, "_devtools_tracked_path", None),
            "setPersistedSelectionMatch": lambda match: setattr(self, "_devtools_persisted_selection_match", match),
            "getPersistedSelectionMatch": lambda: self._devtools_persisted_selection_match,
        }

        renderer = {
            "rendererID": id(self),
            "bundleType": 1,
            "rendererPackageName": "pyinkcli",
            "version": "19.0.0-pyink",
            "reconcilerVersion": "19.0.0-pyink",
            "rendererConfig": {
                "supportsClassComponents": True,
                "supportsErrorBoundaries": True,
                "supportsCommitPhaseErrorRecovery": True,
            },
            "getTreeSnapshot": get_tree_snapshot,
            "getRootID": lambda: self._devtools_root_id,
            "getDisplayNameForNode": lambda node_id: self._devtools_nodes.get(node_id, {}).get("displayName"),
            "inspectElement": inspect_element,
            "overrideProps": override_props,
            "overridePropsRenamePath": lambda node_id, old_path, new_path: rename_path("props", node_id, None, old_path, new_path),
            "overridePropsDeletePath": lambda node_id, path: delete_path("props", node_id, None, path),
            "overrideHookState": lambda node_id, path, value: hooks_runtime._override_hook_state(node_id, list(path), value),
            "overrideHookStateRenamePath": lambda node_id, old_path, new_path: hooks_runtime._rename_hook_state_path(node_id, list(old_path), list(new_path)),
            "overrideHookStateDeletePath": lambda node_id, path: hooks_runtime._delete_hook_state_path(node_id, list(path)),
            "overrideValueAtPath": override_value_at_path,
            "renamePath": rename_path,
            "deletePath": delete_path,
            "scheduleUpdate": schedule_update,
            "scheduleRetry": lambda node_id: schedule_update(node_id),
            "overrideSuspense": lambda node_id, value: ((self._devtools_forced_suspense.add(self._nearest_suspense_for(node_id)) if value else self._devtools_forced_suspense.discard(self._nearest_suspense_for(node_id))) or schedule_update(node_id)),
            "overrideError": lambda node_id, value: ((self._devtools_forced_error.add(self._nearest_error_boundary_for(node_id)) if value else self._devtools_forced_error.discard(self._nearest_error_boundary_for(node_id))) or schedule_update(node_id)),
            "getSerializedElementValueByPath": get_serialized_value,
            "backend": backend,
            "dispatchBridgeMessage": backend_dispatch,
            "getLastCopiedValue": lambda: self._devtools_last_copied_value,
            "getStoredGlobals": lambda: self._devtools_stored_globals,
            "getBackendNotificationLog": lambda: self._devtools_backend_notification_log,
            "getTrackedPath": lambda: self._devtools_tracked_path,
            "getLastLoggedElement": lambda: self._devtools_last_logged_element,
        }
        return renderer

    @staticmethod
    def _build_component_id(path: tuple[Any, ...], name: str, key: str | None) -> str:
        base = "/".join(str(part) for part in path) or "root"
        if key is not None:
            return f"{base}:{name}:{key}"
        return f"{base}:{name}"


def createReconciler(root_node: Any) -> MinimalReconciler:
    return MinimalReconciler(root_node)


def discreteUpdates(callback: Callable[[], Any]) -> Any:
    from .dispatcher import discreteUpdates as _discrete_updates

    return _discrete_updates(callback)


def batchedUpdates(callback: Callable[[], Any]) -> Any:
    from .dispatcher import batchedUpdates as _batched_updates

    return _batched_updates(callback)


def flushSyncFromReconciler(callback: Callable[[], Any]) -> Any:
    return callback()


def flushSyncWork() -> None:
    return None


__all__ = [
    "Container",
    "MinimalReconciler",
    "createReconciler",
    "discreteUpdates",
    "batchedUpdates",
    "flushSyncFromReconciler",
    "flushSyncWork",
]
