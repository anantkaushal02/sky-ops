"""A simple in-memory, process-wide daily message counter.

Not distributed and resets on process restart - this is deliberately not a
real production rate limiter, just cheap insurance for a single free-tier
demo instance sitting in front of a small shared LLM quota (e.g. Gemini's
free-tier daily request cap).
"""

import time


class DailyMessageLimiter:
    def __init__(self, daily_limit: int):
        self.daily_limit = daily_limit
        self._window_start = time.time()
        self._count = 0

    def _reset_if_new_day(self) -> None:
        if time.time() - self._window_start >= 86400:
            self._window_start = time.time()
            self._count = 0

    def try_consume(self) -> bool:
        self._reset_if_new_day()
        if self._count >= self.daily_limit:
            return False
        self._count += 1
        return True
