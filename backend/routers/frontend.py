import math
import os
import time
from typing import Dict, List

from fastapi import APIRouter, HTTPException, Query, status

from services.features import add_indicators
from services.local_regime import classify_regime
from services.market_data import get_multi_timeframe, get_quality
from services.metrics import snapshot, snapshot_by_regime, update_metrics
from services.online_model import get_model
from services.openai_audit import audit_signal, explain_signal
from services.strategies import combine_strategies

router = APIRouter()

DEFAULT_SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "ADAUSDT",
    "DOGEUSDT",
    "DOTUSDT",
    "LTCUSDT",
    "MATICUSDT",
    "AVAXUSDT",
]

_CACHED_SIGNALS: List[Dict] = []
_LAST_UPDATE = ""
_LAST_FETCH = 0.0
_LAST_SIGNAL_AT: Dict[str, float] = {}


def _get_symbols() -> List[str]:
    raw = os.getenv("FRONTEND_SYMBOLS", "")
    if raw.strip():
        return [s.strip().upper() for s in raw.split(",") if s.strip()]
    return DEFAULT_SYMBOLS


def _make_id(symbol: str, ts_ms: int) -> int:
    h = 0
    for ch in symbol:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return (ts_ms % 1_000_000_000) + (h % 1000)


def _map_signal_name(raw: str) -> tuple[str, bool]:
    if raw == "SHORT_FORTE":
        return "SHORT_FRACO", True
    if raw == "SHORT_FRACO":
        return "SHORT_FRACO", False
    if raw == "LONG_FORTE":
        return "LONG_FORTE", True
    if raw == "LONG_FRACO":
        return "LONG_FORTE", False
    return "NEUTRO", False


def _build_signal(symbol: str, interval: str, limit: int) -> Dict:
    def safe_float(value):
        if value is None:
            return None
        try:
            num = float(value)
        except (TypeError, ValueError):
            return None
        return num if math.isfinite(num) else None

    data = get_multi_timeframe(symbol, limit_1m=5000)
    df_1m = data.get("1m")
    if df_1m is None or df_1m.empty:
        ts = int(time.time() * 1000)
        return {
            "id": _make_id(symbol, ts),
            "symbol": symbol,
            "signal": "NEUTRO",
            "score": 0,
            "probability": 0.0,
            "regime": "CHOP",
            "rsi": None,
            "vol_z": None,
            "upper_wick": None,
            "ret_15": None,
            "cooldown_min": None,
            "entry_price": None,
            "stop_loss": None,
            "target_price": None,
            "reasons": ["Sem candles"],
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "strong": False,
        }

    df_1m = add_indicators(df_1m)
    df_5m = add_indicators(data.get("5m")) if data.get("5m") is not None else None
    df_15m = add_indicators(data.get("15m")) if data.get("15m") is not None else None
    df_1m["fwd_ret_5"] = df_1m["close"].pct_change(5).shift(-5)

    df_1m = df_1m.dropna(subset=["close"])
    last = df_1m.iloc[-1].to_dict()

    open_time = last.get("open_time")
    ts_ms = int(open_time.value / 10**6) if hasattr(open_time, "value") else int(time.time() * 1000)

    regime_info = classify_regime(df_15m) if df_15m is not None else {"regime": "CHOP"}
    regime = regime_info.get("regime", "CHOP")

    strat = combine_strategies(last, regime)
    rule_long = int(strat.get("rule_long", 0))
    rule_short = int(strat.get("rule_short", 0))
    strategy = str(strat.get("strategy", "NONE"))

    model = get_model(symbol)
    model.update(df_1m.tail(5000))
    prob_up = model.predict(last)
    if prob_up is None:
        prob_up = 0.5
    prob_down = 1.0 - prob_up

    signal = "NEUTRO"
    strong = False
    if rule_long == 1 and prob_up >= 0.55:
        signal = "LONG_FORTE"
        strong = True
    elif rule_long == 1 or prob_up >= 0.60:
        signal = "LONG_FRACO"
    if rule_short == 1 and prob_down >= 0.55:
        signal = "SHORT_FORTE"
        strong = True
    elif rule_short == 1 or prob_down >= 0.60:
        signal = "SHORT_FRACO"

    reasons = []
    if rule_long == 1:
        reasons.append("Regra LONG ativa")
    if rule_short == 1:
        reasons.append("Regra SHORT ativa")

    # Confirmação 5m para sinais fortes
    if strong and df_5m is not None and not df_5m.empty:
        last_5m = df_5m.iloc[-1].to_dict()
        conf = combine_strategies(last_5m, regime)
        if signal.startswith("LONG") and conf.get("rule_long", 0) != 1:
            signal = "LONG_FRACO"
            strong = False
            reasons.append("Sem confirmação 5m")
        if signal.startswith("SHORT") and conf.get("rule_short", 0) != 1:
            signal = "SHORT_FRACO"
            strong = False
            reasons.append("Sem confirmação 5m")

    # Cooldown
    now = time.time()
    cooldown_sec = 25 * 60
    last_signal = _LAST_SIGNAL_AT.get(symbol, 0)
    cooldown_min = max(0, int((cooldown_sec - (now - last_signal)) / 60))
    if last_signal and (now - last_signal) < cooldown_sec and signal != "NEUTRO":
        reasons.append("Cooldown ativo")
        signal = "NEUTRO"
        strong = False

    if signal != "NEUTRO":
        _LAST_SIGNAL_AT[symbol] = now

    entry = safe_float(last.get("close"))
    atr = safe_float(last.get("atr14"))
    if entry is None:
        stop = None
        target = None
        rr = None
    else:
        atr_val = atr if atr is not None else entry * 0.003
        if signal.startswith("LONG"):
            stop = entry - (atr_val * 1.2)
            target = entry + (entry - stop) * 2.0
            rr = (target - entry) / max(entry - stop, 1e-9)
        elif signal.startswith("SHORT"):
            stop = entry + (atr_val * 1.2)
            target = entry - (stop - entry) * 2.0
            rr = (entry - target) / max(stop - entry, 1e-9)
        else:
            stop = entry - (atr_val * 1.0)
            target = entry + (atr_val * 1.5)
            rr = 1.5

    quality_1m = get_quality(symbol, "1m")
    penalties = 0
    if quality_1m.get("gaps", 0) > 0:
        penalties += 5
        reasons.append("Gaps de dados")
    if quality_1m.get("dups", 0) > 0:
        penalties += 5
        reasons.append("Duplicatas detectadas")
    atr_ratio = safe_float(last.get("atr_ratio"))
    if atr_ratio is not None and atr_ratio > 0.02:
        penalties += 10
        reasons.append("ATR% extremo")
    if regime == "BULL" and signal.startswith("SHORT"):
        penalties += 10
        reasons.append("Regime contra (BULL)")
    if regime == "BEAR" and signal.startswith("LONG"):
        penalties += 10
        reasons.append("Regime contra (BEAR)")

    base_score = max(prob_up, prob_down) * 100
    score = max(0, min(100, int(round(base_score - penalties))))

    fwd_ret = safe_float(last.get("fwd_ret_5"))
    update_metrics(symbol, regime, signal, fwd_ret)

    mapped_signal, strong = _map_signal_name(signal)

    return {
        "id": _make_id(symbol, ts_ms),
        "symbol": symbol,
        "signal": mapped_signal,
        "score": score,
        "probability": prob_down if mapped_signal.startswith("SHORT") else prob_up,
        "regime": regime,
        "rsi": safe_float(last.get("rsi14")),
        "vol_z": safe_float(last.get("vol_z")),
        "upper_wick": safe_float(last.get("upper_wick")),
        "ret_15": safe_float(last.get("ret_15")),
        "cooldown_min": cooldown_min,
        "entry_price": entry,
        "stop_loss": stop,
        "target_price": target,
        "reasons": reasons,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts_ms / 1000)),
        "strong": strong,
        "meta": {
            "strategy": strategy,
            "prob_up": round(prob_up, 4),
            "prob_down": round(prob_down, 4),
            "risk": {
                "entry": entry,
                "stop": stop,
                "take": target,
                "rr": None if rr is None else round(rr, 2),
            },
        },
    }


