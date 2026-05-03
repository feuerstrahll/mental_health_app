import 'package:flutter/material.dart';

class AppConstants {
  static const String appName = 'Mental Health Companion';
  static const String appVersion = '1.0.0';

  static const List<String> emotions = [
    'Happy',
    'Sad',
    'Anxious',
    'Calm',
    'Angry',
    'Neutral',
  ];

  static const Map<String, Color> emotionColors = {
    'Happy': Color(0xFFFFD93D),
    'Sad': Color(0xFF6C9BCF),
    'Anxious': Color(0xFFFF9AA2),
    'Calm': Color(0xFF95E1D3),
    'Angry': Color(0xFFFF6363),
    'Neutral': Color(0xFFB8B8B8),
  };

  static const int minStressLevel = 1;
  static const int maxStressLevel = 10;

  static const String moodEntriesBox = 'mood_entries';
  static const String userPreferencesBox = 'user_preferences';

  static const String dateFormat = 'yyyy-MM-dd';
  static const String displayDateFormat = 'MMMM d, yyyy';
  static const String timeFormat = 'HH:mm';
}

class AppRoutes {
  static const String root = '/';
  static const String home = '/home';
  static const String chat = '/chat';
  static const String diary = '/diary';
  static const String tips = '/tips';
  static const String progress = '/progress';
  static const String help = '/help';
  static const String settings = '/settings';

  // Старый путь оставлен как алиас, чтобы старые переходы не ломались.
  static const String statistics = '/statistics';
}
