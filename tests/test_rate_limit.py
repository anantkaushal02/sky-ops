from flight_ops.rate_limit import DailyMessageLimiter


def test_allows_up_to_the_daily_limit():
    limiter = DailyMessageLimiter(daily_limit=2)
    assert limiter.try_consume() is True
    assert limiter.try_consume() is True
    assert limiter.try_consume() is False


def test_resets_after_a_day_elapses():
    limiter = DailyMessageLimiter(daily_limit=1)
    assert limiter.try_consume() is True
    assert limiter.try_consume() is False
    limiter._window_start -= 86400 + 1
    assert limiter.try_consume() is True
