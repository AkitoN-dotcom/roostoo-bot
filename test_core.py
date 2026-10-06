import pandas as pd, numpy as np, sys
sys.path.insert(0, ".")
from roostoo_bot import config
from roostoo_bot.signals import momentum_weights, crash_check
from roostoo_bot.risk import apply_caps

def mkhist(trend):
    idx = pd.date_range("2026-01-01", periods=200, freq="h", tz="UTC")
    data = {}
    for sym, slope in trend.items():
        data[sym] = 100 * np.cumprod(1 + np.full(200, slope))
    return pd.DataFrame(data, index=idx)

def test_momentum_picks_top_gainers():
    hist = mkhist({"BTC": 0.001, "ETH": 0.002, "SOL": -0.001, "XRP": 0.0005})
    w = momentum_weights(hist)
    assert set(w) == {"ETH", "BTC", "XRP"}  # SOLはマイナスなので除外
    assert abs(sum(w.values()) - config.GROSS) < 1e-9

def test_all_negative_goes_cash():
    hist = mkhist({"BTC": -0.001, "ETH": -0.002, "SOL": -0.001})
    assert momentum_weights(hist) == {}

def test_caps():
    w = apply_caps({"BTC": 0.5, "ETH": 0.5})
    assert max(w.values()) <= config.PER_ASSET_CAP + 1e-9
    assert sum(w.values()) <= config.GROSS + 1e-9

def test_crash_guard():
    hist = mkhist({"BTC": 0.0, "ETH": 0.0})
    hist.loc[hist.index[-1], "BTC"] = hist["BTC"].iloc[-25] * 0.85  # 24hで-15%
    assert crash_check(hist, ["BTC", "ETH"]) == ["BTC"]

def test_insufficient_history():
    hist = mkhist({"BTC": 0.001}).tail(100)
    assert momentum_weights(hist) == {}
