#!/usr/bin/env python3
"""
Layout example for ink-python.

Demonstrates flexbox layout capabilities.
"""

import time
from ink_python import render, Box, Text, Spacer, Newline


def LayoutDemo():
    """Demonstrates various layout options."""

    return Box(
        # Title
        Box(
            Text("Ink-Python Layout Demo", color="cyan", bold=True),
            justifyContent="center",
            padding=1,
        ),

        Newline(),

        # Row layout
        Box(
            Box(
                Text("Left", color="red"),
                padding=1,
                borderStyle="single",
                borderColor="red",
            ),
            Spacer(),
            Box(
                Text("Center", color="green"),
                padding=1,
                borderStyle="single",
                borderColor="green",
            ),
            Spacer(),
            Box(
                Text("Right", color="blue"),
                padding=1,
                borderStyle="single",
                borderColor="blue",
            ),
            width=60,
        ),

        Newline(),

        # Column layout
        Box(
            Box(
                Text("Row 1", backgroundColor="red", color="white"),
                width=40,
                paddingX=1,
            ),
            Box(
                Text("Row 2", backgroundColor="green", color="white"),
                width=40,
                paddingX=1,
            ),
            Box(
                Text("Row 3", backgroundColor="blue", color="white"),
                width=40,
                paddingX=1,
            ),
            flexDirection="column",
            width=50,
            borderStyle="round",
            borderColor="gray",
            padding=1,
        ),

        Newline(),

        # Flex grow demo
        Box(
            Box(
                Text("Fixed", backgroundColor="magenta", color="white"),
            ),
            Box(
                Text("Grows", backgroundColor="yellow"),
                flexGrow=1,
                justifyContent="center",
            ),
            Box(
                Text("Fixed", backgroundColor="magenta", color="white"),
            ),
            width=60,
        ),

        flexDirection="column",
        padding=1,
    )


def main():
    """Run the layout demo."""
    app = render(LayoutDemo())

    # Keep running for a moment
    time.sleep(3)

    app.unmount()
    print("\nLayout demo completed!")


if __name__ == "__main__":
    main()
