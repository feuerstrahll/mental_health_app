from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EmotionMarker:
    value: str

    ALLOWED_VALUES = {
        "очень плохо",
        "плохо",
        "как обычно, нейтрально",
        "хорошее настроение",
        "счастлив",
        "раздражен",
    }

    NEGATIVE_VALUES = {
        "очень плохо",
        "плохо",
        "раздражен",
    }

    POSITIVE_VALUES = {
        "хорошее настроение",
        "счастлив",
    }

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()

        if normalized not in self.ALLOWED_VALUES:
            raise ValueError(f"Unsupported emotion marker: {self.value}")

        object.__setattr__(self, "value", normalized)

    def is_negative(self) -> bool:
        return self.value in self.NEGATIVE_VALUES

    def is_positive(self) -> bool:
        return self.value in self.POSITIVE_VALUES

    def is_neutral(self) -> bool:
        return self.value == "как обычно, нейтрально"