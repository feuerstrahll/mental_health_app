// lib/screens/tips_screen.dart
import 'package:flutter/material.dart';

/// Tips Screen - Self-care tips and practices
/// 
/// Алена: Implement tips section with:
/// - Categories of tips (Breathing, Exercise, Mindfulness, etc.)
/// - Tip cards with descriptions
/// - Favorite tips functionality
/// - Daily tip recommendation

class TipsScreen extends StatelessWidget {
  const TipsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Self-Care Tips'),
      ),
      body: const Center(
        child: Padding(
          padding: EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.spa, size: 80, color: Colors.grey),
              SizedBox(height: 16),
              Text(
                'Self-Care Tips',
                style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
              ),
              SizedBox(height: 8),
              Text(
                'Coming soon...',
                style: TextStyle(fontSize: 16, color: Colors.grey),
              ),
              SizedBox(height: 16),
              Text(
                'Алена will implement self-care tips and practices here',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 14, color: Colors.grey),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

