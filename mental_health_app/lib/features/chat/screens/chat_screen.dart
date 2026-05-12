import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/constants/app_constants.dart';
import '../../../providers/chat_provider.dart';
import '../../../widgets/app_shell.dart';
import '../models/chat_message.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  final List<String> _quickPhrases = const [
    'Мне тревожно',
    'Я устал(а)',
    'Хочу просто поговорить',
    'Не знаю, что чувствую',
    'Помоги успокоиться',
  ];

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _sendMessage([String? forcedText]) {
    final text = (forcedText ?? _messageController.text).trim();
    if (text.isEmpty) return;

    context.read<ChatProvider>().sendMessage(text);
    _messageController.clear();

    Future.delayed(const Duration(milliseconds: 120), () {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final keyboardInset = MediaQuery.of(context).viewInsets.bottom;

    return AppShell(
      title: 'Поговорить',
      currentRoute: AppRoutes.chat,
      backgroundColor: const Color(0xFFFFEFD8),
      useMeadowBackground: false,
      child: Consumer<ChatProvider>(
        builder: (context, chatProvider, _) {
          if (chatProvider.isLoading && !chatProvider.isInitialized) {
            return const Center(child: CircularProgressIndicator());
          }

          return Stack(
            children: [
              Positioned.fill(
                child: Image.asset(
                  'assets/images/ui/chat_room_bg.png',
                  fit: BoxFit.cover,
                ),
              ),
              Positioned.fill(
                child: Container(
                  color: const Color(0xFFFFF1DE).withOpacity(0.58),
                ),
              ),
              SafeArea(
              top: false,
              bottom: false,
                child: Column(
                  children: [
                  const _RoomHeader(),
                  _QuickPhrases(
                    phrases: _quickPhrases,
                    onTap: (phrase) => _sendMessage(phrase),
                  ),
                  Expanded(
                    child: chatProvider.messages.isEmpty
                        ? const _EmptyChat()
                        : ListView.builder(
                            controller: _scrollController,
                            padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
                            itemCount: chatProvider.messages.length,
                            itemBuilder: (context, index) {
                              return _MessageBubble(message: chatProvider.messages[index]);
                            },
                          ),
                  ),
                  AnimatedPadding(
                    duration: const Duration(milliseconds: 180),
                    curve: Curves.easeOut,
                    padding: EdgeInsets.only(bottom: keyboardInset > 0 ? keyboardInset + 8 : 96),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        if (chatProvider.isBotTyping)
                          const Padding(
                            padding: EdgeInsets.fromLTRB(18, 0, 18, 8),
                            child: Row(
                              children: [
                                Icon(Icons.more_horiz_rounded, color: AppColors.brown),
                                SizedBox(width: 8),
                                Text(
                                  'Печатает...',
                                  style: TextStyle(
                                    color: AppColors.brown,
                                    fontStyle: FontStyle.italic,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        _MessageInput(
                          controller: _messageController,
                          enabled: !chatProvider.isBotTyping,
                          onSend: () => _sendMessage(),
                        ),
                      ],
                    ),
                  ),
                ],
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _RoomHeader extends StatelessWidget {
  const _RoomHeader();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(18, 14, 18, 6),
      child: SoftCard(
        color: const Color(0xFFFFF7E8),
        child: Row(
          children: [
            Container(
              width: 56,
              height: 56,
              decoration: const BoxDecoration(color: Color(0xFFFFD59E), shape: BoxShape.circle),
              child: const Icon(Icons.weekend_rounded, color: AppColors.brown, size: 30),
            ),
            const SizedBox(width: 14),
            const Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Уютная комната', style: TextStyle(color: AppColors.brown, fontSize: 19, fontWeight: FontWeight.w900)),
                  SizedBox(height: 4),
                  Text('Можно написать как есть. Без оценки и спешки.', style: TextStyle(color: AppColors.brown, height: 1.25)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _QuickPhrases extends StatelessWidget {
  const _QuickPhrases({required this.phrases, required this.onTap});

  final List<String> phrases;
  final ValueChanged<String> onTap;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 44,
      child: ListView.separated(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        scrollDirection: Axis.horizontal,
        itemBuilder: (context, index) {
          final phrase = phrases[index];
          return ActionChip(
            backgroundColor: AppColors.card,
            label: Text(phrase, style: const TextStyle(color: AppColors.brown)),
            onPressed: () => onTap(phrase),
          );
        },
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemCount: phrases.length,
      ),
    );
  }
}

class _MessageInput extends StatelessWidget {
  const _MessageInput({required this.controller, required this.enabled, required this.onSend});

  final TextEditingController controller;
  final bool enabled;
  final VoidCallback onSend;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 6, 14, 0),
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(28),
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.08), blurRadius: 12, offset: const Offset(0, 4))],
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: controller,
              enabled: enabled,
              minLines: 1,
              maxLines: 4,
              decoration: const InputDecoration(
                hintText: 'Напиши сообщение...',
                border: InputBorder.none,
                contentPadding: EdgeInsets.symmetric(horizontal: 14),
              ),
              textInputAction: TextInputAction.send,
              onSubmitted: (_) => onSend(),
            ),
          ),
          IconButton.filled(
            onPressed: enabled ? onSend : null,
            icon: const Icon(Icons.arrow_upward_rounded),
            style: IconButton.styleFrom(backgroundColor: AppColors.forest, foregroundColor: AppColors.cream),
          ),
        ],
      ),
    );
  }
}

class _MessageBubble extends StatelessWidget {
  const _MessageBubble({required this.message});

  final ChatMessage message;

  @override
  Widget build(BuildContext context) {
    final isUser = message.isFromUser;
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.78),
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 12),
        decoration: BoxDecoration(
          color: isUser ? AppColors.forest : AppColors.card,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(22),
            topRight: const Radius.circular(22),
            bottomLeft: Radius.circular(isUser ? 22 : 6),
            bottomRight: Radius.circular(isUser ? 6 : 22),
          ),
        ),
        child: Text(
          message.text,
          style: TextStyle(color: isUser ? AppColors.cream : AppColors.brown, fontSize: 15, height: 1.25),
        ),
      ),
    );
  }
}

class _EmptyChat extends StatelessWidget {
  const _EmptyChat();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Padding(
        padding: EdgeInsets.all(24),
        child: Text(
          'Начни с быстрой фразы сверху или напиши своими словами.',
          textAlign: TextAlign.center,
          style: TextStyle(color: AppColors.brown, fontSize: 16),
        ),
      ),
    );
  }
}
