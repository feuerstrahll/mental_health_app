/// Модель вмешательства (рекомендации)
class Intervention {
  final String id;
  final String title;
  final String description;
  final InterventionType type;
  final List<String> triggers; // Эмоции/состояния, при которых показывается
  final int minStressLevel; // Минимальный уровень стресса для показа
  final int maxStressLevel; // Максимальный уровень стресса для показа
  final Duration estimatedDuration;
  final String? icon;

  Intervention({
    required this.id,
    required this.title,
    required this.description,
    required this.type,
    required this.triggers,
    this.minStressLevel = 0,
    this.maxStressLevel = 10,
    this.estimatedDuration = const Duration(minutes: 5),
    this.icon,
  });
}

enum InterventionType {
  breathing,      // Дыхательные упражнения
  meditation,      // Медитация
  journaling,     // Ведение дневника
  exercise,       // Физические упражнения
  music,          // Музыка
  nature,         // Природа/прогулка
  social,         // Социальное взаимодействие
  sleep,          // Сон/отдых
  mindfulness,    // Осознанность
  other,          // Другое
}

/// Модель обратной связи пользователя
class InterventionFeedback {
  final String id;
  final String interventionId;
  final DateTime timestamp;
  final bool wasHelpful; // true = помогло, false = не помогло
  final int? moodBefore; // Настроение до (1-10)
  final int? moodAfter; // Настроение после (1-10)
  final String? note; // Дополнительные заметки
  final String emotion; // Эмоция, при которой использовалось
  final int stressLevel; // Уровень стресса

  InterventionFeedback({
    required this.id,
    required this.interventionId,
    required this.timestamp,
    required this.wasHelpful,
    this.moodBefore,
    this.moodAfter,
    this.note,
    required this.emotion,
    required this.stressLevel,
  });

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'interventionId': interventionId,
      'timestamp': timestamp.toIso8601String(),
      'wasHelpful': wasHelpful,
      'moodBefore': moodBefore,
      'moodAfter': moodAfter,
      'note': note,
      'emotion': emotion,
      'stressLevel': stressLevel,
    };
  }

  factory InterventionFeedback.fromJson(Map<String, dynamic> json) {
    return InterventionFeedback(
      id: json['id'] as String,
      interventionId: json['interventionId'] as String,
      timestamp: DateTime.parse(json['timestamp'] as String),
      wasHelpful: json['wasHelpful'] as bool,
      moodBefore: json['moodBefore'] as int?,
      moodAfter: json['moodAfter'] as int?,
      note: json['note'] as String?,
      emotion: json['emotion'] as String,
      stressLevel: json['stressLevel'] as int,
    );
  }
}

/// Статистика эффективности вмешательства для пользователя
class InterventionStats {
  final String interventionId;
  final int totalUses;
  final int helpfulCount;
  final int notHelpfulCount;
  final double averageMoodImprovement; // Среднее улучшение настроения
  final Map<String, int> usesByEmotion; // Использования по эмоциям
  final DateTime lastUsed;

  InterventionStats({
    required this.interventionId,
    required this.totalUses,
    required this.helpfulCount,
    required this.notHelpfulCount,
    required this.averageMoodImprovement,
    required this.usesByEmotion,
    required this.lastUsed,
  });

  double get helpfulnessRate {
    if (totalUses == 0) return 0.0;
    return helpfulCount / totalUses;
  }

  bool get isEffective => helpfulnessRate >= 0.6 && totalUses >= 3;
}

