from enum import Enum
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class SafetyAssessment(BaseModel):
    risk_level: RiskLevel
    risk_score: float = Field(ge=0)
    flags: list[str] = Field(default_factory=list)
    escalation_required: bool = False
