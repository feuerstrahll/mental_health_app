import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'core/constants/app_constants.dart';
import 'providers/mood_provider.dart';
import 'providers/chat_provider.dart';
import 'core/services/mood_repository.dart';
import 'core/services/chat_repository.dart';
import 'core/services/chatbot_service.dart';
import 'core/services/database_service.dart';
import 'core/routing/app_router.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Инициализируем зашифрованную БД
  final databaseService = DatabaseService.instance;
  await databaseService.database;
  
  runApp(MentalHealthApp(databaseService: databaseService));
}

class MentalHealthApp extends StatelessWidget {
  final DatabaseService databaseService;
  
  const MentalHealthApp({
    super.key,
    required this.databaseService,
  });

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        // Mood Provider - управление дневником настроения (зашифрованная БД)
        ChangeNotifierProvider(
          create: (_) => MoodProvider(
            repository: SqliteMoodRepository(databaseService),
          )..loadEntries(),
        ),
        
        // Chat Provider - управление чатом с ботом (зашифрованная БД)
        ChangeNotifierProvider(
          create: (_) => ChatProvider(
            chatbotService: ChatbotService(),
            chatRepository: SqliteChatRepository(databaseService),
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
