# Services Directory

**Assigned to: Nastya**

## Responsibilities

This directory contains business logic and data management services.

### What to create:

1. **storage_service.dart** - Local data persistence
   - Save/load mood entries using SharedPreferences
   - Save/load chat messages
   - Clear data methods

2. **chatbot_service.dart** - Chatbot logic
   - Response generation based on user input
   - Keyword detection
   - Supportive message templates
   - Welcome messages

3. **analytics_service.dart** (optional) - Mood analytics
   - Calculate mood trends
   - Generate statistics
   - Insights generation

## Guidelines

- Services should be stateless utility classes
- Use async/await for I/O operations
- Handle errors gracefully
- Add proper error logging
- Document all public methods

## Example Structure

```dart
class YourService {
  // Async method example
  Future<void> saveData(String data) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('key', data);
    } catch (e) {
      // Handle error
    }
  }
  
  // Synchronous method example
  String processData(String input) {
    // Your logic here
    return result;
  }
}
```

