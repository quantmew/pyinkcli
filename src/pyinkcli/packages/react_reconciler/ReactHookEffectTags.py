"""Hook effect tag constants aligned with ReactHookEffectTags."""

from pyinkcli.hooks._runtime import (
    HookHasEffect as HasEffect,
    HookInsertion as Insertion,
    HookLayout as Layout,
    HookPassive as Passive,
)

__all__ = ["HasEffect", "Insertion", "Layout", "Passive"]
