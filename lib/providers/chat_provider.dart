// lib/providers/chat_provider.dart
//
// Управление состоянием чата с ботом-помощником.
// Интегрируется с ChatbotService для генерации ответов и
// ChatRepository для сохранения истории сообщений в зашифрованной БД.

import 'dart:collection';
import 'dart:io';
import 'dart:math';
import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';
import '../features/chat/models/chat_message.dart';
import '../core/services/chatbot_service.dart';
import '../core/services/chat_repository.dart';

/// Provider для управления состоянием чата
class ChatProvider extends ChangeNotifier {
  ChatProvider({
    required ChatbotService chatbotService,
    required ChatRepository chatRepository,
  })  : _chatbotService = chatbotService,
        _chatRepository = chatRepository;

  final ChatbotService _chatbotService;
  final ChatRepository _chatRepository;
  final List<ChatMessage> _messages = <ChatMessage>[];

  bool _isLoading = false;
  bool _isBotTyping = false;
  bool _hasError = false;
  String? _errorMessage;
  bool _isInitialized = false;

  UnmodifiableListView<ChatMessage> get messages => UnmodifiableListView(_messages);
  bool get isLoading => _isLoading;
  bool get isBotTyping => _isBotTyping;
  bool get hasError => _hasError;
  String? get errorMessage => _errorMessage;
  bool get isInitialized => _isInitialized;
  bool get hasMessages => _messages.isNotEmpty;

  /// Инициализирует чат: загружает историю и отправляет приветствие при первом запуске
  Future<void> initialize() async {
    if (_isInitialized) return;

    _setLoading(true);
    _clearError();

    try {
      // Загружаем историю сообщений из БД
      final savedMessages = await _chatRepository.fetchMessages();
      _messages
        ..clear()
        ..addAll(savedMessages);
      _messages.sort((a, b) => a.timestamp.compareTo(b.timestamp));

      // Если это первый запуск (нет сообщений), отправляем приветствие
      if (_messages.isEmpty) {
        final welcomeMessage = ChatMessage(
          id: _generateId(),
          text: _chatbotService.getWelcomeMessage(),
          sender: MessageSender.bot,
          timestamp: DateTime.now(),
        );
        _messages.add(welcomeMessage);
        await _saveMessages();
      }

      _isInitialized = true;
    } catch (error, stackTrace) {
      _handleError('Failed to initialize chat', error, stackTrace);
    } finally {
      _setLoading(false);
    }
  }

  /// Отправляет сообщение от пользователя и получает ответ бота
  Future<void> sendMessage(String text) async {
    if (text.trim().isEmpty) return;
    if (_isBotTyping) return; // Не отправляем, пока бот печатает

    _clearError();

    // Создаем сообщение пользователя
    final userMessage = ChatMessage(
      id: _generateId(),
      text: text.trim(),
      sender: MessageSender.user,
      timestamp: DateTime.now(),
    );

    // Добавляем сообщение пользователя
    _messages.add(userMessage);
    notifyListeners();

    // Сохраняем в фоне
    _saveMessages();

    // Показываем индикатор печатания бота
    _setBotTyping(true);

    try {
      // Получаем ответ от бота
      final botResponseText = await _chatbotService.generateResponse(text);

      // Создаем сообщение бота
      final botMessage = ChatMessage(
        id: _generateId(),
        text: botResponseText,
        sender: MessageSender.bot,
        timestamp: DateTime.now(),
      );

      _messages.add(botMessage);
      await _saveMessages();
      notifyListeners();
    } catch (error, stackTrace) {
      _handleError('Failed to get bot response', error, stackTrace);
      
      // Добавляем сообщение об ошибке
      final errorMessage = ChatMessage(
        id: _generateId(),
        text: 'Извини, у меня возникла проблема. Попробуй еще раз чуть позже.',
        sender: MessageSender.bot,
        timestamp: DateTime.now(),
      );
      _messages.add(errorMessage);
      notifyListeners();
    } finally {
      _setBotTyping(false);
    }
  }

  /// Удаляет конкретное сообщение
  Future<void> deleteMessage(String id) async {
    final index = _messages.indexWhere((msg) => msg.id == id);
    if (index == -1) return;

    try {
      _messages.removeAt(index);
      await _saveMessages();
      notifyListeners();
    } catch (error, stackTrace) {
      _handleError('Failed to delete message', error, stackTrace);
      rethrow;
    }
  }

  /// Очищает всю историю чата
  Future<void> clearHistory() async {
    try {
      await _chatRepository.clearAll();
      _messages.clear();
      
      // Добавляем приветственное сообщение
      final welcomeMessage = ChatMessage(
        id: _generateId(),
        text: _chatbotService.getWelcomeMessage(),
        sender: MessageSender.bot,
        timestamp: DateTime.now(),
      );
      _messages.add(welcomeMessage);
      
      await _saveMessages();
      notifyListeners();
    } catch (error, stackTrace) {
      _handleError('Failed to clear chat history', error, stackTrace);
      rethrow;
    }
  }

