import requests, time, json, os
import pandas as pd

SYMS = ["BTC","ETH","SOL","XRP","DOGE","ADA","AVAX","LINK","LTC","UNI","NEAR","SUI","DOT","HBAR"]
DAYS = 180
os.makedirs("data/klines", exist_ok=True)
report = {}
for sym in SYMS:
    try:
        rows = []
        end = int(time.time())
        stop = end - DAYS*86400
        while end > stop:
            start = max(stop, end - 300*3600)
            r = requests.get(f"https://api.exchange.coinbase.com/products/{sym}-USD/candles",
                             params={"granularity":3600,"start":start,"end":end}, timeout=15)
            if r.status_code != 200:
                report[sym] = f"HTTP {r.status_code}: {r.text[:60]}"; break
            batch = r.json()
            if len(batch) <= 1:
                rows += batch
                break
            rows += batch
            new_end = min(b[0] for b in batch)
            if new_end >= end:   # 進捗なし＝これ以上古いデータ無し
                break
            end = new_end
            time.sleep(0.08)
        if rows:
            df = pd.DataFrame(rows, columns=["ts","low","high","open","close","volume"])
            df = df.drop_duplicates("ts").sort_values("ts")
            df["timestamp"] = pd.to_datetime(df["ts"], unit="s", utc=True)
            df[["timestamp","open","high","low","close","volume"]].to_csv(f"data/klines/{sym}.csv", index=False)
            report[sym] = f"{len(df)} rows, {str(df['timestamp'].iloc[0])[:10]} .. {str(df['timestamp'].iloc[-1])[:10]}"
    except Exception as e:
        report[sym] = f"ERROR {e}"
print(json.dumps(report, indent=2))
