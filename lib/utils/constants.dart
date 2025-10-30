import 'package:flutter/material.dart';

// App Constants
class AppConstants {
  // App Info
  static const String appName = 'Mental Health Companion';
  static const String appVersion = '1.0.0';

  // Storage Keys
  static const String moodEntriesKey = 'mood_entries';
  static const String chatMessagesKey = 'chat_messages';
  static const String userPreferencesKey = 'user_preferences';

  // UI Constants
  static const double defaultPadding = 16.0;
  static const double smallPadding = 8.0;
  static const double largePadding = 24.0;
  static const double borderRadius = 12.0;
  static const double cardElevation = 4.0;

  // Animation Durations
  static const Duration shortDuration = Duration(milliseconds: 300);
  static const Duration mediumDuration = Duration(milliseconds: 500);
  static const Duration longDuration = Duration(milliseconds: 1000);
}

// App Colors
class AppColors {
  // Primary Colors
  static const Color primary = Colors.deepPurple;
  static const Color primaryLight = Color(0xFFB39DDB);
  static const Color primaryDark = Color(0xFF512DA8);

  // Accent Colors
  static const Color accent = Colors.pinkAccent;
  static const Color accentLight = Color(0xFFFF80AB);

  // Background Colors
  static const Color background = Colors.white;
  static const Color backgroundLight = Color(0xFFF5F5F5);

  // Text Colors
  static const Color textPrimary = Color(0xFF212121);
  static const Color textSecondary = Color(0xFF757575);
  static const Color textHint = Color(0xFF9E9E9E);

  // Feature Colors
  static const Color chatColor = Colors.blue;
  static const Color moodColor = Colors.orange;
  static const Color supportColor = Colors.green;
  static const Color errorColor = Colors.red;

  // Mood Colors
  static const Color veryHappyColor = Color(0xFF4CAF50); // Green
  static const Color happyColor = Color(0xFF8BC34A); // Light Green
  static const Color neutralColor = Color(0xFFFFEB3B); // Yellow
  static const Color sadColor = Color(0xFFFF9800); // Orange
  static const Color verySadColor = Color(0xFFF44336); // Red
}

// Text Styles
class AppTextStyles {
  static const TextStyle heading1 = TextStyle(
    fontSize: 32,
    fontWeight: FontWeight.bold,
    color: AppColors.textPrimary,
  );

  static const TextStyle heading2 = TextStyle(
    fontSize: 24,
    fontWeight: FontWeight.bold,
    color: AppColors.textPrimary,
  );

  static const TextStyle heading3 = TextStyle(
    fontSize: 20,
    fontWeight: FontWeight.bold,
    color: AppColors.textPrimary,
  );

  static const TextStyle bodyLarge = TextStyle(
    fontSize: 16,
    color: AppColors.textPrimary,
  );

  static const TextStyle bodyMedium = TextStyle(
    fontSize: 14,
    color: AppColors.textPrimary,
  );

  static const TextStyle bodySmall = TextStyle(
    fontSize: 12,
    color: AppColors.textSecondary,
  );

  static const TextStyle caption = TextStyle(
    fontSize: 12,
    color: AppColors.textHint,
  );
}

// Route Names
class RouteNames {
  static const String home = '/';
  static const String chat = '/chat';
  static const String moodDiary = '/mood-diary';
  static const String settings = '/settings';
}

// Mood Type Helpers
class MoodHelpers {
  static const Map<int, String> moodEmojis = {
    0: '😄', // Very Happy
    1: '🙂', // Happy
    2: '😐', // Neutral
    3: '☹️', // Sad
    4: '😢', // Very Sad
  };

  static const Map<int, String> moodNames = {
    0: 'Очень хорошо',
    1: 'Хорошо',
    2: 'Нормально',
    3: 'Грустно',
    4: 'Очень грустно',
  };

  static const Map<int, Color> moodColors = {
    0: AppColors.veryHappyColor,
    1: AppColors.happyColor,
    2: AppColors.neutralColor,
    3: AppColors.sadColor,
    4: AppColors.verySadColor,
  };
}

