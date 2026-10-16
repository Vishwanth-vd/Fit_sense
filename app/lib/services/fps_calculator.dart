// ==============================================================================
// FitSense AI - Real-time Frame Rate (FPS) Telemetry Calculator
// ==============================================================================

class FpsCalculator {
  final int windowSize;
  final List<double> _frameTimesMs = [];
  int _lastTimestampMs = 0;
  double _currentFps = 0.0;
  int _totalFramesMeasured = 0;

  FpsCalculator({this.windowSize = 30});

  /// Resets all counters and frame history.
  void reset() {
    _frameTimesMs.clear();
    _lastTimestampMs = 0;
    _currentFps = 0.0;
    _totalFramesMeasured = 0;
  }

  /// Records a new camera / pose frame event and updates rolling FPS.
  double onFrame() {
    final now = DateTime.now().millisecondsSinceEpoch;

    if (_lastTimestampMs > 0) {
      final deltaMs = now - _lastTimestampMs;
      if (deltaMs > 0) {
        _frameTimesMs.add(deltaMs.toDouble());
        if (_frameTimesMs.length > windowSize) {
          _frameTimesMs.removeAt(0);
        }

        final avgDeltaMs =
            _frameTimesMs.reduce((a, b) => a + b) / _frameTimesMs.length;
        _currentFps = avgDeltaMs > 0 ? (1000.0 / avgDeltaMs) : 0.0;
      }
    }

    _lastTimestampMs = now;
    _totalFramesMeasured++;
    return _currentFps;
  }

  /// Current smoothed rolling FPS.
  double get currentFps => _currentFps;

  /// Total frames processed in this session.
  int get totalFramesMeasured => _totalFramesMeasured;
}
