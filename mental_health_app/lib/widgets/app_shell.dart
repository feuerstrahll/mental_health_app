import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../core/constants/app_constants.dart';

class AppColors {
  static const forest = Color(0xFF2F7D3B);
  static const grass = Color(0xFF8ABF68);
  static const lightGrass = Color(0xFFB7D98A);
  static const cream = Color(0xFFFFF4C8);
  static const card = Color(0xFFFFFAE8);
  static const brown = Color(0xFF5F4A32);
  static const softPink = Color(0xFFFFB8B8);
  static const sage = Color(0xFFEAF3D5);
}

class AppShell extends StatelessWidget {
  const AppShell({
    super.key,
    required this.currentRoute,
    required this.child,
    this.title,
    this.showAppBar = true,
    this.backgroundColor = AppColors.sage,
    this.useMeadowBackground = true,
  });

  final String currentRoute;
  final Widget child;
  final String? title;
  final bool showAppBar;
  final Color backgroundColor;
  final bool useMeadowBackground;

  @override
  Widget build(BuildContext context) {
    final keyboardOpen = MediaQuery.of(context).viewInsets.bottom > 0;

    final content = Stack(
      children: [
        if (useMeadowBackground) ...[
          Positioned.fill(
            child: Image.asset(
              'assets/images/home_new/bg_meadow.png',
              fit: BoxFit.cover,
            ),
          ),
          Positioned.fill(
            child: Container(
              color: backgroundColor.withOpacity(0.34),
            ),
          ),
        ],
        Positioned.fill(child: child),
        if (!showAppBar)
          Positioned(
            top: MediaQuery.of(context).padding.top + 8,
            right: 14,
            child: Row(
              children: [
                _TopRoundButton(
                  icon: Icons.settings_outlined,
                  tooltip: 'Настройки',
                  onTap: () => context.go(AppRoutes.settings),
                ),
                const SizedBox(width: 8),
                _SosPill(onTap: () => context.go(AppRoutes.help)),
              ],
            ),
          ),
      ],
    );

    return Scaffold(
      resizeToAvoidBottomInset: false,
      backgroundColor: backgroundColor,
      extendBody: true,
      appBar: showAppBar
          ? AppBar(
              title: Text(title ?? ''),
              centerTitle: false,
              backgroundColor: AppColors.forest,
              foregroundColor: AppColors.cream,
              elevation: 0,
              actions: [
                IconButton(
                  tooltip: 'Настройки',
                  onPressed: () => context.go(AppRoutes.settings),
                  icon: const Icon(Icons.settings_outlined),
                ),
                Padding(
                  padding: const EdgeInsets.only(right: 12),
                  child: _SosPill(onTap: () => context.go(AppRoutes.help)),
                ),
              ],
            )
          : null,
      body: content,
      bottomNavigationBar:
          keyboardOpen ? null : _MainBottomNav(currentRoute: currentRoute),
    );
  }
}

class _MainBottomNav extends StatelessWidget {
  const _MainBottomNav({required this.currentRoute});

  final String currentRoute;

  @override
  Widget build(BuildContext context) {
    final items = [
      _NavItem('Главная', Icons.home_rounded, AppRoutes.home),
      _NavItem('Поговорить', Icons.chat_bubble_rounded, AppRoutes.chat),
      _NavItem('Дневник', Icons.edit_note_rounded, AppRoutes.diary),
      _NavItem('Советы', Icons.spa_rounded, AppRoutes.tips),
      _NavItem('Прогресс', Icons.insights_rounded, AppRoutes.progress),
    ];

    return SafeArea(
      top: false,
      child: Container(
        margin: const EdgeInsets.fromLTRB(12, 0, 12, 10),
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 6),
        decoration: BoxDecoration(
          color: AppColors.card.withOpacity(0.96),
          borderRadius: BorderRadius.circular(28),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.14),
              blurRadius: 16,
              offset: const Offset(0, 6),
            ),
          ],
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: items.map((item) {
            final selected = item.route == currentRoute;
            return Expanded(
              child: InkWell(
                borderRadius: BorderRadius.circular(22),
                onTap: () {
                  if (!selected) context.go(item.route);
                },
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 180),
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  decoration: BoxDecoration(
                    color: selected
                        ? AppColors.forest.withOpacity(0.14)
                        : Colors.transparent,
                    borderRadius: BorderRadius.circular(22),
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        item.icon,
                        size: 22,
                        color: selected
                            ? AppColors.forest
                            : AppColors.brown.withOpacity(0.62),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        item.label,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight:
                              selected ? FontWeight.w700 : FontWeight.w500,
                          color: selected
                              ? AppColors.forest
                              : AppColors.brown.withOpacity(0.68),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            );
          }).toList(),
        ),
      ),
    );
  }
}

class _NavItem {
  const _NavItem(this.label, this.icon, this.route);

  final String label;
  final IconData icon;
  final String route;
}

class _SosPill extends StatelessWidget {
  const _SosPill({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(999),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: AppColors.softPink,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: const Color(0xFFC75D5D), width: 1.4),
        ),
        child: const Text(
          'SOS',
          style: TextStyle(
            color: Color(0xFF9F3131),
            fontWeight: FontWeight.w900,
            letterSpacing: 1,
          ),
        ),
      ),
    );
  }
}

class _TopRoundButton extends StatelessWidget {
  const _TopRoundButton({
    required this.icon,
    required this.tooltip,
    required this.onTap,
  });

  final IconData icon;
  final String tooltip;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: InkWell(
        borderRadius: BorderRadius.circular(999),
        onTap: onTap,
        child: Container(
          width: 42,
          height: 42,
          decoration: BoxDecoration(
            color: AppColors.card.withOpacity(0.95),
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.12),
                blurRadius: 10,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Icon(icon, color: AppColors.brown),
        ),
      ),
    );
  }
}

class SoftCard extends StatelessWidget {
  const SoftCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(16),
    this.color = AppColors.card,
    this.onTap,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final Color color;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final card = Container(
      width: double.infinity,
      padding: padding,
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(26),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.08),
            blurRadius: 12,
            offset: const Offset(0, 5),
          ),
        ],
      ),
      child: child,
    );

    if (onTap == null) return card;

    return InkWell(
      borderRadius: BorderRadius.circular(26),
      onTap: onTap,
      child: card,
    );
  }
}
