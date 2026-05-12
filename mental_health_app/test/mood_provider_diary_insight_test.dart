import 'package:flutter_test/flutter_test.dart';
import 'package:mental_health_app/core/services/mood_repository.dart';
import 'package:mental_health_app/providers/mood_provider.dart';

void main() {
  group('MoodProvider diary insight', () {
    test('shows onboarding text when diary is empty', () {
      final provider = MoodProvider(repository: InMemoryMoodRepository());

      expect(provider.getDiaryInsight(), MoodProvider.diaryOnboardingInsight);
    });

    test('asks for more data before three entries', () async {
      final provider = MoodProvider(repository: InMemoryMoodRepository());

      await provider.addEntry(
        emotion: 'Neutral',
        stressLevel: 5,
        timestamp: DateTime.now().subtract(const Duration(days: 1)),
      );
      await provider.addEntry(
        emotion: 'Calm',
        stressLevel: 4,
        timestamp: DateTime.now(),
      );

      expect(
        provider.getDiaryInsight(),
        MoodProvider.diaryNeedsMoreDataInsight,
      );
    });

    test(
      'builds deterministic local insight from three or more entries',
      () async {
        final provider = MoodProvider(repository: InMemoryMoodRepository());

        for (var index = 0; index < 3; index++) {
          await provider.addEntry(
            emotion: 'Sad',
            stressLevel: 8,
            timestamp: DateTime.now().subtract(Duration(days: index)),
          );
        }

        final first = provider.getDiaryInsight();
        final second = provider.getDiaryInsight();

        expect(first, second);
        expect(first, contains('За последние 7 дней'));
        expect(first, contains('повышенным'));
      },
    );

    test('save persists entry through repository', () async {
      final repository = InMemoryMoodRepository();
      final provider = MoodProvider(repository: repository);

      await provider.addEntry(
        emotion: 'Happy',
        stressLevel: 2,
        note: 'Good walk.',
      );

      final saved = await repository.fetchEntries();
      expect(saved, hasLength(1));
      expect(saved.single.emotion, 'Happy');
      expect(saved.single.note, 'Good walk.');
    });
  });
}
