import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:sqflite_sqlcipher/sqflite.dart';

import '../../features/chat/models/chat_message.dart';
import 'database_service.dart';

/// Repository interface for chat message persistence
abstract class ChatRepository {
  Future<List<ChatMessage>> fetchMessages();
  Future<void> saveMessages(List<ChatMessage> messages);
  Future<void> deleteMessage(String id);
  Future<void> clearAll();
}

/// SQLite implementation with encryption
class SqliteChatRepository implements ChatRepository {
  final DatabaseService _databaseService;
  static const String _tableName = 'chat_messages';

  SqliteChatRepository(this._databaseService);

  Future<Database> get _database async => _databaseService.database;

  @override
  Future<List<ChatMessage>> fetchMessages() async {
    try {
      final db = await _database;
      final List<Map<String, dynamic>> maps = await db.query(
        _tableName,
        orderBy: 'id ASC',
      );

      return maps.map((map) {
        final data = jsonDecode(map['data'] as String) as Map<String, dynamic>;
        return ChatMessage.fromJson(data);
      }).toList();
    } catch (e, stackTrace) {
      if (kDebugMode) {
        debugPrint('Error fetching chat messages: $e');
        debugPrint(stackTrace.toString());
      }
      return [];
    }
  }

  @override
  Future<void> saveMessages(List<ChatMessage> messages) async {
    try {
      final db = await _database;

      // Use batch operation for better performance
      final batch = db.batch();

      // Clear existing messages
      batch.delete(_tableName);

      // Insert all messages
      for (final message in messages) {
        batch.insert(
          _tableName,
          {
            'id': message.id,
            'data': jsonEncode(message.toJson()),
          },
          conflictAlgorithm: ConflictAlgorithm.replace,
        );
      }

      await batch.commit(noResult: true);
    } catch (e, stackTrace) {
      if (kDebugMode) {
        debugPrint('Error saving chat messages: $e');
        debugPrint(stackTrace.toString());
      }
      rethrow;
    }
  }

  @override
  Future<void> deleteMessage(String id) async {
    try {
      final db = await _database;
      await db.delete(
        _tableName,
        where: 'id = ?',
        whereArgs: [id],
      );
    } catch (e, stackTrace) {
      if (kDebugMode) {
        debugPrint('Error deleting chat message: $e');
        debugPrint(stackTrace.toString());
      }
      rethrow;
    }
  }

  @override
  Future<void> clearAll() async {
    try {
      final db = await _database;
      await db.delete(_tableName);
    } catch (e, stackTrace) {
      if (kDebugMode) {
        debugPrint('Error clearing chat messages: $e');
        debugPrint(stackTrace.toString());
      }
      rethrow;
    }
  }
}

/// In-memory implementation for testing
class InMemoryChatRepository implements ChatRepository {
  final List<ChatMessage> _messages = [];

  @override
  Future<List<ChatMessage>> fetchMessages() async {
    return List.from(_messages);
  }

  @override
  Future<void> saveMessages(List<ChatMessage> messages) async {
    _messages.clear();
    _messages.addAll(messages);
  }

  @override
  Future<void> deleteMessage(String id) async {
    _messages.removeWhere((msg) => msg.id == id);
  }

  @override
  Future<void> clearAll() async {
    _messages.clear();
  }
}

