import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:intl/intl.dart';

import '../core/constants/app_constants.dart';
import '../providers/mood_provider.dart';

/// Виджет для отображения графиков настроения
class MoodChart extends StatelessWidget {
  final List<MoodEntry> entries;
  final String period; // 'week' or 'month'

  const MoodChart({
    super.key,
    required this.entries,
    required this.period,
  });

  @override
  Widget build(BuildContext context) {
    if (entries.isEmpty) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(24.0),
          child: Text(
            'Недостаточно данных для отображения графиков',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.grey),
          ),
        ),
      );
    }

    return Column(
      children: [
        // Линейный график уровня стресса
        _StressLevelLineChart(entries: entries, period: period),
        const SizedBox(height: 32),
        // Круговая диаграмма распределения эмоций
        _EmotionDistributionPieChart(entries: entries),
      ],
    );
  }
}

/// Линейный график изменения уровня стресса
class _StressLevelLineChart extends StatelessWidget {
  final List<MoodEntry> entries;
  final String period;

  const _StressLevelLineChart({
    required this.entries,
    required this.period,
  });

  List<MoodEntry> get _sortedEntries {
    final sorted = List<MoodEntry>.from(entries)
      ..sort((a, b) => a.timestamp.compareTo(b.timestamp));
    return sorted;
  }

  List<FlSpot> _getStressSpots() {
    return _sortedEntries.asMap().entries.map((entry) {
      return FlSpot(entry.key.toDouble(), entry.value.stressLevel.toDouble());
    }).toList();
  }

  List<String> _getXAxisLabels() {
    if (_sortedEntries.isEmpty) return [];

    // Для недели показываем дни недели, для месяца - даты
    if (period == 'week') {
      return _sortedEntries.map((entry) {
        try {
          final weekday = DateFormat('E', 'ru_RU').format(entry.timestamp);
          return weekday.substring(0, 1).toUpperCase(); // Первая буква дня недели
        } catch (e) {
          // Fallback на английский формат
          final weekday = DateFormat('E').format(entry.timestamp);
          return weekday.substring(0, 1);
        }
      }).toList();
    } else {
      return _sortedEntries.map((entry) {
        return '${entry.timestamp.day}/${entry.timestamp.month}';
      }).toList();
    }
  }

