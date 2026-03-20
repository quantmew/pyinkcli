from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from pyinkcli.packages.react_devtools_core.src.editor import (
    doesFilePathExist,
    getArgumentsForLineNumber,
    getValidFilePath,
    guessEditor,
    isTerminalEditor,
    launchEditor,
)


def test_get_valid_file_path_resolves_relative_paths_against_project_roots(tmp_path: Path) -> None:
    source = tmp_path / "src" / "app.py"
    source.parent.mkdir(parents=True)
    source.write_text("print('ok')\n")

    resolved = getValidFilePath("src/app.py", [str(tmp_path)])

    assert resolved == str(source)
    assert doesFilePathExist("src/app.py", [str(tmp_path)]) is True


def test_get_arguments_for_line_number_matches_known_editor_shapes() -> None:
    assert getArgumentsForLineNumber("code", "/tmp/app.py", 12) == ["-g", "/tmp/app.py:12"]
    assert getArgumentsForLineNumber("vim", "/tmp/app.py", 12) == ["/tmp/app.py", "+12"]
    assert getArgumentsForLineNumber("emacs", "/tmp/app.py", 12) == ["+12", "/tmp/app.py"]


def test_guess_editor_prefers_react_editor_env() -> None:
    with patch.dict("os.environ", {"REACT_EDITOR": "code --reuse-window"}, clear=False):
        assert guessEditor() == ["code", "--reuse-window"]


def test_terminal_editor_detection_matches_upstream_intent() -> None:
    assert isTerminalEditor("vim") is True
    assert isTerminalEditor("/usr/bin/nano") is True
    assert isTerminalEditor("code") is False


def test_launch_editor_passes_line_number_arguments(tmp_path: Path) -> None:
    source = tmp_path / "main.py"
    source.write_text("print('ok')\n")

    with (
        patch.dict("os.environ", {"REACT_EDITOR": "code"}, clear=False),
        patch("shutil.which", return_value="/usr/bin/code"),
        patch("subprocess.Popen") as popen,
    ):
        assert launchEditor("main.py", 7, [str(tmp_path)]) is True

    popen.assert_called_once_with(
        ["code", "-g", f"{source}:7"],
        stdin=None,
        stdout=None,
        stderr=None,
    )
