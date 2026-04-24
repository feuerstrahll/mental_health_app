"""Train LightGBM baseline for structured support decisioning."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.calibration import CalibratedClassifierCV
from sklearn.utils.class_weight import compute_class_weight

from .artifacts import ensure_dir, write_csv, write_json, write_markdown
from .constants import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SUPPORT_NEED_LABEL_COL,
    DEFAULT_SUPPORT_PROFILE_LABEL_COL,
    ID_TO_PROFILE,
    PROFILE_LABELS,
    PROFILE_TO_ID,
    TRAINING_DEFAULTS,
)
from .feature_builder import AggregatedFeatureBuilder, FeatureBuilderConfig, load_tabular
from .pipeline_core import (
    evaluate_predictions,
    fallback_predictions,
    make_time_split,
    profile_probabilities,
)
from .schema_utils import save_feature_schema


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train structured support baseline (LightGBM)")
    parser.add_argument("--train-data", required=True, help="Path to CSV/Parquet with raw check-in rows")
    parser.add_argument("--external-validation-data", default=None, help="Optional external validation dataset")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Artifacts output directory")

    parser.add_argument(
        "--support-need-label-col",
        default=DEFAULT_SUPPORT_NEED_LABEL_COL,
        help="Column name for support_need_score label [0..1]",
    )
    parser.add_argument(
        "--support-profile-label-col",
        default=DEFAULT_SUPPORT_PROFILE_LABEL_COL,
        help="Column name for support_profile label",
    )

    parser.add_argument("--train-ratio", type=float, default=TRAINING_DEFAULTS.train_ratio)
    parser.add_argument("--val-ratio", type=float, default=TRAINING_DEFAULTS.val_ratio)
    parser.add_argument("--calibration-method", choices=["sigmoid", "isotonic"], default=TRAINING_DEFAULTS.calibration_method)
    parser.add_argument("--confidence-threshold", type=float, default=TRAINING_DEFAULTS.confidence_threshold)
    parser.add_argument("--fallback-profile", choices=list(PROFILE_LABELS), default=TRAINING_DEFAULTS.fallback_profile)
    parser.add_argument("--cold-start-min-events", type=int, default=TRAINING_DEFAULTS.cold_start_min_events)
    parser.add_argument("--personal-baseline-min-events", type=int, default=TRAINING_DEFAULTS.personal_baseline_min_events)
    parser.add_argument("--high-support-threshold", type=float, default=TRAINING_DEFAULTS.high_support_score_threshold)
    parser.add_argument("--random-state", type=int, default=TRAINING_DEFAULTS.random_state)

    return parser.parse_args()


def run_training(args: argparse.Namespace) -> Path:
    output_dir = ensure_dir(Path(args.output_dir))

    raw = load_tabular(args.train_data)
    _validate_label_columns(raw, args.support_need_label_col, args.support_profile_label_col)

    builder = AggregatedFeatureBuilder(
        FeatureBuilderConfig(
            cold_start_min_events=args.cold_start_min_events,
            personal_baseline_min_events=args.personal_baseline_min_events,
        )
    )

    feature_df, feature_names = builder.transform(raw)
    feature_df = _attach_labels(feature_df, raw, args.support_need_label_col, args.support_profile_label_col)

    split = make_time_split(feature_df, args.train_ratio, args.val_ratio)
    x_all = feature_df[feature_names].to_numpy(dtype=np.float32)
    y_profile_all = feature_df["__support_profile_id"].to_numpy(dtype=np.int64)
    y_need_all = feature_df[args.support_need_label_col].to_numpy(dtype=np.float32)

    x_train, x_val, x_test = x_all[split.train_idx], x_all[split.val_idx], x_all[split.test_idx]
    y_profile_train = y_profile_all[split.train_idx]
    y_profile_val = y_profile_all[split.val_idx]
    y_profile_test = y_profile_all[split.test_idx]
    y_need_train, y_need_val, y_need_test = y_need_all[split.train_idx], y_need_all[split.val_idx], y_need_all[split.test_idx]

    cold_mask_test = feature_df.loc[split.test_idx, "is_cold_start"].to_numpy(dtype=bool)

    profile_model = _fit_profile_model(
        x_train,
        y_profile_train,
        x_val,
        y_profile_val,
        random_state=args.random_state,
    )

    calibrator, calibration_status = _fit_calibrator(
        profile_model,
        x_val,
        y_profile_val,
        method=args.calibration_method,
    )

    need_model = _fit_need_model(
        x_train,
        y_need_train,
        x_val,
        y_need_val,
        random_state=args.random_state,
    )

    probs_test = profile_probabilities(profile_model, calibrator, x_test)
    y_pred_profile_test = probs_test.argmax(axis=1)
    confidence_test = probs_test.max(axis=1)
    y_pred_need_test = np.clip(need_model.predict(x_test), 0.0, 1.0)

    fallback_profile_id = PROFILE_TO_ID[args.fallback_profile]
    y_pred_profile_fallback, abstain_mask = fallback_predictions(
        y_pred_profile_test,
        confidence_test,
        cold_mask_test,
        args.confidence_threshold,
        fallback_profile_id,
    )

    metrics_test = evaluate_predictions(
        y_true_profile=y_profile_test,
        y_true_need=y_need_test,
        y_pred_profile=y_pred_profile_test,
        y_pred_need=y_pred_need_test,
        probs=probs_test,
        confidence_threshold=args.confidence_threshold,
        high_support_score_threshold=args.high_support_threshold,
        cold_start_mask=cold_mask_test,
        y_pred_profile_fallback=y_pred_profile_fallback,
        abstain_mask=abstain_mask,
    )

    metrics_report: dict[str, Any] = {
        "calibration_status": calibration_status,
        "test": metrics_test,
        "split": {
            "train_samples": int(split.train_idx.size),
            "val_samples": int(split.val_idx.size),
            "test_samples": int(split.test_idx.size),
            "train_end_timestamp": split.train_end_timestamp,
            "val_end_timestamp": split.val_end_timestamp,
        },
    }

    if args.external_validation_data:
        metrics_report["external_validation"] = _evaluate_external(
            builder=builder,
            profile_model=profile_model,
            calibrator=calibrator,
            need_model=need_model,
            external_path=args.external_validation_data,
            feature_names=feature_names,
            support_need_label_col=args.support_need_label_col,
            support_profile_label_col=args.support_profile_label_col,
            confidence_threshold=args.confidence_threshold,
            fallback_profile_id=fallback_profile_id,
            high_support_threshold=args.high_support_threshold,
        )

    _save_artifacts(
        output_dir=output_dir,
        profile_model=profile_model,
        calibrator=calibrator,
        need_model=need_model,
        feature_names=feature_names,
        metrics_report=metrics_report,
        fallback_profile=args.fallback_profile,
        confidence_threshold=args.confidence_threshold,
        cold_start_min_events=args.cold_start_min_events,
        personal_baseline_min_events=args.personal_baseline_min_events,
        profile_importance=_feature_importance_frame(profile_model, feature_names),
        need_importance=_feature_importance_frame(need_model, feature_names),
    )

    print("=" * 70)
    print("Structured baseline training complete")
    print(f"Artifacts: {output_dir}")
    print(f"Test balanced_accuracy: {metrics_report['test']['balanced_accuracy']:.4f}")
    print(f"Test macro_f1: {metrics_report['test']['macro_f1']:.4f}")
    print(f"Test recall_high_support_depleted_like: {metrics_report['test']['recall_high_support_depleted_like']:.4f}")
    print("=" * 70)

    return output_dir


def _validate_label_columns(frame: pd.DataFrame, need_col: str, profile_col: str) -> None:
    missing = [col for col in (need_col, profile_col) if col not in frame.columns]
    if missing:
        raise ValueError(f"Missing label columns: {missing}")


def _attach_labels(
    feature_df: pd.DataFrame,
    raw_df: pd.DataFrame,
    need_col: str,
    profile_col: str,
) -> pd.DataFrame:
    labels = raw_df[["event_timestamp", "user_key", need_col, profile_col]].copy()
    labels["event_timestamp"] = pd.to_datetime(labels["event_timestamp"], utc=True, errors="coerce")

    merged = feature_df.merge(labels, on=["event_timestamp", "user_key"], how="left")
    merged = merged.dropna(subset=[need_col, profile_col]).copy()

    merged[need_col] = pd.to_numeric(merged[need_col], errors="coerce").clip(lower=0.0, upper=1.0)
    merged = merged.dropna(subset=[need_col])

    unknown_profiles = sorted(set(merged[profile_col].astype(str).unique()) - set(PROFILE_LABELS))
    if unknown_profiles:
        raise ValueError(f"Unsupported support profiles in labels: {unknown_profiles}")

    merged["__support_profile_id"] = merged[profile_col].astype(str).map(PROFILE_TO_ID).astype(int)
    return merged.reset_index(drop=True)


def _fit_profile_model(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
    random_state: int,
) -> LGBMClassifier:
    classes = np.unique(y_train)
    class_weights_raw = compute_class_weight(class_weight="balanced", classes=classes, y=y_train)
    class_weight = {int(cls): float(w) for cls, w in zip(classes, class_weights_raw)}

    model = LGBMClassifier(
        objective="multiclass",
        num_class=len(PROFILE_LABELS),
        n_estimators=700,
        learning_rate=0.03,
        num_leaves=31,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=random_state,
        class_weight=class_weight,
    )

    model.fit(
        x_train,
        y_train,
        eval_set=[(x_val, y_val)],
        eval_metric="multi_logloss",
        callbacks=[lgb.early_stopping(80, verbose=False)],
    )
    return model


def _fit_calibrator(
    profile_model: LGBMClassifier,
    x_val: np.ndarray,
    y_val: np.ndarray,
    method: str,
) -> tuple[CalibratedClassifierCV | None, str]:
    unique_classes = np.unique(y_val)
    if unique_classes.size < 2:
        return None, "skipped_not_enough_classes_in_validation"

    try:
        calibrator = CalibratedClassifierCV(profile_model, method=method, cv="prefit")
        calibrator.fit(x_val, y_val)
        return calibrator, f"ok_{method}"
    except Exception as exc:
        if method == "sigmoid":
            return None, f"failed_sigmoid:{exc}"[:240]

        # explicit fallback when isotonic is unstable on small validation slices
        try:
            calibrator = CalibratedClassifierCV(profile_model, method="sigmoid", cv="prefit")
            calibrator.fit(x_val, y_val)
            return calibrator, f"fallback_sigmoid_after_{method}"
        except Exception as fallback_exc:
            return None, f"failed_{method}_and_sigmoid:{fallback_exc}"[:240]


def _fit_need_model(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
    random_state: int,
) -> LGBMRegressor:
    model = LGBMRegressor(
        objective="regression",
        n_estimators=700,
        learning_rate=0.03,
        num_leaves=31,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=random_state,
    )

    model.fit(
        x_train,
        y_train,
        eval_set=[(x_val, y_val)],
        eval_metric="l2",
        callbacks=[lgb.early_stopping(80, verbose=False)],
    )
    return model


def _evaluate_external(
    *,
    builder: AggregatedFeatureBuilder,
    profile_model: LGBMClassifier,
    calibrator: CalibratedClassifierCV | None,
    need_model: LGBMRegressor,
    external_path: str,
    feature_names: list[str],
    support_need_label_col: str,
    support_profile_label_col: str,
    confidence_threshold: float,
    fallback_profile_id: int,
    high_support_threshold: float,
) -> dict:
    external_raw = load_tabular(external_path)
    _validate_label_columns(external_raw, support_need_label_col, support_profile_label_col)

    external_features, _ = builder.transform(external_raw)
    external_features = _attach_labels(
        external_features,
        external_raw,
        support_need_label_col,
        support_profile_label_col,
    )

    x_ext = external_features[feature_names].to_numpy(dtype=np.float32)
    y_profile_ext = external_features["__support_profile_id"].to_numpy(dtype=np.int64)
    y_need_ext = external_features[support_need_label_col].to_numpy(dtype=np.float32)
    cold_mask_ext = external_features["is_cold_start"].to_numpy(dtype=bool)

    probs_ext = profile_probabilities(profile_model, calibrator, x_ext)
    y_pred_profile_ext = probs_ext.argmax(axis=1)
    confidence_ext = probs_ext.max(axis=1)
    y_pred_need_ext = np.clip(need_model.predict(x_ext), 0.0, 1.0)

    y_pred_profile_fallback_ext, abstain_mask_ext = fallback_predictions(
        y_pred_profile_ext,
        confidence_ext,
        cold_mask_ext,
        confidence_threshold,
        fallback_profile_id,
    )

    return evaluate_predictions(
        y_true_profile=y_profile_ext,
        y_true_need=y_need_ext,
        y_pred_profile=y_pred_profile_ext,
        y_pred_need=y_pred_need_ext,
        probs=probs_ext,
        confidence_threshold=confidence_threshold,
        high_support_score_threshold=high_support_threshold,
        cold_start_mask=cold_mask_ext,
        y_pred_profile_fallback=y_pred_profile_fallback_ext,
        abstain_mask=abstain_mask_ext,
    )


def _feature_importance_frame(model: Any, feature_names: list[str]) -> pd.DataFrame:
    booster = model.booster_
    gain = booster.feature_importance(importance_type="gain")
    split = booster.feature_importance(importance_type="split")

    frame = pd.DataFrame(
        {
            "feature": feature_names,
            "importance_gain": gain,
            "importance_split": split,
        }
    ).sort_values("importance_gain", ascending=False)

    total_gain = frame["importance_gain"].sum()
    frame["importance_gain_pct"] = (
        (frame["importance_gain"] / total_gain) if total_gain > 0 else 0.0
    )
    return frame.reset_index(drop=True)


def _save_artifacts(
    *,
    output_dir: Path,
    profile_model: LGBMClassifier,
    calibrator: CalibratedClassifierCV | None,
    need_model: LGBMRegressor,
    feature_names: list[str],
    metrics_report: dict[str, Any],
    fallback_profile: str,
    confidence_threshold: float,
    cold_start_min_events: int,
    personal_baseline_min_events: int,
    profile_importance: pd.DataFrame,
    need_importance: pd.DataFrame,
) -> None:
    joblib.dump(profile_model, output_dir / "support_profile_model.pkl")
    joblib.dump(need_model, output_dir / "support_need_model.pkl")
    if calibrator is not None:
        joblib.dump(calibrator, output_dir / "support_profile_calibrator.pkl")

    save_feature_schema(output_dir / "feature_schema.json", feature_names)

    write_json(
        output_dir / "label_mapping.json",
        {
            "profile_to_id": PROFILE_TO_ID,
            "id_to_profile": {str(k): v for k, v in ID_TO_PROFILE.items()},
        },
    )

    inference_cfg = {
        "confidence_threshold": confidence_threshold,
        "fallback_profile": fallback_profile,
        "cold_start_min_events": cold_start_min_events,
        "personal_baseline_min_events": personal_baseline_min_events,
    }
    write_json(output_dir / "inference_config.json", inference_cfg)
    write_json(output_dir / "metrics.json", metrics_report)

    write_csv(output_dir / "feature_importance_profile.csv", profile_importance)
    write_csv(output_dir / "feature_importance_support_need.csv", need_importance)

    md = _importance_markdown(profile_importance, need_importance)
    write_markdown(output_dir / "feature_importance_report.md", md)

    manifest = {
        "artifacts": [
            "support_profile_model.pkl",
            "support_need_model.pkl",
            "support_profile_calibrator.pkl (optional)",
            "feature_schema.json",
            "label_mapping.json",
            "inference_config.json",
            "metrics.json",
            "feature_importance_profile.csv",
            "feature_importance_support_need.csv",
            "feature_importance_report.md",
        ]
    }
    write_json(output_dir / "artifact_manifest.json", manifest)


def _importance_markdown(profile_imp: pd.DataFrame, need_imp: pd.DataFrame) -> str:
    top_profile = profile_imp.head(15)
    top_need = need_imp.head(15)

    lines = [
        "# Feature Importance Report",
        "",
        "## Support Profile Model (LightGBMClassifier)",
        "",
        "| Feature | Gain % | Split Count |",
        "|---|---:|---:|",
    ]
    for _, row in top_profile.iterrows():
        lines.append(
            f"| {row['feature']} | {row['importance_gain_pct'] * 100:.2f}% | {int(row['importance_split'])} |"
        )

    lines.extend(
        [
            "",
            "## Support Need Score Model (LightGBMRegressor)",
            "",
            "| Feature | Gain % | Split Count |",
            "|---|---:|---:|",
        ]
    )
    for _, row in top_need.iterrows():
        lines.append(
            f"| {row['feature']} | {row['importance_gain_pct'] * 100:.2f}% | {int(row['importance_split'])} |"
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Baseline is intentionally simple and explainable.",
            "- Personal baseline features are reliability-weighted for sparse history.",
            "- Cold-start behavior is handled by fallback policy, not by complex model logic.",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    run_training(args)


if __name__ == "__main__":
    main()
