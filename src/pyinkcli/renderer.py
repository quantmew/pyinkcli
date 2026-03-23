from __future__ import annotations

from dataclasses import dataclass

from .render_node_to_output import renderNodeToOutput, renderNodeToScreenReaderOutput
from .sanitize_ansi import sanitizeAnsi


@dataclass
class RenderResult:
    output: str
    outputHeight: int
    staticOutput: str


def _join_parts(parts: list[str], separator: str) -> str:
    filtered = [part for part in parts if part]
    if not filtered:
        return ""
    return separator.join(filtered)


def _split_static_output(node) -> tuple[str, str]:
    if getattr(node, "internal_static", False):
        return "", renderNodeToOutput(node)
    node_name = getattr(node, "nodeName", None)
    children = list(getattr(node, "childNodes", []))
    if not children:
        return renderNodeToOutput(node), ""

    main_parts: list[str] = []
    static_parts: list[str] = []
    for child in children:
        main_part, static_part = _split_static_output(child)
        if main_part:
            main_parts.append(main_part)
        if static_part:
            static_parts.append(static_part)

    if not static_parts:
        return renderNodeToOutput(node), ""
    if node_name in {"ink-root", "ink-box", "ink-fragment"}:
        separator = "\n"
        style = getattr(node, "attributes", {}).get("style", {})
        if node_name == "ink-box" and style.get("flexDirection", "column") != "column":
            separator = ""
        return _join_parts(main_parts, separator), _join_parts(static_parts, "\n")

    if not main_parts:
        return "", _join_parts(static_parts, "\n")
    return "".join(main_parts), _join_parts(static_parts, "\n")


def render_dom(node, is_screen_reader_enabled: bool) -> RenderResult:
    if is_screen_reader_enabled:
        output = renderNodeToScreenReaderOutput(node)
        static_output = ""
    else:
        output, static_output = _split_static_output(node)
    output = sanitizeAnsi(output)
    static_output = sanitizeAnsi(static_output)
    output_height = 0 if output == "" else output.count("\n") + 1
    return RenderResult(output=output, outputHeight=output_height, staticOutput=static_output)


__all__ = ["RenderResult", "render_dom"]
