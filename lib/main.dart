import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'core/constants/app_constants.dart';
import 'core/routing/app_router.dart';
import 'core/services/chat_repository.dart';
import 'core/services/chatbot_service.dart';
import 'core/services/clinical_rules_service.dart';
import 'core/services/database_service.dart';
import 'core/services/mood_repository.dart';
import 'providers/chat_provider.dart';
import 'providers/mood_provider.dart';
import 'providers/settings_provider.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final databaseService = DatabaseService.instance;
  await databaseService.database;

  final settingsProvider = SettingsProvider();
  await settingsProvider.load();

  runApp(
    MentalHealthApp(
      databaseService: databaseService,
      settingsProvider: settingsProvider,
    ),
  );
}

class MentalHealthApp extends StatelessWidget {
  const MentalHealthApp({
    super.key,
    required this.databaseService,
    required this.settingsProvider,
  });

  final DatabaseService databaseService;
  final SettingsProvider settingsProvider;

  @override
  Widget build(BuildContext context) {
    final moodRepository = SqliteMoodRepository(databaseService);

    return MultiProvider(
      providers: [
        ChangeNotifierProvider<SettingsProvider>.value(value: settingsProvider),
        ChangeNotifierProvider(
          create: (_) => MoodProvider(repository: moodRepository)..loadEntries(),
        ),
        ChangeNotifierProvider(
          create: (_) => ChatProvider(
            chatbotService: ChatbotService(),
            chatRepository: SqliteChatRepository(databaseService),
            moodRepository: moodRepository,
            clinicalRulesService: ClinicalRulesService(),
          )..initialize(),
        ),
      ],
      child: Consumer<SettingsProvider>(
        builder: (context, settings, _) {
          return MaterialApp.router(
            title: AppConstants.appName,
            debugShowCheckedModeBanner: false,
            routerConfig: AppRouter.router,
            themeMode: settings.themeMode,
            theme: _buildTheme(Brightness.light),
            darkTheme: _buildTheme(Brightness.dark),
          );
        },
      ),
    );
  }

  ThemeData _buildTheme(Brightness brightness) {
    final isDark = brightness == Brightness.dark;

    final base = ThemeData(
      brightness: brightness,
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: const Color(0xFF2F7D3B),
        brightness: brightness,
      ),
    );

    return base.copyWith(
      scaffoldBackgroundColor:
          isDark ? const Color(0xFF1F2A1C) : const Color(0xFFEAF3D5),
      appBarTheme: AppBarTheme(
        backgroundColor: isDark ? const Color(0xFF295330) : const Color(0xFF2F7D3B),
        foregroundColor: const Color(0xFFFFF4C8),
        elevation: 0,
      ),
      cardTheme: CardThemeData(
        color: isDark ? const Color(0xFF2E4330) : const Color(0xFFFFFAE8),
        elevation: 4,
      ),
      snackBarTheme: const SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: isDark
            ? const Color(0xFFF7F3E8).withOpacity(0.96)
            : Colors.white,
        hintStyle: TextStyle(
          color: isDark ? const Color(0xFF8D7A66) : const Color(0xFF9A8A78),
        ),
        labelStyle: const TextStyle(
          color: Color(0xFF5F4A32),
          fontWeight: FontWeight.w700,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: BorderSide.none,
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: const Color(0xFF2F7D3B),
          foregroundColor: const Color(0xFFFFF4C8),
          textStyle: const TextStyle(fontWeight: FontWeight.w800),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          backgroundColor: const Color(0xFFFFFEF4).withOpacity(0.92),
          foregroundColor: const Color(0xFF5F4A32),
          side: const BorderSide(color: Color(0xFFB7C89C), width: 1.2),
          textStyle: const TextStyle(fontWeight: FontWeight.w800),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
          ),
        ),
      ),
    );
  }
}
