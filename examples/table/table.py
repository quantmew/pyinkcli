"""
Table example for pyinkcli.

Demonstrates a table layout with user data.
Port of js_source/ink/examples/table/table.tsx
"""

from pyinkcli import render, Box, Text


USERS = [
    {"id": 0, "name": "john_doe", "email": "john@example.com"},
    {"id": 1, "name": "jane_smith", "email": "jane@example.com"},
    {"id": 2, "name": "bob_wilson", "email": "bob@example.com"},
    {"id": 3, "name": "alice_brown", "email": "alice@example.com"},
    {"id": 4, "name": "charlie_davis", "email": "charlie@example.com"},
    {"id": 5, "name": "diana_miller", "email": "diana@example.com"},
    {"id": 6, "name": "eve_jones", "email": "eve@example.com"},
    {"id": 7, "name": "frank_taylor", "email": "frank@example.com"},
    {"id": 8, "name": "grace_anderson", "email": "grace@example.com"},
    {"id": 9, "name": "henry_thomas", "email": "henry@example.com"},
]


def table_example():
    """Render a table of users."""
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
        for user in USERS
    ]

    return Box(
        header,
        *rows,
        flexDirection="column",
        width=80,
    )


if __name__ == "__main__":
    render(table_example).wait_until_exit()
