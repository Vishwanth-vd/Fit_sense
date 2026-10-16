// ==============================================================================
// FitSense AI - FpsCalculator Unit Tests
// ==============================================================================

import 'package:test/test.dart';

import '../lib/services/fps_calculator.dart';

void main() {
  group('FpsCalculator', () {
    test('initial state has 0 FPS and 0 frames', () {
      final calc = FpsCalculator();
      expect(calc.currentFps, 0.0);
      expect(calc.totalFramesMeasured, 0);
    });

    test('records frames and computes positive FPS', () async {
      final calc = FpsCalculator(windowSize: 10);

      // Record first frame
      calc.onFrame();
      expect(calc.totalFramesMeasured, 1);

      // Wait 33 ms (~30 FPS) and record second frame
      await Future<void>.delayed(const Duration(milliseconds: 33));
      final fps = calc.onFrame();

      expect(calc.totalFramesMeasured, 2);
      expect(fps, greaterThan(15.0));
      expect(fps, lessThan(45.0));
    });

    test('reset clears history and fps', () async {
      final calc = FpsCalculator();
      calc.onFrame();
      await Future<void>.delayed(const Duration(milliseconds: 30));
      calc.onFrame();

      expect(calc.totalFramesMeasured, 2);
      calc.reset();
      expect(calc.currentFps, 0.0);
      expect(calc.totalFramesMeasured, 0);
    });
  });
}
