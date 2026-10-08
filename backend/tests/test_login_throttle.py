from app.core.login_throttle import LoginThrottle


def test_account_is_blocked_after_configured_failures() -> None:
    limiter = LoginThrottle(account_limit=2, ip_limit=10, window_seconds=60)
    limiter.record_failure("user@example.test", "127.0.0.1", now=1)
    limiter.record_failure("user@example.test", "127.0.0.1", now=2)

    assert limiter.is_blocked("user@example.test", "127.0.0.1", now=3)
    assert not limiter.is_blocked("other@example.test", "127.0.0.2", now=3)


def test_expired_failures_are_removed_and_success_clears_account() -> None:
    limiter = LoginThrottle(account_limit=1, ip_limit=10, window_seconds=60)
    limiter.record_failure("user@example.test", "127.0.0.1", now=1)
    assert not limiter.is_blocked("user@example.test", "127.0.0.1", now=62)

    limiter.record_failure("user@example.test", "127.0.0.1", now=70)
    limiter.record_success("user@example.test")
    assert not limiter.is_blocked("user@example.test", "127.0.0.2", now=71)


def test_ip_limit_applies_across_accounts() -> None:
    limiter = LoginThrottle(account_limit=10, ip_limit=2, window_seconds=60)
    limiter.record_failure("one@example.test", "127.0.0.1", now=1)
    limiter.record_failure("two@example.test", "127.0.0.1", now=2)

    assert limiter.is_blocked("three@example.test", "127.0.0.1", now=3)
