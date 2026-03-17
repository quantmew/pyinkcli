"""
Output buffer for ink-python.

Manages the virtual output buffer that gets rendered to the terminal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Tuple, Union

from ink_python.utils.string_width import string_width


@dataclass
class StyledChar:
    """A character with styling information."""

    value: str
    full_width: bool = False
    styles: List[Any] = field(default_factory=list)


@dataclass
class ClipRegion:
    """A clipping region for output."""

    x1: Optional[int] = None
    x2: Optional[int] = None
    y1: Optional[int] = None
    y2: Optional[int] = None


@dataclass
class WriteOperation:
    """A write operation to the output buffer."""

    x: int
    y: int
    text: str
    transformers: List[Callable[[str, int], str]] = field(default_factory=list)


@dataclass
class ClipOperation:
    """A clip operation."""

    clip: ClipRegion


@dataclass
class UnclipOperation:
    """An unclip operation."""

    pass


Operation = Union[WriteOperation, ClipOperation, UnclipOperation]


class Output:
    """
    Virtual output buffer for terminal rendering.

    Handles the positioning and saving of output, applying transformations,
    and generating the final output string.
    """

    def __init__(self, width: int, height: int):
        """
        Initialize the output buffer.

        Args:
            width: Width in columns.
            height: Height in rows.
        """
        self.width = width
        self.height = height
        self._operations: List[Operation] = []

    def write(
        self,
        x: int,
        y: int,
        text: str,
        transformers: Optional[List[Callable[[str, int], str]]] = None,
    ) -> None:
        """
        Write text to the output buffer.

        Args:
            x: X position (column).
            y: Y position (row).
            text: Text to write.
            transformers: Optional list of transformation functions.
        """
        if not text:
            return

        self._operations.append(
            WriteOperation(
                x=x,
                y=y,
                text=text,
                transformers=transformers or [],
            )
        )

    def clip(
        self,
        x1: Optional[int] = None,
        x2: Optional[int] = None,
        y1: Optional[int] = None,
        y2: Optional[int] = None,
    ) -> None:
        """
        Start clipping output to a region.

        Args:
            x1: Left boundary.
            x2: Right boundary.
            y1: Top boundary.
            y2: Bottom boundary.
        """
        self._operations.append(
            ClipOperation(clip=ClipRegion(x1=x1, x2=x2, y1=y1, y2=y2))
        )

    def unclip(self) -> None:
        """End the current clipping region."""
        self._operations.append(UnclipOperation())

    def get(self) -> Tuple[str, int]:
        """
        Generate the final output.

        Returns:
            Tuple of (output_string, height).
        """
        # Initialize output buffer
        output: List[List[str]] = []
        for _ in range(self.height):
            output.append([" "] * self.width)

        # Track clipping regions
        clips: List[ClipRegion] = []

        for operation in self._operations:
            if isinstance(operation, ClipOperation):
                clips.append(operation.clip)
            elif isinstance(operation, UnclipOperation):
                clips.pop()
            elif isinstance(operation, WriteOperation):
                self._apply_write(output, operation, clips)

        # Convert buffer to string
        lines = []
        for row in output:
            line = "".join(row).rstrip()
            lines.append(line)

        result = "\n".join(lines)
        return (result, len(output))

    def _apply_write(
        self,
        output: List[List[str]],
        operation: WriteOperation,
        clips: List[ClipRegion],
    ) -> None:
        """Apply a write operation to the output buffer."""
        x, y = operation.x, operation.y
        text = operation.text
        transformers = operation.transformers

        # Apply clipping
        if clips:
            clip = clips[-1]
            lines = text.split("\n")

            # Horizontal clipping
            if clip.x1 is not None and clip.x2 is not None:
                if x + string_width(text) < clip.x1 or x > clip.x2:
                    return

                new_lines = []
                for line in lines:
                    line_width = string_width(line)
                    from_pos = max(0, clip.x1 - x)
                    to_pos = min(line_width, clip.x2 - x)
                    # Truncate line (simplified - doesn't handle ANSI)
                    new_lines.append(line[from_pos:to_pos])
                lines = new_lines

                if x < clip.x1:
                    x = clip.x1

            # Vertical clipping
            if clip.y1 is not None and clip.y2 is not None:
                if y + len(lines) < clip.y1 or y > clip.y2:
                    return

                from_row = max(0, clip.y1 - y)
                to_row = min(len(lines), clip.y2 - y)
                lines = lines[from_row:to_row]

                if y < clip.y1:
                    y = clip.y1

            text = "\n".join(lines)

        # Write to buffer
        lines = text.split("\n")
        for offset_y, line in enumerate(lines):
            row_y = y + offset_y
            if row_y < 0 or row_y >= len(output):
                continue

            # Apply transformers
            for transformer in transformers:
                line = transformer(line, offset_y)

            # Write characters
            row = output[row_y]
            offset_x = x
            for char in line:
                if offset_x < 0 or offset_x >= len(row):
                    break
                row[offset_x] = char
                offset_x += 1
                # Handle wide characters
                if string_width(char) > 1:
                    offset_x += 1
