import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["close"] = df["close"].astype(float)
    df["volume"] = df["volume"].astype(float)

    # RSI 14
    rsi = RSIIndicator(df["close"], window=14)
    df["rsi14"] = rsi.rsi()

    # Variações
    df["ret_1"] = df["close"].pct_change()
    df["ret_5"] = df["close"].pct_change(5)
    df["ret_15"] = df["close"].pct_change(15)

    # Spike de volume (z-score)
    df["vol_ma20"] = df["volume"].rolling(20).mean()
    df["vol_std20"] = df["volume"].rolling(20).std()
    df["vol_z"] = (df["volume"] - df["vol_ma20"]) / (df["vol_std20"] + 1e-9)

    # Candle de exaustão (sombra superior grande)
    df["upper_wick"] = (
        (df["high"] - df[["close", "open"]].astype(float).max(axis=1))
        / (df["high"] - df["low"] + 1e-9)
    )

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

