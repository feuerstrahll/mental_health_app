import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../../core/constants/app_constants.dart';
import '../../../providers/mood_provider.dart';
import '../../../widgets/app_shell.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int? _selectedMoodIndex;
  bool _sheepJumped = false;
  final TextEditingController _commentController = TextEditingController();

  final List<_MoodOption> _moods = const [
    _MoodOption('😣', 'Очень плохо', 'Sad', 9),
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

  Future<void> _saveMood() async {
    if (_selectedMoodIndex == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Сначала выбери состояние')),
      );
      return;
    }

    final mood = _moods[_selectedMoodIndex!];
    final comment = _commentController.text.trim();

    await context.read<MoodProvider>().addEntry(
          emotion: mood.emotionKey,
          stressLevel: mood.stressLevel,
          note: comment.isEmpty ? null : comment,
        );

    if (!mounted) return;

    setState(() {
      _selectedMoodIndex = null;
      _commentController.clear();
    });

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Отметка сохранена')),
    );
  }

  void _animateSheep() {
    setState(() => _sheepJumped = true);
    Future.delayed(const Duration(milliseconds: 430), () {
      if (mounted) setState(() => _sheepJumped = false);
    });
  }

  @override
  Widget build(BuildContext context) {
    return AppShell(
      currentRoute: AppRoutes.home,
      showAppBar: false,
      backgroundColor: AppColors.grass,
      child: Stack(
        children: [
          const Positioned.fill(child: _GrassBackground()),
          SafeArea(
            bottom: false,
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(18, 18, 18, 110),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: 40),
                  const Text(
                    'Привет, [name]!',
                    style: TextStyle(
                      color: AppColors.cream,
                      fontSize: 34,
                      fontWeight: FontWeight.w800,
                      fontStyle: FontStyle.italic,
                      shadows: [Shadow(color: Colors.black26, blurRadius: 4, offset: Offset(0, 2))],
                    ),
                  ),
                  const SizedBox(height: 18),
                  const _SupportCloud(),
                  const SizedBox(height: 18),
                  Center(
                    child: GestureDetector(
                      onTap: _animateSheep,
                      child: AnimatedSlide(
                        duration: const Duration(milliseconds: 220),
                        offset: _sheepJumped ? const Offset(0, -0.16) : Offset.zero,
                        curve: Curves.easeOutBack,
                        child: AnimatedScale(
                          duration: const Duration(milliseconds: 220),
                          scale: _sheepJumped ? 1.08 : 1,
                          child: const _SheepCharacter(),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 18),
                  SoftCard(
                    color: AppColors.card.withOpacity(0.92),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Как ты сегодня?',
                          style: TextStyle(
                            color: AppColors.brown,
                            fontSize: 24,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                        const SizedBox(height: 12),
                        _MoodSelector(
                          moods: _moods,
                          selectedIndex: _selectedMoodIndex,
                          onSelected: (index) => setState(() => _selectedMoodIndex = index),
                        ),
                        const SizedBox(height: 14),
                        TextField(
                          controller: _commentController,
                          minLines: 1,
                          maxLines: 3,
                          decoration: InputDecoration(
                            hintText: 'Хочешь добавить пару слов?',
                            filled: true,
                            fillColor: Colors.white.withOpacity(0.75),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(18),
                              borderSide: BorderSide.none,
                            ),
                          ),
                        ),
                        const SizedBox(height: 12),
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton.icon(
                            onPressed: _saveMood,
                            icon: const Icon(Icons.check_rounded),
                            label: const Text('Сохранить состояние'),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: AppColors.forest,
                              foregroundColor: AppColors.cream,
                              padding: const EdgeInsets.symmetric(vertical: 14),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 14),
                  const _SmallSupportCard(),
                  const SizedBox(height: 14),
                  SoftCard(
                    onTap: () => context.go(AppRoutes.chat),
                    color: const Color(0xFFFFE8B5),
                    child: Row(
                      children: [
                        Container(
                          width: 56,
                          height: 56,
                          decoration: const BoxDecoration(color: Colors.white, shape: BoxShape.circle),
                          child: const Icon(Icons.chat_bubble_rounded, color: AppColors.forest, size: 30),
                        ),
                        const SizedBox(width: 14),
                        const Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Поговорить',
                                style: TextStyle(
                                  color: AppColors.brown,
                                  fontSize: 23,
                                  fontWeight: FontWeight.w900,
                                ),
                              ),
                              SizedBox(height: 4),
                              Text('Открыть уютный чат с ИИ-помощником'),
                            ],
                          ),
                        ),
                        const Icon(Icons.arrow_forward_ios_rounded, color: AppColors.brown, size: 18),
                      ],
                    ),
                  ),
                  const SizedBox(height: 14),
                  Row(
                    children: [
                      Expanded(
                        child: _QuickAction(
                          label: 'Заполнить день',
                          icon: Icons.edit_note_rounded,
                          onTap: () => context.go(AppRoutes.diary),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _QuickAction(
                          label: 'Совет на 3 минуты',
                          icon: Icons.spa_rounded,
                          onTap: () => context.go(AppRoutes.tips),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  _QuickAction(
                    label: 'Посмотреть прогресс',
                    icon: Icons.insights_rounded,
                    onTap: () => context.go(AppRoutes.progress),
                    wide: true,
                  ),
                ],
              ),
            ),
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

class _MoodSelector extends StatelessWidget {
  const _MoodSelector({
    required this.moods,
    required this.selectedIndex,
    required this.onSelected,
  });

  final List<_MoodOption> moods;
  final int? selectedIndex;
  final ValueChanged<int> onSelected;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: List.generate(moods.length, (index) {
        final mood = moods[index];
        final selected = selectedIndex == index;
        return GestureDetector(
          onTap: () => onSelected(index),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 160),
            width: 48,
            height: 48,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: selected ? AppColors.forest : Colors.white.withOpacity(0.72),
              shape: BoxShape.circle,
              border: Border.all(
                color: selected ? AppColors.cream : AppColors.brown.withOpacity(0.18),
                width: selected ? 2 : 1,
              ),
            ),
            child: Text(mood.emoji, style: const TextStyle(fontSize: 24)),
          ),
        );
      }),
    );
  }
}

class _SupportCloud extends StatelessWidget {
  const _SupportCloud();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(24, 18, 24, 18),
      decoration: BoxDecoration(
        color: AppColors.cream.withOpacity(0.92),
        borderRadius: BorderRadius.circular(42),
      ),
      child: const Text(
        'Тут будут вдохновляющие фразы, цитаты или поддерживающие слова. Они берутся заранее и показываются в кофе-стиле.',
        textAlign: TextAlign.center,
        style: TextStyle(
          color: AppColors.brown,
          fontSize: 16,
          height: 1.35,
          fontStyle: FontStyle.italic,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

class _SmallSupportCard extends StatelessWidget {
  const _SmallSupportCard();

  @override
  Widget build(BuildContext context) {
    return const SoftCard(
      child: Row(
        children: [
          Icon(Icons.favorite_rounded, color: Color(0xFFD86A6A), size: 30),
          SizedBox(width: 12),
          Expanded(
            child: Text(
              'Ты не обязана разбираться со всем сразу. Можно начать с одного маленького шага.',
              style: TextStyle(color: AppColors.brown, fontSize: 15, height: 1.25),
            ),
          ),
        ],
      ),
    );
  }
}

class _QuickAction extends StatelessWidget {
  const _QuickAction({
    required this.label,
    required this.icon,
    required this.onTap,
    this.wide = false,
  });

  final String label;
  final IconData icon;
  final VoidCallback onTap;
  final bool wide;

  @override
  Widget build(BuildContext context) {
    return SoftCard(
      onTap: onTap,
      padding: EdgeInsets.symmetric(horizontal: 14, vertical: wide ? 16 : 14),
      child: Row(
        mainAxisAlignment: wide ? MainAxisAlignment.start : MainAxisAlignment.center,
        children: [
          Icon(icon, color: AppColors.forest),
          const SizedBox(width: 8),
          Flexible(
            child: Text(
              label,
              textAlign: wide ? TextAlign.left : TextAlign.center,
              style: const TextStyle(fontWeight: FontWeight.w800, color: AppColors.brown),
            ),
          ),
        ],
      ),
    );
  }
}

class _SheepCharacter extends StatelessWidget {
  const _SheepCharacter();

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 116,
      height: 104,
      child: Stack(
        alignment: Alignment.center,
        children: [
          Positioned(
            bottom: 8,
            left: 24,
            child: Container(width: 12, height: 28, decoration: BoxDecoration(color: Colors.black87, borderRadius: BorderRadius.circular(8))),
          ),
          Positioned(
            bottom: 8,
            right: 24,
            child: Container(width: 12, height: 28, decoration: BoxDecoration(color: Colors.black87, borderRadius: BorderRadius.circular(8))),
          ),
          Positioned(
            top: 18,
            left: 8,
            child: Transform.rotate(
              angle: -0.45,
              child: Container(width: 32, height: 20, decoration: BoxDecoration(color: const Color(0xFFC184A8), borderRadius: BorderRadius.circular(20))),
            ),
          ),
          Positioned(
            top: 18,
            right: 8,
            child: Transform.rotate(
              angle: 0.45,
              child: Container(width: 32, height: 20, decoration: BoxDecoration(color: const Color(0xFFC184A8), borderRadius: BorderRadius.circular(20))),
            ),
          ),
          Container(
            width: 92,
            height: 78,
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(36),
              boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.12), blurRadius: 8, offset: const Offset(0, 4))],
            ),
          ),
          Positioned(
            top: 36,
            child: Container(
              width: 44,
              height: 40,
              decoration: BoxDecoration(color: Colors.black87, borderRadius: BorderRadius.circular(22)),
              child: const Center(
                child: Text('⌣  ⌣', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12)),
              ),
            ),
          ),
          Positioned(
            top: 0,
            right: 22,
            child: Transform.rotate(
              angle: 0.25,
              child: const Text('♥', style: TextStyle(fontSize: 34, color: Colors.red)),
            ),
          ),
        ],
      ),
    );
  }
}

