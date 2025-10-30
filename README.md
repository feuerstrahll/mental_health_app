# Mental Health Companion 💜

Пилотное приложение-спутник (трекер ментального состояния, дневник, советы и практики) для поддержки психоэмоционального состояния.

## 🏗️ Структура проекта

```
lib/
├── main.dart              # Точка входа приложения
├── models/                # 👤 Алена - Модели данных
│   ├── .gitkeep
│   └── README.md
├── screens/               # 👤 Алена - Экраны приложения
│   ├── .gitkeep
│   └── README.md
├── widgets/               # 👤 Алена - Переиспользуемые компоненты
│   ├── .gitkeep
│   └── README.md
├── services/              # 👤 Вера - Бизнес-логика и сервисы
│   ├── .gitkeep
│   └── README.md
├── providers/             # 👤 Настя - State management
│   └── README.md
├── utils/                 # 👤 Настя - Утилиты и константы
│   └── constants.dart
└── routes/                # 👤 Настя - Навигация
    └── app_router.dart
```

## 👥 Распределение задач

### Алена - UI/Screens/Widgets
**Директории:** `screens/`, `widgets/`

**Задачи:**
- [ ] Создать `home_screen.dart` - главный экран с навигацией
- [ ] Создать `chat_screen.dart` - интерфейс чата с ботом
- [ ] Создать `mood_diary_screen.dart` - экран дневника настроения
- [ ] Создать `message_bubble.dart` в widgets/ - компонент для сообщений
- [ ] Создать `mood_selector.dart` в widgets/ - выбор настроения
- [ ] Создать `feature_card.dart` в widgets/ - карточки функций
- [ ] Создать `mood_chart.dart` в widgets/ - график настроения

### Вера - Models/Services
**Директории:** `models/`, `services/`

**Задачи:**
- [ ] Создать `chat_message.dart` - модель сообщения
- [ ] Создать `mood_entry.dart` - модель записи настроения
- [ ] Создать `storage_service.dart` - сервис хранения данных
- [ ] Создать `chatbot_service.dart` - логика чат-бота
- [ ] Создать `analytics_service.dart` (опционально) - аналитика настроения

### Настя - Providers/Utils/Routes
**Директории:** `providers/`, `utils/`, `routes/`

**Задачи:**
- [x] `utils/constants.dart` - константы приложения ✅
- [x] `routes/app_router.dart` - навигация ✅
- [ ] Создать `chat_provider.dart` - управление состоянием чата
- [ ] Создать `mood_provider.dart` - управление состоянием дневника
- [ ] Интегрировать providers в `main.dart`

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
flutter pub get
```

### 2. Запуск приложения

**В Chrome (веб):**
```bash
flutter run -d chrome
```

**На Windows (требует Visual Studio):**
```bash
flutter run -d windows
```

**На Android (требует Android SDK):**
```bash
flutter run -d <device-id>
```

### 3. Hot Reload

После внесения изменений:
- Нажмите `r` в терминале для hot reload
- Нажмите `R` для полного перезапуска

## 📦 Зависимости

Текущие зависимости:
- `flutter` - SDK
- `cupertino_icons` - iOS-стиль иконок

**Требуемые для проекта:**
```yaml
dependencies:
  provider: ^6.1.1           # State management
  shared_preferences: ^2.2.2 # Локальное хранение
  intl: ^0.19.0             # Форматирование дат
  fl_chart: ^0.66.0         # Графики
```

## 🔄 Git Workflow

### Создание веток

**Person A:**
```bash
git checkout -b feature/screens
git checkout -b feature/widgets
```

**Person B:**
```bash
git checkout -b feature/models
git checkout -b feature/services
```

**You:**
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

- ✅ Web (Chrome) - работает сейчас
- ⚠️ Windows - требует Visual Studio с C++
- ⚠️ Android - требует Android SDK
- ❌ iOS - требует macOS
- ❌ Linux - в разработке

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

## 📚 Полезные ссылки

- [Flutter Documentation](https://docs.flutter.dev/)
- [Provider Package](https://pub.dev/packages/provider)
- [FL Chart Examples](https://pub.dev/packages/fl_chart)
- [Material Design](https://m3.material.io/)

## 💡 Советы

1. **Читайте README.md** в каждой директории перед началом работы
2. **Используйте Hot Reload** для быстрой разработки
3. **Коммитьте часто** с понятными сообщениями
4. **Тестируйте на разных экранах** (разные размеры окна браузера)
5. **Запрашивайте ревью** перед слиянием кода

---

Made with ❤️ for mental health support
