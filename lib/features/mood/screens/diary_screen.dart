import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/constants/app_constants.dart';
import '../../../providers/mood_provider.dart';
import '../../../widgets/mood_selector.dart';

/// Diary Screen - Emotion and mood tracking
class DiaryScreen extends StatefulWidget {
  const DiaryScreen({super.key});

  @override
  State<DiaryScreen> createState() => _DiaryScreenState();
}

class _DiaryScreenState extends State<DiaryScreen> {
  String _selectedFilter = 'all'; // 'all', 'today', 'week', 'month'

  /// Открывает диалог для добавления новой записи настроения
  void _showAddMoodDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => const _AddMoodEntryDialog(),
    );
  }

  /// Открывает диалог для редактирования записи
  void _showEditMoodDialog(BuildContext context, MoodEntry entry) {
    showDialog(
      context: context,
      builder: (context) => _AddMoodEntryDialog(entry: entry),
    );
  }

  /// Показывает диалог подтверждения удаления
  Future<void> _showDeleteConfirmationDialog(
    BuildContext context,
    MoodProvider moodProvider,
    MoodEntry entry,
  ) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Удалить запись?'),
        content: Text(
          'Вы уверены, что хотите удалить запись от '
          '${entry.timestamp.day}.${entry.timestamp.month}.${entry.timestamp.year}?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Отмена'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Удалить'),
          ),
        ],
      ),
    );

    if (confirmed == true && context.mounted) {
      try {
        await moodProvider.deleteEntry(entry.id);
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Запись удалена'),
              backgroundColor: Colors.green,
            ),
          );
        }
      } catch (error) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Ошибка при удалении: $error'),
              backgroundColor: Colors.red,
            ),
          );
        }
      }
    }
  }

  /// Фильтрует записи по выбранному периоду
  List<MoodEntry> _filterEntries(List<MoodEntry> entries) {
    final now = DateTime.now();
    switch (_selectedFilter) {
      case 'today':
        final today = DateTime(now.year, now.month, now.day);
        return entries.where((entry) {
          final entryDate = DateTime(
            entry.timestamp.year,
            entry.timestamp.month,
            entry.timestamp.day,
          );
          return entryDate.isAtSameMomentAs(today);
        }).toList();
      case 'week':
        final weekAgo = now.subtract(const Duration(days: 7));
        return entries.where((entry) => entry.timestamp.isAfter(weekAgo)).toList();
      case 'month':
        final monthAgo = now.subtract(const Duration(days: 30));
        return entries.where((entry) => entry.timestamp.isAfter(monthAgo)).toList();
      default:
        return entries;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mood Diary'),
        backgroundColor: Colors.green.shade700,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: () => _showAddMoodDialog(context),
            tooltip: 'Добавить запись',
          ),
        ],
      ),
      body: Stack(
        children: [
          // ФОН
          Positioned.fill(
            child: Image.asset(
              'assets/images/sheep_diary_bg.jpg',
              fit: BoxFit.cover,
            ),
          ),

          // Содержимое поверх фона
          SafeArea(
            child: Consumer<MoodProvider>(
              builder: (context, moodProvider, child) {
                // Состояние загрузки
                if (moodProvider.isLoading) {
                  return const Center(
                    child: CircularProgressIndicator(),
                  );
                }

                // Состояние ошибки
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
                            style: const TextStyle(
                              color: Colors.red,
                              fontSize: 16,
                            ),
                          ),
                          const SizedBox(height: 24),
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

                // Фильтрация записей
                final filteredEntries = _filterEntries(moodProvider.entries);

                // Пустое состояние
                if (filteredEntries.isEmpty) {
                  return Column(
                    children: [
                      const SizedBox(height: 24),
                      Expanded(
                        child: Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              GestureDetector(
                                onTap: () => _showAddMoodDialog(context),
                                child: Container(
                                  width: 160,
                                  height: 160,
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
                              const SizedBox(height: 16),
                              const Text(
                                'Нажми на овечку, чтобы\nдобавить запись настроения',
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 16,
                                  shadows: [
                                    Shadow(
                                      color: Colors.black54,
                                      blurRadius: 4,
                                    )
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                      Container(
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.95),
                          borderRadius: const BorderRadius.vertical(
                            top: Radius.circular(24),
                          ),
                        ),
                        padding: const EdgeInsets.all(24),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(
                              Icons.edit_note,
                              size: 64,
                              color: Colors.grey,
                            ),
                            const SizedBox(height: 16),
                            Text(
                              moodProvider.entries.isEmpty
                                  ? 'Пока нет записей'
                                  : 'Нет записей за выбранный период',
                              style: const TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 8),
                            ElevatedButton.icon(
                              onPressed: () => _showAddMoodDialog(context),
                              icon: const Icon(Icons.add),
                              label: const Text('Добавить первую запись'),
                            ),
                          ],
                        ),
                      ),
                    ],
                  );
                }

                // Список записей
                return Column(
                  children: [
                    // Фильтр по дате
                    Container(
                      margin: const EdgeInsets.all(16),
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 8,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.95),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                        children: [
                          _FilterChip(
                            label: 'Все',
                            isSelected: _selectedFilter == 'all',
                            onTap: () => setState(() => _selectedFilter = 'all'),
                          ),
                          _FilterChip(
                            label: 'Сегодня',
                            isSelected: _selectedFilter == 'today',
                            onTap: () => setState(() => _selectedFilter = 'today'),
                          ),
                          _FilterChip(
                            label: 'Неделя',
                            isSelected: _selectedFilter == 'week',
                            onTap: () => setState(() => _selectedFilter = 'week'),
                          ),
                          _FilterChip(
                            label: 'Месяц',
                            isSelected: _selectedFilter == 'month',
                            onTap: () => setState(() => _selectedFilter = 'month'),
                          ),
                        ],
                      ),
                    ),

                    // Список записей
                    Expanded(
                      child: Container(
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.95),
                          borderRadius: const BorderRadius.vertical(
                            top: Radius.circular(24),
                          ),
                        ),
                        child: Column(
                          children: [
                            Padding(
                              padding: const EdgeInsets.all(16),
                              child: Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Text(
                                    'Записей: ${filteredEntries.length}',
                                    style: const TextStyle(
                                      fontSize: 16,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            Expanded(
                              child: ListView.builder(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 16,
                                  vertical: 8,
                                ),
                                itemCount: filteredEntries.length,
                                itemBuilder: (context, index) {
                                  final entry = filteredEntries[index];
                                  return _MoodEntryCard(
                                    entry: entry,
                                    onEdit: () => _showEditMoodDialog(context, entry),
                                    onDelete: () => _showDeleteConfirmationDialog(
                                      context,
                                      moodProvider,
                                      entry,
                                    ),
                                  );
                                },
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                );
              },
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showAddMoodDialog(context),
        backgroundColor: Colors.green.shade700,
        child: const Icon(Icons.add),
      ),
    );
  }
}

/// Виджет для фильтра по дате
class _FilterChip extends StatelessWidget {
  final String label;
  final bool isSelected;
  final VoidCallback onTap;

  const _FilterChip({
    required this.label,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected ? Colors.green.shade700 : Colors.grey.shade200,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: isSelected ? Colors.white : Colors.black87,
            fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
            fontSize: 12,
          ),
        ),
      ),
    );
  }
}

/// Карточка записи настроения
class _MoodEntryCard extends StatelessWidget {
  final MoodEntry entry;
  final VoidCallback onEdit;
  final VoidCallback onDelete;

  const _MoodEntryCard({
    required this.entry,
    required this.onEdit,
    required this.onDelete,
  });

  String _formatDateTime(DateTime dateTime) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final entryDate = DateTime(
      dateTime.year,
      dateTime.month,
      dateTime.day,
    );

    final time = '${dateTime.hour.toString().padLeft(2, '0')}:'
        '${dateTime.minute.toString().padLeft(2, '0')}';

    if (entryDate.isAtSameMomentAs(today)) {
      return 'Сегодня в $time';
    } else if (entryDate == today.subtract(const Duration(days: 1))) {
      return 'Вчера в $time';
    } else {
      return '${dateTime.day}.${dateTime.month}.${dateTime.year} в $time';
    }
  }

  @override
  Widget build(BuildContext context) {
    final emotionColor =
        AppConstants.emotionColors[entry.emotion] ?? Colors.grey;

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      elevation: 2,
      child: InkWell(
        onLongPress: onEdit,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Заголовок: эмоция и дата
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: emotionColor.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      entry.emotion,
                      style: TextStyle(
                        color: emotionColor,
                        fontWeight: FontWeight.bold,
                        fontSize: 16,
                      ),
                    ),
                  ),
                  const Spacer(),
                  Text(
                    _formatDateTime(entry.timestamp),
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.grey.shade600,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),

              // Уровень стресса
              Row(
                children: [
                  const Icon(
                    Icons.sentiment_very_dissatisfied,
                    size: 16,
                    color: Colors.grey,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    'Уровень стресса: ',
                    style: TextStyle(
                      fontSize: 14,
                      color: Colors.grey.shade700,
                    ),
                  ),
                  Text(
                    '${entry.stressLevel}/10',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      color: entry.stressLevel > 7
                          ? Colors.red
                          : entry.stressLevel > 4
                              ? Colors.orange
                              : Colors.green,
                    ),
                  ),
                  const Spacer(),
                  // Визуальный индикатор стресса
                  SizedBox(
                    width: 100,
                    child: LinearProgressIndicator(
                      value: entry.stressLevel / 10,
                      backgroundColor: Colors.grey.shade200,
                      valueColor: AlwaysStoppedAnimation<Color>(
                        entry.stressLevel > 7
                            ? Colors.red
                            : entry.stressLevel > 4
                                ? Colors.orange
                                : Colors.green,
                      ),
                    ),
                  ),
                ],
              ),

              // Заметка
              if (entry.note != null && entry.note!.isNotEmpty) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.grey.shade100,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(
                        Icons.note,
                        size: 16,
                        color: Colors.grey,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          entry.note!,
                          style: TextStyle(
                            fontSize: 14,
                            color: Colors.grey.shade800,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],

              // Кнопки действий
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton.icon(
                    onPressed: onEdit,
                    icon: const Icon(Icons.edit, size: 16),
                    label: const Text('Редактировать'),
                    style: TextButton.styleFrom(
                      foregroundColor: Colors.blue,
                    ),
                  ),
                  const SizedBox(width: 8),
                  TextButton.icon(
                    onPressed: onDelete,
                    icon: const Icon(Icons.delete, size: 16),
                    label: const Text('Удалить'),
                    style: TextButton.styleFrom(
                      foregroundColor: Colors.red,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Диалог для добавления/редактирования записи настроения
class _AddMoodEntryDialog extends StatefulWidget {
  final MoodEntry? entry; // Если передан, то режим редактирования

  const _AddMoodEntryDialog({this.entry});

  @override
  State<_AddMoodEntryDialog> createState() => _AddMoodEntryDialogState();
}

class _AddMoodEntryDialogState extends State<_AddMoodEntryDialog> {
  late String? _selectedEmotion;
  late double _stressLevel;
  late final TextEditingController _noteController;
  bool _isSaving = false;
  bool get _isEditMode => widget.entry != null;

  @override
  void initState() {
    super.initState();
    if (_isEditMode) {
      // Режим редактирования: заполняем поля существующими значениями
      _selectedEmotion = widget.entry!.emotion;
      _stressLevel = widget.entry!.stressLevel.toDouble();
      _noteController = TextEditingController(text: widget.entry!.note ?? '');
    } else {
      // Режим добавления: значения по умолчанию
      _selectedEmotion = null;
      _stressLevel = 5.0;
      _noteController = TextEditingController();
    }
  }

  @override
  void dispose() {
    _noteController.dispose();
    super.dispose();
  }

  Future<void> _saveEntry() async {
    // Валидация: эмоция обязательна
    if (_selectedEmotion == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Пожалуйста, выберите эмоцию'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    setState(() {
      _isSaving = true;
    });

    try {
      final moodProvider = context.read<MoodProvider>();

      if (_isEditMode) {
        // Режим редактирования
        final noteText = _noteController.text.trim();
        final updatedEntry = MoodEntry(
          id: widget.entry!.id,
          emotion: _selectedEmotion!,
          stressLevel: _stressLevel.round(),
          timestamp: widget.entry!.timestamp, // Сохраняем оригинальную дату
          note: noteText.isEmpty ? null : noteText,
        );
        await moodProvider.updateEntry(updatedEntry);

        if (mounted) {
          Navigator.of(context).pop();
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Запись успешно обновлена! ✅'),
              backgroundColor: Colors.green,
              duration: Duration(seconds: 2),
            ),
          );
        }
      } else {
        // Режим добавления
        await moodProvider.addEntry(
          emotion: _selectedEmotion!,
          stressLevel: _stressLevel.round(),
          note: _noteController.text.trim().isEmpty
              ? null
              : _noteController.text.trim(),
        );

        if (mounted) {
          Navigator.of(context).pop();
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Запись успешно сохранена! ✅'),
              backgroundColor: Colors.green,
              duration: Duration(seconds: 2),
            ),
          );
        }
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              _isEditMode
                  ? 'Ошибка при обновлении: $error'
                  : 'Ошибка при сохранении: $error',
            ),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isSaving = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Заголовок
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  _isEditMode ? 'Редактировать запись' : 'Новая запись настроения',
                  style: const TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.close),
                  onPressed: _isSaving ? null : () => Navigator.of(context).pop(),
                ),
              ],
            ),
            const SizedBox(height: 24),

            // Выбор эмоции
            const Text(
              'Эмоция *',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 12),
            MoodSelector(
              selectedEmotion: _selectedEmotion,
              onEmotionSelected: (emotion) {
                setState(() {
                  _selectedEmotion = emotion;
                });
              },
              style: EmotionSelectorStyle.chips,
            ),
            const SizedBox(height: 24),

            // Слайдер уровня стресса
            Text(
              'Уровень стресса: ${_stressLevel.round()}/10',
              style: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 12),
            Slider(
              value: _stressLevel,
              min: AppConstants.minStressLevel.toDouble(),
              max: AppConstants.maxStressLevel.toDouble(),
              divisions: 9,
              label: _stressLevel.round().toString(),
              onChanged: (value) {
                setState(() {
                  _stressLevel = value;
                });
              },
            ),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  '${AppConstants.minStressLevel}',
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.grey.shade600,
                  ),
                ),
                Text(
                  '${AppConstants.maxStressLevel}',
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.grey.shade600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),

            // Поле для комментария
            TextField(
              controller: _noteController,
              minLines: 3,
              maxLines: 5,
              decoration: const InputDecoration(
                labelText: 'Заметка (необязательно)',
                hintText: 'Опишите, что произошло сегодня...',
                border: OutlineInputBorder(),
              ),
              enabled: !_isSaving,
            ),
            const SizedBox(height: 24),

            // Кнопка сохранения
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _isSaving ? null : _saveEntry,
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  backgroundColor: Colors.green.shade700,
                  foregroundColor: Colors.white,
                ),
                child: _isSaving
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                        ),
                      )
                    : Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(_isEditMode ? Icons.update : Icons.check),
                          const SizedBox(width: 8),
                          Text(
                            _isEditMode ? 'Обновить' : 'Сохранить',
                            style: const TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
