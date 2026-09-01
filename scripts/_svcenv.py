"""Read the configuration the SERVICE is running, not this process's.

Analysis commands run as separate processes and never source the systemd
EnvironmentFile, so reading os.environ showed package defaults and labelled
them current. That is not a cosmetic bug: MEMEBOT_MIN_ACCEL=0 was set, the
service honoured it, and the screens built to verify configuration kept
printing 1.0. A display that cannot see a config change turns an unverified
belief into an apparently verified one.

One implementation, used by every tool, so the tools cannot drift from each
other the way they drifted from the service.
"""
from __future__ import annotations

import importlib
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATHS = ("/etc/memebot/secrets.env", os.path.join(REPO, "data", "secrets.env"))

DEFAULTS = {"MEMEBOT_FEED": "both", "MEMEBOT_MIN_RANGE": "0.172",
            "MEMEBOT_MIN_ACCEL": "1.0", "MEMEBOT_MAX_ACCEL": "10.0",
            "MEMEBOT_MAX_DRAWDOWN": "1.0",
            "MEMEBOT_PORTAL_STREAM": "migration",
            "MEMEBOT_HELIUS_HOURLY_CAP": "200", "MEMEBOT_TRAIL": "0.10"}


def read_envfile() -> dict:
    """Parse the first service env file that exists. Never raises."""
    for path in PATHS:
        found = {}
        try:
            with open(path) as fh:
                for line in fh:
                    line = line.strip()
                    if line.startswith("export "):
                        line = line[7:]
                    if line and not line.startswith("#") and "=" in line:
                        k, _, v = line.partition("=")
                        found[k.strip()] = v.strip().strip('"').strip("'")
        except OSError:
            continue
        return found
    return {}


def load_scalper():
    """Import the scalper with the service's values in place.

    Returns (module, envfile). The module's constants are then the ones
    actually in force, so a tool can print and filter on them instead of
    hard-coding numbers that go stale the moment a threshold is tuned.
    """
    envfile = read_envfile()
    if os.path.join(REPO, "src") not in sys.path:
        sys.path.insert(0, os.path.join(REPO, "src"))
    for k, v in envfile.items():
        os.environ.setdefault(k, v)
    import memebot.live.scalper as sc
    importlib.reload(sc)
    return sc, envfile
