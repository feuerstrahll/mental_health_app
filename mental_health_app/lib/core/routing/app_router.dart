import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../features/home/screens/home_screen.dart';
import '../../features/chat/screens/chat_screen.dart';
import '../../features/mood/screens/diary_screen.dart';
import '../../features/mood/screens/statistics_screen.dart';
import '../../features/tips/screens/tips_screen.dart';
import '../../features/help/screens/help_screen.dart';
import '../../features/settings/screens/settings_screen.dart';
import '../constants/app_constants.dart';

class AppRouter {
  static final GoRouter router = GoRouter(
    initialLocation: AppRoutes.home,
    routes: [
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
        path: AppRoutes.statistics,
        name: 'statistics',
        pageBuilder: (context, state) => MaterialPage(
          key: state.pageKey,
          child: const StatisticsScreen(),
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
        path: AppRoutes.help,
        name: 'help',
        pageBuilder: (context, state) => MaterialPage(
          key: state.pageKey,
          child: const HelpScreen(),
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
