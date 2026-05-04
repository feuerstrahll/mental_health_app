import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../../core/constants/app_constants.dart';
import '../../../providers/mood_provider.dart';
import '../../../providers/settings_provider.dart';
import '../../../widgets/app_shell.dart';

class StatisticsScreen extends StatefulWidget {
  const StatisticsScreen({super.key});

  @override
  State<StatisticsScreen> createState() => _StatisticsScreenState();
}

class _StatisticsScreenState extends State<StatisticsScreen> {
  int? _periodDays = 7;
  DateTimeRange? _customRange;

  Future<void> _pickCustomRange() async {
    final now = DateTime.now();
    final picked = await showDateRangePicker(
      context: context,
      firstDate: DateTime(now.year - 2),
      lastDate: DateTime(now.year + 1),
      initialDateRange: _customRange ??
          DateTimeRange(
            start: now.subtract(const Duration(days: 6)),
            end: now,
          ),
    );

    if (picked == null || !mounted) return;
    setState(() {
      _customRange = picked;
      _periodDays = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<MoodProvider>();
    final settings = context.watch<SettingsProvider>();
    final now = DateTime.now();
    final start = _customRange?.start ?? now.subtract(Duration(days: _periodDays ?? 7));
    final end = _customRange?.end ?? now;
    final entries = provider.filterByDateRange(start, end);
    final avgStress = provider.averageStressFor(entries);
    final tipStats = _tipSummary(settings.tipFeedback);
    final periodText = _customRange == null
        ? '${_periodDays ?? 7} дней'
        : '${_formatDate(start)} — ${_formatDate(end)}';

    return AppShell(
      title: 'Прогресс',
      currentRoute: AppRoutes.progress,
      backgroundColor: AppColors.sage,
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(16, 18, 16, 118),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final days in [7, 14, 30])
                  ChoiceChip(
                    label: Text('$days дней'),
                    selected: _periodDays == days,
                    selectedColor: AppColors.forest.withOpacity(0.22),
                    labelStyle: const TextStyle(
                      color: AppColors.brown,
                      fontWeight: FontWeight.w700,
                    ),
                    onSelected: (_) => setState(() {
                      _periodDays = days;
                      _customRange = null;
                    }),
                  ),
                ChoiceChip(
                  label: const Text('свой период'),
                  selected: _periodDays == null,
                  selectedColor: AppColors.forest.withOpacity(0.22),
                  labelStyle: const TextStyle(
                    color: AppColors.brown,
                    fontWeight: FontWeight.w700,
                  ),
                  onSelected: (_) => _pickCustomRange(),
                ),
              ],
            ),
            const SizedBox(height: 14),
            SoftCard(
              color: const Color(0xFFFFEFC8),
              child: Row(
                children: [
                  const Icon(Icons.insights_rounded, color: AppColors.forest, size: 34),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      entries.isEmpty
                          ? 'За период $periodText пока нет записей. Заполни дневник, чтобы увидеть динамику.'
                          : 'Период: $periodText. Записей: ${entries.length}. Средний стресс: ${avgStress?.toStringAsFixed(1) ?? '—'}/10.',
                      style: const TextStyle(
                        color: AppColors.brown,
                        height: 1.3,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            _MiniChartCard(
              title: 'Настроение',
              icon: Icons.mood_rounded,
              values: _mockValues(entries.length, 6),
            ),
            _MiniChartCard(
              title: 'Длительность сна',
              icon: Icons.bedtime_rounded,
              values: _mockValues(entries.length, 5),
            ),
            _MiniChartCard(
              title: 'Качество сна',
              icon: Icons.nightlight_round,
              values: _mockValues(entries.length, 4),
            ),
            _MiniChartCard(
              title: 'Активность',
              icon: Icons.directions_walk_rounded,
              values: _mockValues(entries.length, 5),
            ),
            _MiniChartCard(
              title: 'Время на улице',
              icon: Icons.wb_sunny_rounded,
              values: _mockValues(entries.length, 3),
            ),
            _MiniChartCard(
              title: 'Социальность',
              icon: Icons.people_alt_rounded,
              values: _mockValues(entries.length, 4),
            ),
            _MiniChartCard(
              title: 'Регулярность рутины',
              icon: Icons.event_repeat_rounded,
              values: _mockValues(entries.length, 5),
            ),
            SoftCard(
              onTap: () => context.go(AppRoutes.tips),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Какие советы чаще помогали',
                    style: TextStyle(
                      color: AppColors.brown,
                      fontSize: 18,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    tipStats,
                    style: const TextStyle(color: AppColors.brown, height: 1.35),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Открыть советы →',
                    style: TextStyle(
                      color: AppColors.forest,
                      fontWeight: FontWeight.w900,
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

  String _formatDate(DateTime date) {
    return '${date.day.toString().padLeft(2, '0')}.${date.month.toString().padLeft(2, '0')}';
  }

  String _tipSummary(Map<String, String> feedback) {
    if (feedback.isEmpty) {
      return 'Пока нет реакций на советы. После свайпов здесь появится вывод: что помогало, что не подошло и какой тип практик лучше предлагать дальше.';
    }

    final helped = feedback.entries.where((e) => e.value == 'helped').toList();
    final bad = feedback.entries.where((e) => e.value == 'bad').toList();
    final later = feedback.entries.where((e) => e.value == 'later').toList();

    final labels = {
      'breath_46': 'дыхание',
      'walk_light': 'свет и воздух',
      'tiny_step': 'маленькие шаги',
      'body_reset': 'телесные практики',
    };

    final helpedTitles = helped.map((e) => labels[e.key] ?? e.key).take(2).join(', ');
    final lines = [
      'Помогло: ${helped.length}. Не подошло: ${bad.length}. Отложено: ${later.length}.',
    ];

    if (helpedTitles.isNotEmpty) {
      lines.add('Лучше всего сейчас заходят: $helpedTitles.');
    } else if (bad.isNotEmpty) {
      lines.add('Пока лучше сменить курс советов и предложить другие практики.');
    }

    return lines.join('\n');
  }

  List<double> _mockValues(int entriesCount, int seed) {
    final count = entriesCount == 0 ? 7 : entriesCount.clamp(3, 10).toInt();
    return List.generate(count, (index) => ((index + seed) % 5 + 1) / 5);
  }
}

class _MiniChartCard extends StatelessWidget {
  const _MiniChartCard({required this.title, required this.icon, required this.values});

  final String title;
  final IconData icon;
  final List<double> values;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: SoftCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: AppColors.forest),
                const SizedBox(width: 8),
                Text(title, style: const TextStyle(color: AppColors.brown, fontSize: 17, fontWeight: FontWeight.w900)),
              ],
            ),
            const SizedBox(height: 14),
            SizedBox(
              height: 72,
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: values.map((value) {
                  return Expanded(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 3),
                      child: FractionallySizedBox(
                        heightFactor: value.clamp(0.12, 1),
                        alignment: Alignment.bottomCenter,
                        child: Container(
                          decoration: BoxDecoration(
                            color: AppColors.forest.withOpacity(0.68),
                            borderRadius: BorderRadius.circular(10),
                          ),
                        ),
                      ),
                    ),
                  );
                }).toList(),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
