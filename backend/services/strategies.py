from typing import Dict


def rule_short_sniper(row: dict) -> Dict[str, int | str]:
    conds = [
        row.get("rsi14", 0) >= 72,
        row.get("vol_z", 0) >= 1.5,
        row.get("upper_wick", 0) >= 0.35,
        row.get("ret_15", 0) >= 0.12,
    ]
    return {"rule_short": int(all(conds)), "rule_long": 0, "strategy": "SHORT_SNIPER"}


def rule_long_dip(row: dict) -> Dict[str, int | str]:
    conds = [
        row.get("rsi14", 100) <= 28,
        row.get("ret_15", 0) <= -0.08,
        row.get("vol_z", 0) >= 1.2,
        row.get("lower_wick", 0) >= 0.30,
    ]
    return {"rule_long": int(all(conds)), "rule_short": 0, "strategy": "LONG_DIP"}


def rule_trend_pullback(row: dict, regime: str) -> Dict[str, int | str]:
    if regime not in ("BULL", "BEAR"):
        return {"rule_long": 0, "rule_short": 0, "strategy": "TREND_PULLBACK"}

    ret_5 = row.get("ret_5", 0)
    vol_z = row.get("vol_z", 0)
    if regime == "BULL":
        conds = [ret_5 < 0, vol_z >= 1.0]
        return {"rule_long": int(all(conds)), "rule_short": 0, "strategy": "TREND_PULLBACK"}
    conds = [ret_5 > 0, vol_z >= 1.0]
    return {"rule_long": 0, "rule_short": int(all(conds)), "strategy": "TREND_PULLBACK"}


def combine_strategies(row: dict, regime: str) -> Dict[str, int | str]:
    candidates = [
        rule_short_sniper(row),
        rule_long_dip(row),
        rule_trend_pullback(row, regime),
    ]

    best = {"rule_long": 0, "rule_short": 0, "strategy": "NONE"}
    for item in candidates:
        if item["rule_long"] == 1 or item["rule_short"] == 1:
            best = item
            break
    return best
