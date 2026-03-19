"""Legacy keypress parsing split from `hooks/use_input.py`."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from pyinkcli.kitty_keyboard import kittyModifiers


class _Parser:
    metaKeyCodeRe = re.compile(r"^(?:\x1b)([a-zA-Z0-9])$")
    fnKeyRe = re.compile(
        r"^(?:\x1b+)(O|N|\[|\[\[)(?:(\d+)(?:;(\d+))?([~^$])|(?:1;)?(\d+)?([a-zA-Z]))"
    )
    kittyKeyRe = re.compile(r"^\x1b\[(\d+)(?:;(\d+)(?::(\d+))?(?:;([\d:]+))?)?u$")
    kittySpecialKeyRe = re.compile(r"^\x1b\[(\d+);(\d+):(\d+)([A-Za-z~])$")

    keyNames: dict[str, str] = {
        "OP": "f1",
        "OQ": "f2",
        "OR": "f3",
        "OS": "f4",
        "[11~": "f1",
        "[12~": "f2",
        "[13~": "f3",
        "[14~": "f4",
        "[[A": "f1",
        "[[B": "f2",
        "[[C": "f3",
        "[[D": "f4",
        "[[E": "f5",
        "[15~": "f5",
        "[17~": "f6",
        "[18~": "f7",
        "[19~": "f8",
        "[20~": "f9",
        "[21~": "f10",
        "[23~": "f11",
        "[24~": "f12",
        "[A": "up",
        "[B": "down",
        "[C": "right",
        "[D": "left",
        "[E": "clear",
        "[F": "end",
        "[H": "home",
        "OA": "up",
        "OB": "down",
        "OC": "right",
        "OD": "left",
        "OE": "clear",
        "OF": "end",
        "OH": "home",
        "[1~": "home",
        "[2~": "insert",
        "[3~": "delete",
        "[4~": "end",
        "[5~": "pageup",
        "[6~": "pagedown",
        "[[5~": "pageup",
        "[[6~": "pagedown",
        "[7~": "home",
        "[8~": "end",
        "[a": "up",
        "[b": "down",
        "[c": "right",
        "[d": "left",
        "[e": "clear",
        "[2$": "insert",
        "[3$": "delete",
        "[5$": "pageup",
        "[6$": "pagedown",
        "[7$": "home",
        "[8$": "end",
        "Oa": "up",
        "Ob": "down",
        "Oc": "right",
        "Od": "left",
        "Oe": "clear",
        "[2^": "insert",
        "[3^": "delete",
        "[5^": "pageup",
        "[6^": "pagedown",
        "[7^": "home",
        "[8^": "end",
        "[Z": "tab",
    }

    nonAlphanumericKeys = [*keyNames.values(), "backspace"]
    kittySpecialLetterKeys = {
        "A": "up",
        "B": "down",
        "C": "right",
        "D": "left",
        "E": "clear",
        "F": "end",
        "H": "home",
        "P": "f1",
        "Q": "f2",
        "R": "f3",
        "S": "f4",
    }
    kittySpecialNumberKeys = {
        2: "insert",
        3: "delete",
        5: "pageup",
        6: "pagedown",
        7: "home",
        8: "end",
        11: "f1",
        12: "f2",
        13: "f3",
        14: "f4",
        15: "f5",
        17: "f6",
        18: "f7",
        19: "f8",
        20: "f9",
        21: "f10",
        23: "f11",
        24: "f12",
    }
    kittyCodepointNames = {
        27: "escape",
        9: "tab",
        127: "delete",
        8: "backspace",
        57358: "capslock",
        57359: "scrolllock",
        57360: "numlock",
        57361: "printscreen",
        57362: "pause",
        57363: "menu",
        57376: "f13",
        57377: "f14",
        57378: "f15",
        57379: "f16",
        57380: "f17",
        57381: "f18",
        57382: "f19",
        57383: "f20",
        57384: "f21",
        57385: "f22",
        57386: "f23",
        57387: "f24",
        57388: "f25",
        57389: "f26",
        57390: "f27",
        57391: "f28",
        57392: "f29",
        57393: "f30",
        57394: "f31",
        57395: "f32",
        57396: "f33",
        57397: "f34",
        57398: "f35",
        57399: "kp0",
        57400: "kp1",
        57401: "kp2",
        57402: "kp3",
        57403: "kp4",
        57404: "kp5",
        57405: "kp6",
        57406: "kp7",
        57407: "kp8",
        57408: "kp9",
        57409: "kpdecimal",
        57410: "kpdivide",
        57411: "kpmultiply",
        57412: "kpsubtract",
        57413: "kpadd",
        57414: "kpenter",
        57415: "kpequal",
        57416: "kpseparator",
        57417: "kpleft",
        57418: "kpright",
        57419: "kpup",
        57420: "kpdown",
        57421: "kppageup",
        57422: "kppagedown",
        57423: "kphome",
        57424: "kpend",
        57425: "kpinsert",
        57426: "kpdelete",
        57427: "kpbegin",
        57428: "mediaplay",
        57429: "mediapause",
        57430: "mediaplaypause",
        57431: "mediareverse",
        57432: "mediastop",
        57433: "mediafastforward",
        57434: "mediarewind",
        57435: "mediatracknext",
        57436: "mediatrackprevious",
        57437: "mediarecord",
        57438: "lowervolume",
        57439: "raisevolume",
        57440: "mutevolume",
        57441: "leftshift",
        57442: "leftcontrol",
        57443: "leftalt",
        57444: "leftsuper",
        57445: "lefthyper",
        57446: "leftmeta",
        57447: "rightshift",
        57448: "rightcontrol",
        57449: "rightalt",
        57450: "rightsuper",
        57451: "righthyper",
        57452: "rightmeta",
        57453: "isoLevel3Shift",
        57454: "isoLevel5Shift",
    }

    @dataclass
    class ParsedKey:
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
        isPrintable: bool = False
        text: str | None = None

    @staticmethod
    def isShiftKey(code: str) -> bool:
        return code in {
            "[a",
            "[b",
            "[c",
            "[d",
            "[e",
            "[2$",
            "[3$",
            "[5$",
            "[6$",
            "[7$",
            "[8$",
            "[Z",
        }

    @staticmethod
    def isCtrlKey(code: str) -> bool:
        return code in {
            "Oa",
            "Ob",
            "Oc",
            "Od",
            "Oe",
            "[2^",
            "[3^",
            "[5^",
            "[6^",
            "[7^",
            "[8^",
        }

    @staticmethod
    def normalizeSequence(data: Any = "") -> str:
        if isinstance(data, (bytes, bytearray)):
            raw = bytes(data)
            if raw and raw[0] > 127 and len(raw) == 1:
                raw = bytes([raw[0] - 128])
                return "\x1b" + raw.decode("latin-1")
            return raw.decode("utf-8", errors="surrogateescape")

        if data is None:
            return ""

        if isinstance(data, str):
            return data

        return str(data)


metaKeyCodeRe = _Parser.metaKeyCodeRe
fnKeyRe = _Parser.fnKeyRe
kittyKeyRe = _Parser.kittyKeyRe
kittySpecialKeyRe = _Parser.kittySpecialKeyRe
nonAlphanumericKeys = _Parser.nonAlphanumericKeys


def isValidCodepoint(cp: int) -> bool:
    return 0 <= cp <= 0x10FFFF and not (0xD800 <= cp <= 0xDFFF)


def safeFromCodePoint(cp: int) -> str:
    return chr(cp) if isValidCodepoint(cp) else "?"


def resolveEventType(value: int) -> str:
    if value == 3:
        return "release"
    if value == 2:
        return "repeat"
    return "press"


def parseKittyModifiers(modifiers: int) -> dict[str, bool]:
    return {
        "ctrl": bool(modifiers & kittyModifiers["ctrl"]),
        "shift": bool(modifiers & kittyModifiers["shift"]),
        "meta": bool(modifiers & kittyModifiers["meta"]),
        "option": bool(modifiers & kittyModifiers["alt"]),
        "super": bool(modifiers & kittyModifiers["super"]),
        "hyper": bool(modifiers & kittyModifiers["hyper"]),
        "capsLock": bool(modifiers & kittyModifiers["capsLock"]),
        "numLock": bool(modifiers & kittyModifiers["numLock"]),
    }


def parseKittyKeypress(sequence: str) -> _Parser.ParsedKey | None:
    match = _Parser.kittyKeyRe.match(sequence)
    if not match:
        return None

    codepoint = int(match[1])
    modifiers = max(0, int(match[2]) - 1) if match[2] else 0
    event_type = int(match[3]) if match[3] else 1
    text_field = match[4]

    if not isValidCodepoint(codepoint):
        return None

    text = None
    if text_field:
        text = "".join(safeFromCodePoint(int(cp)) for cp in text_field.split(":"))

    if codepoint == 32:
        name = "space"
        is_printable = True
    elif codepoint == 13:
        name = "return"
        is_printable = True
    elif codepoint in _Parser.kittyCodepointNames:
        name = _Parser.kittyCodepointNames[codepoint]
        is_printable = False
    elif 1 <= codepoint <= 26:
        name = chr(codepoint + 96)
        is_printable = False
    else:
        name = safeFromCodePoint(codepoint).lower()
        is_printable = True

    if is_printable and not text:
        text = safeFromCodePoint(codepoint)

    return _Parser.ParsedKey(
        name=name,
        sequence=sequence,
        raw=sequence,
        eventType=resolveEventType(event_type),
        isKittyProtocol=True,
        isPrintable=is_printable,
        text=text,
        **parseKittyModifiers(modifiers),
    )


def parseKittySpecialKey(sequence: str) -> _Parser.ParsedKey | None:
    match = _Parser.kittySpecialKeyRe.match(sequence)
    if not match:
        return None

    number = int(match[1])
    modifiers = max(0, int(match[2]) - 1)
    event_type = int(match[3])
    terminator = match[4]
    name = (
        _Parser.kittySpecialNumberKeys.get(number)
        if terminator == "~"
        else _Parser.kittySpecialLetterKeys.get(terminator)
    )
    if not name:
        return None

    return _Parser.ParsedKey(
        name=name,
        sequence=sequence,
        raw=sequence,
        eventType=resolveEventType(event_type),
        isKittyProtocol=True,
        isPrintable=False,
        **parseKittyModifiers(modifiers),
    )


def parseKeypress(data: Any = "") -> _Parser.ParsedKey:
    parts = None
    sequence = _Parser.normalizeSequence(data)
    key = _Parser.ParsedKey(sequence=sequence or "", raw=sequence or None)
    key.sequence = sequence

    kitty_result = parseKittyKeypress(sequence)
    if kitty_result is not None:
        return kitty_result

    if _Parser.kittyKeyRe.match(sequence):
        return _Parser.ParsedKey(
            name="",
            sequence=sequence,
            raw=sequence,
            isKittyProtocol=True,
            isPrintable=False,
        )

    kitty_special_result = parseKittySpecialKey(sequence)
    if kitty_special_result is not None:
        return kitty_special_result

    if sequence in ("\r", "\x1b\r"):
        key.raw = None
        key.name = "return"
        key.option = len(sequence) == 2
        return key

    if sequence == "\n":
        key.name = "enter"
        return key

    if sequence == "\t":
        key.name = "tab"
        return key

    if sequence in ("\b", "\x1b\b"):
        key.name = "backspace"
        key.meta = sequence.startswith("\x1b")
        return key

    if sequence in ("\x7f", "\x1b\x7f"):
        key.name = "delete"
        key.meta = sequence.startswith("\x1b")
        return key

    if sequence in ("\x1b", "\x1b\x1b"):
        key.name = "escape"
        key.meta = len(sequence) == 2
        return key

    if sequence in (" ", "\x1b "):
        key.name = "space"
        key.meta = len(sequence) == 2
        return key

    if len(sequence) == 1 and sequence <= "\x1a":
        key.name = chr(ord(sequence) + ord("a") - 1)
        key.ctrl = True
        return key

    if len(sequence) == 1 and "0" <= sequence <= "9":
        key.name = "number"
        return key

    if len(sequence) == 1 and "a" <= sequence <= "z":
        key.name = sequence
        return key

    if len(sequence) == 1 and "A" <= sequence <= "Z":
        key.name = sequence.lower()
        key.shift = True
        return key

    parts = _Parser.metaKeyCodeRe.match(sequence)
    if parts:
        key.meta = True
        key.shift = bool(re.match(r"^[A-Z]$", parts[1]))
        key.name = parts[1].lower()
        return key

    parts = _Parser.fnKeyRe.match(sequence)
    if parts:
        segments = list(sequence)
        if len(segments) > 1 and segments[0] == "\x1b" and segments[1] == "\x1b":
            key.option = True

        code = "".join(part for part in [parts[1], parts[2], parts[4], parts[6]] if part)
        modifier_text = parts[3] or parts[5] or "1"
        modifier = int(modifier_text) - 1
        key.ctrl = bool(modifier & 4)
        key.meta = bool(modifier & 10)
        key.shift = bool(modifier & 1)
        key.code = code
        key.name = _Parser.keyNames.get(code, "")
        key.shift = _Parser.isShiftKey(code) or key.shift
        key.ctrl = _Parser.isCtrlKey(code) or key.ctrl
        return key

    return key
