"""Public hook entrypoints aligned with ReactHooks."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from pyinkcli.hooks._runtime import Ref
from pyinkcli.packages.react.dispatcher import resolveDispatcher

T = TypeVar("T")


def useContext(context: Any) -> Any:
    return resolveDispatcher().useContext(context)


def useState(initial_state: T | Callable[[], T]) -> tuple[T, Callable[[T | Callable[[T], T]], None]]:
    return resolveDispatcher().useState(initial_state)


def useEffect(
    create: Callable[[], Callable[[], None] | None],
    deps: tuple[Any, ...] | None = None,
) -> None:
    return resolveDispatcher().useEffect(create, deps)


def useLayoutEffect(
    create: Callable[[], Callable[[], None] | None],
    deps: tuple[Any, ...] | None = None,
) -> None:
    return resolveDispatcher().useLayoutEffect(create, deps)


def useInsertionEffect(
    create: Callable[[], Callable[[], None] | None],
    deps: tuple[Any, ...] | None = None,
) -> None:
    return resolveDispatcher().useInsertionEffect(create, deps)


def useRef(initial_value: T | None = None) -> Ref[T]:
    return resolveDispatcher().useRef(initial_value)


def useMemo(factory: Callable[[], T], deps: tuple[Any, ...]) -> T:
    return resolveDispatcher().useMemo(factory, deps)


def useCallback(callback: Callable[..., T], deps: tuple[Any, ...]) -> Callable[..., T]:
    return resolveDispatcher().useCallback(callback, deps)


def useReducer(
    reducer: Callable[[T, Any], T],
    initial_arg: T,
    init: Callable[[T], T] | None = None,
) -> tuple[T, Callable[[Any], None]]:
    return resolveDispatcher().useReducer(reducer, initial_arg, init)


def useTransition() -> tuple[bool, Callable[[Callable[[], None]], None]]:
    return resolveDispatcher().useTransition()


def useDebugValue(value: Any, formatterFn: Callable[[Any], Any] | None = None) -> None:
    del value, formatterFn


def useImperativeHandle(
    ref: Any,
    create: Callable[[], Any],
    deps: tuple[Any, ...] | None = None,
) -> None:
    def assign_ref() -> Callable[[], None]:
        value = create()
        if isinstance(ref, dict):
            ref["current"] = value
        elif hasattr(ref, "current"):
            ref.current = value
        elif callable(ref):
            ref(value)

        def cleanup() -> None:
            if isinstance(ref, dict):
                ref["current"] = None
            elif hasattr(ref, "current"):
                ref.current = None
            elif callable(ref):
                ref(None)

        return cleanup

    useLayoutEffect(assign_ref, deps)


def useDeferredValue(value: T, initialValue: T | None = None) -> T:
    del initialValue
    return value


def useId() -> str:
    id_ref = useRef(None)
    if id_ref.current is None:
        counter_ref = getattr(useId, "_counter", 0) + 1
        setattr(useId, "_counter", counter_ref)
        id_ref.current = f":r{counter_ref:x}:"
    return id_ref.current


def useSyncExternalStore(
    subscribe: Callable[[Callable[[], None]], Callable[[], None]],
    getSnapshot: Callable[[], T],
    getServerSnapshot: Callable[[], T] | None = None,
) -> T:
    del getServerSnapshot
    snapshot, setSnapshot = useState(getSnapshot)

    def bind() -> Callable[[], None]:
        def handle_store_change() -> None:
            setSnapshot(getSnapshot())

        return subscribe(handle_store_change)

    useEffect(bind, (subscribe, getSnapshot))
    return snapshot


def useEffectEvent(callback: Callable[..., T]) -> Callable[..., T]:
    callback_ref = useRef(callback)
    callback_ref.current = callback
    return useCallback(lambda *args, **kwargs: callback_ref.current(*args, **kwargs), ())


__all__ = [
    "Ref",
    "useCallback",
    "useContext",
    "useDebugValue",
    "useDeferredValue",
    "useEffect",
    "useEffectEvent",
    "useId",
    "useImperativeHandle",
    "useInsertionEffect",
    "useLayoutEffect",
    "useMemo",
    "useReducer",
    "useRef",
    "useState",
    "useSyncExternalStore",
    "useTransition",
]
