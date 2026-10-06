import os
from pathlib import Path

def _load_env():
    p = Path(__file__).resolve().parent.parent / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
_load_env()

MODE = os.environ.get("MODE", "test")  # "test" or "prod"
DRY_RUN = os.environ.get("DRY_RUN", "0") == "1"

API_KEY = os.environ["ROOSTOO_PROD_KEY" if MODE == "prod" else "ROOSTOO_TEST_KEY"]
API_SECRET = os.environ["ROOSTOO_PROD_SECRET" if MODE == "prod" else "ROOSTOO_TEST_SECRET"]
BASE_URL = "https://mock-api.roostoo.com"

UNIVERSE = ["BTC","ETH","SOL","XRP","DOGE","ADA","AVAX","LINK","LTC","UNI","NEAR","SUI","DOT","HBAR"]
LOOKBACK_H = 168          # 7日モメンタム
TOP_K = 3
GROSS = 0.80              # 総投下上限
PER_ASSET_CAP = 0.30
REBALANCE_UTC_HOUR = 0    # 毎日00:00 UTCにリバランス
LOOP_SECONDS = 3600
MIN_DW = 0.02             # 2%未満の差は取引しない
CRASH_GUARD_24H = -0.10   # 保有銘柄が24hで-10%なら即切る
KILL_DD = -0.10           # ピーク比-10%で全解消
HALT_HOURS = 24           # キルスイッチ後の停止時間
FEE_TAKER = 0.001         # 実測値

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs"; LOG_DIR.mkdir(exist_ok=True)
DATA_DIR = ROOT / "data"; DATA_DIR.mkdir(exist_ok=True)
STATE_FILE = DATA_DIR / "state.json"
PRICE_LOG = DATA_DIR / "price_log.csv"
