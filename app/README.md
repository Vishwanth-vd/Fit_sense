# FitSense AI - Flutter Mobile Application

This directory contains the production Android-first Flutter application for FitSense AI.

## Highlights
- **On-Device Pose Estimation:** Google MediaPipe Pose Landmarker via pinned `flutter_mp_pose_landmarker` plugin.
- **Pure-Dart PushUpAnalyzer:** Bit-for-bit parity with `prototype/analyzer/`.
- **Audio Feedback:** Real-time speech synthesis with rate-limiting using `flutter_tts`.
- **Local Persistence:** Offline-first SQLite database (`sqflite`).
- **Telemetry & Charts:** Interactive analytics using `fl_chart`.
- **Cloud Synchronization:** HTTPS synchronization with FastAPI backend.
