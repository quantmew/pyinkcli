from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from shlex import split as shell_split


def isTerminalEditor(editor: str) -> bool:
    return Path(editor).name in {"vim", "emacs", "nano"}


def getArgumentsForLineNumber(editor: str, filePath: str, lineNumber: int) -> list[str]:
    name = Path(editor).name
    if name in {"vim", "mvim"}:
        return [filePath, f"+{lineNumber}"]
    if name in {"atom", "Atom", "Atom Beta", "subl", "sublime", "wstorm", "appcode", "charm", "idea"}:
        return [f"{filePath}:{lineNumber}"]
    if name in {"joe", "emacs", "emacsclient"}:
        return [f"+{lineNumber}", filePath]
    if name in {"rmate", "mate", "mine"}:
        return ["--line", str(lineNumber), filePath]
    if name == "code":
        return ["-g", f"{filePath}:{lineNumber}"]
    return [filePath]


def guessEditor() -> list[str]:
    editor = os.environ.get("REACT_EDITOR")
    if editor:
        return shell_split(editor)

    visual = os.environ.get("VISUAL")
    if visual:
        return [visual]

    env_editor = os.environ.get("EDITOR")
    if env_editor:
        return [env_editor]

    return []


def getValidFilePath(
    maybeRelativePath: str,
    absoluteProjectRoots: list[str],
) -> str | None:
    candidate = Path(maybeRelativePath)
    if candidate.is_absolute():
        return str(candidate) if candidate.exists() else None

    for root in absoluteProjectRoots:
        joined = Path(root) / maybeRelativePath
        if joined.exists():
            return str(joined)
    return None


def doesFilePathExist(maybeRelativePath: str, absoluteProjectRoots: list[str]) -> bool:
    return getValidFilePath(maybeRelativePath, absoluteProjectRoots) is not None


def launchEditor(
    maybeRelativePath: str,
    lineNumber: int,
    absoluteProjectRoots: list[str],
) -> bool:
    filePath = getValidFilePath(maybeRelativePath, absoluteProjectRoots)
    if filePath is None:
        return False

    if lineNumber and not isinstance(lineNumber, int):
        return False

    editor_parts = guessEditor()
    if not editor_parts:
        return False

    editor, *args = editor_parts
    if lineNumber:
        args = args + getArgumentsForLineNumber(editor, filePath, lineNumber)
    else:
        args = args + [filePath]

    if shutil.which(editor) is None and not Path(editor).is_absolute():
        return False

    subprocess.Popen(
        [editor, *args],
        stdin=None,
        stdout=None,
        stderr=None,
    )
    return True

