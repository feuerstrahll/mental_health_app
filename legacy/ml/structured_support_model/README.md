# Structured Support Model (Production-like Baseline)

This package implements the first production-like **product ML baseline** for the mental health companion.

## Scope

- Product model, **not** clinical diagnosis.
- Predicts:
  - `support_need_score` (regression, 0..1)
  - `support_profile` (4-class classification)
- Uses only aggregated product signals available in app runtime.
- Enforces time-based split and confidence-based fallback.

## Files

- `feature_builder.py`: aggregates 3/7/14 day windows + personal baseline + cold-start features.
- `train_pipeline.py`: training pipeline, calibration, metrics, artifact generation.
- `eval_pipeline.py`: offline evaluation on eval/external datasets.
- `inference_wrapper.py`: production inference API with abstain/fallback behavior.
- `metrics.py`: balanced accuracy, macro F1, high-support recall, calibration metrics.
- `schema_utils.py`: feature schema JSON generation.
- `pipeline_core.py`: split/eval/fallback shared logic.
- `feature_schema.json`: baseline schema template for runtime contracts.

## Data Contract (training input)

Required raw columns:

- `event_timestamp` (datetime)
- `user_key` (anonymized user id)
- `stress_level` (0..10)
- `energy_level` (0..10)
- `sleep_hours` (0..24)
- `support_need_score_label` (0..1, configurable)
- `support_profile_label` (`stable_pattern | elevated_stress_pattern | depleted_pattern | unstable_pattern`, configurable)

## Run

From `mental_health_app/ml`:

```bash
python train_structured_support_model.py --train-data ./data/train.csv
python eval_structured_support_model.py --artifacts-dir ./artifacts/structured_support_model/latest --eval-data ./data/test.csv
```

## Main artifacts after training

- `support_profile_model.pkl`
- `support_profile_calibrator.pkl` (optional)
- `support_need_model.pkl`
- `feature_schema.json`
- `label_mapping.json`
- `inference_config.json`
- `metrics.json`
- `feature_importance_profile.csv`
- `feature_importance_support_need.csv`
- `feature_importance_report.md`
- `artifact_manifest.json`
