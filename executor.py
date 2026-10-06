import math, json, time
from . import config

def portfolio_value(balance, ticker):
    """USD換算の総評価額と現在ウェイト"""
    spot = balance.get("SpotWallet", {})
    usd = spot.get("USD", {}).get("Free", 0.0) + spot.get("USD", {}).get("Lock", 0.0)
    vals = {}
    total = usd
    for sym, d in spot.items():
        if sym == "USD":
            continue
        amt = d.get("Free", 0.0) + d.get("Lock", 0.0)
        if amt <= 0:
            continue
        t = ticker.get(f"{sym}/USD")
        if not t:
            continue
        v = amt * (t["MaxBid"] + t["MinAsk"]) / 2
        vals[sym] = v
        total += v
    cur = {s: v / total for s, v in vals.items()} if total > 0 else {}
    return total, cur

class Executor:
    def __init__(self, api, log):
        self.api = api; self.log = log

    def rebalance(self, target, ticker, balance):
        """目標ウェイトへ寄せる。売りを先に。2%未満の差は無視"""
        total, cur = portfolio_value(balance, ticker)
        syms = set(target) | set(cur)
        diffs = {s: target.get(s, 0.0) - cur.get(s, 0.0) for s in syms}
        plan = [(s, d) for s, d in diffs.items() if abs(d) >= config.MIN_DW]
        plan.sort(key=lambda x: x[1])  # 売り(負)が先
        results = []
        for s, d in plan:
            side = "BUY" if d > 0 else "SELL"
            usd_amt = abs(d) * total
            mid = (ticker[f"{s}/USD"]["MaxBid"] + ticker[f"{s}/USD"]["MinAsk"]) / 2
            qty = math.floor(usd_amt / mid * 1e6) / 1e6
            if usd_amt < 2 or qty <= 0:
                continue
            action = {"sym": s, "side": side, "usd": round(usd_amt, 2), "qty": qty}
            if config.DRY_RUN:
                results.append({**action, "status": "dry_run"})
                continue
            try:
                r = self.api.market_order(f"{s}/USD", side, qty)
                od = r.get("OrderDetail", {})
                results.append({**action, "status": "ok" if r.get("Success") else "err",
                                "err": r.get("ErrMsg"), "filled": od.get("FilledQuantity"),
                                "avg_px": od.get("FilledAverPrice"), "fee_pct": od.get("CommissionPercent")})
            except Exception as e:
                results.append({**action, "status": "exception", "err": str(e)})
            time.sleep(0.3)
        return results

    def flatten(self, ticker, balance):
        """全保有を成行で解消"""
        spot = balance.get("SpotWallet", {})
        results = []
        for sym, d in spot.items():
            if sym == "USD":
                continue
            amt = d.get("Free", 0.0)
            if amt <= 0:
                continue
            if config.DRY_RUN:
                results.append({"sym": sym, "side": "SELL", "qty": amt, "status": "dry_run"})
                continue
            try:
                r = self.api.market_order(f"{sym}/USD", "SELL", str(amt))
                results.append({"sym": sym, "side": "SELL", "qty": amt,
                                "status": "ok" if r.get("Success") else "err", "err": r.get("ErrMsg")})
            except Exception as e:
                results.append({"sym": sym, "side": "SELL", "qty": amt, "status": "exception", "err": str(e)})
            time.sleep(0.3)
        return results
