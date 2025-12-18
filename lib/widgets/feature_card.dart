import 'package:flutter/material.dart';

/// Карточка функции для главного экрана
/// 
/// Используется для отображения доступных функций приложения
/// с иконкой, заголовком, описанием и обработчиком нажатия
class FeatureCard extends StatelessWidget {
  const FeatureCard({
    super.key,
    required this.icon,
    required this.title,
    this.description,
    this.onTap,
    this.color,
    this.iconColor,
  });

  /// Иконка функции
  final IconData icon;
  
  /// Заголовок функции
  final String title;
  
  /// Описание функции (опционально)
  final String? description;
  
  /// Callback при нажатии на карточку
  final VoidCallback? onTap;
  
  /// Цвет фона карточки (опционально)
  final Color? color;
  
  /// Цвет иконки (опционально)
  final Color? iconColor;

  @override
  Widget build(BuildContext context) {
    final cardColor = color ?? Theme.of(context).cardColor;
    final defaultIconColor = iconColor ?? Theme.of(context).colorScheme.primary;

    return Card(
      elevation: 2,
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              // Иконка
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: cardColor,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(
                  icon,
                  color: defaultIconColor,
                  size: 32,
                ),
              ),
              const SizedBox(width: 16),
              // Текст
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    if (description != null) ...[
                      const SizedBox(height: 4),
                      Text(
                        description!,
                        style: TextStyle(
                          fontSize: 14,
                          color: Colors.grey.shade600,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              // Стрелка
              if (onTap != null)
                Icon(
                  Icons.chevron_right,
                  color: Colors.grey.shade400,
                ),
            ],
          ),
        ),
      ),
    );
  }
}

