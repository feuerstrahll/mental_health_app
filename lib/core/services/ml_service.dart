import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:tflite_flutter/tflite_flutter.dart';

import '../../providers/mood_provider.dart';

class MLService {
  Interpreter? _interpreter;
  bool _isInitialized = false;

  static const int _lookbackDays = 7;
  static const int _numFeatures = 4;
  static const int _numEmotionClasses = 5;

  Future<void> initialize() async {
    if (_isInitialized) return;

    try {
      _interpreter = await Interpreter.fromAsset('models/mood_predictor.tflite');
      _isInitialized = true;
      if (kDebugMode) print('ML Model loaded successfully');
    } catch (e) {
      if (kDebugMode) print('ML Model not found, using fallback: $e');
    }
  }

  Future<Map<String, double>> predictNextMood(List<MoodEntry> entries) async {
    if (!_isInitialized) await initialize();
    if (_interpreter == null || entries.length < 3) return _fallbackPrediction(entries);

    try {
      final input = _prepareInput(entries);
      final output = List.filled(_numEmotionClasses, 0.0).reshape([1, _numEmotionClasses]);
      
      _interpreter!.run(input, output);

      return {
        'Радость': output[0][0],
        'Грусть': output[0][1],
        'Тревога': output[0][2],
        'Спокойствие': output[0][3],
        'Стресс': output[0][4],
      };
    } catch (e) {
      if (kDebugMode) print('Prediction error: $e');
      return _fallbackPrediction(entries);
    }
  }

  String recommendTipCategory(List<MoodEntry> entries) {
    if (entries.isEmpty) return 'general';

    final recent = entries.take(_lookbackDays).toList();
    final avgStress = recent.fold<int>(0, (sum, e) => sum + e.stressLevel) / recent.length;
    final stressValues = recent.map((e) => e.stressLevel).toList();
    final isIncreasing = _isTrendIncreasing(stressValues);

    if (avgStress > 7 || (avgStress > 5 && isIncreasing)) {
      return 'stress_management';
    } else if (avgStress > 5) {
      return 'relaxation';
    } else if (avgStress < 3) {
      return 'positive_habits';
    }
    return 'general';
  }

  List<double> analyzeStressTrend(List<MoodEntry> entries) {
    if (entries.length < 7) return [];
    
    final stressLevels = entries.take(14).map((e) => e.stressLevel.toDouble()).toList();
    final weeklyAvg = <double>[];
    
    for (int i = 0; i < stressLevels.length - 6; i += 7) {
      final weekData = stressLevels.skip(i).take(7);
      weeklyAvg.add(weekData.reduce((a, b) => a + b) / 7);
    }
    
    return weeklyAvg;
  }

  List<List<double>> _prepareInput(List<MoodEntry> entries) {
    final recent = entries.take(_lookbackDays).toList();
    final input = List.generate(_lookbackDays, (_) => List.filled(_numFeatures, 0.0));

    for (int i = 0; i < min(recent.length, _lookbackDays); i++) {
      final entry = recent[i];
      input[i] = [
        _encodeEmotion(entry.emotion),
        entry.stressLevel / 10.0,
        entry.timestamp.hour / 24.0,
        entry.timestamp.weekday / 7.0,
      ];
    }

    return input;
  }

  double _encodeEmotion(String emotion) {
    final emotionMap = {
      'радость': 0.0,
      'грусть': 0.25,
      'тревога': 0.5,
      'спокойствие': 0.75,
      'стресс': 1.0,
    };
    return emotionMap[emotion.toLowerCase()] ?? 0.5;
  }

  Map<String, double> _fallbackPrediction(List<MoodEntry> entries) {
    if (entries.isEmpty) {
      return {
        'Радость': 0.2,
        'Грусть': 0.2,
        'Тревога': 0.2,
        'Спокойствие': 0.2,
        'Стресс': 0.2,
      };
    }

    final emotionCounts = <String, int>{};
    for (final entry in entries.take(7)) {
      emotionCounts[entry.emotion] = (emotionCounts[entry.emotion] ?? 0) + 1;
    }

    final total = emotionCounts.values.fold(0, (sum, count) => sum + count);
    final predictions = <String, double>{};
    
    for (final emotion in ['Радость', 'Грусть', 'Тревога', 'Спокойствие', 'Стресс']) {
      predictions[emotion] = (emotionCounts[emotion] ?? 0) / total;
    }

    return predictions;
  }

  bool _isTrendIncreasing(List<int> values) {
    if (values.length < 2) return false;
    
    final firstHalf = values.take(values.length ~/ 2);
    final secondHalf = values.skip(values.length ~/ 2);
    
    final firstAvg = firstHalf.reduce((a, b) => a + b) / firstHalf.length;
    final secondAvg = secondHalf.reduce((a, b) => a + b) / secondHalf.length;
    
    return secondAvg > firstAvg;
  }

  void dispose() {
    _interpreter?.close();
    _isInitialized = false;
  }
}
