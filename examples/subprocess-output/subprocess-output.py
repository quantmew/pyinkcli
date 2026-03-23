"""subprocess-output example for pyinkcli."""

from __future__ import annotations

import subprocess
import sys
import threading

from pyinkcli import Box, Text, render
from pyinkcli.ansi_tokenizer import tokenizeAnsi
from pyinkcli.hooks import useEffect, useState


def strip_ansi(text: str) -> str:
    return "".join(token.value for token in tokenizeAnsi(text) if token.type == "text")


def load_initial_output() -> str:
    completed = subprocess.run(
        [
            sys.executable,
            "-u",
            "-c",
            (
                "import pathlib;"
                "base=pathlib.Path('tests');"
                "paths=sorted(str(p).replace('\\\\','/') for p in base.iterdir())[:20];"
                "print('\\n'.join(paths))"
            ),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    cleaned = strip_ansi(completed.stdout)
    collected = [entry for entry in cleaned.splitlines() if entry.strip()]
    return "\n".join(collected[-5:]) if collected else "tests/"


def subprocess_output_example():
    output, set_output = useState(load_initial_output())

    def setup():
        def consume():
            completed = subprocess.run(
                [
                    sys.executable,
                    "-u",
                    "-c",
                    (
                        "import pathlib;"
                        "base=pathlib.Path('tests');"
                        "paths=sorted(str(p).replace('\\\\','/') for p in base.iterdir())[:20];"
                        "print('\\n'.join(paths))"
                    ),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
            cleaned = strip_ansi(completed.stdout)
            collected = [entry for entry in cleaned.splitlines() if entry.strip()]
            set_output("\n".join(collected[-5:]))

        thread = threading.Thread(target=consume, daemon=True)
        thread.start()

        def cleanup():
            return None

        return cleanup

    useEffect(setup, ())

    return Box(
        Text("Command output:"),
        Box(Text(output), marginTop=1),
        flexDirection="column",
        padding=1,
    )


if __name__ == "__main__":
    render(subprocess_output_example, interactive=True, patch_console=False).wait_until_exit()
