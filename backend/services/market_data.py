from datetime import datetime
from typing import Dict, List, Tuple

import pandas as pd

from .collector import get_klines
from .market_stream import get_cached_1m, start_stream

_QUALITY_CACHE: Dict[Tuple[str, str], Dict[str, int]] = {}


def _validate_df(df: pd.DataFrame, interval_min: int) -> Dict[str, int]:
    if df.empty:
        return {"gaps": 0, "dups": 0}
    ts = pd.to_datetime(df["open_time"]).dropna()
    dups = int(ts.duplicated().sum())
    diffs = ts.sort_values().diff().dt.total_seconds().dropna()
    gap_threshold = interval_min * 60 * 1.5
    gaps = int((diffs > gap_threshold).sum())
    return {"gaps": gaps, "dups": dups}


def _resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    df = df.copy()
    df["open_time"] = pd.to_datetime(df["open_time"])
    df = df.set_index("open_time").sort_index()
    agg = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    out = df.resample(rule, label="right", closed="right").agg(agg).dropna()
    out = out.reset_index()
    return out


def get_ohlcv(symbol: str, interval: str, limit: int) -> pd.DataFrame:
    symbol = symbol.upper()
    if interval == "1m":
        start_stream()
        cached = get_cached_1m(symbol.lower(), limit)
        if cached:
            df = pd.DataFrame(cached)
            _QUALITY_CACHE[(symbol, interval)] = _validate_df(df, 1)
            return df

    df = get_klines(symbol, interval, limit)
    interval_min = 1 if interval == "1m" else 5 if interval == "5m" else 15
    _QUALITY_CACHE[(symbol, interval)] = _validate_df(df, interval_min)
    return df


def get_multi_timeframe(symbol: str, limit_1m: int = 1000) -> Dict[str, pd.DataFrame]:
    df_1m = get_ohlcv(symbol, "1m", limit_1m)
    if df_1m is None or df_1m.empty:
        return {"1m": df_1m, "5m": pd.DataFrame(), "15m": pd.DataFrame()}
    df_5m = _resample(df_1m, "5min")
    df_15m = _resample(df_1m, "15min")
    _QUALITY_CACHE[(symbol, "5m")] = _validate_df(df_5m, 5)
    _QUALITY_CACHE[(symbol, "15m")] = _validate_df(df_15m, 15)
    return {"1m": df_1m, "5m": df_5m, "15m": df_15m}


def get_quality(symbol: str, interval: str) -> Dict[str, int]:
    return _QUALITY_CACHE.get((symbol.upper(), interval), {"gaps": 0, "dups": 0})
