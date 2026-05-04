import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../features/chat/screens/chat_screen.dart';
import '../../features/help/screens/help_screen.dart';
import '../../features/home/screens/home_screen.dart';
import '../../features/mood/screens/diary_screen.dart';
import '../../features/mood/screens/statistics_screen.dart';
import '../../features/onboarding/screens/launch_gate_screen.dart';
import '../../features/onboarding/screens/onboarding_screen.dart';
import '../../features/settings/screens/settings_screen.dart';
import '../../features/tips/screens/tips_screen.dart';
import '../constants/app_constants.dart';

class AppRouter {
  static final GoRouter router = GoRouter(
    initialLocation: AppRoutes.root,
    routes: [
      GoRoute(
        path: AppRoutes.root,
        name: 'root',
        pageBuilder: (context, state) => MaterialPage(
          key: state.pageKey,
          child: const LaunchGateScreen(),
        ),
      ),
      GoRoute(
        path: AppRoutes.onboarding,
        name: 'onboarding',
        pageBuilder: (context, state) => MaterialPage(
          key: state.pageKey,
          child: const OnboardingScreen(),
        ),
      ),
      GoRoute(
        path: AppRoutes.home,
        name: 'home',
        pageBuilder: (context, state) => MaterialPage(
          key: state.pageKey,
          child: const HomeScreen(),
        ),
      ),
      GoRoute(
        path: AppRoutes.chat,
        name: 'chat',
        pageBuilder: (context, state) => MaterialPage(
          key: state.pageKey,
          child: const ChatScreen(),
        ),
      ),
      GoRoute(
        path: AppRoutes.diary,
        name: 'diary',
        pageBuilder: (context, state) => MaterialPage(
          key: state.pageKey,
          child: const DiaryScreen(),
        ),
      ),
      GoRoute(
        path: AppRoutes.tips,
        name: 'tips',
        pageBuilder: (context, state) => MaterialPage(
          key: state.pageKey,
          child: const TipsScreen(),
        ),
      ),
      GoRoute(
        path: AppRoutes.progress,
        name: 'progress',
        pageBuilder: (context, state) => MaterialPage(
          key: state.pageKey,
          child: const StatisticsScreen(),
        ),
      ),
      GoRoute(
        path: AppRoutes.statistics,
        redirect: (_, __) => AppRoutes.progress,
      ),
      GoRoute(
        path: AppRoutes.help,
        name: 'help',
        pageBuilder: (context, state) => MaterialPage(
          key: state.pageKey,
          child: const HelpScreen(),
        ),
      ),
      GoRoute(
        path: AppRoutes.helpSafety,
        name: 'help_safety',
        pageBuilder: (context, state) => MaterialPage(
          key: state.pageKey,
          child: const HelpDetailScreen(kind: 'safety'),
        ),
      ),
      GoRoute(
        path: AppRoutes.helpBreathing,
        name: 'help_breathing',
        pageBuilder: (context, state) => MaterialPage(
          key: state.pageKey,
          child: const HelpDetailScreen(kind: 'breathing'),
        ),
      ),
      GoRoute(
        path: AppRoutes.helpGrounding,
        name: 'help_grounding',
        pageBuilder: (context, state) => MaterialPage(
          key: state.pageKey,
          child: const HelpDetailScreen(kind: 'grounding'),
        ),
      ),
      GoRoute(
        path: AppRoutes.helpContact,
        name: 'help_contact',
        pageBuilder: (context, state) => MaterialPage(
          key: state.pageKey,
          child: const HelpDetailScreen(kind: 'contact'),
        ),
      ),
      GoRoute(
        path: AppRoutes.helpCrisis,
        name: 'help_crisis',
        pageBuilder: (context, state) => MaterialPage(
          key: state.pageKey,
          child: const HelpDetailScreen(kind: 'crisis'),
        ),
      ),
      GoRoute(
        path: AppRoutes.settings,
        name: 'settings',
        pageBuilder: (context, state) => MaterialPage(
          key: state.pageKey,
          child: const SettingsScreen(),
        ),
      ),
    ],
  );
}
