# Models Directory

**Assigned to: Vera**

This directory хранит **общие** модели, переиспользуемые в нескольких модулях.

Модели, относящиеся к одному фиче-модулю, теперь лежат рядом с ним, напр.:

- `lib/features/chat/models/chat_message.dart`
- `lib/features/mood/...` (планируется `mood_entry.dart`)

### Что добавить сюда в будущем

1. **mood_entry.dart** — общий объект записи настроения (когда понадобятся общие операции)
2. **user_profile.dart** (опционально) — пользовательские настройки/предпочтения

## Guidelines

- Use immutable models where possible
- Include `toJson()` and `fromJson()` methods for persistence
- Add proper documentation for each model
- Follow Dart naming conventions

## Example Structure

```dart
class YourModel {
  final String id;
  final String field;
  
  YourModel({required this.id, required this.field});
  
  Map<String, dynamic> toJson() => {
    'id': id,
    'field': field,
  };
  
  factory YourModel.fromJson(Map<String, dynamic> json) => YourModel(
    id: json['id'],
    field: json['field'],
  );
}
```

