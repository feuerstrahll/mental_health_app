import 'package:flutter/material.dart';

import '../core/constants/app_constants.dart';

/// Виджет для выбора эмоции/настроения
/// 
/// Поддерживает два режима отображения:
/// - [EmotionSelectorStyle.chips] - чипсы с названиями эмоций (для форм)
/// - [EmotionSelectorStyle.emoji] - эмодзи с подписями (для главного экрана)
class MoodSelector extends StatelessWidget {
  const MoodSelector({
    super.key,
    required this.selectedEmotion,
    required this.onEmotionSelected,
    this.style = EmotionSelectorStyle.chips,
    this.emotionLabels,
  });

  /// Выбранная эмоция (null если ничего не выбрано)
  final String? selectedEmotion;
  
  /// Callback при выборе эмоции
  final ValueChanged<String> onEmotionSelected;
  
  /// Стиль отображения
  final EmotionSelectorStyle style;
  
  /// Кастомные подписи для эмодзи (только для emoji стиля)
  /// Если не указано, используются стандартные эмодзи
  final List<String>? emotionLabels;

  @override
  Widget build(BuildContext context) {
    switch (style) {
      case EmotionSelectorStyle.chips:
        return _buildChipsStyle();
      case EmotionSelectorStyle.emoji:
        return _buildEmojiStyle();
    }
  }

  /// Стиль чипсов - для форм и диалогов
  Widget _buildChipsStyle() {
    return Wrap(
      spacing: 12,
      runSpacing: 12,
      children: AppConstants.emotions.map((emotion) {
        final isSelected = selectedEmotion == emotion;
        final color = AppConstants.emotionColors[emotion] ?? Colors.grey;
        return GestureDetector(
          onTap: () => onEmotionSelected(emotion),
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: 16,
              vertical: 12,
            ),
            decoration: BoxDecoration(
              color: isSelected ? color : color.withOpacity(0.2),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: isSelected ? color : Colors.grey.shade300,
                width: isSelected ? 2 : 1,
              ),
            ),
            child: Text(
              emotion,
              style: TextStyle(
                color: isSelected ? Colors.white : Colors.black87,
                fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
              ),
            ),
          ),
        );
      }).toList(),
    );
  }

  /// Стиль эмодзи - для главного экрана
  Widget _buildEmojiStyle() {
    final emojis = ['😢', '🙁', '😐', '🙂', '🤩'];
    final labels = emotionLabels ?? ['Очень плохо', 'Так себе', 'Нормально', 'Хорошо', 'Отлично'];
    
    // Маппинг эмодзи к эмоциям (упрощенный)
    final emotionMap = {
      0: 'Sad',
      1: 'Sad',
      2: 'Neutral',
      3: 'Happy',
      4: 'Happy',
    };
    
    // Находим индекс выбранной эмоции
    int? selectedIndex;
    if (selectedEmotion != null) {
      for (int i = 0; i < emotionMap.length; i++) {
        if (emotionMap[i] == selectedEmotion) {
          selectedIndex = i;
          break;
        }
      }
    }

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
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
            children: List.generate(emojis.length, (index) {
              final emotion = emotionMap[index] ?? 'Neutral';
              final isSelected = selectedEmotion == emotion;
              return GestureDetector(
                onTap: () => onEmotionSelected(emotion),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 150),
                  margin: const EdgeInsets.symmetric(horizontal: 4),
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: isSelected
                        ? Colors.white.withOpacity(0.9)
                        : Colors.white.withOpacity(0.3),
                    border: isSelected
                        ? Border.all(
                            color: Colors.white,
                            width: 2,
                          )
                        : null,
                  ),
                  child: Text(
                    emojis[index],
                    style: const TextStyle(
                      fontSize: 24,
                    ),
                  ),
                ),
              );
            }),
          ),
        ),
        if (selectedIndex != null && selectedIndex < labels.length) ...[
          const SizedBox(height: 8),
          Text(
            labels[selectedIndex],
            style: const TextStyle(
              color: Colors.white,
              fontSize: 16,
              fontWeight: FontWeight.bold,
              shadows: [
                Shadow(
                  color: Colors.black54,
                  blurRadius: 4,
                ),
              ],
            ),
          ),
        ],
      ],
    );
  }
}

/// Стиль отображения селектора эмоций
enum EmotionSelectorStyle {
  /// Чипсы с названиями эмоций (для форм)
  chips,
  
  /// Эмодзи с подписями (для главного экрана)
  emoji,
}

