"""Translated helpers from `react-router/lib/href.ts`."""

from __future__ import annotations

import re
from typing import Any


def href(path: str, params: dict[str, Any] | None = None) -> str:
    parameters = params or {}
    result = re.sub(
        r"/:([\w-]+)(\?)?",
        lambda match: _replace_path_param(path, parameters, match.group(1), match.group(2)),
        _trimTrailingSplat(path),
    )

    if path.endswith("*"):
        value = parameters.get("*")
        if value is not None:
            result += "/" + str(value)

    return result or "/"


def _replace_path_param(
    path: str,
    params: dict[str, Any],
    param: str,
    question_mark: str | None,
) -> str:
    is_required = question_mark is None
    value = params.get(param)
    if is_required and value is None:
        raise ValueError(
            f"Path '{path}' requires param '{param}' but it was not provided"
        )
    return "" if value is None else "/" + str(value)


def _trimTrailingSplat(path: str) -> str:
    index = len(path) - 1
    if index < 0:
        return path

    char = path[index]
    if char not in {"*", "/"}:
        return path

    index -= 1
    while index >= 0:
        if path[index] != "/":
            break
        index -= 1

    return path[: index + 1]
