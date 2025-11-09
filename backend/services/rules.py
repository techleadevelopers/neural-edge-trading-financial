def fuse_model_and_rules(prob_down: float, short_rule: int) -> dict:
    """
    Combinação conservadora:
    - Se regra de euforia acende (1), e prob_down >= 0.55 => SHORT_STRONG
    - Se qualquer um acende isolado => SHORT_WEAK
    - Senão => NEUTRAL
    """
    if short_rule == 1 and prob_down >= 0.55:
        return {"signal": "SHORT_STRONG", "confidence": round(max(prob_down, 0.7), 3)}
    if short_rule == 1 or prob_down >= 0.60:
        return {"signal": "SHORT_WEAK", "confidence": round(max(prob_down, 0.55), 3)}
    return {"signal": "NEUTRAL", "confidence": round(prob_down, 3)}


def fuse_with_regime(fused_signal: dict, regime: str, symbol: str):
    s = fused_signal["signal"]
    conf = float(fused_signal.get("confidence", 0.0))
    # Bias dinâmico
    if regime == "ALT_ROTATION" and symbol.endswith("USDT") and symbol not in ("BTCUSDT", "ETHUSDT"):
        if s.startswith("SHORT"):
            conf += 0.05  # shorts em alts tendem a render mais em rotações
    if regime in ("BTC_TREND", "RISK_OFF") and symbol != "BTCUSDT":
        if s.startswith("SHORT"):
            conf -= 0.05  # mais conservador fora de altseason
    conf = max(0.0, min(1.0, conf))
    return {"signal": s, "confidence": round(conf, 3), "regime": regime}
