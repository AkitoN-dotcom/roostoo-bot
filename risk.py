import json, time
from . import config

def load_state():
    if config.STATE_FILE.exists():
        return json.loads(config.STATE_FILE.read_text())
    return {"peak_equity": None, "halt_until": 0, "active_days": []}

def save_state(st):
    config.STATE_FILE.write_text(json.dumps(st, indent=2))

def check_kill_switch(equity, st):
    """ピーク比DDが閾値を超えたら True を返す。ピークは state に永続化"""
    if st["peak_equity"] is None or equity > st["peak_equity"]:
        st["peak_equity"] = equity
        save_state(st)
        return False
    dd = equity / st["peak_equity"] - 1
    if dd <= config.KILL_DD and time.time() >= st.get("halt_until", 0):
        st["halt_until"] = time.time() + config.HALT_HOURS * 3600
        save_state(st)
        return True
    return False

def is_halted(st):
    return time.time() < st.get("halt_until", 0)

def apply_caps(weights):
    """目標ウェイトに上限を適用"""
    w = {s: min(v, config.PER_ASSET_CAP) for s, v in weights.items()}
    total = sum(w.values())
    if total > config.GROSS:
        w = {s: v * config.GROSS / total for s, v in w.items()}
    return w
