"""Optional Telegram notifications (no external deps).

Set MEMEBOT_TG_TOKEN and MEMEBOT_TG_CHAT and enable telegram in config.
Failures are logged and swallowed — notifications must never break trading.
"""
from __future__ import annotations

import logging

import requests

from ..config import env

log = logging.getLogger(__name__)


class Notifier:
    def __init__(self, enabled: bool):
        self.token = env("MEMEBOT_TG_TOKEN")
        self.chat = env("MEMEBOT_TG_CHAT")
        self.enabled = bool(enabled and self.token and self.chat)

    def send(self, text: str) -> None:
        log.info("NOTIFY: %s", text)
        if not self.enabled:
            return
        try:
            requests.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                json={"chat_id": self.chat, "text": text}, timeout=10,
            )
        except requests.RequestException as e:
            log.warning("telegram send failed: %s", e)
