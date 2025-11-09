from fastapi import APIRouter
from services.collector import get_klines
from services.features import add_indicators
from services.models import train_baseline, predict_proba_down
from services.rules import fuse_model_and_rules
from services.utils import DEFAULT_SYMBOL, DEFAULT_INTERVAL, CANDLES_LIMIT

router = APIRouter()


@router.post("/train")
def train(
    symbol: str = DEFAULT_SYMBOL,
    interval: str = DEFAULT_INTERVAL,
    limit: int = CANDLES_LIMIT,
):
    df = get_klines(symbol, interval, limit)
    df = add_indicators(df)
    path = train_baseline(df)
    return {"ok": True, "model_path": path}


@router.post("/predict")
def predict(
    symbol: str = DEFAULT_SYMBOL,
    interval: str = DEFAULT_INTERVAL,
    limit: int = CANDLES_LIMIT,
):
    df = get_klines(symbol, interval, limit)
    df = add_indicators(df)
    last = df.dropna().iloc[-1].to_dict()

    # regra de euforia (teu short)
    from services.features import rule_short_sniper_row

    rule_flag = rule_short_sniper_row(last)

    # prob de queda pelo modelo
    try:
        prob_down = predict_proba_down(last)
        fused = fuse_model_and_rules(prob_down, rule_flag)
        return {
            "symbol": symbol,
            "interval": interval,
            "prob_down": prob_down,
            "rule_short": rule_flag,
            "fused": fused,
            "last": last,
        }
    except FileNotFoundError:
        return {
            "symbol": symbol,
            "interval": interval,
            "prob_down": None,
            "rule_short": rule_flag,
            "fused": {"signal": "NEUTRAL", "confidence": 0.0},
            "last": last,
            "error": "Modelo não encontrado. Treine primeiro em /model/train.",
        }

