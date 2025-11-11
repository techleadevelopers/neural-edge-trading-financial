from fastapi import APIRouter
from services.collector import get_klines
from services.features import add_indicators
from services.models import train_baseline, predict_proba_down, predict_proba_both, get_threshold, get_model_info, get_weights
from services.rules import fuse_model_and_rules, fuse_with_regime
from services.utils import DEFAULT_SYMBOL, DEFAULT_INTERVAL, CANDLES_LIMIT

router = APIRouter()


@router.post("/train")
def train(
    symbol: str = DEFAULT_SYMBOL,
    interval: str = DEFAULT_INTERVAL,
    limit: int = CANDLES_LIMIT,
):
    df = get_klines(symbol, interval, limit)
    if df is None or df.empty:
        return {"ok": False, "error": f"Sem candles para {symbol} {interval}."}
    df = add_indicators(df)
    df2 = df.dropna()
    if len(df2) < 60:
        return {"ok": False, "error": "Poucos dados apos indicadores (min ~60)."}
    try:
        path = train_baseline(df2)
        # carrega meta compacta do payload recem treinado
        import joblib
        payload = joblib.load(path)
        meta = payload.get("meta", {})
        return {
            "ok": True,
            "model_path": path,
            "meta": meta,
            "features": payload.get("features", []),
            "threshold": payload.get("threshold"),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/predict")
def predict(
    symbol: str = DEFAULT_SYMBOL,
    interval: str = DEFAULT_INTERVAL,
    limit: int = CANDLES_LIMIT,
):
    df = get_klines(symbol, interval, limit)
    if df is None or df.empty:
        return {
            "symbol": symbol,
            "interval": interval,
            "error": f"Sem candles para {symbol} {interval}.",
            "fused": {"signal": "NEUTRAL", "confidence": 0.0},
        }
    df = add_indicators(df)
    df2 = df.dropna()
    if df2.empty:
        return {
            "symbol": symbol,
            "interval": interval,
            "error": "Dados insuficientes apos indicadores (precisa de ~30+ candles).",
            "last_raw": df.tail(3).to_dict(orient="records"),
            "fused": {"signal": "NEUTRAL", "confidence": 0.0},
        }
    last = df2.iloc[-1].to_dict()

    # regra de euforia
    from services.features import rule_short_sniper_row

    rule_flag = rule_short_sniper_row(last)

    # prob de queda + regime (macro)
    from services.regime import compute_regime_snapshot

    snap = compute_regime_snapshot()

    try:
        probs = predict_proba_both(last)
        wm, wn = get_weights()
        p_model = probs.get("model") or 0.0
        p_neural = probs.get("neural") if probs.get("neural") is not None else p_model
        prob_down = wm * p_model + wn * p_neural
        thr = get_threshold(0.55)
        fused = fuse_model_and_rules(prob_down, rule_flag, thr)
        fused2 = fuse_with_regime(fused, snap["regime"], symbol)
        return {
            "symbol": symbol,
            "interval": interval,
            "prob_down": prob_down,
            "prob_model": p_model,
            "prob_neural": p_neural,
            "weights": {"model": wm, "neural": wn},
            "threshold": thr,
            "rule_short": rule_flag,
            "fused": fused,
            "fused_final": fused2,
            "regime": snap,
            "last": last,
        }
    except FileNotFoundError:
        thr = 0.55
        fused = {"signal": "NEUTRAL", "confidence": 0.0}
        fused2 = fuse_with_regime(fused, snap["regime"], symbol)
        return {
            "symbol": symbol,
            "interval": interval,
            "prob_down": None,
            "threshold": thr,
            "rule_short": rule_flag,
            "fused": fused,
            "fused_final": fused2,
            "regime": snap,
            "last": last,
            "error": "Modelo nao encontrado. Treine primeiro em /model/train.",
        }


@router.get("/meta")
def meta():
    try:
        info = get_model_info()
        return {"ok": True, **info}
    except FileNotFoundError:
        return {"ok": False, "error": "Modelo nao encontrado. Treine em /model/train."}
