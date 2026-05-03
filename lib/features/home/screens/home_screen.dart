import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../../core/constants/app_constants.dart';
import '../../../providers/mood_provider.dart';

const _cream = Color(0xFFFFF8D2);
const _forest = Color(0xFF477C3F);
const _brown = Color(0xFF5F4A32);

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int? _selectedMoodIndex;
  final TextEditingController _commentController = TextEditingController();

  final List<_MoodOption> _moods = const [
    _MoodOption('😢', 'Очень плохо', 'Sad', 9),
    _MoodOption('😟', 'Тревожно', 'Anxious', 8),
    _MoodOption('😔', 'Грустно', 'Sad', 7),
    _MoodOption('😐', 'Нормально', 'Neutral', 5),
    _MoodOption('🙂', 'Спокойно', 'Calm', 3),
    _MoodOption('😊', 'Хорошо', 'Happy', 2),
  ];

  @override
  void dispose() {
    _commentController.dispose();
    super.dispose();
  }

  Future<bool> _saveMood() async {
    if (_selectedMoodIndex == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Сначала выбери настроение')),
      );
      return false;
    }

    final mood = _moods[_selectedMoodIndex!];
    final comment = _commentController.text.trim();

    await context.read<MoodProvider>().addEntry(
          emotion: mood.emotionKey,
          stressLevel: mood.stressLevel,
          note: comment.isEmpty ? null : comment,
        );

    if (!mounted) return false;

    setState(() {
      _selectedMoodIndex = null;
      _commentController.clear();
    });

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Настроение сохранено')),
    );

    return true;
  }

  void _openMoodSheet() {
    int? sheetSelectedIndex = _selectedMoodIndex;

    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (sheetContext) {
        return StatefulBuilder(
          builder: (context, setSheetState) {
            return Padding(
              padding: EdgeInsets.only(
                left: 14,
                right: 14,
                bottom: MediaQuery.of(sheetContext).viewInsets.bottom + 14,
              ),
              child: Container(
                padding: const EdgeInsets.fromLTRB(18, 18, 18, 18),
                decoration: BoxDecoration(
                  color: _cream,
                  borderRadius: BorderRadius.circular(32),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.18),
                      blurRadius: 22,
                      offset: const Offset(0, 8),
                    ),
                  ],
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Text(
                      'Как ты сегодня?',
                      style: TextStyle(
                        color: _brown,
                        fontSize: 24,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 14),
                    Wrap(
                      alignment: WrapAlignment.center,
                      spacing: 8,
                      runSpacing: 8,
                      children: List.generate(_moods.length, (index) {
                        final mood = _moods[index];
                        final selected = sheetSelectedIndex == index;

                        return InkWell(
                          borderRadius: BorderRadius.circular(999),
                          onTap: () {
                            setState(() => _selectedMoodIndex = index);
                            setSheetState(() => sheetSelectedIndex = index);
                          },
                          child: AnimatedContainer(
                            duration: const Duration(milliseconds: 160),
                            width: 50,
                            height: 50,
                            alignment: Alignment.center,
                            decoration: BoxDecoration(
                              color: selected
                                  ? _forest
                                  : Colors.white.withValues(alpha: 0.82),
                              shape: BoxShape.circle,
                            ),
                            child: Text(
                              mood.emoji,
                              style: const TextStyle(fontSize: 24),
                            ),
                          ),
                        );
                      }),
                    ),
                    const SizedBox(height: 14),
                    TextField(
                      controller: _commentController,
                      minLines: 1,
                      maxLines: 3,
                      decoration: InputDecoration(
                        hintText: 'Хочешь добавить пару слов?',
                        filled: true,
                        fillColor: Colors.white.withValues(alpha: 0.78),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(22),
                          borderSide: BorderSide.none,
                        ),
                      ),
                    ),
                    const SizedBox(height: 14),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton(
                        onPressed: () async {
                          final saved = await _saveMood();
                          if (saved && sheetContext.mounted) {
                            Navigator.of(sheetContext).pop();
                          }
                        },
                        style: ElevatedButton.styleFrom(
                          backgroundColor: _forest,
                          foregroundColor: _cream,
                          padding: const EdgeInsets.symmetric(vertical: 15),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(22),
                          ),
                        ),
                        child: const Text(
                          'Сохранить отметку',
                          style: TextStyle(fontWeight: FontWeight.w900),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  void _go(String route) {
    context.go(route);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBody: true,
      resizeToAvoidBottomInset: false,
      body: LayoutBuilder(
        builder: (context, constraints) {
          final width = constraints.maxWidth;
          final height = constraints.maxHeight;

          return Stack(
            children: [
              Positioned.fill(
                child: Image.asset(
                  'assets/images/sheep_diary_bg.jpg',
                  fit: BoxFit.cover,
                  alignment: Alignment.topCenter,
                ),
              ),

              // Кликабельная зона поверх нарисованной шестерёнки.
              Positioned(
                left: width * 0.04,
                top: height * 0.045,
                width: width * 0.24,
                height: height * 0.12,
                child: _TransparentTap(
                  label: 'Настройки',
                  onTap: () => _go(AppRoutes.settings),
                ),
              ),

              // Кликабельная зона поверх нарисованных графиков.
              Positioned(
                left: width * 0.04,
                top: height * 0.17,
                width: width * 0.24,
                height: height * 0.12,
                child: _TransparentTap(
                  label: 'Прогресс',
                  onTap: () => _go(AppRoutes.progress),
                ),
              ),

              // Кликабельная зона поверх нарисованной SOS-кнопки.
              Positioned(
                right: width * 0.04,
                top: height * 0.045,
                width: width * 0.24,
                height: height * 0.12,
                child: _TransparentTap(
                  label: 'SOS',
                  onTap: () => _go(AppRoutes.help),
                ),
              ),

              // Прозрачная зона поверх овечки на самой картинке.
              // Никакой отдельной Flutter-овечки тут больше нет.
              Positioned(
                left: width * 0.36,
                top: height * 0.48,
                width: width * 0.28,
                height: height * 0.17,
                child: _TransparentTap(
                  label: 'Отметить настроение',
                  onTap: _openMoodSheet,
                ),
              ),

              Positioned(
                left: 12,
                right: 12,
                bottom: 10,
                child: _HomeBottomNav(
                  onHome: () {},
                  onChat: () => _go(AppRoutes.chat),
                  onDiary: () => _go(AppRoutes.diary),
                  onTips: () => _go(AppRoutes.tips),
                  onProgress: () => _go(AppRoutes.progress),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _TransparentTap extends StatelessWidget {
  const _TransparentTap({
    required this.label,
    required this.onTap,
  });

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: label,
      child: GestureDetector(
        behavior: HitTestBehavior.translucent,
        onTap: onTap,
        child: const SizedBox.expand(),
      ),
    );
  }
}

class _HomeBottomNav extends StatelessWidget {
  const _HomeBottomNav({
    required this.onHome,
    required this.onChat,
    required this.onDiary,
    required this.onTips,
    required this.onProgress,
  });

  final VoidCallback onHome;
  final VoidCallback onChat;
  final VoidCallback onDiary;
  final VoidCallback onTips;
  final VoidCallback onProgress;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 7),
        decoration: BoxDecoration(
          color: _cream.withValues(alpha: 0.94),
          borderRadius: BorderRadius.circular(30),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.16),
              blurRadius: 18,
              offset: const Offset(0, 7),
            ),
          ],
        ),
        child: Row(
          children: [
            _NavButton(
              icon: Icons.home_rounded,
              label: 'Главная',
              selected: true,
              onTap: onHome,
            ),
            _NavButton(
              icon: Icons.chat_bubble_rounded,
              label: 'Поговорить',
              onTap: onChat,
            ),
            _NavButton(
              icon: Icons.edit_note_rounded,
              label: 'Дневник',
              onTap: onDiary,
            ),
            _NavButton(
              icon: Icons.spa_rounded,
              label: 'Советы',
              onTap: onTips,
            ),
            _NavButton(
              icon: Icons.insights_rounded,
              label: 'Прогресс',
              onTap: onProgress,
            ),
          ],
        ),
      ),
    );
  }
}

class _NavButton extends StatelessWidget {
  const _NavButton({
    required this.icon,
    required this.label,
    required this.onTap,
    this.selected = false,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: InkWell(
        borderRadius: BorderRadius.circular(22),
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 160),
          padding: const EdgeInsets.symmetric(vertical: 8),
          decoration: BoxDecoration(
            color: selected
                ? _forest.withValues(alpha: 0.14)
                : Colors.transparent,
            borderRadius: BorderRadius.circular(22),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                icon,
                size: 22,
                color: selected ? _forest : _brown.withValues(alpha: 0.65),
              ),
              const SizedBox(height: 2),
              Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
                  color: selected ? _forest : _brown.withValues(alpha: 0.72),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _MoodOption {
  const _MoodOption(
    this.emoji,
    this.label,
    this.emotionKey,
    this.stressLevel,
  );

  final String emoji;
  final String label;
  final String emotionKey;
  final int stressLevel;
}