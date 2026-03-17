"""
Use Stdout example for ink-python.

Demonstrates the useStdout hook to inspect stdout dimensions.
Based on js_source/ink/examples/use-stdout/use-stdout.tsx
"""

from ink_python import render, Box, Text, use_stdout


def use_stdout_example():
    """Render stdout dimensions."""
    stdout = use_stdout()

    return Box(
        Box(
            Text("Terminal dimensions:", bold=True, underline=True),
            Box(
                Text("Width: "),
                Text(str(stdout.columns), bold=True),
                marginTop=1,
            ),
            Box(
                Text("Height: "),
                Text(str(stdout.rows), bold=True),
            ),
            flexDirection="column",
        ),
        paddingX=2,
        paddingY=1,
        flexDirection="column",
    )


if __name__ == "__main__":
    render(use_stdout_example).wait_until_exit()
