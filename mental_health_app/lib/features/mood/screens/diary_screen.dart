import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/constants/app_constants.dart';
import '../../../providers/mood_provider.dart';

class DiaryScreen extends StatefulWidget {
  const DiaryScreen({super.key});

  @override
  State<DiaryScreen> createState() => _DiaryScreenState();
}

class _DiaryScreenState extends State<DiaryScreen> {
  bool _showEmotions = true;
  bool _isSaving = false;
  int? _selectedEmotionIndex;
  int _stressLevel = 5;
  String? _selectedTag;
  final TextEditingController _noteController = TextEditingController();

  final List<String> _emotionLabels = const [
    'Очень плохо',
    'Тревожно',
    'Нейтрально',
    'Спокойно',
    'Хорошо',
  ];

  final List<String> _emotionValues = const [
    'Sad',
    'Anxious',
    'Neutral',
    'Calm',
    'Happy',
  ];

  final List<String> _emotionIcons = const ['😢', '🙁', '😐', '🙂', '🤩'];

  final List<String> _tags = const [
    'Учёба / работа',
    'Отдых',
    'Друзья / семья',
    'Здоровье',
  ];

  @override
  void dispose() {
    _noteController.dispose();
    super.dispose();
  }

  void _onSheepTap() {
    setState(() {
      _showEmotions = !_showEmotions;
    });
  }

  void _onEmotionTap(int index) {
    setState(() {
      _selectedEmotionIndex = index;
    });
  }

  Future<void> _onSave() async {
    final selectedIndex = _selectedEmotionIndex;
    if (selectedIndex == null || _isSaving) return;

    setState(() {
      _isSaving = true;
    });

    final moodProvider = context.read<MoodProvider>();
    final note = _buildNote();

    try {
      await moodProvider.addEntry(
        emotion: _emotionValues[selectedIndex],
        stressLevel: _stressLevel,
        note: note.isEmpty ? null : note,
      );

      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Запись сохранена')));

      setState(() {
        _selectedEmotionIndex = null;
        _selectedTag = null;
        _stressLevel = 5;
        _noteController.clear();
      });
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Не удалось сохранить запись')),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isSaving = false;
        });
      }
    }
  }

  String _buildNote() {
    final parts = <String>[];
    if (_selectedTag != null) {
      parts.add('Тег: $_selectedTag.');
    }
    final rawNote = _noteController.text.trim();
    if (rawNote.isNotEmpty) {
      parts.add(rawNote);
    }
    return parts.join('\n');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Дневник'),
        backgroundColor: Colors.green.shade700,
        foregroundColor: Colors.white,
      ),
      body: Stack(
        children: [
          Positioned.fill(
            child: Image.asset(
              'assets/images/sheep_diary_bg.jpg',
              fit: BoxFit.cover,
            ),
          ),
          Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(
                color: Colors.black.withValues(alpha: 0.12),
              ),
            ),
          ),
          SafeArea(
            child: Column(
              children: [
                _DiaryInsightCard(),
                Expanded(
                  child: Center(
                    child: SingleChildScrollView(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 12,
                      ),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          GestureDetector(
                            onTap: _onSheepTap,
                            child: Container(
                              width: 160,
                              height: 160,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: Colors.black.withValues(alpha: 0.10),
                              ),
                              alignment: Alignment.center,
                              child: const Text(
                                'Нажми, чтобы выбрать настроение',
                                style: TextStyle(
                                  fontSize: 14,
                                  color: Colors.white,
                                  shadows: [
                                    Shadow(
                                      color: Colors.black54,
                                      blurRadius: 4,
                                      offset: Offset(0, 1),
                                    ),
                                  ],
                                ),
                                textAlign: TextAlign.center,
                              ),
                            ),
                          ),
                          const SizedBox(height: 20),
                          AnimatedSwitcher(
                            duration: const Duration(milliseconds: 250),
                            child: _showEmotions
                                ? _EmotionPicker(
                                    selectedEmotionIndex: _selectedEmotionIndex,
                                    emotionLabels: _emotionLabels,
                                    emotionIcons: _emotionIcons,
                                    onEmotionTap: _onEmotionTap,
                                  )
                                : const SizedBox.shrink(),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
                _DiaryInputPanel(
                  selectedTag: _selectedTag,
                  tags: _tags,
                  noteController: _noteController,
                  stressLevel: _stressLevel,
                  isSaveEnabled: _selectedEmotionIndex != null && !_isSaving,
                  isSaving: _isSaving,
                  onTagChanged: (value) => setState(() => _selectedTag = value),
                  onStressChanged: (value) =>
                      setState(() => _stressLevel = value.round()),
                  onSave: _onSave,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _DiaryInsightCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Consumer<MoodProvider>(
      builder: (context, moodProvider, _) {
        final entryCount = moodProvider.entries.length;
        final insight = moodProvider.getDiaryInsight();
        return Container(
          width: double.infinity,
          margin: const EdgeInsets.fromLTRB(16, 12, 16, 8),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.94),
            borderRadius: BorderRadius.circular(8),
            boxShadow: const [
              BoxShadow(
                color: Colors.black26,
                blurRadius: 8,
                offset: Offset(0, 2),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(Icons.insights, color: Colors.green.shade800),
                  const SizedBox(width: 8),
                  const Expanded(
                    child: Text(
                      'Наблюдение',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  IconButton(
                    tooltip: 'Обновить наблюдение',
                    onPressed: () => moodProvider.refreshDiaryInsight(),
                    icon: const Icon(Icons.refresh),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(insight, style: const TextStyle(fontSize: 14, height: 1.35)),
              const SizedBox(height: 10),
              Text(
                entryCount == 0 ? 'Записей пока нет' : 'Записей: $entryCount',
                style: TextStyle(fontSize: 12, color: Colors.grey.shade700),
              ),
              if (moodProvider.isLoading) ...[
                const SizedBox(height: 10),
                const LinearProgressIndicator(minHeight: 3),
              ],
            ],
          ),
        );
      },
    );
  }
}

class _EmotionPicker extends StatelessWidget {
  const _EmotionPicker({
    required this.selectedEmotionIndex,
    required this.emotionLabels,
    required this.emotionIcons,
    required this.onEmotionTap,
  });

  final int? selectedEmotionIndex;
  final List<String> emotionLabels;
  final List<String> emotionIcons;
  final ValueChanged<int> onEmotionTap;

  @override
  Widget build(BuildContext context) {
    return Column(
      key: const ValueKey('emotions'),
      children: [
        const Text(
          'Как ты себя чувствуешь?',
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.w600,
            color: Colors.white,
            shadows: [Shadow(color: Colors.black54, blurRadius: 4)],
          ),
        ),
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: Colors.black.withValues(alpha: 0.35),
            borderRadius: BorderRadius.circular(32),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: List.generate(emotionIcons.length, (index) {
              final isSelected = selectedEmotionIndex == index;
              return Tooltip(
                message: emotionLabels[index],
                child: InkWell(
                  customBorder: const CircleBorder(),
                  onTap: () => onEmotionTap(index),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 150),
                    width: 46,
                    height: 46,
                    margin: const EdgeInsets.symmetric(horizontal: 3),
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: isSelected
                          ? Colors.white.withValues(alpha: 0.95)
                          : Colors.white.withValues(alpha: 0.28),
                      border: isSelected
                          ? Border.all(color: Colors.white, width: 2)
                          : null,
                    ),
                    alignment: Alignment.center,
                    child: Text(
                      emotionIcons[index],
                      style: const TextStyle(fontSize: 23),
                    ),
                  ),
                ),
              );
            }),
          ),
        ),
        const SizedBox(height: 8),
        SizedBox(
          height: 22,
          child: selectedEmotionIndex == null
              ? const SizedBox.shrink()
              : Text(
                  emotionLabels[selectedEmotionIndex!],
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                    shadows: [Shadow(color: Colors.black54, blurRadius: 4)],
                  ),
                ),
        ),
      ],
    );
  }
}

