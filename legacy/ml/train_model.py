"""
Обучение TFLite модели для предсказания настроения с использованием предобученной модели
и правильных метрик для дисбалансированных классов.

Запуск: python train_model.py
"""

import numpy as np
import tensorflow as tf
from tensorflow import keras
from sklearn.metrics import (
    classification_report,
    precision_recall_fscore_support,
    confusion_matrix,
)
from sklearn.utils.class_weight import compute_class_weight
import yaml
import os
from pathlib import Path

# ============================================================================
# Configuration Loading - Load from model_config.yaml (single source of truth)
# ============================================================================

def load_model_config(config_path='../../model_config.yaml'):
    """
    Loads model configuration from YAML file.
    This is the single source of truth for all hyperparameters.
    """
    try:
        # Try relative path from ml directory
        if not os.path.exists(config_path):
            config_path = '../model_config.yaml'
        if not os.path.exists(config_path):
            config_path = 'model_config.yaml'
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        print(f"[OK] Config loaded from {config_path}")
        return config
    except Exception as e:
        print(f"WARNING: Could not load config: {e}")
        print("Using hardcoded defaults...")
        return None


def init_config_from_yaml():
    """
    Initialize global constants from config file.
    Falls back to hardcoded values if config unavailable.
    """
    global LOOKBACK_DAYS, NUM_FEATURES, NUM_CLASSES, EMOTION_MAP, CRITICAL_EMOTIONS, EPOCHS, BATCH_SIZE, VALIDATION_SPLIT
    
    config = load_model_config()
    
    if config and 'model' in config:
        model_cfg = config['model']
        LOOKBACK_DAYS = model_cfg.get('lookback_days', 14)
        NUM_FEATURES = model_cfg.get('num_features', 4)
        NUM_CLASSES = model_cfg.get('num_classes', 6)
        EPOCHS = model_cfg.get('epochs', 100)
        BATCH_SIZE = model_cfg.get('batch_size', 32)
        VALIDATION_SPLIT = model_cfg.get('validation_split', 0.2)
    
    if config and 'emotions' in config:
        if 'map' in config['emotions']:
            EMOTION_MAP = config['emotions']['map']
        if 'critical' in config['emotions']:
            CRITICAL_EMOTIONS = config['emotions']['critical']


# Параметры (будут перезаписаны из конфига model_config.yaml).
# Контракт с Flutter (ml_service.dart): те же значения — иначе TFLite не совпадёт с инференсом.
LOOKBACK_DAYS = 14   # окно анализа, дней (PHQ-9 / клинический период)
NUM_FEATURES = 4   # emotion_encoded, stress_norm, hour_norm, weekday_norm
NUM_CLASSES = 6      # Happy, Sad, Anxious, Calm, Angry, Neutral — как в AppConstants.emotions
EPOCHS = 100
BATCH_SIZE = 32
VALIDATION_SPLIT = 0.2

# Маппинг эмоций к индексам (соответствует AppConstants.emotions)
EMOTION_MAP = {
    'Happy': 0,
    'Sad': 1,
    'Anxious': 2,
    'Calm': 3,
    'Angry': 4,
    'Neutral': 5,
}

# Критические эмоции, где false negatives особенно опасны
CRITICAL_EMOTIONS = ['Anxious', 'Sad']  # Высокий приоритет на recall
CRITICAL_CLASS_WEIGHT_MULTIPLIER = 3.0  # Safety-first: false positive < false negative

# Minimum quality gates for deployment-oriented evaluation
REQUIRED_METRICS = {
    'Anxious': {'recall': 0.80, 'precision': 0.55, 'priority': 'CRITICAL'},
    'Sad': {'recall': 0.80, 'precision': 0.55, 'priority': 'CRITICAL'},
    'Happy': {'recall': 0.65, 'precision': 0.65, 'priority': 'HIGH'},
    'Calm': {'recall': 0.55, 'precision': 0.50, 'priority': 'MEDIUM'},
    'Neutral': {'recall': 0.55, 'precision': 0.50, 'priority': 'MEDIUM'},
    'Angry': {'recall': 0.55, 'precision': 0.50, 'priority': 'MEDIUM'},
}


# ============================================================================
# Input Validation
# ============================================================================

