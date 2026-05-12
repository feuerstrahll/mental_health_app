import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';

class StorageService {
  StorageService();

  static const String _settingsFileName = 'settings.json';

  Future<Map<String, dynamic>> loadSettings() async {
    try {
      final file = await _getSettingsFile();
      if (!await file.exists()) {
        return _getDefaultSettings();
      }

      final contents = await file.readAsString();
      if (contents.isEmpty) {
        return _getDefaultSettings();
      }

      return jsonDecode(contents) as Map<String, dynamic>;
    } catch (error, stackTrace) {
      if (kDebugMode) {
        debugPrint('Error loading settings: $error');
        debugPrint(stackTrace.toString());
      }
      return _getDefaultSettings();
    }
  }

  Future<void> saveSettings(Map<String, dynamic> settings) async {
    try {
      final file = await _getSettingsFile();
      final jsonString = jsonEncode(settings);
      await file.writeAsString(jsonString, flush: true);
    } catch (error, stackTrace) {
      if (kDebugMode) {
        debugPrint('Error saving settings: $error');
        debugPrint(stackTrace.toString());
      }
      rethrow;
    }
  }

  Future<void> clearSettings() async {
    try {
      final settingsFile = await _getSettingsFile();
      if (await settingsFile.exists()) {
        await settingsFile.delete();
      }
    } catch (error, stackTrace) {
      if (kDebugMode) {
        debugPrint('Error clearing settings: $error');
        debugPrint(stackTrace.toString());
      }
      rethrow;
    }
  }

  Future<File> _getSettingsFile() async {
    final directory = await getApplicationDocumentsDirectory();
    return File('${directory.path}/$_settingsFileName');
  }

  Map<String, dynamic> _getDefaultSettings() {
    return {
      'theme': 'dynamic',
      'daily_reminder': true,
      'tips_reminder': false,
      'onboarding_complete': false,
      'profile': <String, dynamic>{},
      'tip_feedback': <String, dynamic>{},
      'starter_quiz': <String, dynamic>{},
    };
  }
}
