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

# Параметры
LOOKBACK_DAYS = 7
NUM_FEATURES = 4
NUM_CLASSES = 6  # Happy, Sad, Anxious, Calm, Angry, Neutral
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
            weight *= 2.0  # Удваиваем вес для критических состояний
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


def generate_realistic_synthetic_data(num_samples=2000):
    """
    Генерирует более реалистичные синтетические данные с учетом дисбаланса классов.
    Большинство людей не в кризисе большую часть времени.
    """
    np.random.seed(42)
    X = np.zeros((num_samples, LOOKBACK_DAYS, NUM_FEATURES), dtype=np.float32)
    y = np.zeros((num_samples, NUM_CLASSES), dtype=np.float32)
    
    # Распределение классов (реалистичное - большинство нейтральных/спокойных)
    class_distribution = {
        0: 0.25,  # Happy - 25%
        1: 0.10,  # Sad - 10% (критическая)
        2: 0.15,  # Anxious - 15% (критическая)
        3: 0.30,  # Calm - 30%
        4: 0.05,  # Angry - 5%
        5: 0.15,  # Neutral - 15%
    }
    
    samples_per_class = {
        cls: int(num_samples * prob) 
        for cls, prob in class_distribution.items()
    }
    
    sample_idx = 0
    for emotion_idx, count in samples_per_class.items():
        for _ in range(count):
            if sample_idx >= num_samples:
                break
                
            # Генерируем признаки в зависимости от эмоции
            if emotion_idx == 0:  # Happy
                emotion_val = np.random.uniform(0.7, 1.0)
                stress_val = np.random.uniform(0.1, 0.4)
            elif emotion_idx == 1:  # Sad
                emotion_val = np.random.uniform(0.0, 0.3)
                stress_val = np.random.uniform(0.6, 1.0)
            elif emotion_idx == 2:  # Anxious
                emotion_val = np.random.uniform(0.2, 0.5)
                stress_val = np.random.uniform(0.7, 1.0)
            elif emotion_idx == 3:  # Calm
                emotion_val = np.random.uniform(0.5, 0.8)
                stress_val = np.random.uniform(0.1, 0.3)
            elif emotion_idx == 4:  # Angry
                emotion_val = np.random.uniform(0.0, 0.4)
                stress_val = np.random.uniform(0.8, 1.0)
            else:  # Neutral
                emotion_val = np.random.uniform(0.4, 0.6)
                stress_val = np.random.uniform(0.3, 0.6)
            
            # Заполняем 7 дней с небольшими вариациями
            for day in range(LOOKBACK_DAYS):
                X[sample_idx, day, 0] = emotion_val + np.random.uniform(-0.1, 0.1)
                X[sample_idx, day, 1] = stress_val + np.random.uniform(-0.1, 0.1)
                X[sample_idx, day, 2] = np.random.uniform(0.0, 1.0)  # час дня
                X[sample_idx, day, 3] = np.random.uniform(0.0, 1.0)  # день недели
            
            # Нормализуем
            X[sample_idx] = np.clip(X[sample_idx], 0.0, 1.0)
            y[sample_idx, emotion_idx] = 1.0
            
            sample_idx += 1
    
    # Перемешиваем данные
    indices = np.random.permutation(num_samples)
    X = X[indices]
    y = y[indices]
    
    return X, y


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
        target_names=list(EMOTION_MAP.keys()),
        digits=4
    ))
    
    # Precision, Recall, F1 для каждого класса
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, average=None, zero_division=0
    )
    
    print("\n" + "="*60)
    print("PER-CLASS METRICS")
    print("="*60)
    print(f"{'Emotion':<12} {'Precision':<12} {'Recall':<12} {'F1-Score':<12} {'Support':<12}")
    print("-"*60)
    
    for i, emotion in enumerate(EMOTION_MAP.keys()):
        is_critical = emotion in CRITICAL_EMOTIONS
        marker = " ⚠️" if is_critical else ""
        print(f"{emotion:<12} {precision[i]:<12.4f} {recall[i]:<12.4f} "
              f"{f1[i]:<12.4f} {support[i]:<12}{marker}")
    
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
        
        if recall[idx] < 0.7:
            print(f"  ⚠️  WARNING: Low recall for {emotion}! Missing distress signals.")
        if precision[idx] < 0.5:
            print(f"  ⚠️  WARNING: Low precision for {emotion}! Too many false alarms.")
    
    # Confusion Matrix
    print("\n" + "="*60)
    print("CONFUSION MATRIX")
    print("="*60)
    cm = confusion_matrix(y_true, y_pred)
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
    
    # Генерация данных
    print("\n[1/5] Generating realistic synthetic data...")
    X, y = generate_realistic_synthetic_data(2000)
    
    # Разделение на train/validation/test
    n_train = int(len(X) * (1 - VALIDATION_SPLIT - 0.1))
    n_val = int(len(X) * VALIDATION_SPLIT)
    
    X_train = X[:n_train]
    y_train = y[:n_train]
    X_val = X[n_train:n_train+n_val]
    y_val = y[n_train:n_train+n_val]
    X_test = X[n_train+n_val:]
    y_test = y[n_train+n_val:]
    
    print(f"Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")
    
    # Вычисление весов классов
    print("\n[2/5] Computing class weights...")
    class_weights = compute_class_weights(y_train)
    print("Class weights:", class_weights)
    
    # Создание модели
    print("\n[3/5] Creating model with detailed metrics...")
    model = create_model_with_metrics()
    
    # Попытка загрузить предобученные веса
    print("\n[4/5] Attempting to load pretrained weights...")
    weights_loaded = load_pretrained_weights(model, 'pretrained_weights.h5')
    
    if not weights_loaded:
        print("Training from scratch with class-weighted loss...")
    
    model.summary()
    
    # Обучение
    print("\n[5/5] Training model...")
    print("Note: Critical emotions (Anxious, Sad) have 2x class weight")
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
    print("2. Critical emotions (Anxious, Sad) have 2x weight for better recall")
    print("3. Per-class precision/recall metrics are tracked")
    print("4. False negatives in critical states are prioritized over false positives")
    print("\nNext steps:")
    print("- Review per-class metrics, especially for critical emotions")
    print("- If recall for Anxious/Sad is low, increase their class weight")
    print("- Use pretrained_weights.h5 for transfer learning on user data")


if __name__ == '__main__':
    main()
