def fuse_model_and_rules(prob_down: float, short_rule: int, thr: float = 0.55) -> dict:
    """
    Fusão com limiar treinado (thr):
    - STRONG: regra ativa e prob_down >= thr + 0.05
    - WEAK: regra ativa OU prob_down >= thr
    - NEUTRAL: caso contrário
    """
    strong = short_rule == 1 and prob_down >= (thr + 0.05)
    weak = (short_rule == 1) or (prob_down >= thr)
    if strong:
        return {"signal": "SHORT_STRONG", "confidence": round(max(prob_down, thr + 0.05), 3)}
    if weak:
        return {"signal": "SHORT_WEAK", "confidence": round(max(prob_down, thr), 3)}
    return {"signal": "NEUTRAL", "confidence": round(prob_down, 3)}


def fuse_with_regime(fused_signal: dict, regime: str, symbol: str):
    s = fused_signal["signal"]
    conf = float(fused_signal.get("confidence", 0.0))
    # Bias dinamico por regime/ativo
    if regime == "ALT_ROTATION" and symbol.endswith("USDT") and symbol not in ("BTCUSDT", "ETHUSDT"):
        if s.startswith("SHORT"):
            conf += 0.05  # shorts em alts tendem a render mais em rotacoes
    if regime in ("BTC_TREND", "RISK_OFF") and symbol != "BTCUSDT":
        if s.startswith("SHORT"):
            conf -= 0.05  # mais conservador fora de altseason
    conf = max(0.0, min(1.0, conf))
    return {"signal": s, "confidence": round(conf, 3), "regime": regime}

