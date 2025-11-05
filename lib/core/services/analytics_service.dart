import '../../providers/mood_provider.dart';
import 'ml_service.dart';

class AnalyticsService {
  final MLService _mlService;

  AnalyticsService(this._mlService);

  Future<Map<String, dynamic>> generateInsights(List<MoodEntry> entries) async {
    if (entries.isEmpty) return {'status': 'no_data'};

    final recent = entries.take(14).toList();
    final avgStress = recent.fold<int>(0, (sum, e) => sum + e.stressLevel) / recent.length;
    final prediction = await _mlService.predictNextMood(entries);
    final tipCategory = _mlService.recommendTipCategory(entries);
    final trend = _mlService.analyzeStressTrend(entries);

    return {
      'average_stress': avgStress,
      'predicted_mood': prediction,
      'recommended_category': tipCategory,
      'stress_trend': trend,
      'risk_level': _calculateRiskLevel(avgStress, trend),
    };
  }

  String _calculateRiskLevel(double avgStress, List<double> trend) {
    if (avgStress > 7.5 || (trend.isNotEmpty && trend.last > 7)) return 'high';
    if (avgStress > 5 || (trend.isNotEmpty && trend.last > 5)) return 'medium';
    return 'low';
  }

  List<String> generateRecommendations(String category, double avgStress) {
    final recommendations = <String>[];

    switch (category) {
      case 'stress_management':
        recommendations.addAll([
          'Попробуйте технику глубокого дыхания 4-7-8',
          'Сделайте перерыв каждые 2 часа',
          'Рассмотрите медитацию или йогу',
        ]);
        break;
      case 'relaxation':
        recommendations.addAll([
          'Уделите время хобби',
          'Прогуляйтесь на свежем воздухе',
          'Послушайте спокойную музыку',
        ]);
        break;
      case 'positive_habits':
        recommendations.addAll([
          'Продолжайте вести дневник настроения',
          'Поддерживайте регулярный режим сна',
          'Общайтесь с близкими людьми',
        ]);
        break;
      default:
        recommendations.addAll([
          'Следите за регулярностью записей',
          'Обращайте внимание на триггеры стресса',
          'Заботьтесь о физическом здоровье',
        ]);
    }

    return recommendations;
  }
}
