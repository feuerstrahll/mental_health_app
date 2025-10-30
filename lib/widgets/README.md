# Widgets Directory

**Assigned to: Person A**

## Responsibilities

This directory contains reusable UI components used across multiple screens.

### What to create:

1. **message_bubble.dart** - Chat message bubble widget
   - Different styles for user vs bot messages
   - Timestamp display

2. **mood_selector.dart** - Emoji/icon picker for mood selection
   - 5 mood options (very happy to very sad)
   - Visual feedback on selection

3. **feature_card.dart** - Card widget for home screen features
   - Icon, title, description
   - Tap handler

4. **mood_chart.dart** - Chart widget for mood visualization
   - Uses fl_chart package
   - Shows mood trends over time

## Guidelines

- Create small, focused, reusable widgets
- Accept data through constructor parameters
- Use callbacks for user interactions
- Make widgets customizable with optional parameters
- Document all parameters

## Example Structure

```dart
class YourWidget extends StatelessWidget {
  final String title;
  final VoidCallback onTap;
  
  const YourWidget({
    super.key,
    required this.title,
    required this.onTap,
  });
  
  @override
  Widget build(BuildContext context) {
    return // Your widget here
  }
}
```

