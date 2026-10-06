import numpy as np, pandas as pd, glob, json, itertools

FEE = 0.001          # 実測: テイカー0.1%/片道
MIN_TRADE_DW = 0.02  # 2%未満のウェイト差は見送り

# --- data ---
frames = {}
for f in glob.glob("data/klines/*.csv"):
    sym = f.split("/")[-1][:-4]
    df = pd.read_csv(f, parse_dates=["timestamp"])[["timestamp","close"]].set_index("timestamp")
    frames[sym] = df["close"]
px = pd.DataFrame(frames).dropna()
SYMS = list(px.columns)
R = px.pct_change().fillna(0).values
C = px.values
T, N = C.shape
print(f"data: {T} hours x {N} assets, {px.index[0]} .. {px.index[-1]}")

def simulate(target_w_fn, rebal_h, gross, voltarget=None, name=""):
    """target_w_fn(t) -> weight vector at rebalance times. Returns hourly equity."""
    eq = 1.0
    w = np.zeros(N)
    eqs = np.empty(T); fees = 0.0; trades = 0
    for t in range(T):
        if t > 0:
            r = R[t]
            port_r = w @ r
            eq *= (1 + port_r)
            if abs(port_r) < 0.5:
                w = w * (1 + r) / (1 + port_r)
        if t % rebal_h == 0 and t > 0:
            tw = target_w_fn(t) * gross
            if voltarget is not None:
                tw = tw * vol_scale(t, tw, voltarget)
            dw = np.abs(tw - w)
            mask = dw >= MIN_TRADE_DW
            turn = np.where(mask, dw, 0).sum()
            if turn > 0:
                fee = FEE * turn
                eq *= (1 - fee); fees += fee; trades += int(mask.sum())
                w = np.where(mask, tw, w)
        eqs[t] = eq
    return eqs, fees, trades

def vol_scale(t, tw, target_dvol):
    """30日実現ボラでスケールダウン（上乗せはしない）"""
    if t < 31*24: return 1.0
    rets = (C[t-30*24:t] / C[t-30*24-1:t-1] - 1)
    dvol = np.nanstd(rets[::24], axis=0) * 1.0
    sc = np.where(dvol > 0, np.minimum(1.0, target_dvol/np.maximum(dvol,1e-9)), 1.0)
    active = np.abs(tw) > 0
    if active.sum() == 0: return 1.0
    return float(np.clip(np.min(sc[active]), 0.1, 1.0))

def mom_ret(t, L):
    if t < L: return np.zeros(N)
    return C[t]/C[t-L] - 1

def rsi14(t):
    if t < 15: return np.full(N, 50.0)
    d = np.diff(C[t-15:t+1], axis=0)
    up = np.where(d>0, d, 0).mean(axis=0); dn = -np.where(d<0, d, 0).mean(axis=0)
    rs = np.divide(up, dn, out=np.full(N, 1e9), where=dn>1e-12)
    return 100 - 100/(1+rs)

def metrics(eqs, fees, trades):
    e = pd.Series(eqs, index=px.index)
    d = e.resample("1D").last().dropna()
    dr = d.pct_change().dropna()
    tot = e.iloc[-1]/e.iloc[0]-1
    sh = dr.mean()/dr.std()*np.sqrt(365) if dr.std()>0 else 0
    dn = dr[dr<0]
    so = dr.mean()/dn.std()*np.sqrt(365) if len(dn)>1 and dn.std()>0 else 0
    dd = (e/e.cummax()-1).min()
    calm = tot/abs(dd) if dd<0 else np.nan
    # rolling 14-day windows (336h), step 24h
    wr, wdd, wsh = [], [], []
    for s in range(0, T-336, 24):
        seg = eqs[s:s+336]
        r_ = np.diff(seg)/seg[:-1]
        wr.append(seg[-1]/seg[0]-1)
        wdd.append((seg/np.maximum.accumulate(seg)-1).min())
        sd = r_.std()
        wsh.append(r_.mean()/sd*np.sqrt(24*365) if sd>0 else 0)
    wr, wdd, wsh = np.array(wr), np.array(wdd), np.array(wsh)
    return dict(total_ret=tot, sharpe=sh, sortino=so, maxdd=dd, calmar=calm,
                fees=fees, trades=trades,
                w_ret_med=np.median(wr), w_ret_p25=np.percentile(wr,25), w_ret_p75=np.percentile(wr,75),
                w_ret_min=wr.min(), w_pos=(wr>0).mean(),
                w_dd_worst=wdd.min(), w_sh_med=np.median(wsh))