def validate_input_shape(X, y=None, lookback_days=None, num_features=None):
    """
    Validates input tensor shape and feature ranges.
    
    Args:
        X: Input features array of shape (batch_size, lookback_days, num_features)
        y: Optional labels array of shape (batch_size, num_classes)
        lookback_days: Expected number of lookback days (default: LOOKBACK_DAYS)
        num_features: Expected number of features (default: NUM_FEATURES)
    
    Raises:
        ValueError: If input shape or values don't match expected format
    
    Returns:
        dict: Validation result with status and details
    """
    global LOOKBACK_DAYS, NUM_FEATURES, NUM_CLASSES
    
    if lookback_days is None:
        lookback_days = LOOKBACK_DAYS
    if num_features is None:
        num_features = NUM_FEATURES
    
    validation_result = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'shape': X.shape,
        'dtype': str(X.dtype)
    }
    
    # Check array type
    if not isinstance(X, np.ndarray):
        validation_result['valid'] = False
        validation_result['errors'].append(
            f"X must be numpy.ndarray, got {type(X)}"
        )
        return validation_result
    
    # Check number of dimensions
    if len(X.shape) != 3:
        validation_result['valid'] = False
        validation_result['errors'].append(
            f"X must be 3D (batch_size, {lookback_days}, {num_features}), "
            f"got shape {X.shape}"
        )
        return validation_result
    
    # Check lookback_days
    if X.shape[1] != lookback_days:
        validation_result['valid'] = False
        validation_result['errors'].append(
            f"Expected {lookback_days} lookback days, got {X.shape[1]}. "
            f"Shape is {X.shape}, expected (batch_size, {lookback_days}, {num_features})"
        )
    
    # Check num_features
    if X.shape[2] != num_features:
        validation_result['valid'] = False
        validation_result['errors'].append(
            f"Expected {num_features} features, got {X.shape[2]}. "
            f"Shape is {X.shape}, expected (batch_size, {lookback_days}, {num_features})"
        )
    
    # Check feature value ranges [0, 1]
    if np.any(X < 0.0) or np.any(X > 1.0):
        min_val = np.min(X)
        max_val = np.max(X)
        validation_result['warnings'].append(
            f"Feature values out of [0, 1] range: min={min_val:.4f}, max={max_val:.4f}. "
            f"Consider normalizing data."
        )
    
    # Check NaN or Inf
    if np.any(np.isnan(X)) or np.any(np.isinf(X)):
        validation_result['valid'] = False
        validation_result['errors'].append(
            "Input contains NaN or Inf values"
        )
    
    # Validate labels if provided
    if y is not None:
        if not isinstance(y, np.ndarray):
            validation_result['valid'] = False
            validation_result['errors'].append(
                f"y must be numpy.ndarray, got {type(y)}"
            )
        elif len(y.shape) != 2:
            validation_result['valid'] = False
            validation_result['errors'].append(
                f"y must be 2D (batch_size, num_classes), got shape {y.shape}"
            )
        elif y.shape[0] != X.shape[0]:
            validation_result['valid'] = False
            validation_result['errors'].append(
                f"X and y batch sizes don't match: X={X.shape[0]}, y={y.shape[0]}"
            )
        elif y.shape[1] != NUM_CLASSES:
            validation_result['valid'] = False
            validation_result['errors'].append(
                f"y has {y.shape[1]} classes, expected {NUM_CLASSES}"
            )
        
        # Check that labels are one-hot encoded
        row_sums = np.sum(y, axis=1)
        if not np.allclose(row_sums, 1.0):
            validation_result['warnings'].append(
                "Labels don't appear to be one-hot encoded (row sums != 1.0)"
            )
    
    return validation_result


def print_validation_result(result):
    """Pretty-print validation result."""
    if result['valid']:
        print("[OK] Input validation PASSED")
    else:
        print("[FAIL] Input validation FAILED:")
        for error in result['errors']:
            print(f"  ERROR: {error}")
    
    if result['warnings']:
        for warning in result['warnings']:
            print(f"  WARNING: {warning}")
    
    print(f"  Shape: {result['shape']}, dtype: {result['dtype']}")


def create_base_model():
    """
    Создает базовую предобученную модель на основе общих паттернов.
    Эта модель может быть загружена из предобученных весов или обучена на большом датасете.
    """
    model = keras.Sequential([
        keras.layers.Input(shape=(LOOKBACK_DAYS, NUM_FEATURES)),
        keras.layers.LSTM(64, return_sequences=True),
        keras.layers.Dropout(0.3),
        keras.layers.LSTM(32, return_sequences=False),
        keras.layers.Dropout(0.2),
        keras.layers.Dense(32, activation='relu'),
        keras.layers.Dropout(0.2),
        keras.layers.Dense(NUM_CLASSES, activation='softmax')
    ])
    
    return model


