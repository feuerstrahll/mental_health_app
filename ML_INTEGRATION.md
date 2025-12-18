# ML Integration Guide

## Быстрый старт

### 1. Обучение модели

```bash
cd ml
pip install -r requirements.txt
python train_model.py
```

Модель (~100-200KB) сохранится в `assets/models/mood_predictor.tflite`

**Важно:** Модель использует предобученную архитектуру с class-weighted loss для учета дисбаланса классов.

### 2. Установка зависимостей Flutter

```bash
flutter pub get
```

### 3. Использование в коде

```dart
// Предсказание настроения
final moodProvider = context.read<MoodProvider>();
final prediction = await moodProvider.predictNextMood();
// {'Happy': 0.3, 'Sad': 0.1, 'Anxious': 0.2, ...}

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

## Метрики и качество модели

### Ключевые принципы:

1. **Precision и Recall важнее Accuracy**
   - Accuracy вводит в заблуждение при дисбалансе классов
   - Каждый класс эмоций оценивается отдельно

2. **Приоритет критических состояний**
   - `Anxious` и `Sad` с высоким стрессом - критичные состояния
   - **False Negatives опаснее False Positives**
   - Минимальный recall для критических: **≥ 0.7**

3. **Дисбаланс классов**
   - Большинство людей не в кризисе большую часть времени
   - Модель использует class-weighted loss
   - Критические эмоции имеют 2x вес

### Ожидаемые метрики:

```
Anxious:  Recall ≥ 0.7, Precision ≥ 0.5
Sad:      Recall ≥ 0.7, Precision ≥ 0.5
Other:    Balanced precision/recall
```

## Файлы

- `lib/core/services/ml_service.dart` - TFLite inference
- `lib/core/services/analytics_service.dart` - аналитика и рекомендации
- `ml/train_model.py` - обучение с правильными метриками
- `ml/pretrained_weights.h5` - веса для transfer learning

## Персонализация модели

1. Экспорт данных пользователя:
   ```dart
   final exportPath = await moodProvider.exportDataForML();
   ```

2. Дообучение на пользовательских данных:
   ```bash
   python train_model.py --fine_tune --user_data export.json
   ```

3. Обновление модели в приложении

## Мониторинг в продакшене

- Отслеживайте recall для критических эмоций
- Логируйте false negatives для Anxious/Sad
- Регулярно переобучайте на новых данных