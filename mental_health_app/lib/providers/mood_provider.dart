// lib/providers/mood_provider.dart
//
// Integration roadmap:
// 1. Vera implements MoodRepository using Hive (or another local database).
// 2. Alena consumes MoodProvider from the UI layer to read/write diary data.
// 3. Nastya wires the provider into the widget tree (see main.dart) and coordinates data flow.
// 4. Later, TensorFlow Lite can be added on top of the provider for mood prediction.

import 'dart:collection';
import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';

import '../core/constants/app_constants.dart';
import '../core/services/ml_service.dart';

/// Represents a single mood diary entry.
///
/// NOTE: Person B will eventually replace this stub with a richer model,
/// ideally moved into `lib/models/mood_entry.dart` and annotated for Hive.
class MoodEntry {
  MoodEntry({
    required this.id,
    required this.emotion,
    required this.stressLevel,
    required this.timestamp,
    this.note,
  }) : assert(
         stressLevel >= AppConstants.minStressLevel &&
             stressLevel <= AppConstants.maxStressLevel,
         'Stress level must be between ${AppConstants.minStressLevel} and ${AppConstants.maxStressLevel}',
       );

  final String id;
  final String emotion;
  final int stressLevel;
  final DateTime timestamp;
  final String? note;

  MoodEntry copyWith({
    String? emotion,
    int? stressLevel,
    DateTime? timestamp,
    String? note,
  }) {
    return MoodEntry(
      id: id,
      emotion: emotion ?? this.emotion,
      stressLevel: stressLevel ?? this.stressLevel,
      timestamp: timestamp ?? this.timestamp,
      note: note ?? this.note,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'id': id,
      'emotion': emotion,
      'stressLevel': stressLevel,
      'timestamp': timestamp.toIso8601String(),
      'note': note,
    };
  }

  factory MoodEntry.fromJson(Map<String, dynamic> json) {
    return MoodEntry(
      id: json['id'] as String,
      emotion: json['emotion'] as String,
      stressLevel: json['stressLevel'] as int,
      timestamp: DateTime.parse(json['timestamp'] as String),
      note: json['note'] as String?,
    );
  }
}

/// Contract that connects the provider with the persistence layer.
///
/// Person B should provide a Hive-based implementation that satisfies
/// this interface. During development, an in-memory implementation is
/// sufficient for widgets tests.
abstract class MoodRepository {
  Future<List<MoodEntry>> fetchEntries();
  Future<void> upsertEntry(MoodEntry entry);
  Future<void> deleteEntry(String id);
  Future<void> clearAll();
}

class MoodProvider extends ChangeNotifier {
  MoodProvider({required MoodRepository repository}) : _repository = repository;

  static const String diaryOnboardingInsight =
      'Заполняй свои данные каждый день и следи за прогрессом, а я помогу тебе замечать изменения в привычках.';
  static const String diaryNeedsMoreDataInsight =
      'Нужно ещё немного данных. После нескольких записей здесь появятся наблюдения за твоими привычками.';

  final MoodRepository _repository;
  final List<MoodEntry> _entries = <MoodEntry>[];
  MLService? _mlService;
  String? _cachedDiaryInsight;
  String? _cachedDiaryInsightSignature;

  bool _isLoading = false;
  bool _hasError = false;
  String? _errorMessage;

  UnmodifiableListView<MoodEntry> get entries => UnmodifiableListView(_entries);
  bool get isLoading => _isLoading;
  bool get hasError => _hasError;
  String? get errorMessage => _errorMessage;

  /// Loads diary entries from the repository.
  Future<void> loadEntries() async {
    if (_isLoading) return;
    _setLoading(true);
    _clearError();

    try {
      final fetched = await _repository.fetchEntries();
      _entries
        ..clear()
        ..addAll(fetched);
      _entries.sort((a, b) => b.timestamp.compareTo(a.timestamp));
      refreshDiaryInsight(notify: false);
    } catch (error, stackTrace) {
      _handleError('Failed to load mood entries', error, stackTrace);
    } finally {
      _setLoading(false);
    }
  }

