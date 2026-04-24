# Core Services

**Assigned to: Nastya & Vera**

## Responsibilities

Базовые сервисы приложения, доступные всем фичам:

1. `database_service.dart` — инициализация зашифрованной SQLite (sqflite_sqlcipher)
2. `chatbot_service.dart` — правила ответов чат-бота
3. `ml_service.dart` — обертка над TensorFlow Lite моделью
4. `mood_repository.dart` — загрузка/сохранение записей настроения (зашифрованная БД)
5. `chat_repository.dart` — загрузка/сохранение сообщений чата (зашифрованная БД)
6. `storage_service.dart` — файловое хранилище для настроек приложения

## Guidelines

- Сервисы остаются stateless, состояние хранит Provider
- Все I/O оборачиваем в try/catch, логируем ошибки в debug режиме
- Общие зависимости (например `ChatMessage`) импортируем из feature-модулей
- Шифровальные ключи храним только через `FlutterSecureStorage`
- При добавлении нового сервиса обновляем документацию `legacy/ML_INTEGRATION.md` (архив) / `PROVIDERS_GUIDE.md`
