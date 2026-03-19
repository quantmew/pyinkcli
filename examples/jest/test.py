"""Test row component for jest example."""

from pyinkcli import Box, Text


def get_background_for_status(status: str):
    if status == "runs":
        return "yellow"
    if status == "pass":
        return "green"
    if status == "fail":
        return "red"
    return None


def Test(*, status: str, path: str):
    parts = path.split("/", 1)
    prefix = f"{parts[0]}/" if len(parts) > 1 else ""
    suffix = parts[1] if len(parts) > 1 else path

    return Box(
        Text(f" {status.upper()} ", color="black", backgroundColor=get_background_for_status(status)),
        Box(
            Text(prefix, dimColor=True),
            Text(suffix, bold=True, color="white"),
            marginLeft=1,
        ),
    )
