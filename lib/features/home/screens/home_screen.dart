import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/constants/app_constants.dart';

/// Home Screen - Main dashboard
/// 
/// Алена: Implement the main dashboard with:
/// - Welcome message
/// - Quick action cards (Log Mood, View Stats, Get Tips)
/// - Recent mood summary
/// - Navigation to other screens

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Home'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Welcome back! 👋',
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 8),
            Text(
              'How are you feeling today?',
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: Colors.grey[600],
                  ),
            ),
            const SizedBox(height: 24),
            
            _QuickActionCard(
              title: 'Mood Diary',
              description: 'Track your emotions and thoughts',
              icon: Icons.edit_note,
              color: Colors.blue,
              onTap: () => context.go(AppRoutes.diary),
            ),
            const SizedBox(height: 12),
            
            _QuickActionCard(
              title: 'Statistics',
              description: 'View your progress and insights',
              icon: Icons.bar_chart,
              color: Colors.green,
              onTap: () => context.go(AppRoutes.statistics),
            ),
            const SizedBox(height: 12),
            
            _QuickActionCard(
              title: 'Self-Care Tips',
              description: 'Get helpful advice and practices',
              icon: Icons.spa,
              color: Colors.purple,
              onTap: () => context.go(AppRoutes.tips),
            ),
            const SizedBox(height: 12),
            
            _QuickActionCard(
              title: 'Get Help',
              description: 'Access support resources',
              icon: Icons.support_agent,
              color: Colors.orange,
              onTap: () => context.go(AppRoutes.help),
            ),
          ],
        ),
      ),
    );
  }
}

class _QuickActionCard extends StatelessWidget {
  final String title;
  final String description;
  final IconData icon;
  final Color color;
  final VoidCallback onTap;

  const _QuickActionCard({
    required this.title,
    required this.description,
    required this.icon,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(icon, color: color, size: 28),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      description,
                      style: TextStyle(
                        fontSize: 14,
                        color: Colors.grey[600],
                      ),
                    ),
                  ],
                ),
              ),
              Icon(Icons.arrow_forward_ios, color: Colors.grey[400], size: 16),
            ],
          ),
        ),
      ),
    );
  }
}
