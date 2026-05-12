from fastapi import APIRouter, Depends

from app.api.deps import get_decision_pipeline
from app.schemas.decision import SupportDecisionRequest, SupportDecisionResponse
from app.services.orchestration.decision_pipeline import DecisionPipeline

router = APIRouter(prefix="/support-decision")


@router.post("", response_model=SupportDecisionResponse)
async def support_decision(
    payload: SupportDecisionRequest,
    pipeline: DecisionPipeline = Depends(get_decision_pipeline),
) -> SupportDecisionResponse:
    return await pipeline.run(
        payload.wellbeing,
        session_id=payload.session_id,
        latest_user_message=payload.latest_user_message,
        latest_diary_note=payload.latest_diary_note,
        dialogue_state=payload.dialogue_state.model_dump() if payload.dialogue_state else None,
        client_safety_precheck_result=payload.client_safety_precheck_result,
    )
