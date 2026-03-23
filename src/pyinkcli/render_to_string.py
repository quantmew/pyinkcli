from __future__ import annotations

from .component import RenderableNode, isElement
from .components.Text import ANSI_BG_OPEN, ANSI_OPEN
from ._component_runtime import _Component
from .sanitize_ansi import sanitizeAnsi
from .suspense_runtime import SuspendSignal
from .utils.cli_boxes import get_box_style
from .utils.string_width import string_width
from .utils.wrap_ansi import wrap_ansi

from .hooks import _runtime as hooks_runtime
from .packages import react
from .packages import react_router


def _flatten_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return "".join(_flatten_text(item) for item in value)
    if isElement(value):
        return _render(value, "0")
    return str(value)


def _background_wrap(text: str, background: str | None, *, width: int | None = None) -> str:
    if not background:
        return text
    bg_open = ANSI_BG_OPEN.get(background)
    if bg_open is None:
        return text
    if width is None:
        return bg_open + text + "\x1b[49m"
    padded = text + (" " * max(width - string_width(sanitizeAnsi(text)), 0))
    return bg_open + padded + "\x1b[49m"


def _border_wrap(lines: list[str], style_name: str, border_color: str | None) -> str:
    style = get_box_style(style_name)
    content_width = max((string_width(sanitizeAnsi(line)) for line in lines), default=0)
    prefix = ANSI_OPEN.get(border_color, "")
    suffix = "\x1b[39m" if prefix else ""
    top = prefix + style.top_left + (style.top * content_width) + style.top_right + suffix
    middle = [
        prefix
        + style.left
        + suffix
        + line
        + (" " * max(content_width - string_width(sanitizeAnsi(line)), 0))
        + prefix
        + style.right
        + suffix
        for line in lines
    ]
    bottom = prefix + style.bottom_left + (style.bottom * content_width) + style.bottom_right + suffix
    return "\n".join([top, *middle, bottom])


def _render_ink_text(node: RenderableNode, instance_id: str) -> str:
    text = "".join(_flatten_text(child) for child in node.children)
    transform = node.props.get("internal_transform")
    return transform(text) if callable(transform) else text


def _render_box(node: RenderableNode, instance_id: str) -> str:
    style = node.props.get("style", {})
    background = style.get("backgroundColor")
    width = style.get("width")
    height = style.get("height")
    padding = style.get("padding", 0)
    padding_x = style.get("padding_x", 0)
    padding_y = style.get("padding_y", 0)
    effective_padding_x = padding + padding_x
    effective_padding_y = padding + padding_y
    border_style = style.get("borderStyle")
    border_color = style.get("borderColor")

    def soft_wrap_plain(text: str, limit: int) -> list[str]:
        remaining = text
        lines: list[str] = []
        while remaining:
            if string_width(remaining) <= limit:
                lines.append(remaining)
                break
            candidate = remaining[:limit]
            split_at = candidate.rfind(" ")
            if split_at > 0:
                lines.append(remaining[: split_at + 1])
                remaining = remaining[split_at + 1 :]
            else:
                lines.append(candidate)
                remaining = remaining[limit:]
        return lines or [""]

    if width and not border_style and not padding and not padding_x and not padding_y and not height and len(node.children) == 1 and isinstance(node.children[0], RenderableNode) and node.children[0].type == "ink-text":
        child = node.children[0]
        child_background = child.props.get("backgroundColor")
        plain_text = sanitizeAnsi("".join(_flatten_text(part) for part in child.children))
        wrapped_lines = soft_wrap_plain(plain_text, width)
        if background:
            lines = [_background_wrap(line, background, width=width) for line in wrapped_lines]
            if height:
                while len(lines) < height:
                    lines.append(_background_wrap("", background, width=width))
            return "\n".join(lines)
        if child_background:
            return "\n".join(_background_wrap(line, child_background) for line in wrapped_lines)

    outputs: list[str] = []
    buffered_plain = ""

    def flush_plain() -> None:
        nonlocal buffered_plain
        if buffered_plain:
            if background and not width and not border_style:
                outputs.append(buffered_plain)
            else:
                outputs.append(_background_wrap(buffered_plain, background))
            buffered_plain = ""

    for index, child in enumerate(node.children):
        if isinstance(child, RenderableNode) and child.type == "ink-text" and not child.props.get("backgroundColor") and background and not width:
            buffered_plain += _render(child, f"{instance_id}:{index}")
            continue
        flush_plain()
        outputs.append(_render(child, f"{instance_id}:{index}"))
    flush_plain()

    separator = "\n" if style.get("flexDirection") == "column" else ""
    content = separator.join(outputs)
    if (
        border_style
        and width
        and separator == ""
        and len(node.children) > 1
        and all(isinstance(child, RenderableNode) and child.type == "ink-text" for child in node.children)
    ):
        pieces = [sanitizeAnsi(_render(child, f"{instance_id}:{index}")) for index, child in enumerate(node.children)]
        content = "".join(piece.rstrip(": ") if index < len(pieces) - 1 else piece for index, piece in enumerate(pieces))

    if background and not width and not border_style:
        bg_open = ANSI_BG_OPEN.get(background, "")
        if bg_open:
            return bg_open + content.replace("\x1b[49m", "") + "\x1b[49m"

    if width and not border_style:
        inner_width = max(width - 2 * effective_padding_x, 1)
        wrapped_lines = soft_wrap_plain(sanitizeAnsi(content), inner_width)
        final_lines: list[str] = []
        for _ in range(effective_padding_y):
            final_lines.append(_background_wrap(" " * width, background, width=width) if background else " " * width)
        for line in wrapped_lines:
            padded_content = (" " * effective_padding_x) + line
            total_width = width
            if background:
                final_lines.append(_background_wrap(padded_content, background, width=total_width))
            else:
                final_lines.append(padded_content)
        for _ in range(effective_padding_y):
            final_lines.append(_background_wrap(" " * width, background, width=width) if background else " " * width)
        if height:
            while len(final_lines) < height:
                final_lines.append(_background_wrap("", background, width=width) if background else " " * width)
        content = "\n".join(final_lines)

    if border_style:
        inner_width = max((width - 2) if width else max(string_width(sanitizeAnsi(content)), 1), 1)
        inner_height = max((height - 2) if height else 0, 0)
        wrapped_lines = soft_wrap_plain(sanitizeAnsi(content), max(inner_width - 2 * effective_padding_x, 1))
        bordered_lines: list[str] = []
        for _ in range(effective_padding_y):
            bordered_lines.append(_background_wrap(" " * inner_width, background, width=inner_width) if background else " " * inner_width)
        for line in wrapped_lines:
            padded_line = (" " * effective_padding_x) + line + (" " * effective_padding_x)
            bordered_lines.append(
                _background_wrap(padded_line, background, width=inner_width) if background else padded_line
            )
        for _ in range(effective_padding_y):
            bordered_lines.append(_background_wrap(" " * inner_width, background, width=inner_width) if background else " " * inner_width)
        if inner_height:
            while len(bordered_lines) < inner_height:
                bordered_lines.append(_background_wrap("", background, width=inner_width) if background else " " * inner_width)
        return _border_wrap(bordered_lines, border_style, border_color)

    return content