  /// Adds a new diary entry and persists it.
  Future<MoodEntry> addEntry({
    required String emotion,
    required int stressLevel,
    String? note,
    DateTime? timestamp,
  }) async {
    final entry = MoodEntry(
      id: _generateId(),
      emotion: emotion,
      stressLevel: stressLevel,
      note: note,
      timestamp: timestamp ?? DateTime.now(),
    );

    try {
      await _repository.upsertEntry(entry);
      _entries.add(entry);
      _entries.sort((a, b) => b.timestamp.compareTo(a.timestamp));
      refreshDiaryInsight(notify: false);
      notifyListeners();
      return entry;
    } catch (error, stackTrace) {
      _handleError('Failed to add mood entry', error, stackTrace);
      rethrow;
    }
  }

  /// Updates an existing entry. Throws if the entry is not found.
  Future<void> updateEntry(MoodEntry updated) async {
    final index = _entries.indexWhere((entry) => entry.id == updated.id);
    if (index == -1) {
      throw ArgumentError('Entry with id ${updated.id} not found');
    }

    try {
      await _repository.upsertEntry(updated);
      _entries[index] = updated;
      _entries.sort((a, b) => b.timestamp.compareTo(a.timestamp));
      refreshDiaryInsight(notify: false);
      notifyListeners();
    } catch (error, stackTrace) {
      _handleError('Failed to update mood entry', error, stackTrace);
      rethrow;
    }
  }

  /// Deletes an entry by id.
  Future<void> deleteEntry(String id) async {
    final index = _entries.indexWhere((entry) => entry.id == id);
    if (index == -1) {
      return;
    }

    try {
      await _repository.deleteEntry(id);
      _entries.removeAt(index);
      refreshDiaryInsight(notify: false);
      notifyListeners();
    } catch (error, stackTrace) {
      _handleError('Failed to delete mood entry', error, stackTrace);
      rethrow;
    }
  }

  /// Clears the entire diary (with confirmation in UI).
  Future<void> clearDiary() async {
    try {
      await _repository.clearAll();
      _entries.clear();
      refreshDiaryInsight(notify: false);
      notifyListeners();
    } catch (error, stackTrace) {
      _handleError('Failed to clear diary', error, stackTrace);
      rethrow;
    }
  }

  /// Filters entries within an inclusive date range.
  List<MoodEntry> filterByDateRange(DateTime start, DateTime end) {
    final normalizedStart = DateTime(start.year, start.month, start.day);
    final normalizedEnd = DateTime(end.year, end.month, end.day, 23, 59, 59);
    return _entries
        .where(
          (entry) =>
              entry.timestamp.isAfter(
                normalizedStart.subtract(const Duration(seconds: 1)),
              ) &&
              entry.timestamp.isBefore(
                normalizedEnd.add(const Duration(seconds: 1)),
              ),
        )
        .toList();
  }

  /// Filters entries by emotion keyword.
  List<MoodEntry> filterByEmotion(String emotion) {
    final query = emotion.toLowerCase();
    return _entries
        .where((entry) => entry.emotion.toLowerCase() == query)
        .toList();
  }

  /// Filters entries by stress level range.
  List<MoodEntry> filterByStressLevel({int? minLevel, int? maxLevel}) {
    final minValue = minLevel ?? AppConstants.minStressLevel;
    final maxValue = maxLevel ?? AppConstants.maxStressLevel;
    return _entries
        .where(
          (entry) =>
              entry.stressLevel >= minValue && entry.stressLevel <= maxValue,
        )
        .toList();
  }

  /// Returns the latest entry if available.
  MoodEntry? get latestEntry => _entries.isEmpty ? null : _entries.first;

  /// Returns the average stress level across all entries.
  double? get averageStressLevel {
    if (_entries.isEmpty) return null;
    final total = _entries.fold<int>(
      0,
      (sum, entry) => sum + entry.stressLevel,
    );
    return total / _entries.length;
  }

  /// Calculates the average stress level for a given collection.
  double? averageStressFor(List<MoodEntry> entries) {
    if (entries.isEmpty) return null;
    final total = entries.fold<int>(0, (sum, entry) => sum + entry.stressLevel);
    return total / entries.length;
  }

