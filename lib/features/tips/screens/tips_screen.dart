import 'package:flutter/material.dart';

import '../../../core/constants/app_constants.dart';
import '../../../widgets/app_shell.dart';

class TipsScreen extends StatefulWidget {
  const TipsScreen({super.key});

  @override
  State<TipsScreen> createState() => _TipsScreenState();
}

class _TipsScreenState extends State<TipsScreen> {
  final Map<int, String> _feedback = {};

  final List<_Tip> _tips = const [
    _Tip(
      title: 'Дыхание 4–6',
      description: 'Вдох на 4 счёта, выдох на 6. Повтори 6–8 раз.',
      why: 'Рекомендовано, потому что последние дни ты отмечала тревогу и плохой сон.',
      minutes: 3,
    ),
    _Tip(
      title: 'Мягкая прогулка',
      description: 'Выйди на улицу хотя бы на 5 минут или подойди к окну с дневным светом.',
      why: 'Рекомендовано для поддержки ритма дня и энергии.',
      minutes: 5,
    ),
    _Tip(
      title: 'Один маленький шаг',
      description: 'Выбери одну простую задачу, которую можно закрыть за 2 минуты.',
      why: 'Рекомендовано, если день кажется хаотичным.',
      minutes: 2,
    ),
  ];

  void _setFeedback(int index, String value) {
    setState(() => _feedback[index] = value);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(value == 'helped' ? 'Отмечено: помогло' : 'Отмечено: не подходит')),
    );
  }

  void _tryTip(_Tip tip) {
    showModalBottomSheet(
      context: context,
      showDragHandle: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(28))),
      builder: (context) => Padding(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(tip.title, style: const TextStyle(color: AppColors.brown, fontSize: 24, fontWeight: FontWeight.w900)),
            const SizedBox(height: 10),
            Text(tip.description, style: const TextStyle(color: AppColors.brown, height: 1.35)),
            const SizedBox(height: 16),
            Text('Время: около ${tip.minutes} мин.', style: const TextStyle(color: AppColors.forest, fontWeight: FontWeight.w800)),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AppShell(
      title: 'Советы',
      currentRoute: AppRoutes.tips,
      backgroundColor: AppColors.sage,
      child: ListView.separated(
        padding: const EdgeInsets.fromLTRB(16, 18, 16, 118),
        itemCount: _tips.length + 1,
        separatorBuilder: (_, __) => const SizedBox(height: 12),
        itemBuilder: (context, index) {
          if (index == 0) {
            return const SoftCard(
              color: Color(0xFFFFEFC8),
              child: Text(
                'Персональные рекомендации будут подстраиваться под дневник и реакции: помогло / не подходит.',
                style: TextStyle(color: AppColors.brown, fontWeight: FontWeight.w700, height: 1.3),
              ),
            );
          }

          final tipIndex = index - 1;
          final tip = _tips[tipIndex];
          return Dismissible(
            key: ValueKey(tip.title),
            background: const _SwipeBackground(text: 'Помогло', alignment: Alignment.centerLeft, icon: Icons.thumb_up_rounded),
            secondaryBackground: const _SwipeBackground(text: 'Не подходит', alignment: Alignment.centerRight, icon: Icons.block_rounded),
            confirmDismiss: (direction) async {
              _setFeedback(tipIndex, direction == DismissDirection.startToEnd ? 'helped' : 'bad');
              return false;
            },
            child: _TipCard(
              tip: tip,
              feedback: _feedback[tipIndex],
              onTry: () => _tryTip(tip),
              onHelped: () => _setFeedback(tipIndex, 'helped'),
              onLater: () => ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Ок, можно вернуться позже'))),
              onBad: () => _setFeedback(tipIndex, 'bad'),
            ),
          );
        },
      ),
    );
  }
}

class _TipCard extends StatelessWidget {
  const _TipCard({
    required this.tip,
    required this.feedback,
    required this.onTry,
    required this.onHelped,
    required this.onLater,
    required this.onBad,
  });

  final _Tip tip;
  final String? feedback;
  final VoidCallback onTry;
  final VoidCallback onHelped;
  final VoidCallback onLater;
  final VoidCallback onBad;

  @override
  Widget build(BuildContext context) {
    return SoftCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.spa_rounded, color: AppColors.forest),
              const SizedBox(width: 8),
              Expanded(child: Text(tip.title, style: const TextStyle(color: AppColors.brown, fontSize: 20, fontWeight: FontWeight.w900))),
              Text('${tip.minutes} мин', style: const TextStyle(color: AppColors.forest, fontWeight: FontWeight.w800)),
            ],
          ),
          const SizedBox(height: 8),
          Text(tip.description, style: const TextStyle(color: AppColors.brown, height: 1.3)),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: AppColors.sage, borderRadius: BorderRadius.circular(18)),
            child: Text(tip.why, style: const TextStyle(color: AppColors.brown, fontSize: 13, height: 1.3)),
          ),
          if (feedback != null) ...[
            const SizedBox(height: 8),
            Text(
              feedback == 'helped' ? 'Ты отметила: помогло' : 'Ты отметила: не подходит',
              style: const TextStyle(color: AppColors.forest, fontWeight: FontWeight.w800),
            ),
          ],
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              ElevatedButton(onPressed: onTry, child: const Text('Попробовать')),
              OutlinedButton(onPressed: onHelped, child: const Text('Помогло')),
              OutlinedButton(onPressed: onLater, child: const Text('Не сейчас')),
              TextButton(onPressed: onBad, child: const Text('Не подходит')),
            ],
          ),
        ],
      ),
    );
  }
}

class _SwipeBackground extends StatelessWidget {
  const _SwipeBackground({required this.text, required this.alignment, required this.icon});

  final String text;
  final Alignment alignment;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      alignment: alignment,
      padding: const EdgeInsets.symmetric(horizontal: 22),
      decoration: BoxDecoration(color: AppColors.forest.withOpacity(0.18), borderRadius: BorderRadius.circular(26)),
      child: Row(
        mainAxisAlignment: alignment == Alignment.centerLeft ? MainAxisAlignment.start : MainAxisAlignment.end,
        children: [
          Icon(icon, color: AppColors.forest),
          const SizedBox(width: 8),
          Text(text, style: const TextStyle(color: AppColors.forest, fontWeight: FontWeight.w900)),
        ],
      ),
    );
  }
}

class _Tip {
  const _Tip({required this.title, required this.description, required this.why, required this.minutes});

  final String title;
  final String description;
  final String why;
  final int minutes;
}