def _render(node, instance_id: str) -> str:
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, (list, tuple)):
        return "".join(_render(child, f"{instance_id}:{index}") for index, child in enumerate(node))
    if not isinstance(node, RenderableNode):
        return str(node)

    if node.type is react.Fragment:
        return "".join(_render(child, f"{instance_id}:{index}") for index, child in enumerate(node.children))
    if getattr(node.type, "__ink_react_provider__", False):
        value = node.props.get("value", node.type._context.default_value)
        with hooks_runtime._push_context(node.type._context, value):
            return "".join(_render(child, f"{instance_id}:{index}") for index, child in enumerate(node.children))
    if getattr(node.type, "__ink_react_consumer__", False):
        reader = node.children[0]
        return _render(reader(hooks_runtime.useContext(node.type._context)), f"{instance_id}:consumer")
    if getattr(node.type, "__ink_react_forward_ref__", False):
        return _render(node.type.render(node.props, node.props.get("ref")), f"{instance_id}:fwd")
    if getattr(node.type, "__ink_react_lazy__", False):
        resolved = node.type._init(node.type._payload)
        return _render(RenderableNode(type=resolved, props=node.props, children=node.children, key=node.key), instance_id)
    if getattr(node.type, "__ink_react_memo__", False):
        return _render(RenderableNode(type=node.type.type, props=node.props, children=node.children, key=node.key), instance_id)
    if node.type == "__router_provider__":
        with react_router.push_router_context(node.props["internal_router_context"]):
            return "".join(_render(child, f"{instance_id}:{index}") for index, child in enumerate(node.children))
    if node.type == "__ink-suspense__":
        try:
            return "".join(_render(child, f"{instance_id}:{index}") for index, child in enumerate(node.children))
        except SuspendSignal:
            return _render(node.props.get("fallback"), f"{instance_id}:fallback")
    if isinstance(node.type, type) and issubclass(node.type, _Component):
        instance = node.type(props=node.props)
        return _render(instance.render(), f"{instance_id}:class")
    if callable(node.type):
        component_instance_id = f"{instance_id}:{getattr(node.type, '__name__', 'anonymous')}"
        hooks_runtime._begin_component_render(component_instance_id, node.type)
        try:
            rendered = node.type(*node.children, **node.props)
        finally:
            hooks_runtime._end_component_render()
        return _render(rendered, f"{component_instance_id}:rendered")
    if node.type == "ink-text":
        return _render_ink_text(node, instance_id)
    if node.type == "ink-box":
        return _render_box(node, instance_id)
    return "".join(_render(child, f"{instance_id}:{index}") for index, child in enumerate(node.children))


def create_root_node(width: int = 80, height: int = 24):
    from .dom import createNode

    root = createNode("ink-root")
    root.width = width
    root.height = height
    return root


def renderToString(node, options=None, **kwargs) -> str:
    hooks_runtime._reset_hook_state()
    try:
        return _render(node, "root")
    finally:
        hooks_runtime._finish_hook_state()


__all__ = ["renderToString", "create_root_node"]
