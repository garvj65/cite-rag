"""Small process-local Gemini budgets shared by clients, including retry attempts."""

import time
from collections import deque
from collections.abc import Callable
from threading import Lock

from app.deadlines import remaining_timeout
from app.errors import ProviderConfigurationError, RequestDeadlineError

WINDOW_SECONDS = 60.0


class RequestPacer:
    """Space attempts and bound weighted inputs in a rolling minute without storing secrets."""

    def __init__(self, limit: int, clock: Callable[[], float] = time.monotonic) -> None:
        if limit < 1:
            raise ValueError("pacing limit must be positive")
        self._limit = limit
        self._clock = clock
        self._attempts: deque[tuple[float, int]] = deque()
        self._next_start = 0.0
        self._lock = Lock()

    def wait(self, units: int, sleep: Callable[[float], None] = time.sleep) -> None:
        """Charge one attempt before HTTP; waiting cannot exceed the API request deadline."""
        if not 1 <= units <= self._limit:
            raise ProviderConfigurationError("provider_batch_exceeds_pacing_limit")
        with self._lock:
            while True:
                remaining_timeout(0)
                now = self._clock()
                while self._attempts and self._attempts[0][0] <= now - WINDOW_SECONDS:
                    self._attempts.popleft()
                delay = max(0.0, self._next_start - now)
                if sum(cost for _, cost in self._attempts) + units > self._limit:
                    delay = max(delay, self._attempts[0][0] + WINDOW_SECONDS - now)
                if delay <= 0:
                    self._attempts.append((now, units))
                    self._next_start = now + WINDOW_SECONDS * units / self._limit
                    return
                if remaining_timeout(delay) < delay:
                    raise RequestDeadlineError("request_deadline_exceeded")
                sleep(delay)


_pacers: dict[tuple[str, int], RequestPacer] = {}
_pacers_lock = Lock()


def get_pacer(endpoint: str, limit: int) -> RequestPacer | None:
    """Reuse a model endpoint budget across clients; zero explicitly disables pacing."""
    if not limit:
        return None
    with _pacers_lock:
        key = (endpoint, limit)
        if key not in _pacers:
            _pacers[key] = RequestPacer(limit)
        return _pacers[key]
