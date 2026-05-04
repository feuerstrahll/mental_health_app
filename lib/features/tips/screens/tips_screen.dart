import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/constants/app_constants.dart';
import '../../../providers/settings_provider.dart';
import '../../../widgets/app_shell.dart';

class TipsScreen extends StatefulWidget {
  const TipsScreen({super.key});

  @override
  State<TipsScreen> createState() => _TipsScreenState();
}

class _TipsScreenState extends State<TipsScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  Offset _dragOffset = Offset.zero;
  Offset _animStart = Offset.zero;
  Offset _animEnd = Offset.zero;
  bool _animatingOut = false;
  int _currentIndex = 0;

  final List<_Tip> _tips = const [
    _Tip(
      id: 'breath_46',
      title: 'Дыхание 4–6',
      description:
          'Сделай 6 спокойных циклов: вдох на 4 счёта и мягкий выдох на 6.',
      why: 'Подходит в моменты тревоги и внутреннего напряжения.',
      minutes: 3,
      illustrationPath: 'assets/images/ui/tips/breath_46.png',
    ),
    _Tip(
      id: 'walk_light',
      title: 'Свет и воздух',
      description:
          'Выйди на 5 минут на улицу или подойди к окну с дневным светом.',
      why: 'Полезно, если день кажется вязким и энергии мало.',
      minutes: 5,
      illustrationPath: 'assets/images/ui/tips/walk_light.png',
    ),
    _Tip(
      id: 'tiny_step',
      title: 'Один маленький шаг',
      description:
          'Выбери очень маленькое действие на 2 минуты: вода, душ, один ответ, один файл.',
      why: 'Помогает, когда всё кажется слишком большим и тяжёлым.',
      minutes: 2,
      illustrationPath: 'assets/images/ui/tips/tiny_step.png',
    ),
    _Tip(
      id: 'body_reset',
      title: 'Мягкая встряска',
      description:
          'Потянись, расправь плечи, встряхни кисти и сделай пару глубоких выдохов.',
      why: 'Хорошо, если тело зажато и голова перегружена.',
      minutes: 1,
      illustrationPath: 'assets/images/ui/tips/body_reset.png',
    ),
  ];

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 320),
    )..addListener(() {
        if (!mounted) return;
        setState(() {
          _dragOffset = Offset.lerp(_animStart, _animEnd, _controller.value)!;
        });
      });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _mark(_Tip tip, String reaction, double width) async {
    if (_animatingOut) return;

    setState(() {
      _animatingOut = true;
      _animStart = _dragOffset;
      _animEnd = Offset(
        reaction == 'helped' ? width * 1.08 : -width * 1.08,
        190,
      );
    });

    await _controller.forward(from: 0);
    if (!mounted) return;

    _controller.reset();
    setState(() {
      _currentIndex = (_currentIndex + 1) % _tips.length;
      _dragOffset = Offset.zero;
      _animatingOut = false;
    });

    await context.read<SettingsProvider>().saveTipFeedback(tip.id, reaction);
  }

  void _showPractice(_Tip tip) {
    showModalBottomSheet(
      context: context,
      showDragHandle: true,
      backgroundColor: AppColors.card,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
      ),
      builder: (context) => Padding(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              tip.title,
              style: const TextStyle(
                color: AppColors.brown,
                fontSize: 24,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: 10),
            Text(
              tip.description,
              style: const TextStyle(
                color: AppColors.brown,
                height: 1.35,
              ),
            ),
            const SizedBox(height: 14),
            Text(
              'Займёт около ${tip.minutes} мин.',
              style: const TextStyle(
                color: AppColors.forest,
                fontWeight: FontWeight.w800,
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<SettingsProvider>(
      builder: (context, settings, _) {
        final current = _tips[_currentIndex % _tips.length];
        final next = _tips[(_currentIndex + 1) % _tips.length];

        return AppShell(
          title: 'Советы',
          currentRoute: AppRoutes.tips,
          backgroundColor: AppColors.sage,
          child: LayoutBuilder(
            builder: (context, constraints) {
              final width = constraints.maxWidth - 32;
              final cardOffset = _dragOffset;
              final rotation = (cardOffset.dx / width) * 0.18;
              final nextScale =
                  (_dragOffset.dx.abs() / width).clamp(0.0, 1.0) * 0.04;

              return Padding(
                padding: const EdgeInsets.fromLTRB(16, 18, 16, 116),
                child: Stack(
                  clipBehavior: Clip.none,
                  alignment: Alignment.center,
                  children: [
                    Positioned(
                      left: 10,
                      right: 10,
                      top: 26,
                      bottom: 10,
                      child: Transform.scale(
                        scale: 0.95 + nextScale,
                        child: Opacity(
                          opacity: 0.72,
                          child: _TipCard(
                            key: ValueKey('back_${next.id}'),
                            tip: next,
                            ghost: true,
                            onTry: null,
                            onHelped: null,
                            onBad: null,
                            onLater: null,
                          ),
                        ),
                      ),
                    ),
                    GestureDetector(
                      onPanUpdate: _animatingOut
                          ? null
                          : (details) {
                              setState(() {
                                _dragOffset += details.delta;
                              });
                            },
                      onPanEnd: _animatingOut
                          ? null
                          : (_) {
                              final absDx = _dragOffset.dx.abs();
                              if (absDx > 70) {
                                _mark(
                                  current,
                                  _dragOffset.dx > 0 ? 'helped' : 'bad',
                                  width,
                                );
                              } else {
                                setState(() => _dragOffset = Offset.zero);
                              }
                            },
                      child: Transform.translate(
                        offset: Offset(
                          cardOffset.dx,
                          cardOffset.dy + (cardOffset.dx.abs() * 0.16),
                        ),
                        child: Transform.rotate(
                          angle: rotation,
                          child: _TipCard(
                            key: ValueKey('front_${current.id}'),
                            tip: current,
                            onTry: () => _showPractice(current),
                            onHelped: () => _mark(current, 'helped', width),
                            onBad: () => _mark(current, 'bad', width),
                            onLater: () async {
                              setState(() {
                                _currentIndex = (_currentIndex + 1) % _tips.length;
                              });
                              await context
                                  .read<SettingsProvider>()
                                  .saveTipFeedback(current.id, 'later');
                            },
                          ),
                        ),
                      ),
                    ),
                    Positioned(
                      top: 18,
                      left: 0,
                      child: AnimatedOpacity(
                        duration: const Duration(milliseconds: 120),
                        opacity: _dragOffset.dx < -20 ? 1 : 0,
                        child: const _Badge(text: 'Не помогло'),
                      ),
                    ),
                    Positioned(
                      top: 18,
                      right: 0,
                      child: AnimatedOpacity(
                        duration: const Duration(milliseconds: 120),
                        opacity: _dragOffset.dx > 20 ? 1 : 0,
                        child: const _Badge(text: 'Помогло'),
                      ),
                    ),
                  ],
                ),
              );
            },
          ),
        );
      },
    );
  }
}

class _TipCard extends StatelessWidget {
  const _TipCard({
    super.key,
    required this.tip,
    this.ghost = false,
    required this.onTry,
    required this.onHelped,
    required this.onBad,
    required this.onLater,
  });

  final _Tip tip;
  final bool ghost;
  final VoidCallback? onTry;
  final VoidCallback? onHelped;
  final VoidCallback? onBad;
  final VoidCallback? onLater;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      height: double.infinity,
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(30),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(ghost ? 0.04 : 0.12),
            blurRadius: 18,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 54,
                height: 54,
                decoration: const BoxDecoration(
                  color: Color(0xFFE9F2D7),
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.spa_rounded,
                  color: AppColors.forest,
                  size: 28,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  tip.title,
                  style: const TextStyle(
                    color: AppColors.brown,
                    fontSize: 26,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
              Text(
                '${tip.minutes} мин',
                style: const TextStyle(
                  color: AppColors.forest,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          Text(
            tip.description,
            style: const TextStyle(
              color: AppColors.brown,
              fontSize: 22,
              height: 1.35,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFFEAF3D5),
              borderRadius: BorderRadius.circular(22),
            ),
            child: Text(
              tip.why,
              style: const TextStyle(
                color: AppColors.brown,
                fontSize: 16,
                height: 1.35,
              ),
            ),
          ),
          const SizedBox(height: 18),
          Expanded(
            child: SizedBox(
              width: double.infinity,
              child: Image.asset(
                tip.illustrationPath,
                fit: BoxFit.contain,
                alignment: Alignment.center,
                errorBuilder: (context, error, stackTrace) {
                  return const SizedBox.shrink();
                },
              ),
            ),
          ),
          const SizedBox(height: 16),
          if (!ghost) ...[
            const Text(
              'Проведи карточку вправо или влево — так мы запомним реакцию.',
              style: TextStyle(
                color: AppColors.brown,
                height: 1.3,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                ElevatedButton(
                  onPressed: onTry,
                  child: const Text('Попробовать'),
                ),
                TextButton(
                  onPressed: onLater,
                  child: const Text('Позже'),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _Badge extends StatelessWidget {
  const _Badge({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: AppColors.forest, width: 1.3),
      ),
      child: Text(
        text,
        style: const TextStyle(
          color: AppColors.forest,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }
}

class _Tip {
  const _Tip({
    required this.id,
    required this.title,
    required this.description,
    required this.why,
    required this.minutes,
    required this.illustrationPath,
  });

  final String id;
  final String title;
  final String description;
  final String why;
  final int minutes;
  final String illustrationPath;
}
