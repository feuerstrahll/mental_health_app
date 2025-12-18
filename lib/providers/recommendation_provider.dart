import 'package:flutter/foundation.dart';
import 'package:provider/provider.dart';

import '../core/models/intervention.dart';
import '../core/services/recommendation_service.dart';
import '../core/services/feedback_service.dart';
import 'mood_provider.dart';

/// Provider для управления рекомендациями и обратной связью
class RecommendationProvider extends ChangeNotifier {
  RecommendationProvider({
    required RecommendationService recommendationService,
    required FeedbackService feedbackService,
  })  : _recommendationService = recommendationService,
        _feedbackService = feedbackService;

  final RecommendationService _recommendationService;
  final FeedbackService _feedbackService;

  List<Intervention> _currentRecommendations = [];
  bool _isLoading = false;
  String? _errorMessage;

  List<Intervention> get currentRecommendations =>
      UnmodifiableListView(_currentRecommendations);
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  /// Загружает рекомендации на основе текущего состояния
  Future<void> loadRecommendations(BuildContext context) async {
    _setLoading(true);
    _clearError();

    try {
      final moodProvider = context.read<MoodProvider>();
      final entries = moodProvider.entries;

      if (entries.isEmpty) {
        _currentRecommendations = [];
        notifyListeners();
        return;
      }

      // Получаем последнюю запись для текущего состояния
      final latestEntry = entries.first;
      final recentEntries = entries.take(7).toList();

      _currentRecommendations = await _recommendationService.getRecommendations(
        recentEntries: recentEntries,
        currentEmotion: latestEntry.emotion,
        currentStressLevel: latestEntry.stressLevel,
        maxRecommendations: 5,
      );

      notifyListeners();
    } catch (error, stackTrace) {
      _handleError('Failed to load recommendations', error, stackTrace);
    } finally {
      _setLoading(false);
    }
  }

  /// Загружает рекомендации на основе паттернов
  Future<void> loadRecommendationsForPattern(BuildContext context) async {
    _setLoading(true);
    _clearError();

    try {
      final moodProvider = context.read<MoodProvider>();
      final entries = moodProvider.entries;

      _currentRecommendations =
          await _recommendationService.getRecommendationsForPattern(
        recentEntries: entries,
      );

      notifyListeners();
    } catch (error, stackTrace) {
      _handleError('Failed to load recommendations', error, stackTrace);
    } finally {
      _setLoading(false);
    }
  }

  /// Сохраняет обратную связь о вмешательстве
  Future<void> submitFeedback({
    required String interventionId,
    required bool wasHelpful,
    required String emotion,
    required int stressLevel,
    int? moodBefore,
    int? moodAfter,
    String? note,
  }) async {
    try {
      final feedback = InterventionFeedback(
        id: 'feedback_${DateTime.now().millisecondsSinceEpoch}',
        interventionId: interventionId,
        timestamp: DateTime.now(),
        wasHelpful: wasHelpful,
        moodBefore: moodBefore,
        moodAfter: moodAfter,
        note: note,
        emotion: emotion,
        stressLevel: stressLevel,
      );

      await _feedbackService.saveFeedback(feedback);

      // Перезагружаем рекомендации, чтобы учесть новую обратную связь
      notifyListeners();
    } catch (error, stackTrace) {
      _handleError('Failed to submit feedback', error, stackTrace);
      rethrow;
    }
  }

  /// Получает статистику эффективности вмешательств
  Future<Map<String, InterventionStats>> getInterventionStats() async {
    try {
      return await _feedbackService.getUserInterventionStats();
    } catch (error, stackTrace) {
      _handleError('Failed to get intervention stats', error, stackTrace);
      return {};
    }
  }

  /// Получает наиболее эффективные вмешательства
  Future<List<String>> getMostEffectiveInterventions() async {
    try {
      return await _feedbackService.getMostEffectiveInterventions();
    } catch (error, stackTrace) {
      _handleError('Failed to get effective interventions', error, stackTrace);
      return [];
    }
  }

  void _setLoading(bool value) {
    if (_isLoading == value) return;
    _isLoading = value;
    notifyListeners();
  }

  void _handleError(String message, Object error, StackTrace stackTrace) {
    _errorMessage = '$message: $error';
    if (kDebugMode) {
      debugPrint(_errorMessage);
      debugPrint(stackTrace.toString());
    }
    notifyListeners();
  }

  void _clearError() {
    _errorMessage = null;
  }
}

