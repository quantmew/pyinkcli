from __future__ import annotations

import asyncio
from typing import Any


class ExitManager:
    def __init__(self) -> None:
        self.result: Any = None
        self.error: BaseException | None = None

    def set_result(self, value: Any) -> None:
        self.result = value

    def set_error(self, error: BaseException | None) -> None:
        self.error = error

    def consume_error(self) -> BaseException | None:
        error = self.error
        self.error = None
        return error

    def has_error(self) -> bool:
        return self.error is not None

    def wait_until_exit(self, unmount, flush_callback, *, timeout: float | None = None):
        if self.error is not None:
            error = self.consume_error()
            assert error is not None
            unmount()
            raise error
        flush_callback(timeout or 0.3)
        return self.result

    async def wait_until_exit_async(self, unmount, session, loop_thread, *, timeout: float | None = None):
        if self.error is not None:
            error = self.consume_error()
            assert error is not None
            unmount()
            raise error
        future = loop_thread.submit_coroutine(session.wait_until_exit())
        wrapped = asyncio.wrap_future(future)
        if timeout is None:
            return await wrapped
        return await asyncio.wait_for(wrapped, timeout=timeout)


__all__ = ["ExitManager"]
