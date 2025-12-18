from collections import defaultdict
from typing import Dict


_METRICS = defaultdict(lambda: {"tp": 0, "fp": 0, "total": 0})
_REGIME_METRICS = defaultdict(lambda: {"tp": 0, "fp": 0, "total": 0})


def update_metrics(symbol: str, regime: str, signal: str, fwd_ret_5: float | None) -> None:
    if fwd_ret_5 is None:
        return
    if signal == "NEUTRO":
        return

    key = symbol.upper()
    _METRICS[key]["total"] += 1
    _REGIME_METRICS[regime]["total"] += 1

    is_long = signal.startswith("LONG")
    is_short = signal.startswith("SHORT")
    win = (is_long and fwd_ret_5 > 0) or (is_short and fwd_ret_5 < 0)
    if win:
        _METRICS[key]["tp"] += 1
        _REGIME_METRICS[regime]["tp"] += 1
    else:
        _METRICS[key]["fp"] += 1
        _REGIME_METRICS[regime]["fp"] += 1


def snapshot() -> Dict[str, Dict[str, float]]:
    out = {}
    for key, item in _METRICS.items():
        total = item["total"] or 1
        out[key] = {
            "precision": round(item["tp"] / total, 4),
            "total": item["total"],
        }
    return out


def snapshot_by_regime() -> Dict[str, Dict[str, float]]:
    out = {}
    for key, item in _REGIME_METRICS.items():
        total = item["total"] or 1
        out[key] = {
            "precision": round(item["tp"] / total, 4),
            "total": item["total"],
        }
    return out
