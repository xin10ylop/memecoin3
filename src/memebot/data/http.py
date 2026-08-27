"""Shared HTTP plumbing: paced, retrying GET/POST with per-host rate limits."""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

import requests

log = logging.getLogger(__name__)


class RateLimiter:
    """Evenly paced limiter, thread-safe."""

    def __init__(self, per_min: float):
        self.min_interval = 60.0 / per_min
        self._last = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delta = now - self._last
            if delta < self.min_interval:
                time.sleep(self.min_interval - delta)
            self._last = time.monotonic()


class HttpClient:
    def __init__(self, per_min: float = 30.0, headers: dict | None = None):
        self.limiter = RateLimiter(per_min)
        self.session = requests.Session()
        self.session.headers.update({"accept": "application/json",
                                     "user-agent": "memebot/0.1"})
        if headers:
            self.session.headers.update(headers)

    def get_json(self, url: str, params: dict | None = None,
                 retries: int = 3, timeout: int = 20) -> Any | None:
        for attempt in range(retries + 1):
            self.limiter.wait()
            try:
                r = self.session.get(url, params=params, timeout=timeout)
            except requests.RequestException as e:
                log.warning("GET %s failed (%s) attempt=%d", url, e, attempt)
                time.sleep(2 * (attempt + 1))
                continue
            if r.status_code == 200:
                try:
                    return r.json()
                except ValueError:
                    return None
            if r.status_code == 429:
                log.warning("429 on %s; backing off", url)
                time.sleep(15 * (attempt + 1))
                continue
            if r.status_code == 404:
                return None
            log.warning("HTTP %d on %s", r.status_code, url)
            time.sleep(2 * (attempt + 1))
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
