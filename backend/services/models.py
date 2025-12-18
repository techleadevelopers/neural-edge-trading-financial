import os
import threading
from datetime import datetime
import numpy as np
import pandas as pd
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import TimeSeriesSplit
from sklearn.calibration import CalibratedClassifierCV
from sklearn import metrics

MODEL_PATH = "data/models/baseline_logreg.pkl"
FEE_SLIPPAGE = float(os.getenv("FEE_SLIPPAGE", "0"))

_MODEL_CACHE = {"payload": None, "mtime": 0.0}
_MODEL_LOCK = threading.Lock()


def _load_payload():
    with _MODEL_LOCK:
        try:
            mtime = os.path.getmtime(MODEL_PATH)
        except FileNotFoundError:
            raise
        cached = _MODEL_CACHE.get("payload")
        cached_mtime = _MODEL_CACHE.get("mtime")
        if cached is not None and cached_mtime == mtime:
            return cached
        payload = joblib.load(MODEL_PATH)
        _MODEL_CACHE["payload"] = payload
        _MODEL_CACHE["mtime"] = mtime
        return payload


def build_training_frame(df: pd.DataFrame):
    df = df.dropna().copy()
    # target: prob de queda nas proximas 5 barras
    df["fwd_ret_5"] = df["close"].pct_change(5).shift(-5)
    if FEE_SLIPPAGE > 0:
        df["y_down"] = (df["fwd_ret_5"] < -FEE_SLIPPAGE).astype(int)
    else:
        df["y_down"] = (df["fwd_ret_5"] < 0).astype(int)
    feats = [
        "rsi14",
        "rsi_slope3",
        "rsi_z",
        "ret_1",
        "ret_5",
        "ret_15",
        "vol_z",
        "vol_ratio",
        "upper_wick",
        "body_norm",
        "wick_ratio",
        "ema_dist20",
        "ema_dist50",
        "bb_bw",
        "bb_pos",
        "atr14",
        "atr_ratio",
    ]
    feats = [f for f in feats if f in df.columns]
    X = df[feats].values
    y = df["y_down"].values
    return X, y, feats


def _tscv_best_c(X, y, Cs=(0.1, 1.0, 3.0), n_splits=5):
    tscv = TimeSeriesSplit(n_splits=n_splits)
    best_c, best_auc = None, -1
    for C in Cs:
        aucs = []
        for train_idx, val_idx in tscv.split(X):
            Xtr, Xval = X[train_idx], X[val_idx]
            ytr, yval = y[train_idx], y[val_idx]
            if len(np.unique(ytr)) < 2 or len(np.unique(yval)) < 2:
                continue
            pipe = Pipeline(
                [
                    ("scaler", StandardScaler()),
                    ("lr", LogisticRegression(max_iter=400, class_weight="balanced", C=C)),
                ]
            )
            pipe.fit(Xtr, ytr)
            p = pipe.predict_proba(Xval)[:, 1]
            aucs.append(metrics.roc_auc_score(yval, p))
        if len(aucs) and np.nanmean(aucs) > best_auc:
            best_auc = float(np.nanmean(aucs))
            best_c = C
    return best_c or 1.0, best_auc if best_auc is not None else None


def _best_threshold(y_true, proba, grid=None):
    if grid is None:
        grid = [i / 100 for i in range(35, 80)]  # 0.35..0.79
    best_thr, best_f1 = 0.5, -1
    for thr in grid:
        yhat = (proba >= thr).astype(int)
        f1 = metrics.f1_score(y_true, yhat, zero_division=0)
        if f1 > best_f1:
            best_f1, best_thr = f1, thr
    return float(best_thr), float(best_f1)


