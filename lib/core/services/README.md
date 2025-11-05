# Core Services

**Assigned to: Nastya & Vera**

## Responsibilities

Базовые сервисы приложения, доступные всем фичам:

1. `database_service.dart` — инициализация зашифрованной SQLite (sqflite_sqlcipher)
2. `analytics_service.dart` — аналитика и рекомендации (ML + эвристики)
3. `chatbot_service.dart` — правила ответов чат-бота
4. `ml_service.dart` — обертка над TensorFlow Lite моделью
5. `mood_repository.dart` — загрузка/сохранение записей настроения
6. `storage_service.dart` — файловое хранилище настроек и чатов

## Guidelines

- Сервисы остаются stateless, состояние хранит Provider
- Все I/O оборачиваем в try/catch, логируем ошибки в debug режиме
- Общие зависимости (например `ChatMessage`) импортируем из feature-модулей
- Шифровальные ключи храним только через `FlutterSecureStorage`
- При добавлении нового сервиса обновляем документацию `ML_INTEGRATION.md` / `PROVIDERS_GUIDE.md`
