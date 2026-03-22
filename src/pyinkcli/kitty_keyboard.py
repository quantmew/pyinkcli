from __future__ import annotations

kittyModifiers = {
    "shift": 1,
    "alt": 2,
    "ctrl": 4,
    "super": 8,
    "hyper": 16,
    "meta": 2,
    "capsLock": 64,
    "numLock": 128,
}

kittyFlags = {
    "disambiguateEscapeCodes": 1,
    "reportEventTypes": 2,
    "reportAlternateKeys": 4,
    "reportAllKeysAsEscapeCodes": 8,
    "reportAssociatedText": 16,
}


def resolveFlags(options: dict[str, bool] | None) -> int:
    if not options:
        return 0
    result = 0
    for key, enabled in options.items():
        if enabled:
            result |= kittyFlags.get(key, 0)
    return result


__all__ = ["kittyFlags", "kittyModifiers", "resolveFlags"]