class _GrassBackground extends StatelessWidget {
  const _GrassBackground();

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      painter: _GrassPainter(),
      child: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFF2F8D3A), Color(0xFF8ABF68), Color(0xFF477C3F)],
          ),
        ),
      ),
    );
  }
}

class _GrassPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final bladePaint = Paint()
      ..color = AppColors.lightGrass.withOpacity(0.35)
      ..strokeWidth = 2
      ..strokeCap = StrokeCap.round;
    final hillPaint = Paint()..color = const Color(0xFF3F7938).withOpacity(0.55);

    for (double x = 12; x < size.width; x += 34) {
      for (double y = 130; y < size.height; y += 88) {
        canvas.drawLine(Offset(x, y), Offset(x + 8, y - 18), bladePaint);
        canvas.drawLine(Offset(x + 9, y), Offset(x + 1, y - 16), bladePaint);
      }
    }

    final topPath = Path()..moveTo(0, 190);
    for (double x = 0; x <= size.width + 30; x += 28) {
      topPath.lineTo(x + 14, 158);
      topPath.lineTo(x + 28, 190);
    }
    topPath.lineTo(size.width, 0);
    topPath.lineTo(0, 0);
    topPath.close();
    canvas.drawPath(topPath, hillPaint);

    final bottomPath = Path()..moveTo(0, size.height - 92);
    for (double x = 0; x <= size.width + 30; x += 30) {
      bottomPath.lineTo(x + 15, size.height - 128);
      bottomPath.lineTo(x + 30, size.height - 92);
    }
    bottomPath.lineTo(size.width, size.height);
    bottomPath.lineTo(0, size.height);
    bottomPath.close();
    canvas.drawPath(bottomPath, hillPaint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
