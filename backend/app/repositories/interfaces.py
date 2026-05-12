from collections.abc import Sequence
from typing import Protocol

from app.schemas.wellbeing import WellbeingSignalsRequest


class WellbeingRepository(Protocol):
    async def save(self, payload: WellbeingSignalsRequest) -> None:
        ...

    async def get_recent_by_user(self, user_id: str, limit: int = 14) -> Sequence[WellbeingSignalsRequest]:
        ...
