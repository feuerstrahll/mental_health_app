# Mental Health Companion 💜

Пилотное приложение-спутник (трекер ментального состояния, дневник, советы и практики) для поддержки психоэмоционального состояния.

## 🏗️ Структура проекта

```
lib/
├── main.dart                      # ✅ Точка входа с провайдерами
├── core/
│   ├── constants/app_constants.dart   # ✅ Константы и роуты
│   ├── routing/app_router.dart        # ✅ Навигация (GoRouter)
│   └── services/                      # Бизнес-логика и ML
│       ├── database_service.dart      # ✅ Шифрованная SQLite
│       ├── chatbot_service.dart       # ✅ Логика чат-бота
│       ├── ml_service.dart            # ✅ TFLite inference
│       ├── mood_repository.dart       # ✅ Репозиторий дневника
│       └── storage_service.dart       # ✅ Локальное хранение
├── features/
│   ├── chat/
│   │   ├── models/chat_message.dart   # ✅ Модель сообщения
│   │   └── screens/chat_screen.dart   # ✅ Экран чата
│   ├── home/screens/home_screen.dart  # ✅ Главная панель
│   ├── mood/screens/
│   │   ├── diary_screen.dart          # ✅ Дневник настроения
│   │   └── statistics_screen.dart     # ✅ Статистика
│   ├── tips/screens/tips_screen.dart  # ✅ Советы и практики
│   ├── help/screens/help_screen.dart  # ✅ Поддержка и контакты
│   └── settings/screens/settings_screen.dart # ✅ Настройки
├── providers/
│   ├── chat_provider.dart            # ✅ Провайдер чата
│   └── mood_provider.dart            # ✅ Провайдер дневника и ML
├── widgets/                           # Переиспользуемые компоненты
│   └── README.md
└── features/README.md               # Документация по модулям
```

## 👥 Распределение задач

### Алена — UI & Widgets
**Директории:** `lib/features/*/screens`, `lib/widgets/`

**Задачи:**
- [x] `home/screens/home_screen.dart` — главный экран ✅
- [x] `chat/screens/chat_screen.dart` — интерфейс чата ✅ (пример)
- [ ] `mood/screens/diary_screen.dart` — дневник (плейсхолдер)
- [ ] `mood/screens/statistics_screen.dart` — статистика (плейсхолдер)
- [ ] Общие виджеты: `message_bubble`, `mood_selector`, `feature_card`, `mood_chart`

### Вера — Данные и сервисы
**Директории:** `lib/core/services/`, `lib/features/chat/models/`

**Задачи:**
- [x] `chat/models/chat_message.dart` — модель сообщения ✅
- [x] `core/services/storage_service.dart` — локальное хранение ✅
- [x] `core/services/mood_repository.dart` — репозиторий дневника ✅
- [ ] Улучшения ML/Analytics по данным пользователей

### Настя — Архитектура, провайдеры, ML
**Директории:** `lib/providers/`, `lib/core/constants/`, `lib/core/routing/`, `lib/core/services/ml_service.dart`

**Задачи:**
- [x] `core/constants/app_constants.dart` — константы и роуты ✅
- [x] `core/routing/app_router.dart` — навигация ✅
- [x] `providers/chat_provider.dart` — состояние чата ✅
- [x] `core/services/chatbot_service.dart` — логика чат-бота ✅
- [x] `providers/mood_provider.dart` — состояние дневника + ML ✅
- [x] `core/services/ml_service.dart` — интеграция TensorFlow Lite ✅

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
cd mental_health_app
flutter pub get
```

### 2. Запуск приложения

**На Android (рекомендуется):**
```bash
flutter run
# или указать конкретное устройство
flutter run -d <device-id>
```

**Проверка доступных устройств:**
```bash
flutter devices
```

### 3. Hot Reload

После внесения изменений:
- Нажмите `r` в терминале для hot reload
- Нажмите `R` для полного перезапуска

### 4. Использование Providers

Все провайдеры уже интегрированы в `main.dart` и готовы к использованию:

```dart
// Пример использования ChatProvider
final chatProvider = context.read<ChatProvider>();
chatProvider.sendMessage('Привет!');

