from collections import defaultdict, deque
from threading import Lock
from time import monotonic


class LoginThrottle:
    """Small single-process fixed-window limiter for the local MVP."""

    def __init__(self, account_limit: int = 5, ip_limit: int = 20, window_seconds: int = 60) -> None:
        self.account_limit = account_limit
        self.ip_limit = ip_limit
        self.window_seconds = window_seconds
        self._account_failures: dict[str, deque[float]] = defaultdict(deque)
        self._ip_failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _trim(self, values: deque[float], now: float) -> None:
        cutoff = now - self.window_seconds
        while values and values[0] <= cutoff:
            values.popleft()

    def is_blocked(self, account_key: str, ip_key: str, now: float | None = None) -> bool:
        current = monotonic() if now is None else now
        with self._lock:
            account = self._account_failures[account_key]
            ip = self._ip_failures[ip_key]
            self._trim(account, current)
            self._trim(ip, current)
            return len(account) >= self.account_limit or len(ip) >= self.ip_limit

    def record_failure(self, account_key: str, ip_key: str, now: float | None = None) -> None:
        current = monotonic() if now is None else now
        with self._lock:
            account = self._account_failures[account_key]
            ip = self._ip_failures[ip_key]
            self._trim(account, current)
            self._trim(ip, current)
            account.append(current)
            ip.append(current)

    def record_success(self, account_key: str) -> None:
        with self._lock:
            self._account_failures.pop(account_key, None)

    def reset(self) -> None:
        with self._lock:
            self._account_failures.clear()
            self._ip_failures.clear()


login_throttle = LoginThrottle()
