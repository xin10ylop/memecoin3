import numpy as np
import pandas as pd

from memebot.data.store import sanitize_bars

T0 = 1_700_000_000


def frame(closes):
    ts = [T0 + 60 * i for i in range(len(closes))]
    return pd.DataFrame({
        "o": closes, "h": [c * 1.02 for c in closes],
        "l": [c * 0.98 for c in closes], "c": closes,
        "vol_usd": [100.0] * len(closes),
    }, index=ts)


def test_denomination_glitch_bar_removed():
    closes = [5e-5, 5.2e-5, 5.1e-5, 1519.0, 5.3e-5, 5.2e-5]
    out = sanitize_bars(frame(closes))
    assert len(out) == 5
    assert out["c"].max() < 1e-3


def test_real_pump_untouched():
    # a genuine path-connected 100x pump over 10 bars survives intact
    closes = list(np.geomspace(1e-5, 1e-3, 10))
    out = sanitize_bars(frame(closes))
    assert len(out) == 10
    assert out["c"].iloc[-1] == closes[-1]


def test_real_crash_untouched():
    # a genuine rug: -95% in one bar, stays down (path-connected enough:
    # 20x < 50x threshold)
    closes = [1.0, 1.0, 0.05, 0.04, 0.045, 0.05]
    out = sanitize_bars(frame(closes))
    assert len(out) == 6


def test_nonpositive_prices_removed():
    closes = [1.0, 0.0, 1.0, 1.0, 1.0]
    out = sanitize_bars(frame(closes))
    assert len(out) == 4
