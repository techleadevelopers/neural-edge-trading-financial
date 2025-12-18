import asyncio
import json
import os
import threading
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Deque, Dict, List

import websockets


BINANCE_WS_URL = "wss://stream.binance.com:9443/stream"

_STREAM_STARTED = False
_LOCK = threading.Lock()
_CANDLES_1M: Dict[str, Deque[dict]] = defaultdict(lambda: deque(maxlen=6000))


def _symbols() -> List[str]:
    raw = os.getenv("FRONTEND_SYMBOLS", "")
    if raw.strip():
        return [s.strip().lower() for s in raw.split(",") if s.strip()]
    return [
        "btcusdt",
        "ethusdt",
        "solusdt",
        "xrpusdt",
        "adausdt",
        "dogeusdt",
        "dotusdt",
        "ltcusdt",
        "maticusdt",
        "avaxusdt",
        "bnbusdt",
        "linkusdt",
        "uniusdt",
        "atomusdt",
        "opususdt",
        "arbusdt",
        "tonusdt",
        "nearusdt",
        "aptusdt",
        "suiusdt",
    ]


def _store_candle(symbol: str, candle: dict) -> None:
    with _LOCK:
        dq = _CANDLES_1M[symbol]
        if dq and dq[-1]["open_time"] == candle["open_time"]:
            dq[-1] = candle
        else:
            dq.append(candle)


async def _listen() -> None:
    streams = "/".join([f"{sym}@kline_1m" for sym in _symbols()])
    url = f"{BINANCE_WS_URL}?streams={streams}"
    async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
        async for msg in ws:
            data = json.loads(msg)
            payload = data.get("data", {})
            k = payload.get("k", {})
            if not k or not k.get("x"):
                continue
            symbol = payload.get("s", "").lower()
            candle = {
                "open_time": datetime.fromtimestamp(k["t"] / 1000, tz=timezone.utc),
                "open": float(k["o"]),
                "high": float(k["h"]),
                "low": float(k["l"]),
                "close": float(k["c"]),
                "volume": float(k["v"]),
            }
            _store_candle(symbol, candle)


def start_stream() -> None:
    global _STREAM_STARTED
    if _STREAM_STARTED:
        return

    def runner():
        while True:
            try:
                asyncio.run(_listen())
            except Exception:
                continue

    thread = threading.Thread(target=runner, name="binance-ws", daemon=True)
    thread.start()
    _STREAM_STARTED = True


def get_cached_1m(symbol: str, limit: int) -> List[dict]:
    with _LOCK:
        dq = list(_CANDLES_1M.get(symbol.lower(), []))
    if not dq:
        return []
    return dq[-limit:]
