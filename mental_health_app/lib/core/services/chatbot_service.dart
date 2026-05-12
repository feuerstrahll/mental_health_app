import 'dart:convert';
import 'dart:math';

import 'package:http/http.dart' as http;

import 'clinical_rules_service.dart';

class ChatContext {
  const ChatContext({
    required this.daysAnalyzed,
    required this.averageStress,
    required this.riskLevel,
    required this.isCrisis,
    required this.triggeredRules,
    required this.predictedMood,
    required this.topEmotions,
  });

  final int daysAnalyzed;
  final double averageStress;
  final RiskLevel riskLevel;
  final bool isCrisis;
  final List<String> triggeredRules;
  final String? predictedMood;
  final List<String> topEmotions;
}

/// Chat service with two tiers:
/// 1) call local backend (/api/v1/support-decision) that can use Qwen,
/// 2) fallback to lightweight keyword responses.
class ChatbotService {
  ChatbotService({
    http.Client? httpClient,
    String? backendBaseUrl,
    bool? useBackendQwen,
    String? userId,
  })  : _httpClient = httpClient ?? http.Client(),
        _backendBaseUrl = backendBaseUrl ?? _defaultBackendBaseUrl,
        _useBackendQwen = useBackendQwen ?? _defaultUseBackendQwen,
        _userId = userId ?? _defaultUserId;

  final Random _random = Random();
  final http.Client _httpClient;
  final String _backendBaseUrl;
  final bool _useBackendQwen;
  final String _userId;

