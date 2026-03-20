"""subprocess-output example for pyinkcli."""

from __future__ import annotations

import subprocess
import threading
from pathlib import Path

from pyinkcli import Box, Text, render
from pyinkcli.ansi_tokenizer import tokenizeAnsi
from pyinkcli.hooks import useEffect, useState


def strip_ansi(text: str) -> str:
    return "".join(token.value for token in tokenizeAnsi(text) if token.type == "text")


def subprocess_output_example():
    output, set_output = useState("")

    def setup():
        process = subprocess.Popen(
            [
                "python",
                "-u",
                str(Path(__file__).resolve().parents[1] / "jest" / "index.py"),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=False,
        )

        def consume():
            collected: list[str] = []
            buffer = ""
            assert process.stdout is not None
            while True:
                chunk = process.stdout.read1(64)
                if not chunk:
                    break

                buffer += chunk.decode("utf8", errors="replace")
                cleaned = strip_ansi(buffer)
                collected = [entry for entry in cleaned.splitlines() if entry.strip()]
                set_output("\n".join(collected[-5:]))

        thread = threading.Thread(target=consume, daemon=True)
        thread.start()

        def cleanup():
            if process.poll() is None:
                process.kill()

        return cleanup

    useEffect(setup, ())

    return Box(
        Text("Command output:"),
        Box(Text(output), marginTop=1),
        flexDirection="column",
        padding=1,
    )


if __name__ == "__main__":
    render(subprocess_output_example).wait_until_exit()
