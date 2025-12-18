import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/constants/app_constants.dart';
import '../../../providers/mood_provider.dart';
import '../../../widgets/mood_chart.dart';

/// Statistics Screen - Displays graphs and observations
class StatisticsScreen extends StatefulWidget {
  const StatisticsScreen({super.key});

  @override
  State<StatisticsScreen> createState() => _StatisticsScreenState();
}

class _StatisticsScreenState extends State<StatisticsScreen> {
  String _selectedPeriod = 'week'; // 'week' or 'month'

  List<MoodEntry> _getFilteredEntries(List<MoodEntry> entries) {
    final now = DateTime.now();
    switch (_selectedPeriod) {
      case 'week':
        final weekAgo = now.subtract(const Duration(days: 7));
        return entries
            .where((entry) => entry.timestamp.isAfter(weekAgo))
            .toList();
      case 'month':
        final monthAgo = now.subtract(const Duration(days: 30));
        return entries
            .where((entry) => entry.timestamp.isAfter(monthAgo))
            .toList();
      default:
        return entries;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Statistics & Insights'),
        backgroundColor: Theme.of(context).colorScheme.primary,
        foregroundColor: Colors.white,
      ),
      body: Consumer<MoodProvider>(
        builder: (context, moodProvider, child) {
          if (moodProvider.isLoading) {
            return const Center(
              child: CircularProgressIndicator(),
            );
          }

          if (moodProvider.hasError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24.0),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(
                      Icons.error_outline,
                      size: 64,
                      color: Colors.red,
                    ),
                    const SizedBox(height: 16),
                    Text(
                      moodProvider.errorMessage ?? 'Произошла ошибка',
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Colors.red),
                    ),
                    const SizedBox(height: 16),
                    ElevatedButton.icon(
                      onPressed: () => moodProvider.loadEntries(),
                      icon: const Icon(Icons.refresh),
                      label: const Text('Попробовать снова'),
                    ),
                  ],
                ),
              ),
            );
          }

          final filteredEntries = _getFilteredEntries(moodProvider.entries);

          return SingleChildScrollView(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Заголовок
                Text(
                  'Your Mental Health Journey',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
                const SizedBox(height: 8),
                Text(
                  'Track your progress and discover patterns',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: Colors.grey[600],
                      ),
                ),
                const SizedBox(height: 24),

                // Переключатель периода
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(12.0),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                      children: [
                        _PeriodChip(
                          label: 'Неделя',
                          isSelected: _selectedPeriod == 'week',
                          onTap: () => setState(() => _selectedPeriod = 'week'),
                        ),
                        _PeriodChip(
                          label: 'Месяц',
                          isSelected: _selectedPeriod == 'month',
                          onTap: () => setState(() => _selectedPeriod = 'month'),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 24),

                // Графики
                if (filteredEntries.isNotEmpty)
                  MoodChart(
                    entries: filteredEntries,
                    period: _selectedPeriod,
                  )
                else
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(24.0),
                      child: Column(
                        children: [
                          const Icon(
                            Icons.bar_chart,
                            size: 64,
                            color: Colors.grey,
                          ),
                          const SizedBox(height: 16),
                          Text(
                            'Недостаточно данных',
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                              color: Colors.grey[700],
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'Добавьте записи в дневнике, чтобы увидеть статистику',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontSize: 14,
                              color: Colors.grey[600],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),

                const SizedBox(height: 24),

                // Статистика и наблюдения
                if (filteredEntries.isNotEmpty) ...[
                  _StatisticsSummaryCard(
                    entries: filteredEntries,
                    moodProvider: moodProvider,
                  ),
                  const SizedBox(height: 16),
                  _ObservationsCard(
                    observations: moodProvider.generateObservations(
                      lookbackDays: _selectedPeriod == 'week' ? 7 : 30,
                    ),
                  ),
                ],
              ],
            ),
          );
        },
      ),
    );
  }
}

/// Переключатель периода
class _PeriodChip extends StatelessWidget {
  final String label;
  final bool isSelected;
  final VoidCallback onTap;

  const _PeriodChip({
    required this.label,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
        decoration: BoxDecoration(
          color: isSelected
              ? Theme.of(context).colorScheme.primary
              : Colors.grey.shade200,
          borderRadius: BorderRadius.circular(24),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: isSelected ? Colors.white : Colors.black87,
            fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
            fontSize: 14,
          ),
        ),
      ),
    );
  }
}

/// Карточка со сводной статистикой
class _StatisticsSummaryCard extends StatelessWidget {
  final List<MoodEntry> entries;
  final MoodProvider moodProvider;

  const _StatisticsSummaryCard({
    required this.entries,
    required this.moodProvider,
  });

  @override
  Widget build(BuildContext context) {
    final avgStress = moodProvider.averageStressFor(entries);
    final emotionDistribution = _getEmotionDistribution(entries);

    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Сводная статистика',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            if (avgStress != null)
              _StatisticRow(
                icon: Icons.sentiment_very_dissatisfied,
                label: 'Средний уровень стресса',
                value: avgStress.toStringAsFixed(1),
                color: avgStress > 7
                    ? Colors.red
                    : avgStress > 4
                        ? Colors.orange
                        : Colors.green,
              ),
            const SizedBox(height: 12),
            if (emotionDistribution.isNotEmpty) ...[
              const Text(
                'Наиболее частые эмоции:',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 8),
              ...emotionDistribution.entries.take(3).map((entry) {
                return Padding(
                  padding: const EdgeInsets.only(bottom: 4.0),
                  child: Row(
                    children: [
                      Container(
                        width: 12,
                        height: 12,
                        decoration: BoxDecoration(
                          color: AppConstants.emotionColors[entry.key] ??
                              Colors.grey,
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(entry.key),
                      ),
                      Text(
                        '${entry.value.toStringAsFixed(1)}%',
                        style: const TextStyle(fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                );
              }),
            ],
          ],
        ),
      ),
    );
  }

  Map<String, double> _getEmotionDistribution(List<MoodEntry> entries) {
    if (entries.isEmpty) return {};

    final counts = <String, int>{};
    for (final entry in entries) {
      counts[entry.emotion] = (counts[entry.emotion] ?? 0) + 1;
    }

    return counts.map((emotion, count) {
      final percentage = (count / entries.length) * 100;
      return MapEntry(emotion, percentage);
    });
  }
}

/// Карточка с наблюдениями
class _ObservationsCard extends StatelessWidget {
  final List<String> observations;

  const _ObservationsCard({required this.observations});

  @override
  Widget build(BuildContext context) {
    if (observations.isEmpty) {
      return const SizedBox.shrink();
    }

    return Card(
      elevation: 2,
      color: Colors.blue.shade50,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.lightbulb_outline,
                  color: Colors.blue.shade700,
                  size: 24,
                ),
                const SizedBox(width: 8),
                Text(
                  'Наблюдения',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: Colors.blue.shade900,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            ...observations.map((observation) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 8.0),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      Icons.check_circle_outline,
                      size: 16,
                      color: Colors.blue.shade700,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        observation,
                        style: TextStyle(
                          fontSize: 14,
                          color: Colors.blue.shade800,
                        ),
                      ),
                    ),
                  ],
                ),
              );
            }),
          ],
        ),
      ),
    );
  }
}

/// Строка статистики
class _StatisticRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Color color;

  const _StatisticRow({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, color: color, size: 20),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            label,
            style: const TextStyle(fontSize: 14),
          ),
        ),
        Text(
          value,
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
      ],
    );
  }
}
