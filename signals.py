import numpy as np
from . import config

def momentum_weights(hist):
    """7日モメンタム上位Kに等ウェイト（GROSS按分）。全銘柄マイナスなら現金"""
    if len(hist) < config.LOOKBACK_H + 1:
        return {}
    now = hist.iloc[-1]; past = hist.iloc[-1 - config.LOOKBACK_H]
    ret = (now / past - 1).dropna()
    winners = [s for s in ret.sort_values(ascending=False).index[:config.TOP_K] if ret[s] > 0]
    if not winners:
        return {}
    w = min(config.GROSS / len(winners), config.PER_ASSET_CAP)
    return {s: w for s in winners}

def crash_check(hist, holdings):
    """保有銘柄の24h変化が閾値割れしたらその銘柄を返す"""
    if len(hist) < 25:
        return []
    chg = hist.iloc[-1] / hist.iloc[-25] - 1
    return [s for s in holdings if s in chg and chg[s] <= config.CRASH_GUARD_24H]
