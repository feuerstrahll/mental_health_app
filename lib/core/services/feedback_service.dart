import 'dart:collection';
import 'package:flutter/foundation.dart';

import '../models/intervention.dart';
import '../../core/services/database_service.dart';
import 'package:sqflite_sqlcipher/sqflite.dart';

/// Сервис для отслеживания обратной связи пользователя о вмешательствах
class FeedbackService {
  final DatabaseService _databaseService;

  FeedbackService(this._databaseService);

  static const String _tableName = 'intervention_feedback';

  Future<Database> _db() => _databaseService.database;

  /// Инициализация таблицы для обратной связи
  Future<void> initialize() async {
    final db = await _db();
    await db.execute('''
      CREATE TABLE IF NOT EXISTS $_tableName (
        id TEXT PRIMARY KEY,
        intervention_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        was_helpful INTEGER NOT NULL,
        mood_before INTEGER,
        mood_after INTEGER,
        note TEXT,
        emotion TEXT NOT NULL,
        stress_level INTEGER NOT NULL
      )
    ''');
    
    await db.execute('''
      CREATE INDEX IF NOT EXISTS idx_intervention_id 
      ON $_tableName(intervention_id)
    ''');
    
    await db.execute('''
      CREATE INDEX IF NOT EXISTS idx_timestamp 
      ON $_tableName(timestamp)
    ''');
  }

  /// Сохраняет обратную связь о вмешательстве
  Future<void> saveFeedback(InterventionFeedback feedback) async {
    try {
      final db = await _db();
      await db.insert(
        _tableName,
        {
          'id': feedback.id,
          'intervention_id': feedback.interventionId,
          'timestamp': feedback.timestamp.toIso8601String(),
          'was_helpful': feedback.wasHelpful ? 1 : 0,
          'mood_before': feedback.moodBefore,
          'mood_after': feedback.moodAfter,
          'note': feedback.note,
          'emotion': feedback.emotion,
          'stress_level': feedback.stressLevel,
        },
        conflictAlgorithm: ConflictAlgorithm.replace,
      );
    } catch (error, stackTrace) {
      if (kDebugMode) {
        debugPrint('Error saving feedback: $error');
        debugPrint(stackTrace.toString());
      }
      rethrow;
    }
  }

  /// Получает всю обратную связь пользователя
  Future<List<InterventionFeedback>> getAllFeedback() async {
    try {
      final db = await _db();
      final rows = await db.query(
        _tableName,
        orderBy: 'timestamp DESC',
      );

      return rows.map((row) {
        return InterventionFeedback.fromJson({
          'id': row['id'] as String,
          'interventionId': row['intervention_id'] as String,
          'timestamp': row['timestamp'] as String,
          'wasHelpful': (row['was_helpful'] as int) == 1,
          'moodBefore': row['mood_before'] as int?,
          'moodAfter': row['mood_after'] as int?,
          'note': row['note'] as String?,
          'emotion': row['emotion'] as String,
          'stressLevel': row['stress_level'] as int,
        });
      }).toList();
    } catch (error, stackTrace) {
      if (kDebugMode) {
        debugPrint('Error fetching feedback: $error');
        debugPrint(stackTrace.toString());
      }
      return [];
    }
  }

