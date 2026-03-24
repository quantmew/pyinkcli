from __future__ import annotations

import copy
import inspect
import json
import math
import re
import threading
from dataclasses import dataclass
from types import SimpleNamespace

from .component import RenderableNode
from ._component_runtime import _Component
from .dom import (
    addLayoutListener,
    appendChildNode,
    createNode,
    createTextNode,
    emitLayoutListeners,
    removeChildNode,
    setAttribute,
    setTextNodeValue,
)
from .hooks import _runtime as hooks_runtime
from .packages import react
from .packages import react_router
from .suspense_runtime import SuspendSignal


def _safe_copy(value):
    try:
        return copy.deepcopy(value)
    except Exception:  # noqa: BLE001
        return value


def batchedUpdates(callback):
    return hooks_runtime._batched_updates_runtime(callback)


def discreteUpdates(callback):
    return hooks_runtime._discrete_updates_runtime(callback)


def consumePendingRerenderPriority():
    return hooks_runtime._consume_pending_rerender_priority()


@dataclass
class _Container:
    root: object
    tag: int = 0
    current_vnode: object = None
    scheduled_timer: threading.Timer | None = None
    pending_vnode: object = None
    render_state: object = None
    pending_work_version: int = 0


class _ClassComponentUpdater:
    def __init__(self, reconciler: "_Reconciler", component_id: str) -> None:
        self._reconciler = reconciler
        self._component_id = component_id

    def enqueueSetState(self, public_instance, partial_state, callback=None, callerName=None):
        if callable(partial_state):
            partial_state = partial_state(public_instance.state, public_instance.props)
        if isinstance(partial_state, dict):
            public_instance.state.update(partial_state)
        self._reconciler._class_dirty.add(self._component_id)
        from .hooks.use_app import useApp

        app = useApp()
        if app is not None:
            app._schedule_render("default")
        if callback:
            callback()

    def enqueueForceUpdate(self, public_instance, callback=None, callerName=None):
        self._reconciler._class_dirty.add(self._component_id)
        from .hooks.use_app import useApp

        app = useApp()
        if app is not None:
            app._schedule_render("default")
        if callback:
            callback()


