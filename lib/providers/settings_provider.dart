import 'package:flutter/material.dart';

import '../core/services/storage_service.dart';

class UserProfile {
  const UserProfile({
    required this.name,
    required this.email,
    required this.phone,
    required this.gender,
    required this.age,
  });

  final String name;
  final String email;
  final String phone;
  final String gender;
  final String age;

  UserProfile copyWith({
    String? name,
    String? email,
    String? phone,
    String? gender,
    String? age,
  }) {
    return UserProfile(
      name: name ?? this.name,
      email: email ?? this.email,
      phone: phone ?? this.phone,
      gender: gender ?? this.gender,
      age: age ?? this.age,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'email': email,
      'phone': phone,
      'gender': gender,
      'age': age,
    };
  }

  factory UserProfile.fromJson(Map<String, dynamic> json) {
    return UserProfile(
      name: (json['name'] ?? '').toString(),
      email: (json['email'] ?? '').toString(),
      phone: (json['phone'] ?? '').toString(),
      gender: (json['gender'] ?? '').toString(),
      age: (json['age'] ?? '').toString(),
    );
  }

  static const empty = UserProfile(
    name: '',
    email: '',
    phone: '',
    gender: '',
    age: '',
  );
}

class SettingsProvider extends ChangeNotifier {
  SettingsProvider({StorageService? storageService})
      : _storageService = storageService ?? StorageService();

  final StorageService _storageService;

  bool _isLoading = true;
  bool _onboardingComplete = false;
  String _theme = 'dynamic';
  bool _dailyReminder = true;
  bool _tipsReminder = false;
  UserProfile _profile = UserProfile.empty;
  Map<String, String> _tipFeedback = {};
  Map<String, String> _starterQuiz = {};

  bool get isLoading => _isLoading;
  bool get onboardingComplete => _onboardingComplete;
  String get theme => _theme;
  bool get dailyReminder => _dailyReminder;
  bool get tipsReminder => _tipsReminder;
  UserProfile get profile => _profile;
  Map<String, String> get tipFeedback => Map.unmodifiable(_tipFeedback);
  Map<String, String> get starterQuiz => Map.unmodifiable(_starterQuiz);
  String get displayName => _profile.name.trim().isEmpty ? 'друг' : _profile.name.trim();

  ThemeMode get themeMode {
    if (_theme == 'light') return ThemeMode.light;
    if (_theme == 'dark') return ThemeMode.dark;

    final hour = DateTime.now().hour;
    return hour >= 20 || hour < 7 ? ThemeMode.dark : ThemeMode.light;
  }

  Future<void> load() async {
    _isLoading = true;
    notifyListeners();

    final data = await _storageService.loadSettings();
    _theme = (data['theme'] ?? 'dynamic').toString();
    _dailyReminder = data['daily_reminder'] as bool? ?? true;
    _tipsReminder = data['tips_reminder'] as bool? ?? false;
    _onboardingComplete = data['onboarding_complete'] as bool? ?? false;

    final profileJson = data['profile'];
    if (profileJson is Map<String, dynamic>) {
      _profile = UserProfile.fromJson(profileJson);
    } else {
      _profile = UserProfile.empty;
    }

    final tipFeedbackJson = data['tip_feedback'];
    if (tipFeedbackJson is Map) {
      _tipFeedback = tipFeedbackJson.map(
        (key, value) => MapEntry(key.toString(), value.toString()),
      );
    }

    final starterQuizJson = data['starter_quiz'];
    if (starterQuizJson is Map) {
      _starterQuiz = starterQuizJson.map(
        (key, value) => MapEntry(key.toString(), value.toString()),
      );
    }

    _isLoading = false;
    notifyListeners();
  }

  Future<void> saveProfile(UserProfile profile) async {
    _profile = profile;
    await _persist();
  }

  Future<void> savePreferences({
    required String theme,
    required bool dailyReminder,
    required bool tipsReminder,
  }) async {
    _theme = theme;
    _dailyReminder = dailyReminder;
    _tipsReminder = tipsReminder;
    await _persist();
  }

  Future<void> saveTheme(String theme) async {
    _theme = theme;
    await _persist();
  }

  Future<void> saveReminderPrefs({
    bool? dailyReminder,
    bool? tipsReminder,
  }) async {
    if (dailyReminder != null) _dailyReminder = dailyReminder;
    if (tipsReminder != null) _tipsReminder = tipsReminder;
    await _persist();
  }

  Future<void> saveTipFeedback(String tipId, String value) async {
    _tipFeedback[tipId] = value;
    await _persist();
  }

  Future<void> completeOnboarding(
    UserProfile profile, {
    Map<String, String>? starterQuiz,
  }) async {
    _profile = profile;
    if (starterQuiz != null) {
      _starterQuiz = starterQuiz;
    }
    _onboardingComplete = true;
    await _persist();
  }


  Future<void> clearPersonalData() async {
    _profile = UserProfile.empty;
    _tipFeedback.clear();
    _starterQuiz.clear();
    _onboardingComplete = false;
    _theme = 'dynamic';
    _dailyReminder = true;
    _tipsReminder = false;
    await _persist();
  }

  Future<void> resetOnboarding() async {
    _onboardingComplete = false;
    await _persist();
  }

  Future<void> _persist() async {
    await _storageService.saveSettings({
      'theme': _theme,
      'daily_reminder': _dailyReminder,
      'tips_reminder': _tipsReminder,
      'onboarding_complete': _onboardingComplete,
      'profile': _profile.toJson(),
      'tip_feedback': _tipFeedback,
      'starter_quiz': _starterQuiz,
    });
    notifyListeners();
  }
}