  /// Получает статистику эффективности вмешательств для пользователя
  Future<Map<String, InterventionStats>> getUserInterventionStats() async {
    final allFeedback = await getAllFeedback();
    final statsMap = <String, InterventionStats>{};

    // Группируем по interventionId
    final feedbackByIntervention = <String, List<InterventionFeedback>>{};
    for (final feedback in allFeedback) {
      feedbackByIntervention.putIfAbsent(
        feedback.interventionId,
        () => [],
      ).add(feedback);
    }

    // Вычисляем статистику для каждого вмешательства
    for (final entry in feedbackByIntervention.entries) {
      final interventionId = entry.key;
      final feedbacks = entry.value;

      final helpfulCount =
          feedbacks.where((f) => f.wasHelpful).length;
      final notHelpfulCount = feedbacks.length - helpfulCount;

      // Вычисляем среднее улучшение настроения
      double moodImprovementSum = 0.0;
      int moodImprovementCount = 0;
      for (final feedback in feedbacks) {
        if (feedback.moodBefore != null && feedback.moodAfter != null) {
          moodImprovementSum +=
              (feedback.moodAfter! - feedback.moodBefore!).toDouble();
          moodImprovementCount++;
        }
      }
      final averageMoodImprovement = moodImprovementCount > 0
          ? moodImprovementSum / moodImprovementCount
          : 0.0;

      // Использования по эмоциям
      final usesByEmotion = <String, int>{};
      for (final feedback in feedbacks) {
        usesByEmotion[feedback.emotion] =
            (usesByEmotion[feedback.emotion] ?? 0) + 1;
      }

      // Последнее использование
      final lastUsed = feedbacks
          .map((f) => f.timestamp)
          .reduce((a, b) => a.isAfter(b) ? a : b);

      statsMap[interventionId] = InterventionStats(
        interventionId: interventionId,
        totalUses: feedbacks.length,
        helpfulCount: helpfulCount,
        notHelpfulCount: notHelpfulCount,
        averageMoodImprovement: averageMoodImprovement,
        usesByEmotion: usesByEmotion,
        lastUsed: lastUsed,
      );
    }

    return statsMap;
  }

  /// Получает статистику для конкретного вмешательства
  Future<InterventionStats?> getInterventionStats(String interventionId) async {
    final allStats = await getUserInterventionStats();
    return allStats[interventionId];
  }

  /// Получает наиболее эффективные вмешательства для пользователя
  Future<List<String>> getMostEffectiveInterventions({
    int limit = 5,
  }) async {
    final allStats = await getUserInterventionStats();
    final sorted = allStats.values.toList()
      ..sort((a, b) {
        // Сортируем по helpfulness rate, затем по количеству использований
        final rateComparison = b.helpfulnessRate.compareTo(a.helpfulnessRate);
        if (rateComparison != 0) return rateComparison;
        return b.totalUses.compareTo(a.totalUses);
      });

    return sorted
        .where((stats) => stats.totalUses >= 2) // Минимум 2 использования
        .take(limit)
        .map((stats) => stats.interventionId)
        .toList();
  }

  /// Получает наименее эффективные вмешательства (для исключения из рекомендаций)
  Future<List<String>> getLeastEffectiveInterventions({
    int limit = 3,
  }) async {
    final allStats = await getUserInterventionStats();
    final sorted = allStats.values.toList()
      ..sort((a, b) {
        // Сортируем по низкому helpfulness rate
        final rateComparison = a.helpfulnessRate.compareTo(b.helpfulnessRate);
        if (rateComparison != 0) return rateComparison;
        return b.totalUses.compareTo(a.totalUses);
      });

    return sorted
        .where((stats) =>
            stats.totalUses >= 3 &&
            stats.helpfulnessRate < 0.3) // Низкая эффективность
        .take(limit)
        .map((stats) => stats.interventionId)
        .toList();
  }

  /// Удаляет обратную связь
  Future<void> deleteFeedback(String feedbackId) async {
    try {
      final db = await _db();
      await db.delete(
        _tableName,
        where: 'id = ?',
        whereArgs: [feedbackId],
      );
    } catch (error, stackTrace) {
      if (kDebugMode) {
        debugPrint('Error deleting feedback: $error');
        debugPrint(stackTrace.toString());
      }
      rethrow;
    }
  }

  /// Очищает всю обратную связь
  Future<void> clearAllFeedback() async {
    try {
      final db = await _db();
      await db.delete(_tableName);
    } catch (error, stackTrace) {
      if (kDebugMode) {
        debugPrint('Error clearing feedback: $error');
        debugPrint(stackTrace.toString());
      }
      rethrow;
    }
  }
}

