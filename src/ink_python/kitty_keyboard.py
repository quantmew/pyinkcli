"""Kitty keyboard protocol helpers."""

from __future__ import annotations

kittyFlags = {
    "disambiguateEscapeCodes": 1,
    "reportEventTypes": 2,
    "reportAlternateKeys": 4,
    "reportAllKeysAsEscapeCodes": 8,
    "reportAssociatedText": 16,
}


def resolveFlags(flags: list[str]) -> int:
    result = 0
    for flag in flags:
        result |= kittyFlags[flag]
    return result


kittyModifiers = {
    "shift": 1,
    "alt": 2,
    "ctrl": 4,
    "super": 8,
    "hyper": 16,
    "meta": 32,
    "capsLock": 64,
    "numLock": 128,
}
