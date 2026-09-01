"""Shared HTTP plumbing: paced, retrying GET/POST with per-host rate limits."""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

import requests

log = logging.getLogger(__name__)


class RateLimiter:
    """Adaptive paced limiter, thread-safe: multiplies the interval on 429s,
    decays back to base on success (shared-IP burst buckets are unknowable)."""

    def __init__(self, per_min: float):
        self.base_interval = 60.0 / per_min
        self.interval = self.base_interval
        self.max_interval = 20.0
        self._last = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delta = now - self._last
            if delta < self.interval:
                time.sleep(self.interval - delta)
            self._last = time.monotonic()

    def penalize(self) -> None:
        with self._lock:
            self.interval = min(self.max_interval, self.interval * 1.5)

    def reward(self) -> None:
        with self._lock:
            self.interval = max(self.base_interval, self.interval * 0.90)


class HttpClient:
    def __init__(self, per_min: float = 30.0, headers: dict | None = None):
        self.limiter = RateLimiter(per_min)
        self.last_error: str | None = None
        self.session = requests.Session()
        self.session.headers.update({"accept": "application/json",
                                     "user-agent": "memebot/0.1"})
        if headers:
            self.session.headers.update(headers)

    def get_json(self, url: str, params: dict | None = None,
                 retries: int = 3, timeout: int = 20) -> Any | None:
        """None means 'no answer' OR 'no data' -- last_error tells them apart.

        Callers that record a permanent verdict about a resource need to know
        which one they got. A backfill that treats "throttled four times" the
        same as "this pool no longer exists" writes off rows it could have
        scored, and does it fastest exactly when the API is busiest.
        """
        self.last_error: str | None = None
        for attempt in range(retries + 1):
            self.limiter.wait()
            try:
                r = self.session.get(url, params=params, timeout=timeout)
            except requests.RequestException as e:
                self.last_error = str(e)
                log.warning("GET %s failed (%s) attempt=%d", url, e, attempt)
                time.sleep(2 * (attempt + 1))
                continue
            if r.status_code == 200:
                self.limiter.reward()
                try:
                    return r.json()
                except ValueError:
                    return None
            if r.status_code == 429:
                self.last_error = "429"
                self.limiter.penalize()
                log.info("429 on %s (interval now %.1fs)", url,
                         self.limiter.interval)
                time.sleep(3 * (attempt + 1))
                continue
            if r.status_code == 404:
                return None            # definitive: it is not there
            self.last_error = f"http {r.status_code}"
            log.warning("HTTP %d on %s", r.status_code, url)
            time.sleep(2 * (attempt + 1))
        self.last_error = self.last_error or "no answer after retries"
        return None

    def post_json(self, url: str, payload: dict, retries: int = 3,
                  timeout: int = 25) -> Any | None:
        for attempt in range(retries + 1):
            self.limiter.wait()
            try:
                r = self.session.post(url, json=payload, timeout=timeout)
            except requests.RequestException as e:
                log.warning("POST %s failed (%s) attempt=%d", url, e, attempt)
                time.sleep(2 * (attempt + 1))
                continue
            if r.status_code == 200:
                try:
                    return r.json()
                except ValueError:
                    return None
            if r.status_code == 429:
                time.sleep(15 * (attempt + 1))
                continue
            log.warning("HTTP %d on %s: %s", r.status_code, url, r.text[:200])
            time.sleep(2 * (attempt + 1))
        return None
