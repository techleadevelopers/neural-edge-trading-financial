from fastapi import APIRouter
from services.collector import get_klines
from services.features import add_indicators
from services.models import train_baseline, predict_proba_down
from services.rules import fuse_model_and_rules
from services.regime import compute_regime_snapshot
from services.rules import fuse_with_regime
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
        return {"ok": True, "model_path": path}
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

    # regra de euforia (teu short)
    from services.features import rule_short_sniper_row

    rule_flag = rule_short_sniper_row(last)

    # prob de queda pelo modelo
    # snapshot de regime (macro)
    snap = compute_regime_snapshot()

    try:
        prob_down = predict_proba_down(last)
        fused = fuse_model_and_rules(prob_down, rule_flag)
        fused2 = fuse_with_regime(fused, snap["regime"], symbol)
        return {
            "symbol": symbol,
            "interval": interval,
            "prob_down": prob_down,
            "rule_short": rule_flag,
            "fused": fused,
            "fused_final": fused2,
            "regime": snap,
            "last": last,
        }
    except FileNotFoundError:
        fused = {"signal": "NEUTRAL", "confidence": 0.0}
        fused2 = fuse_with_regime(fused, snap["regime"], symbol)
        return {
            "symbol": symbol,
            "interval": interval,
            "prob_down": None,
            "rule_short": rule_flag,
            "fused": fused,
            "fused_final": fused2,
            "regime": snap,
            "last": last,
            "error": "Modelo não encontrado. Treine primeiro em /model/train.",
        }
