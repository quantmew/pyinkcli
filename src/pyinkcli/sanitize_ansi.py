from __future__ import annotations

import re
from functools import lru_cache

from .ansi_tokenizer import hasAnsiControlCharacters, tokenizeAnsi

sgrParametersRegex = re.compile(r"^[\d:;]*$")


@lru_cache(maxsize=4096)
def sanitizeAnsi(text: str) -> str:
    if not hasAnsiControlCharacters(text):
        return text
    output = []
    for token in tokenizeAnsi(text):
        if token.type in {"text", "osc"}:
            output.append(token.value)
            continue
        if (
            token.type == "csi"
            and token.final_character == "m"
            and token.intermediate_string == ""
            and sgrParametersRegex.match(token.parameter_string)
        ):
            output.append(token.value)
    return "".join(output)


__all__ = ["sanitizeAnsi"]
