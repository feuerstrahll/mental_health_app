// lib/screens/diary_screen.dart
import 'package:flutter/material.dart';

/// Diary Screen - Emotion and mood tracking
/// 
/// Алена: Implement diary functionality with:
/// - Emotion selector (from AppConstants.emotions)
/// - Stress level slider (1-10)
/// - Notes text field
/// - Save button
/// - List of previous entries
/// - Edit/delete functionality

class DiaryScreen extends StatelessWidget {
  const DiaryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mood Diary'),
      ),
      body: const Center(
        child: Padding(
          padding: EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.edit_note, size: 80, color: Colors.grey),
              SizedBox(height: 16),
              Text(
                'Diary Screen',
                style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
              ),
              SizedBox(height: 8),
              Text(
                'Coming soon...',
                style: TextStyle(fontSize: 16, color: Colors.grey),
              ),
              SizedBox(height: 16),
              Text(
                'Алена will implement emotion tracking here',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 14, color: Colors.grey),
              ),
            ],
          ),
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          // TODO: Open new entry dialog
        },
        child: const Icon(Icons.add),
      ),
    );
  }
}

