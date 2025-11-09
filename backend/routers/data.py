from fastapi import APIRouter, Query
from services.collector import get_klines
from services.features import add_indicators, generate_short_signals
from services.utils import DEFAULT_SYMBOL, DEFAULT_INTERVAL, CANDLES_LIMIT

router = APIRouter()


@router.get("/candles")
def candles(
    symbol: str = DEFAULT_SYMBOL,
    interval: str = DEFAULT_INTERVAL,
    limit: int = CANDLES_LIMIT,
):
    df = get_klines(symbol, interval, limit)
    if df is None or df.empty:
        return []
    df["open_time"] = df["open_time"].astype(str)
    return df.to_dict(orient="records")


@router.get("/signals")
def signals(
    symbol: str = DEFAULT_SYMBOL,
    interval: str = DEFAULT_INTERVAL,
    limit: int = CANDLES_LIMIT,
):
    df = get_klines(symbol, interval, limit)
    if df is None or df.empty:
        return []
    df = add_indicators(df)
    df = generate_short_signals(df)
    return df.tail(10).to_dict(orient="records")