def load_pretrained_weights(model, weights_path=None):
    """
    Загружает предобученные веса модели.
    Если весов нет, модель будет обучена с нуля, но архитектура оптимизирована.
    """
    if weights_path and tf.io.gfile.exists(weights_path):
        try:
            model.load_weights(weights_path)
            print(f"Loaded pretrained weights from {weights_path}")
            return True
        except Exception as e:
            print(f"Could not load weights: {e}. Training from scratch.")
    return False


def compute_class_weights(y_train):
    """
    Вычисляет веса классов для учета дисбаланса.
    Критические эмоции получают больший вес.
    """
    # Получаем индексы классов из меток
    class_indices = np.argmax(y_train, axis=1)
    
    # Вычисляем стандартные веса на основе частоты
    classes = np.unique(class_indices)
    class_weights = compute_class_weight(
        'balanced',
        classes=classes,
        y=class_indices
    )
    
    # Увеличиваем вес для критических эмоций
    critical_indices = [EMOTION_MAP[emotion] for emotion in CRITICAL_EMOTIONS 
                       if EMOTION_MAP[emotion] in classes]
    
    weight_dict = {}
    for i, cls in enumerate(classes):
        weight = class_weights[i]
        # Увеличиваем вес для критических эмоций (улучшаем recall)
        if cls in critical_indices:
            weight *= CRITICAL_CLASS_WEIGHT_MULTIPLIER
        weight_dict[int(cls)] = weight
    
    return weight_dict


def create_model_with_metrics():
    """
    Создает модель с кастомными метриками для каждого класса.
    """
    model = create_base_model()
    
    # Кастомные метрики для каждого класса
    metrics = ['accuracy']
    
    # Добавляем precision и recall для каждого класса
    for i, emotion in enumerate(EMOTION_MAP.keys()):
        metrics.append(
            keras.metrics.Precision(name=f'precision_{emotion.lower()}', class_id=i)
        )
        metrics.append(
            keras.metrics.Recall(name=f'recall_{emotion.lower()}', class_id=i)
        )
    
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.001),
        loss='categorical_crossentropy',
        metrics=metrics
    )
    
    return model


SEVERITY_PROFILES = {
    # PHQ-9 score 0-4: minimal depression
    'minimal': {
        'emotion_base': 0.75,  # Happy/Calm доминируют
        'stress_base': 0.15,
        'variability': 0.10,
        'target_class': 0,     # Happy
    },
    # PHQ-9 score 5-9: mild
    'mild': {
        'emotion_base': 0.55,
        'stress_base': 0.35,
        'variability': 0.15,
        'target_class': 5,     # Neutral
    },
    # PHQ-9 score 10-14: moderate
    'moderate': {
        'emotion_base': 0.35,
        'stress_base': 0.60,
        'variability': 0.20,
        'target_class': 2,     # Anxious
    },
    # PHQ-9 score 15+: severe
    'severe': {
        'emotion_base': 0.10,
        'stress_base': 0.85,
        'variability': 0.08,
        'target_class': 1,     # Sad
    },
}


def generate_phq_sample(severity, days=14):
    """Generate one synthetic sequence using PHQ-9 severity profile."""
    profile = SEVERITY_PROFILES[severity]
    X = np.zeros((days, 4), dtype=np.float32)

    for d in range(days):
        X[d, 0] = np.clip(
            profile['emotion_base'] + np.random.uniform(-profile['variability'], profile['variability']),
            0.0,
            1.0
        )
        X[d, 1] = np.clip(
            profile['stress_base'] + np.random.uniform(-profile['variability'], profile['variability']),
            0.0,
            1.0
        )
        X[d, 2] = np.random.uniform(0.0, 1.0)   # hour_of_day normalized
        X[d, 3] = np.random.uniform(0.0, 1.0)   # day_of_week normalized

    return X


def generate_realistic_synthetic_data(num_samples=2000):
    """
    Генерирует синтетический датасет на основе PHQ-9 severity-паттернов.
    Каждый sample соответствует уровню тяжести: minimal/mild/moderate/severe.
    """
    np.random.seed(42)
    X = np.zeros((num_samples, LOOKBACK_DAYS, NUM_FEATURES), dtype=np.float32)
    y = np.zeros((num_samples, NUM_CLASSES), dtype=np.float32)

    # Доля профилей в популяции (можно калибровать под реальные данные)
    severity_distribution = {
        'minimal': 0.35,
        'mild': 0.30,
        'moderate': 0.22,
        'severe': 0.13,
    }

    sample_idx = 0
    for severity, ratio in severity_distribution.items():
        count = int(num_samples * ratio)
        target_class = SEVERITY_PROFILES[severity]['target_class']

        for _ in range(count):
            if sample_idx >= num_samples:
                break
            X[sample_idx] = generate_phq_sample(severity, days=LOOKBACK_DAYS)
            y[sample_idx, target_class] = 1.0
            sample_idx += 1

    # Если из-за округления осталось место, докидываем minimal-профили
    while sample_idx < num_samples:
        X[sample_idx] = generate_phq_sample('minimal', days=LOOKBACK_DAYS)
        y[sample_idx, SEVERITY_PROFILES['minimal']['target_class']] = 1.0
        sample_idx += 1

    # Перемешиваем данные
    indices = np.random.permutation(num_samples)
    return X[indices], y[indices]


