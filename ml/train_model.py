"""
Обучение TFLite модели для предсказания настроения
Запуск: python train_model.py
"""

import numpy as np
import tensorflow as tf
from tensorflow import keras

# Параметры
LOOKBACK_DAYS = 7
NUM_FEATURES = 4
NUM_CLASSES = 5
EPOCHS = 50
BATCH_SIZE = 32

def create_model():
    """Создает простую LSTM модель"""
    model = keras.Sequential([
        keras.layers.Input(shape=(LOOKBACK_DAYS, NUM_FEATURES)),
        keras.layers.LSTM(32, return_sequences=False),
        keras.layers.Dense(16, activation='relu'),
        keras.layers.Dropout(0.2),
        keras.layers.Dense(NUM_CLASSES, activation='softmax')
    ])
    
    model.compile(
        optimizer='adam',
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
    
    return model

def generate_synthetic_data(num_samples=1000):
    """Генерирует синтетические данные для обучения"""
    X = np.random.rand(num_samples, LOOKBACK_DAYS, NUM_FEATURES).astype(np.float32)
    
    # Синтетические метки на основе признаков
    y = np.zeros((num_samples, NUM_CLASSES))
    for i in range(num_samples):
        avg_stress = X[i, :, 1].mean()
        
        if avg_stress > 0.7:
            label = 4  # Стресс
        elif avg_stress < 0.3:
            label = 0  # Радость
        elif X[i, :, 0].mean() < 0.5:
            label = 1  # Грусть
        elif avg_stress > 0.5:
            label = 2  # Тревога
        else:
            label = 3  # Спокойствие
            
        y[i, label] = 1
    
    return X, y

def convert_to_tflite(model, output_path):
    """Конвертирует модель в TFLite формат"""
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.target_spec.supported_types = [tf.float32]
    
    tflite_model = converter.convert()
    
    with open(output_path, 'wb') as f:
        f.write(tflite_model)
    
    print(f"Model saved to {output_path}")
    print(f"Model size: {len(tflite_model) / 1024:.2f} KB")

def main():
    print("Generating synthetic data...")
    X_train, y_train = generate_synthetic_data(1000)
    X_val, y_val = generate_synthetic_data(200)
    
    print("Creating model...")
    model = create_model()
    model.summary()
    
    print("Training model...")
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        verbose=1
    )
    
    print(f"\nFinal accuracy: {history.history['accuracy'][-1]:.4f}")
    print(f"Validation accuracy: {history.history['val_accuracy'][-1]:.4f}")
    
    print("\nConverting to TFLite...")
    convert_to_tflite(model, '../assets/models/mood_predictor.tflite')
    
    print("\nDone! Copy mood_predictor.tflite to assets/models/")

if __name__ == '__main__':
    main()

