"""Constants and defaults for structured support model baseline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROFILE_LABELS = (
    "stable_pattern",
    "elevated_stress_pattern",
    "depleted_pattern",
    "unstable_pattern",
)
PROFILE_TO_ID = {label: idx for idx, label in enumerate(PROFILE_LABELS)}
ID_TO_PROFILE = {idx: label for label, idx in PROFILE_TO_ID.items()}

DEPLETED_LIKE_PROFILES = {"depleted_pattern", "unstable_pattern"}

WINDOW_DAYS = (3, 7, 14)

RAW_REQUIRED_COLUMNS = (
    "event_timestamp",
    "user_key",
    "stress_level",
    "energy_level",
    "sleep_hours",
)

DEFAULT_SUPPORT_NEED_LABEL_COL = "support_need_score_label"
DEFAULT_SUPPORT_PROFILE_LABEL_COL = "support_profile_label"

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "artifacts" / "structured_support_model" / "latest"


@dataclass(frozen=True)
class TrainingDefaults:
    train_ratio: float = 0.70
    val_ratio: float = 0.15
    random_state: int = 42
    calibration_method: str = "sigmoid"
    confidence_threshold: float = 0.55
    fallback_profile: str = "stable_pattern"
    cold_start_min_events: int = 5
    personal_baseline_min_events: int = 10
    high_support_score_threshold: float = 0.70


TRAINING_DEFAULTS = TrainingDefaults()
