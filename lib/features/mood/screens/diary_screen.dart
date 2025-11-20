import 'package:flutter/material.dart';

/// Diary Screen - Emotion and mood tracking
/// 
/// Алена: Implement diary functionality with:
/// - Emotion selector (from AppConstants.emotions)
/// - Stress level slider (1-10)
/// - Notes text field
/// - Save button
/// - List of previous entries
/// - Edit/delete functionality


class DiaryScreen extends StatefulWidget {
  const DiaryScreen({super.key});

  @override
  State<DiaryScreen> createState() => _DiaryScreenState();
}

class _DiaryScreenState extends State<DiaryScreen> {
  bool _showEmotions = false;
  int? _selectedEmotionIndex;
  String? _selectedTag;
  final TextEditingController _noteController = TextEditingController();

  final List<String> _emotionLabels = [
    'Очень плохо',
    'Так себе',
    'Нормально',
    'Хорошо',
    'Отлично',
  ];

  final List<String> _tags = [
    'Без тега',
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

  void _onSave() {
    // TODO: сохранить в БД
    // Пример структуры:
    // final entry = DiaryEntry(
    //   emotionIndex: _selectedEmotionIndex,
    //   note: _noteController.text,
    //   tag: _selectedTag,
    //   date: DateTime.now(),
    // );

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Запись будет сохранена в БД позже 🙂')),
    );

    // очистка формы (по желанию)
    setState(() {
      _selectedEmotionIndex = null;
      _selectedTag = null;
      _noteController.clear();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mood Diary'),
        backgroundColor: Colors.green.shade700,
        foregroundColor: Colors.white,
      ),
      body: Stack(
        children: [
          // ФОН
          Positioned.fill(
            child: Image.asset(
              'assets/images/sheep_diary_bg.jpg', // <–– твоя картинка с овечкой и травой
              fit: BoxFit.cover,
            ),
          ),

          // Содержимое поверх фона
          SafeArea(
            child: Column(
              children: [
                const SizedBox(height: 24),

                // Центр: овечка + смайлики
                Expanded(
                  child: Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        // Зона клика по овечке
                        GestureDetector(
                          onTap: _onSheepTap,
                          child: SizedBox(
                            width: 160,
                            height: 160,
                            // Прозрачная область поверх овечки на фоне
                            child: Container(
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: Colors.black.withOpacity(0.05),
                              ),
                              alignment: Alignment.center,
                              child: const Text(
                                'нажми на овечку',
                                style: TextStyle(
                                  fontSize: 14,
                                  color: Colors.white,
                                  shadows: [
                                    Shadow(
                                      color: Colors.black54,
                                      blurRadius: 4,
                                      offset: Offset(0, 1),
                                    )
                                  ],
                                ),
                                textAlign: TextAlign.center,
                              ),
                            ),
                          ),
                        ),

                        const SizedBox(height: 24),

                        AnimatedSwitcher(
                          duration: const Duration(milliseconds: 250),
                          child: _showEmotions
                              ? Column(
                                  key: const ValueKey('emotions'),
                                  children: [
                                    const Text(
                                      'Как ты себя чувствуешь?',
                                      style: TextStyle(
                                        fontSize: 18,
                                        fontWeight: FontWeight.w600,
                                        color: Colors.white,
                                        shadows: [
                                          Shadow(
                                            color: Colors.black54,
                                            blurRadius: 4,
                                          )
                                        ],
                                      ),
                                    ),
                                    const SizedBox(height: 12),
                                    Container(
                                      padding: const EdgeInsets.symmetric(
                                        horizontal: 16,
                                        vertical: 8,
                                      ),
                                      decoration: BoxDecoration(
                                        color: Colors.black.withOpacity(0.35),
                                        borderRadius: BorderRadius.circular(32),
                                      ),
                                      child: Row(
                                        mainAxisSize: MainAxisSize.min,
                                        mainAxisAlignment:
                                            MainAxisAlignment.spaceEvenly,
                                        children: List.generate(5, (index) {
                                          final isSelected =
                                              _selectedEmotionIndex == index;
                                          return GestureDetector(
                                            onTap: () => _onEmotionTap(index),
                                            child: AnimatedContainer(
                                              duration: const Duration(
                                                  milliseconds: 150),
                                              margin:
                                                  const EdgeInsets.symmetric(
                                                      horizontal: 4),
                                              padding:
                                                  const EdgeInsets.all(10),
                                              decoration: BoxDecoration(
                                                shape: BoxShape.circle,
                                                color: isSelected
                                                    ? Colors.white
                                                        .withOpacity(0.9)
                                                    : Colors.white
                                                        .withOpacity(0.3),
                                                border: isSelected
                                                    ? Border.all(
                                                        color: Colors.white,
                                                        width: 2,
                                                      )
                                                    : null,
                                              ),
                                              child: Text(
                                                // временно просто эмодзи; потом можно заменить на картинки
                                                ['😢', '🙁', '😐', '🙂', '🤩']
                                                    [index],
                                                style: const TextStyle(
                                                    fontSize: 24),
                                              ),
                                            ),
                                          );
                                        }),
                                      ),
                                    ),
                                    const SizedBox(height: 8),
                                    if (_selectedEmotionIndex != null)
                                      Text(
                                        _emotionLabels[_selectedEmotionIndex!],
                                        style: const TextStyle(
                                          color: Colors.white,
                                          fontSize: 14,
                                          fontWeight: FontWeight.w500,
                                          shadows: [
                                            Shadow(
                                              color: Colors.black54,
                                              blurRadius: 4,
                                            )
                                          ],
                                        ),
                                      ),
                                  ],
                                )
                              : const SizedBox.shrink(),
                        ),
                      ],
                    ),
                  ),
                ),

                // Нижняя карточка с заметкой и тегом
                Container(
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.95),
                    borderRadius: const BorderRadius.vertical(
                      top: Radius.circular(24),
                    ),
                    boxShadow: const [
                      BoxShadow(
                        color: Colors.black26,
                        blurRadius: 8,
                        offset: Offset(0, -2),
                      ),
                    ],
                  ),
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.calendar_today, size: 18),
                          const SizedBox(width: 8),
                          Text(
                            'Запись на ${DateTime.now().day.toString().padLeft(2, '0')}.'
                            '${DateTime.now().month.toString().padLeft(2, '0')}.'
                            '${DateTime.now().year}',
                            style: const TextStyle(
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      DropdownButtonFormField<String>(
                        value: _selectedTag,
                        decoration: const InputDecoration(
                          labelText: 'Тег (для календаря)',
                          border: OutlineInputBorder(),
                        ),
                        items: _tags
                            .map(
                              (tag) => DropdownMenuItem(
                                value: tag == 'Без тега' ? null : tag,
                                child: Text(tag),
                              ),
                            )
                            .toList(),
                        onChanged: (value) {
                          setState(() {
                            _selectedTag = value;
                          });
                        },
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _noteController,
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
                          onPressed: _selectedEmotionIndex == null
                              ? null
                              : _onSave,
                          icon: const Icon(Icons.check),
                          label: const Text('Сохранить (позже в БД)'),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