  /// Экспортирует историю чата в текстовый файл
  Future<String> exportHistory() async {
    try {
      if (_messages.isEmpty) {
        return 'No messages to export';
      }

      // Используем path_provider для получения директории
      final directory = await getApplicationDocumentsDirectory();
      final timestamp = DateTime.now().toIso8601String().replaceAll(':', '-');
      final file = File('${directory.path}/chat_export_$timestamp.txt');
      
      final buffer = StringBuffer();
      buffer.writeln('Chat History Export');
      buffer.writeln('Generated: ${DateTime.now()}');
      buffer.writeln('=' * 50);
      buffer.writeln();

      for (final message in _messages) {
        final sender = message.isFromUser ? 'You' : 'Bot';
        buffer.writeln('[$sender] ${message.timestamp}');
        buffer.writeln(message.text);
        buffer.writeln();
      }

      await file.writeAsString(buffer.toString(), flush: true);
      return 'Chat history exported to:\n${file.path}';
    } catch (error, stackTrace) {
      _handleError('Failed to export chat history', error, stackTrace);
      return 'Export failed: $error';
    }
  }

  /// Перезагружает историю чата из хранилища
  Future<void> reloadHistory() async {
    _setLoading(true);
    _clearError();

    try {
      final savedMessages = await _chatRepository.fetchMessages();
      _messages
        ..clear()
        ..addAll(savedMessages);
      _messages.sort((a, b) => a.timestamp.compareTo(b.timestamp));
      notifyListeners();
    } catch (error, stackTrace) {
      _handleError('Failed to reload chat history', error, stackTrace);
    } finally {
      _setLoading(false);
    }
  }

  /// Возвращает количество сообщений пользователя
  int get userMessageCount =>
      _messages.where((msg) => msg.isFromUser).length;

  /// Возвращает количество сообщений бота
  int get botMessageCount =>
      _messages.where((msg) => msg.isFromBot).length;

  /// Возвращает последнее сообщение
  ChatMessage? get lastMessage =>
      _messages.isEmpty ? null : _messages.last;

  /// Возвращает последнее сообщение пользователя
  ChatMessage? get lastUserMessage =>
      _messages.lastWhere(
        (msg) => msg.isFromUser,
        orElse: () => ChatMessage(
          id: '',
          text: '',
          sender: MessageSender.user,
          timestamp: DateTime.now(),
        ),
      ).id.isEmpty
          ? null
          : _messages.lastWhere((msg) => msg.isFromUser);

  /// Фильтрует сообщения по дате
  List<ChatMessage> getMessagesByDate(DateTime date) {
    final start = DateTime(date.year, date.month, date.day);
    final end = DateTime(date.year, date.month, date.day, 23, 59, 59);
    
    return _messages
        .where((msg) =>
            msg.timestamp.isAfter(start.subtract(const Duration(seconds: 1))) &&
            msg.timestamp.isBefore(end.add(const Duration(seconds: 1))))
        .toList();
  }

  /// Фильтрует сообщения по диапазону дат
  List<ChatMessage> getMessagesByDateRange(DateTime start, DateTime end) {
    final normalizedStart = DateTime(start.year, start.month, start.day);
    final normalizedEnd = DateTime(end.year, end.month, end.day, 23, 59, 59);
    
    return _messages
        .where((msg) =>
            msg.timestamp.isAfter(normalizedStart.subtract(const Duration(seconds: 1))) &&
            msg.timestamp.isBefore(normalizedEnd.add(const Duration(seconds: 1))))
        .toList();
  }

  /// Поиск сообщений по тексту
  List<ChatMessage> searchMessages(String query) {
    if (query.trim().isEmpty) return [];
    
    final lowerQuery = query.toLowerCase();
    return _messages
        .where((msg) => msg.text.toLowerCase().contains(lowerQuery))
        .toList();
  }

  // ============ Private Methods ============

  Future<void> _saveMessages() async {
    try {
      await _chatRepository.saveMessages(_messages);
    } catch (error, stackTrace) {
      if (kDebugMode) {
        debugPrint('Error saving messages: $error');
        debugPrint(stackTrace.toString());
      }
      // Не пробрасываем ошибку, чтобы не блокировать UI
    }
  }

  void _setLoading(bool value) {
    if (_isLoading == value) return;
    _isLoading = value;
    notifyListeners();
  }

  void _setBotTyping(bool value) {
    if (_isBotTyping == value) return;
    _isBotTyping = value;
    notifyListeners();
  }

  void _handleError(String message, Object error, StackTrace stackTrace) {
    _hasError = true;
    _errorMessage = '$message: $error';
    if (kDebugMode) {
      debugPrint(_errorMessage);
      debugPrint(stackTrace.toString());
    }
    notifyListeners();
  }

  void _clearError() {
    _hasError = false;
    _errorMessage = null;
  }

  String _generateId() {
    final milliseconds = DateTime.now().millisecondsSinceEpoch;
    final randomSuffix = Random().nextInt(9999).toString().padLeft(4, '0');
    return 'chat_$milliseconds$randomSuffix';
  }
}

