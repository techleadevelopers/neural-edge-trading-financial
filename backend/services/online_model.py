from __future__ import annotations

from collections import deque
from typing import Deque, Dict, Tuple

import numpy as np
import pandas as pd
from sklearn.linear_model import SGDClassifier
from sklearn.preprocessing import StandardScaler

FEATURES = [
    "rsi14",
    "ret_1",
    "ret_5",
    "ret_15",
    "vol_z",
    "upper_wick",
    "lower_wick",
    "atr_ratio",
    "ema200",
    "ema200_slope",
    "adx14",
]


class OnlineModel:
    def __init__(self, window: int = 5000) -> None:
        self.window = window
        self.scaler = StandardScaler()
        self.model = SGDClassifier(loss="log_loss", max_iter=1, learning_rate="optimal")
        self._fit = False
        self._buffer: Deque[Tuple[np.ndarray, int]] = deque(maxlen=window)

    def _prepare(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        df = df.dropna(subset=FEATURES + ["fwd_ret_5"])
        if df.empty:
            return np.empty((0, len(FEATURES))), np.array([])
        X = df[FEATURES].astype(float).values
        y = (df["fwd_ret_5"] > 0).astype(int).values
        return X, y

    def update(self, df: pd.DataFrame) -> None:
        X, y = self._prepare(df)
        if X.size == 0:
            return
        for i in range(len(X)):
            self._buffer.append((X[i], int(y[i])))
        Xb = np.array([row for row, _ in self._buffer])
        yb = np.array([label for _, label in self._buffer])
        self.scaler.partial_fit(Xb)
        Xs = self.scaler.transform(Xb)
        if not self._fit:
            self.model.partial_fit(Xs, yb, classes=np.array([0, 1]))
            self._fit = True
        else:
            self.model.partial_fit(Xs, yb)

    def predict(self, row: dict) -> float | None:
        if not self._fit:
            return None
        try:
            x = np.array([float(row.get(f)) for f in FEATURES], dtype=float).reshape(1, -1)
        except (TypeError, ValueError):
            return None
        if np.isnan(x).any():
            return None
        xs = self.scaler.transform(x)
        prob_up = float(self.model.predict_proba(xs)[0][1])
        return prob_up


_MODELS: Dict[str, OnlineModel] = {}


def get_model(symbol: str) -> OnlineModel:
    key = symbol.upper()
    if key not in _MODELS:
        _MODELS[key] = OnlineModel()
    return _MODELS[key]
