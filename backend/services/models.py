import os
import numpy as np
import pandas as pd
import joblib
from sklearn.linear_model import LogisticRegression

MODEL_PATH = "data/models/baseline_logreg.pkl"


def build_training_frame(df: pd.DataFrame):
    df = df.dropna().copy()
    # target: prob de queda nas próximas 5 barras
    df["fwd_ret_5"] = df["close"].pct_change(5).shift(-5)
    df["y_down"] = (df["fwd_ret_5"] < 0).astype(int)
    feats = ["rsi14", "ret_1", "ret_5", "ret_15", "vol_z", "upper_wick"]
    X = df[feats].values
    y = df["y_down"].values
    return X, y, feats


def train_baseline(df: pd.DataFrame) -> str:
    X, y, feats = build_training_frame(df)
    if len(np.unique(y)) < 2:
        raise ValueError("Target sem variação para treino.")
    clf = LogisticRegression(max_iter=200)
    clf.fit(X, y)
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump({"model": clf, "features": feats}, MODEL_PATH)
    return MODEL_PATH


def predict_proba_down(df_row: dict) -> float:
    payload = joblib.load(MODEL_PATH)
    clf, feats = payload["model"], payload["features"]
    x = np.array([[df_row.get(f, 0.0) for f in feats]])
    p = float(clf.predict_proba(x)[0][1])
    return p

