import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../../core/constants/app_constants.dart';
import '../../../providers/mood_provider.dart';
import '../../../providers/settings_provider.dart';
import '../../../widgets/app_shell.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late final TextEditingController _nameController;
  late final TextEditingController _emailController;
  late final TextEditingController _phoneController;
  late final TextEditingController _genderController;
  late final TextEditingController _ageController;

  String _theme = 'dynamic';
  bool _dailyReminder = true;
  bool _tipsReminder = false;
  bool _initialized = false;
  bool _savingProfile = false;

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController();
    _emailController = TextEditingController();
    _phoneController = TextEditingController();
    _genderController = TextEditingController();
    _ageController = TextEditingController();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _phoneController.dispose();
    _genderController.dispose();
    _ageController.dispose();
    super.dispose();
  }

  void _sync(SettingsProvider settings) {
    if (_initialized) return;
    final profile = settings.profile;
    _nameController.text = profile.name;
    _emailController.text = profile.email;
    _phoneController.text = profile.phone;
    _genderController.text = profile.gender;
    _ageController.text = profile.age;
    _theme = settings.theme;
    _dailyReminder = settings.dailyReminder;
    _tipsReminder = settings.tipsReminder;
    _initialized = true;
  }

  Future<void> _saveProfile() async {
    setState(() => _savingProfile = true);
    await context.read<SettingsProvider>().saveProfile(
          UserProfile(
            name: _nameController.text.trim(),
            email: _emailController.text.trim(),
            phone: _phoneController.text.trim(),
            gender: _genderController.text.trim(),
            age: _ageController.text.trim(),
          ),
        );
    if (!mounted) return;
    setState(() => _savingProfile = false);
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Профиль сохранён')),
    );
  }

  void _close() {
    if (Navigator.of(context).canPop()) {
      context.pop();
    } else {
      context.go(AppRoutes.home);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<SettingsProvider>(
      builder: (context, settings, _) {
        _sync(settings);

        return Scaffold(
          resizeToAvoidBottomInset: false,
          backgroundColor: AppColors.sage,
          appBar: AppBar(
            title: const Text('Настройки'),
            centerTitle: false,
            backgroundColor: AppColors.forest,
            foregroundColor: AppColors.cream,
            leading: IconButton(
              onPressed: _close,
              icon: const Icon(Icons.close_rounded),
            ),
          ),
          body: Stack(
            children: [
              Positioned.fill(
                child: Image.asset(
                  'assets/images/home_new/bg_meadow.png',
                  fit: BoxFit.cover,
                ),
              ),
              Positioned.fill(
                child: Container(color: AppColors.sage.withOpacity(0.56)),
              ),
              ListView(
                padding: const EdgeInsets.fromLTRB(16, 18, 16, 24),
                children: [
                  SoftCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Профиль',
                          style: TextStyle(
                            color: AppColors.brown,
                            fontSize: 20,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                        const SizedBox(height: 10),
                        _ProfileField(label: 'Имя', controller: _nameController),
                        _ProfileField(label: 'Почта', controller: _emailController),
                        _ProfileField(label: 'Телефон', controller: _phoneController),
                        _ProfileField(label: 'Пол', controller: _genderController),
                        _ProfileField(label: 'Возраст', controller: _ageController),
                        const SizedBox(height: 6),
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton.icon(
                            onPressed: _savingProfile ? null : _saveProfile,
                            icon: const Icon(Icons.save_rounded),
                            label: Text(
                              _savingProfile ? 'Сохраняем...' : 'Сохранить данные',
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 12),
                  SoftCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Уведомления',
                          style: TextStyle(
                            color: AppColors.brown,
                            fontSize: 20,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                        SwitchListTile(
                          contentPadding: EdgeInsets.zero,
                          title: const Text(
                            'Напоминать заполнить день',
                            style: TextStyle(
                              color: AppColors.brown,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          value: _dailyReminder,
                          onChanged: (v) async {
                            setState(() => _dailyReminder = v);
                            await context
                                .read<SettingsProvider>()
                                .saveReminderPrefs(dailyReminder: v);
                          },
                        ),
                        SwitchListTile(
                          contentPadding: EdgeInsets.zero,
                          title: const Text(
                            'Напоминать про советы',
                            style: TextStyle(
                              color: AppColors.brown,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          value: _tipsReminder,
                          onChanged: (v) async {
                            setState(() => _tipsReminder = v);
                            await context
                                .read<SettingsProvider>()
                                .saveReminderPrefs(tipsReminder: v);
                          },
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 12),
                  SoftCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Персонализация',
                          style: TextStyle(
                            color: AppColors.brown,
                            fontSize: 20,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                        const SizedBox(height: 10),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: [
                            _ThemeChip(
                              label: 'Светлая',
                              selected: _theme == 'light',
                              onTap: () async {
                                setState(() => _theme = 'light');
                                await context.read<SettingsProvider>().saveTheme('light');
                              },
                            ),
                            _ThemeChip(
                              label: 'Тёмная',
                              selected: _theme == 'dark',
                              onTap: () async {
                                setState(() => _theme = 'dark');
                                await context.read<SettingsProvider>().saveTheme('dark');
                              },
                            ),
                            _ThemeChip(
                              label: 'Динамическая',
                              selected: _theme == 'dynamic',
                              onTap: () async {
                                setState(() => _theme = 'dynamic');
                                await context.read<SettingsProvider>().saveTheme('dynamic');
                              },
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 12),
                  SoftCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Управление данными',
                          style: TextStyle(
                            color: AppColors.brown,
                            fontSize: 20,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                        const SizedBox(height: 10),
                        SizedBox(
                          width: double.infinity,
                          child: OutlinedButton.icon(
                            onPressed: () async {
                              final result =
                                  await context.read<MoodProvider>().exportDataForML();
                              if (!context.mounted) return;
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(content: Text(result)),
                              );
                            },
                            icon: const Icon(Icons.file_download_rounded),
                            label: const Text('Экспортировать данные'),
                          ),
                        ),
                        const SizedBox(height: 8),
                        SizedBox(
                          width: double.infinity,
                          child: TextButton.icon(
                            onPressed: () async {
                              final confirmed = await showDialog<bool>(
                                context: context,
                                builder: (context) => AlertDialog(
                                  title: const Text('Удалить данные?'),
                                  content: const Text(
                                    'Будут очищены профиль, ответы теста, реакции на советы и записи дневника.',
                                  ),
                                  actions: [
                                    TextButton(
                                      onPressed: () => Navigator.of(context).pop(false),
                                      child: const Text('Отмена'),
                                    ),
                                    ElevatedButton(
                                      onPressed: () => Navigator.of(context).pop(true),
                                      child: const Text('Удалить'),
                                    ),
                                  ],
                                ),
                              );

                              if (confirmed != true || !context.mounted) return;
                              await context.read<MoodProvider>().clearDiary();
                              await context.read<SettingsProvider>().clearPersonalData();

                              _nameController.clear();
                              _emailController.clear();
                              _phoneController.clear();
                              _genderController.clear();
                              _ageController.clear();

                              if (!context.mounted) return;
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(content: Text('Данные удалены')),
                              );
                              context.go(AppRoutes.onboarding);
                            },
                            icon: const Icon(Icons.delete_outline_rounded),
                            label: const Text('Удалить мои данные'),
                          ),
                        ),
                        const SizedBox(height: 8),
                        SizedBox(
                          width: double.infinity,
                          child: TextButton.icon(
                            onPressed: () async {
                              await context.read<SettingsProvider>().resetOnboarding();
                              if (!context.mounted) return;
                              context.go(AppRoutes.onboarding);
                            },
                            icon: const Icon(Icons.restart_alt_rounded),
                            label: const Text('Показать регистрацию ещё раз'),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }
}

class _ThemeChip extends StatelessWidget {
  const _ThemeChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(999),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        decoration: BoxDecoration(
          color: selected ? AppColors.forest : const Color(0xFFFFFEF4),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(
            color: selected ? AppColors.forest : const Color(0xFFB7C89C),
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: selected ? AppColors.cream : AppColors.brown,
            fontWeight: FontWeight.w800,
          ),
        ),
      ),
    );
  }
}

class _ProfileField extends StatelessWidget {
  const _ProfileField({
    required this.label,
    required this.controller,
  });

  final String label;
  final TextEditingController controller;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: TextField(
        controller: controller,
        style: const TextStyle(
          color: AppColors.brown,
          fontWeight: FontWeight.w700,
        ),
        decoration: InputDecoration(
          labelText: label,
          labelStyle: const TextStyle(
            color: AppColors.brown,
            fontWeight: FontWeight.w700,
          ),
          filled: true,
          fillColor: Colors.white,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: BorderSide.none,
          ),
        ),
      ),
    );
  }
}
