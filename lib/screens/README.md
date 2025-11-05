# Screens Directory

**Assigned to: Alena**

## Responsibilities

This directory contains all full-page screens for the app.

### What to create:

1. **home_screen.dart** - Main screen with navigation
   - Bottom navigation bar
   - Tab controller for Home/Chat/Mood Diary

2. **chat_screen.dart** - Chat interface with bot
   - Message list view
   - Input field for user messages
   - Bot response display

3. **mood_diary_screen.dart** - Mood tracking screen
   - Mood entry form
   - List of past mood entries
   - Mood chart/visualization

## Guidelines

- Each screen should be a StatefulWidget or StatelessWidget
- Use proper AppBar with titles
- Implement responsive layouts
- Extract reusable components to widgets/ directory
- Use the app router for navigation

## Example Structure

```dart
class YourScreen extends StatefulWidget {
  const YourScreen({super.key});
  
  @override
  State<YourScreen> createState() => _YourScreenState();
}

class _YourScreenState extends State<YourScreen> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Screen Title')),
      body: // Your content here
    );
  }
}
```

