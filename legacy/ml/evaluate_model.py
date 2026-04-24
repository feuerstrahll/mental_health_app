"""
Оценка обученной модели на тестовой выборке (6 классов: Happy … Neutral).

Требует предварительного запуска train_model.py (файл pretrained_weights.h5 в папке ml/).

Запуск из каталога ml:
    python evaluate_model.py
"""

from pathlib import Path

import train_model as tm


def main():
    tm.init_config_from_yaml()
    assert tm.NUM_CLASSES == 6, "Ожидается NUM_CLASSES == 6 (синхронизация с ml_service.dart и AppConstants)"

    print("=" * 60)
    print("EVALUATE MODEL - 6-class report (must match Flutter / TFLite)")
    print(f"  LOOKBACK_DAYS={tm.LOOKBACK_DAYS}, NUM_FEATURES={tm.NUM_FEATURES}, NUM_CLASSES={tm.NUM_CLASSES}")
    print("=" * 60)

    X, y = tm.generate_realistic_synthetic_data(2000)

    n_train = int(len(X) * (1 - tm.VALIDATION_SPLIT - 0.1))
    n_val = int(len(X) * tm.VALIDATION_SPLIT)
    X_test = X[n_train + n_val :]
    y_test = y[n_train + n_val :]

    print(f"Test samples: {len(X_test)}")

    model = tm.create_model_with_metrics()
    weights_path = Path(__file__).parent / "pretrained_weights.h5"
    if weights_path.exists():
        model.load_weights(str(weights_path))
        print(f"Loaded weights from {weights_path}")
    else:
        print(
            "WARNING: pretrained_weights.h5 not found. "
            "Run train_model.py first, or evaluation reflects random weights."
        )

    tm.evaluate_model_detailed(model, X_test, y_test)
    print("\nDone: report must list 6 classes (Happy, Sad, Anxious, Calm, Angry, Neutral).")


if __name__ == "__main__":
    main()
