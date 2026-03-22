from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BoxStyle:
    top_left: str
    top: str
    top_right: str
    right: str
    bottom_right: str
    bottom: str
    bottom_left: str
    left: str


def _load_boxes() -> dict[str, BoxStyle]:
    path = Path(__file__).resolve().parents[3] / "js_source" / "cli-boxes" / "boxes.json"
    raw = json.loads(path.read_text())
    return {
        name: BoxStyle(
            top_left=value["topLeft"],
            top=value["top"],
            top_right=value["topRight"],
            right=value["right"],
            bottom_right=value["bottomRight"],
            bottom=value["bottom"],
            bottom_left=value["bottomLeft"],
            left=value["left"],
        )
        for name, value in raw.items()
    }


BOXES = _load_boxes()


def get_box_style(style: str | BoxStyle) -> BoxStyle:
    if isinstance(style, BoxStyle):
        return style
    return BOXES[style]


__all__ = ["BOXES", "BoxStyle", "get_box_style"]

