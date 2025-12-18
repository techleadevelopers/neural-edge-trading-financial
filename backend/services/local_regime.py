import math
from typing import Dict

import pandas as pd


def classify_regime(df_15m: pd.DataFrame) -> Dict[str, str]:
    if df_15m is None or df_15m.empty:
        return {"regime": "CHOP"}

    last = df_15m.iloc[-1]
    close = last.get("close")
    ema200 = last.get("ema200")
    ema200_slope = last.get("ema200_slope")
    adx = last.get("adx14")
    atr_ratio = last.get("atr_ratio")

    if close is None or ema200 is None or ema200_slope is None:
        return {"regime": "CHOP"}

    try:
        close = float(close)
        ema200 = float(ema200)
        ema200_slope = float(ema200_slope)
    except (TypeError, ValueError):
        return {"regime": "CHOP"}

    adx_val = float(adx) if adx is not None and math.isfinite(adx) else None
    atr_val = float(atr_ratio) if atr_ratio is not None and math.isfinite(atr_ratio) else None

    if adx_val is not None and adx_val < 18:
        return {"regime": "CHOP"}
    if atr_val is not None and atr_val < 0.003:
        return {"regime": "CHOP"}

    if close > ema200 and ema200_slope > 0:
        return {"regime": "BULL"}
    if close < ema200 and ema200_slope < 0:
        return {"regime": "BEAR"}
    return {"regime": "CHOP"}
