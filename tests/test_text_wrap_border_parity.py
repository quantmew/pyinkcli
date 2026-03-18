from __future__ import annotations

from ink_python import Box, Text, renderToString


def test_nested_text_wrap_inside_bordered_box_preserves_label_spacing() -> None:
    output = renderToString(
        Box(
            Text(
                "Selected: ",
                Text(
                    "Server Authentication Module - Handles JWT token validation, OAuth2 flows, and session management across distributed systems",
                    bold=True,
                    color="magenta",
                ),
            ),
            borderStyle="round",
            borderColor="magenta",
            paddingX=2,
            width=80,
        )
    )

    assert "Selected: " in output
    assert "Server Authentication Module" in output
    assert "OAuth2 flows, and session management across distributed systems" in output


def test_long_text_wrap_in_bordered_column_box_keeps_borders_intact() -> None:
    output = renderToString(
        Box(
            Text(
                "System Services Monitor (3 of 30 services):",
                bold=True,
                color="magenta",
            ),
            Text(
                "> Server Authentication Module - Handles JWT token validation, OAuth2 flows, and session management across distributed systems",
                color="blue",
            ),
            Text(
                "  Database Connection Pool - Maintains persistent connections to PostgreSQL cluster with automatic failover and load balancing",
                color="white",
            ),
            borderStyle="single",
            borderColor="gray",
            paddingX=2,
            paddingY=1,
            flexDirection="column",
            width=80,
        )
    )

    lines = output.splitlines()
    assert lines[0].startswith("\x1b[")
    assert "┌" in lines[0]
    assert "┐" in lines[0]
    assert any("System Services Monitor (3 of 30 services):" in line for line in lines)
    assert any("Server Authentication Module" in line for line in lines)
    assert any("Database Connection Pool" in line for line in lines)
