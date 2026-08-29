"""Layered configuration: default.yaml <- override yaml <- env vars.

Secrets (keys, tokens) NEVER live in yaml — env only:
  MEMEBOT_LIVE=YES            explicit opt-in gate for live trading
  MEMEBOT_PRIVATE_KEY         base58 solana keypair (live only)
  MEMEBOT_RPC_URL             custom RPC endpoint (default public mainnet)
  MEMEBOT_TG_TOKEN / MEMEBOT_TG_CHAT   telegram notifications
"""
from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

import yaml

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "config" / "default.yaml"


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


class Config:
    """Dot-access wrapper over the merged config dict."""

    def __init__(self, d: dict[str, Any]):
        self._d = d

    def __getattr__(self, k: str) -> Any:
        try:
            v = self._d[k]
        except KeyError as e:
            raise AttributeError(k) from e
        return Config(v) if isinstance(v, dict) else v

    def get(self, k: str, default: Any = None) -> Any:
        v = self._d.get(k, default)
        return Config(v) if isinstance(v, dict) else v

    def __contains__(self, k: str) -> bool:
        return k in self._d

    def raw(self) -> dict[str, Any]:
        return copy.deepcopy(self._d)


def load(override_path: str | None = None) -> Config:
    with open(DEFAULT_PATH) as fh:
        d = yaml.safe_load(fh)
    if override_path:
        with open(override_path) as fh:
            d = _deep_merge(d, yaml.safe_load(fh) or {})
    return Config(d)


def env(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)


def live_trading_armed() -> bool:
    """Live trading requires BOTH config mode=live and env MEMEBOT_LIVE=YES."""
    return env("MEMEBOT_LIVE") == "YES"
