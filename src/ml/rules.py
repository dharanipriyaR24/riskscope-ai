def rule_score(txn: dict) -> float:
    """
    Returns 0..100 rule-based risk.
    """
    score = 0

    amt = float(txn.get("amount", 0))
    cat = str(txn.get("merchant_category", ""))
    is_new = int(txn.get("is_new_device", 0))
    intl = int(txn.get("is_international", 0))
    vel = int(txn.get("velocity_1h", 0))
    hour = int(txn.get("hour", 12))

    if amt >= 1500:
        score += 30
    if cat in ["GIFT_CARDS", "CRYPTO_EXCHANGE", "WIRE_SERVICE"]:
        score += 25
    if vel >= 6:
        score += 20
    if is_new == 1:
        score += 10
    if intl == 1:
        score += 10
    if hour <= 4 or hour >= 23:
        score += 5

    return min(100.0, float(score))


def blended_score(ml_risk_pct: float, rule_risk_pct: float, w_ml=0.7, w_rule=0.3) -> float:
    return float(w_ml * ml_risk_pct + w_rule * rule_risk_pct)
