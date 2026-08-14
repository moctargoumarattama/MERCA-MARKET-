from collections import deque
from functools import wraps
from time import time

from flask import abort, request


class RateLimiter:
    def __init__(self, max_buckets=4096, retention_seconds=300):
        self._buckets = {}
        self._max_buckets = max_buckets
        self._retention_seconds = retention_seconds
        self._last_cleanup = 0

    def _client_key(self) -> str:
        client_ip = request.remote_addr or "unknown"
        return f"{client_ip}:{request.endpoint}"

    def _cleanup(self, now):
        if now - self._last_cleanup < self._retention_seconds:
            return

        self._buckets = {
            key: bucket
            for key, bucket in self._buckets.items()
            if bucket and bucket[-1] > now - self._retention_seconds
        }
        self._last_cleanup = now

    def allow(self, limit: int, window_seconds: int) -> bool:
        now = time()
        self._cleanup(now)
        key = self._client_key()
        bucket = self._buckets.get(key)

        if bucket is None:
            if len(self._buckets) >= self._max_buckets:
                return False
            bucket = deque()
            self._buckets[key] = bucket

        while bucket and bucket[0] <= now - window_seconds:
            bucket.popleft()

        if not bucket:
            self._buckets.pop(key, None)
            bucket = deque()
            self._buckets[key] = bucket

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
