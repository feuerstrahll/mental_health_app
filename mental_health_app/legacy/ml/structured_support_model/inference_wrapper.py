"""Inference wrapper with confidence-threshold abstain/fallback policy."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from .constants import ID_TO_PROFILE, PROFILE_TO_ID


@dataclass(frozen=True)
class InferenceConfig:
    confidence_threshold: float
    fallback_profile: str
    cold_start_min_events: int


class StructuredSupportInference:
    def __init__(
        self,
        support_profile_model: Any,
        support_profile_calibrator: Any | None,
        support_need_model: Any,
        feature_names: list[str],
        config: InferenceConfig,
    ) -> None:
        self.support_profile_model = support_profile_model
        self.support_profile_calibrator = support_profile_calibrator
        self.support_need_model = support_need_model
        self.feature_names = feature_names
        self.config = config

    @classmethod
    def from_artifacts(cls, artifacts_dir: str | Path) -> "StructuredSupportInference":
        root = Path(artifacts_dir)

        model_profile = joblib.load(root / "support_profile_model.pkl")
        model_need = joblib.load(root / "support_need_model.pkl")
        calibrator_path = root / "support_profile_calibrator.pkl"
        calibrator = joblib.load(calibrator_path) if calibrator_path.exists() else None

        schema = json.loads((root / "feature_schema.json").read_text(encoding="utf-8"))
        feature_names = [item["name"] for item in schema["features"]]

        cfg_raw = json.loads((root / "inference_config.json").read_text(encoding="utf-8"))
        config = InferenceConfig(
            confidence_threshold=float(cfg_raw["confidence_threshold"]),
            fallback_profile=str(cfg_raw["fallback_profile"]),
            cold_start_min_events=int(cfg_raw["cold_start_min_events"]),
        )

        return cls(model_profile, calibrator, model_need, feature_names, config)

    def predict(self, aggregated_features: dict[str, float]) -> dict[str, Any]:
        vector = self._vectorize(aggregated_features)

        if self.support_profile_calibrator is not None:
            profile_probs = self.support_profile_calibrator.predict_proba(vector)[0]
        else:
            profile_probs = self.support_profile_model.predict_proba(vector)[0]

        pred_idx = int(np.argmax(profile_probs))
        confidence = float(np.max(profile_probs))
        predicted_profile = ID_TO_PROFILE[pred_idx]

        support_need_score = float(np.clip(self.support_need_model.predict(vector)[0], 0.0, 1.0))

        history_events = float(aggregated_features.get("history_events", 0.0))
        is_cold_start = history_events < float(self.config.cold_start_min_events)

        low_confidence = confidence < self.config.confidence_threshold
        abstain = bool(is_cold_start or low_confidence)

        fallback_reason = None
        if abstain:
            predicted_profile = self.config.fallback_profile
            fallback_reason = "cold_start" if is_cold_start else "low_confidence"

        return {
            "support_profile": predicted_profile,
            "support_need_score": support_need_score,
            "confidence": confidence,
            "abstain": abstain,
            "fallback_reason": fallback_reason,
            "safe_response_required": abstain,
            "response_mode": "template_only" if not abstain else "safety_template_only",
        }

    def _vectorize(self, aggregated_features: dict[str, float]) -> np.ndarray:
        missing = [name for name in self.feature_names if name not in aggregated_features]
        if missing:
            raise ValueError(f"Missing required features for inference: {missing[:10]}")

        row = np.array([float(aggregated_features[name]) for name in self.feature_names], dtype=np.float32)
        return row.reshape(1, -1)
