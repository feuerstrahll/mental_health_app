# Руководство по использованию Providers

## 📦 Обзор

В приложении реализованы два основных провайдера для управления состоянием:

1. **ChatProvider** - управление чатом с ботом-помощником
2. **MoodProvider** - управление дневником настроения

Оба провайдера используют паттерн **Provider** из пакета `provider` и следуют архитектуре с разделением на слои: UI → Provider → Service → Storage.

---

## 🤖 ChatProvider

### Описание
Управляет состоянием чата, взаимодействием с ботом и хранением истории сообщений.

### Основные возможности
- ✅ Отправка и получение сообщений
- ✅ Автоматическая генерация ответов бота на основе ключевых слов
- ✅ Сохранение истории чата в локальном хранилище
- ✅ Экспорт истории в текстовый файл
- ✅ Поиск по сообщениям
- ✅ Фильтрация по дате

### Использование в UI

#### Базовое использование

```dart
import 'package:provider/provider.dart';
import 'providers/chat_provider.dart';

// Чтение данных
Consumer<ChatProvider>(
  builder: (context, chatProvider, child) {
    if (chatProvider.isLoading) {
      return CircularProgressIndicator();
    }
    
    return ListView.builder(
      itemCount: chatProvider.messages.length,
      itemBuilder: (context, index) {
        final message = chatProvider.messages[index];
        return Text(message.text);
      },
    );
  },
)

// Отправка сообщения
final chatProvider = context.read<ChatProvider>();
chatProvider.sendMessage('Привет, бот!');

// Очистка истории
chatProvider.clearHistory();

// Экспорт
final result = await chatProvider.exportHistory();
```

#### Доступные свойства

```dart
// Список сообщений (read-only)
UnmodifiableListView<ChatMessage> messages

// Состояния
bool isLoading         // Загрузка данных
bool isBotTyping       // Бот печатает ответ
bool hasError          // Есть ошибка
String? errorMessage   // Текст ошибки
bool isInitialized     // Провайдер инициализирован
bool hasMessages       // Есть сообщения

// Статистика
int userMessageCount   // Количество сообщений пользователя
int botMessageCount    // Количество сообщений бота
ChatMessage? lastMessage        // Последнее сообщение
ChatMessage? lastUserMessage    // Последнее сообщение пользователя
```

#### Доступные методы

```dart
// Инициализация (вызывается автоматически в main.dart)
await chatProvider.initialize()

// Отправка сообщения
await chatProvider.sendMessage(String text)

// Удаление конкретного сообщения
await chatProvider.deleteMessage(String id)

// Очистка всей истории
await chatProvider.clearHistory()

// Экспорт истории
String result = await chatProvider.exportHistory()

// Перезагрузка истории
await chatProvider.reloadHistory()

// Поиск сообщений
List<ChatMessage> results = chatProvider.searchMessages('стресс')

// Фильтрация по дате
List<ChatMessage> todayMessages = chatProvider.getMessagesByDate(DateTime.now())
List<ChatMessage> rangeMessages = chatProvider.getMessagesByDateRange(start, end)
```

### Модель ChatMessage

```dart
class ChatMessage {
  final String id;
  final String text;
  final MessageSender sender;  // MessageSender.user или MessageSender.bot
  final DateTime timestamp;
  final bool isTyping;
  
  bool get isFromUser;
  bool get isFromBot;
}
```

---

## 📔 MoodProvider

### Описание
Управляет дневником настроения, записями эмоций и аналитикой.

### Основные возможности
- ✅ Добавление, обновление, удаление записей настроения
- ✅ Фильтрация по дате, эмоции, уровню стресса
- ✅ Расчет статистики (средний уровень стресса, распределение эмоций)
- ✅ Генерация наблюдений на основе данных
- ✅ Экспорт данных для ML обучения

### Использование в UI

#### Базовое использование