  /// Returns emotion distribution as a percentage (0-100).
  Map<String, double> get emotionDistribution {
    if (_entries.isEmpty) return const <String, double>{};

    final counts = <String, int>{};
    for (final entry in _entries) {
      counts.update(entry.emotion, (value) => value + 1, ifAbsent: () => 1);
    }

    return counts.map((emotion, count) {
      final percentage = (count / _entries.length) * 100;
      return MapEntry(emotion, double.parse(percentage.toStringAsFixed(1)));
    });
  }

  /// Produces simple textual observations based on recent data.
  List<String> generateObservations({int lookbackDays = 7}) {
    if (_entries.isEmpty) return const <String>[];

    final now = DateTime.now();
    final recentEntries = filterByDateRange(
      now.subtract(Duration(days: lookbackDays)),
      now,
    );
    if (recentEntries.isEmpty) return const <String>[];

    final observations = <String>[];
    final average = averageStressFor(recentEntries);
    if (average != null) {
      observations.add(
        'Average stress over the last $lookbackDays days: ${average.toStringAsFixed(1)}',
      );
    }

    final distribution = _emotionDistributionFor(recentEntries);
    if (distribution.isNotEmpty) {
      final topEmotion = distribution.entries.reduce(
        (a, b) => a.value >= b.value ? a : b,
      );
      observations.add(
        'Most common emotion: ${topEmotion.key} (${topEmotion.value.toStringAsFixed(1)}%)',
      );
    }

    return observations;
  }

  /// Returns a short cached local diary insight for the Diary page.
  ///
  /// This method is intentionally deterministic and local-only. A future LLM
  /// implementation should update this cache after a saved entry or manual
  /// refresh, never from a widget build.
  String getDiaryInsight({int lookbackDays = 7}) {
    if (_entries.isEmpty) return diaryOnboardingInsight;
    if (_entries.length < 3) return diaryNeedsMoreDataInsight;

    final signature = _diaryInsightSignature(lookbackDays: lookbackDays);
    if (_cachedDiaryInsight != null &&
        _cachedDiaryInsightSignature == signature) {
      return _cachedDiaryInsight!;
    }

    _cachedDiaryInsight = _buildLocalDiaryInsight(lookbackDays: lookbackDays);
    _cachedDiaryInsightSignature = signature;
    return _cachedDiaryInsight!;
  }

  void refreshDiaryInsight({int lookbackDays = 7, bool notify = true}) {
    _cachedDiaryInsight = _entries.length < 3
        ? null
        : _buildLocalDiaryInsight(lookbackDays: lookbackDays);
    _cachedDiaryInsightSignature = _entries.length < 3
        ? null
        : _diaryInsightSignature(lookbackDays: lookbackDays);
    if (notify) notifyListeners();
  }

  /// Exports all mood entries into a JSON file for external ML training.
  Future<String> exportDataForML() async {
    try {
      final entries = await _repository.fetchEntries();
      if (entries.isEmpty) {
        return 'No mood entries to export yet';
      }

      final jsonList = entries.map((entry) => entry.toJson()).toList();
      final directory = await getApplicationDocumentsDirectory();
      final timestamp = DateTime.now().toIso8601String().replaceAll(':', '-');
      final file = File('${directory.path}/mood_export_$timestamp.json');
      await file.writeAsString(jsonEncode(jsonList), flush: true);

      return 'Exported ${entries.length} entries to:\n${file.path}';
    } catch (error, stackTrace) {
      _handleError('Failed to export mood data', error, stackTrace);
      return 'Export failed: $error';
    }
  }

  /// Предсказание следующего настроения с использованием ML
  Future<Map<String, double>> predictNextMood() async {
    if (_entries.length < 3) {
      return {};
    }

    // Lazy load ML service
    try {
      final mlService = await _getMLService();
      return await mlService.predictNextMood(_entries);
    } catch (e) {
      if (kDebugMode) {
        debugPrint('ML prediction failed: $e');
      }
      return {};
    }
  }

