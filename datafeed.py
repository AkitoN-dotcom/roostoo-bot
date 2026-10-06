import time, requests
import pandas as pd
from . import config

def warmup():
    """Coinbase 1h足で価格履歴を初期化（Roostoo価格の代理。乖離±0.15%以内を検証済み）"""
    frames = {}
    for sym in config.UNIVERSE:
        end = int(time.time()); stop = end - 10*86400
        rows = []
        while end > stop:
            start = max(stop, end - 300*3600)
            r = requests.get(f"https://api.exchange.coinbase.com/products/{sym}-USD/candles",
                             params={"granularity": 3600, "start": start, "end": end}, timeout=15)
            b = r.json()
            if not isinstance(b, list) or len(b) <= 1:
                rows += b if isinstance(b, list) else []
                break
            rows += b
            new_end = min(x[0] for x in b)
            if new_end >= end:
                break
            end = new_end
            time.sleep(0.05)
        if rows:
            df = pd.DataFrame(rows, columns=["ts","low","high","open","close","volume"])
            df = df.drop_duplicates("ts").sort_values("ts")
            frames[sym] = pd.Series(df["close"].values, index=pd.to_datetime(df["ts"], unit="s", utc=True))
    px = pd.DataFrame(frames).dropna()
    px.index.name = "timestamp"
    px.to_csv(config.PRICE_LOG)

def load_history():
    if not config.PRICE_LOG.exists():
        warmup()
    df = pd.read_csv(config.PRICE_LOG, parse_dates=["timestamp"], index_col="timestamp")
    return df

def append_tick(ticker_data):
    """Roostoo ticker のミッド価格を1時間に1行追記"""
    now = pd.Timestamp.utcnow().floor("h")
    row = {}
    for sym in config.UNIVERSE:
        d = ticker_data.get(f"{sym}/USD")
        if d:
            row[sym] = (d["MaxBid"] + d["MinAsk"]) / 2
    if len(row) != len(config.UNIVERSE):
        return
    df = load_history()
    df.loc[now] = row
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df.tail(24*30).to_csv(config.PRICE_LOG)  # 30日分だけ保持