```dart
import 'package:provider/provider.dart';
import 'providers/mood_provider.dart';

// Чтение данных
Consumer<MoodProvider>(
  builder: (context, moodProvider, child) {
    if (moodProvider.isLoading) {
      return CircularProgressIndicator();
    }
    
    return ListView.builder(
      itemCount: moodProvider.entries.length,
      itemBuilder: (context, index) {
        final entry = moodProvider.entries[index];
        return ListTile(
          title: Text(entry.emotion),
          subtitle: Text('Стресс: ${entry.stressLevel}'),
        );
      },
    );
  },
)

// Добавление записи
final moodProvider = context.read<MoodProvider>();
await moodProvider.addEntry(
  emotion: 'Радость',
  stressLevel: 3,
  note: 'Хороший день на работе',
);

// Обновление записи
final updated = entry.copyWith(stressLevel: 5);
await moodProvider.updateEntry(updated);

// Удаление записи
await moodProvider.deleteEntry(entry.id);
```

#### Доступные свойства

```dart
// Список записей (read-only)
UnmodifiableListView<MoodEntry> entries

// Состояния
bool isLoading         // Загрузка данных
bool hasError          // Есть ошибка
String? errorMessage   // Текст ошибки

// Статистика
MoodEntry? latestEntry          // Последняя запись
double? averageStressLevel      // Средний уровень стресса
Map<String, double> emotionDistribution  // Распределение эмоций в %
```

#### Доступные методы

```dart
// Загрузка записей (вызывается автоматически в main.dart)
await moodProvider.loadEntries()

// Добавление записи
MoodEntry entry = await moodProvider.addEntry(
  emotion: String,
  stressLevel: int,      // от 1 до 10
  note: String?,         // опционально
  timestamp: DateTime?,  // опционально, по умолчанию DateTime.now()
)

// Обновление записи
await moodProvider.updateEntry(MoodEntry updated)

// Удаление записи
await moodProvider.deleteEntry(String id)

// Очистка всего дневника
await moodProvider.clearDiary()

// Фильтрация
List<MoodEntry> filtered = moodProvider.filterByDateRange(start, end)
List<MoodEntry> byEmotion = moodProvider.filterByEmotion('Радость')
List<MoodEntry> byStress = moodProvider.filterByStressLevel(minLevel: 7, maxLevel: 10)

// Аналитика
double? average = moodProvider.averageStressFor(entries)
List<String> observations = moodProvider.generateObservations(lookbackDays: 7)

// Экспорт для ML
String result = await moodProvider.exportDataForML()
```

### Модель MoodEntry

```dart
class MoodEntry {
  final String id;
  final String emotion;
  final int stressLevel;      // 1-10
  final DateTime timestamp;
  final String? note;
}
```

---

## 🔧 Сервисы

### ChatbotService
Генерирует ответы бота на основе ключевых слов.

**Поддерживаемые темы:**
- Приветствия и прощания
- Негативные эмоции (грусть, тревога, стресс)
- Позитивные эмоции
- Запросы помощи
- Стресс и работа
- Проблемы со сном
- Отношения

```dart
final service = ChatbotService();
String response = await service.generateResponse('Мне грустно');
String welcome = service.getWelcomeMessage();
```

### StorageService
Управляет локальным хранилищем данных (JSON файлы).

```dart
final storage = StorageService();

// Чат
List<ChatMessage> messages = await storage.loadChatMessages();
await storage.saveChatMessages(messages);
await storage.clearChatHistory();
String result = await storage.exportChatHistory(messages);

// Настройки
Map<String, dynamic> settings = await storage.loadSettings();
await storage.saveSettings(settings);

// Очистка всех данных
await storage.clearAllData();
```

### MoodRepository
Интерфейс для работы с записями настроения.

**Реализации:**
- `SqliteMoodRepository` - зашифрованное локальное хранилище SQLite (по умолчанию)
- `InMemoryMoodRepository` - хранит в памяти (для тестов)

```dart
final repository = SqliteMoodRepository();

List<MoodEntry> entries = await repository.fetchEntries();
await repository.upsertEntry(entry);
await repository.deleteEntry(id);
await repository.clearAll();
```

---

## 🎯 Примеры интеграции

### Пример 1: Экран чата

