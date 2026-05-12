from app.schemas.safety import RiskLevel


def escalation_for_risk(risk_level: RiskLevel) -> bool:
    return risk_level in {RiskLevel.high, RiskLevel.urgent}
