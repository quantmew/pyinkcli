"""Summary component for jest example."""

from ink_python import Box, Text


def Summary(*, is_finished: bool, passed: int, failed: int, time_text: str):
    total = passed + failed

    return Box(
        Box(
            Box(Text("Test Suites:", bold=True), width=14),
            Text(f"{failed} failed, ", bold=True, color="red") if failed else Text(""),
            Text(f"{passed} passed, ", bold=True, color="green") if passed else Text(""),
            Text(f"{total} total"),
        ),
        Box(
            Box(Text("Time:", bold=True), width=14),
            Text(time_text),
        ),
        Box(Text("Ran all test suites.", dimColor=True)) if is_finished else Box(),
        flexDirection="column",
        marginTop=1,
    )
