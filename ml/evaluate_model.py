"""
Скрипт для оценки обученной модели с детальными метриками.
Используется для проверки качества модели перед деплоем.

Запуск: python evaluate_model.py [path_to_model]
"""

import sys
import numpy as np
import tensorflow as tf
from sklearn.metrics import (
    classification_report,
    precision_recall_fscore_support,
    confusion_matrix,
)

# Параметры (должны совпадать с train_model.py)
LOOKBACK_DAYS = 7
NUM_FEATURES = 4
NUM_CLASSES = 6

EMOTION_MAP = {
    'Happy': 0,
    'Sad': 1,
    'Anxious': 2,
    'Calm': 3,
    'Angry': 4,
    'Neutral': 5,
}

CRITICAL_EMOTIONS = ['Anxious', 'Sad']
MIN_RECALL_THRESHOLD = 0.7
MIN_PRECISION_THRESHOLD = 0.5


def load_tflite_model(model_path):
    """Загружает TFLite модель"""
    interpreter = tf.lite.Interpreter(model_path=model_path)
    interpreter.allocate_tensors()
    return interpreter


def predict_tflite(interpreter, X):
    """Делает предсказания через TFLite модель"""
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    
    predictions = []
    for sample in X:
        interpreter.set_tensor(input_details[0]['index'], sample.reshape(1, LOOKBACK_DAYS, NUM_FEATURES))
        interpreter.invoke()
        output = interpreter.get_tensor(output_details[0]['index'])
        predictions.append(output[0])
    
    return np.array(predictions)


def generate_test_data(num_samples=500):
    """Генерирует тестовые данные (аналогично train_model.py)"""
    np.random.seed(42)
    X = np.zeros((num_samples, LOOKBACK_DAYS, NUM_FEATURES), dtype=np.float32)
    y = np.zeros((num_samples, NUM_CLASSES), dtype=np.float32)
    
    class_distribution = {
        0: 0.25, 1: 0.10, 2: 0.15, 3: 0.30, 4: 0.05, 5: 0.15
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
            
            for day in range(LOOKBACK_DAYS):
                X[sample_idx, day, 0] = emotion_val + np.random.uniform(-0.1, 0.1)
                X[sample_idx, day, 1] = stress_val + np.random.uniform(-0.1, 0.1)
                X[sample_idx, day, 2] = np.random.uniform(0.0, 1.0)
                X[sample_idx, day, 3] = np.random.uniform(0.0, 1.0)
            
            X[sample_idx] = np.clip(X[sample_idx], 0.0, 1.0)
            y[sample_idx, emotion_idx] = 1.0
            sample_idx += 1
    
    indices = np.random.permutation(num_samples)
    return X[indices], y[indices]


def evaluate_model(model_path):
    """Оценивает модель с детальными метриками"""
    print("="*60)
    print("MODEL EVALUATION")
    print("="*60)
    print(f"Loading model from: {model_path}\n")
    
    # Загрузка модели
    interpreter = load_tflite_model(model_path)
    
    # Генерация тестовых данных
    print("Generating test data...")
    X_test, y_test = generate_test_data(500)
    
    # Предсказания
    print("Making predictions...")
    y_pred_proba = predict_tflite(interpreter, X_test)
    y_pred = np.argmax(y_pred_proba, axis=1)
    y_true = np.argmax(y_test, axis=1)
    
    # Общие метрики
    print("\n" + "="*60)
    print("CLASSIFICATION REPORT")
    print("="*60)
    print(classification_report(
        y_true, y_pred,
        target_names=list(EMOTION_MAP.keys()),
        digits=4
    ))
    
    # Per-class метрики
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, average=None, zero_division=0
    )
    
    print("\n" + "="*60)
    print("PER-CLASS METRICS")
    print("="*60)
    print(f"{'Emotion':<12} {'Precision':<12} {'Recall':<12} {'F1-Score':<12} {'Support':<12} {'Status':<12}")
    print("-"*72)
    
    all_passed = True
    for i, emotion in enumerate(EMOTION_MAP.keys()):
        is_critical = emotion in CRITICAL_EMOTIONS
        
        # Проверка порогов
        status = "✅ OK"
        if is_critical:
            if recall[i] < MIN_RECALL_THRESHOLD:
                status = "❌ LOW RECALL"
                all_passed = False
            elif precision[i] < MIN_PRECISION_THRESHOLD:
                status = "⚠️  LOW PRECISION"
        
        marker = " ⚠️" if is_critical else ""
        print(f"{emotion:<12} {precision[i]:<12.4f} {recall[i]:<12.4f} "
              f"{f1[i]:<12.4f} {support[i]:<12}{marker} {status}")
    
    # Анализ критических эмоций
    print("\n" + "="*60)
    print("CRITICAL EMOTIONS ANALYSIS")
    print("="*60)
    critical_passed = True
    for emotion in CRITICAL_EMOTIONS:
        idx = EMOTION_MAP[emotion]
        print(f"\n{emotion}:")
        print(f"  Recall: {recall[idx]:.4f} (target: ≥ {MIN_RECALL_THRESHOLD})")
        print(f"  Precision: {precision[idx]:.4f} (target: ≥ {MIN_PRECISION_THRESHOLD})")
        print(f"  F1-Score: {f1[idx]:.4f}")
        print(f"  False Negatives: {support[idx] * (1 - recall[idx]):.0f}")
        print(f"  False Positives: {support[idx] * (1 - precision[idx]):.0f}")
        
        if recall[idx] < MIN_RECALL_THRESHOLD:
            print(f"  ❌ FAIL: Recall too low! Missing {support[idx] * (1 - recall[idx]):.0f} distress signals.")
            critical_passed = False
        elif precision[idx] < MIN_PRECISION_THRESHOLD:
            print(f"  ⚠️  WARNING: Precision low. {support[idx] * (1 - precision[idx]):.0f} false alarms.")
        else:
            print(f"  ✅ PASS: Meets quality thresholds")
    
    # Итоговый вердикт
    print("\n" + "="*60)
    print("FINAL VERDICT")
    print("="*60)
    if all_passed and critical_passed:
        print("✅ MODEL APPROVED FOR DEPLOYMENT")
        print("   All metrics meet quality thresholds")
    else:
        print("❌ MODEL NOT READY FOR DEPLOYMENT")
        print("   Review metrics above and retrain if necessary")
        print("\n   Recommendations:")
        if not critical_passed:
            print("   - Increase class weight for critical emotions")
            print("   - Add more training data for Anxious/Sad")
        print("   - Consider adjusting model architecture")
        return False
    
    return True


if __name__ == '__main__':
    model_path = sys.argv[1] if len(sys.argv) > 1 else '../assets/models/mood_predictor.tflite'
    
    try:
        success = evaluate_model(model_path)
        sys.exit(0 if success else 1)
    except FileNotFoundError:
        print(f"❌ Error: Model file not found: {model_path}")
        print("   Train the model first: python train_model.py")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

