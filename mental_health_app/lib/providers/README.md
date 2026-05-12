# Providers Directory

**Assigned to: You**

## Responsibilities

This directory contains state management providers using the `provider` package.

### What to create:

1. **chat_provider.dart** - Manages chat state
   - List of messages
   - Send message method
   - Load/save chat history

2. **mood_provider.dart** - Manages mood diary state
   - List of mood entries
   - Add new entry method
   - Get entries by date range
   - Load/save mood history

## Guidelines

- Use `ChangeNotifier` for state management
- Call `notifyListeners()` after state changes
- Inject services through constructor
- Keep providers focused on single responsibility

## Example Structure

```dart
import 'package:flutter/foundation.dart';

class YourProvider extends ChangeNotifier {
  final YourService _service;
  List<YourModel> _items = [];
  
  YourProvider(this._service);
  
  List<YourModel> get items => _items;
  
  Future<void> loadItems() async {
    _items = await _service.loadItems();
    notifyListeners();
  }
  
  void addItem(YourModel item) {
    _items.add(item);
    notifyListeners();
  }
}
```

## Integration with main.dart

```dart
MultiProvider(
  providers: [
    ChangeNotifierProvider(
      create: (_) => ChatProvider(
        chatbotService: ChatbotService(),
        storageService: StorageService(),
      )..initialize(),
    ),
    ChangeNotifierProvider(
      create: (_) => MoodProvider(
        repository: SqliteMoodRepository(),
      )..loadEntries(),
    ),
  ],
  child: MyApp(),
)
```