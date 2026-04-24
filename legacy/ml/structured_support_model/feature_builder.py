"""Feature engineering for structured support baseline (aggregated-only signals)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Tuple

import numpy as np
import pandas as pd

from .constants import RAW_REQUIRED_COLUMNS, WINDOW_DAYS


@dataclass(frozen=True)
class FeatureBuilderConfig:
    windows: Tuple[int, ...] = WINDOW_DAYS
    cold_start_min_events: int = 5
    personal_baseline_min_events: int = 10


class AggregatedFeatureBuilder:
    """Builds explainable aggregated features using only app-available raw signals."""

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

        for numeric_col, lower, upper in (
            ("stress_level", 0.0, 10.0),
            ("energy_level", 0.0, 10.0),
            ("sleep_hours", 0.0, 24.0),
        ):
            df[numeric_col] = pd.to_numeric(df[numeric_col], errors="coerce")
            if df[numeric_col].isna().any():
                raise ValueError(f"{numeric_col} contains NaN values after numeric conversion")
            df[numeric_col] = df[numeric_col].clip(lower=lower, upper=upper)

        return df.sort_values(["user_key", "event_timestamp"]).reset_index(drop=True)

    def _transform_user_group(self, group: pd.DataFrame) -> pd.DataFrame:
        g = group.sort_values("event_timestamp").copy()

        for window in self.config.windows:
            self._add_window_features(g, window)

        self._add_cross_window_deltas(g)
        self._add_personal_baseline_features(g)

        return g

    def _add_window_features(self, group: pd.DataFrame, window: int) -> None:
        suffix = f"_{window}d"

        for signal in ("stress_level", "energy_level", "sleep_hours"):
            rolling = group[signal].rolling(window=window, min_periods=1)
            group[f"{signal.replace('_level', '').replace('_hours', '')}_mean{suffix}"] = rolling.mean()
            group[f"{signal.replace('_level', '').replace('_hours', '')}_std{suffix}"] = rolling.std().fillna(0.0)
            group[f"{signal.replace('_level', '').replace('_hours', '')}_min{suffix}"] = rolling.min()
            group[f"{signal.replace('_level', '').replace('_hours', '')}_max{suffix}"] = rolling.max()
            group[f"{signal.replace('_level', '').replace('_hours', '')}_trend{suffix}"] = rolling.apply(
                self._trend_slope,
                raw=True,
            )

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

        # Cold users: blend personal baseline with short-window aggregate.
        stress_blended = reliability * stress_baseline.fillna(group["stress_mean_14d"]) + (1.0 - reliability) * group["stress_mean_3d"]
        energy_blended = reliability * energy_baseline.fillna(group["energy_mean_14d"]) + (1.0 - reliability) * group["energy_mean_3d"]
        sleep_blended = reliability * sleep_baseline.fillna(group["sleep_mean_14d"]) + (1.0 - reliability) * group["sleep_mean_3d"]

        group["history_events"] = history_events
        group["history_days"] = history_days.clip(lower=0.0)
        group["personal_baseline_reliability"] = reliability

        group["stress_vs_personal_baseline"] = group["stress_level"] - stress_blended
        group["energy_vs_personal_baseline"] = group["energy_level"] - energy_blended
        group["sleep_vs_personal_baseline"] = group["sleep_hours"] - sleep_blended

        group["is_cold_start"] = (history_events < float(self.config.cold_start_min_events)).astype(float)

    def _feature_columns(self) -> list[str]:
        features: List[str] = []
        for window in self.config.windows:
            suffix = f"_{window}d"
            for base in ("stress", "energy", "sleep"):
                features.extend(
                    [
                        f"{base}_mean{suffix}",
                        f"{base}_std{suffix}",
                        f"{base}_min{suffix}",
                        f"{base}_max{suffix}",
                        f"{base}_trend{suffix}",
                    ]
                )
            features.append(f"checkins_count{suffix}")

        features.extend(
            [
                "stress_mean_delta_3d_14d",
                "energy_mean_delta_3d_14d",
                "sleep_mean_delta_3d_14d",
                "history_events",
                "history_days",
                "personal_baseline_reliability",
                "stress_vs_personal_baseline",
                "energy_vs_personal_baseline",
                "sleep_vs_personal_baseline",
                "is_cold_start",
            ]
        )
        return features


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
