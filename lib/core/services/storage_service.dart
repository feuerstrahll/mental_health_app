import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';

/// Сервис для хранения настроек приложения и экспорта данных
/// 
/// Использует JSON файлы для простых настроек.
/// Критичные данные (mood entries, chat messages) хранятся в зашифрованной БД.
class StorageService {
  StorageService();

  static const String _settingsFileName = 'settings.json';

  // ============ Settings ============

  /// Загружает настройки приложения
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

  /// Сохраняет настройки приложения
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

  /// Очищает настройки приложения
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

  // ============ Private Helpers ============

  Future<File> _getSettingsFile() async {
    final directory = await getApplicationDocumentsDirectory();
    return File('${directory.path}/$_settingsFileName');
  }

  Map<String, dynamic> _getDefaultSettings() {
    return {
      'theme': 'light',
      'notifications_enabled': true,
      'chat_history_enabled': true,
      'auto_save_diary': true,
      'language': 'ru',
    };
  }
}
