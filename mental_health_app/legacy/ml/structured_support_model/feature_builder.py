"""Feature engineering for structured support baseline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Tuple

import numpy as np
import pandas as pd

from .constants import RAW_REQUIRED_COLUMNS, WINDOW_DAYS


OPTIONAL_NUMERIC_SIGNALS: tuple[tuple[str, str, float, float], ...] = (
    ("sleep_regularity_score", "sleep_regularity", 0.0, 10.0),
    ("sleep_quality_score", "sleep_quality", 0.0, 10.0),
    ("physical_activity_minutes", "activity_minutes", 0.0, 1440.0),
    ("sedentary_minutes", "sedentary_minutes", 0.0, 1440.0),
    ("outdoor_minutes", "outdoor_minutes", 0.0, 1440.0),
    ("social_connectedness_score", "social_connectedness", 0.0, 10.0),
    ("routine_regularity_score", "routine_regularity", 0.0, 10.0),
)

CORE_NUMERIC_SIGNALS: tuple[tuple[str, str, float, float], ...] = (
    ("stress_level", "stress", 0.0, 10.0),
    ("energy_level", "energy", 0.0, 10.0),
    ("sleep_hours", "sleep", 0.0, 24.0),
)

EMOTION_VALENCE_MAP = {
    "happy": 1.0,
    "calm": 0.65,
    "neutral": 0.1,
    "okay": 0.2,
    "sad": -0.8,
    "anxious": -0.9,
    "angry": -0.75,
    "overwhelmed": -0.95,
    "stressed": -0.7,
    "tired": -0.45,
}

NOTE_NEGATIVE_KEYWORDS = (
    "overwhelm",
    "panic",
    "hopeless",
    "worthless",
    "exhaust",
    "burnout",
    "stuck",
    "alone",
    "anxious",
    "sad",
)


@dataclass(frozen=True)
class FeatureBuilderConfig:
    windows: Tuple[int, ...] = WINDOW_DAYS
    cold_start_min_events: int = 5
    personal_baseline_min_events: int = 10


class AggregatedFeatureBuilder:
    """Builds explainable aggregated features from runtime-available signals."""

    def __init__(self, config: FeatureBuilderConfig | None = None) -> None:
        self.config = config or FeatureBuilderConfig()

    def transform(self, raw_df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
        df = self._prepare(raw_df)

        transformed_parts: List[pd.DataFrame] = []
        for _, group in df.groupby("user_key", sort=False):
            transformed_parts.append(self._transform_user_group(group))

        feature_df = pd.concat(transformed_parts, axis=0, ignore_index=True)
        feature_df = feature_df.sort_values("event_timestamp").reset_index(drop=True)

        feature_columns = self._feature_columns()
        # Safety: force numeric and deterministic NaN handling.
        for col in feature_columns:
            feature_df[col] = pd.to_numeric(feature_df[col], errors="coerce").fillna(0.0)

        return feature_df, feature_columns

    def _prepare(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        missing = [col for col in RAW_REQUIRED_COLUMNS if col not in raw_df.columns]
        if missing:
            raise ValueError(f"Missing required columns for feature building: {missing}")

        df = raw_df.copy()
        df["event_timestamp"] = pd.to_datetime(df["event_timestamp"], utc=True, errors="coerce")
        if df["event_timestamp"].isna().any():
            bad_rows = int(df["event_timestamp"].isna().sum())
            raise ValueError(f"event_timestamp contains {bad_rows} invalid rows")

        for numeric_col, _, lower, upper in CORE_NUMERIC_SIGNALS:
            df[numeric_col] = pd.to_numeric(df[numeric_col], errors="coerce")
            if df[numeric_col].isna().any():
                raise ValueError(f"{numeric_col} contains NaN values after numeric conversion")
            df[numeric_col] = df[numeric_col].clip(lower=lower, upper=upper)

        for numeric_col, _, lower, upper in OPTIONAL_NUMERIC_SIGNALS:
            if numeric_col not in df.columns:
                df[numeric_col] = np.nan
            df[numeric_col] = pd.to_numeric(df[numeric_col], errors="coerce")
            df[numeric_col] = df[numeric_col].clip(lower=lower, upper=upper)

        if "emotion_marker" not in df.columns:
            df["emotion_marker"] = ""
        df["emotion_marker"] = df["emotion_marker"].fillna("").astype(str)

        if "diary_note" not in df.columns and "note_text" in df.columns:
            df["diary_note"] = df["note_text"]
        if "diary_note" not in df.columns:
            df["diary_note"] = ""
        df["diary_note"] = df["diary_note"].fillna("").astype(str)

        return df.sort_values(["user_key", "event_timestamp"]).reset_index(drop=True)

    def _transform_user_group(self, group: pd.DataFrame) -> pd.DataFrame:
        g = group.sort_values("event_timestamp").copy()
        g["emotion_valence"] = g["emotion_marker"].map(self._emotion_to_valence).astype(float)
        g["note_present"] = g["diary_note"].map(lambda text: 1.0 if text.strip() else 0.0).astype(float)
        g["note_length"] = g["diary_note"].map(lambda text: float(min(len(text), 500))).astype(float)
        g["note_negative_score"] = g["diary_note"].map(self._note_negative_score).astype(float)
        g["inactivity_streak_days"] = self._inactivity_streak(g["sedentary_minutes"])

        for window in self.config.windows:
            self._add_window_features(g, window)

        self._add_cross_window_deltas(g)
        self._add_personal_baseline_features(g)

        return g

    def _add_window_features(self, group: pd.DataFrame, window: int) -> None:
        suffix = f"_{window}d"

        rolling_signals: tuple[tuple[str, str], ...] = (
            ("stress_level", "stress"),
            ("energy_level", "energy"),
            ("sleep_hours", "sleep"),
            ("sleep_regularity_score", "sleep_regularity"),
            ("sleep_quality_score", "sleep_quality"),
            ("physical_activity_minutes", "activity_minutes"),
            ("sedentary_minutes", "sedentary_minutes"),
            ("outdoor_minutes", "outdoor_minutes"),
            ("social_connectedness_score", "social_connectedness"),
            ("routine_regularity_score", "routine_regularity"),
            ("emotion_valence", "emotion_valence"),
            ("note_present", "note_present"),
            ("note_length", "note_length"),
            ("note_negative_score", "note_negative_score"),
            ("inactivity_streak_days", "inactivity_streak_days"),
        )
        for signal, feature_base in rolling_signals:
            rolling = group[signal].rolling(window=window, min_periods=1)
            group[f"{feature_base}_mean{suffix}"] = rolling.mean()
            group[f"{feature_base}_std{suffix}"] = rolling.std().fillna(0.0)
            group[f"{feature_base}_min{suffix}"] = rolling.min()
            group[f"{feature_base}_max{suffix}"] = rolling.max()
            group[f"{feature_base}_trend{suffix}"] = rolling.apply(
                self._trend_slope,
                raw=True,
            )
            availability_rolling = group[signal].notna().astype(float).rolling(window=window, min_periods=1)
            group[f"{feature_base}_availability{suffix}"] = availability_rolling.mean()

        group[f"checkins_count{suffix}"] = (
            group["stress_level"].rolling(window=window, min_periods=1).count().astype(float)
        )

    @staticmethod
    def _trend_slope(values: np.ndarray) -> float:
        if values.size < 2:
            return 0.0
        x = np.arange(values.size, dtype=float)
        x_centered = x - x.mean()
        denom = np.sum(x_centered**2)
        if denom == 0.0:
            return 0.0
        y_centered = values - values.mean()
        return float(np.sum(x_centered * y_centered) / denom)

    def _add_cross_window_deltas(self, group: pd.DataFrame) -> None:
        group["stress_mean_delta_3d_14d"] = group["stress_mean_3d"] - group["stress_mean_14d"]
        group["energy_mean_delta_3d_14d"] = group["energy_mean_3d"] - group["energy_mean_14d"]
        group["sleep_mean_delta_3d_14d"] = group["sleep_mean_3d"] - group["sleep_mean_14d"]
        group["sleep_quality_mean_delta_3d_14d"] = (
            group["sleep_quality_mean_3d"] - group["sleep_quality_mean_14d"]
        )
        group["activity_minutes_mean_delta_3d_14d"] = (
            group["activity_minutes_mean_3d"] - group["activity_minutes_mean_14d"]
        )
        group["sedentary_minutes_mean_delta_3d_14d"] = (
            group["sedentary_minutes_mean_3d"] - group["sedentary_minutes_mean_14d"]
        )
        group["outdoor_minutes_mean_delta_3d_14d"] = (
            group["outdoor_minutes_mean_3d"] - group["outdoor_minutes_mean_14d"]
        )
        group["social_connectedness_mean_delta_3d_14d"] = (
            group["social_connectedness_mean_3d"] - group["social_connectedness_mean_14d"]
        )
        group["routine_regularity_mean_delta_3d_14d"] = (
            group["routine_regularity_mean_3d"] - group["routine_regularity_mean_14d"]
        )
        group["emotion_valence_mean_delta_3d_14d"] = (
            group["emotion_valence_mean_3d"] - group["emotion_valence_mean_14d"]
        )
        group["note_negative_score_mean_delta_3d_14d"] = (
            group["note_negative_score_mean_3d"] - group["note_negative_score_mean_14d"]
        )

    def _add_personal_baseline_features(self, group: pd.DataFrame) -> None:
        history_events = np.arange(group.shape[0], dtype=float)
        history_days = (
            group["event_timestamp"] - group["event_timestamp"].iloc[0]
        ).dt.total_seconds() / 86400.0

        reliability = np.clip(
            history_events / float(self.config.personal_baseline_min_events),
            0.0,
            1.0,
        )

        stress_baseline = group["stress_level"].expanding(min_periods=1).mean().shift(1)
        energy_baseline = group["energy_level"].expanding(min_periods=1).mean().shift(1)
        sleep_baseline = group["sleep_hours"].expanding(min_periods=1).mean().shift(1)
        sleep_quality_baseline = group["sleep_quality_score"].expanding(min_periods=1).mean().shift(1)
        sleep_regularity_baseline = group["sleep_regularity_score"].expanding(min_periods=1).mean().shift(1)
        activity_baseline = group["physical_activity_minutes"].expanding(min_periods=1).mean().shift(1)
        sedentary_baseline = group["sedentary_minutes"].expanding(min_periods=1).mean().shift(1)
        outdoor_baseline = group["outdoor_minutes"].expanding(min_periods=1).mean().shift(1)
        social_baseline = group["social_connectedness_score"].expanding(min_periods=1).mean().shift(1)
        routine_baseline = group["routine_regularity_score"].expanding(min_periods=1).mean().shift(1)
        emotion_baseline = group["emotion_valence"].expanding(min_periods=1).mean().shift(1)
        note_negative_baseline = group["note_negative_score"].expanding(min_periods=1).mean().shift(1)

        # Cold users: blend personal baseline with short-window aggregate.
        stress_blended = reliability * stress_baseline.fillna(group["stress_mean_14d"]) + (1.0 - reliability) * group["stress_mean_3d"]
        energy_blended = reliability * energy_baseline.fillna(group["energy_mean_14d"]) + (1.0 - reliability) * group["energy_mean_3d"]
        sleep_blended = reliability * sleep_baseline.fillna(group["sleep_mean_14d"]) + (1.0 - reliability) * group["sleep_mean_3d"]
        sleep_quality_blended = reliability * sleep_quality_baseline.fillna(group["sleep_quality_mean_14d"]) + (
            1.0 - reliability
        ) * group["sleep_quality_mean_3d"]
        sleep_regularity_blended = reliability * sleep_regularity_baseline.fillna(group["sleep_regularity_mean_14d"]) + (
            1.0 - reliability
        ) * group["sleep_regularity_mean_3d"]
        activity_blended = reliability * activity_baseline.fillna(group["activity_minutes_mean_14d"]) + (
            1.0 - reliability
        ) * group["activity_minutes_mean_3d"]
        sedentary_blended = reliability * sedentary_baseline.fillna(group["sedentary_minutes_mean_14d"]) + (
            1.0 - reliability
        ) * group["sedentary_minutes_mean_3d"]
        outdoor_blended = reliability * outdoor_baseline.fillna(group["outdoor_minutes_mean_14d"]) + (
            1.0 - reliability
        ) * group["outdoor_minutes_mean_3d"]
        social_blended = reliability * social_baseline.fillna(group["social_connectedness_mean_14d"]) + (
            1.0 - reliability
        ) * group["social_connectedness_mean_3d"]
        routine_blended = reliability * routine_baseline.fillna(group["routine_regularity_mean_14d"]) + (
            1.0 - reliability
        ) * group["routine_regularity_mean_3d"]
        emotion_blended = reliability * emotion_baseline.fillna(group["emotion_valence_mean_14d"]) + (
            1.0 - reliability
        ) * group["emotion_valence_mean_3d"]
        note_negative_blended = reliability * note_negative_baseline.fillna(group["note_negative_score_mean_14d"]) + (
            1.0 - reliability
        ) * group["note_negative_score_mean_3d"]

        group["history_events"] = history_events
        group["history_days"] = history_days.clip(lower=0.0)
        group["personal_baseline_reliability"] = reliability

        group["stress_vs_personal_baseline"] = group["stress_level"] - stress_blended
        group["energy_vs_personal_baseline"] = group["energy_level"] - energy_blended
        group["sleep_vs_personal_baseline"] = group["sleep_hours"] - sleep_blended
        group["sleep_quality_vs_personal_baseline"] = group["sleep_quality_score"] - sleep_quality_blended
        group["sleep_regularity_vs_personal_baseline"] = (
            group["sleep_regularity_score"] - sleep_regularity_blended
        )
        group["activity_minutes_vs_personal_baseline"] = (
            group["physical_activity_minutes"] - activity_blended
        )
        group["sedentary_minutes_vs_personal_baseline"] = group["sedentary_minutes"] - sedentary_blended
        group["outdoor_minutes_vs_personal_baseline"] = group["outdoor_minutes"] - outdoor_blended
        group["social_connectedness_vs_personal_baseline"] = (
            group["social_connectedness_score"] - social_blended
        )
        group["routine_regularity_vs_personal_baseline"] = (
            group["routine_regularity_score"] - routine_blended
        )
        group["emotion_valence_vs_personal_baseline"] = group["emotion_valence"] - emotion_blended
        group["note_negative_score_vs_personal_baseline"] = (
            group["note_negative_score"] - note_negative_blended
        )

        group["is_cold_start"] = (history_events < float(self.config.cold_start_min_events)).astype(float)

    def _feature_columns(self) -> list[str]:
        features: List[str] = []
        rolling_feature_bases = (
            "stress",
            "energy",
            "sleep",
            "sleep_regularity",
            "sleep_quality",
            "activity_minutes",
            "sedentary_minutes",
            "outdoor_minutes",
            "social_connectedness",
            "routine_regularity",
            "emotion_valence",
            "note_present",
            "note_length",
            "note_negative_score",
            "inactivity_streak_days",
        )
        for window in self.config.windows:
            suffix = f"_{window}d"
            for base in rolling_feature_bases:
                features.extend(
                    [
                        f"{base}_mean{suffix}",
                        f"{base}_std{suffix}",
                        f"{base}_min{suffix}",
                        f"{base}_max{suffix}",
                        f"{base}_trend{suffix}",
                        f"{base}_availability{suffix}",
                    ]
                )
            features.append(f"checkins_count{suffix}")

        features.extend(
            [
                "stress_mean_delta_3d_14d",
                "energy_mean_delta_3d_14d",
                "sleep_mean_delta_3d_14d",
                "sleep_quality_mean_delta_3d_14d",
                "activity_minutes_mean_delta_3d_14d",
                "sedentary_minutes_mean_delta_3d_14d",
                "outdoor_minutes_mean_delta_3d_14d",
                "social_connectedness_mean_delta_3d_14d",
                "routine_regularity_mean_delta_3d_14d",
                "emotion_valence_mean_delta_3d_14d",
                "note_negative_score_mean_delta_3d_14d",
                "history_events",
                "history_days",
                "personal_baseline_reliability",
                "stress_vs_personal_baseline",
                "energy_vs_personal_baseline",
                "sleep_vs_personal_baseline",
                "sleep_quality_vs_personal_baseline",
                "sleep_regularity_vs_personal_baseline",
                "activity_minutes_vs_personal_baseline",
                "sedentary_minutes_vs_personal_baseline",
                "outdoor_minutes_vs_personal_baseline",
                "social_connectedness_vs_personal_baseline",
                "routine_regularity_vs_personal_baseline",
                "emotion_valence_vs_personal_baseline",
                "note_negative_score_vs_personal_baseline",
                "is_cold_start",
            ]
        )
        return features

    @staticmethod
    def _emotion_to_valence(raw: str) -> float:
        text = raw.strip().lower()
        if not text:
            return 0.0
        return float(EMOTION_VALENCE_MAP.get(text, 0.0))

    @staticmethod
    def _note_negative_score(raw: str) -> float:
        text = raw.strip().lower()
        if not text:
            return 0.0
        hits = sum(1 for marker in NOTE_NEGATIVE_KEYWORDS if marker in text)
        score = hits / max(len(NOTE_NEGATIVE_KEYWORDS), 1)
        return float(np.clip(score, 0.0, 1.0))

    @staticmethod
    def _inactivity_streak(sedentary_minutes: pd.Series) -> pd.Series:
        threshold = 600.0
        streak_values: list[float] = []
        current = 0.0
        for value in sedentary_minutes:
            if pd.notna(value) and float(value) >= threshold:
                current += 1.0
            else:
                current = 0.0
            streak_values.append(current)
        return pd.Series(streak_values, index=sedentary_minutes.index, dtype=float)


def load_tabular(path: str) -> pd.DataFrame:
    """Load CSV/Parquet tabular data."""
    lower = path.lower()
    if lower.endswith(".csv"):
        return pd.read_csv(path)
    if lower.endswith(".parquet"):
        return pd.read_parquet(path)
    raise ValueError("Unsupported input format. Use .csv or .parquet")


def filter_known_columns(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    """Keep only selected columns if present."""
    selected = [col for col in columns if col in df.columns]
    return df[selected].copy()
