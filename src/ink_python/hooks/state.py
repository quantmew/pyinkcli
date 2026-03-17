"""
State management hooks for ink-python.

Provides React-like state management for Python.
"""

from __future__ import annotations

from typing import Any, Callable, Generic, List, Optional, Tuple, TypeVar, Union
from dataclasses import dataclass, field
from functools import wraps

T = TypeVar("T")
Deps = Tuple[Any, ...]


@dataclass
class HookState:
    """State for a single hook."""
    index: int = 0
    states: List[Any] = field(default_factory=list)
    effects: List[Tuple[Callable, Deps, Optional[Callable]]] = field(default_factory=list)
    refs: dict[int, Any] = field(default_factory=dict)
    memos: dict[int, Tuple[Any, Deps]] = field(default_factory=dict)


# Current component state (thread-local in real implementation)
_current_state: Optional[HookState] = None

# Global rerender callback set by the runtime
_rerender_callback: Optional[Callable[[], None]] = None


def _get_current_state() -> HookState:
    """Get or create the current hook state."""
    global _current_state
    if _current_state is None:
        _current_state = HookState()
    return _current_state


def _reset_hook_state() -> None:
    """Reset hook state (called at start of render)."""
    global _current_state
    if _current_state is not None:
        _current_state.index = 0


def _set_rerender_callback(callback: Optional[Callable[[], None]]) -> None:
    """Set the global rerender callback used by state setters."""
    global _rerender_callback
    _rerender_callback = callback


def useState(
    initial_value: Union[T, Callable[[], T]],
) -> Tuple[T, Callable[[Union[T, Callable[[T], T]]], None]]:
    """
    Hook for managing state.

    Args:
        initial_value: Initial state value or function returning initial value.

    Returns:
        Tuple of (current_value, setter_function).

    Example:
        count, setCount = useState(0)
        setCount(count + 1)
        setCount(lambda c: c + 1)  # Functional update
    """
    state = _get_current_state()
    index = state.index
    state.index += 1

    # Initialize state if needed
    if index >= len(state.states):
        if callable(initial_value):
            state.states.append(initial_value())
        else:
            state.states.append(initial_value)

    current_value = state.states[index]

    def set_value(new_value: Union[T, Callable[[T], T]]) -> None:
        if callable(new_value):
            state.states[index] = new_value(state.states[index])
        else:
            state.states[index] = new_value

        if _rerender_callback is not None:
            _rerender_callback()

    return (current_value, set_value)


def useEffect(
    effect: Callable[[], Optional[Callable[[], None]]],
    deps: Optional[Deps] = None,
) -> None:
    """
    Hook for side effects.

    Args:
        effect: Function to run on mount/update. Can return a cleanup function.
        deps: Dependencies array. Effect runs when deps change. None = every render.

    Example:
        useEffect(lambda: print("Mounted"), ())
        useEffect(lambda: ...return cleanup..., [count])
    """
    state = _get_current_state()
    index = state.index
    state.index += 1

    # Check if we need to run the effect
    should_run = True
    old_effect = None

    if index < len(state.effects):
        old_effect = state.effects[index]
        old_deps = old_effect[1]

        if deps is not None and old_deps is not None:
            # Compare dependencies
            should_run = len(deps) != len(old_deps) or any(
                d is not od or d != od
                for d, od in zip(deps, old_deps)
            )
    else:
        # First run
        while len(state.effects) <= index:
            state.effects.append((None, (), None))

    if should_run:
        # Run cleanup from previous effect
        if old_effect and old_effect[2] is not None:
            try:
                old_effect[2]()
            except Exception:
                pass

        # Run new effect
        cleanup = effect()
        state.effects[index] = (effect, deps or (), cleanup)


def useRef(initial_value: Optional[T] = None) -> "Ref[T]":
    """
    Hook for a mutable reference.

    Args:
        initial_value: Initial value for the ref.

    Returns:
        A ref object with .current property.

    Example:
        input_ref = useRef(None)
        input_ref.current = "value"
    """
    state = _get_current_state()
    index = state.index
    state.index += 1

    if index not in state.refs:
        state.refs[index] = Ref(initial_value)

    return state.refs[index]


@dataclass
class Ref(Generic[T]):
    """Mutable reference object."""
    current: Optional[T] = None


def useMemo(
    factory: Callable[[], T],
    deps: Deps,
) -> T:
    """
    Hook for memoizing values.

    Args:
        factory: Function to compute the value.
        deps: Dependencies array.

    Returns:
        The memoized value.

    Example:
        expensive_value = useMemo(lambda: compute(x), (x,))
    """
    state = _get_current_state()
    index = state.index
    state.index += 1

    # Check if we need to recompute
    should_recompute = True

    if index in state.memos:
        old_value, old_deps = state.memos[index]
        if len(deps) == len(old_deps):
            should_recompute = any(
                d is not od or d != od
                for d, od in zip(deps, old_deps)
            )
        if not should_recompute:
            return old_value

    # Compute new value
    new_value = factory()
    state.memos[index] = (new_value, deps)
    return new_value


def useCallback(
    callback: Callable,
    deps: Deps,
) -> Callable:
    """
    Hook for memoizing callbacks.

    Args:
        callback: The callback function.
        deps: Dependencies array.

    Returns:
        The memoized callback.

    Example:
        handler = useCallback(lambda: do_something(x), (x,))
    """
    return useMemo(lambda: callback, deps)


def useReducer(
    reducer: Callable[[T, Any], T],
    initial_state: T,
    init: Optional[Callable[[T], T]] = None,
) -> Tuple[T, Callable[[Any], None]]:
    """
    Hook for state management with a reducer.

    Args:
        reducer: Function (state, action) -> new_state.
        initial_state: Initial state value.
        init: Optional function to initialize state.

    Returns:
        Tuple of (state, dispatch_function).

    Example:
        def reducer(state, action):
            if action == "increment":
                return state + 1
            return state

        count, dispatch = useReducer(reducer, 0)
        dispatch("increment")
    """
    if init is not None:
        initial_state = init(initial_state)

    state, set_state = useState(initial_state)

    def dispatch(action: Any) -> None:
        set_state(lambda s: reducer(s, action))

    return (state, dispatch)
