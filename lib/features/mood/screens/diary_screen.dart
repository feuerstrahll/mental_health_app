import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../../core/constants/app_constants.dart';
import '../../../providers/mood_provider.dart';
import '../../../widgets/app_shell.dart';

class DiaryScreen extends StatefulWidget {
  const DiaryScreen({super.key});

  @override
  State<DiaryScreen> createState() => _DiaryScreenState();
}

class _DiaryScreenState extends State<DiaryScreen> {
  bool _fullMode = false;
  int _moodIndex = 3;
  double _sleepHours = 7;
  double _sleepQuality = 3;
  double _sleepRegularity = 3;
  double _activity = 2;
  double _sedentary = 4;
  double _outsideTime = 1;
  bool _socialContact = false;
  bool _structuredDay = true;
  final TextEditingController _commentController = TextEditingController();

  final List<_MoodOption> _moods = const [
    _MoodOption('😣', 'Очень плохо', 'Sad', 9),
    _MoodOption('😟', 'Тревожно', 'Anxious', 8),
    _MoodOption('😔', 'Грустно', 'Sad', 7),
    _MoodOption('😐', 'Нейтрально', 'Neutral', 5),
    _MoodOption('🙂', 'Спокойно', 'Calm', 3),
    _MoodOption('😊', 'Хорошо', 'Happy', 2),
  ];

  @override
  void dispose() {
    _commentController.dispose();
    super.dispose();
  }

  Future<void> _saveDay() async {
    final mood = _moods[_moodIndex];
    final comment = _commentController.text.trim();

    final details = StringBuffer();
    if (comment.isNotEmpty) details.writeln(comment);
    details
      ..writeln('Сон: ${_sleepHours.toStringAsFixed(1)} ч')
      ..writeln('Качество сна: ${_sleepQuality.round()}/5');

    if (_fullMode) {
      details
        ..writeln('Регулярность сна: ${_sleepRegularity.round()}/5')
        ..writeln('Физическая активность: ${_activity.round()}/5')
        ..writeln('Сидячее время: ${_sedentary.round()}/5')
        ..writeln('Время на улице: ${_outsideTime.toStringAsFixed(1)} ч')
        ..writeln('Социальный контакт: ${_socialContact ? 'да' : 'нет'}')
        ..writeln('День: ${_structuredDay ? 'структурный' : 'хаотичный'}');
    }

    await context.read<MoodProvider>().addEntry(
          emotion: mood.emotionKey,
          stressLevel: mood.stressLevel,
          note: details.toString().trim(),
        );

    if (!mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: const Text('День сохранён'),
        action: SnackBarAction(
          label: 'Советы',
          onPressed: () => context.go(AppRoutes.tips),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AppShell(
      title: 'Дневник',
      currentRoute: AppRoutes.diary,
      backgroundColor: AppColors.sage,
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(16, 18, 16, 118),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const _SummaryCard(),
            const SizedBox(height: 16),
            SegmentedButton<bool>(
              segments: const [
                ButtonSegment(value: false, label: Text('Быстро'), icon: Icon(Icons.flash_on_rounded)),
                ButtonSegment(value: true, label: Text('Полностью'), icon: Icon(Icons.checklist_rounded)),
              ],
              selected: {_fullMode},
              onSelectionChanged: (value) => setState(() => _fullMode = value.first),
            ),
            const SizedBox(height: 16),
            SoftCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Настроение', style: _sectionTitleStyle),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: List.generate(_moods.length, (index) {
                      final mood = _moods[index];
                      final selected = _moodIndex == index;
                      return ChoiceChip(
                        selected: selected,
                        label: Text('${mood.emoji} ${mood.label}'),
                        selectedColor: AppColors.forest.withOpacity(0.22),
                        onSelected: (_) => setState(() => _moodIndex = index),
                      );
                    }),
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _commentController,
                    minLines: 2,
                    maxLines: 4,
                    decoration: InputDecoration(
                      labelText: 'Короткий комментарий',
                      hintText: 'Что важного было сегодня?',
                      filled: true,
                      fillColor: Colors.white,
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(18), borderSide: BorderSide.none),
                    ),
                  ),
                  const SizedBox(height: 16),
                  _SliderField(
                    title: 'Длительность сна',
                    value: _sleepHours,
                    min: 0,
                    max: 12,
                    divisions: 24,
                    suffix: 'ч',
                    onChanged: (v) => setState(() => _sleepHours = v),
                  ),
                  _SliderField(
                    title: 'Качество сна',
                    value: _sleepQuality,
                    min: 1,
                    max: 5,
                    divisions: 4,
                    onChanged: (v) => setState(() => _sleepQuality = v),
                  ),
                  if (_fullMode) ...[
                    _SliderField(
                      title: 'Регулярность сна',
                      value: _sleepRegularity,
                      min: 1,
                      max: 5,
                      divisions: 4,
                      onChanged: (v) => setState(() => _sleepRegularity = v),
                    ),
                    _SliderField(
                      title: 'Физическая активность',
                      value: _activity,
                      min: 1,
                      max: 5,
                      divisions: 4,
                      onChanged: (v) => setState(() => _activity = v),
                    ),
                    _SliderField(
                      title: 'Сидячее время',
                      value: _sedentary,
                      min: 1,
                      max: 5,
                      divisions: 4,
                      onChanged: (v) => setState(() => _sedentary = v),
                    ),
                    _SliderField(
                      title: 'Время на улице / дневной свет',
                      value: _outsideTime,
                      min: 0,
                      max: 6,
                      divisions: 12,
                      suffix: 'ч',
                      onChanged: (v) => setState(() => _outsideTime = v),
                    ),
                    SwitchListTile(
                      value: _socialContact,
                      contentPadding: EdgeInsets.zero,
                      title: const Text('Был значимый социальный контакт'),
                      onChanged: (v) => setState(() => _socialContact = v),
                    ),
                    SwitchListTile(
                      value: _structuredDay,
                      contentPadding: EdgeInsets.zero,
                      title: const Text('День был структурным'),
                      subtitle: Text(_structuredDay ? 'Не хаотичным' : 'Скорее хаотичным'),
                      onChanged: (v) => setState(() => _structuredDay = v),
                    ),
                  ],
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: _saveDay,
                      icon: const Icon(Icons.check_rounded),
                      label: const Text('Сохранить день'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.forest,
                        foregroundColor: AppColors.cream,
                        padding: const EdgeInsets.symmetric(vertical: 15),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
                      ),
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

const TextStyle _sectionTitleStyle = TextStyle(
  color: AppColors.brown,
  fontSize: 20,
  fontWeight: FontWeight.w900,
);

class _SummaryCard extends StatelessWidget {
  const _SummaryCard();

