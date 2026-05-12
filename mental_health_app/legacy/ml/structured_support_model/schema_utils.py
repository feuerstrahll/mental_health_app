"""Feature schema utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .constants import PROFILE_LABELS


def build_feature_schema(feature_columns: Iterable[str]) -> dict:
    features = []
    for name in feature_columns:
        features.append(
            {
                "name": name,
                "dtype": "float",
                "required": True,
                "nullable": False,
                "description": _feature_description(name),
            }
        )

    return {
        "schema_version": "1.0.0",
        "task": "structured_support_baseline",
        "output_targets": {
            "support_need_score": "float_0_1",
            "support_profile": list(PROFILE_LABELS),
        },
        "features": features,
        "notes": [
            "Baseline uses product signals and lightweight note-derived indicators (no PII).",
            "Windows are limited to 3/7/14 days for production availability.",
            "Cold-start handling is explicit via is_cold_start and reliability features.",
        ],
    }


def save_feature_schema(path: Path, feature_columns: Iterable[str]) -> None:
    schema = build_feature_schema(feature_columns)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")


def _feature_description(name: str) -> str:
    if name.endswith("_3d") or name.endswith("_7d") or name.endswith("_14d"):
        return "Rolling aggregate over recent history window"
    if "personal_baseline" in name:
        return "Deviation from user-specific baseline with reliability weighting"
    if name == "is_cold_start":
        return "1 if user history is below safe threshold"
    if "availability" in name:
        return "Share of available values in the rolling window"
    if "note_" in name:
        return "Lightweight diary-note derived indicator"
    if "emotion_valence" in name:
        return "Mapped emotion marker valence"
    if "inactivity_streak" in name:
        return "Consecutive days with high sedentary time"
    if name in {"history_events", "history_days"}:
        return "User history depth at decision time"
    if "delta" in name:
        return "Short-vs-long window shift indicator"
    return "Aggregated product signal"
