"""
Sanitize ANSI control sequences for Ink layout rendering.

Preserves printable text, OSC control strings, and safe SGR sequences while
dropping cursor movement and other layout-affecting control codes.
"""

from __future__ import annotations

import re

from ink_python.ansi_tokenizer import hasAnsiControlCharacters, tokenizeAnsi

_SGR_PARAMETERS_RE = re.compile(r"^[\d:;]*$")


def sanitizeAnsi(text: str) -> str:
    """
    Strip ANSI escape sequences that would interfere with Ink's layout.

    This function is part of a layered defense strategy:
    render input -> output buffer -> app writes -> debug writes.
    New user-text entry points should reuse this instead of reimplementing
    ad-hoc ANSI filtering.
    """

    if not hasAnsiControlCharacters(text):
        return text

    output: list[str] = []
    for token in tokenizeAnsi(text):
        if token.type in {"text", "osc"}:
            output.append(token.value)
            continue

        if (
            token.type == "csi"
            and token.final_character == "m"
            and token.intermediate_string == ""
            and _SGR_PARAMETERS_RE.match(token.parameter_string)
        ):
            output.append(token.value)

    return "".join(output)
