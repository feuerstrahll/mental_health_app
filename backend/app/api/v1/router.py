from fastapi import APIRouter

from app.api.v1.endpoints import health, support_decision, wellbeing_signals

router = APIRouter()
router.include_router(health.router, tags=["health"])
router.include_router(wellbeing_signals.router, tags=["wellbeing"])
router.include_router(support_decision.router, tags=["decision"])