class _DiaryInputPanel extends StatelessWidget {
  const _DiaryInputPanel({
    required this.selectedTag,
    required this.tags,
    required this.noteController,
    required this.stressLevel,
    required this.isSaveEnabled,
    required this.isSaving,
    required this.onTagChanged,
    required this.onStressChanged,
    required this.onSave,
  });

  final String? selectedTag;
  final List<String> tags;
  final TextEditingController noteController;
  final int stressLevel;
  final bool isSaveEnabled;
  final bool isSaving;
  final ValueChanged<String?> onTagChanged;
  final ValueChanged<double> onStressChanged;
  final VoidCallback onSave;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.96),
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        boxShadow: const [
          BoxShadow(
            color: Colors.black26,
            blurRadius: 8,
            offset: Offset(0, -2),
          ),
        ],
      ),
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              const Icon(Icons.calendar_today, size: 18),
              const SizedBox(width: 8),
              Text(
                _formatDate(DateTime.now()),
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
            ],
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            initialValue: selectedTag,
            decoration: const InputDecoration(
              labelText: 'Тег',
              border: OutlineInputBorder(),
            ),
            hint: const Text('Без тега'),
            items: tags
                .map(
                  (tag) =>
                      DropdownMenuItem<String>(value: tag, child: Text(tag)),
                )
                .toList(),
            onChanged: onTagChanged,
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              const Icon(Icons.speed, size: 18),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Напряжение: $stressLevel из ${AppConstants.maxStressLevel}',
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
              ),
            ],
          ),
          Slider(
            value: stressLevel.toDouble(),
            min: AppConstants.minStressLevel.toDouble(),
            max: AppConstants.maxStressLevel.toDouble(),
            divisions:
                AppConstants.maxStressLevel - AppConstants.minStressLevel,
            label: stressLevel.toString(),
            onChanged: onStressChanged,
          ),
          TextField(
            controller: noteController,
            minLines: 2,
            maxLines: 4,
            decoration: const InputDecoration(
              labelText: 'Короткая заметка о дне',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: isSaveEnabled ? onSave : null,
              icon: isSaving
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.check),
              label: Text(isSaving ? 'Сохраняю...' : 'Сохранить'),
            ),
          ),
        ],
      ),
    );
  }

  String _formatDate(DateTime date) {
    final day = date.day.toString().padLeft(2, '0');
    final month = date.month.toString().padLeft(2, '0');
    return 'Запись на $day.$month.${date.year}';
  }
}