  @override
  Widget build(BuildContext context) {
    final spots = _getStressSpots();
    final xLabels = _getXAxisLabels();

    if (spots.isEmpty) {
      return const SizedBox.shrink();
    }

    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Уровень стресса',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              period == 'week' ? 'За неделю' : 'За месяц',
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey[600],
              ),
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: 200,
              child: LineChart(
                LineChartData(
                  gridData: FlGridData(
                    show: true,
                    drawVerticalLine: false,
                    horizontalInterval: 1,
                    getDrawingHorizontalLine: (value) {
                      return FlLine(
                        color: Colors.grey.withOpacity(0.2),
                        strokeWidth: 1,
                      );
                    },
                  ),
                  titlesData: FlTitlesData(
                    show: true,
                    rightTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false),
                    ),
                    topTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false),
                    ),
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        reservedSize: 30,
                        interval: spots.length > 7 ? 2 : 1,
                        getTitlesWidget: (value, meta) {
                          final index = value.toInt();
                          if (index >= 0 && index < xLabels.length) {
                            return Padding(
                              padding: const EdgeInsets.only(top: 8.0),
                              child: Text(
                                xLabels[index],
                                style: const TextStyle(
                                  fontSize: 10,
                                  color: Colors.grey,
                                ),
                              ),
                            );
                          }
                          return const Text('');
                        },
                      ),
                    ),
                    leftTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        reservedSize: 40,
                        interval: 2,
                        getTitlesWidget: (value, meta) {
                          return Text(
                            value.toInt().toString(),
                            style: const TextStyle(
                              fontSize: 10,
                              color: Colors.grey,
                            ),
                          );
                        },
                      ),
                    ),
                  ),
                  borderData: FlBorderData(
                    show: true,
                    border: Border(
                      bottom: BorderSide(color: Colors.grey.shade300),
                      left: BorderSide(color: Colors.grey.shade300),
                    ),
                  ),
                  minX: 0,
                  maxX: (spots.length - 1).toDouble(),
                  minY: 0,
                  maxY: 10,
                  lineBarsData: [
                    LineChartBarData(
                      spots: spots,
                      isCurved: true,
                      color: Colors.blue,
                      barWidth: 3,
                      isStrokeCapRound: true,
                      dotData: FlDotData(
                        show: true,
                        getDotPainter: (spot, percent, barData, index) {
                          return FlDotCirclePainter(
                            radius: 4,
                            color: Colors.blue,
                            strokeWidth: 2,
                            strokeColor: Colors.white,
                          );
                        },
                      ),
                      belowBarData: BarAreaData(
                        show: true,
                        color: Colors.blue.withOpacity(0.1),
                      ),
                    ),
                  ],
                  lineTouchData: LineTouchData(
                    touchTooltipData: LineTouchTooltipData(
                      getTooltipItems: (List<LineBarSpot> touchedSpots) {
                        return touchedSpots.map((spot) {
                          final index = spot.x.toInt();
                          if (index >= 0 && index < _sortedEntries.length) {
                            final entry = _sortedEntries[index];
                            return LineTooltipItem(
                              '${entry.stressLevel}/10\n${DateFormat('dd.MM.yyyy HH:mm').format(entry.timestamp)}',
                              const TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.bold,
                              ),
                            );
                          }
                          return const LineTooltipItem('', TextStyle());
                        }).toList();
                      },
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                _LegendItem(
                  color: Colors.blue,
                  label: 'Уровень стресса',
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

/// Круговая диаграмма распределения эмоций
class _EmotionDistributionPieChart extends StatelessWidget {
  final List<MoodEntry> entries;

  const _EmotionDistributionPieChart({required this.entries});

  Map<String, int> _getEmotionCounts() {
    final counts = <String, int>{};
    for (final entry in entries) {
      counts[entry.emotion] = (counts[entry.emotion] ?? 0) + 1;
    }
    return counts;
  }

  List<PieChartSectionData> _getPieChartSections() {
    final emotionCounts = _getEmotionCounts();
    final total = entries.length;

    if (emotionCounts.isEmpty) return [];

    final sections = <PieChartSectionData>[];
    int startAngle = -90; // Начинаем сверху

    emotionCounts.forEach((emotion, count) {
      final percentage = (count / total) * 100;
      final color = AppConstants.emotionColors[emotion] ?? Colors.grey;

      sections.add(
        PieChartSectionData(
          value: count.toDouble(),
          title: '${percentage.toStringAsFixed(0)}%',
          color: color,
          radius: 60,
          titleStyle: const TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.bold,
            color: Colors.white,
          ),
        ),
      );
    });

    return sections;
  }

  @override
  Widget build(BuildContext context) {
    final emotionCounts = _getEmotionCounts();

    if (emotionCounts.isEmpty) {
      return const SizedBox.shrink();
    }

    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Распределение эмоций',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Всего записей: ${entries.length}',
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey[600],
              ),
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: 200,
              child: Row(
                children: [
                  Expanded(
                    child: PieChart(
                      PieChartData(
                        sections: _getPieChartSections(),
                        sectionsSpace: 2,
                        centerSpaceRadius: 40,
                        pieTouchData: PieTouchData(
                          touchCallback: (FlTouchEvent event, pieTouchResponse) {
                            // Можно добавить обработку нажатий
                          },
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: emotionCounts.entries.map((entry) {
                        final emotion = entry.key;
                        final count = entry.value;
                        final percentage = (count / entries.length) * 100;
                        final color =
                            AppConstants.emotionColors[emotion] ?? Colors.grey;

                        return Padding(
                          padding: const EdgeInsets.only(bottom: 8.0),
                          child: Row(
                            children: [
                              Container(
                                width: 16,
                                height: 16,
                                decoration: BoxDecoration(
                                  color: color,
                                  shape: BoxShape.circle,
                                ),
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  emotion,
                                  style: const TextStyle(fontSize: 12),
                                ),
                              ),
                              Text(
                                '${count} (${percentage.toStringAsFixed(0)}%)',
                                style: TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.grey[700],
                                ),
                              ),
                            ],
                          ),
                        );
                      }).toList(),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Элемент легенды
class _LegendItem extends StatelessWidget {
  final Color color;
  final String label;

  const _LegendItem({
    required this.color,
    required this.label,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 16,
          height: 16,
          decoration: BoxDecoration(
            color: color,
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(width: 8),
        Text(
          label,
          style: const TextStyle(fontSize: 12),
        ),
      ],
    );
  }
}

