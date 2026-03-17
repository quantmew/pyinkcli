#!/usr/bin/env python3
"""
Hello World example for ink-python.

A simple example showing basic text rendering.
"""

import time
from ink_python import render, Box, Text


def HelloApp():
    """A simple hello world app."""

    return Box(
        Text(
            "Hello, World!",
            color="green",
            bold=True,
        ),
        flexDirection="column",
        alignItems="center",
        padding=1,
    )


def main():
    """Run the hello world app."""
    app = render(HelloApp())

    # Keep running for a moment to see the output
    time.sleep(2)

    # Clean exit
    app.unmount()
    print("Goodbye!")


if __name__ == "__main__":
    main()