См. `lib/features/chat/screens/chat_screen.dart` - полная реализация UI для чата с ботом.

### Пример 2: Добавление записи настроения

```dart
class AddMoodScreen extends StatefulWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Consumer<MoodProvider>(
        builder: (context, moodProvider, child) {
          return Column(
            children: [
              // UI для выбора эмоции и уровня стресса
              ElevatedButton(
                onPressed: () async {
                  await moodProvider.addEntry(
                    emotion: selectedEmotion,
                    stressLevel: stressLevel,
                    note: noteController.text,
                  );
                  
                  if (context.mounted) {
                    Navigator.pop(context);
                  }
                },
                child: Text('Сохранить'),
              ),
            ],
          );
        },
      ),
    );
  }
}
```

### Пример 3: Статистика настроения

```dart
class StatisticsScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Consumer<MoodProvider>(
      builder: (context, moodProvider, child) {
        final average = moodProvider.averageStressLevel;
        final distribution = moodProvider.emotionDistribution;
        final observations = moodProvider.generateObservations();
        
        return Column(
          children: [
            Text('Средний стресс: ${average?.toStringAsFixed(1) ?? "N/A"}'),
            
            // График эмоций
            ...distribution.entries.map((e) =>
              Text('${e.key}: ${e.value.toStringAsFixed(1)}%')
            ),
            
            // Наблюдения
            ...observations.map((obs) => Text(obs)),
          ],
        );
      },
    );
  }
}
```

---

## 🧪 Тестирование

### Использование InMemoryMoodRepository для тестов

```dart
testWidgets('MoodProvider adds entry', (tester) async {
  final repository = InMemoryMoodRepository();
  final provider = MoodProvider(repository: repository);
  
  await provider.addEntry(
    emotion: 'Радость',
    stressLevel: 5,
  );
  
  expect(provider.entries.length, 1);
  expect(provider.entries.first.emotion, 'Радость');
});
```

---

## 📝 Best Practices

1. **Используйте `context.read()` для вызова методов**
   ```dart
   context.read<ChatProvider>().sendMessage('text');
   ```

2. **Используйте `context.watch()` или `Consumer` для реактивности**
   ```dart
   final messages = context.watch<ChatProvider>().messages;
   // или
   Consumer<ChatProvider>(builder: ...)
   ```

3. **Обрабатывайте ошибки**
   ```dart
   if (provider.hasError) {
     return ErrorWidget(provider.errorMessage);
   }
   ```

4. **Проверяйте состояние загрузки**
   ```dart
   if (provider.isLoading) {
     return CircularProgressIndicator();
   }
   ```

5. **Не забывайте про async/await**
   ```dart
   await provider.sendMessage('text');
   if (context.mounted) {
     Navigator.pop(context);
   }
   ```

---

## 🔮 Планы на будущее

### ChatProvider
- [ ] Интеграция с GPT API для более умных ответов
- [ ] Голосовой ввод/вывод
- [ ] Отправка изображений
- [ ] Предложения быстрых ответов

### MoodProvider
- [ ] Интеграция с TensorFlow Lite для предсказания настроения
- [ ] Графики и визуализации
- [ ] Напоминания о записи настроения
- [ ] Корреляция с внешними факторами (погода, сон и т.д.)

---

## 🆘 Troubleshooting

**Проблема:** Провайдер не обновляет UI

**Решение:** Убедитесь, что используете `Consumer` или `context.watch()`, а не `context.read()` для чтения данных.

---

**Проблема:** Ошибка "Provider not found"

**Решение:** Убедитесь, что `MultiProvider` обернут вокруг `MaterialApp` в `main.dart`.

---

**Проблема:** Данные не сохраняются

**Решение:** Проверьте права доступа к файловой системе. На Android убедитесь, что добавлены необходимые permissions в `AndroidManifest.xml`.

---

## 📚 Дополнительные ресурсы

- [Provider Package Documentation](https://pub.dev/packages/provider)
- [Flutter State Management](https://docs.flutter.dev/development/data-and-backend/state-mgmt)
- [path_provider Package](https://pub.dev/packages/path_provider)

