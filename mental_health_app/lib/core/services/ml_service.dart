class MLService {
  bool _isInitialized = false;

  Future<void> initialize() async {
    _isInitialized = true;
  }

  Future<Map<String, double>> predictNextMood(List<dynamic> entries) async {
    if (!_isInitialized) {
      await initialize();
    }
    return <String, double>{};
  }

  void dispose() {
    _isInitialized = false;
  }
}