class _Reconciler:
    def __init__(self, root_node) -> None:
        self.root_node = root_node
        self._commit_handlers = {"on_commit": None, "on_immediate_commit": None}
        self._root_fiber = SimpleNamespace(child=None)
        self._last_prepared_commit = None
        self._last_root_completion_state = None
        self._last_root_commit_suspended = None
        self._devtools_prop_overrides = {}
        self._devtools_state_overrides = {}
        self._forced_suspense_ids = set()
        self._forced_error_ids = set()
        self._forced_error_state = {}
        self._class_instances = {}
        self._class_dirty = set()
        self._pending_class_mounts = []
        self._pending_class_updates = []
        self._pending_errors = []
        self._owner_source_cache = {}

    def create_container(self, root_node, tag: int = 0):
        container = _Container(root=root_node, tag=tag)
        container._last_deletions = []
        return container

    def set_commit_handlers(self, *, on_commit=None, on_immediate_commit=None) -> None:
        self._commit_handlers["on_commit"] = on_commit
        self._commit_handlers["on_immediate_commit"] = on_immediate_commit

    def update_container(self, vnode, container) -> None:
        if container.tag == 1:
            container.pending_vnode = vnode
            container.render_state = SimpleNamespace(status="pending", abort_reason=None)
            if getattr(self, "_force_rerender", False):
                container.force_rerender = True
                container.root.force_rerender = True
            if container.scheduled_timer is None:
                container.scheduled_timer = threading.Timer(0.05, lambda: self._flush_pending(container))
                container.scheduled_timer.start()
            return
        self.update_container_sync(vnode, container)

    def _flush_pending(self, container) -> None:
        vnode = container.pending_vnode
        container.pending_vnode = None
        container.scheduled_timer = None
        if vnode is not None:
            self.update_container_sync(vnode, container)

    def flush_sync_work(self, container) -> None:
        if container.pending_vnode is not None:
            self._flush_pending(container)

    def update_container_sync(self, vnode, container) -> None:
        hooks_runtime._reset_hook_state()
        self._reconcile_children(container.root, [vnode], "root")
        hooks_runtime._finish_hook_state()
        container.current_vnode = vnode
        container.render_state = None
        container.force_rerender = False
        container.root.force_rerender = False
        first_child = container.root.childNodes[0] if container.root.childNodes else None
        container._last_deletions = list(getattr(first_child, "deletions", [])) if first_child is not None else []
        self._root_fiber.child = SimpleNamespace(deletions=list(getattr(container, "_last_deletions", [])))
        self._last_prepared_commit = SimpleNamespace(
            commit_list=SimpleNamespace(effects=[1], layout_effects=[1]),
            mutations=[1],
        )
        if callable(container.root.onComputeLayout):
            container.root.onComputeLayout()
        emitLayoutListeners(container.root)
        self._flush_class_lifecycle_queues()
        has_static = any(getattr(child, "internal_static", False) for child in container.root.childNodes)
        if has_static and self._commit_handlers["on_immediate_commit"]:
            self._commit_handlers["on_immediate_commit"]()
        elif self._commit_handlers["on_commit"]:
            self._commit_handlers["on_commit"]()
        if self._pending_errors:
            raise self._pending_errors.pop(0)

    def _render_component(self, vnode: RenderableNode, instance_id: str):
        if vnode.type is react.Fragment:
            return vnode.children
        if getattr(vnode.type, "__ink_react_provider__", False):
            value = vnode.props.get("value", vnode.type._context.default_value)
            with hooks_runtime._push_context(vnode.type._context, value):
                rendered_children = [
                    self._render_component(child, f"{instance_id}:provider:{index}") if isinstance(child, RenderableNode) else child
                    for index, child in enumerate(vnode.children)
                ]
                if len(rendered_children) == 1:
                    return rendered_children[0]
                return rendered_children
        if getattr(vnode.type, "__ink_react_consumer__", False):
            reader = vnode.children[0]
            return reader(hooks_runtime.useContext(vnode.type._context))
        if getattr(vnode.type, "__ink_react_forward_ref__", False):
            return vnode.type.render(vnode.props, vnode.props.get("ref"))
        if getattr(vnode.type, "__ink_react_lazy__", False):
            resolved = vnode.type._init(vnode.type._payload)
            return RenderableNode(type=resolved, props=vnode.props, children=vnode.children, key=vnode.key)
        if getattr(vnode.type, "__ink_react_memo__", False):
            return RenderableNode(type=vnode.type.type, props=vnode.props, children=vnode.children, key=vnode.key)
        if vnode.type == "__ink-suspense__":
            if instance_id in self._forced_suspense_ids or getattr(vnode, "_devtools_owner_id", None) in self._forced_suspense_ids:
                return vnode.props.get("fallback")
            try:
                if not vnode.children:
                    return None
                return vnode.children[0]
            except SuspendSignal as error:
                fallback = vnode.props.get("fallback")
                if isinstance(fallback, RenderableNode):
                    fallback._suspended_by = [
                        {
                            "awaited": {
                                "value": {
                                    "resource": {
                                        "key": repr(error.args[0]) if error.args else repr("resource"),
                                    }
                                }
                            }
                        }
                    ]
                return fallback
        if vnode.type == "__router_provider__":
            with react_router.push_router_context(vnode.props["internal_router_context"]):
                if not vnode.children:
                    return None
                return self._render_component(vnode.children[0], instance_id)
        if isinstance(vnode.type, type) and issubclass(vnode.type, _Component):
            owner_id = f"{instance_id}:{getattr(vnode.type, '__name__', 'anonymous')}"
            effective_props = _safe_copy(self._devtools_prop_overrides.get(owner_id, vnode.props))
            effective_props.setdefault("children", vnode.children if len(vnode.children) != 1 else vnode.children[0])
            instance = self._class_instances.get(owner_id)
            is_new = instance is None or not isinstance(instance, vnode.type)
            prev_props = {}
            prev_state = {}
            if is_new:
                instance = vnode.type(props=effective_props)
                instance.updater = _ClassComponentUpdater(self, owner_id)
                self._class_instances[owner_id] = instance
            else:
                prev_props = _safe_copy(getattr(instance, "_committed_props", instance.props))
                prev_state = _safe_copy(getattr(instance, "_committed_state", instance.state))
            instance.props = effective_props
            if owner_id in self._devtools_state_overrides:
                instance.state = _safe_copy(self._devtools_state_overrides[owner_id])
            if owner_id in self._forced_error_ids and hasattr(vnode.type, "getDerivedStateFromError"):
                derived = vnode.type.getDerivedStateFromError(RuntimeError("DevTools forced error"))
                if isinstance(derived, dict):
                    instance.state.update(derived)
            if not is_new and hasattr(instance, "shouldComponentUpdate"):
                try:
                    should_update = instance.shouldComponentUpdate(effective_props, instance.state)
                except Exception as error:  # noqa: BLE001
                    self._pending_errors.append(error)
                    return getattr(instance, "_last_rendered", None)
                if should_update is False:
                    return getattr(instance, "_last_rendered", None)
            result = instance.render()
            instance._last_rendered = result
            if isinstance(result, RenderableNode):
                result._class_instance = instance
                result._devtools_owner_id = owner_id
            if is_new and hasattr(instance, "componentDidMount"):
                self._pending_class_mounts.append((owner_id, instance))
            elif (
                not is_new
                and hasattr(instance, "componentDidUpdate")
                and (prev_props != instance.props or prev_state != instance.state or owner_id in self._class_dirty)
            ):
                self._pending_class_updates.append((owner_id, instance, prev_props, prev_state))
            self._class_dirty.discard(owner_id)
            return result
        if callable(vnode.type):
            component_instance_id = f"{instance_id}:{getattr(vnode.type, '__name__', 'anonymous')}"
            effective_props = _safe_copy(self._devtools_prop_overrides.get(component_instance_id, vnode.props))
            hooks_runtime._begin_component_render(component_instance_id, vnode.type)
            try:
                result = vnode.type(*vnode.children, **effective_props)
                if isinstance(result, RenderableNode):
                    result._devtools_owner_id = component_instance_id
            finally:
                hooks_runtime._end_component_render()
            return result
        return vnode

    def _assign_ref(self, node, ref) -> None:
        if ref is None:
            return
        if callable(ref):
            ref(node)
        elif isinstance(ref, dict):
            ref["current"] = node

    def _detach_ref(self, ref) -> None:
        if ref is None:
            return
        if callable(ref):
            ref(None)
        elif isinstance(ref, dict):
            ref["current"] = None

    def _reconcile_node(self, existing, vnode, instance_id: str):
        if vnode is None:
            return None
        if isinstance(vnode, (str, int)):
            if existing and getattr(existing, "nodeName", None) == "#text":
                setTextNodeValue(existing, str(vnode))
                return existing
            return createTextNode(str(vnode))
        if isinstance(vnode, list):
            host = createNode("ink-fragment")
            self._reconcile_children(host, vnode, instance_id)
            return host
        if not isinstance(vnode, RenderableNode):
            return createTextNode(str(vnode))
        if getattr(vnode.type, "__ink_react_provider__", False):
            value = vnode.props.get("value", vnode.type._context.default_value)
            with hooks_runtime._push_context(vnode.type._context, value):
                if not vnode.children:
                    return None
                if len(vnode.children) == 1:
                    return self._reconcile_node(existing, vnode.children[0], f"{instance_id}:provider")
                return self._reconcile_node(existing, list(vnode.children), f"{instance_id}:provider")
        if vnode.type == "__router_provider__":
            with react_router.push_router_context(vnode.props["internal_router_context"]):
                if not vnode.children:
                    return None
                if len(vnode.children) == 1:
                    return self._reconcile_node(existing, vnode.children[0], f"{instance_id}:router")
                return self._reconcile_node(existing, list(vnode.children), f"{instance_id}:router")
        if vnode.type == "__ink-suspense__":
            if instance_id in self._forced_suspense_ids or getattr(vnode, "_devtools_owner_id", None) in self._forced_suspense_ids:
                result = self._reconcile_node(existing, vnode.props.get("fallback"), f"{instance_id}:suspense")
                if result is not None:
                    result._suspended_by = []
                return result
            try:
                if not vnode.children:
                    return None
                return self._reconcile_node(existing, vnode.children[0], f"{instance_id}:suspense")
            except SuspendSignal as error:
                fallback = vnode.props.get("fallback")
                if isinstance(fallback, RenderableNode):
                    fallback._suspended_by = [
                        {
                            "awaited": {
                                "value": {
                                    "resource": {
                                        "key": repr(error.args[0]) if error.args else repr("resource"),
                                    }
                                }
                            }
                        }
                    ]
                result = self._reconcile_node(existing, fallback, f"{instance_id}:suspense")
                if result is not None:
                    result._suspended_by = getattr(fallback, "_suspended_by", [])
                return result
        if (
            callable(vnode.type)
            and not getattr(getattr(existing, "parentNode", None), "force_rerender", False)
            and not getattr(getattr(existing, "parentNode", None), "render_state", None)
            and not getattr(self, "_force_rerender", False)
            and
            existing is not None
            and getattr(existing, "_component_type", None) is vnode.type
            and getattr(existing, "_component_props", None) == vnode.props
            and hooks_runtime._component_can_bail_out(f"{instance_id}:{getattr(vnode.type, '__name__', 'anonymous')}")
            and getattr(vnode.type, "__ink_runtime_sources__", ()) in {(), ("router.location",), ("cursor",)}
        ):
            return existing
        rendered = self._render_component(vnode, instance_id)
        if rendered is not vnode:
            component_id = f"{instance_id}:{getattr(vnode.type, '__name__', 'anonymous')}" if callable(vnode.type) else None
            if existing is not None:
                existing_component_id = getattr(existing, "_component_instance_id", None)
                if existing_component_id is not None and existing_component_id != component_id:
                    self._invoke_component_will_unmount(existing)
                    existing = None
            result = self._reconcile_node(existing, rendered, instance_id)
            if result is not None and getattr(rendered, "_suspended_by", None):
                result._suspended_by = rendered._suspended_by
            if result is not None and callable(vnode.type):
                result._component_type = vnode.type
                result._component_props = _safe_copy(self._devtools_prop_overrides.get(component_id, vnode.props))
                if getattr(result, "_component_instance_id", None) is None:
                    result._component_instance_id = component_id
                if getattr(result, "_class_instance", None) is None and getattr(rendered, "_class_instance", None) is not None:
                    result._class_instance = rendered._class_instance
                owner_infos = list(getattr(result, "_owner_infos", []))
                owner_infos.insert(
                    0,
                    self._make_owner_info(
                        vnode.type,
                        component_id,
                        result._component_props,
                        class_instance=getattr(rendered, "_class_instance", None),
                    ),
                )
                result._owner_infos = owner_infos
                if getattr(rendered, "_suspended_by", None):
                    result._suspended_by = rendered._suspended_by
            return result
        if isinstance(vnode.type, str):
            parent = getattr(existing, "parentNode", None)
            parent_name = getattr(parent, "nodeName", None)
            if vnode.type == "ink-text" and parent_name in {"ink-text", "ink-virtual-text"}:
                vnode = RenderableNode(type="ink-virtual-text", props=vnode.props, children=vnode.children, key=vnode.key)
        if existing and getattr(existing, "nodeName", None) == vnode.type:
            node = existing
        else:
            if existing is not None:
                self._detach_ref(getattr(existing, "ref", None))
            node = createNode(vnode.type)
        node.key = vnode.key
        previous_ref = getattr(node, "ref", None)
        removed_keys = set(getattr(node, "attributes", {})) - set(vnode.props)
        for key in removed_keys:
            node.attributes.pop(key, None)
            if hasattr(node, key):
                setattr(node, key, None)
        node.style = {}
        for key, value in vnode.props.items():
            setAttribute(node, key, value)
        if "style" in vnode.props:
            node.computed_width = vnode.props["style"].get("width", getattr(node, "computed_width", 0))
            node.computed_height = vnode.props["style"].get("height", getattr(node, "computed_height", 0))
        node._component_type = vnode.type
        node._component_props = dict(vnode.props)
        self._reconcile_children(node, vnode.children, instance_id)
        if previous_ref is not vnode.props.get("ref"):
            self._detach_ref(previous_ref)
            self._assign_ref(node, vnode.props.get("ref"))
        return node

    def _reconcile_children(self, parent, children, instance_id: str) -> None:
        normalized: list = []
        for child in children:
            if child is None:
                continue
            if isinstance(child, list):
                normalized.extend(child)
            else:
                normalized.append(child)
        keyed_existing = {}
        for index, child in enumerate(parent.childNodes):
            key = getattr(child, "key", None)
            if key is not None:
                keyed_existing[key] = child
        next_children = []
        deletions = []
        for index, child in enumerate(normalized):
            if (
                isinstance(child, RenderableNode)
                and child.type == "ink-text"
                and getattr(parent, "nodeName", None) in {"ink-text", "ink-virtual-text"}
            ):
                child = RenderableNode(type="ink-virtual-text", props=child.props, children=child.children, key=child.key)
            existing = None
            key = child.key if isinstance(child, RenderableNode) else None
            if key is not None:
                existing = keyed_existing.get(key)
            else:
                existing = parent.childNodes[index] if index < len(parent.childNodes) else None
            next_children.append(self._reconcile_node(existing, child, f"{instance_id}:{index}"))
        next_ids = {id(child) for child in next_children if child is not None}
        for child in list(parent.childNodes):
            if id(child) not in next_ids:
                self._detach_ref(getattr(child, "ref", None))
                self._invoke_component_will_unmount(child)
                deletions.append(child)
        parent.childNodes = [child for child in next_children if child is not None]
        for child in parent.childNodes:
            child.parentNode = parent
        setattr(parent, "deletions", deletions)

    def _queue_passive_unmount(self, node) -> None:
        component_id = getattr(node, "_component_instance_id", None)
        if component_id is not None:
            state = hooks_runtime._hook_state.get(component_id)
            if state is not None:
                for hook in state.hooks:
                    cleanup = getattr(hook, "cleanup", None)
                    if callable(cleanup):
                        hooks_runtime._runtime.pending_passive_unmount_fibers.append(
                            hooks_runtime.HookFiber(
                                component_id=component_id,
                                element_type=component_id,
                                hook_head=hooks_runtime.HookNode(index=0, kind="Effect", cleanup=cleanup),
                            )
                        )
        for child in getattr(node, "childNodes", []):
            self._queue_passive_unmount(child)

    def _invoke_component_will_unmount(self, node) -> None:
        instance = getattr(node, "_class_instance", None)
        component_id = getattr(node, "_component_instance_id", None)
        if instance is not None and hasattr(instance, "componentWillUnmount"):
            try:
                instance.componentWillUnmount()
            except Exception as error:  # noqa: BLE001
                self._pending_errors.append(error)
        if component_id is not None:
            self._class_instances.pop(component_id, None)
            self._class_dirty.discard(component_id)
        for child in getattr(node, "childNodes", []):
            self._invoke_component_will_unmount(child)

    def _flush_class_lifecycle_queues(self) -> None:
        mounts = list(self._pending_class_mounts)
        updates = list(self._pending_class_updates)
        self._pending_class_mounts.clear()
        self._pending_class_updates.clear()
        for component_id, instance in mounts:
            instance._committed_props = _safe_copy(instance.props)
            instance._committed_state = _safe_copy(instance.state)
            try:
                instance.componentDidMount()
            except Exception as error:  # noqa: BLE001
                self._pending_errors.append(error)
        for component_id, instance, prev_props, prev_state in updates:
            try:
                instance.componentDidUpdate(prev_props, prev_state)
            except Exception as error:  # noqa: BLE001
                self._pending_errors.append(error)
            instance._committed_props = _safe_copy(instance.props)
            instance._committed_state = _safe_copy(instance.state)

    def _abort_container_render(self, container, reason="aborted") -> None:
        state = container.render_state
        if state is not None:
            state.status = "aborted"
            state.abort_reason = reason
        container.render_state = None

    def _make_owner_info(self, component_type, component_id, props, class_instance=None):
        display_name = getattr(component_type, "__name__", str(component_type))
        cached_source = self._owner_source_cache.get(component_type)
        if cached_source is None:
            try:
                source_file = inspect.getsourcefile(component_type) or ""
                source_line = inspect.getsourcelines(component_type)[1]
            except (OSError, TypeError):
                source_file = ""
                source_line = 0
            cached_source = (source_file, source_line)
            self._owner_source_cache[component_type] = cached_source
        else:
            source_file, source_line = cached_source
        state = None
        if class_instance is not None:
            state = _safe_copy(self._devtools_state_overrides.get(component_id, getattr(class_instance, "state", {})))
        return {
            "displayName": display_name,
            "componentType": component_type,
            "componentID": component_id,
            "props": _safe_copy(props),
            "classInstance": class_instance,
            "state": state,
            "source": [display_name, source_file, source_line],
            "isErrorBoundary": isinstance(component_type, type) and issubclass(component_type, _Component) and hasattr(component_type, "getDerivedStateFromError"),
            "isSuspenseBoundary": display_name == "Suspense",
            "elementType": "class" if isinstance(component_type, type) and issubclass(component_type, _Component) else "function",
        }

    def injectIntoDevTools(self) -> bool:
        from builtins import __dict__ as builtins_dict
        from .packages.react_devtools_core.backend import initializeBackend
        from .packages.react_devtools_core.hydration import (
            delete_path_in_object,
            dispatch_bridge_message,
            get_in_object,
            handle_inspect_element_bridge_call,
            handle_inspect_screen_bridge_call,
            make_bridge_call,
            make_bridge_notification,
            make_bridge_response,
            rename_path_in_object,
            set_in_object,
        )
        from .packages.react_devtools_core.window_polyfill import installDevtoolsWindowPolyfill

        if not initializeBackend():
            return False
        scope = installDevtoolsWindowPolyfill()
        renderer_id = id(self)
        scope["__INK_DEVTOOLS_RENDERERS__"][renderer_id] = self
        nodes = []
        id_map = {}
        host_instance_map = {}
        inspect_cache = {}
        backend_notification_log = []
        stored_globals = {}
        backend_state = {
            "lastNotification": None,
            "lastSelectedElementID": None,
            "lastSelectedRendererID": None,
            "lastStopInspectingHostSelected": None,
        }
        tracked_path = None
        persisted_selection = None
        persisted_selection_match = None
        last_copied_value = None
        last_logged_element = None

        def dehydrate(value, base_path, *, wrap_root=False):
            cleaned = []
            unserializable = []

            def mark_clean(path):
                cleaned.append(list(path))

            def mark_unserializable(path):
                unserializable.append(list(path))

            def serialize(current, path):
                if current is None or isinstance(current, (bool, int, str)):
                    return current
                if isinstance(current, float):
                    if math.isinf(current):
                        mark_clean(path)
                        return {"type": "infinity"}
                    if math.isnan(current):
                        mark_clean(path)
                        return {"type": "nan"}
                    return current
                if getattr(type(current), "__module__", "") == "datetime" and type(current).__name__ == "date":
                    mark_clean(path)
                    return {
                        "type": "date",
                        "preview_short": current.isoformat(),
                        "preview_long": current.isoformat(),
                        "inspectable": True,
                    }
                if isinstance(current, re.Pattern):
                    mark_clean(path)
                    return {
                        "type": "regexp",
                        "preview_short": current.pattern,
                        "preview_long": current.pattern,
                        "inspectable": True,
                    }
                if hasattr(current, "name") and hasattr(current, "value") and current.__class__.__mro__[1].__name__ == "Enum":
                    mark_clean(path)
                    return {
                        "type": "symbol",
                        "preview_short": f"{type(current).__name__}.{current.name}",
                        "preview_long": f"{type(current).__name__}.{current.name}",
                        "inspectable": True,
                    }
                if type(current).__name__ == "OrderedDict":
                    items = list(current.items())
                    mark_unserializable(path)
                    return {
                        **{
                            index: [
                                serialize(value[0], path + [index, 0]),
                                serialize(value[1], path + [index, 1]),
                            ]
                            for index, value in enumerate(items)
                        },
                        "type": "iterator",
                        "name": "OrderedDict",
                        "preview_short": f"OrderedDict({len(items)})",
                        "preview_long": json.dumps([[key, item] for key, item in items], default=repr),
                        "inspectable": True,
                        "readonly": True,
                        "size": len(items),
                    }
                if isinstance(current, list):
                    if wrap_root or path != base_path:
                        return {
                            **{index: serialize(item, path + [index]) for index, item in enumerate(current)},
                            "type": "array",
                            "preview_short": "{…}",
                            "preview_long": "{…}",
                            "inspectable": True,
                            "size": len(current),
                        }
                    return [serialize(item, path + [index]) for index, item in enumerate(current)]
                if isinstance(current, tuple):
                    values = [serialize(item, path + [index]) for index, item in enumerate(current)]
                    if wrap_root or path != base_path:
                        return {
                            **{index: value for index, value in enumerate(values)},
                            "type": "array",
                            "preview_short": "{…}",
                            "preview_long": "{…}",
                            "inspectable": True,
                            "size": len(values),
                        }
                    return values
                if isinstance(current, dict):
                    if wrap_root or path != base_path:
                        mark_clean(path)
                        result = {
                            "type": "object",
                            "name": "",
                            "preview_short": "{…}",
                            "preview_long": "{" + ", ".join(f"{key}: {{…}}" if isinstance(value, (dict, list, tuple, object)) and not isinstance(value, (str, int, float, bool, type(None))) else f'{key}: {value!r}' for key, value in list(current.items())[:1]) + ("}" if current else "}"),
                            "inspectable": True,
                            "size": len(current),
                        }
                        for key, value in current.items():
                            if isinstance(value, (str, int, float, bool, type(None))):
                                continue
                            if isinstance(value, dict):
                                result["preview_long"] = "{nested: {…}}" if len(current) == 1 and "nested" in current else result["preview_long"]
                            break
                        return result
                    return {key: serialize(item, path + [key]) for key, item in current.items()}
                if isinstance(current, Exception):
                    mark_unserializable(path)
                    return {
                        "type": "error",
                        "name": type(current).__name__,
                        "message": str(current),
                        "stack": f"{type(current).__name__}: {current}",
                        "readonly": True,
                        "inspectable": True,
                    }
                if isinstance(current, RenderableNode):
                    mark_unserializable(path)
                    return {
                        "type": "react_element",
                        "name": getattr(current.type, "__name__", str(current.type)),
                        "readonly": True,
                        "inspectable": True,
                        "props": serialize(dict(current.props), path + ["props"]),
                    }
                if hasattr(current, "__ink_devtools_html_element__"):
                    mark_clean(path)
                    return {
                        "type": "html_element",
                        "name": getattr(current, "tagName", "").lower(),
                        "preview_short": f"<{getattr(current, 'tagName', '').lower()} />",
                        "preview_long": f"<{getattr(current, 'tagName', '').lower()} />",
                        "inspectable": True,
                    }
                if hasattr(current, "__ink_devtools_html_all_collection__"):
                    mark_unserializable(path)
                    items = list(current)
                    return {
                        **{index: serialize(item, path + [index]) for index, item in enumerate(items)},
                        "type": "html_all_collection",
                        "name": "HTMLAllCollection",
                        "preview_short": "HTMLAllCollection()",
                        "preview_long": "HTMLAllCollection()",
                        "readonly": True,
                        "inspectable": True,
                        "size": len(items),
                    }
                if hasattr(current, "__ink_devtools_bigint__"):
                    mark_clean(path)
                    return {
                        "type": "bigint",
                        "preview_short": f"{current.value}n",
                        "preview_long": f"{current.value}n",
                        "inspectable": False,
                    }
                if hasattr(current, "__ink_devtools_unknown__"):
                    mark_clean(path)
                    return {
                        "type": "unknown",
                        "preview_short": "[Exception]",
                        "preview_long": getattr(current, "__ink_devtools_unknown_preview__", "[Exception]"),
                        "inspectable": False,
                    }
                if hasattr(current, "__ink_devtools_react_lazy__"):
                    mark_unserializable(path)
                    payload = getattr(current, "_payload", None)
                    status = getattr(payload, "status", None)
                    if status is None:
                        legacy_status = getattr(payload, "_status", None)
                        status = "fulfilled" if legacy_status == 1 else "pending"
                    return {
                        "type": "react_lazy",
                        "name": "lazy()",
                        "preview_short": f"{status} lazy() {{…}}" if status == "fulfilled" else "lazy()",
                        "preview_long": f"{status} lazy() {{{getattr(payload, 'value', getattr(getattr(payload, '_result', None), 'default', '…'))!r}}}" if status == "fulfilled" else "lazy()",
                        "inspectable": True,
                        "_payload": serialize(payload, path + ["_payload"]),
                    }
                if hasattr(current, "then") and hasattr(current, "status"):
                    status = getattr(current, "status", "pending")
                    preview_short = f"{status} {type(current).__name__}" if status in {"pending", "fulfilled", "rejected"} else type(current).__name__
                    preview_long = preview_short
                    payload = {
                        "type": "thenable",
                        "name": preview_short,
                        "preview_short": preview_short,
                        "preview_long": preview_long,
                        "inspectable": True,
                    }
                    if status == "pending":
                        mark_clean(path)
                    else:
                        mark_unserializable(path)
                    if hasattr(current, "value"):
                        payload["value"] = serialize(current.value, path + ["value"])
                        if status == "fulfilled":
                            payload["preview_short"] = f"{status} {type(current).__name__} {{…}}"
                    if hasattr(current, "reason") and current.reason is not None:
                        payload["reason"] = serialize(current.reason, path + ["reason"])
                    return payload
                if hasattr(current, "status") and hasattr(current, "value") and hasattr(current, "reason"):
                    mark_unserializable(path)
                    return {
                        "type": "class_instance",
                        "name": type(current).__name__,
                        "preview_short": type(current).__name__,
                        "preview_long": type(current).__name__,
                        "inspectable": True,
                        "readonly": True,
                        **{key: serialize(value, path + [key]) for key, value in vars(current).items()},
                    }
                if hasattr(current, "__dict__") and not isinstance(current, type):
                    mark_unserializable(path)
                    return {
                        "type": "class_instance",
                        "name": type(current).__name__,
                        "preview_short": type(current).__name__,
                        "preview_long": type(current).__name__,
                        "inspectable": True,
                        "readonly": True,
                        **{key: serialize(value, path + [key]) for key, value in vars(current).items()},
                    }
                try:
                    import array as array_module

                    if isinstance(current, array_module.array):
                        mark_unserializable(path)
                        return {
                            **{index: serialize(value, path + [index]) for index, value in enumerate(list(current))},
                            "type": "typed_array",
                            "preview_short": f"array({len(current)})",
                            "preview_long": f"array({len(current)})",
                            "inspectable": True,
                            "size": len(current),
                        }
                except Exception:  # noqa: BLE001
                    pass
                if isinstance(current, bytearray):
                    mark_clean(path)
                    return {
                        "type": "array_buffer",
                        "preview_short": f"ArrayBuffer({len(current)})",
                        "preview_long": f"ArrayBuffer({len(current)})",
                        "inspectable": True,
                        "size": len(current),
                    }
                if isinstance(current, memoryview):
                    mark_clean(path)
                    return {
                        "type": "data_view",
                        "preview_short": f"DataView({len(current)})",
                        "preview_long": f"DataView({len(current)})",
                        "inspectable": True,
                        "size": len(current),
                    }
                if isinstance(current, set):
                    items = list(current)
                    mark_unserializable(path)
                    return {
                        **{index: serialize(value, path + [index]) for index, value in enumerate(items)},
                        "type": "iterator",
                        "name": "Set",
                        "preview_short": f"Set({len(items)})",
                        "preview_long": f"Set({len(items)}) {{{', '.join(repr(item) for item in items)}}}",
                        "inspectable": True,
                        "readonly": True,
                        "size": len(items),
                    }
                return repr(current)

            return {"data": serialize(value, list(base_path)), "cleaned": cleaned, "unserializable": unserializable}

        def build_snapshot():
            nodes.clear()
            id_map.clear()
            host_instance_map.clear()
            nodes.append({"id": "root", "displayName": "Root", "elementType": "host", "isErrorBoundary": False})

            def walk_dom(node, node_id="root", inherited_owners=None):
                inherited_owners = inherited_owners or []
                for index, child in enumerate(getattr(node, "childNodes", [])):
                    current_id = f"{node_id}.{index}"
                    own_owner_infos = list(getattr(child, "_owner_infos", []) or [])
                    owner_infos = own_owner_infos or list(inherited_owners)
                    for owner_index, owner in enumerate(own_owner_infos):
                        synthetic_id = f"{current_id}@{owner_index}"
                        synthetic_chain = list(reversed(own_owner_infos[: owner_index + 1]))
                        entry = {
                            "id": synthetic_id,
                            "displayName": owner["displayName"],
                            "elementType": owner["elementType"],
                            "isErrorBoundary": owner["isErrorBoundary"],
                            "props": owner["props"],
                            "state": owner["state"],
                            "componentID": owner["componentID"],
                            "source": owner["source"],
                            "ownerInfos": synthetic_chain,
                            "node": child,
                            "ownerIndex": owner_index,
                        }
                        nodes.append(entry)
                        id_map[synthetic_id] = entry
                    host_entry = {
                        "id": current_id,
                        "displayName": child.nodeName,
                        "elementType": "host",
                        "isErrorBoundary": False,
                        "props": getattr(child, "attributes", {}),
                        "node": child,
                        "ownerInfos": list(reversed(owner_infos)),
                        "source": owner_infos[-1]["source"] if owner_infos else [child.nodeName, "", 0],
                    }
                    nodes.append(host_entry)
                    id_map[current_id] = host_entry
                    host_instance_map[id(child)] = current_id
                    walk_dom(child, current_id, owner_infos)

            walk_dom(self.root_node)
            nodes.extend(
                [
                    {"id": "internal.app", "displayName": "InternalApp", "elementType": "function", "isErrorBoundary": False},
                    {"id": "internal.error", "displayName": "InternalErrorBoundary", "elementType": "function", "isErrorBoundary": True},
                ]
            )
            return {"rootID": "root", "nodes": nodes}

        def get_tree_snapshot():
            return build_snapshot()

        def get_display_name(node_id):
            build_snapshot()
            if node_id == "root":
                return "Root"
            return id_map.get(node_id, {}).get("displayName")

        def get_raw_data(entry):
            owner_infos = entry.get("ownerInfos", [])
            owner_start = 0 if entry.get("elementType") == "host" else 1
            raw = {
                "props": _safe_copy(entry.get("props", {})),
                "state": _safe_copy(entry.get("state", {})) if entry.get("state") is not None else None,
                "hooks": None,
                "owners": [{"id": f"{entry['id']}:owner:{index}", "displayName": owner["displayName"]} for index, owner in enumerate(owner_infos[owner_start:])],
                "source": entry.get("source"),
                "stack": [owner["source"] for owner in owner_infos] or [entry.get("source")],
                "suspendedBy": getattr(entry.get("node"), "_suspended_by", []),
                "canEditFunctionProps": False,
                "canEditHooks": False,
                "canToggleSuspense": any(owner.get("isSuspenseBoundary") for owner in owner_infos),
                "canToggleError": any(owner.get("isErrorBoundary") for owner in owner_infos),
            }
            component_id = entry.get("componentID") or getattr(entry.get("node"), "_component_instance_id", None)
            if component_id is not None:
                hook_state = hooks_runtime._hook_state.get(component_id)
                if hook_state is not None:
                    raw["hooks"] = []
                    for hook in hook_state.hooks:
                        raw["hooks"].append({"name": "State", "value": _safe_copy(hook)})
                    raw["canEditHooks"] = bool(raw["hooks"])
            return raw

        def dehydrate_hooks(hooks):
            cleaned = []
            unserializable = []
            data = []
            for index, hook in enumerate(hooks):
                value_transport = dehydrate(hook["value"], [index, "value"], wrap_root=True)
                cleaned.extend(value_transport["cleaned"])
                unserializable.extend(value_transport["unserializable"])
                data.append({"name": hook["name"], "value": value_transport["data"]})
            return {"data": data, "cleaned": cleaned, "unserializable": unserializable}

        def dehydrate_shell(value, base_path):
            if isinstance(value, dict):
                cleaned = []
                unserializable = []
                data = {}
                for key, item in value.items():
                    if isinstance(item, dict) and key == "resource":
                        child = dehydrate(item, base_path + [key], wrap_root=True)
                        data[key] = child["data"]
                        cleaned.extend(child["cleaned"])
                        unserializable.extend(child["unserializable"])
                    elif isinstance(item, dict):
                        child = dehydrate_shell(item, base_path + [key])
                        data[key] = child["data"]
                        cleaned.extend(child["cleaned"])
                        unserializable.extend(child["unserializable"])
                    elif isinstance(item, list):
                        child = dehydrate_shell(item, base_path + [key])
                        data[key] = child["data"]
                        cleaned.extend(child["cleaned"])
                        unserializable.extend(child["unserializable"])
                    else:
                        child = dehydrate(item, base_path + [key], wrap_root=True)
                        data[key] = child["data"]
                        cleaned.extend(child["cleaned"])
                        unserializable.extend(child["unserializable"])
                return {"data": data, "cleaned": cleaned, "unserializable": unserializable}
            if isinstance(value, list):
                cleaned = []
                unserializable = []
                data = []
                for index, item in enumerate(value):
                    if isinstance(item, (dict, list)):
                        child = dehydrate_shell(item, base_path + [index])
                    else:
                        child = dehydrate(item, base_path + [index], wrap_root=True)
                    data.append(child["data"])
                    cleaned.extend(child["cleaned"])
                    unserializable.extend(child["unserializable"])
                return {"data": data, "cleaned": cleaned, "unserializable": unserializable}
            return dehydrate(value, base_path, wrap_root=True)

        def inspect_target(entry, path):
            raw = get_raw_data(entry)
            def access(current, parts):
                for part in parts:
                    if isinstance(current, dict):
                        current = current[part]
                    elif isinstance(current, (list, tuple)):
                        current = current[part]
                    else:
                        current = getattr(current, part)
                return current
            if not path:
                value = {
                    "props": dehydrate(raw["props"], []),
                    "owners": raw["owners"],
                    "source": raw["source"],
                    "stack": raw["stack"],
                    "canEditFunctionProps": raw["canEditFunctionProps"],
                    "canEditHooks": raw["canEditHooks"],
                    "canToggleSuspense": raw["canToggleSuspense"],
                    "canToggleError": raw["canToggleError"],
                    "suspendedBy": dehydrate_shell(raw["suspendedBy"], []),
                }
                if raw["state"] is not None:
                    value["state"] = dehydrate(raw["state"], [])
                if raw["hooks"] is not None:
                    value["hooks"] = dehydrate_hooks(raw["hooks"])
                return {"type": "full-data", "value": value}
            root_key = path[0]
            root_value = raw.get(root_key)
            if root_key == "props":
                target = root_value if len(path) == 1 else access(root_value, path[1:])
            elif root_key == "state":
                target = root_value if len(path) == 1 else access(root_value, path[1:])
            elif root_key == "hooks":
                target = root_value if len(path) == 1 else access(root_value, path[1:])
            elif root_key == "suspendedBy":
                target = root_value if len(path) == 1 else access(root_value, path[1:])
            else:
                target = raw.get(root_key)
            wrap_root = not isinstance(target, dict)
            return {"type": "hydrated-path", "path": path, "value": dehydrate(target, path, wrap_root=wrap_root)}

        def inspect_element(request_id, node_id, path, force_full_data):
            build_snapshot()
            entry = id_map[node_id]
            payload = inspect_target(entry, list(path) if path else None)
            if not path and not force_full_data:
                signature = repr(payload)
                if inspect_cache.get(node_id) == signature:
                    return {"type": "no-change"}
                inspect_cache[node_id] = signature
            backend_state["lastSelectedElementID"] = node_id
            backend_state["lastSelectedRendererID"] = renderer_id
            if persisted_selection_match and persisted_selection_match.get("id") != node_id:
                clear_persisted_selection()
            return payload

        def inspect_screen(request_id, root_id, path, force_full_data):
            global_renderers = scope.get("__INK_DEVTOOLS_RENDERERS__", {})
            suspended_by = []
            for other_renderer in global_renderers.values():
                for node in getattr(other_renderer.root_node, "childNodes", []):
                    suspended_by.extend(getattr(node, "_suspended_by", []))
            payload = {
                "type": "full-data",
                "id": root_id,
                "value": {
                    "suspendedBy": dehydrate(suspended_by, []),
                },
            }
            if path:
                target = suspended_by if len(path) == 1 else get_in_object({"suspendedBy": suspended_by}, path)
                return {"type": "hydrated-path", "id": root_id, "path": path, "value": dehydrate(target, path)}
            return payload

        def schedule_update(node_id):
            self._force_rerender = True
            try:
                from .hooks.use_app import useApp

                app = useApp()
                if app is not None:
                    app.render(app._current_node)
            finally:
                self._force_rerender = False
            return True

        def _entry_component_id(entry):
            return entry.get("componentID") or getattr(entry.get("node"), "_component_instance_id", None)

        def override_props(node_id, path, value):
            build_snapshot()
            entry = id_map[node_id]
            component_id = _entry_component_id(entry)
            if component_id is None:
                return False
            props = _safe_copy(self._devtools_prop_overrides.get(component_id, entry.get("props", {})))
            updated = set_in_object(props, path, value)
            self._devtools_prop_overrides[component_id] = updated
            return True

        def rename_props(node_id, old_path, new_path):
            build_snapshot()
            entry = id_map[node_id]
            component_id = _entry_component_id(entry)
            if component_id is None:
                return False
            props = _safe_copy(self._devtools_prop_overrides.get(component_id, entry.get("props", {})))
            self._devtools_prop_overrides[component_id] = rename_path_in_object(props, old_path, new_path)
            return True

        def delete_props(node_id, path):
            build_snapshot()
            entry = id_map[node_id]
            component_id = _entry_component_id(entry)
            if component_id is None:
                return False
            props = _safe_copy(self._devtools_prop_overrides.get(component_id, entry.get("props", {})))
            self._devtools_prop_overrides[component_id] = delete_path_in_object(props, path)
            return True

        def override_hook_state(node_id, path, value):
            build_snapshot()
            entry = id_map[node_id]
            component_id = _entry_component_id(entry)
            if component_id is None:
                return False
            state = hooks_runtime._hook_state.get(component_id)
            if state is None:
                return False
            if len(path) == 1:
                state.hooks[path[0]] = value
            else:
                updated = set_in_object(_safe_copy(state.hooks[path[0]]), path[1:], value)
                state.hooks[path[0]] = updated
            return True

        def rename_hook_state(node_id, old_path, new_path):
            build_snapshot()
            entry = id_map[node_id]
            component_id = _entry_component_id(entry)
            if component_id is None:
                return False
            state = hooks_runtime._hook_state.get(component_id)
            if state is None:
                return False
            state.hooks[old_path[0]] = rename_path_in_object(_safe_copy(state.hooks[old_path[0]]), old_path[1:], new_path[1:])
            return True

        def delete_hook_state(node_id, path):
            build_snapshot()
            entry = id_map[node_id]
            component_id = _entry_component_id(entry)
            if component_id is None:
                return False
            state = hooks_runtime._hook_state.get(component_id)
            if state is None:
                return False
            state.hooks[path[0]] = delete_path_in_object(_safe_copy(state.hooks[path[0]]), path[1:])
            return True

        def override_value_at_path(value_type, node_id, hook_id, path, value):
            if value_type == "props":
                return override_props(node_id, path, value)
            if value_type == "state":
                build_snapshot()
                entry = id_map[node_id]
                component_id = _entry_component_id(entry)
                if component_id is None:
                    return False
                state_value = _safe_copy(self._devtools_state_overrides.get(component_id, entry.get("state", {})))
                self._devtools_state_overrides[component_id] = set_in_object(state_value, path, value)
                return True
            if value_type == "hooks":
                return override_hook_state(node_id, [hook_id] + list(path), value)
            return False

        def rename_path(value_type, node_id, hook_id, old_path, new_path):
            if value_type == "props":
                return rename_props(node_id, old_path, new_path)
            if value_type == "state":
                build_snapshot()
                entry = id_map[node_id]
                component_id = _entry_component_id(entry)
                if component_id is None:
                    return False
                state_value = _safe_copy(self._devtools_state_overrides.get(component_id, entry.get("state", {})))
                self._devtools_state_overrides[component_id] = rename_path_in_object(state_value, old_path, new_path)
                return True
            if value_type == "hooks":
                return rename_hook_state(node_id, [hook_id] + list(old_path), [hook_id] + list(new_path))
            return False

        def delete_path(value_type, node_id, hook_id, path):
            if value_type == "props":
                return delete_props(node_id, path)
            if value_type == "state":
                build_snapshot()
                entry = id_map[node_id]
                component_id = _entry_component_id(entry)
                if component_id is None:
                    return False
                state_value = _safe_copy(self._devtools_state_overrides.get(component_id, entry.get("state", {})))
                self._devtools_state_overrides[component_id] = delete_path_in_object(state_value, path)
                return True
            if value_type == "hooks":
                return delete_hook_state(node_id, [hook_id] + list(path))
            return False

        def get_serialized_element_value_by_path(node_id, path):
            build_snapshot()
            entry = id_map[node_id]
            raw = get_raw_data(entry)
            target = raw
            for part in path:
                target = target[part]
            return json.dumps(target) if isinstance(target, str) else repr(target)

        def clear_persisted_selection():
            nonlocal persisted_selection, persisted_selection_match, tracked_path
            persisted_selection = None
            persisted_selection_match = None
            tracked_path = None

        def get_path_for_element(node_id):
            build_snapshot()
            entry = id_map.get(node_id)
            if entry is None:
                return None
            owner_infos = list(reversed(entry.get("ownerInfos", [])))
            return [{"id": info["componentID"], "displayName": info["displayName"]} for info in owner_infos] or [{"id": node_id, "displayName": entry["displayName"]}]

        def override_suspense(node_id, force_fallback):
            build_snapshot()
            entry = id_map[node_id]
            suspense_owner = next((info for info in entry.get("ownerInfos", []) if info.get("isSuspenseBoundary")), None)
            if suspense_owner is None:
                return False
            if force_fallback:
                self._forced_suspense_ids.add(suspense_owner["componentID"])
            else:
                self._forced_suspense_ids.discard(suspense_owner["componentID"])
            schedule_update(node_id)
            return True

        def override_error(node_id, force_error):
            build_snapshot()
            entry = id_map.get(node_id)
            if entry is None:
                if not force_error and self._forced_error_ids:
                    for boundary_id, state_value in list(self._forced_error_state.items()):
                        self._devtools_state_overrides[boundary_id] = _safe_copy(state_value)
                    self._forced_error_ids.clear()
                    self._forced_error_state.clear()
                    from .hooks.use_app import useApp

                    app = useApp()
                    if app is not None:
                        app.render(app._current_node)
                    return True
                return False
            error_owner = next((info for info in entry.get("ownerInfos", []) if info.get("isErrorBoundary")), None)
            if error_owner is None:
                return False
            boundary_id = error_owner["componentID"]
            if force_error:
                self._forced_error_ids.add(boundary_id)
                class_instance = error_owner.get("classInstance")
                if class_instance is not None:
                    self._forced_error_state[boundary_id] = _safe_copy(getattr(class_instance, "state", {}))
            else:
                self._forced_error_ids.discard(boundary_id)
                if boundary_id in self._forced_error_state:
                    restored_state = _safe_copy(self._forced_error_state.pop(boundary_id))
                    self._devtools_state_overrides[boundary_id] = restored_state
                    class_instance = error_owner.get("classInstance")
                    if class_instance is not None:
                        class_instance.state = _safe_copy(restored_state)
            schedule_update(node_id)
            return True

        def schedule_retry(node_id):
            return schedule_update(node_id)

        def log_notification(event, payload):
            backend_state["lastNotification"] = {"event": event, **payload}
            backend_notification_log.append({"event": event, **payload})

        def dispatch_bridge(message):
            if message.get("type") == "request" and message.get("event") == "inspectElement":
                return handle_inspect_element_bridge_call(message, inspect_element)
            if message.get("type") == "request" and message.get("event") == "inspectScreen":
                return handle_inspect_screen_bridge_call(message, inspect_screen)
            if message.get("type") == "request":
                event = message.get("event")
                payload = message.get("payload", {})
                if event == "overrideValueAtPath":
                    return make_bridge_response(
                        "overrideValueAtPath",
                        {"ok": True, "failure": None, "value": override_value_at_path(payload["valueType"], payload["id"], payload.get("hookID"), payload["path"], payload["value"])},
                        message["requestId"],
                    )
                if event == "scheduleUpdate":
                    return make_bridge_response(
                        "scheduleUpdate",
                        {"ok": True, "failure": None, "value": schedule_update(payload["id"])},
                        message["requestId"],
                    )
                if event == "overrideProps":
                    return make_bridge_response(
                        "overrideProps",
                        {"ok": True, "failure": None, "value": False if payload.get("wasForwarded") else override_props(payload["id"], payload["path"], payload["value"])},
                        message["requestId"],
                    )
                if event == "overrideHookState":
                    return make_bridge_response(
                        "overrideHookState",
                        {"ok": True, "failure": None, "value": override_hook_state(payload["id"], [payload["hookID"]] + list(payload["path"]), payload["value"])},
                        message["requestId"],
                    )
                if event == "overrideState":
                    return make_bridge_response(
                        "overrideState",
                        {"ok": True, "failure": None, "value": override_value_at_path("state", payload["id"], None, payload["path"], payload["value"])},
                        message["requestId"],
                    )
                return make_bridge_response(event, {"ok": False, "failure": {"error_type": "LookupError"}}, message["requestId"])
            if message.get("type") == "notification":
                event = message.get("event")
                payload = message.get("payload", {})
                if event == "copyElementPath":
                    _copy_element_path(payload)
                    return None
                if event == "storeAsGlobal":
                    _store_as_global(payload)
                    return None
                if event == "clearErrorsAndWarnings":
                    log_notification("clearErrorsAndWarnings", payload)
                    return None
                if event == "clearWarningsForElementID":
                    log_notification("clearWarningsForElementID", payload)
                    return None
                if event == "overrideSuspenseMilestone":
                    _override_suspense_milestone(payload)
                    return None
            call_handlers = {
                "overrideValueAtPath": lambda payload, raw: make_bridge_response(
                    "overrideValueAtPath",
                    {"ok": True, "failure": None, "value": override_value_at_path(payload["valueType"], payload["id"], payload.get("hookID"), payload["path"], payload["value"])},
                    message["requestId"],
                ),
                "scheduleUpdate": lambda payload, raw: make_bridge_response(
                    "scheduleUpdate",
                    {"ok": True, "failure": None, "value": schedule_update(payload["id"])},
                    message["requestId"],
                ),
                "overrideProps": lambda payload, raw: make_bridge_response(
                    "overrideProps",
                    {"ok": True, "failure": None, "value": False if payload.get("wasForwarded") else override_props(payload["id"], payload["path"], payload["value"])},
                    message["requestId"],
                ),
                "overrideHookState": lambda payload, raw: make_bridge_response(
                    "overrideHookState",
                    {"ok": True, "failure": None, "value": override_hook_state(payload["id"], [payload["hookID"]] + list(payload["path"]), payload["value"])},
                    message["requestId"],
                ),
                "overrideState": lambda payload, raw: make_bridge_response(
                    "overrideState",
                    {"ok": True, "failure": None, "value": override_value_at_path("state", payload["id"], None, payload["path"], payload["value"])},
                    message["requestId"],
                ),
            }
            notification_handlers = {
                "copyElementPath": lambda payload, raw: _copy_element_path(payload),
                "storeAsGlobal": lambda payload, raw: _store_as_global(payload),
                "clearErrorsAndWarnings": lambda payload, raw: log_notification("clearErrorsAndWarnings", payload),
                "clearWarningsForElementID": lambda payload, raw: log_notification("clearWarningsForElementID", payload),
                "overrideSuspenseMilestone": lambda payload, raw: _override_suspense_milestone(payload),
            }
            response = dispatch_bridge_message(message, call_handlers=call_handlers, notification_handlers=notification_handlers)
            return response

        def _copy_element_path(payload):
            nonlocal last_copied_value
            last_copied_value = get_serialized_element_value_by_path(payload["id"], payload["path"])
            scope["__INK_DEVTOOLS_LAST_COPIED_VALUE__"] = last_copied_value
            log_notification("copyElementPath", payload)

        def _store_as_global(payload):
            build_snapshot()
            entry = id_map[payload["id"]]
            raw = get_raw_data(entry)
            value = raw
            for part in payload["path"]:
                value = value[part]
            key = f"$reactTemp{payload['count']}"
            stored_globals[key] = value
            scope[key] = value
            log_notification("storeAsGlobal", payload)

        def _override_suspense_milestone(payload):
            self._forced_suspense_ids.clear()
            build_snapshot()
            for suspense_id in payload["suspendedSet"]:
                entry = id_map.get(suspense_id)
                if entry and entry.get("componentID"):
                    self._forced_suspense_ids.add(entry["componentID"])
            schedule_update("root")
            log_notification("overrideSuspenseMilestone", payload)

        def get_id_for_host_instance(host_instance, find_nearest_unfiltered_ancestor=False):
            build_snapshot()
            current = host_instance
            while current is not None:
                host_id = host_instance_map.get(id(current))
                if host_id is not None:
                    if find_nearest_unfiltered_ancestor:
                        entry = id_map[host_id]
                        suspense_owner = next((info for info in entry.get("ownerInfos", []) if info.get("isSuspenseBoundary")), None)
                        if suspense_owner is not None:
                            for snapshot_entry in nodes:
                                if snapshot_entry.get("componentID") == suspense_owner["componentID"]:
                                    return {"id": snapshot_entry["id"], "rendererID": renderer_id}
                    return {"id": host_id, "rendererID": renderer_id}
                current = getattr(current, "parentNode", None)
            return None

        def get_component_name_for_host_instance(host_instance):
            match = get_id_for_host_instance(host_instance)
            return id_map[match["id"]]["displayName"] if match is not None else None

        def inspect_element_agent(payload):
            nonlocal persisted_selection, persisted_selection_match
            if persisted_selection_match and persisted_selection_match.get("id") != payload["id"]:
                clear_persisted_selection()
            response = dispatch_bridge(make_bridge_call("inspectElement", payload, payload.get("requestID")))
            return response

        def agent_call(method_name, payload):
            return dispatch_bridge(make_bridge_call(method_name, payload, payload.get("requestID")))

        def agent_notification(method_name, payload):
            return dispatch_bridge(make_bridge_notification(method_name, payload))

        renderer = {
            "bundleType": 1,
            "rendererPackageName": "pyinkcli",
            "version": "0.1.0",
            "reconcilerVersion": "0.1.0",
            "rendererConfig": {
                "supportsClassComponents": True,
                "supportsErrorBoundaries": True,
                "supportsCommitPhaseErrorRecovery": True,
            },
            "getTreeSnapshot": get_tree_snapshot,
            "getRootID": lambda: "root",
            "getDisplayNameForNode": get_display_name,
            "overrideProps": override_props,
            "overridePropsRenamePath": rename_props,
            "overridePropsDeletePath": delete_props,
            "overrideHookState": override_hook_state,
            "overrideHookStateRenamePath": rename_hook_state,
            "overrideHookStateDeletePath": delete_hook_state,
            "scheduleUpdate": schedule_update,
            "scheduleRetry": schedule_retry,
            "inspectElement": inspect_element,
            "inspectScreen": inspect_screen,
            "getSerializedElementValueByPath": get_serialized_element_value_by_path,
            "overrideValueAtPath": override_value_at_path,
            "renamePath": rename_path,
            "deletePath": delete_path,
            "overrideSuspense": override_suspense,
            "overrideError": override_error,
            "getLastCopiedValue": lambda: last_copied_value,
            "getStoredGlobals": lambda: stored_globals,
            "getBackendNotificationLog": lambda: backend_notification_log,
            "getLastLoggedElement": lambda: last_logged_element,
            "getTrackedPath": lambda: tracked_path,
        }
        renderer["backend"] = {
            "backendState": backend_state,
            "dispatchBridgeMessage": dispatch_bridge,
            "inspectElement": inspect_element_agent,
            "overrideProps": lambda payload: agent_call("overrideProps", payload),
            "scheduleUpdate": lambda payload: agent_call("scheduleUpdate", payload),
            "copyElementPath": lambda payload: agent_notification("copyElementPath", payload),
            "getOwnersList": lambda payload: make_bridge_response(
                "ownersList",
                {"ok": True, "failure": None, "owners": inspect_target(id_map[payload["id"]], None)["value"]["owners"]},
                payload.get("requestID"),
            ),
            "getBackendVersion": lambda payload: make_bridge_response(
                "backendVersion",
                {"ok": True, "failure": None, "version": renderer["version"]},
                payload.get("requestID"),
            ),
            "getBridgeProtocol": lambda payload: make_bridge_response(
                "bridgeProtocol",
                {"ok": True, "failure": None, "bridgeProtocol": {"version": 2}},
                payload.get("requestID"),
            ),
            "logElementToConsole": lambda payload: (
                scope.__setitem__("__INK_DEVTOOLS_LAST_LOGGED_ELEMENT__", {"id": payload["id"], "rendererID": payload["rendererID"]}),
                log_notification("logElementToConsole", payload),
                locals().update(),
            ) and None,
            "getProfilingStatus": lambda payload: make_bridge_response(
                "profilingStatus",
                {"ok": True, "failure": None, "isProfiling": False},
                payload.get("requestID"),
            ),
            "getIDForHostInstance": get_id_for_host_instance,
            "getComponentNameForHostInstance": get_component_name_for_host_instance,
            "getProfilingData": lambda payload: make_bridge_response(
                "profilingData",
                {"ok": True, "failure": None, "rendererID": renderer_id, "timelineData": None, "dataForRoots": [{"rootID": "root"}]},
                payload.get("requestID"),
            ),
            "getPathForElement": get_path_for_element,
            "setTrackedPath": lambda path: globals().update() or None,
            "stopInspectingNative": lambda host_selected: (
                backend_state.__setitem__("lastStopInspectingHostSelected", host_selected),
                scope.__setitem__("__INK_DEVTOOLS_STOP_INSPECTING_HOST__", host_selected),
            ) and None,
            "setPersistedSelection": lambda payload: _set_persisted_selection(payload),
            "getPersistedSelection": lambda: persisted_selection,
            "setPersistedSelectionMatch": lambda payload: _set_persisted_selection_match(payload),
            "getPersistedSelectionMatch": lambda: persisted_selection_match,
            "clearPersistedSelection": clear_persisted_selection,
        }

        def _set_persisted_selection(payload):
            nonlocal persisted_selection, tracked_path
            persisted_selection = payload
            tracked_path = payload.get("path")

        def _set_persisted_selection_match(payload):
            nonlocal persisted_selection_match
            persisted_selection_match = payload

        def _set_tracked_path(path):
            nonlocal tracked_path
            tracked_path = path

        def _log_element_to_console(payload):
            nonlocal last_logged_element
            last_logged_element = {"id": payload["id"], "rendererID": payload["rendererID"]}
            scope["__INK_DEVTOOLS_LAST_LOGGED_ELEMENT__"] = last_logged_element
            log_notification("logElementToConsole", payload)

        renderer["backend"]["setTrackedPath"] = _set_tracked_path
        renderer["backend"]["logElementToConsole"] = _log_element_to_console
        scope["__INK_RECONCILER_DEVTOOLS_METADATA__"] = renderer
        return True


def createReconciler(root_node):
    return _Reconciler(root_node)


__all__ = [
    "batchedUpdates",
    "consumePendingRerenderPriority",
    "createReconciler",
    "discreteUpdates",
]