def evaluate_model_detailed(model, X_test, y_test):
    """
    Детальная оценка модели с метриками для каждого класса.
    """
    y_pred_proba = model.predict(X_test, verbose=0)
    y_pred = np.argmax(y_pred_proba, axis=1)
    y_true = np.argmax(y_test, axis=1)
    
    # Общие метрики
    print("\n" + "="*60)
    print("DETAILED CLASSIFICATION REPORT")
    print("="*60)
    print(classification_report(
        y_true, y_pred,
        labels=list(range(NUM_CLASSES)),
        target_names=list(EMOTION_MAP.keys()),
        digits=4,
        zero_division=0
    ))
    
    # Precision, Recall, F1 для каждого класса
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=list(range(NUM_CLASSES)), average=None, zero_division=0
    )
    
    print("\n" + "="*60)
    print("PER-CLASS METRICS")
    print("="*60)
    print(f"{'Emotion':<12} {'Precision':<12} {'Recall':<12} {'F1-Score':<12} {'Support':<12}")
    print("-"*60)
    
    for i, emotion in enumerate(EMOTION_MAP.keys()):
        is_critical = emotion in CRITICAL_EMOTIONS
        marker = " [!]" if is_critical else ""
        print(f"{emotion:<12} {precision[i]:<12.4f} {recall[i]:<12.4f} "
              f"{f1[i]:<12.4f} {support[i]:<12}{marker}")

    # Проверка against product quality gates
    print("\n" + "="*60)
    print("QUALITY GATES (DEPLOYMENT READINESS)")
    print("="*60)
    all_passed = True
    for emotion, req in REQUIRED_METRICS.items():
        idx = EMOTION_MAP[emotion]
        p_ok = precision[idx] >= req['precision']
        r_ok = recall[idx] >= req['recall']
        status = "PASS" if p_ok and r_ok else "FAIL"
        if status == "FAIL":
            all_passed = False
        print(
            f"{emotion:<8} [{req['priority']:<8}] "
            f"Recall {recall[idx]:.3f}/{req['recall']:.2f} "
            f"Precision {precision[idx]:.3f}/{req['precision']:.2f} -> {status}"
        )
    print(f"\nOverall quality gates: {'PASS' if all_passed else 'FAIL'}")
    
    # Особое внимание к критическим эмоциям
    print("\n" + "="*60)
    print("CRITICAL EMOTIONS ANALYSIS")
    print("="*60)
    for emotion in CRITICAL_EMOTIONS:
        idx = EMOTION_MAP[emotion]
        print(f"\n{emotion}:")
        print(f"  Recall: {recall[idx]:.4f} (False Negatives: {support[idx] * (1 - recall[idx]):.0f})")
        print(f"  Precision: {precision[idx]:.4f} (False Positives: {support[idx] * (1 - precision[idx]):.0f})")
        print(f"  F1-Score: {f1[idx]:.4f}")
        
        if recall[idx] < REQUIRED_METRICS[emotion]['recall']:
            print(f"  [WARN] Low recall for {emotion}! Missing distress signals.")
        if precision[idx] < REQUIRED_METRICS[emotion]['precision']:
            print(f"  [WARN] Low precision for {emotion}! Too many false alarms.")
    
    # Confusion Matrix
    print("\n" + "="*60)
    print("CONFUSION MATRIX")
    print("="*60)
    cm = confusion_matrix(y_true, y_pred, labels=list(range(NUM_CLASSES)))
    print("\nRows = True, Columns = Predicted")
    print(f"{'':<12}", end="")
    for emotion in EMOTION_MAP.keys():
        print(f"{emotion[:6]:<12}", end="")
    print()
    for i, emotion in enumerate(EMOTION_MAP.keys()):
        print(f"{emotion[:12]:<12}", end="")
        for j in range(NUM_CLASSES):
            print(f"{cm[i, j]:<12}", end="")
        print()
    
    return {
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'support': support
    }


