import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:tflite_flutter/tflite_flutter.dart';

import '../../providers/mood_provider.dart';

/// Input tensor shape constants (must match legacy/ml/model_config.yaml / legacy/ml/train_model.py).
const int mlLookbackDays = 14; // LOOKBACK_DAYS
const int mlNumFeatures = 4; // emotion_encoded, stress_norm, hour_norm, weekday_norm
const int mlNumClasses = 6; // Happy, Sad, Anxious, Calm, Angry, Neutral

class MLService {
  Interpreter? _interpreter;
  bool _isInitialized = false;

  /// Должно совпадать с legacy/ml/train_model.py / legacy/ml/model_config.yaml (иначе неверная форма тензора).
  static const int _lookbackDays = mlLookbackDays;
  static const int _numFeatures = mlNumFeatures;
  static const int _numEmotionClasses = mlNumClasses;

  Future<void> initialize() async {
    if (_isInitialized) return;

    try {
      _interpreter = await Interpreter.fromAsset('models/mood_predictor.tflite');
      _isInitialized = true;
      if (kDebugMode) print('ML Model loaded successfully');
      _validateInterpreterShape();
    } catch (e) {
      if (kDebugMode) print('ML Model not found, using fallback: $e');
    }
  }

  /// Validates interpreter input/output tensor shapes match expected dimensions
  void _validateInterpreterShape() {
    if (_interpreter == null) return;
    
    try {
      final inputShape = _interpreter!.getInputTensor(0).shape;
      final outputShape = _interpreter!.getOutputTensor(0).shape;
      
      // Expected: input [1, lookback_days, num_features], output [1, num_classes]
      if (inputShape.length != 3 || inputShape[1] != _lookbackDays || inputShape[2] != _numFeatures) {
        throw Exception(
          'Input tensor shape mismatch! Expected [1, $_lookbackDays, $_numFeatures], '
          'got $inputShape. Please regenerate the model with legacy/ml/model_config.yaml.'
        );
      }
      
      if (outputShape.length != 2 || outputShape[1] != _numEmotionClasses) {
        throw Exception(
          'Output tensor shape mismatch! Expected [1, $_numEmotionClasses], '
          'got $outputShape. Please regenerate the model with legacy/ml/model_config.yaml.'
        );
      }
      
      if (kDebugMode) {
        print('✓ Interpreter shapes validated:');
        print('  Input:  $inputShape');
        print('  Output: $outputShape');
      }
    } catch (e) {
      if (kDebugMode) print('WARNING: Interpreter validation error: $e');
    }
  }

  Future<Map<String, double>> predictNextMood(List<MoodEntry> entries) async {
    if (!_isInitialized) await initialize();
    if (_interpreter == null || entries.length < 3) return _fallbackPrediction(entries);

    try {
      final input = _prepareInput(entries);
      
      // Validate input shape before inference
      if (input.length != _lookbackDays || input[0].length != _numFeatures) {
        throw Exception(
          'Input shape mismatch! Expected [$_lookbackDays, $_numFeatures], '
          'got [${input.length}, ${input[0].length}]'
        );
      }
      
      final output = List.filled(_numEmotionClasses, 0.0).reshape([1, _numEmotionClasses]);
      
      _interpreter!.run(input, output);

      return {
        'Happy': output[0][0],
        'Sad': output[0][1],
        'Anxious': output[0][2],
        'Calm': output[0][3],
        'Angry': output[0][4],
        'Neutral': output[0][5],
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
    final recent = entries.take(_lookbackDays).toList().reversed.toList();
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
    // Maps emotions to [0, 1] range (must match train_model.py encoding)
    final emotionMap = {
      'happy': 0.83,      // High emotion value
      'радость': 0.83,
      'sad': 0.17,        // Low emotion value
      'грусть': 0.17,
      'очень плохо': 0.17,
      'anxious': 0.35,    // Low-moderate emotion value
      'тревога': 0.35,
      'так себе': 0.35,
      'calm': 0.65,       // Moderate-high emotion value
      'спокойствие': 0.65,
      'angry': 0.17,      // Low emotion value
      'злость': 0.17,
      'neutral': 0.50,    // Middle emotion value
      'нормально': 0.50,
      'хорошо': 0.70,
      'отлично': 0.90,
    };
    return emotionMap[emotion.toLowerCase()] ?? 0.5;
  }

  Map<String, double> _fallbackPrediction(List<MoodEntry> entries) {
    if (entries.isEmpty) {
      return {
        'Happy': 0.167,
        'Sad': 0.167,
        'Anxious': 0.167,
        'Calm': 0.167,
        'Angry': 0.167,
        'Neutral': 0.167,
      };
    }

    final emotionCounts = <String, int>{};
    for (final entry in entries.take(_lookbackDays)) {
      emotionCounts[entry.emotion] = (emotionCounts[entry.emotion] ?? 0) + 1;
    }

    final total = emotionCounts.values.fold(0, (sum, count) => sum + count);
    final predictions = <String, double>{};
    
    for (final emotion in ['Happy', 'Sad', 'Anxious', 'Calm', 'Angry', 'Neutral']) {
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
