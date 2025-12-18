import 'dart:math';
import 'package:flutter/foundation.dart';

import '../models/intervention.dart';
import '../../providers/mood_provider.dart';
import 'feedback_service.dart';

/// Rule-based система рекомендаций с адаптацией на основе обратной связи
class RecommendationService {
  final FeedbackService _feedbackService;
  final Random _random = Random();

  RecommendationService(this._feedbackService);

  /// Получает рекомендации на основе текущего состояния пользователя
  Future<List<Intervention>> getRecommendations({
    required List<MoodEntry> recentEntries,
    required String currentEmotion,
    required int currentStressLevel,
    int maxRecommendations = 3,
  }) async {
    // Получаем все доступные вмешательства
    final allInterventions = _getAvailableInterventions();

    // Фильтруем по правилам (triggers, stress level)
    final ruleBasedMatches = allInterventions.where((intervention) {
      // Проверка уровня стресса
      if (currentStressLevel < intervention.minStressLevel ||
          currentStressLevel > intervention.maxStressLevel) {
        return false;
      }

      // Проверка триггеров (эмоций)
      if (intervention.triggers.isNotEmpty &&
          !intervention.triggers.contains(currentEmotion)) {
        return false;
      }

      return true;
    }).toList();

    // Получаем статистику эффективности для пользователя
    final userStats = await _feedbackService.getUserInterventionStats();

    // Сортируем по эффективности (collaborative filtering подход)
    final scoredInterventions = ruleBasedMatches.map((intervention) {
      final stats = userStats[intervention.id];
      double score = 0.5; // Базовый score

      if (stats != null) {
        // Увеличиваем score на основе helpfulness rate
        score = stats.helpfulnessRate;

        // Бонус за эффективность
        if (stats.isEffective) {
          score += 0.2;
        }

        // Небольшой бонус за недавнее использование (если помогло)
        final daysSinceLastUse =
            DateTime.now().difference(stats.lastUsed).inDays;
        if (daysSinceLastUse < 7 && stats.helpfulnessRate > 0.5) {
          score += 0.1;
        }

        // Штраф за неэффективность
        if (stats.helpfulnessRate < 0.3 && stats.totalUses >= 3) {
          score -= 0.3;
        }
      } else {
        // Для новых вмешательств даем небольшой бонус
        score = 0.6;
      }

      // Бонус для вмешательств, подходящих для текущей эмоции
      if (intervention.triggers.contains(currentEmotion)) {
        score += 0.15;
      }

      return MapEntry(intervention, score);
    }).toList();

    // Сортируем по score (от большего к меньшему)
    scoredInterventions.sort((a, b) => b.value.compareTo(a.value));

    // Выбираем топ рекомендации
    final topRecommendations = scoredInterventions
        .take(maxRecommendations)
        .map((e) => e.key)
        .toList();

    // Если рекомендаций меньше, чем нужно, добавляем случайные из подходящих
    if (topRecommendations.length < maxRecommendations) {
      final remaining = ruleBasedMatches
          .where((i) => !topRecommendations.contains(i))
          .toList();
      if (remaining.isNotEmpty) {
        remaining.shuffle(_random);
        topRecommendations.addAll(
          remaining.take(maxRecommendations - topRecommendations.length),
        );
      }
    }

    return topRecommendations;
  }

  /// Получает рекомендации на основе паттернов (высокая тревога, грусть и т.д.)
  Future<List<Intervention>> getRecommendationsForPattern({
    required List<MoodEntry> recentEntries,
    int lookbackDays = 7,
  }) async {
    if (recentEntries.isEmpty) {
      return _getDefaultRecommendations();
    }

    final recent = recentEntries.take(lookbackDays).toList();
    final avgStress = recent.fold<int>(0, (sum, e) => sum + e.stressLevel) /
        recent.length;

    // Определяем доминирующую эмоцию
    final emotionCounts = <String, int>{};
    for (final entry in recent) {
      emotionCounts[entry.emotion] =
          (emotionCounts[entry.emotion] ?? 0) + 1;
    }
    final dominantEmotion = emotionCounts.entries
        .reduce((a, b) => a.value > b.value ? a : b)
        .key;

    // Правила для рекомендаций
    if (avgStress >= 7 || dominantEmotion == 'Anxious') {
      return getRecommendations(
        recentEntries: recent,
        currentEmotion: 'Anxious',
        currentStressLevel: avgStress.round(),
      );
    } else if (dominantEmotion == 'Sad' || avgStress >= 5) {
      return getRecommendations(
        recentEntries: recent,
        currentEmotion: 'Sad',
        currentStressLevel: avgStress.round(),
      );
    } else if (dominantEmotion == 'Angry') {
      return getRecommendations(
        recentEntries: recent,
        currentEmotion: 'Angry',
        currentStressLevel: avgStress.round(),
      );
    }

    return _getDefaultRecommendations();
  }

