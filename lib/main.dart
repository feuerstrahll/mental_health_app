import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'core/constants/app_constants.dart';
import 'providers/mood_provider.dart';
import 'providers/chat_provider.dart';
import 'core/services/mood_repository.dart';
import 'core/services/chatbot_service.dart';
import 'core/services/storage_service.dart';
import 'core/routing/app_router.dart';

void main() {
  runApp(const MentalHealthApp());
}

class MentalHealthApp extends StatelessWidget {
  const MentalHealthApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        // Mood Provider - управление дневником настроения
        ChangeNotifierProvider(
          create: (_) => MoodProvider(
            repository: SqliteMoodRepository(),
          )..loadEntries(),
        ),
        
        // Chat Provider - управление чатом с ботом
        ChangeNotifierProvider(
          create: (_) => ChatProvider(
            chatbotService: ChatbotService(),
            storageService: StorageService(),
          )..initialize(),
        ),
      ],
      child: MaterialApp.router(
        title: AppConstants.appName,
        debugShowCheckedModeBanner: false,
        routerConfig: AppRouter.router,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: Colors.deepPurple,
          ),
          useMaterial3: true,
          appBarTheme: const AppBarTheme(
            backgroundColor: Colors.deepPurple,
            foregroundColor: Colors.white,
            elevation: 0,
          ),
          floatingActionButtonTheme: const FloatingActionButtonThemeData(
            backgroundColor: Colors.deepPurple,
            foregroundColor: Colors.white,
          ),
          cardTheme: const CardThemeData(
            elevation: 4,
          ),
        ),
      ),
    );
  }
}
