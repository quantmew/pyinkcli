"""Compatibility facade for the internal hooks runtime."""

from ink_python.hooks._runtime import (
    Ref,
    useCallback,
    useEffect,
    useMemo,
    useReducer,
    useRef,
    useState,
)

__all__ = ["useState", "useEffect", "useRef", "useMemo", "useCallback", "useReducer", "Ref"]
