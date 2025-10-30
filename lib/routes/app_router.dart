import 'package:flutter/material.dart';

/// App Router - Handles all navigation in the app
/// 
/// Usage:
/// - Push named route: Navigator.pushNamed(context, RouteNames.chat);
/// - Pop: Navigator.pop(context);
/// - Replace: Navigator.pushReplacementNamed(context, RouteNames.home);
// lib/routes/app_router.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../screens/home_screen.dart';
import '../screens/diary_screen.dart';
import '../screens/tips_screen.dart';
import '../screens/help_screen.dart';
import '../screens/settings_screen.dart';
import '../utils/constants.dart';


class AppRouter {
  /// Generate routes for the app
  static Route<dynamic> generateRoute(RouteSettings settings) {
    switch (settings.name) {
      case '/':
        // Import and use once Person A creates HomeScreen
        // return MaterialPageRoute(builder: (_) => const HomeScreen());
        return MaterialPageRoute(
          builder: (_) => const PlaceholderScreen(title: 'Home Screen'),
        );

      case '/chat':
        // Import and use once Person A creates ChatScreen
        // return MaterialPageRoute(builder: (_) => const ChatScreen());
        return MaterialPageRoute(
          builder: (_) => const PlaceholderScreen(title: 'Chat Screen'),
        );

      case '/mood-diary':
        // Import and use once Person A creates MoodDiaryScreen
        // return MaterialPageRoute(builder: (_) => const MoodDiaryScreen());
        return MaterialPageRoute(
          builder: (_) => const PlaceholderScreen(title: 'Mood Diary Screen'),
        );

      case '/settings':
        // Future feature
        return MaterialPageRoute(
          builder: (_) => const PlaceholderScreen(title: 'Settings Screen'),
        );

      default:
        return MaterialPageRoute(
          builder: (_) => Scaffold(
            body: Center(
              child: Text('No route defined for ${settings.name}'),
            ),
          ),
        );
    }
  }

  /// Navigate to a named route
  static Future<T?> navigateTo<T>(BuildContext context, String routeName) {
    return Navigator.pushNamed<T>(context, routeName);
  }

  /// Replace current route with a named route
  static Future<T?> replaceTo<T extends Object?>(
      BuildContext context, String routeName) {
    return Navigator.pushReplacementNamed<T, T>(context, routeName);
  }

  /// Navigate back
  static void goBack(BuildContext context) {
    Navigator.pop(context);
  }
}

/// Placeholder screen for routes that haven't been implemented yet
class PlaceholderScreen extends StatelessWidget {
  final String title;

  const PlaceholderScreen({super.key, required this.title});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(title),
        backgroundColor: Colors.deepPurple,
        foregroundColor: Colors.white,
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.construction,
              size: 64,
              color: Colors.grey,
            ),
            const SizedBox(height: 16),
            Text(
              title,
              style: const TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Coming soon...',
              style: TextStyle(
                fontSize: 16,
                color: Colors.grey,
              ),
            ),
            const SizedBox(height: 32),
            ElevatedButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Go Back'),
            ),
          ],
        ),
      ),
    );
  }
}