rows = []
def add(name, fn, R_h, gross, vt=None, **params):
    eqs, fees, trades = simulate(fn, R_h, gross, vt)
    m = metrics(eqs, fees, trades)
    rows.append(dict(strategy=name, params=json.dumps(params), rebal_h=R_h, gross=gross, voltarget=vt, **m))

# A. 時系列モメンタム
for L, thr, Rh, vt in itertools.product([24,72,168],[0.0,0.01],[4,24],[None,0.03]):
    def fn(t, L=L, thr=thr):
        r = mom_ret(t, L); w = np.where(r>thr, 1.0, 0.0)
        n = (w>0).sum()
        return w/n if n>0 else w
    add("ts_mom", fn, Rh, 0.8, vt, L=L, thr=thr)

# B. クロスセクショナル・モメンタム
for L, k, Rh, ls, vt in itertools.product([24,72,168],[1,2,3],[4,24],[False,True],[None,0.03]):
    def fn(t, L=L, k=k, ls=ls):
        r = mom_ret(t, L); w = np.zeros(N)
        order = np.argsort(-r)
        longs = [i for i in order[:k] if r[i]>0]
        for i in longs: w[i] = 1.0/len(longs) if longs else 0
        if ls:
            shorts = [i for i in order[-k:] if r[i]<0]
            for i in shorts: w[i] = -(1.0/len(shorts) if shorts else 0)
            if longs: w[longs] *= 0.5/ (sum(w[longs]) or 1) if False else 1  # keep simple
        return w
    if ls:  # LSはロング0.5/ショート0.5
        def fn2(t, L=L, k=k):
            r = mom_ret(t, L); w = np.zeros(N)
            order = np.argsort(-r)
            longs = [i for i in order[:k] if r[i]>0]
            shorts = [i for i in order[-k:] if r[i]<0]
            if longs:
                for i in longs: w[i] = 0.5/len(longs)
            if shorts:
                for i in shorts: w[i] = -0.5/len(shorts)
            return w
        add("xs_mom_ls", fn2, Rh, 0.8, vt, L=L, k=k)
    else:
        add("xs_mom", fn, Rh, 0.8, vt, L=L, k=k)

# C. 平均回帰 RSI
def mr_fn(t):
    rs = rsi14(t)
    w = np.where(rs<30, 0.2, 0.0)
    return w
add("mean_rev_rsi", mr_fn, 4, 0.8)

# E. ベンチマーク
add("bench_btc", lambda t: np.array([1.0 if s=="BTC" else 0.0 for s in SYMS]), 24, 1.0)
add("bench_eqw", lambda t: np.full(N, 1.0/N), 24, 1.0)

df = pd.DataFrame(rows)
df.to_csv("results/backtest_summary.csv", index=False)
cols = ["strategy","params","rebal_h","voltarget","total_ret","sharpe","sortino","maxdd","calmar",
        "w_ret_med","w_pos","w_dd_worst","w_sh_med","fees","trades"]
print("\n=== TOP12 by 14d-window median Sharpe ===")
print(df.sort_values("w_sh_med", ascending=False)[cols].head(12).to_string(index=False, float_format=lambda x: f"{x:.3f}"))
print("\n=== TOP12 by 14d-window median return ===")
print(df.sort_values("w_ret_med", ascending=False)[cols].head(12).to_string(index=False, float_format=lambda x: f"{x:.3f}"))
print("\n=== benchmarks ===")
print(df[df.strategy.str.startswith("bench")][cols].to_string(index=False, float_format=lambda x: f"{x:.3f}"))
