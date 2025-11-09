import httpx
import pandas as pd
from .utils import EXCHANGE, BINGX_BASE_URL, BINANCE_BASE_URL


def _bingx_klines(symbol: str, interval: str, limit: int = 500) -> pd.DataFrame:
    # BingX swap v3 public kline
    url = f"{BINGX_BASE_URL}/openApi/swap/v3/quote/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    r = httpx.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json().get("data", [])
    # Expected: [ [openTime, open, high, low, close, volume], ... ]
    cols = ["open_time", "open", "high", "low", "close", "volume"]
    df = pd.DataFrame(data, columns=cols)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df = df.astype({"open": float, "high": float, "low": float, "close": float, "volume": float})
    return df


def _binance_klines(symbol: str, interval: str, limit: int = 500) -> pd.DataFrame:
    url = f"{BINANCE_BASE_URL}/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    r = httpx.get(url, params=params, timeout=20)
    r.raise_for_status()
    raw = r.json()
    # [ openTime, open, high, low, close, volume, closeTime, ... ]
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
    if EXCHANGE == "BINGX":
        try:
            return _bingx_klines(symbol, interval, limit)
        except Exception:
            return _binance_klines(symbol, interval, limit)
    else:
        return _binance_klines(symbol, interval, limit)

