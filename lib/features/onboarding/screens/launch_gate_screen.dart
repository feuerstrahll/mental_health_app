import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../../core/constants/app_constants.dart';
import '../../../providers/settings_provider.dart';

class LaunchGateScreen extends StatefulWidget {
  const LaunchGateScreen({super.key});

  @override
  State<LaunchGateScreen> createState() => _LaunchGateScreenState();
}

class _LaunchGateScreenState extends State<LaunchGateScreen> {
  bool _redirected = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final settings = context.watch<SettingsProvider>();

    if (_redirected || settings.isLoading) return;
    _redirected = true;

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      context.go(
        settings.onboardingComplete ? AppRoutes.home : AppRoutes.onboarding,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      backgroundColor: Color(0xFF7EAF5C),
      body: Center(
        child: CircularProgressIndicator(color: Color(0xFFFFF4C8)),
      ),
    );
  }
}
