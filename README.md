# Mental Health Companion 💜

A pilot companion app (mood tracker, diary, tips, and practices) that supports psycho-emotional well-being.

## 🏗️ Project Structure


```
lib/
├── main.dart                      # Entry point with providers
├── core/
│   ├── constants/app_constants.dart   # Constants and routes
│   ├── routing/app_router.dart        # Navigation (GoRouter)
│   └── services/                      # Business logic and ML
│       ├── database_service.dart      # Encrypted SQLite
│       ├── analytics_service.dart     # Analytics and tips
│       ├── chatbot_service.dart       # Chatbot logic
│       ├── ml_service.dart            # TFLite inference
│       ├── mood_repository.dart       # Diary repository
│       ├── storage_service.dart       # Local storage
│       ├── chat_repository.dart       # Chat repository
│       ├── feedback_service.dart      # Feedback service
│       └── recommendation_service.dart # Recommendation service
├── features/
│   ├── chat/
│   │   ├── models/chat_message.dart   # Message model
│   │   └── screens/chat_screen.dart   # Chat screen
│   ├── home/screens/home_screen.dart  # Main dashboard
│   ├── mood/screens/
│   │   ├── diary_screen.dart          # Mood diary
│   │   └── statistics_screen.dart     # Statistics
│   ├── tips/screens/tips_screen.dart  # Tips and practices
│   ├── help/screens/help_screen.dart  # Support and contacts
│   └── settings/screens/settings_screen.dart # Settings
├── providers/
│   ├── chat_provider.dart            # Chat provider
│   ├── mood_provider.dart            # Diary and ML provider
│   └── recommendation_provider.dart   # Recommendation provider
├── widgets/                           # Reusable components
│   ├── message_bubble.dart          # Chat message widget
│   ├── mood_selector.dart           # Emotion selector
│   ├── feature_card.dart             # Feature card
│   ├── mood_chart.dart               # Mood charts
│   └── README.md
└── features/README.md               # Module documentation
```


## 🚀 Quick Start

### 1. Install dependencies

```bash
cd mental_health_app
flutter pub get
```

### 2. Run the app

**On Android (recommended):**
```bash
flutter run
# or specify a particular device
flutter run -d <device-id>
```

**Check available devices:**
```bash
flutter devices
```

### 3. Hot Reload

After making changes:
- Press `r` in the terminal for hot reload
- Press `R` for a full restart

### 4. Using Providers

All providers are already integrated into `main.dart` and ready to use:

```dart
// Example of using ChatProvider
final chatProvider = context.read<ChatProvider>();
chatProvider.sendMessage('Hello!');

// Example of using MoodProvider
final moodProvider = context.read<MoodProvider>();
await moodProvider.addEntry(
  emotion: 'Joy',
  stressLevel: 5,
);
```

📖 **Full guide:** see `PROVIDERS_GUIDE.md`

## 📦 Dependencies

Installed dependencies:
-  `flutter` - SDK
-  `provider: ^6.1.1` - State management
-  `path_provider: ^2.1.4` - File system access
-  `go_router: ^13.0.0` - Navigation
-  `intl: ^0.18.1` - Date formatting
-  `hive: ^2.2.3` - Local storage (for future use)
-  `hive_flutter: ^1.1.0`

**Additional dependencies:**
-  `fl_chart: ^0.66.0` - Charts for statistics (used in mood_chart.dart)
-  `sqflite_sqlcipher: ^2.3.0` - Encrypted SQLite database

## 🔄 Git Workflow

### Creating branches

**Alena:**
```bash
git checkout -b feature/screens
git checkout -b feature/widgets
```

**Vera:**
```bash
git checkout -b feature/models
git checkout -b feature/services
```

**Nastya:**
```bash
git checkout -b feature/providers
```

### Commits

```bash
git add .
git commit -m "feat: add chat screen"
git push origin feature/screens
```

### Merging

Create a Pull Request and request a review from the team before merging.

## 📝 Code Style

- Use `const` for immutable widgets
- Name files in snake_case: `chat_screen.dart`
- Name classes in PascalCase: `ChatScreen`
- Add comments to public methods
- Follow the `flutter_lints` recommendations

## 🧪 Testing

```bash
# Run tests
flutter test

# Analyze code
flutter analyze
```

## 📱 Platforms

- ✅ Android - main platform (requires the Android SDK)
- ⚠️ iOS, Windows, Linux, Web - removed to simplify development

## 🆘 Help

**Trouble running the app?**
```bash
flutter doctor -v
```

**Clear the cache:**
```bash
flutter clean
flutter pub get
```

**Dependency conflicts:**
```bash
flutter pub upgrade
```

## ✨ Implemented Features

### 🤖 Chatbot Assistant
-  Smart keyword-based responses
-  Supported topics: stress, emotions, sleep, relationships
-  Chat history saving
-  Export of history to a file
-  Message search

### 📔 Mood Diary
-  Add, edit, and delete entries
-  Tracking of emotions and stress level (1-10)
-  Statistics and analytics with charts
-  Filtering by date, emotion, and stress
-  Data export for ML
-  Data visualization (line charts, pie charts)

### 🎯 Recommendation System
-  Personalized recommendations based on mood
-  Feedback on interventions
-  Recommendations adapted to their effectiveness

### 🎨 UI/UX
-  Material Design 3
-  Convenient navigation
-  Responsive design
-  Modern interface

## 📚 Documentation

- **PROVIDERS_GUIDE.md** - Full guide to using providers
- **lib/models/README.md** - Description of data models
- **lib/core/services/README.md** - Description of services
- **lib/features/README.md** - Description of screens by module

## 🔗 Useful Links

- [Flutter Documentation](https://docs.flutter.dev/)
- [Provider Package](https://pub.dev/packages/provider)
- [Go Router](https://pub.dev/packages/go_router)
- [Material Design](https://m3.material.io/)



