import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';

import '../../features/chat/models/chat_message.dart';

/// Сервис для хранения данных приложения
/// 
/// Использует JSON файлы для персистентности данных.
/// В будущем можно заменить на Hive для лучшей производительности.
class StorageService {
  StorageService();

  static const String _chatFileName = 'chat_history.json';
  static const String _settingsFileName = 'settings.json';

  // ============ Chat Messages ============

  /// Загружает историю сообщений из файла
  Future<List<ChatMessage>> loadChatMessages() async {
    try {
      final file = await _getChatFile();
      
      if (!await file.exists()) {
        return [];
      }

      final contents = await file.readAsString();
      if (contents.isEmpty) {
        return [];
      }

      final List<dynamic> jsonList = jsonDecode(contents) as List<dynamic>;
      return jsonList
          .map((json) => ChatMessage.fromJson(json as Map<String, dynamic>))
          .toList();
    } catch (error, stackTrace) {
      if (kDebugMode) {
        debugPrint('Error loading chat messages: $error');
        debugPrint(stackTrace.toString());
      }
      return [];
    }
  }

  /// Сохраняет историю сообщений в файл
  Future<void> saveChatMessages(List<ChatMessage> messages) async {
    try {
      final file = await _getChatFile();
      final jsonList = messages.map((msg) => msg.toJson()).toList();
      final jsonString = jsonEncode(jsonList);
      await file.writeAsString(jsonString, flush: true);
    } catch (error, stackTrace) {
      if (kDebugMode) {
        debugPrint('Error saving chat messages: $error');
        debugPrint(stackTrace.toString());
      }
      rethrow;
    }
  }

  /// Очищает всю историю сообщений
  Future<void> clearChatHistory() async {
    try {
      final file = await _getChatFile();
      if (await file.exists()) {
        await file.delete();
      }
    } catch (error, stackTrace) {
      if (kDebugMode) {
        debugPrint('Error clearing chat history: $error');
        debugPrint(stackTrace.toString());
      }
      rethrow;
    }
  }

  /// Экспортирует историю чата в читаемый формат
  Future<String> exportChatHistory(List<ChatMessage> messages) async {
    try {
      if (messages.isEmpty) {
        return 'No messages to export';
      }

      final directory = await getApplicationDocumentsDirectory();
      final timestamp = DateTime.now().toIso8601String().replaceAll(':', '-');
      final file = File('${directory.path}/chat_export_$timestamp.txt');
      
      final buffer = StringBuffer();
      buffer.writeln('Chat History Export');
      buffer.writeln('Generated: ${DateTime.now()}');
      buffer.writeln('=' * 50);
      buffer.writeln();

      for (final message in messages) {
        final sender = message.isFromUser ? 'You' : 'Bot';
        buffer.writeln('[$sender] ${message.timestamp}');
        buffer.writeln(message.text);
        buffer.writeln();
      }

      await file.writeAsString(buffer.toString(), flush: true);
      return 'Chat history exported to:\n${file.path}';
    } catch (error, stackTrace) {
      if (kDebugMode) {
        debugPrint('Error exporting chat history: $error');
        debugPrint(stackTrace.toString());
      }
      return 'Export failed: $error';
    }
  }

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

  /// Очищает все данные приложения
  Future<void> clearAllData() async {
    await clearChatHistory();
    
    try {
      final settingsFile = await _getSettingsFile();
      if (await settingsFile.exists()) {
        await settingsFile.delete();
      }
    } catch (error, stackTrace) {
      if (kDebugMode) {
        debugPrint('Error clearing all data: $error');
        debugPrint(stackTrace.toString());
      }
      rethrow;
    }
  }

  // ============ Private Helpers ============

  Future<File> _getChatFile() async {
    final directory = await getApplicationDocumentsDirectory();
    return File('${directory.path}/$_chatFileName');
  }

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
