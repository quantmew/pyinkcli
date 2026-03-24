"""Table example for pyinkcli."""

from __future__ import annotations

from pyinkcli import Box, Text, render
from pyinkcli.example_data import TABLE_USERS


def _generate_users() -> list[dict[str, object]]:
    return list(TABLE_USERS)


def table_example():
    users = _generate_users()
    header = Box(
        Box(Text("ID"), width="10%"),
        Box(Text("Name"), width="50%"),
        Box(Text("Email"), width="40%"),
    )

    rows = [
        Box(
            Box(Text(str(user["id"])), width="10%"),
            Box(Text(user["name"]), width="50%"),
            Box(Text(user["email"]), width="40%"),
        )
        for user in users
    ]

    return Box(
        header,
        *rows,
        flexDirection="column",
        width=80,
    )


if __name__ == "__main__":
    render(table_example).wait_until_exit()