  /// Получение рекомендованной категории советов
  String getRecommendedTipCategory() {
    if (_entries.isEmpty) return 'general';

    try {
      // Используем синхронный анализ для быстрого ответа
      final recent = _entries.take(7).toList();
      final avgStress =
          recent.fold<int>(0, (sum, e) => sum + e.stressLevel) / recent.length;

      if (avgStress > 7) return 'stress_management';
      if (avgStress > 5) return 'relaxation';
      if (avgStress < 3) return 'positive_habits';
      return 'general';
    } catch (e) {
      return 'general';
    }
  }

  // Lazy ML service loader
  Future<MLService> _getMLService() async {
    _mlService ??= MLService();
    await _mlService!.initialize();
    return _mlService!;
  }

  @override
  void dispose() {
    _mlService?.dispose();
    super.dispose();
  }

  void _setLoading(bool value) {
    if (_isLoading == value) return;
    _isLoading = value;
    notifyListeners();
  }

  void _handleError(String message, Object error, StackTrace stackTrace) {
    _hasError = true;
    _errorMessage = '$message: $error';
    if (kDebugMode) {
      debugPrint(_errorMessage);
      debugPrint(stackTrace.toString());
    }
    notifyListeners();
  }

  void _clearError() {
    _hasError = false;
    _errorMessage = null;
  }

  String _generateId() {
    final milliseconds = DateTime.now().millisecondsSinceEpoch;
    final randomSuffix = Random().nextInt(9999).toString().padLeft(4, '0');
    return 'mood_$milliseconds$randomSuffix';
  }

  Map<String, double> _emotionDistributionFor(List<MoodEntry> entries) {
    if (entries.isEmpty) return <String, double>{};

    final counts = <String, int>{};
    for (final entry in entries) {
      counts.update(entry.emotion, (value) => value + 1, ifAbsent: () => 1);
    }

    return counts.map((emotion, count) {
      final percentage = (count / entries.length) * 100;
      return MapEntry(emotion, percentage);
    });
  }

  String _buildLocalDiaryInsight({required int lookbackDays}) {
    final now = DateTime.now();
    final recentEntries = filterByDateRange(
      now.subtract(Duration(days: lookbackDays)),
      now,
    );
    final sourceEntries = recentEntries.length >= 3
        ? recentEntries
        : _entries.take(lookbackDays).toList();
    final averageStress = averageStressFor(sourceEntries);
    final distribution = _emotionDistributionFor(sourceEntries);

    final parts = <String>[];
    if (distribution.isNotEmpty) {
      final topEmotion = distribution.entries.reduce(
        (a, b) => a.value >= b.value ? a : b,
      );
      parts.add('чаще отмечалось состояние «${_emotionLabel(topEmotion.key)}»');
    }
    if (averageStress != null) {
      if (averageStress >= 7) {
        parts.add('уровень напряжения был повышенным');
      } else if (averageStress <= 3) {
        parts.add('уровень напряжения оставался низким');
      } else {
        parts.add('уровень напряжения был умеренным');
      }
    }

    final observation = parts.isEmpty
        ? 'За последние $lookbackDays дней уже появились первые данные для наблюдения.'
        : 'За последние $lookbackDays дней ${parts.join(', ')}.';
    return '$observation Продолжай заполнять дневник, чтобы точнее замечать изменения в привычках.';
  }

  String _diaryInsightSignature({required int lookbackDays}) {
    final ids = _entries
        .take(lookbackDays)
        .map(
          (entry) =>
              '${entry.id}:${entry.timestamp.toIso8601String()}:${entry.emotion}:${entry.stressLevel}:${entry.note ?? ''}',
        )
        .join('|');
    return '$lookbackDays:$ids';
  }

  String _emotionLabel(String emotion) {
    switch (emotion.toLowerCase()) {
      case 'happy':
        return 'хорошо';
      case 'sad':
        return 'грустно';
      case 'anxious':
        return 'тревожно';
      case 'calm':
        return 'спокойно';
      case 'angry':
        return 'злость';
      case 'neutral':
        return 'нейтрально';
      default:
        return emotion;
    }
  }
}
