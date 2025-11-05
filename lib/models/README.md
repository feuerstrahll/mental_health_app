# Models Directory

**Assigned to: Vera**

## Responsibilities

This directory contains all data models for the Mental Health Companion app.

### What to create:

1. **chat_message.dart** - Model for chat messages
   - id, text, isUser, timestamp fields
   - JSON serialization methods

2. **mood_entry.dart** - Model for mood diary entries
   - id, mood type (enum), note, timestamp fields
   - Helper methods for mood representation (emoji, names, values)

3. **user_profile.dart** (optional) - User settings and preferences

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

