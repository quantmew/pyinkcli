from __future__ import annotations

from .components import _accessibility_runtime
from .components.Text import ANSI_BG_OPEN
from .squash_text_nodes import squashTextNodes

OutputTransformer = object


def indentString(text: str, count: int, indent: str = " ") -> str:
    prefix = indent * count
    return "\n".join(prefix + line for line in text.splitlines())


def applyPaddingToText(text: str, left: int = 0, right: int = 0) -> str:
    return "\n".join((" " * left) + line + (" " * right) for line in text.splitlines())


def _direct_text(node) -> str:
    parts: list[str] = []
    for child in getattr(node, "childNodes", []):
        if getattr(child, "aria_hidden", False):
            continue
        if getattr(child, "aria_role", None):
            continue
        if getattr(child, "nodeName", None) == "#text":
            parts.append(child.nodeValue)
        else:
            parts.append(_direct_text(child))
    return "".join(parts)


def _screen_reader_lines(node) -> list[str]:
    if getattr(node, "aria_hidden", False):
        return []
    lines: list[str] = []
    role = getattr(node, "aria_role", None)
    state = getattr(node, "aria_state", None) or {}
    if role:
        label = getattr(node, "aria_label", None) or _direct_text(node) or squashTextNodes(node)
        state_prefix = "".join(f"({name}) " for name, enabled in state.items() if enabled)
        lines.append(f"{role}: {state_prefix}{label}".rstrip())
    for child in getattr(node, "childNodes", []):
        if getattr(child, "aria_hidden", False):
            continue
        if getattr(child, "aria_role", None):
            lines.extend(_screen_reader_lines(child))
        elif getattr(child, "nodeName", None) != "#text":
            lines.extend(_screen_reader_lines(child))
    return lines


def renderNodeToScreenReaderOutput(node) -> str:
    lines = _screen_reader_lines(node)
    if lines:
        return "\n".join(lines)
    return squashTextNodes(node)


def renderNodeToOutput(node) -> str:
    node_name = getattr(node, "nodeName", None)
    if node_name == "#text":
        return node.nodeValue
    if node_name == "ink-text":
        content = "".join(renderNodeToOutput(child) for child in getattr(node, "childNodes", []))
        transform = getattr(node, "internal_transform", None)
        return transform(content) if callable(transform) else content
    if node_name == "ink-box":
        style = getattr(node, "attributes", {}).get("style", {})
        background = style.get("backgroundColor")
        separator = "\n" if style.get("flexDirection") == "column" else ""
        content = separator.join(renderNodeToOutput(child) for child in getattr(node, "childNodes", []))
        if background in ANSI_BG_OPEN:
            return ANSI_BG_OPEN[background] + content.replace("\x1b[49m", "") + "\x1b[49m"
        return content
    parts = [renderNodeToOutput(child) for child in getattr(node, "childNodes", []) if not getattr(child, "aria_hidden", False)]
    parts = [part for part in parts if part != ""]
    if node_name in {"ink-root", "ink-box", "ink-fragment"}:
        return "\n".join(parts)
    if parts:
        return "".join(parts)
    return squashTextNodes(node)


render_node_to_screen_reader_output = renderNodeToScreenReaderOutput
render_node_to_output = renderNodeToOutput

__all__ = [
    "OutputTransformer",
    "applyPaddingToText",
    "indentString",
    "renderNodeToOutput",
    "renderNodeToScreenReaderOutput",
]
