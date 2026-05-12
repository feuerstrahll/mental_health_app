"""Evaluation metrics for structured product model."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import balanced_accuracy_score, f1_score, recall_score

from .constants import DEPLETED_LIKE_PROFILES, ID_TO_PROFILE


def multiclass_brier_score(y_true: np.ndarray, probs: np.ndarray, num_classes: int) -> float:
    one_hot = np.eye(num_classes)[y_true]
    return float(np.mean(np.sum((one_hot - probs) ** 2, axis=1)))


def expected_calibration_error(y_true: np.ndarray, probs: np.ndarray, bins: int = 15) -> float:
    confidences = probs.max(axis=1)
    predictions = probs.argmax(axis=1)
    correct = (predictions == y_true).astype(float)

    edges = np.linspace(0.0, 1.0, bins + 1)
    ece = 0.0
    n = len(y_true)

    for idx in range(bins):
        lo, hi = edges[idx], edges[idx + 1]
        if idx == bins - 1:
            mask = (confidences >= lo) & (confidences <= hi)
        else:
            mask = (confidences >= lo) & (confidences < hi)

        if not np.any(mask):
            continue

        bin_acc = float(correct[mask].mean())
        bin_conf = float(confidences[mask].mean())
        ece += (mask.sum() / n) * abs(bin_acc - bin_conf)

    return float(ece)


def _high_support_recall(
    y_true_profile: np.ndarray,
    y_pred_profile: np.ndarray,
    y_true_need: np.ndarray,
    y_pred_need: np.ndarray,
    high_support_score_threshold: float,
) -> float:
    true_labels = np.array([ID_TO_PROFILE[int(v)] for v in y_true_profile])
    pred_labels = np.array([ID_TO_PROFILE[int(v)] for v in y_pred_profile])

    true_high = (y_true_need >= high_support_score_threshold) | np.isin(true_labels, list(DEPLETED_LIKE_PROFILES))
    pred_high = (y_pred_need >= high_support_score_threshold) | np.isin(pred_labels, list(DEPLETED_LIKE_PROFILES))

    if true_high.sum() == 0:
        return 0.0
    return float(recall_score(true_high.astype(int), pred_high.astype(int), zero_division=0))


def compute_metrics(
    y_true_profile: np.ndarray,
    y_pred_profile: np.ndarray,
    y_true_need: np.ndarray,
    y_pred_need: np.ndarray,
    probs: np.ndarray,
    confidence_threshold: float,
    high_support_score_threshold: float,
    cold_start_mask: np.ndarray | None = None,
) -> dict[str, Any]:
    confidence = probs.max(axis=1)
    low_conf_mask = confidence < confidence_threshold

    metrics: dict[str, Any] = {
        "balanced_accuracy": float(balanced_accuracy_score(y_true_profile, y_pred_profile)),
        "macro_f1": float(f1_score(y_true_profile, y_pred_profile, average="macro", zero_division=0)),
        "recall_high_support_depleted_like": _high_support_recall(
            y_true_profile,
            y_pred_profile,
            y_true_need,
            y_pred_need,
            high_support_score_threshold,
        ),
        "calibration": {
            "multiclass_brier_score": multiclass_brier_score(y_true_profile, probs, probs.shape[1]),
            "ece_15": expected_calibration_error(y_true_profile, probs, bins=15),
            "mean_confidence": float(confidence.mean()),
        },
        "low_confidence_rate": float(low_conf_mask.mean()),
    }

    if cold_start_mask is not None and cold_start_mask.size:
        cold_mask = cold_start_mask.astype(bool)
        warm_mask = ~cold_mask

        metrics["cold_start"] = _slice_metrics(
            cold_mask,
            y_true_profile,
            y_pred_profile,
            y_true_need,
            y_pred_need,
            probs,
            high_support_score_threshold,
        )
        metrics["warm_start"] = _slice_metrics(
            warm_mask,
            y_true_profile,
            y_pred_profile,
            y_true_need,
            y_pred_need,
            probs,
            high_support_score_threshold,
        )

    return metrics


def _slice_metrics(
    mask: np.ndarray,
    y_true_profile: np.ndarray,
    y_pred_profile: np.ndarray,
    y_true_need: np.ndarray,
    y_pred_need: np.ndarray,
    probs: np.ndarray,
    high_support_score_threshold: float,
) -> dict[str, Any]:
    if mask.sum() == 0:
        return {"samples": 0}

    y_true_slice = y_true_profile[mask]
    y_pred_slice = y_pred_profile[mask]
    need_true_slice = y_true_need[mask]
    need_pred_slice = y_pred_need[mask]
    prob_slice = probs[mask]

    return {
        "samples": int(mask.sum()),
        "balanced_accuracy": float(balanced_accuracy_score(y_true_slice, y_pred_slice)),
        "macro_f1": float(f1_score(y_true_slice, y_pred_slice, average="macro", zero_division=0)),
        "recall_high_support_depleted_like": _high_support_recall(
            y_true_slice,
            y_pred_slice,
            need_true_slice,
            need_pred_slice,
            high_support_score_threshold,
        ),
        "calibration": {
            "multiclass_brier_score": multiclass_brier_score(y_true_slice, prob_slice, prob_slice.shape[1]),
            "ece_15": expected_calibration_error(y_true_slice, prob_slice, bins=15),
        },
    }
