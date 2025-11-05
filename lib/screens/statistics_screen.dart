// lib/screens/statistics_screen.dart
import 'package:flutter/material.dart';

/// Statistics Screen - Displays graphs and observations
/// 
/// Features to implement:
/// - Emotion trends over time (line/bar charts)
/// - Stress level patterns (graphs)
/// - Weekly/monthly summaries
/// - Insights and observations based on patterns
/// - Export statistics functionality
/// 
/// Charts to consider:
/// - Line chart for emotion trends
/// - Bar chart for emotion frequency
/// - Heatmap for daily mood patterns
/// - Stress level timeline

class StatisticsScreen extends StatelessWidget {
  const StatisticsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Statistics & Insights'),
        backgroundColor: Theme.of(context).colorScheme.primary,
        foregroundColor: Colors.white,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Welcome header
            Text(
              'Your Mental Health Journey',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 8),
            Text(
              'Track your progress and discover patterns',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.grey[600],
                  ),
            ),
            const SizedBox(height: 24),

            // Placeholder cards for different statistics
            _StatisticCard(
              title: 'Emotion Trends',
              description: 'See how your emotions change over time',
              icon: Icons.timeline,
              color: Colors.blue,
              onTap: () {
                // TODO: Navigate to detailed emotion trends
              },
            ),
            const SizedBox(height: 16),
            
            _StatisticCard(
              title: 'Stress Patterns',
              description: 'Analyze your stress levels throughout the week',
              icon: Icons.show_chart,
              color: Colors.orange,
              onTap: () {
                // TODO: Navigate to stress analysis
              },
            ),
            const SizedBox(height: 16),
            
            _StatisticCard(
              title: 'Monthly Summary',
              description: 'Review your overall mental health this month',
              icon: Icons.calendar_today,
              color: Colors.green,
              onTap: () {
                // TODO: Navigate to monthly summary
              },
            ),
            const SizedBox(height: 16),
            
            _StatisticCard(
              title: 'Insights & Observations',
              description: 'Personalized insights based on your data',
              icon: Icons.lightbulb_outline,
              color: Colors.purple,
              onTap: () {
                // TODO: Navigate to insights
              },
            ),
            const SizedBox(height: 24),

            // Information card
            Card(
              color: Colors.blue.shade50,
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Row(
                  children: [
                    Icon(
                      Icons.info_outline,
                      color: Colors.blue.shade700,
                      size: 32,
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Coming Soon',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              color: Colors.blue.shade900,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            'Start logging your emotions in the Diary to see statistics and insights here.',
                            style: TextStyle(
                              fontSize: 14,
                              color: Colors.blue.shade700,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _StatisticCard extends StatelessWidget {
  final String title;
  final String description;
  final IconData icon;
  final Color color;
  final VoidCallback onTap;

  const _StatisticCard({
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
                child: Icon(
                  icon,
                  color: color,
                  size: 32,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(
                        fontSize: 18,
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
              Icon(
                Icons.arrow_forward_ios,
                color: Colors.grey[400],
                size: 16,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