def convert_to_tflite(model, output_path):
    """Конвертирует модель в TFLite формат"""
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.target_spec.supported_types = [tf.float32]
    
    tflite_model = converter.convert()
    
    with open(output_path, 'wb') as f:
        f.write(tflite_model)
    
    print(f"\nModel saved to {output_path}")
    print(f"Model size: {len(tflite_model) / 1024:.2f} KB")


def main():
    print("="*60)
    print("MOOD PREDICTION MODEL TRAINING")
    print("Using pretrained architecture with class-weighted loss")
    print("="*60)
    
    # Initialize config from YAML
    print("\n[0/6] Loading configuration...")
    init_config_from_yaml()
    print(f"  [OK] LOOKBACK_DAYS: {LOOKBACK_DAYS}")
    print(f"  [OK] NUM_FEATURES: {NUM_FEATURES}")
    print(f"  [OK] NUM_CLASSES: {NUM_CLASSES}")
    
    # Генерация данных
    print("\n[1/6] Generating realistic synthetic data...")
    X, y = generate_realistic_synthetic_data(2000)
    
    # Validate input shape
    print("\n[2/6] Validating input data...")
    validation_result = validate_input_shape(X, y)
    print_validation_result(validation_result)
    
    if not validation_result['valid']:
        print("\n[FAIL] VALIDATION FAILED - Cannot proceed with training")
        print("Please fix the issues above and try again.")
        return
    
    # Разделение на train/validation/test
    n_train = int(len(X) * (1 - VALIDATION_SPLIT - 0.1))
    n_val = int(len(X) * VALIDATION_SPLIT)
    
    X_train = X[:n_train]
    y_train = y[:n_train]
    X_val = X[n_train:n_train+n_val]
    y_val = y[n_train:n_train+n_val]
    X_test = X[n_train+n_val:]
    y_test = y[n_train+n_val:]
    
    print(f"  [OK] Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")
    
    # Вычисление весов классов
    print("\n[3/6] Computing class weights...")
    class_weights = compute_class_weights(y_train)
    print("  [OK] Class weights:", class_weights)
    
    # Создание модели
    print("\n[4/6] Creating model with detailed metrics...")
    model = create_model_with_metrics()
    
    # Попытка загрузить предобученные веса
    print("\n[5/6] Attempting to load pretrained weights...")
    weights_loaded = load_pretrained_weights(model, 'pretrained_weights.h5')
    
    if not weights_loaded:
        print("  [INFO] Training from scratch with class-weighted loss...")
    
    model.summary()
    
    # Обучение
    print("\n[6/6] Training model...")
    print(f"Note: Critical emotions (Anxious, Sad) have {CRITICAL_CLASS_WEIGHT_MULTIPLIER:.0f}x class weight")
    print("      to prioritize recall (catching distress signals)")
    
    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=15,
            restore_best_weights=True
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=5,
            min_lr=1e-6
        )
    ]
    
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        class_weight=class_weights,
        callbacks=callbacks,
        verbose=1
    )
    
    # Детальная оценка
    print("\n" + "="*60)
    print("EVALUATION ON TEST SET")
    print("="*60)
    metrics = evaluate_model_detailed(model, X_test, y_test)
    
    # Сохранение модели
    print("\n" + "="*60)
    print("SAVING MODEL")
    print("="*60)
    
    # Сохраняем веса для будущего использования
    model.save_weights('pretrained_weights.h5')
    print("Saved weights to pretrained_weights.h5")
    
    # Конвертируем в TFLite
    import os
    os.makedirs('../assets/models', exist_ok=True)
    convert_to_tflite(model, '../assets/models/mood_predictor.tflite')
    
    print("\n" + "="*60)
    print("TRAINING COMPLETE")
    print("="*60)
    print("\nKey points:")
    print("1. Model uses class-weighted loss to handle imbalanced data")
    print(f"2. Critical emotions (Anxious, Sad) have {CRITICAL_CLASS_WEIGHT_MULTIPLIER:.0f}x weight for better recall")
    print("3. Per-class precision/recall metrics are tracked")
    print("4. False negatives in critical states are prioritized over false positives")
    print("5. Input validation ensures compatibility with ml_service.dart")
    print("\nNext steps:")
    print("- Review per-class metrics, especially for critical emotions")
    print("- If recall for Anxious/Sad is low, increase their class weight")
    print("- Use pretrained_weights.h5 for transfer learning on user data")


if __name__ == '__main__':
    main()
