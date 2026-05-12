from app.domain.rules.escalation import escalation_for_risk
from app.schemas.safety import RiskLevel, SafetyAssessment


class SafetyChecker:
    def assess(self, risk_score: float, flags: list[str]) -> SafetyAssessment:
        if risk_score >= 0.9:
            risk_level = RiskLevel.urgent
        elif risk_score >= 0.6:
            risk_level = RiskLevel.high
        elif risk_score >= 0.3:
            risk_level = RiskLevel.medium
        else:
            risk_level = RiskLevel.low

        return SafetyAssessment(
            risk_level=risk_level,
            risk_score=risk_score,
            flags=flags,
            escalation_required=escalation_for_risk(risk_level),
        )
