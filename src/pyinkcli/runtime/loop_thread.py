from __future__ import annotations

import asyncio
import concurrent.futures
import threading
from collections.abc import Callable
from typing import Any


class AsyncLoopThread:
    def __init__(self) -> None:
        self._ready = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._ready.wait()

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None:
            raise RuntimeError("event loop not ready")
        return self._loop

    def _run(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._ready.set()
        loop.run_forever()
        pending = [task for task in asyncio.all_tasks(loop) if not task.done()]
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()

    def call_soon(self, callback: Callable[..., Any], *args: Any) -> None:
        self.loop.call_soon_threadsafe(callback, *args)

    def submit(self, callback: Callable[..., Any], *args: Any) -> concurrent.futures.Future:
        future: concurrent.futures.Future = concurrent.futures.Future()

        def runner() -> None:
            if future.cancelled():
                return
            try:
                future.set_result(callback(*args))
            except BaseException as error:  # pragma: no cover
                future.set_exception(error)

        self.loop.call_soon_threadsafe(runner)
        return future

    def submit_coroutine(self, coroutine) -> concurrent.futures.Future:
        return asyncio.run_coroutine_threadsafe(coroutine, self.loop)

    def stop(self) -> None:
        if self._loop is None:
            return
        self.loop.call_soon_threadsafe(self.loop.stop)
        self._thread.join(timeout=1.0)
