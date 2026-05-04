import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../../core/constants/app_constants.dart';
import '../../../providers/settings_provider.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  final _phoneController = TextEditingController();
  final _genderController = TextEditingController();
  final _ageController = TextEditingController();
  final Map<String, String> _quizAnswers = {};

  int _step = 0;
  bool _saving = false;

  final List<_QuizQuestion> _questions = const [
    _QuizQuestion(
      keyName: 'pace',
      title: 'Какой ритм тебе обычно ближе?',
      options: ['Спокойный', 'Средний', 'Меняется по дням'],
    ),
    _QuizQuestion(
      keyName: 'support',
      title: 'Какой формат поддержки тебе комфортнее?',
      options: ['Короткие советы', 'Разговор', 'И то, и другое'],
    ),
    _QuizQuestion(
      keyName: 'energy',
      title: 'Как чаще ощущается уровень энергии?',
      options: ['Низкий', 'Средний', 'Разный'],
    ),
    _QuizQuestion(
      keyName: 'help',
      title: 'Что обычно помогает больше?',
      options: ['Пауза и тишина', 'Действие', 'Общение'],
    ),
    _QuizQuestion(
      keyName: 'plan',
      title: 'Насколько тебе важен понятный план дня?',
      options: ['Очень важен', 'Иногда', 'Не всегда'],
    ),
    _QuizQuestion(
      keyName: 'checkins',
      title: 'Как часто удобно отмечать состояние?',
      options: ['Каждый день', 'Пару раз в неделю', 'По настроению'],
    ),
  ];

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _phoneController.dispose();
    _genderController.dispose();
    _ageController.dispose();
    super.dispose();
  }

  UserProfile get _profile => UserProfile(
        name: _nameController.text.trim(),
        email: _emailController.text.trim(),
        phone: _phoneController.text.trim(),
        gender: _genderController.text.trim(),
        age: _ageController.text.trim(),
      );

  void _next() {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _step = 1);
  }

  Future<void> _finish({bool skipQuiz = false}) async {
    setState(() => _saving = true);
    await context.read<SettingsProvider>().completeOnboarding(
          _profile,
          starterQuiz: skipQuiz ? {} : _quizAnswers,
        );
    if (!mounted) return;
    context.go(AppRoutes.home);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          Positioned.fill(
            child: Image.asset(
              'assets/images/home_new/bg_meadow.png',
              fit: BoxFit.cover,
            ),
          ),
          Positioned.fill(
            child: Container(color: const Color(0xFF7EAF5C).withOpacity(0.18)),
          ),
          SafeArea(
            child: Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(20),
                child: Container(
                  constraints: const BoxConstraints(maxWidth: 540),
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFFF4C8),
                    borderRadius: BorderRadius.circular(30),
                    boxShadow: const [
                      BoxShadow(
                        blurRadius: 20,
                        offset: Offset(0, 8),
                        color: Color(0x33000000),
                      ),
                    ],
                  ),
                  child: _step == 0 ? _buildRegistration() : _buildQuiz(),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRegistration() {
    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Добро пожаловать 🌿',
            style: TextStyle(
              fontSize: 28,
              fontWeight: FontWeight.w900,
              color: Color(0xFF5F4A32),
            ),
          ),
          const SizedBox(height: 10),
          const Text(
            'Заполни короткую регистрацию. Она появится только при первом открытии.',
            style: TextStyle(
              fontSize: 15,
              height: 1.4,
              color: Color(0xFF5F4A32),
            ),
          ),
          const SizedBox(height: 18),
          _Field(
            controller: _nameController,
            label: 'Имя *',
            validator: (value) {
              if (value == null || value.trim().isEmpty) {
                return 'Введите имя';
              }
              return null;
            },
          ),
          _Field(controller: _emailController, label: 'Почта'),
          _Field(controller: _phoneController, label: 'Телефон'),
          _Field(controller: _genderController, label: 'Пол'),
          _Field(controller: _ageController, label: 'Возраст'),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: _saving ? null : _next,
              child: const Text('Продолжить'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildQuiz() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            IconButton(
              onPressed: _saving ? null : () => setState(() => _step = 0),
              icon: const Icon(Icons.arrow_back_rounded),
              color: const Color(0xFF5F4A32),
            ),
            const Expanded(
              child: Text(
                'Ознакомительный тест',
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.w900,
                  color: Color(0xFF5F4A32),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        const Text(
          'Можно пропустить. Это нужно только для мягкой стартовой персонализации.',
          style: TextStyle(
            fontSize: 15,
            height: 1.4,
            color: Color(0xFF5F4A32),
          ),
        ),
        const SizedBox(height: 16),
        ..._questions.map(
          (q) => Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.92),
                borderRadius: BorderRadius.circular(18),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    q.title,
                    style: const TextStyle(
                      color: Color(0xFF5F4A32),
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: q.options.map((option) {
                      final selected = _quizAnswers[q.keyName] == option;
                      return ChoiceChip(
                        selected: selected,
                        backgroundColor: const Color(0xFFFFFEF4),
                        selectedColor: const Color(0xFF2F7D3B),
                        side: const BorderSide(color: Color(0xFFB7C89C), width: 1.1),
                        label: Text(
                          option,
                          style: TextStyle(
                            color: selected
                                ? const Color(0xFFFFF4C8)
                                : const Color(0xFF5F4A32),
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        onSelected: (_) {
                          setState(() => _quizAnswers[q.keyName] = option);
                        },
                      );
                    }).toList(),
                  ),
                ],
              ),
            ),
          ),
        ),
        Row(
          children: [
            Expanded(
              child: OutlinedButton(
                onPressed: _saving ? null : () => _finish(skipQuiz: true),
                child: const Text('Пропустить'),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: ElevatedButton(
                onPressed: _saving ? null : _finish,
                child: Text(_saving ? 'Сохраняем...' : 'Завершить'),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _Field extends StatelessWidget {
  const _Field({
    required this.controller,
    required this.label,
    this.validator,
  });

  final TextEditingController controller;
  final String label;
  final String? Function(String?)? validator;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: TextFormField(
        controller: controller,
        validator: validator,
        cursorColor: const Color(0xFF2F7D3B),
        style: const TextStyle(
          color: Color(0xFF5F4A32),
          fontWeight: FontWeight.w800,
          fontSize: 16,
        ),
        decoration: InputDecoration(
          labelText: label,
          labelStyle: const TextStyle(
            color: Color(0xFF8C7A63),
            fontWeight: FontWeight.w700,
          ),
          hintStyle: const TextStyle(
            color: Color(0xFFA79884),
          ),
          filled: true,
          fillColor: Colors.white.withOpacity(0.95),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(18),
            borderSide: BorderSide.none,
          ),
        ),
      ),
    );
  }
}

class _QuizQuestion {
  const _QuizQuestion({
    required this.keyName,
    required this.title,
    required this.options,
  });

  final String keyName;
  final String title;
  final List<String> options;
}
