import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../../core/constants/app_constants.dart';
import '../../../core/services/home_support_service.dart';
import '../../../providers/mood_provider.dart';
import '../../../providers/settings_provider.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with WidgetsBindingObserver {
  final TextEditingController _commentController = TextEditingController();
  final FocusNode _commentFocusNode = FocusNode();
  final HomeSupportService _supportService = HomeSupportService();

  int? _selectedMoodIndex;
  String _supportText = 'Загружаю поддерживающую фразу...';
  bool _supportLoading = true;
  bool _showKeyboardDock = false;
  bool _waitingForKeyboardOpen = false;

  final List<_MoodOption> _moods = const [
    _MoodOption('assets/images/ui/emoji_cry.png', 'Очень плохо', 'Sad', 10),
    _MoodOption('assets/images/ui/emoji_sad.png', 'Грустно', 'Sad', 8),
    _MoodOption('assets/images/ui/emoji_worried.png', 'Тревожно', 'Anxious', 9),
    _MoodOption('assets/images/ui/emoji_neutral.png', 'Нормально', 'Neutral', 5),
    _MoodOption('assets/images/ui/emoji_calm.png', 'Спокойно', 'Calm', 3),
    _MoodOption('assets/images/ui/emoji_happy.png', 'Хорошо', 'Happy', 2),
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _commentFocusNode.addListener(_handleCommentFocusChange);
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadSupportText());
  }

  @override
  void didChangeMetrics() {
    super.didChangeMetrics();
    final view = WidgetsBinding.instance.platformDispatcher.views.first;
    final keyboardBottom = view.viewInsets.bottom / view.devicePixelRatio;

    if (keyboardBottom > 0) {
      _waitingForKeyboardOpen = false;
      return;
    }

    if (!_showKeyboardDock || _waitingForKeyboardOpen) return;

    if (_commentController.text.trim().isEmpty) {
      _commentFocusNode.unfocus();
    }

    if (mounted) {
      setState(() => _showKeyboardDock = false);
    }
  }

  void _handleCommentFocusChange() {
    if (!mounted) return;
    if (_waitingForKeyboardOpen) return;
    if (!_commentFocusNode.hasFocus && _showKeyboardDock) {
      setState(() => _showKeyboardDock = false);
    }
  }

  void _openCommentDock() {
    _waitingForKeyboardOpen = true;
    setState(() => _showKeyboardDock = true);

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        _commentFocusNode.requestFocus();
      }
    });

    Future.delayed(const Duration(milliseconds: 1200), () {
      if (mounted && _waitingForKeyboardOpen) {
        _waitingForKeyboardOpen = false;
      }
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _commentFocusNode.removeListener(_handleCommentFocusChange);
    _commentController.dispose();
    _commentFocusNode.dispose();
    super.dispose();
  }

  Future<void> _loadSupportText() async {
    if (!mounted) return;
    setState(() => _supportLoading = true);

    final settings = context.read<SettingsProvider>();
    final moodProvider = context.read<MoodProvider>();
    final latestEntry = moodProvider.entries.isEmpty
        ? null
        : moodProvider.entries.first;

    final text = await _supportService.loadSupportText(
      userName: settings.displayName,
      latestEntry: latestEntry,
    );

    if (!mounted) return;
    setState(() {
      _supportText = text;
      _supportLoading = false;
    });
  }

  Future<void> _saveMood() async {
    if (_selectedMoodIndex == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Выбери настроение')),
      );
      return;
    }

    final mood = _moods[_selectedMoodIndex!];
    final note = _commentController.text.trim();

    await context.read<MoodProvider>().addEntry(
      emotion: mood.emotionKey,
      stressLevel: mood.stressLevel,
      note: note.isEmpty ? null : note,
    );

    if (!mounted) return;

    _commentFocusNode.unfocus();

    setState(() {
      _selectedMoodIndex = null;
      _waitingForKeyboardOpen = false;
      _showKeyboardDock = false;
      _commentController.clear();
    });

    await _loadSupportText();

    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('День сохранён')),
    );
  }

  void _go(String route) => context.go(route);

  @override
  Widget build(BuildContext context) {
    final topInset = MediaQuery.of(context).padding.top;
    final keyboardInset = MediaQuery.of(context).viewInsets.bottom;
    final keyboardOpen = keyboardInset > 0;
    final showKeyboardDock = keyboardOpen || _showKeyboardDock;
    final userName = context.watch<SettingsProvider>().displayName;

    return Scaffold(
      resizeToAvoidBottomInset: false,
      backgroundColor: const Color(0xFF93BC68),
      body: Stack(
        children: [
          Positioned.fill(
            child: Image.asset(
              'assets/images/home_new/bg_meadow.png',
              fit: BoxFit.cover,
            ),
          ),
          Positioned(
            left: 0,
            right: 0,
            top: 0,
            child: Container(
              height: topInset + 56,
              color: const Color(0xFF2F8C3A),
            ),
          ),
          Positioned(
            left: 16,
            right: 16,
            top: topInset + 10,
            child: Text(
              'Привет, $userName!',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                fontSize: 22,
                color: Color(0xFFF7F2DB),
                fontWeight: FontWeight.w700,
                fontStyle: FontStyle.italic,
              ),
            ),
          ),
          Positioned(
            left: 8,
            right: 8,
            top: topInset + 68,
            child: _CloudTipCard(
              text: _supportText,
              loading: _supportLoading,
              onRefresh: _loadSupportText,
            ),
          ),
          Positioned(
            left: 8,
            top: topInset + 188,
            child: _AssetButton(
              assetPath: 'assets/images/home_new/btn_settings.png',
              width: 112,
              height: 112,
              onTap: () => _go(AppRoutes.settings),
            ),
          ),
          Positioned(
            left: 8,
            top: topInset + 306,
            child: _AssetButton(
              assetPath: 'assets/images/home_new/btn_statistics.png',
              width: 112,
              height: 112,
              onTap: () => _go(AppRoutes.progress),
            ),
          ),
          Positioned(
            right: 8,
            top: topInset + 188,
            child: _AssetButton(
              assetPath: 'assets/images/home_new/btn_sos.png',
              width: 112,
              height: 112,
              onTap: () => _go(AppRoutes.help),
            ),
          ),
          Positioned(
            left: 112,
            right: 112,
            top: topInset + 316,
            height: 80,
            child: _RunningSheep(onTap: () {}),
          ),
          Positioned(
            left: 6,
            right: 6,
            bottom: 238,
            child: _MoodQuestionArc(
              moods: _moods,
              selectedIndex: _selectedMoodIndex,
              onSelected: (index) {
                setState(() => _selectedMoodIndex = index);
              },
            ),
          ),
          Positioned(
            left: 24,
            right: 24,
            bottom: 174,
            child: _CommentLauncher(
              controller: _commentController,
              onTap: _openCommentDock,
              onSave: _saveMood,
            ),
          ),
          if (!showKeyboardDock)
            const Positioned(
              left: 24,
              right: 24,
              bottom: 146,
              child: Text(
                'опиши свое самочувствие, не стесняйся',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Color(0xFFF7F2DB),
                  fontSize: 14,
                  fontStyle: FontStyle.italic,
                  shadows: [
                    Shadow(color: Color(0x33000000), blurRadius: 1),
                  ],
                ),
              ),
            ),
          Positioned(
            left: 0,
            bottom: 0,
            child: _AssetButton(
              assetPath: 'assets/images/home_new/btn_diary.png',
              width: 154,
              height: 136,
              onTap: () => _go(AppRoutes.diary),
            ),
          ),
          Positioned(
            right: 0,
            bottom: 0,
            child: _AssetButton(
              assetPath: 'assets/images/home_new/btn_chat.png',
              width: 154,
              height: 136,
              onTap: () => _go(AppRoutes.chat),
            ),
          ),
          Positioned(
            left: 0,
            right: 0,
            bottom: 12,
            child: Center(
              child: _AssetButton(
                assetPath: 'assets/images/home_new/btn_tips.png',
                width: 96,
                height: 96,
                onTap: () => _go(AppRoutes.tips),
              ),
            ),
          ),
          if (showKeyboardDock)
            Positioned(
              left: 12,
              right: 12,
              bottom: keyboardInset + 8,
              child: _KeyboardInputDock(
                controller: _commentController,
                focusNode: _commentFocusNode,
                onSave: _saveMood,
              ),
            ),
        ],
      ),
    );
  }
}

