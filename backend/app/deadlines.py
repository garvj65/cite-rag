"""Bound HTTP response waiting while keeping worker-owned resources safe after cancellation."""

import asyncio
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from app.errors import RequestDeadlineError

_deadline: ContextVar[float | None] = ContextVar("citerag_request_deadline", default=None)


def remaining_timeout(configured: float) -> float:
    """Cap a provider phase by the remaining API budget; CLI/evaluation calls stay unchanged."""
    deadline = _deadline.get()
    if deadline is None:
        return configured
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise RequestDeadlineError("request_deadline_exceeded")
    return min(configured, remaining)


@contextmanager
def request_budget(deadline: float) -> Iterator[None]:
    """Scope a monotonic deadline to one worker without leaking it into subsequent calls."""
    token = _deadline.set(deadline)
    try:
        remaining_timeout(0)
        yield
    finally:
        _deadline.reset(token)


async def execute_with_deadline[T](operation: Callable[[], T], seconds: float) -> T:
    """Return a timely 504 while an in-flight worker retains ownership of its cleanup."""
    deadline = time.monotonic() + seconds

    def execute() -> T:
        with request_budget(deadline):
            return operation()

    try:
        async with asyncio.timeout(seconds):
            return await asyncio.to_thread(execute)
    except TimeoutError:
        raise RequestDeadlineError("request_deadline_exceeded") from None