  /// Получает все доступные вмешательства
  List<Intervention> _getAvailableInterventions() {
    return [
      // Дыхательные упражнения
      Intervention(
        id: 'breathing_478',
        title: 'Дыхание 4-7-8',
        description:
            'Вдохните на 4 счета, задержите на 7, выдохните на 8. Повторите 4 раза.',
        type: InterventionType.breathing,
        triggers: ['Anxious', 'Angry'],
        minStressLevel: 5,
        maxStressLevel: 10,
        estimatedDuration: const Duration(minutes: 5),
        icon: '🌬️',
      ),
      Intervention(
        id: 'breathing_box',
        title: 'Квадратное дыхание',
        description:
            'Вдох 4 сек, задержка 4 сек, выдох 4 сек, пауза 4 сек. Повторите 5 раз.',
        type: InterventionType.breathing,
        triggers: ['Anxious', 'Angry'],
        minStressLevel: 4,
        maxStressLevel: 10,
        estimatedDuration: const Duration(minutes: 3),
        icon: '🟦',
      ),

      // Медитация
      Intervention(
        id: 'meditation_body_scan',
        title: 'Сканирование тела',
        description:
            'Медленно направьте внимание на каждую часть тела, замечая ощущения без суждений.',
        type: InterventionType.meditation,
        triggers: ['Anxious', 'Sad'],
        minStressLevel: 4,
        maxStressLevel: 10,
        estimatedDuration: const Duration(minutes: 10),
        icon: '🧘',
      ),
      Intervention(
        id: 'meditation_mindfulness',
        title: 'Медитация осознанности',
        description:
            'Сядьте удобно, закройте глаза, сосредоточьтесь на дыхании. Когда мысли отвлекают, мягко верните внимание.',
        type: InterventionType.mindfulness,
        triggers: ['Anxious', 'Sad', 'Angry'],
        minStressLevel: 3,
        maxStressLevel: 10,
        estimatedDuration: const Duration(minutes: 5),
        icon: '🧘‍♀️',
      ),

      // Ведение дневника
      Intervention(
        id: 'journaling_gratitude',
        title: 'Дневник благодарности',
        description:
            'Запишите 3 вещи, за которые вы благодарны сегодня. Может быть что-то маленькое.',
        type: InterventionType.journaling,
        triggers: ['Sad'],
        minStressLevel: 0,
        maxStressLevel: 8,
        estimatedDuration: const Duration(minutes: 5),
        icon: '📝',
      ),
      Intervention(
        id: 'journaling_thoughts',
        title: 'Выплесните мысли',
        description:
            'Запишите все, что вас беспокоит, без фильтров. Просто дайте мыслям выйти на бумагу.',
        type: InterventionType.journaling,
        triggers: ['Anxious', 'Sad', 'Angry'],
        minStressLevel: 5,
        maxStressLevel: 10,
        estimatedDuration: const Duration(minutes: 10),
        icon: '✍️',
      ),

      // Физические упражнения
      Intervention(
        id: 'exercise_walk',
        title: 'Прогулка на свежем воздухе',
        description:
            'Выйдите на улицу и пройдитесь 10-15 минут. Обратите внимание на окружающий мир.',
        type: InterventionType.nature,
        triggers: ['Sad', 'Anxious'],
        minStressLevel: 0,
        maxStressLevel: 10,
        estimatedDuration: const Duration(minutes: 15),
        icon: '🚶',
      ),
      Intervention(
        id: 'exercise_stretch',
        title: 'Растяжка',
        description:
            'Выполните простые упражнения на растяжку: наклоны, повороты, потягивания.',
        type: InterventionType.exercise,
        triggers: ['Anxious', 'Angry'],
        minStressLevel: 4,
        maxStressLevel: 10,
        estimatedDuration: const Duration(minutes: 5),
        icon: '🤸',
      ),

      // Музыка
      Intervention(
        id: 'music_calm',
        title: 'Спокойная музыка',
        description:
            'Включите спокойную музыку или звуки природы. Закройте глаза и просто слушайте.',
        type: InterventionType.music,
        triggers: ['Anxious', 'Angry'],
        minStressLevel: 4,
        maxStressLevel: 10,
        estimatedDuration: const Duration(minutes: 10),
        icon: '🎵',
      ),
      Intervention(
        id: 'music_energizing',
        title: 'Энергичная музыка',
        description:
            'Включите любимую музыку, которая поднимает настроение. Можно подвигаться под неё.',
        type: InterventionType.music,
        triggers: ['Sad'],
        minStressLevel: 0,
        maxStressLevel: 7,
        estimatedDuration: const Duration(minutes: 10),
        icon: '🎶',
      ),

      // Социальное
      Intervention(
        id: 'social_call',
        title: 'Позвоните близкому',
        description:
            'Позвоните другу или члену семьи. Просто поговорите о чем угодно.',
        type: InterventionType.social,
        triggers: ['Sad'],
        minStressLevel: 0,
        maxStressLevel: 8,
        estimatedDuration: const Duration(minutes: 15),
        icon: '📞',
      ),

      // Сон/отдых
      Intervention(
        id: 'rest_break',
        title: 'Короткий перерыв',
        description:
            'Отложите дела на 10 минут. Закройте глаза, дышите глубоко, просто отдохните.',
        type: InterventionType.sleep,
        triggers: ['Anxious', 'Angry'],
        minStressLevel: 5,
        maxStressLevel: 10,
        estimatedDuration: const Duration(minutes: 10),
        icon: '😴',
      ),

      // Универсальные
      Intervention(
        id: 'general_mindful_moment',
        title: 'Момент осознанности',
        description:
            'Остановитесь на минуту. Что вы видите? Слышите? Чувствуете? Просто будьте здесь и сейчас.',
        type: InterventionType.mindfulness,
        triggers: [], // Подходит для всех
        minStressLevel: 0,
        maxStressLevel: 10,
        estimatedDuration: const Duration(minutes: 2),
        icon: '🌿',
      ),
    ];
  }

  /// Получает рекомендации по умолчанию
  List<Intervention> _getDefaultRecommendations() {
    return [
      _getAvailableInterventions().firstWhere(
        (i) => i.id == 'general_mindful_moment',
      ),
      _getAvailableInterventions().firstWhere(
        (i) => i.id == 'breathing_478',
      ),
      _getAvailableInterventions().firstWhere(
        (i) => i.id == 'meditation_mindfulness',
      ),
    ];
  }
}

