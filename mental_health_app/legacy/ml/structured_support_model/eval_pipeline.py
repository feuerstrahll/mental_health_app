"""Evaluate saved structured support artifacts on validation datasets."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from .artifacts import write_json
from .constants import (
    DEFAULT_SUPPORT_NEED_LABEL_COL,
    DEFAULT_SUPPORT_PROFILE_LABEL_COL,
    PROFILE_TO_ID,
)
from .feature_builder import AggregatedFeatureBuilder, FeatureBuilderConfig, load_tabular
from .pipeline_core import evaluate_predictions, fallback_predictions, profile_probabilities
from .train_pipeline import _attach_labels, _validate_label_columns


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate structured support model artifacts")
    parser.add_argument("--artifacts-dir", required=True)
    parser.add_argument("--eval-data", required=True)
    parser.add_argument("--external-validation-data", default=None)
    parser.add_argument("--output-report", default=None)
    parser.add_argument("--support-need-label-col", default=DEFAULT_SUPPORT_NEED_LABEL_COL)
    parser.add_argument("--support-profile-label-col", default=DEFAULT_SUPPORT_PROFILE_LABEL_COL)
    return parser.parse_args()


def run_evaluation(args: argparse.Namespace) -> dict[str, Any]:
    artifacts_dir = Path(args.artifacts_dir)
    profile_model = joblib.load(artifacts_dir / "support_profile_model.pkl")
    need_model = joblib.load(artifacts_dir / "support_need_model.pkl")
    calibrator_path = artifacts_dir / "support_profile_calibrator.pkl"
    calibrator = joblib.load(calibrator_path) if calibrator_path.exists() else None

    inference_cfg = _load_json(artifacts_dir / "inference_config.json")
    feature_schema = _load_json(artifacts_dir / "feature_schema.json")
    feature_names = [item["name"] for item in feature_schema["features"]]

    builder = AggregatedFeatureBuilder(
        FeatureBuilderConfig(
            cold_start_min_events=int(inference_cfg["cold_start_min_events"]),
            personal_baseline_min_events=int(inference_cfg.get("personal_baseline_min_events", 10)),
        )
    )

    report: dict[str, Any] = {}
    report["eval"] = _evaluate_dataset(
        path=args.eval_data,
        builder=builder,
        profile_model=profile_model,
        calibrator=calibrator,
        need_model=need_model,
        feature_names=feature_names,
        support_need_label_col=args.support_need_label_col,
        support_profile_label_col=args.support_profile_label_col,
        confidence_threshold=float(inference_cfg["confidence_threshold"]),
        fallback_profile=inference_cfg["fallback_profile"],
    )

    if args.external_validation_data:
        report["external_validation"] = _evaluate_dataset(
            path=args.external_validation_data,
            builder=builder,
            profile_model=profile_model,
            calibrator=calibrator,
            need_model=need_model,
            feature_names=feature_names,
            support_need_label_col=args.support_need_label_col,
            support_profile_label_col=args.support_profile_label_col,
            confidence_threshold=float(inference_cfg["confidence_threshold"]),
            fallback_profile=inference_cfg["fallback_profile"],
        )

    output_path = Path(args.output_report) if args.output_report else artifacts_dir / "evaluation_report.json"
    write_json(output_path, report)

    print("=" * 70)
    print("Structured support evaluation complete")
    print(f"Report: {output_path}")
    print(f"Eval balanced_accuracy: {report['eval']['balanced_accuracy']:.4f}")
    print(f"Eval macro_f1: {report['eval']['macro_f1']:.4f}")
    print("=" * 70)

    return report


def _evaluate_dataset(
    *,
    path: str,
    builder: AggregatedFeatureBuilder,
    profile_model: Any,
    calibrator: Any | None,
    need_model: Any,
    feature_names: list[str],
    support_need_label_col: str,
    support_profile_label_col: str,
    confidence_threshold: float,
    fallback_profile: str,
) -> dict[str, Any]:
    raw = load_tabular(path)
    _validate_label_columns(raw, support_need_label_col, support_profile_label_col)

    features, _ = builder.transform(raw)
    features = _attach_labels(features, raw, support_need_label_col, support_profile_label_col)

    x = features[feature_names].to_numpy(dtype=np.float32)
    y_profile = features["__support_profile_id"].to_numpy(dtype=np.int64)
    y_need = features[support_need_label_col].to_numpy(dtype=np.float32)
    cold_mask = features["is_cold_start"].to_numpy(dtype=bool)

    probs = profile_probabilities(profile_model, calibrator, x)
    y_pred_profile = probs.argmax(axis=1)
    confidence = probs.max(axis=1)
    y_pred_need = np.clip(need_model.predict(x), 0.0, 1.0)

    fallback_profile_id = PROFILE_TO_ID[fallback_profile]
    y_pred_profile_fallback, abstain_mask = fallback_predictions(
        y_pred_profile,
        confidence,
        cold_mask,
        confidence_threshold,
        fallback_profile_id,
    )

    metrics = evaluate_predictions(
        y_true_profile=y_profile,
        y_true_need=y_need,
        y_pred_profile=y_pred_profile,
        y_pred_need=y_pred_need,
        probs=probs,
        confidence_threshold=confidence_threshold,
        high_support_score_threshold=0.70,
        cold_start_mask=cold_mask,
        y_pred_profile_fallback=y_pred_profile_fallback,
        abstain_mask=abstain_mask,
    )
    metrics["samples"] = int(features.shape[0])
    return metrics


def _load_json(path: Path) -> dict[str, Any]:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    args = parse_args()
    run_evaluation(args)


if __name__ == "__main__":
    main()
