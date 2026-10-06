import hmac, hashlib, time, requests
from . import config

class ApiError(Exception):
    pass

class Roostoo:
    def __init__(self):
        self.s = requests.Session()
        self._fail_streak = 0

    def _ts(self):
        try:
            r = self.s.get(f"{config.BASE_URL}/v3/serverTime", timeout=10)
            return str(r.json()["ServerTime"])
        except Exception:
            return str(int(time.time() * 1000))

    def _signed(self, payload: dict):
        payload["timestamp"] = self._ts()
        tp = "&".join(f"{k}={payload[k]}" for k in sorted(payload))
        sig = hmac.new(config.API_SECRET.encode(), tp.encode(), hashlib.sha256).hexdigest()
        return {"RST-API-KEY": config.API_KEY, "MSG-SIGNATURE": sig,
                "Content-Type": "application/x-www-form-urlencoded"}, tp

    def _request(self, method, path, payload=None, signed=True):
        payload = payload or {}
        headers, tp = self._signed(dict(payload)) if signed else ({}, "")
        url = f"{config.BASE_URL}{path}"
        try:
            if method == "GET":
                r = self.s.get(url, headers=headers, params=(tp if signed else payload), timeout=15)
            else:
                r = self.s.post(url, headers=headers, data=tp, timeout=15)
            r.raise_for_status()
            j = r.json()
            self._fail_streak = 0
            return j
        except Exception as e:
            self._fail_streak += 1
            if self._fail_streak >= 5:
                raise ApiError(f"5 consecutive API failures: {e}")
            raise

    def ticker(self):
        return self._request("GET", "/v3/ticker", {"timestamp": self._ts()}, signed=False)["Data"]

    def balance(self):
        return self._request("GET", "/v3/balance")

    def pending_count(self):
        return self._request("GET", "/v3/pending_count")

    def market_order(self, pair, side, quantity):
        return self._request("POST", "/v3/place_order",
                             {"pair": pair, "side": side, "type": "MARKET", "quantity": str(quantity)})

    def cancel_all(self, pair):
        return self._request("POST", "/v3/cancel_order", {"pair": pair})
