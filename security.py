from collections import defaultdict, deque
from functools import wraps
from time import time

from flask import abort, request


class RateLimiter:
    def __init__(self):
        self._buckets = defaultdict(deque)

    def _client_key(self) -> str:
        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr) or "unknown"
        return f"{client_ip}:{request.endpoint}"

    def allow(self, limit: int, window_seconds: int) -> bool:
        now = time()
        key = self._client_key()
        bucket = self._buckets[key]

        while bucket and bucket[0] <= now - window_seconds:
            bucket.popleft()

        if len(bucket) >= limit:
            return False

        bucket.append(now)
        return True


limiter = RateLimiter()


def rate_limit(limit: int, window_seconds: int):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not limiter.allow(limit, window_seconds):
                abort(429, description="Too many requests")
            return view(*args, **kwargs)

        return wrapped

    return decorator