def train_baseline(df: pd.DataFrame) -> str:
    X, y, feats = build_training_frame(df)
    if len(np.unique(y)) < 2:
        raise ValueError("Target sem variacao para treino.")

    # escolhe C via TSCV
    best_c, cv_auc = _tscv_best_c(X, y)

    # holdout final para calibracao
    split = int(len(X) * 0.8)
    Xtr, ytr = X[:split], y[:split]
    Xval, yval = X[split:], y[split:]

    base = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("lr", LogisticRegression(max_iter=400, class_weight="balanced", C=best_c)),
        ]
    )
    base.fit(Xtr, ytr)

    calibrator = None
    if len(np.unique(yval)) >= 2:
        calibrator = CalibratedClassifierCV(base, cv="prefit", method="sigmoid")
        calibrator.fit(Xval, yval)

    # MLP refiner (pequeno), calibrado no holdout
    mlp_base = None
    mlp_cal = None
    try:
        mlp_base = Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "mlp",
                    MLPClassifier(
                        hidden_layer_sizes=(16, 16),
                        activation="relu",
                        max_iter=500,
                        random_state=42,
                    ),
                ),
            ]
        )
        mlp_base.fit(Xtr, ytr)
        if len(np.unique(yval)) >= 2:
            mlp_cal = CalibratedClassifierCV(mlp_base, cv="prefit", method="sigmoid")
            mlp_cal.fit(Xval, yval)
    except Exception:
        mlp_base, mlp_cal = None, None

    proba_val = (
        calibrator.predict_proba(Xval)[:, 1]
        if calibrator is not None
        else base.predict_proba(Xval)[:, 1]
    )
    thr_best, f1_best = _best_threshold(yval, proba_val)
    try:
        auc_val = metrics.roc_auc_score(yval, proba_val)
        pr_val = metrics.average_precision_score(yval, proba_val)
    except Exception:
        auc_val, pr_val = None, None

    payload = {
        "model": base,
        "calibrator": calibrator,
        "model_neural": mlp_base,
        "calibrator_neural": mlp_cal,
        "features": feats,
        "threshold": thr_best,
        "meta": {
            "C": best_c,
            "cv_auc": cv_auc,
            "val_auc": auc_val,
            "val_pr_auc": pr_val,
            "f1_short": f1_best,
            "timestamp": datetime.utcnow().isoformat(),
            "model_type": "hybrid" if mlp_base is not None else "logreg",
        },
        "weights": {"model": 0.7, "neural": 0.3},
    }
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(payload, MODEL_PATH)
    with _MODEL_LOCK:
        _MODEL_CACHE["payload"] = payload
        _MODEL_CACHE["mtime"] = os.path.getmtime(MODEL_PATH)
    return MODEL_PATH


def _predict(payload, x: np.ndarray) -> tuple[float, float | None]:
    if payload.get("calibrator") is not None:
        p_model = float(payload["calibrator"].predict_proba(x)[0][1])
    else:
        p_model = float(payload["model"].predict_proba(x)[0][1])

    p_neural = None
    if payload.get("calibrator_neural") is not None:
        try:
            p_neural = float(payload["calibrator_neural"].predict_proba(x)[0][1])
        except Exception:
            p_neural = None
    elif payload.get("model_neural") is not None:
        try:
            p_neural = float(payload["model_neural"].predict_proba(x)[0][1])
        except Exception:
            p_neural = None
    return p_model, p_neural


def predict_proba_down(df_row: dict) -> float:
    payload = _load_payload()
    feats = payload["features"]
    x = np.array([[df_row.get(f, 0.0) for f in feats]])
    p_model, _ = _predict(payload, x)
    return p_model


def predict_proba_both(df_row: dict) -> dict:
    payload = _load_payload()
    feats = payload["features"]
    x = np.array([[df_row.get(f, 0.0) for f in feats]])
    p_model, p_neural = _predict(payload, x)
    return {"model": p_model, "neural": p_neural}


def get_weights(default_model: float = 0.7, default_neural: float = 0.3) -> tuple[float, float]:
    try:
        payload = _load_payload()
        w = payload.get("weights") or {}
        wm = float(w.get("model", default_model))
        wn = float(w.get("neural", default_neural))
        s = wm + wn
        if s <= 0:
            return default_model, default_neural
        return wm / s, wn / s
    except Exception:
        return default_model, default_neural


def get_model_info():
    payload = _load_payload()
    return {
        "threshold": payload.get("threshold"),
        "features": payload.get("features", []),
        "meta": payload.get("meta", {}),
        "has_calibrator": payload.get("calibrator") is not None,
    }


def get_threshold(default: float = 0.55) -> float:
    try:
        info = get_model_info()
        thr = info.get("threshold")
        return float(thr) if thr is not None else float(default)
    except Exception:
        return float(default)
