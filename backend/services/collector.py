import time
import httpx
import pandas as pd
from .utils import (
    EXCHANGE,
    BINGX_BASE_URL,
    BINANCE_BASE_URL,
    CANDLES_CACHE_SEC,
    HTTP_RETRIES,
    HTTP_BACKOFF_BASE,
)

# In-memory cache to reduce repeated HTTP calls per symbol/interval/limit
_CANDLE_CACHE = {}


def _get_with_retries(url: str, params: dict) -> httpx.Response:
    last_err = None
    for attempt in range(HTTP_RETRIES + 1):
        try:
            r = httpx.get(url, params=params, timeout=20)
            r.raise_for_status()
            return r
        except Exception as e:
            last_err = e
            sleep = HTTP_BACKOFF_BASE * (2 ** attempt)
            time.sleep(sleep)
    # raise last error if all attempts fail
    raise last_err


def _bingx_klines(symbol: str, interval: str, limit: int = 500) -> pd.DataFrame:
    url = f"{BINGX_BASE_URL}/openApi/swap/v3/quote/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    r = _get_with_retries(url, params)
    data = r.json().get("data", [])
    if not data:
        # force fallback if BingX returns empty
        raise ValueError("BingX klines vazio")
    cols = ["open_time", "open", "high", "low", "close", "volume"]
    df = pd.DataFrame(data, columns=cols)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df = df.astype(
        {"open": float, "high": float, "low": float, "close": float, "volume": float}
    )
    return df


def _binance_klines(symbol: str, interval: str, limit: int = 500) -> pd.DataFrame:
    url = f"{BINANCE_BASE_URL}/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    r = _get_with_retries(url, params)
    raw = r.json()
    df = pd.DataFrame(
        raw,
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "qav",
            "trades",
            "taker_base",
            "taker_quote",
            "ignore",
        ],
    )
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df = df[["open_time", "open", "high", "low", "close", "volume"]]
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    return df


def get_klines(symbol: str, interval: str, limit: int = 500) -> pd.DataFrame:
    symbol = str(symbol).upper()
    key = (symbol, interval, int(limit))
    now = time.time()
    cached = _CANDLE_CACHE.get(key)
    if cached:
        ts, df_cached = cached
        if (now - ts) < CANDLES_CACHE_SEC and df_cached is not None:
            return df_cached.copy()

    if EXCHANGE == "BINGX":
        try:
            df = _bingx_klines(symbol, interval, limit)
        except Exception:
            df = _binance_klines(symbol, interval, limit)
    else:
        df = _binance_klines(symbol, interval, limit)

    if not df.empty:
        df = df.sort_values("open_time").reset_index(drop=True)
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    _CANDLE_CACHE[key] = (now, df)
    return df
