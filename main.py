import json, time, datetime, sys
from pathlib import Path
from . import config
from .api_client import Roostoo, ApiError
from .datafeed import warmup, load_history, append_tick
from .signals import momentum_weights, crash_check
from .risk import load_state, save_state, check_kill_switch, is_halted, apply_caps
from .executor import Executor, portfolio_value

def log(event, **kw):
    rec = {"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(), "event": event, **kw}
    day = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
    with open(config.LOG_DIR / f"{day}.jsonl", "a") as f:
        f.write(json.dumps(rec, default=str) + "\n")
    print(json.dumps(rec, default=str), flush=True)

def main():
    if Path("HALT").exists():
        print("HALT file exists; refusing to start"); sys.exit(1)
    log("boot", mode=config.MODE, dry_run=config.DRY_RUN)
    try:
        warmup()
    except Exception as e:
        log("warmup_failed", err=str(e))
    api = Roostoo(); ex = Executor(api, log)
    last_rebal_date = load_state().get("last_rebal")  # Noneなら初回即リバランス
    while True:
        try:
            if Path("HALT").exists():
                log("halt_file_detected"); break
            ticker = api.ticker()
            append_tick(ticker)
            hist = load_history()
            balance = api.balance()
            equity, cur = portfolio_value(balance, ticker)
            st = load_state()
            today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
            if today not in st["active_days"]:
                st["active_days"].append(today); save_state(st)
            log("heartbeat", equity=round(equity, 2), holdings=cur,
                peak=st["peak_equity"], halted=is_halted(st), active_days=len(st["active_days"]))

            if is_halted(st):
                time.sleep(config.LOOP_SECONDS); continue

            if check_kill_switch(equity, st):
                log("kill_switch_fired", equity=equity, peak=st["peak_equity"])
                res = ex.flatten(ticker, balance)
                log("flatten", results=res)
                time.sleep(config.LOOP_SECONDS); continue

            # クラッシュガード（毎時間）
            crashed = crash_check(hist, [s for s, w in cur.items() if w > 0.01])
            for s in crashed:
                log("crash_guard", sym=s)
            if crashed and not config.DRY_RUN:
                for s in crashed:
                    amt = balance.get("SpotWallet", {}).get(s, {}).get("Free", 0.0)
                    if amt > 0:
                        api.market_order(f"{s}/USD", "SELL", str(amt))
                        time.sleep(0.3)

            # 日次リバランス
            now = datetime.datetime.now(datetime.timezone.utc)
            if (now.hour == config.REBALANCE_UTC_HOUR and last_rebal_date != today) or last_rebal_date is None:
                target = apply_caps(momentum_weights(hist))
                log("rebalance_start", target=target)
                res = ex.rebalance(target, ticker, balance)
                log("rebalance_done", results=res)
                last_rebal_date = today
                st = load_state(); st["last_rebal"] = today; save_state(st)
        except ApiError as e:
            log("api_error_fatal", err=str(e))
            break
        except Exception as e:
            log("loop_error", err=str(e))
        time.sleep(config.LOOP_SECONDS)

if __name__ == "__main__":
    main()
