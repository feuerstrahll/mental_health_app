from app.schemas.wellbeing import WellbeingSignalsRequest


class RiskScoring:
    CRISIS_KEYWORDS = {"self-harm", "suicide", "hopeless", "end it"}

    def score(self, payload: WellbeingSignalsRequest, pattern_tags: list[str]) -> tuple[float, list[str]]:
        score = 0.0
        flags: list[str] = []

        emotion = payload.signals.emotion_marker.lower()
        diary = (payload.signals.diary_note or "").lower()

        if emotion in {"panic", "despair", "crisis"}:
            score += 0.6
            flags.append("critical_emotion_marker")

        if any(keyword in diary for keyword in self.CRISIS_KEYWORDS):
            score += 0.8
            flags.append("crisis_language_detected")

        if "sleep_debt" in pattern_tags:
            score += 0.1
        if "high_inactivity" in pattern_tags:
            score += 0.1
        if "low_social_connection" in pattern_tags:
            score += 0.1

        return min(score, 1.0), flags
