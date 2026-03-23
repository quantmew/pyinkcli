from __future__ import annotations

from .connection import connectToDevTools, connectWithCustomMessagingProtocol
from .hook import initialize, installHook


__all__ = [
    "initialize",
    "installHook",
    "connectToDevTools",
    "connectWithCustomMessagingProtocol",
]
