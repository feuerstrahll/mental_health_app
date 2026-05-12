from fastapi import APIRouter, Depends

from app.api.deps import get_decision_pipeline
from app.schemas.decision import SupportDecisionResponse
from app.schemas.wellbeing import WellbeingSignalsRequest
from app.services.orchestration.decision_pipeline import DecisionPipeline

router = APIRouter(prefix="/wellbeing-signals")


@router.post("", response_model=SupportDecisionResponse)
async def evaluate_wellbeing(
    payload: WellbeingSignalsRequest,
    pipeline: DecisionPipeline = Depends(get_decision_pipeline),
) -> SupportDecisionResponse:
    return await pipeline.run(payload)
