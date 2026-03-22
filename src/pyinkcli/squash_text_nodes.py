from __future__ import annotations

import inspect

from .sanitize_ansi import sanitizeAnsi


def squashTextNodes(node) -> str:
    parts: list[str] = []
    for index, child in enumerate(getattr(node, "childNodes", [])):
        if getattr(child, "nodeName", None) == "#text":
            parts.append(sanitizeAnsi(child.nodeValue))
            continue
        text = squashTextNodes(child)
        transform = getattr(child, "internal_transform", None)
        if callable(transform):
            try:
                if len(inspect.signature(transform).parameters) >= 2:
                    text = transform(text, index)
                else:
                    text = transform(text)
            except (TypeError, ValueError):
                text = transform(text)
        parts.append(text)
    return "".join(parts)


__all__ = ["squashTextNodes"]

