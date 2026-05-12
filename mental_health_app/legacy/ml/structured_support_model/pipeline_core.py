"""Core helpers shared by train/eval pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .metrics import compute_metrics


@dataclass(frozen=True)
class TimeSplit:
    train_idx: np.ndarray
    val_idx: np.ndarray
    test_idx: np.ndarray
    train_end_timestamp: str
    val_end_timestamp: str


def make_time_split(frame: pd.DataFrame, train_ratio: float, val_ratio: float) -> TimeSplit:
    if train_ratio <= 0 or val_ratio <= 0 or (train_ratio + val_ratio) >= 1:
        raise ValueError("train_ratio and val_ratio must be >0 and their sum must be <1")

    ordered = frame.sort_values("event_timestamp")
    idx = ordered.index.to_numpy()
    n = idx.size
    if n < 30:
        raise ValueError("Need at least 30 samples for stable time-based split")

    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    train_idx = idx[:train_end]
    val_idx = idx[train_end:val_end]
    test_idx = idx[val_end:]

    if min(train_idx.size, val_idx.size, test_idx.size) == 0:
        raise ValueError("Time split produced empty train/val/test partition")

    train_end_ts = str(ordered.iloc[train_end - 1]["event_timestamp"])
    val_end_ts = str(ordered.iloc[val_end - 1]["event_timestamp"])

    return TimeSplit(
        train_idx=train_idx,
        val_idx=val_idx,
        test_idx=test_idx,
        train_end_timestamp=train_end_ts,
        val_end_timestamp=val_end_ts,
    )


def profile_probabilities(model: Any, calibrator: Any | None, x: np.ndarray) -> np.ndarray:
    if calibrator is not None:
        return calibrator.predict_proba(x)
    return model.predict_proba(x)


def fallback_predictions(
    y_pred: np.ndarray,
    confidence: np.ndarray,
    cold_start_mask: np.ndarray,
    confidence_threshold: float,
    fallback_profile_id: int,
) -> tuple[np.ndarray, np.ndarray]:
    abstain_mask = (confidence < confidence_threshold) | cold_start_mask.astype(bool)
    y_pred_final = y_pred.copy()
    y_pred_final[abstain_mask] = fallback_profile_id
    return y_pred_final, abstain_mask


def evaluate_predictions(
    *,
    y_true_profile: np.ndarray,
    y_true_need: np.ndarray,
    y_pred_profile: np.ndarray,
    y_pred_need: np.ndarray,
    probs: np.ndarray,
    confidence_threshold: float,
    high_support_score_threshold: float,
    cold_start_mask: np.ndarray,
    y_pred_profile_fallback: np.ndarray,
    abstain_mask: np.ndarray,
) -> dict:
    metrics = compute_metrics(
        y_true_profile=y_true_profile,
        y_pred_profile=y_pred_profile,
        y_true_need=y_true_need,
        y_pred_need=y_pred_need,
        probs=probs,
        confidence_threshold=confidence_threshold,
        high_support_score_threshold=high_support_score_threshold,
        cold_start_mask=cold_start_mask,
    )

    fallback_metrics = compute_metrics(
        y_true_profile=y_true_profile,
        y_pred_profile=y_pred_profile_fallback,
        y_true_need=y_true_need,
        y_pred_need=y_pred_need,
        probs=probs,
        confidence_threshold=confidence_threshold,
        high_support_score_threshold=high_support_score_threshold,
        cold_start_mask=cold_start_mask,
    )

    metrics["with_fallback"] = {
        "balanced_accuracy": fallback_metrics["balanced_accuracy"],
        "macro_f1": fallback_metrics["macro_f1"],
        "abstain_rate": float(abstain_mask.mean()),
    }
    return metrics
