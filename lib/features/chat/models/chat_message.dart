/// Тип отправителя сообщения
enum MessageSender {
  user,
  bot,
}

/// Модель сообщения в чате
class ChatMessage {
  ChatMessage({
    required this.id,
    required this.text,
    required this.sender,
    required this.timestamp,
    this.isTyping = false,
  });

  final String id;
  final String text;
  final MessageSender sender;
  final DateTime timestamp;
  final bool isTyping;

  bool get isFromUser => sender == MessageSender.user;
  bool get isFromBot => sender == MessageSender.bot;

  ChatMessage copyWith({
    String? text,
    MessageSender? sender,
    DateTime? timestamp,
    bool? isTyping,
  }) {
    return ChatMessage(
      id: id,
      text: text ?? this.text,
      sender: sender ?? this.sender,
      timestamp: timestamp ?? this.timestamp,
      isTyping: isTyping ?? this.isTyping,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'id': id,
      'text': text,
      'sender': sender == MessageSender.user ? 'user' : 'bot',
      'timestamp': timestamp.toIso8601String(),
      'isTyping': isTyping,
    };
  }

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      id: json['id'] as String,
      text: json['text'] as String,
      sender: json['sender'] == 'user' ? MessageSender.user : MessageSender.bot,
      timestamp: DateTime.parse(json['timestamp'] as String),
      isTyping: json['isTyping'] as bool? ?? false,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is ChatMessage && other.id == id;
  }

  @override
  int get hashCode => id.hashCode;

  @override
  String toString() {
    return 'ChatMessage(id: $id, sender: $sender, text: $text, timestamp: $timestamp)';
  }
}
