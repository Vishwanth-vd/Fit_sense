# FitSense AI - Python Reference Prototype

This directory houses the Python reference implementation of the push-up biomechanics analyzer, video/webcam runner, synthetic test vectors, and parity exporter for the Flutter/Dart port.

## Structure
- `analyzer/`: Pure Python push-up analyzer, biomechanics math, and FSM state machine.
- `config/`: Centralized algorithm thresholds (UP/DOWN angles, window size, z-score limits, etc.).
- `runners/`: Video file and live webcam processing scripts.
- `tests/`: Comprehensive unit tests with synthetic test vector generation (clean reps, partial reps, jitter, leaving frame).
- `vectors/`: Exported golden JSON test vectors used to guarantee 100% parity with the Dart port in `app/`.
