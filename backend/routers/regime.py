from fastapi import APIRouter
from services.regime import (
    compute_regime_snapshot,
    train_regime,
    predict_regime,
    get_regime_history,
    refresh_regime_mv,
)

router = APIRouter()


@router.get("/snapshot")
def snapshot(symbol_btc: str = "BTCUSDT"):
    return compute_regime_snapshot(symbol_btc)


@router.post("/train")
def train():
    path = train_regime()
    return {"ok": True, "model_path": path}


@router.get("/predict")
def predict():
    return predict_regime()


@router.get("/history")
def history(days: int = 30, use_mv: bool | None = None, refresh: bool = False):
    return get_regime_history(days=days, use_mv=use_mv, refresh=refresh)


@router.post("/refresh")
def refresh_mv():
    return refresh_regime_mv()
