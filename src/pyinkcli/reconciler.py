from __future__ import annotations

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


class _Reconciler:
    def __init__(self, root_node) -> None:
        self.root_node = root_node
        self._commit_handlers = {"on_commit": None, "on_immediate_commit": None}
        self._root_fiber = SimpleNamespace(child=None)
        self._last_prepared_commit = None
        self._last_root_completion_state = None
        self._last_root_commit_suspended = None

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
        has_static = any(getattr(child, "internal_static", False) for child in container.root.childNodes)
        if has_static and self._commit_handlers["on_immediate_commit"]:
            self._commit_handlers["on_immediate_commit"]()
        elif self._commit_handlers["on_commit"]:
            self._commit_handlers["on_commit"]()

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
            try:
                if not vnode.children:
                    return None
                return self._render_component(vnode.children[0], f"{instance_id}:suspense")
            except SuspendSignal:
                return vnode.props.get("fallback")
        if vnode.type == "__router_provider__":
            with react_router._push_router_context(vnode.props["internal_router_context"]):
                if not vnode.children:
                    return None
                return self._render_component(vnode.children[0], instance_id)
        if isinstance(vnode.type, type) and issubclass(vnode.type, _Component):
            instance = vnode.type(props=vnode.props)
            result = instance.render()
            if isinstance(result, RenderableNode):
                result._class_instance = instance
            return result
        if callable(vnode.type):
            component_instance_id = f"{instance_id}:{getattr(vnode.type, '__name__', 'anonymous')}"
            hooks_runtime._begin_component_render(component_instance_id, vnode.type)
            try:
                result = vnode.type(*vnode.children, **vnode.props)
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
            result = self._reconcile_node(existing, rendered, instance_id)
            if result is not None and callable(vnode.type):
                result._component_type = vnode.type
                result._component_props = dict(vnode.props)
                result._component_instance_id = f"{instance_id}:{getattr(vnode.type, '__name__', 'anonymous')}"
            return result
        if existing and getattr(existing, "nodeName", None) == vnode.type:
            node = existing
        else:
            if existing is not None:
                self._detach_ref(getattr(existing, "ref", None))
            node = createNode(vnode.type)
        node.key = vnode.key
        previous_ref = getattr(node, "ref", None)
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

    def _abort_container_render(self, container, reason="aborted") -> None:
        state = container.render_state
        if state is not None:
            state.status = "aborted"
            state.abort_reason = reason
        container.render_state = None

    def injectIntoDevTools(self) -> bool:
        from builtins import __dict__ as builtins_dict
        from .packages.react_devtools_core.backend import initializeBackend
        from .packages.react_devtools_core.window_polyfill import installDevtoolsWindowPolyfill

        if not initializeBackend():
            return False
        scope = installDevtoolsWindowPolyfill()
        nodes = []
        id_map = {}

        def walk_dom(node, node_id="root"):
            if node_id == "root":
                nodes.append({"id": "root", "displayName": "Root", "elementType": "host", "isErrorBoundary": False})
            for index, child in enumerate(getattr(node, "childNodes", [])):
                current_id = f"{node_id}.{index}"
                component_type = getattr(child, "_component_type", None)
                display_name = (
                    getattr(component_type, "__name__", child.nodeName)
                    if component_type is not None
                    else child.nodeName
                )
                element_type = "class" if isinstance(component_type, type) and issubclass(component_type, _Component) else "function" if callable(component_type) else "host"
                entry = {
                    "id": current_id,
                    "displayName": display_name,
                    "elementType": element_type,
                    "isErrorBoundary": display_name in {"InternalErrorBoundary", "ErrorBoundary"},
                    "props": getattr(child, "_component_props", getattr(child, "props", {})),
                    "node": child,
                }
                nodes.append(entry)
                id_map[current_id] = entry
                walk_dom(child, current_id)

        walk_dom(self.root_node)
        nodes.extend(
            [
                {"id": "internal.app", "displayName": "InternalApp", "elementType": "function", "isErrorBoundary": False},
                {"id": "internal.error", "displayName": "InternalErrorBoundary", "elementType": "function", "isErrorBoundary": True},
            ]
        )

        def get_tree_snapshot():
            return {"rootID": "root", "nodes": nodes}

        def get_display_name(node_id):
            for node in nodes:
                if node["id"] == node_id:
                    return node["displayName"]
            return None

        def override_props(node_id, path, value):
            entry = id_map[node_id]
            props = entry["props"]
            current = props
            for part in path[:-1]:
                current = current[part]
            current[path[-1]] = value
            from .hooks.use_app import useApp

            app = useApp()
            if app is not None and getattr(app._current_node, "type", None) is entry["node"]._component_type:
                app._current_node.props = props
            return True

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

        def override_hook_state(node_id, path, value):
            entry = id_map[node_id]
            component_id = getattr(entry["node"], "_component_instance_id", None)
            if component_id is None:
                return False
            state = hooks_runtime._hook_state.get(component_id)
            if state is None:
                return False
            index = path[0]
            state.hooks[index] = value
            return True

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
            "getDisplayNameForNode": get_display_name,
            "overrideProps": override_props,
            "overridePropsRenamePath": lambda node_id, old_path, new_path: True,
            "overridePropsDeletePath": lambda node_id, path: True,
            "overrideHookState": override_hook_state,
            "overrideHookStateRenamePath": lambda node_id, old_path, new_path: True,
            "overrideHookStateDeletePath": lambda node_id, path: True,
            "scheduleUpdate": schedule_update,
            "scheduleRetry": lambda node_id: True,
            "inspectElement": lambda rendererID, id, path, forceFullData: {"value": {"props": {"data": id_map.get(id, {}).get("props", {})}}},
        }
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
