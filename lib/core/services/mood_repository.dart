import 'package:flutter/foundation.dart';
import 'package:sqflite_sqlcipher/sqflite.dart';

import '../../providers/mood_provider.dart';
import 'database_service.dart';

/// Реализация MoodRepository на основе зашифрованной SQLite (sqflite_sqlcipher)
class SqliteMoodRepository implements MoodRepository {
  SqliteMoodRepository();

  static const String _tableName = 'mood_entries';

  Future<Database> _db() => DatabaseService.instance.database;

  @override
  Future<List<MoodEntry>> fetchEntries() async {
    try {
      final db = await _db();
      final rows = await db.query(
        _tableName,
        orderBy: 'timestamp DESC',
      );

      return rows.map((row) {
        return MoodEntry.fromJson({
          'id': row['id'] as String,
          'emotion': row['emotion'] as String,
          'stressLevel': row['stress_level'] as int,
          'timestamp': row['timestamp'] as String,
          'note': row['note'] as String?,
        });
      }).toList();
    } catch (error, stackTrace) {
      if (kDebugMode) {
        debugPrint('Error fetching mood entries: $error');
        debugPrint(stackTrace.toString());
      }
      return [];
    }
  }

  @override
  Future<void> upsertEntry(MoodEntry entry) async {
    try {
      final db = await _db();
      await db.insert(
        _tableName,
        {
          'id': entry.id,
          'emotion': entry.emotion,
          'stress_level': entry.stressLevel,
          'timestamp': entry.timestamp.toIso8601String(),
          'note': entry.note,
        },
        conflictAlgorithm: ConflictAlgorithm.replace,
      );
    } catch (error, stackTrace) {
      if (kDebugMode) {
        debugPrint('Error upserting mood entry: $error');
        debugPrint(stackTrace.toString());
      }
      rethrow;
    }
  }

  @override
  Future<void> deleteEntry(String id) async {
    try {
      final db = await _db();
      await db.delete(
        _tableName,
        where: 'id = ?',
        whereArgs: [id],
      );
    } catch (error, stackTrace) {
      if (kDebugMode) {
        debugPrint('Error deleting mood entry: $error');
        debugPrint(stackTrace.toString());
      }
      rethrow;
    }
  }

  @override
  Future<void> clearAll() async {
    try {
      final db = await _db();
      await db.delete(_tableName);
    } catch (error, stackTrace) {
      if (kDebugMode) {
        debugPrint('Error clearing mood entries: $error');
        debugPrint(stackTrace.toString());
      }
      rethrow;
    }
  }
}

/// In-memory реализация для тестирования
class InMemoryMoodRepository implements MoodRepository {
  InMemoryMoodRepository();

  final List<MoodEntry> _entries = <MoodEntry>[];

  @override
  Future<List<MoodEntry>> fetchEntries() async {
    return List<MoodEntry>.from(_entries);
  }

  @override
  Future<void> upsertEntry(MoodEntry entry) async {
    final existingIndex = _entries.indexWhere((e) => e.id == entry.id);
    
    if (existingIndex != -1) {
      _entries[existingIndex] = entry;
    } else {
      _entries.add(entry);
    }
  }

  @override
  Future<void> deleteEntry(String id) async {
    _entries.removeWhere((entry) => entry.id == id);
  }

  @override
  Future<void> clearAll() async {
    _entries.clear();
  }
}
