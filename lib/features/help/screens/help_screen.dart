import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/constants/app_constants.dart';
import '../../../widgets/app_shell.dart';

class HelpScreen extends StatelessWidget {
  const HelpScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return AppShell(
      title: 'Помощь',
      currentRoute: AppRoutes.help,
      backgroundColor: const Color(0xFFFFEFEF),
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 18, 16, 118),
        children: [
          const SoftCard(
            color: Color(0xFFFFD6D6),
            child: Text(
              'Если есть риск для жизни или безопасности — звони в местные экстренные службы. Этот экран не заменяет профессиональную помощь.',
              style: TextStyle(
                color: Color(0xFF7A2525),
                fontWeight: FontWeight.w800,
                height: 1.35,
              ),
            ),
          ),
          const SizedBox(height: 12),
          _HelpAction(
            icon: Icons.priority_high_rounded,
            title: 'Мне очень плохо сейчас',
            subtitle: 'Открыть быстрый план безопасности',
            route: AppRoutes.helpSafety,
          ),
          _HelpAction(
            icon: Icons.air_rounded,
            title: 'Дыхание на 1 минуту',
            subtitle: 'Короткая практика для стабилизации',
            route: AppRoutes.helpBreathing,
          ),
          _HelpAction(
            icon: Icons.touch_app_rounded,
            title: 'Заземление 5–4–3–2–1',
            subtitle: 'Вернуться вниманием в настоящий момент',
            route: AppRoutes.helpGrounding,
          ),
          _HelpAction(
            icon: Icons.phone_in_talk_rounded,
            title: 'Связаться с близким',
            subtitle: 'Напомнить себе, кому можно написать',
            route: AppRoutes.helpContact,
          ),
          _HelpAction(
            icon: Icons.local_phone_rounded,
            title: 'Кризисные контакты',
            subtitle: 'Горячие линии и экстренная помощь',
            route: AppRoutes.helpCrisis,
          ),
        ],
      ),
    );
  }
}

class HelpDetailScreen extends StatelessWidget {
  const HelpDetailScreen({super.key, required this.kind});

  final String kind;

  @override
  Widget build(BuildContext context) {
    final detail = _detailFor(kind);

    return AppShell(
      title: detail.title,
      currentRoute: AppRoutes.help,
      backgroundColor: const Color(0xFFFFEFEF),
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 18, 16, 118),
        children: [
          SoftCard(
            color: detail.warning ? const Color(0xFFFFD6D6) : AppColors.card,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(detail.icon, color: detail.warning ? const Color(0xFFC75D5D) : AppColors.forest, size: 34),
                const SizedBox(height: 10),
                Text(
                  detail.title,
                  style: const TextStyle(
                    color: AppColors.brown,
                    fontSize: 22,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  detail.description,
                  style: const TextStyle(
                    color: AppColors.brown,
                    height: 1.35,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          for (final step in detail.steps)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: SoftCard(
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.check_circle_rounded, color: AppColors.forest),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        step,
                        style: const TextStyle(
                          color: AppColors.brown,
                          height: 1.35,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          const SizedBox(height: 4),
          OutlinedButton.icon(
            onPressed: () => context.go(AppRoutes.help),
            icon: const Icon(Icons.arrow_back_rounded),
            label: const Text('Назад к помощи'),
          ),
        ],
      ),
    );
  }
}

class _HelpAction extends StatelessWidget {
  const _HelpAction({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.route,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final String route;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: SoftCard(
        onTap: () => context.go(route),
        child: Row(
          children: [
            Container(
              width: 48,
              height: 48,
              decoration: const BoxDecoration(
                color: Color(0xFFFFEFEF),
                shape: BoxShape.circle,
              ),
              child: Icon(icon, color: const Color(0xFFC75D5D)),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      color: AppColors.brown,
                      fontWeight: FontWeight.w900,
                      fontSize: 16,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    subtitle,
                    style: const TextStyle(
                      color: AppColors.brown,
                      height: 1.25,
                    ),
                  ),
                ],
              ),
            ),
            const Icon(Icons.arrow_forward_ios_rounded, color: AppColors.brown, size: 16),
          ],
        ),
      ),
    );
  }
}

_HelpDetail _detailFor(String kind) {
  switch (kind) {
    case 'breathing':
      return const _HelpDetail(
        title: 'Дыхание на 1 минуту',
        icon: Icons.air_rounded,
        description: 'Короткая практика, чтобы немного стабилизироваться здесь и сейчас.',
        steps: [
          'Сядь удобнее и поставь стопы на пол.',
          'Вдохни носом на 4 счёта.',
          'Медленно выдохни на 6 счётов.',
          'Повтори 6 раз. Не нужно делать идеально.',
        ],
      );
    case 'grounding':
      return const _HelpDetail(
        title: 'Заземление 5–4–3–2–1',
        icon: Icons.touch_app_rounded,
        description: 'Практика помогает вернуть внимание к реальности вокруг.',
        steps: [
          'Назови 5 предметов, которые видишь.',
          'Назови 4 ощущения тела: стопы, ладони, спина, дыхание.',
          'Назови 3 звука вокруг.',
          'Назови 2 запаха или вкуса.',
          'Назови 1 действие, которое можешь сделать сейчас.',
        ],
      );
    case 'contact':
      return const _HelpDetail(
        title: 'Связаться с близким',
        icon: Icons.phone_in_talk_rounded,
        description: 'Иногда безопаснее не оставаться одному/одной с тяжёлым состоянием.',
        steps: [
          'Выбери одного человека, кому можно написать без объяснений.',
          'Сообщение может быть простым: «Мне сейчас тяжело, можешь побыть на связи?»',
          'Если не хочется писать — просто открой контакт и подержи телефон рядом.',
        ],
      );
    case 'crisis':
      return const _HelpDetail(
        title: 'Кризисные контакты',
        icon: Icons.local_phone_rounded,
        description: 'Если есть риск причинить вред себе или другим, лучше обращаться в экстренные службы.',
        warning: true,
        steps: [
          '112 — единый номер экстренных служб в большинстве стран Европы.',
          'Если ты в другой стране, используй местный номер экстренной помощи.',
          'Можно также обратиться в ближайший травмпункт, приёмное отделение или к дежурному врачу.',
          'Если рядом есть человек, попроси его остаться с тобой до стабилизации.',
        ],
      );
    case 'safety':
    default:
      return const _HelpDetail(
        title: 'Мне очень плохо сейчас',
        icon: Icons.priority_high_rounded,
        description: 'Быстрый план на ближайшие минуты. Это не замена профессиональной помощи.',
        warning: true,
        steps: [
          'Отойди от предметов, которыми можно навредить себе.',
          'Перейди в более безопасное место: к людям, в освещённую комнату, на открытое пространство.',
          'Напиши или позвони человеку, которому доверяешь.',
          'Если есть риск для жизни — звони в экстренные службы прямо сейчас.',
        ],
      );
  }
}

class _HelpDetail {
  const _HelpDetail({
    required this.title,
    required this.icon,
    required this.description,
    required this.steps,
    this.warning = false,
  });

  final String title;
  final IconData icon;
  final String description;
  final List<String> steps;
  final bool warning;
}
