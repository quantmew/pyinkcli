from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path


def isTerminalEditor(editor: str) -> bool:
    name = Path(editor).name
    return name in {"vim", "nvim", "nano", "emacs", "vi"}


def getArgumentsForLineNumber(editor: str, file_path: str, line_number: int):
    name = Path(editor).name
    if name == "code":
        return ["-g", f"{file_path}:{line_number}"]
    if name in {"vim", "nvim", "nano"}:
        return [file_path, f"+{line_number}"]
    if name == "emacs":
        return [f"+{line_number}", file_path]
    return [file_path]


def guessEditor():
    value = os.environ.get("REACT_EDITOR") or os.environ.get("EDITOR")
    return shlex.split(value) if value else None


def getValidFilePath(file_path: str, project_roots: list[str]):
    candidate = Path(file_path)
    if candidate.is_file():
        return str(candidate)
    for root in project_roots:
        resolved = Path(root) / file_path
        if resolved.is_file():
            return str(resolved)
    return None


def doesFilePathExist(file_path: str, project_roots: list[str]) -> bool:
    return getValidFilePath(file_path, project_roots) is not None


def launchEditor(file_path: str, line_number: int, project_roots: list[str]):
    editor = guessEditor()
    if not editor:
        return False
    resolved = getValidFilePath(file_path, project_roots)
    if resolved is None:
        return False
    binary = shutil.which(editor[0])
    if not binary:
        return False
    subprocess.Popen(
        [editor[0], *editor[1:], *getArgumentsForLineNumber(editor[0], resolved, line_number)],
        stdin=None,
        stdout=None,
        stderr=None,
    )
    return True

