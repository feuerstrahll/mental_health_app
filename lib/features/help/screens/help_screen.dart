import 'package:flutter/material.dart';

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
        children: const [
          SoftCard(
            color: Color(0xFFFFD6D6),
            child: Text(
              'Если есть риск для жизни или безопасности — звони в местные экстренные службы. Этот экран не заменяет профессиональную помощь.',
              style: TextStyle(color: Color(0xFF7A2525), fontWeight: FontWeight.w800, height: 1.35),
            ),
          ),
          SizedBox(height: 12),
          _HelpAction(icon: Icons.priority_high_rounded, title: 'Мне очень плохо сейчас', subtitle: 'Открыть быстрый план безопасности'),
          _HelpAction(icon: Icons.air_rounded, title: 'Дыхание на 1 минуту', subtitle: 'Короткая практика для стабилизации'),
          _HelpAction(icon: Icons.touch_app_rounded, title: 'Заземление 5–4–3–2–1', subtitle: 'Вернуться вниманием в настоящий момент'),
          _HelpAction(icon: Icons.phone_in_talk_rounded, title: 'Связаться с близким', subtitle: 'Напомнить себе, кому можно написать'),
          _HelpAction(icon: Icons.local_phone_rounded, title: 'Кризисные контакты', subtitle: 'Горячие линии и экстренная помощь'),
        ],
      ),
    );
  }
}

class _HelpAction extends StatelessWidget {
  const _HelpAction({required this.icon, required this.title, required this.subtitle});

  final IconData icon;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: SoftCard(
        child: Row(
          children: [
            Container(
              width: 48,
              height: 48,
              decoration: const BoxDecoration(color: Color(0xFFFFEFEF), shape: BoxShape.circle),
              child: Icon(icon, color: Color(0xFFC75D5D)),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(color: AppColors.brown, fontWeight: FontWeight.w900, fontSize: 16)),
                  const SizedBox(height: 3),
                  Text(subtitle, style: const TextStyle(color: AppColors.brown, height: 1.25)),
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
