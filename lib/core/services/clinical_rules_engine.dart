import '../../providers/mood_provider.dart';

enum RiskLevel { normal, elevated, high, crisis }

class ClinicalAssessment {
  const ClinicalAssessment({
    required this.riskLevel,
    required this.primaryPattern,
    required this.phq2Score,
    required this.gad2Score,
    required this.requiresEscalation,
    required this.triggerReasons,
  });

  final RiskLevel riskLevel;
  final String primaryPattern;
  final double phq2Score;
  final double gad2Score;
  final bool requiresEscalation;
  final List<String> triggerReasons;
}

/// On-device clinical rules: PHQ-2 / GAD-2 screening + crisis + stress pattern.
/// Правила проверяются строго сверху вниз — первое сработавшее определяет [RiskLevel].
class ClinicalRulesEngine {
  static const int minContextDays = 14;
  static const int maxContextDays = 28;

  /// Основной API: оценка по записям дневника (лучше последние 14–28 дней, хронология не обязательна — будет отсортировано).
  ClinicalAssessment assess(List<MoodEntry> entries) {
    if (entries.isEmpty) {
      return const ClinicalAssessment(
        riskLevel: RiskLevel.normal,
        primaryPattern: 'no_data',
        phq2Score: 0,
        gad2Score: 0,
        requiresEscalation: false,
        triggerReasons: <String>[],
      );
    }

    final last14 = _filterLastDays(entries, 14);
    final last7 = _filterLastDays(entries, 7);

    final phq2 = _computePhq2Score(last14);
    final gad2 = _computeGad2Score(last14);

    // --- Правило 0: детектор кризиса (приоритет максимальный) ---
    final crisis = _rule0Crisis(last7: last7, last14: last14);
    if (crisis != null) {
      return ClinicalAssessment(
        riskLevel: RiskLevel.crisis,
        primaryPattern: 'crisis_pattern',
        phq2Score: phq2,
        gad2Score: gad2,
        requiresEscalation: true,
        triggerReasons: crisis,
      );
    }

    // --- Правило 1: PHQ-2 скрининг депрессии ---
    if (phq2 >= 3) {
      return ClinicalAssessment(
        riskLevel: RiskLevel.high,
        primaryPattern: 'depressive_pattern',
        phq2Score: phq2,
        gad2Score: gad2,
        requiresEscalation: false,
        triggerReasons: <String>['phq2_positive_screening'],
      );
    }

    // --- Правило 2: GAD-2 скрининг тревоги ---
    if (gad2 >= 3) {
      return ClinicalAssessment(
        riskLevel: RiskLevel.elevated,
        primaryPattern: 'anxiety_pattern',
        phq2Score: phq2,
        gad2Score: gad2,
        requiresEscalation: false,
        triggerReasons: <String>['gad2_positive_screening'],
      );
    }

    // --- Правило 3: хронический стресс (PSS-inspired) ---
    final avgStress = _averageStressInt(last14);
    final highChronicStress = avgStress > 6.5 && last14.length >= 10;
    final stressTrendUp =
        _isIncreasingTrend(last14.map((e) => e.stressLevel).toList());
    if (highChronicStress && stressTrendUp) {
      return ClinicalAssessment(
        riskLevel: RiskLevel.elevated,
        primaryPattern: 'chronic_stress',
        phq2Score: phq2,
        gad2Score: gad2,
        requiresEscalation: false,
        triggerReasons: <String>['chronic_stress_rising_trend'],
      );
    }

    return ClinicalAssessment(
      riskLevel: RiskLevel.normal,
      primaryPattern: 'no_clinical_pattern',
      phq2Score: phq2,
      gad2Score: gad2,
      requiresEscalation: false,
      triggerReasons: <String>[],
    );
  }

  /// Совместимость со старым именем.
  ClinicalAssessment evaluate(List<MoodEntry> entries) => assess(entries);

  // ---------------------------------------------------------------------------
  // Правило 0
  // ---------------------------------------------------------------------------

  /// Возвращает список причин кризиса или null, если кризис не выявлен.
  List<String>? _rule0Crisis({
    required List<MoodEntry> last7,
    required List<MoodEntry> last14,
  }) {
    final reasons = <String>[];

    if (last7.any((e) => e.stressLevel == 10)) {
      reasons.add('max_stress_in_last_7_days');
    }

    final last14Chrono = _chronological(last14);
    if (_hasSadConsecutiveStressStreak(last14Chrono, minLength: 3, minStress: 8)) {
      reasons.add('three_consecutive_sad_high_stress');
    }

    final sadCount14 = last14.where((e) => _isSad(e.emotion)).length;
    if (sadCount14 > 10) {
      reasons.add('excessive_sad_entries_14d');
    }

    if (reasons.isEmpty) return null;
    return reasons;
  }