class _CloudTipCard extends StatelessWidget {
  const _CloudTipCard({
    required this.text,
    required this.loading,
    required this.onRefresh,
  });

  final String text;
  final bool loading;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onRefresh,
      borderRadius: BorderRadius.circular(36),
      child: SizedBox(
        height: 126,
        child: Stack(
          children: [
            Positioned.fill(
              child: Image.asset(
                'assets/images/home_new/tip_cloud.png',
                fit: BoxFit.fill,
              ),
            ),
            Positioned(
              left: 72,
              right: 72,
              top: 30,
              bottom: 28,
              child: Align(
                alignment: Alignment.center,
                child: Text(
                  loading ? 'Подбираю совет...' : text,
                  textAlign: TextAlign.center,
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Color(0xFF5A4C43),
                    fontSize: 15,
                    height: 1.2,
                    fontStyle: FontStyle.italic,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _AssetButton extends StatelessWidget {
  const _AssetButton({
    required this.assetPath,
    required this.width,
    required this.height,
    required this.onTap,
  });

  final String assetPath;
  final double width;
  final double height;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(28),
        child: SizedBox(
          width: width,
          height: height,
          child: FittedBox(
            fit: BoxFit.contain,
            child: Image.asset(assetPath),
          ),
        ),
      ),
    );
  }
}

class _MoodQuestionArc extends StatelessWidget {
  const _MoodQuestionArc({
    required this.moods,
    required this.selectedIndex,
    required this.onSelected,
  });

  final List<_MoodOption> moods;
  final int? selectedIndex;
  final ValueChanged<int> onSelected;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 186,
      child: LayoutBuilder(
        builder: (context, constraints) {
          final width = constraints.maxWidth;
          final radius = min(width / 2 - 26, 168.0);
          final center = Offset(width / 2, 174);
          const start = 3.58;
          const end = 5.84;
          final step = (end - start) / (moods.length - 1);

          return Stack(
            clipBehavior: Clip.none,
            children: [
              CustomPaint(
                size: Size(width, 186),
                painter: _ArcPainter(radius: radius),
              ),
              const Positioned(
                left: 74,
                right: 74,
                top: 86,
                child: Text(
                  'Какое у тебя настроение\nсегодня?',
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  style: TextStyle(
                    color: Color(0xFFF7F2DB),
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    fontStyle: FontStyle.italic,
                    height: 1.05,
                    shadows: [
                      Shadow(color: Color(0x33000000), blurRadius: 1),
                    ],
                  ),
                ),
              ),
              for (int i = 0; i < moods.length; i++)
                Positioned(
                  left: center.dx + cos(start + step * i) * radius - 35,
                  top: center.dy + sin(start + step * i) * radius - 35,
                  child: GestureDetector(
                    onTap: () => onSelected(i),
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 180),
                      width: 70,
                      height: 70,
                      decoration: BoxDecoration(
                        color: selectedIndex == i
                            ? const Color(0xFFF7E9BC)
                            : const Color(0x33FFF7E9),
                        shape: BoxShape.circle,
                        border: Border.all(
                          color: const Color(0xFFF7E9BC),
                          width: selectedIndex == i ? 2 : 1.4,
                        ),
                      ),
                      padding: const EdgeInsets.all(6),
                      clipBehavior: Clip.antiAlias,
                      child: Center(
                        child: Image.asset(
                          moods[i].assetPath,
                          fit: BoxFit.contain,
                          alignment: Alignment.center,
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
}

class _ArcPainter extends CustomPainter {
  const _ArcPainter({required this.radius});

  final double radius;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = const Color(0xFFF7E9BC)
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;

    final rect = Rect.fromCircle(
      center: Offset(size.width / 2, 172),
      radius: radius,
    );
    canvas.drawArc(rect, 3.58, 2.26, false, paint);
  }

  @override
  bool shouldRepaint(covariant _ArcPainter oldDelegate) {
    return oldDelegate.radius != radius;
  }
}

class _CommentLauncher extends StatelessWidget {
  const _CommentLauncher({
    required this.controller,
    required this.onTap,
    required this.onSave,
  });

  final TextEditingController controller;
  final VoidCallback onTap;
  final VoidCallback onSave;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        height: 64,
        decoration: BoxDecoration(
          color: const Color(0x22000000),
          borderRadius: BorderRadius.circular(22),
          border: Border.all(color: const Color(0xFFF7E9BC), width: 2),
        ),
        child: Row(
          children: [
            Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: ValueListenableBuilder<TextEditingValue>(
                  valueListenable: controller,
                  builder: (context, value, _) {
                    final text = value.text.trim();
                    return Text(
                      text.isEmpty ? 'Хочешь добавить пару слов?' : text,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: text.isEmpty
                            ? const Color(0xE6F7F2DB)
                            : const Color(0xFFF7F2DB),
                        fontSize: 16,
                      ),
                    );
                  },
                ),
              ),
            ),
            IconButton(
              onPressed: onSave,
              icon: const Icon(
                Icons.check_circle_rounded,
                color: Color(0xFFF7E9BC),
                size: 30,
              ),
            ),
            const SizedBox(width: 4),
          ],
        ),
      ),
    );
  }
}

class _KeyboardInputDock extends StatelessWidget {
  const _KeyboardInputDock({
    required this.controller,
    required this.focusNode,
    required this.onSave,
  });

  final TextEditingController controller;
  final FocusNode focusNode;
  final VoidCallback onSave;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: Container(
        padding: const EdgeInsets.fromLTRB(10, 8, 10, 8),
        decoration: BoxDecoration(
          color: const Color(0xFFF7E9BC),
          borderRadius: BorderRadius.circular(24),
          boxShadow: const [
            BoxShadow(
              color: Color(0x22000000),
              blurRadius: 10,
              offset: Offset(0, 2),
            ),
          ],
        ),
        child: Row(
          children: [
            Expanded(
              child: TextField(
                controller: controller,
                focusNode: focusNode,
                maxLines: 2,
                minLines: 1,
                style: const TextStyle(
                  color: Color(0xFF5A4C43),
                  fontSize: 16,
                ),
                decoration: const InputDecoration(
                  hintText: 'Хочешь добавить пару слов?',
                  hintStyle: TextStyle(color: Color(0xAA5A4C43)),
                  border: InputBorder.none,
                  contentPadding: EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 12,
                  ),
                ),
              ),
            ),
            IconButton(
              onPressed: onSave,
              icon: const Icon(
                Icons.check_circle_rounded,
                color: Color(0xFF7B8D4A),
                size: 30,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _RunningSheep extends StatefulWidget {
  const _RunningSheep({required this.onTap});

  final VoidCallback onTap;

  @override
  State<_RunningSheep> createState() => _RunningSheepState();
}

class _RunningSheepState extends State<_RunningSheep>
    with TickerProviderStateMixin {
  late final AnimationController _moveController;
  late final AnimationController _heartController;
  Timer? _hideHeartsTimer;
  bool _showHearts = false;

  @override
  void initState() {
    super.initState();
    _moveController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 14),
    )..repeat(reverse: true);
    _heartController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    );
  }

  @override
  void dispose() {
    _moveController.dispose();
    _heartController.dispose();
    _hideHeartsTimer?.cancel();
    super.dispose();
  }

  void _handleTap() {
    widget.onTap();
    setState(() => _showHearts = true);
    _heartController.forward(from: 0);
    _hideHeartsTimer?.cancel();
    _hideHeartsTimer = Timer(const Duration(milliseconds: 1500), () {
      if (mounted) {
        setState(() => _showHearts = false);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final maxX = max(0.0, constraints.maxWidth - 62 - 24);

        return AnimatedBuilder(
          animation: Listenable.merge([_moveController, _heartController]),
          builder: (context, child) {
            final progress = Curves.easeInOut.transform(_moveController.value);
            final x = 12 + maxX * progress;
            final heartRise = 14 * _heartController.value;
            final sway = sin(_moveController.value * 2 * pi) * 0.12;
            final nearTurn =
                _moveController.value < 0.08 || _moveController.value > 0.92;
            final stepMirror = nearTurn
                ? 1.0
                : (((_moveController.value * 20).floor() % 2 == 0)
                    ? 1.0
                    : -1.0);

            return Stack(
              clipBehavior: Clip.none,
              children: [
                Positioned(
                  left: x,
                  top: 8 + sin(_moveController.value * 2 * pi) * 1.5,
                  child: GestureDetector(
                    behavior: HitTestBehavior.opaque,
                    onTap: _handleTap,
                    child: SizedBox(
                      width: 62,
                      height: 62,
                      child: Stack(
                        clipBehavior: Clip.none,
                        children: [
                          if (_showHearts)
                            Positioned(
                              left: 24,
                              top: -14 - heartRise,
                              child: Opacity(
                                opacity: 1 - (_heartController.value * 0.35),
                                child: SizedBox(
                                  width: 24,
                                  height: 24,
                                  child: Image.asset(
                                    'assets/images/ui/hearts.png',
                                    fit: BoxFit.contain,
                                  ),
                                ),
                              ),
                            ),
                          Transform.rotate(
                            angle: sway,
                            child: Transform(
                              alignment: Alignment.center,
                              transform: Matrix4.identity()
                                ..scale(stepMirror, 1.0),
                              child: Image.asset(
                                'assets/images/ui/sheep.png',
                                fit: BoxFit.contain,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            );
          },
        );
      },
    );
  }
}

class _MoodOption {
  const _MoodOption(
    this.assetPath,
    this.label,
    this.emotionKey,
    this.stressLevel,
  );

  final String assetPath;
  final String label;
  final String emotionKey;
  final int stressLevel;
}
