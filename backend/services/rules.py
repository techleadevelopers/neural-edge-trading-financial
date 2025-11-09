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