def _get_cached_signals(interval: str, limit: int) -> List[Dict]:
    global _CACHED_SIGNALS, _LAST_UPDATE, _LAST_FETCH
    now = time.time()
    if _CACHED_SIGNALS and (now - _LAST_FETCH) < 10:
        return _CACHED_SIGNALS

    results = []
    for symbol in _get_symbols():
        results.append(_build_signal(symbol, interval, limit))

    _CACHED_SIGNALS = sorted(results, key=lambda s: s.get("score", 0), reverse=True)
    _LAST_UPDATE = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _LAST_FETCH = now
    return _CACHED_SIGNALS


@router.get("/signals")
def list_signals(
    minScore: int = Query(default=0),
    onlyStrong: bool = Query(default=False),
    interval: str = Query(default="1m"),
    limit: int = Query(default=500),
):
    signals = _get_cached_signals(interval, limit)
    filtered = [
        s for s in signals
        if s.get("score", 0) >= minScore and (not onlyStrong or s.get("strong"))
    ]
    response = []
    for entry in filtered:
        item = dict(entry)
        item.pop("strong", None)
        response.append(item)
    return response


@router.get("/signals/latest")
def signals_latest(
    interval: str = Query(default="1m"),
    limit: int = Query(default=500),
):
    _get_cached_signals(interval, limit)
    return {"lastUpdate": _LAST_UPDATE}


@router.get("/signals/{signal_id}")
def get_signal(
    signal_id: int,
    interval: str = Query(default="1m"),
    limit: int = Query(default=500),
):
    signals = _get_cached_signals(interval, limit)
    for entry in signals:
        if entry.get("id") == signal_id:
            item = dict(entry)
            item.pop("strong", None)
            return item
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signal not found")


@router.get("/alerts")
def list_alerts(
    interval: str = Query(default="1m"),
    limit: int = Query(default=500),
):
    signals = _get_cached_signals(interval, limit)
    alerts = []
    for entry in signals:
        if entry.get("strong"):
            alerts.append(
                {
                    "id": entry.get("id"),
                    "message": f"Sinal {entry.get('signal')} em {entry.get('symbol')}",
                    "type": "NEW_SIGNAL",
                    "timestamp": entry.get("timestamp"),
                }
            )
        if len(alerts) >= 20:
            break
    return alerts


@router.get("/metrics")
def metrics():
    return {"symbols": snapshot(), "regimes": snapshot_by_regime()}


@router.post("/audit/explain")
def audit_explain(payload: dict):
    return {"explanation": explain_signal(payload)}


@router.post("/audit/check")
def audit_check(payload: dict):
    return {"audit": audit_signal(payload)}
