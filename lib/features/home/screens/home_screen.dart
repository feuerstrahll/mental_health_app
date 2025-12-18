// R - перезагрузка проги, (без перезапуска) чтобы посмотреть как работает измененное
// q - завершить работу проги
// плсмотреть эмуляторы
// flutter emulators 
// запуск:
// (flutter clean)
// flutter pub get
// flutter run -v -d emulator-5554   (запуск с логами)

import 'package:flutter/material.dart';

import 'package:mental_health_app/features/chat/screens/chat_screen.dart';
import 'package:mental_health_app/features/mood/screens/statistics_screen.dart';
import 'package:mental_health_app/features/help/screens/help_screen.dart';
import 'package:mental_health_app/features/tips/screens/tips_screen.dart';
import 'package:mental_health_app/features/settings/screens/settings_screen.dart';
import 'package:mental_health_app/widgets/mood_selector.dart';
import 'package:mental_health_app/core/constants/app_constants.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  bool _interactionActive = false; // показывать ли смайлы + карточку снизу
  String? _selectedEmotion; // Изменено с int? на String?
  String? _selectedTag;
  final TextEditingController _noteController = TextEditingController();

  final List<String> _emotionLabels = [
    'Очень плохо',
    'Так себе',
    'Нормально',
    'Хорошо',
    'Отлично',
  ];
  
  // Маппинг эмодзи к эмоциям из AppConstants
  final List<String> _emojiToEmotion = ['Sad', 'Sad', 'Neutral', 'Happy', 'Happy'];

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
      _interactionActive = true; // включаем режим выбора эмоции
    });
  }

  void _onEmotionSelected(String emotion) {
    setState(() {
      _selectedEmotion = emotion;
    });
  }

  void _resetUI() {
    setState(() {
      _interactionActive = false;
      _selectedEmotion = null;
      _selectedTag = null;
      _noteController.clear();
    });
  }

  void _onSave() {
    // TODO: сохранить данные в БД (эмоция, тег, заметка, дата)
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Запись будет сохранена в БД позже 🙂')),
    );
    _resetUI(); // после сохранения возвращаем экран в исходное состояние
  }

  void _openMenu() {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (context) {
        return SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const SizedBox(height: 12),
              const Text(
                'Навигация',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 8),
              ListTile(
                leading: const Icon(Icons.smart_toy_outlined),
                title: const Text('ИИ-бот'),
                subtitle: const Text('Поговорить и получить поддержку'),
                onTap: () {
                  Navigator.pop(context);
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => const ChatScreen()),
                  );
                },
              ),
              ListTile(
                leading: const Icon(Icons.bar_chart),
                title: const Text('Статистика'),
                subtitle: const Text('Посмотреть динамику настроения'),
                onTap: () {
                  Navigator.pop(context);
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                        builder: (_) => const StatisticsScreen()),
                  );
                },
              ),
              ListTile(
                leading: const Icon(Icons.help_outline),
                title: const Text('Помощь'),
                subtitle: const Text('Полезная информация и ресурсы'),
                onTap: () {
                  Navigator.pop(context);
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => const HelpScreen()),
                  );
                },
              ),
              ListTile(
                leading: const Icon(Icons.lightbulb_outline),
                title: const Text('Советы'),
                subtitle: const Text('Небольшие рекомендации на каждый день'),
                onTap: () {
                  Navigator.pop(context);
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => const TipsScreen()),
                  );
                },
              ),
              ListTile(
              leading: const Icon(Icons.settings_outlined),
              title: const Text('Настройки'),
              subtitle: const Text('Тема, уведомления и другие опции'),
              onTap: () {
                Navigator.pop(context);
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => const SettingsScreen(),
                  ),
                );
              },
            ),
              const SizedBox(height: 12),
            ],
          ),
        );
      },
    );
  }

  Widget _buildBottomCard(DateTime now) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.96),
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
                'Сегодня: '
                '${now.day.toString().padLeft(2, '0')}.'
                '${now.month.toString().padLeft(2, '0')}.'
                '${now.year}',
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
              labelText: 'Тег для записи (для календаря)',
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
            minLines: 1,
            maxLines: 3,
            decoration: const InputDecoration(
              labelText: 'Короткая подпись к сегодняшней записи',
              hintText: 'Например: «гуляла с друзьями, стало легче»',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed:
                  _selectedEmotion == null ? null : _onSave, // без эмоции не сохраняем
              icon: const Icon(Icons.check),
              label: const Text('Сохранить настроение'),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Твой день'),
        backgroundColor: Colors.green.shade700,
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: Stack(
        children: [
          // Фон с овечкой
          Positioned.fill(
            child: Image.asset(
              'assets/images/sheep_diary_bg.jpg',
              fit: BoxFit.cover,
            ),
          ),

          SafeArea(
            child: Column(
              children: [
                // Верхняя часть: овечка + смайлы
                Expanded(
                  child: Stack(
                    children: [
                      // Тап по свободному месту скрывает эмоции/карточку
                      GestureDetector(
                        behavior: HitTestBehavior.opaque,
                        onTap: () {
                          if (_interactionActive) {
                            _resetUI();
                          }
                        },
                        child: Container(),
                      ),

                      // Круг в районе овечки
                      Align(
                        alignment: const Alignment(0, 0.55),
                        child: GestureDetector(
                          onTap: _onSheepTap,
                          child: SizedBox(
                            width: 160,
                            height: 160,
                            child: Container(
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: Colors.black.withOpacity(0.12),
                              ),
                              alignment: Alignment.center,
                              child: const Text(
                                'нажми на овечку',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 14,
                                  shadows: [
                                    Shadow(
                                      color: Colors.black54,
                                      blurRadius: 4,
                                    ),
                                  ],
                                ),
                                textAlign: TextAlign.center,
                              ),
                            ),
                          ),
                        ),
                      ),

                      // Смайлики под овечкой
                      Align(
                        alignment: const Alignment(0, 0.9),
                        child: AnimatedSwitcher(
                          duration: const Duration(milliseconds: 220),
                          child: _interactionActive
                              ? MoodSelector(
                                  key: const ValueKey('home_emotions'),
                                  selectedEmotion: _selectedEmotion,
                                  onEmotionSelected: _onEmotionSelected,
                                  style: EmotionSelectorStyle.emoji,
                                  emotionLabels: _emotionLabels,
                                )
                              : const SizedBox.shrink(),
                        ),
                      ),
                    ],
                  ),
                ),

                // Нижняя карточка появляется только в режиме взаимодействия
                AnimatedSwitcher(
                  duration: const Duration(milliseconds: 220),
                  child: _interactionActive
                      ? _buildBottomCard(now)
                      : const SizedBox.shrink(),
                ),
              ],
            ),
          ),
        ],
      ),

      // Кружок-меню снизу
      floatingActionButton: FloatingActionButton(
        onPressed: _openMenu,
        child: const Icon(Icons.menu),
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerFloat,
    );
  }
}
