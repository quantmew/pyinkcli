"""subprocess-output example for pyinkcli."""

from __future__ import annotations

import os
import selectors
import subprocess
import sys
import threading
import time
from pathlib import Path

from pyinkcli import Box, Text
from pyinkcli.ansi_tokenizer import tokenizeAnsi
from pyinkcli.example_runner import run_example
from pyinkcli.hooks import useEffect, useState


def strip_ansi(text: str) -> str:
    return "".join(token.value for token in tokenizeAnsi(text) if token.type == "text")


def _js_root() -> Path:
    return Path(__file__).resolve().parents[2] / "js_source" / "ink"


def _js_example_dir() -> Path:
    return _js_root() / "examples" / "subprocess-output"


NON_TTY_INITIAL_OUTPUT = "> ink@6.8.0 example\n> NODE_NO_WARNINGS=1 node --import=tsx examples/jest"


def subprocess_output_example():
    output, set_output = useState(f"\n{NON_TTY_INITIAL_OUTPUT}")

    def setup():
        process = None
        running = True
        start_time = time.monotonic()

        def consume():
            nonlocal process
            process = subprocess.Popen(
                [
                    "npm",
                    "run",
                    "example",
                    "examples/jest",
                ],
                cwd=_js_example_dir(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=False,
                bufsize=0,
            )

            assert process.stdout is not None
            selector = selectors.DefaultSelector()
            selector.register(process.stdout, selectors.EVENT_READ)
            while running:
                ready = selector.select(timeout=0.1)
                if not ready:
                    if process.poll() is not None:
                        break
                    continue

                chunk = os.read(process.stdout.fileno(), 128)
                if not chunk:
                    break
                if running:
                    cleaned = strip_ansi(chunk.decode("utf-8", "replace"))
                    lines = cleaned.split("\n")
                    if time.monotonic() - start_time < 1.0:
                        continue
                    set_output("\n".join(lines[-5:]))

        thread = threading.Thread(target=consume, daemon=True)
        thread.start()

        def cleanup():
            nonlocal running
            running = False
            if process is not None and process.poll() is None:
                process.terminate()
            return None

        return cleanup

    useEffect(setup, ())

    return Box(
        Text("Сommand output:"),
        Box(Text(output), marginTop=1),
        flexDirection="column",
        padding=1,
    )


if __name__ == "__main__":
    run_example(subprocess_output_example, patch_console=False)
