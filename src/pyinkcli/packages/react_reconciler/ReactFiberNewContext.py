from __future__ import annotations

_currently_reading_fiber = None


def prepareToReadContext(fiber) -> None:
    global _currently_reading_fiber
    _currently_reading_fiber = fiber
    fiber.dependencies = []


def finishReadingContext() -> None:
    global _currently_reading_fiber
    _currently_reading_fiber = None


def readContext(context):
    value = getattr(context, "current_value", context.default_value)
    if _currently_reading_fiber is not None:
        _currently_reading_fiber.dependencies.append((context, value))
    return value


def pushProvider(reconciler, context, value) -> None:
    stack = getattr(reconciler, "_context_provider_stack", [])
    stack.append((context, context.current_value))
    reconciler._context_provider_stack = stack
    context.current_value = value


def popProvider(reconciler, context) -> None:
    stack = getattr(reconciler, "_context_provider_stack", [])
    while stack:
        ctx, previous = stack.pop()
        if ctx is context:
            context.current_value = previous
            break
    reconciler._context_provider_stack = stack


def checkIfContextChanged(dependencies) -> bool:
    if not dependencies:
        return False
    return any(getattr(context, "current_value", None) != value for context, value in dependencies)

