"""Source editor helpers mirroring react-devtools-core/src/editor.js."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from contextlib import suppress
from pathlib import Path

_COMMON_EDITORS = {
    "/Applications/Atom.app/Contents/MacOS/Atom": "atom",
    "/Applications/Atom Beta.app/Contents/MacOS/Atom Beta": (
        "/Applications/Atom Beta.app/Contents/MacOS/Atom Beta"
    ),
    "/Applications/Sublime Text.app/Contents/MacOS/Sublime Text": (
        "/Applications/Sublime Text.app/Contents/SharedSupport/bin/subl"
    ),
    "/Applications/Sublime Text 2.app/Contents/MacOS/Sublime Text 2": (
        "/Applications/Sublime Text 2.app/Contents/SharedSupport/bin/subl"
    ),
    "/Applications/Visual Studio Code.app/Contents/MacOS/Electron": "code",
}

_TERMINAL_EDITORS = {"vim", "emacs", "nano"}
_child_process: subprocess.Popen[str] | None = None


def isTerminalEditor(editor: str) -> bool:
    return Path(editor).name in _TERMINAL_EDITORS


def getArgumentsForLineNumber(editor: str, file_path: str, line_number: int) -> list[str]:
    editor_name = Path(editor).name
    if editor_name in {"vim", "mvim"}:
        return [file_path, f"+{line_number}"]
    if editor_name in {"atom", "Atom", "Atom Beta", "subl", "sublime", "wstorm", "appcode", "charm", "idea"}:
        return [f"{file_path}:{line_number}"]
    if editor_name in {"joe", "emacs", "emacsclient"}:
        return [f"+{line_number}", file_path]
    if editor_name in {"rmate", "mate", "mine"}:
        return ["--line", str(line_number), file_path]
    if editor_name == "code":
        return ["-g", f"{file_path}:{line_number}"]
    return [file_path]


def guessEditor() -> list[str]:
    react_editor = os.environ.get("REACT_EDITOR")
    if react_editor:
        return shlex.split(react_editor)

    if sys.platform == "darwin":
        try:
            output = subprocess.check_output(["ps", "x"], text=True)
            for process_name, editor_binary in _COMMON_EDITORS.items():
                if process_name in output:
                    return [editor_binary]
        except Exception:
            pass

    visual = os.environ.get("VISUAL")
    if visual:
        return [visual]

    editor = os.environ.get("EDITOR")
    if editor:
        return shlex.split(editor)

    return []


def getValidFilePath(
    maybe_relative_path: str,
    absolute_project_roots: list[str] | None = None,
) -> str | None:
    if not maybe_relative_path:
        return None

    candidate = Path(maybe_relative_path)
    if candidate.is_absolute():
        return str(candidate) if candidate.exists() else None

    for project_root in absolute_project_roots or []:
        joined = Path(project_root) / maybe_relative_path
        if joined.exists():
            return str(joined)

    return None


def doesFilePathExist(
    maybe_relative_path: str,
    absolute_project_roots: list[str] | None = None,
) -> bool:
    return getValidFilePath(maybe_relative_path, absolute_project_roots) is not None


def launchEditor(
    maybe_relative_path: str,
    line_number: int | None,
    absolute_project_roots: list[str] | None = None,
) -> bool:
    global _child_process

    file_path = getValidFilePath(maybe_relative_path, absolute_project_roots)
    if file_path is None:
        return False

    if line_number is not None and not isinstance(line_number, int):
        return False

    editor_command = guessEditor()
    if not editor_command:
        return False

    editor, *args = editor_command
    if shutil.which(editor) is None and not Path(editor).exists():
        return False

    if line_number and line_number > 0:
        args.extend(getArgumentsForLineNumber(editor, file_path, line_number))
    else:
        args.append(file_path)

    if _child_process is not None and isTerminalEditor(editor):
        with suppress(OSError):
            _child_process.kill()
        _child_process = None

    try:
        if sys.platform == "win32":
            _child_process = subprocess.Popen(
                ["cmd.exe", "/C", editor, *args],
                stdin=None,
                stdout=None,
                stderr=None,
            )
        else:
            _child_process = subprocess.Popen(
                [editor, *args],
                stdin=None,
                stdout=None,
                stderr=None,
            )
    except OSError:
        return False

    return True


__all__ = [
    "doesFilePathExist",
    "getArgumentsForLineNumber",
    "getValidFilePath",
    "guessEditor",
    "isTerminalEditor",
    "launchEditor",
]
