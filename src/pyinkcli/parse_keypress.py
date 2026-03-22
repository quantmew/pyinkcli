from __future__ import annotations

import re
from dataclasses import dataclass

from .kitty_keyboard import kittyModifiers

metaKeyCodeRe = re.compile(r"^(?:\x1b)([a-zA-Z0-9])$")
fnKeyRe = re.compile(
    r"^(?:\x1b+)(O|N|\[|\[\[)(?:(\d+)(?:;(\d+))?([~^$])|(?:1;)?(\d+)?([a-zA-Z]))"
)
kittyKeyRe = re.compile(r"^\x1b\[(\d+)(?:;(\d+)(?::(\d+))?(?:;([\d:]+))?)?u$")
kittySpecialKeyRe = re.compile(r"^\x1b\[(\d+);(\d+):(\d+)([A-Za-z~])$")

keyName = {
    "[A": "up",
    "[B": "down",
    "[C": "right",
    "[D": "left",
    "OA": "up",
    "OB": "down",
    "OC": "right",
    "OD": "left",
    "[3~": "delete",
    "[Z": "tab",
}

kittySpecialLetterKeys = {
    "A": "up",
    "B": "down",
    "C": "right",
    "D": "left",
    "E": "clear",
    "F": "end",
    "H": "home",
}

kittySpecialNumberKeys = {2: "insert", 3: "delete", 5: "pageup", 6: "pagedown", 7: "home", 8: "end"}
kittyCodepointNames = {27: "escape", 9: "tab", 127: "delete", 8: "backspace", 57361: "printscreen"}
nonAlphanumericKeys = [*keyName.values(), "backspace"]


@dataclass
class Key:
    name: str = ""
    ctrl: bool = False
    meta: bool = False
    shift: bool = False
    option: bool = False
    sequence: str = ""
    raw: str | None = None
    code: str | None = None
    super: bool = False
    hyper: bool = False
    capsLock: bool = False
    numLock: bool = False
    eventType: str | None = None
    isKittyProtocol: bool = False
    text: str | None = None
    isPrintable: bool = True


def _kitty_modifier_flags(modifiers_value: int) -> dict[str, bool]:
    bits = max(modifiers_value - 1, 0)
    return {
        "shift": bool(bits & kittyModifiers["shift"]),
        "meta": bool(bits & kittyModifiers["alt"]),
        "ctrl": bool(bits & kittyModifiers["ctrl"]),
        "super": bool(bits & kittyModifiers["super"]),
        "hyper": bool(bits & kittyModifiers["hyper"]),
        "capsLock": bool(bits & kittyModifiers["capsLock"]),
        "numLock": bool(bits & kittyModifiers["numLock"]),
    }


def parseKittyKeypress(sequence: str) -> Key | None:
    match = kittyKeyRe.match(sequence)
    if not match:
        return None
    codepoint = int(match.group(1))
    modifiers_value = int(match.group(2) or "1")
    event_type = {"1": "press", "2": "repeat", "3": "release"}.get(match.group(3) or "1", "press")
    flags = _kitty_modifier_flags(modifiers_value)
    try:
        text = chr(codepoint)
    except ValueError:
        return Key(sequence=sequence, raw=sequence, isKittyProtocol=True, isPrintable=False)
    if 0xD800 <= codepoint <= 0xDFFF:
        return Key(sequence=sequence, raw=sequence, isKittyProtocol=True, isPrintable=False)
    name = kittyCodepointNames.get(codepoint)
    printable = True
    if name is None:
        name = text.lower()
        printable = codepoint >= 32
    else:
        printable = codepoint in {13, 32}
    return Key(
        name=name,
        ctrl=flags["ctrl"],
        meta=flags["meta"],
        shift=flags["shift"] or (text.isalpha() and text.isupper()),
        sequence=sequence,
        raw=sequence,
        eventType=event_type,
        isKittyProtocol=True,
        super=flags["super"],
        hyper=flags["hyper"],
        capsLock=flags["capsLock"],
        numLock=flags["numLock"],
        text=text,
        isPrintable=printable,
    )


def parseKittySpecialKey(sequence: str) -> Key | None:
    match = kittySpecialKeyRe.match(sequence)
    if not match:
        return None
    code_number = int(match.group(1))
    modifiers_value = int(match.group(2))
    event_type = {"1": "press", "2": "repeat", "3": "release"}.get(match.group(3), "press")
    suffix = match.group(4)
    name = kittySpecialLetterKeys.get(suffix) or kittySpecialNumberKeys.get(code_number, "")
    flags = _kitty_modifier_flags(modifiers_value)
    return Key(
        name=name,
        ctrl=flags["ctrl"],
        meta=flags["meta"],
        shift=flags["shift"],
        sequence=sequence,
        raw=sequence,
        eventType=event_type,
        isKittyProtocol=True,
        isPrintable=False,
    )


def parseKeypress(value: str | bytes) -> Key:
    if isinstance(value, bytes):
        if len(value) == 1 and value[0] >= 0x80:
            value = "\x1b" + chr(value[0] & 0x7F)
        else:
            value = value.decode("utf-8", "ignore")
    kitty = parseKittyKeypress(value) or parseKittySpecialKey(value)
    if kitty is not None:
        return kitty
    if value == "\x03":
        return Key(name="c", ctrl=True, sequence=value, raw=value, isPrintable=False)
    if len(value) == 1 and value.isalpha():
        return Key(
            name=value.lower(),
            shift=value.isupper(),
            sequence=value,
            raw=value,
            isPrintable=True,
        )
    meta_match = metaKeyCodeRe.match(value)
    if meta_match:
        char = meta_match.group(1)
        return Key(name=char.lower(), meta=True, shift=char.isupper(), sequence=value, raw=value)
    match = fnKeyRe.match(value)
    if match:
        code = (match.group(1) or "") + (match.group(2) or match.group(5) or "") + (match.group(4) or match.group(6) or "")
        name = keyName.get(code, "")
        modifier = int(match.group(3) or match.group(5) or "1")
        return Key(
            name=name,
            ctrl=modifier == 5,
            shift=modifier == 2,
            meta=modifier == 3,
            sequence=value,
            raw=value,
            code=code,
            isPrintable=False,
        )
    return Key(name="", sequence=value, raw=value, isPrintable=False)


__all__ = [
    "Key",
    "nonAlphanumericKeys",
    "parseKeypress",
    "parseKittyKeypress",
    "parseKittySpecialKey",
]