  bool _hasSadConsecutiveStressStreak(
    List<MoodEntry> chronological, {
    required int minLength,
    required int minStress,
  }) {
    if (chronological.length < minLength) return false;
    var run = 0;
    for (final e in chronological) {
      if (_isSad(e.emotion) && e.stressLevel >= minStress) {
        run++;
        if (run >= minLength) return true;
      } else {
        run = 0;
      }
    }
    return false;
  }

  // ---------------------------------------------------------------------------
  // Правило 1 — PHQ-2
  // ---------------------------------------------------------------------------

  double _computePhq2Score(List<MoodEntry> last14) {
    double phq2Score = 0;
    final sadDays = last14.where((e) => _isSad(e.emotion)).length;
    if (sadDays >= 7) {
      phq2Score += 3;
    } else if (sadDays >= 4) {
      phq2Score += 2;
    } else if (sadDays >= 2) {
      phq2Score += 1;
    }

    final avgStress = _averageStressInt(last14);
    if (avgStress >= 8) {
      phq2Score += 3;
    } else if (avgStress >= 6) {
      phq2Score += 2;
    } else if (avgStress >= 4) {
      phq2Score += 1;
    }

    return phq2Score.clamp(0.0, 6.0);
  }

  // ---------------------------------------------------------------------------
  // Правило 2 — GAD-2
  // ---------------------------------------------------------------------------

  double _computeGad2Score(List<MoodEntry> last14) {
    double gad2Score = 0;
    final anxiousDays = last14.where((e) => _isAnxious(e.emotion)).length;
    if (anxiousDays >= 7) {
      gad2Score += 3;
    } else if (anxiousDays >= 4) {
      gad2Score += 2;
    } else if (anxiousDays >= 2) {
      gad2Score += 1;
    }

    final last14Chrono = _chronological(last14);
    final highStressStreak = _maxConsecutiveHighStress(last14Chrono, threshold: 6);
    if (highStressStreak >= 5) {
      gad2Score += 3;
    } else if (highStressStreak >= 3) {
      gad2Score += 2;
    } else if (highStressStreak >= 1) {
      gad2Score += 1;
    }

    return gad2Score.clamp(0.0, 6.0);
  }

  /// Максимальная длина подряд идущих записей со stressLevel > threshold (для «выше 6» — 1–10 шкала).
  int _maxConsecutiveHighStress(List<MoodEntry> chronological, {required int threshold}) {
    var maxRun = 0;
    var run = 0;
    for (final e in chronological) {
      if (e.stressLevel > threshold) {
        run++;
        if (run > maxRun) maxRun = run;
      } else {
        run = 0;
      }
    }
    return maxRun;
  }

  // ---------------------------------------------------------------------------
  // Правило 3 — тренд стресса
  // ---------------------------------------------------------------------------

  /// Возрастающий тренд: среднее второй половины ряда > первой (хронологический порядок).
  bool _isIncreasingTrend(List<int> stressLevels) {
    if (stressLevels.length < 4) return false;
    final mid = stressLevels.length ~/ 2;
    final first = stressLevels.sublist(0, mid);
    final second = stressLevels.sublist(mid);
    final avgFirst = first.reduce((a, b) => a + b) / first.length;
    final avgSecond = second.reduce((a, b) => a + b) / second.length;
    return avgSecond > avgFirst;
  }

  // ---------------------------------------------------------------------------
  // Утилиты
  // ---------------------------------------------------------------------------

  List<MoodEntry> _filterLastDays(List<MoodEntry> entries, int days) {
    final cutoff = DateTime.now().subtract(Duration(days: days));
    return entries.where((e) => e.timestamp.isAfter(cutoff)).toList();
  }

  List<MoodEntry> _chronological(List<MoodEntry> entries) {
    final copy = List<MoodEntry>.from(entries);
    copy.sort((a, b) => a.timestamp.compareTo(b.timestamp));
    return copy;
  }

  double _averageStressInt(List<MoodEntry> entries) {
    if (entries.isEmpty) return 0;
    final sum = entries.fold<int>(0, (s, e) => s + e.stressLevel);
    return sum / entries.length;
  }

  bool _isSad(String emotion) => emotion.toLowerCase() == 'sad';

  bool _isAnxious(String emotion) => emotion.toLowerCase() == 'anxious';
}
