import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/constants/app_constants.dart';
import '../../../providers/mood_provider.dart';
import '../../../widgets/app_shell.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  String _theme = 'dynamic';
  bool _dailyReminder = true;
  bool _tipsReminder = false;

  @override
  Widget build(BuildContext context) {
    return AppShell(
      title: 'Настройки',
      currentRoute: AppRoutes.settings,
      backgroundColor: AppColors.sage,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 18, 16, 118),
        children: [
          const SoftCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Профиль', style: TextStyle(color: AppColors.brown, fontSize: 20, fontWeight: FontWeight.w900)),
                SizedBox(height: 10),
                _ProfileField(label: 'Имя', hint: '[name]'),
                _ProfileField(label: 'Почта', hint: 'необязательно'),
                _ProfileField(label: 'Телефон', hint: 'необязательно'),
                _ProfileField(label: 'Пол', hint: 'необязательно'),
                _ProfileField(label: 'Возраст', hint: 'необязательно'),
              ],
            ),
          ),
          const SizedBox(height: 12),
          SoftCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Уведомления', style: TextStyle(color: AppColors.brown, fontSize: 20, fontWeight: FontWeight.w900)),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Напоминать заполнить день'),
                  value: _dailyReminder,
                  onChanged: (v) => setState(() => _dailyReminder = v),
                ),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Напоминать про короткие советы'),
                  value: _tipsReminder,
                  onChanged: (v) => setState(() => _tipsReminder = v),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          SoftCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Персонализация', style: TextStyle(color: AppColors.brown, fontSize: 20, fontWeight: FontWeight.w900)),
                RadioListTile<String>(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Светлая тема'),
                  value: 'light',
                  groupValue: _theme,
                  onChanged: (v) => setState(() => _theme = v ?? 'light'),
                ),
                RadioListTile<String>(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Тёмная тема'),
                  value: 'dark',
                  groupValue: _theme,
                  onChanged: (v) => setState(() => _theme = v ?? 'dark'),
                ),
                RadioListTile<String>(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Динамическая по времени суток'),
                  value: 'dynamic',
                  groupValue: _theme,
                  onChanged: (v) => setState(() => _theme = v ?? 'dynamic'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          SoftCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Управление данными', style: TextStyle(color: AppColors.brown, fontSize: 20, fontWeight: FontWeight.w900)),
                const SizedBox(height: 10),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    onPressed: () async {
                      final result = await context.read<MoodProvider>().exportDataForML();
                      if (!context.mounted) return;
                      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(result)));
                    },
                    icon: const Icon(Icons.file_download_rounded),
                    label: const Text('Экспортировать данные'),
                  ),
                ),
                const SizedBox(height: 8),
                SizedBox(
                  width: double.infinity,
                  child: TextButton.icon(
                    onPressed: () => ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Удаление данных можно подключить позже'))),
                    icon: const Icon(Icons.delete_outline_rounded),
                    label: const Text('Удалить мои данные'),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ProfileField extends StatelessWidget {
  const _ProfileField({required this.label, required this.hint});

  final String label;
  final String hint;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: TextField(
        decoration: InputDecoration(
          labelText: label,
          hintText: hint,
          filled: true,
          fillColor: Colors.white,
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide.none),
        ),
      ),
    );
  }
}