  @override
  Widget build(BuildContext context) {
    final entriesCount = context.watch<MoodProvider>().entries.length;
    return SoftCard(
      color: const Color(0xFFFFEFC8),
      child: Row(
        children: [
          Container(
            width: 54,
            height: 54,
            decoration: const BoxDecoration(color: Colors.white, shape: BoxShape.circle),
            child: const Icon(Icons.auto_awesome_rounded, color: AppColors.forest),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              entriesCount == 0
                  ? 'Пока данных мало. Заполни день, и тут появится краткий вывод.'
                  : 'За последние записи можно будет показать вывод по сну, настроению и рутине.',
              style: const TextStyle(color: AppColors.brown, height: 1.25),
            ),
          ),
        ],
      ),
    );
  }
}

class _SliderField extends StatelessWidget {
  const _SliderField({
    required this.title,
    required this.value,
    required this.min,
    required this.max,
    required this.divisions,
    required this.onChanged,
    this.suffix = '/5',
  });

  final String title;
  final double value;
  final double min;
  final double max;
  final int divisions;
  final String suffix;
  final ValueChanged<double> onChanged;

  @override
  Widget build(BuildContext context) {
    final display = suffix == 'ч' ? value.toStringAsFixed(1) : value.round().toString();
    return Padding(
      padding: const EdgeInsets.only(top: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: Text(title, style: const TextStyle(fontWeight: FontWeight.w700, color: AppColors.brown))),
              Text('$display $suffix', style: const TextStyle(color: AppColors.brown, fontWeight: FontWeight.w800)),
            ],
          ),
          Slider(
            value: value,
            min: min,
            max: max,
            divisions: divisions,
            activeColor: AppColors.forest,
            onChanged: onChanged,
          ),
        ],
      ),
    );
  }
}

class _MoodOption {
  const _MoodOption(this.emoji, this.label, this.emotionKey, this.stressLevel);

  final String emoji;
  final String label;
  final String emotionKey;
  final int stressLevel;
}
