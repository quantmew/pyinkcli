from __future__ import annotations

from dataclasses import dataclass

from .layout_render import compute_layout
from .render_node_to_output import renderNodeToOutput, renderNodeToScreenReaderOutput


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


def _style_int(style: dict, *keys: str) -> int:
    for key in keys:
        value = style.get(key)
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return 0


def _has_static_subtree(node) -> bool:
    if getattr(node, "internal_static", False):
        return True
    return any(_has_static_subtree(child) for child in getattr(node, "childNodes", []))


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
        style = getattr(node, "attributes", {}).get("style", {})
        if node_name == "ink-box" and style.get("flexDirection", "column") != "column":
            return _join_parts(main_parts, ""), _join_parts(static_parts, "\n")

        gap = _style_int(style, "gap")
        built_main: list[str] = []
        emitted_main = False
        for child in children:
            main_part, _ = _split_static_output(child)
            if not main_part:
                continue
            child_style = getattr(child, "attributes", {}).get("style", {})
            prefix = ""
            if emitted_main and gap > 0:
                prefix += "\n" * gap
            margin_top = _style_int(child_style, "marginTop", "margin_top")
            if margin_top > 0:
                prefix += "\n" * margin_top
            built_main.append(prefix + main_part)
            emitted_main = True

        return "".join(built_main), _join_parts(static_parts, "\n")

    if not main_parts:
        return "", _join_parts(static_parts, "\n")
    return "".join(main_parts), _join_parts(static_parts, "\n")


def render_dom(node, is_screen_reader_enabled: bool) -> RenderResult:
    if is_screen_reader_enabled:
        output = renderNodeToScreenReaderOutput(node)
        static_output = ""
    else:
        compute_layout(node)
        if _has_static_subtree(node):
            output, static_output = _split_static_output(node)
        else:
            output = renderNodeToOutput(node)
            static_output = ""
    output_height = 0 if output == "" else output.count("\n") + 1
    return RenderResult(output=output, outputHeight=output_height, staticOutput=static_output)


__all__ = ["RenderResult", "render_dom"]
