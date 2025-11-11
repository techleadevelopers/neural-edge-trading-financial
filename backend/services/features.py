import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange, BollingerBands


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["close"] = df["close"].astype(float)
    df["volume"] = df["volume"].astype(float)
    # garantir tipos float para OHLC
    if "open" in df: df["open"] = df["open"].astype(float)
    if "high" in df: df["high"] = df["high"].astype(float)
    if "low" in df: df["low"] = df["low"].astype(float)

    # RSI 14
    rsi = RSIIndicator(df["close"], window=14)
    df["rsi14"] = rsi.rsi()
    # RSI meta: slope 3 e zscore 50
    try:
        df["rsi_slope3"] = df["rsi14"].diff(3)
        rsi_ma50 = df["rsi14"].rolling(50, min_periods=10).mean()
        rsi_sd50 = df["rsi14"].rolling(50, min_periods=10).std()
        df["rsi_z"] = (df["rsi14"] - rsi_ma50) / (rsi_sd50 + 1e-9)
    except Exception:
        df["rsi_slope3"] = pd.NA
        df["rsi_z"] = pd.NA

    # Variações
    df["ret_1"] = df["close"].pct_change()
    df["ret_5"] = df["close"].pct_change(5)
    df["ret_15"] = df["close"].pct_change(15)

    # Spike de volume (z-score)
    df["vol_ma20"] = df["volume"].rolling(20).mean()
    df["vol_std20"] = df["volume"].rolling(20).std()
    df["vol_z"] = (df["volume"] - df["vol_ma20"]) / (df["vol_std20"] + 1e-9)
    df["vol_ratio"] = df["volume"] / (df["vol_ma20"] + 1e-9)

    # Candle de exaustão (sombra superior grande)
    df["upper_wick"] = (
        (df["high"] - df[["close", "open"]].max(axis=1))
        / (df["high"] - df["low"] + 1e-9)
    )

    # Corpo normalizado e razão de pavio superior
    if "open" in df and "high" in df and "low" in df:
        rng = (df["high"] - df["low"]).replace(0, np.nan)
        df["body_norm"] = ((df["close"] - df["open"]) / (rng + 1e-9)).clip(-5, 5)
        df["wick_ratio"] = ((df["high"] - df["close"]) / (rng + 1e-9)).clip(0, 1)

    # Tendência: EMA20/EMA50 e distância relativa
    try:
        ema20 = EMAIndicator(close=df["close"], window=20).ema_indicator()
        ema50 = EMAIndicator(close=df["close"], window=50).ema_indicator()
        df["ema20"] = ema20
        df["ema50"] = ema50
        df["ema_dist20"] = (df["close"] - ema20) / (ema20 + 1e-9)
        df["ema_dist50"] = (df["close"] - ema50) / (ema50 + 1e-9)
    except Exception:
        pass

    # Bollinger Bands (20, 2) e largura de banda
    try:
        bb = BollingerBands(close=df["close"], window=20, window_dev=2.0)
        df["bb_high"] = bb.bollinger_hband()
        df["bb_low"] = bb.bollinger_lband()
        width = (df["bb_high"] - df["bb_low"]).abs()
        df["bb_bw"] = width / (df["close"] + 1e-9)
        df["bb_pos"] = (df["close"] - df["bb_low"]) / (width + 1e-9)
    except Exception:
        pass

    # ATR14 (volatilidade absoluta)
    try:
        atr = AverageTrueRange(high=df["high"], low=df["low"], close=df["close"], window=14)
        df["atr14"] = atr.average_true_range()
        df["atr_ratio"] = df["atr14"] / (df["close"].rolling(5).mean() + 1e-9)
    except Exception:
        pass

    return df


def rule_short_sniper_row(row) -> int:
    """
    1) RSI alto (>= 72)
    2) Volume em spike (vol_z >= 1.5)
    3) Sombra superior relevante (upper_wick >= 0.35) – exaustão
    4) Retorno 15 barras esticado (ret_15 >= 0.12)
    """
    conds = [
        row.get("rsi14", 0) >= 72,
        row.get("vol_z", 0) >= 1.5,
        row.get("upper_wick", 0) >= 0.35,
        row.get("ret_15", 0) >= 0.12,
    ]
    return int(all(conds))


def generate_short_signals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["short_signal"] = df.apply(rule_short_sniper_row, axis=1)
    return df
