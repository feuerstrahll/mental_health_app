import '../../providers/mood_provider.dart';
import 'clinical_rules_engine.dart' as engine;

enum RiskLevel { low, moderate, high, crisis }

class ClinicalAssessment {
  const ClinicalAssessment({
    required this.riskLevel,
    required this.isCrisis,
    required this.triggeredRules,
    required this.phq9Score,
    required this.gad7Score,
    required this.avgStressNormalized,
    required this.avgEmotionValue,
  });

  final RiskLevel riskLevel;
  final bool isCrisis;
  final List<String> triggeredRules;
  final double phq9Score;
  final double gad7Score;
  final double avgStressNormalized;
  final double avgEmotionValue;
}

/// Compatibility adapter that preserves the old `ClinicalRulesService` API,
/// while delegating analysis to `ClinicalRulesEngine`.
class ClinicalRulesService {
  static const int minContextDays = engine.ClinicalRulesEngine.minContextDays;
  static const int maxContextDays = engine.ClinicalRulesEngine.maxContextDays;

  final engine.ClinicalRulesEngine _engine = engine.ClinicalRulesEngine();

  ClinicalAssessment evaluate(List<MoodEntry> entries) {
    final recent = List<MoodEntry>.from(entries)
      ..sort((a, b) => b.timestamp.compareTo(a.timestamp));
    final capped = recent.take(maxContextDays).toList();
    final assessed = _engine.evaluate(capped);

    return ClinicalAssessment(
      riskLevel: _mapRiskLevel(assessed.riskLevel),
      isCrisis: assessed.riskLevel == engine.RiskLevel.crisis,
      triggeredRules: assessed.triggerReasons,
      // Legacy fields retained for compatibility with existing UI/debug code.
      phq9Score: (assessed.phq2Score / 6.0 * 30.0).clamp(0.0, 30.0),
      gad7Score: (assessed.gad2Score / 6.0 * 21.0).clamp(0.0, 21.0),
      avgStressNormalized: _averageStressNormalized(capped),
      avgEmotionValue: _averageEmotionValue(capped),
    );
  }

  RiskLevel _mapRiskLevel(engine.RiskLevel source) {
    switch (source) {
      case engine.RiskLevel.normal:
        return RiskLevel.low;
      case engine.RiskLevel.elevated:
        return RiskLevel.moderate;
      case engine.RiskLevel.high:
        return RiskLevel.high;
      case engine.RiskLevel.crisis:
        return RiskLevel.crisis;
    }
  }

  double _averageStressNormalized(List<MoodEntry> entries) {
    if (entries.isEmpty) return 0.0;
    final total = entries.fold<int>(0, (sum, e) => sum + e.stressLevel);
    return (total / entries.length / 10.0).clamp(0.0, 1.0);
  }

  double _averageEmotionValue(List<MoodEntry> entries) {
    if (entries.isEmpty) return 0.5;
    final values = entries.map((e) => _encodeEmotion(e.emotion)).toList();
    final sum = values.fold<double>(0.0, (acc, value) => acc + value);
    return (sum / values.length).clamp(0.0, 1.0);
  }

  double _encodeEmotion(String emotion) {
    switch (emotion.toLowerCase()) {
      case 'happy':
      case 'радость':
        return 0.83;
      case 'sad':
      case 'грусть':
      case 'очень плохо':
        return 0.17;
      case 'anxious':
      case 'тревога':
        return 0.35;
      case 'calm':
      case 'спокойствие':
        return 0.65;
      case 'angry':
      case 'злость':
        return 0.17;
      case 'neutral':
      case 'нормально':
        return 0.50;
      case 'так себе':
        return 0.35;
      case 'хорошо':
        return 0.70;
      case 'отлично':
        return 0.90;
      default:
        return 0.50;
    }
  }
}
