import 'package:flutter/material.dart';

class AppConstants {
  // App Info
  static const String appName = 'Mental Health Companion';
  static const String appVersion = '1.0.0';
  
  // Emotions List
  static const List<String> emotions = [
    'Happy',
    'Sad',
    'Anxious',
    'Calm',
    'Angry',
    'Neutral',
  ];
  
  // Emotion Colors (Person A will use these for UI)
  static const Map<String, Color> emotionColors = {
    'Happy': Color(0xFFFFD93D),
    'Sad': Color(0xFF6C9BCF),
    'Anxious': Color(0xFFFF6B9D),
    'Calm': Color(0xFF95E1D3),
    'Angry': Color(0xFFFF6363),
    'Neutral': Color(0xFFB8B8B8),
  };
  
  // Stress Levels
  static const int minStressLevel = 1;
  static const int maxStressLevel = 10;
  
  // Storage Keys (Person B will use these)
  static const String moodEntriesBox = 'mood_entries';
  static const String userPreferencesBox = 'user_preferences';
  
  // Date Formats
  static const String dateFormat = 'yyyy-MM-dd';
  static const String displayDateFormat = 'MMMM d, yyyy';
  static const String timeFormat = 'HH:mm';
}

class AppRoutes {
  static const String home = '/';
  static const String chat = '/chat';
  static const String diary = '/diary';
  static const String statistics = '/statistics';
  static const String tips = '/tips';
  static const String help = '/help';
  static const String settings = '/settings';
}
