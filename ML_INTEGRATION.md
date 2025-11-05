# ML Integration Guide

## Быстрый старт

### 1. Обучение модели

```bash
cd ml
pip install -r requirements.txt
python train_model.py
```

Модель (~50KB) сохранится в `assets/models/mood_predictor.tflite`

### 2. Установка зависимостей Flutter

```bash
flutter pub get
```

### 3. Использование в коде

```dart
// Предсказание настроения
final moodProvider = context.read<MoodProvider>();
final prediction = await moodProvider.predictNextMood();
// {'Радость': 0.3, 'Грусть': 0.1, ...}

// Рекомендация категории
final category = moodProvider.getRecommendedTipCategory();
// 'stress_management' | 'relaxation' | 'positive_habits' | 'general'
```

## Архитектура

```
User Data → MoodProvider → MLService → TFLite Model → Predictions
                         ↓
                    AnalyticsService → Insights & Recommendations
```

### Файлы

- `lib/core/services/ml_service.dart` - TFLite inference
- `lib/core/services/analytics_service.dart` - аналитика и рекомендации
- `ml/train_model.py`