// Пример использования MoodProvider
final moodProvider = context.read<MoodProvider>();
await moodProvider.addEntry(
  emotion: 'Радость',
  stressLevel: 5,
);
```

📖 **Полное руководство:** см. `PROVIDERS_GUIDE.md`

## 📦 Зависимости

Установленные зависимости:
- ✅ `flutter` - SDK
- ✅ `provider: ^6.1.1` - State management
- ✅ `path_provider: ^2.1.4` - Доступ к файловой системе
- ✅ `go_router: ^13.0.0` - Навигация
- ✅ `intl: ^0.18.1` - Форматирование дат
- ✅ `hive: ^2.2.3` - Локальное хранилище (для будущего использования)
- ✅ `hive_flutter: ^1.1.0`

**Опциональные (пока не установлены):**
```yaml
dependencies:
  fl_chart: ^0.66.0         # Графики для статистики
```

## 🗃️ Архив legacy ML

- Экспериментальные ML-скрипты перенесены в `legacy/ml/`.
- Документ `ML_INTEGRATION.md` перенесен в `legacy/ML_INTEGRATION.md`.
- Эта часть оставлена только как исторический архив и не является активной MVP-архитектурой backend-бота.

## 🔄 Git Workflow

### Создание веток

**Алена:**
```bash
git checkout -b feature/screens
git checkout -b feature/widgets
```

**Вера:**
```bash
git checkout -b feature/models
git checkout -b feature/services
```

**Настя**
```bash
git checkout -b feature/providers
```

### Коммиты

```bash
git add .
git commit -m "feat: add chat screen"
git push origin feature/screens
```

### Merge

Создайте Pull Request и запросите ревью у команды перед слиянием.

## 📝 Code Style

- Используйте `const` для неизменяемых виджетов
- Называйте файлы в snake_case: `chat_screen.dart`
- Называйте классы в PascalCase: `ChatScreen`
- Добавляйте комментарии к публичным методам
- Следуйте рекомендациям `flutter_lints`

## 🧪 Тестирование

```bash
# Запуск тестов
flutter test

# Анализ кода
flutter analyze
```

## 📱 Платформы

- ✅ Android - основная платформа (требует Android SDK)
- ⚠️ iOS, Windows, Linux, Web - удалены для упрощения разработки

## 🆘 Помощь

**Проблемы с запуском?**
```bash
flutter doctor -v
```

**Очистка кэша:**
```bash
flutter clean
flutter pub get
```

**Конфликты зависимостей:**
```bash
flutter pub upgrade
```

## ✨ Реализованные функции

### 🤖 Чат-бот помощник
- ✅ Интеллектуальные ответы на основе ключевых слов
- ✅ Поддержка тем: стресс, эмоции, сон, отношения
- ✅ Сохранение истории чата
- ✅ Экспорт истории в файл
- ✅ Поиск по сообщениям

### 📔 Дневник настроения
- ✅ Добавление/редактирование/удаление записей
- ✅ Отслеживание эмоций и уровня стресса (1-10)
- ✅ Статистика и аналитика
- ✅ Фильтрация по дате, эмоциям, стрессу
- ✅ Экспорт данных для ML

### 🎨 UI/UX
- ✅ Material Design 3
- ✅ Удобная навигация
- ✅ Адаптивный дизайн
- ✅ Современный интерфейс

## 📚 Документация

- **PROVIDERS_GUIDE.md** - Полное руководство по использованию провайдеров
- **lib/models/README.md** - Описание моделей данных
- **lib/core/services/README.md** - Описание сервисов
- **lib/features/README.md** - Описание экранов по модулям

## 📚 Полезные ссылки

- [Flutter Documentation](https://docs.flutter.dev/)
- [Provider Package](https://pub.dev/packages/provider)
- [Go Router](https://pub.dev/packages/go_router)
- [Material Design](https://m3.material.io/)

## 💡 Советы для разработчиков

1. **Читайте PROVIDERS_GUIDE.md** перед работой с state management
2. **Используйте Hot Reload** для быстрой разработки
3. **Коммитьте часто** с понятными сообщениями
4. **Тестируйте на реальном устройстве** для лучшего опыта
5. **Запрашивайте ревью** перед слиянием кода
6. **Используйте `context.read()` для действий**, `context.watch()` для чтения данных

---

Made with ❤️ for mental health support