  static const bool _defaultUseBackendQwen =
      bool.fromEnvironment('MH_USE_BACKEND_QWEN', defaultValue: true);
  static const String _defaultBackendBaseUrl = String.fromEnvironment(
    'MH_BACKEND_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );
  static const String _defaultUserId = String.fromEnvironment(
    'MH_USER_ID',
    defaultValue: 'local_user',
  );

  Future<String> generateResponse(String userMessage, {ChatContext? context}) async {
    final trimmed = userMessage.trim();
    if (trimmed.isEmpty) {
      return _withContext(_pick(_defaultResponses), context);
    }

    if (context != null && context.isCrisis) {
      return _buildCrisisResponse(context);
    }

    if (_useBackendQwen) {
      final llmResponse = await _tryGenerateBackendResponse(trimmed, context: context);
      if (llmResponse != null && llmResponse.isNotEmpty) {
        return llmResponse;
      }
    }

    await Future.delayed(Duration(milliseconds: 500 + _random.nextInt(1000)));
    return _fallbackResponse(trimmed.toLowerCase(), context);
  }

  String getWelcomeMessage() {
    return 'Hi. I am your support companion. '
        'You can share how you feel, and I can suggest small steps. '
        'How are you feeling today?';
  }

  void dispose() {
    _httpClient.close();
  }

  Future<String?> _tryGenerateBackendResponse(
    String userMessage, {
    ChatContext? context,
  }) async {
    final endpoint = Uri.parse('$_backendBaseUrl/api/v1/support-decision');

    try {
      final response = await _httpClient
          .post(
            endpoint,
            headers: const <String, String>{'Content-Type': 'application/json'},
            body: jsonEncode(_buildSupportDecisionPayload(userMessage, context: context)),
          )
          .timeout(const Duration(seconds: 12));

      if (response.statusCode < 200 || response.statusCode >= 300) {
        return null;
      }

      final decoded = jsonDecode(response.body);
      if (decoded is! Map<String, dynamic>) {
        return null;
      }

      final llmResponse = decoded['llm_response'];
      if (llmResponse is String && llmResponse.trim().isNotEmpty) {
        return llmResponse.trim();
      }
    } catch (_) {
      // Network or parse failure: fallback is used silently.
    }

    return null;
  }

  Map<String, dynamic> _buildSupportDecisionPayload(
    String userMessage, {
    ChatContext? context,
  }) {
    final stress = _deriveStress(context);

    final sleepQuality = _scoreFromStress(stress + 1.0);
    final sleepRegularity = _scoreFromStress(stress);
    final socialConnectedness = _scoreFromStress(stress);
    final routineRegularity = _scoreFromStress(stress + 0.5);

    final physicalActivityMinutes = (70 - (stress * 5)).clamp(0, 180).round();
    final sedentaryMinutes = (660 + (stress * 22)).clamp(240, 1320).round();
    final outdoorMinutes = (55 - (stress * 4)).clamp(0, 180).round();
    final sleepDurationHours = (8.2 - (stress * 0.35)).clamp(3.5, 9.5);

    return <String, dynamic>{
      'wellbeing': <String, dynamic>{
        'user_id': _userId,
        'client_timestamp': DateTime.now().toUtc().toIso8601String(),
        'signals': <String, dynamic>{
          'emotion_marker': _deriveEmotionMarker(context),
          'diary_note': userMessage,
          'sleep_duration_hours': sleepDurationHours,
          'sleep_regularity': sleepRegularity,
          'sleep_quality': sleepQuality,
          'physical_activity_minutes': physicalActivityMinutes,
          'sedentary_minutes': sedentaryMinutes,
          'outdoor_minutes': outdoorMinutes,
          'social_connectedness': socialConnectedness,
          'routine_regularity': routineRegularity,
        },
      },
      'latest_user_message': userMessage,
      'latest_diary_note': userMessage,
      'dialogue_state': const <String, dynamic>{'state': 'followup_wait'},
      'client_safety_precheck_result': <String, dynamic>{
        'safe_response_required': context?.isCrisis ?? false,
        'flags': context?.triggeredRules ?? const <String>[],
      },
    };
  }

  double _deriveStress(ChatContext? context) {
    if (context == null) return 5.0;
    return context.averageStress.clamp(1.0, 10.0);
  }

  int _scoreFromStress(double stress) {
    return (6 - (stress / 2.0).round()).clamp(1, 5).toInt();
  }

  String _deriveEmotionMarker(ChatContext? context) {
    final predicted = context?.predictedMood?.trim();
    if (predicted != null && predicted.isNotEmpty) {
      return predicted.toLowerCase();
    }

    if (context != null && context.topEmotions.isNotEmpty) {
      final top = context.topEmotions.first.trim();
      if (top.isNotEmpty) {
        return top.toLowerCase();
      }
    }

    return 'neutral';
  }

  String _fallbackResponse(String message, ChatContext? context) {
    if (_containsAny(message, <String>['hi', 'hello', 'hey', 'привет'])) {
      return _withContext(_pick(_greetingResponses), context);
    }

    if (_containsAny(message, <String>['bye', 'goodbye', 'пока'])) {
      return _pick(_farewellResponses);
    }

    if (_containsAny(message, <String>['thank', 'thanks', 'спасибо'])) {
      return _pick(_gratitudeResponses);
    }

    if (_containsAny(message, <String>['stress', 'anxious', 'panic', 'тревог', 'стресс'])) {
      return _withContext(_pick(_stressResponses), context);
    }

    if (_containsAny(message, <String>['sad', 'depress', 'tired', 'груст', 'плохо', 'устал'])) {
      return _withContext(_pick(_supportiveResponses), context);
    }

    if (_containsAny(message, <String>['sleep', 'insomnia', 'сон', 'бессон'])) {
      return _withContext(_pick(_sleepResponses), context);
    }

    if (_containsAny(message, <String>['help', 'advice', 'помоги', 'совет'])) {
      return _withContext(_pick(_helpResponses), context);
    }

    if (_containsAny(message, <String>['good', 'great', 'happy', 'рад', 'хорошо'])) {
      return _pick(_positiveResponses);
    }

    return _withContext(_pick(_defaultResponses), context);
  }

  bool _containsAny(String text, List<String> keywords) {
    return keywords.any((keyword) => text.contains(keyword));
  }

  String _pick(List<String> values) {
    return values[_random.nextInt(values.length)];
  }

  String _withContext(String base, ChatContext? context) {
    if (context == null) return base;

    final riskHint = _riskToHint(context.riskLevel);
    final moodHint = context.predictedMood != null
        ? ' Predicted next mood: ${context.predictedMood}.'
        : '';
    final emotionHint = context.topEmotions.isEmpty
        ? ''
        : ' Frequent emotions in the last ${context.daysAnalyzed} days: ${context.topEmotions.join(', ')}.';

    return '$base\n\n$riskHint$moodHint$emotionHint';
  }

  String _riskToHint(RiskLevel level) {
    switch (level) {
      case RiskLevel.low:
        return 'Current diary risk: low.';
      case RiskLevel.moderate:
        return 'Current diary risk: moderate. Keep sleep and rest stable if possible.';
      case RiskLevel.high:
        return 'Current diary risk: high. Consider reducing load and talking to someone you trust.';
      case RiskLevel.crisis:
        return 'Current diary risk: crisis.';
    }
  }

  String _buildCrisisResponse(ChatContext context) {
    final triggers = context.triggeredRules.isEmpty
        ? 'we detected concerning signals'
        : 'detected triggers: ${context.triggeredRules.join(', ')}';

    return 'Your safety matters first. Based on recent data, $triggers. '
        'If there is any risk of harm to yourself, call emergency services now (112) '
        'or contact a trusted person immediately. '
        'If you can, try 2 minutes of slow breathing: inhale 4 sec, hold 2 sec, exhale 6 sec.';
  }

  static const List<String> _greetingResponses = <String>[
    'Hi. I am here with you. What feels most difficult right now?',
    'Hello. Thanks for checking in. How has your day been so far?',
    'Hey. You can share as much or as little as you want.',
  ];

  static const List<String> _farewellResponses = <String>[
    'See you later. Take care of yourself.',
    'Goodbye. I am here whenever you want to check in again.',
  ];

  static const List<String> _gratitudeResponses = <String>[
    'You are welcome.',
    'Glad to help. We can continue whenever you want.',
  ];

  static const List<String> _supportiveResponses = <String>[
    'That sounds heavy. Thank you for saying it out loud.',
    'I hear you. It is okay to take this one small step at a time.',
    'What you feel is valid. We can focus on one manageable action now.',
  ];

  static const List<String> _positiveResponses = <String>[
    'That is good to hear. Notice what helped, and keep that pattern.',
    'Great. Holding onto small positive moments can build stability.',
  ];

  static const List<String> _helpResponses = <String>[
    'We can pick one small step: breathing, a short walk, or a glass of water.',
    'If you want, tell me what feels hardest right now and we will narrow it down.',
  ];

  static const List<String> _stressResponses = <String>[
    'Stress can narrow attention. Try a 60-second reset: slow inhale, longer exhale.',
    'When stress is high, reduce scope: choose the smallest next action only.',
  ];

  static const List<String> _sleepResponses = <String>[
    'Sleep strongly affects mood. A simple target is a consistent bedtime this week.',
    'For tonight, try a short wind-down without screens before sleep.',
  ];

  static const List<String> _defaultResponses = <String>[
    'I hear you. Tell me a bit more about what you are feeling now.',
    'Thanks for sharing. What would feel most supportive in this moment?',
    'We can move slowly. What is one small thing that might help right now?',
  ];
}
